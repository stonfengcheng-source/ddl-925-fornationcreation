"""Run real governance and supervised training using isolated HTTP storage."""
import hashlib
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "tmp/baseline-v13" / uuid.uuid4().hex[:10]
RUN.mkdir(parents=True, exist_ok=True)
env = {**os.environ, "APP_ENV":"development", "AUTH_MODE":"passwordless", "DEV_AUTH_USERNAME":"admin", "PLATFORM_DEMO_MODE":"1",
       "DATABASE_URL":"sqlite:///" + (RUN / "test.db").as_posix(), "PREPROJECT_DATA_DIR":str(RUN / "storage")}
events = []
log = (RUN / "server.log").open("w", encoding="utf-8")
server = None

def start():
    global server
    server = subprocess.Popen([sys.executable,"-m","uvicorn","app.main:app","--host","127.0.0.1","--port","18889"], cwd=ROOT / "backend", env=env, stdout=log, stderr=log)
    for _ in range(120):
        try:
            if client.get("http://127.0.0.1:18889/health").status_code == 200: return
        except httpx.TransportError: pass
        if server.poll() is not None: raise RuntimeError("service failed to start")
        time.sleep(.25)
    raise RuntimeError("service did not become ready")

def stop():
    if server and server.poll() is None:
        server.terminate()
        try: server.wait(timeout=10)
        except subprocess.TimeoutExpired: server.kill(); server.wait()

def call(step, response, expected=200):
    events.append({"step":step,"status":response.status_code})
    if response.status_code != expected: raise RuntimeError(f"{step}: {response.status_code}: {response.text[:600]}")
    return response

def wait(path):
    for _ in range(600):
        state = client.get(path).json()
        if state["status"] in {"completed","failed","cancelled"}:
            if state["status"] != "completed": raise RuntimeError(f"{path} failed: {state.get('error')}")
            return state
        time.sleep(.25)
    raise RuntimeError("task timeout")

try:
    with httpx.Client(base_url="http://127.0.0.1:18889/api", timeout=90, trust_env=False) as client:
        start()
        assert not call("empty_tasks", client.get("/preproject-data/tasks")).json()["items"]
        boot = call("bootstrap_resources", client.post("/preproject-data/examples/bootstrap")).json()
        prepared_tasks = call("bootstrap_prepares_version", client.get("/preproject-data/tasks")).json()["items"]
        assert len(prepared_tasks) == 1 and prepared_tasks[0]["status"] == "completed"
        assert not call("bootstrap_does_not_train", client.get("/baseline/experiments")).json()["items"]
        again = call("bootstrap_idempotent", client.post("/preproject-data/examples/bootstrap")).json()
        assert again["classification_version"]["version_id"] == boot["classification_version"]["version_id"]
        token = call("login", client.post("/auth/login", json={"username":"admin", "password":"", "source":"web"})).json()["token"]
        client.headers["Authorization"] = "Bearer " + token
        source = boot["classification_source"]
        assert source["sample_count"] == 54 and source["is_classification_dataset"]
        governance_source = boot["source"]
        qa = call("start_qa_governance", client.post("/preproject-data/tasks", json={"source_id":governance_source["source_id"],"template_id":"education_qa","version_name":"问答治理"}), 202).json()["task"]
        qa = wait(f"/preproject-data/tasks/{qa['task_id']}")
        incompatible = call("unlabeled_training_denied", client.post("/baseline/experiments", json={"version_id":qa["version_id"],"seed":42,"test_size":.25}), 409).json()
        assert "分类标签" in str(incompatible)
        qa_id = qa["task_id"]
        qa_result = call("synthetic_governance_results", client.get(f"/preproject-data/tasks/{qa_id}/results")).json()
        assert qa_result["outcome"]["professional"]["status"] == "unverified"
        assert qa_result["outcome"]["publication"]["status"] == "blocked"
        for issue in ("structure_conversion", "cleaning_modified", "near_duplicate_requires_review", "privacy_hit", "pending_review"):
            samples = call("synthetic_samples_" + issue, client.get(f"/preproject-data/tasks/{qa_id}/samples", params={"issue":issue})).json()
            assert "items" in samples and "total" in samples
        preview = call("synthetic_processed_preview", client.get(f"/preproject-data/tasks/{qa_id}/delivery-preview?kind=processed")).json()
        qualified_preview = call("synthetic_qualified_preview", client.get(f"/preproject-data/tasks/{qa_id}/delivery-preview?kind=qualified")).json()
        assert preview["total"] == qa_result["statistics"]["raw_sample_count"] and qualified_preview["total"] == qa_result["statistics"]["final_retained_count"]
        qa_report = call("synthetic_governance_report", client.get(f"/preproject-data/tasks/{qa_id}/governance-report")).text
        assert "执行摘要" in qa_report and "专业内容认定" in qa_report and "发布授权认定" in qa_report
        (RUN.parent / "synthetic_governance_report.md").write_text(qa_report, encoding="utf-8")
        queue = call("synthetic_review_queue", client.get(f"/preproject-data/tasks/{qa_id}/review-items")).json()
        if queue["items"]:
            reviewed = call("synthetic_review", client.post(f"/preproject-data/tasks/{qa_id}/reviews", json={"sample_id":queue["items"][0]["sample_id"],"decision":"reject","expected_revision":queue["revision"]}), 201).json()
            assert reviewed["quality_recomputed"]
            after = call("reviewed_processed_preview", client.get(f"/preproject-data/tasks/{qa_id}/delivery-preview?kind=processed")).json()
            after_qualified = call("reviewed_qualified_preview", client.get(f"/preproject-data/tasks/{qa_id}/delivery-preview?kind=qualified")).json()
            assert after["filename"] == "reviewed_all.jsonl" and after_qualified["filename"] == "reviewed_processed.jsonl" and after["version_id"] == after_qualified["version_id"]
            call("reviewed_processed_download", client.get(f"/preproject-data/tasks/{qa_id}/files/{after['filename']}"))
            call("reviewed_qualified_download", client.get(f"/preproject-data/tasks/{qa_id}/files/{after_qualified['filename']}"))
        assert call("validate_data", client.post(f"/preproject-data/sources/{source['source_id']}/validate")).json()["valid"]
        task = call("read_prepared_governance", client.get(f"/preproject-data/tasks/{boot['classification_version']['task_id']}")).json()
        assert task["status"] == "completed"
        result = call("quality", client.get(f"/preproject-data/tasks/{task['task_id']}/results")).json()
        call("governed_download", client.get(f"/preproject-data/tasks/{task['task_id']}/files/qualified.jsonl"))
        versions = call("classification_versions", client.get("/baseline/versions")).json()["items"]
        item = next(v for v in versions if v["version_id"] == task["version_id"])
        assert item["compatible"] and item["is_default"] and sum(item["label_distribution"].values()) == item["sample_count"], item
        assert call("baseline_environment", client.get("/baseline/environment")).json()["ready"]
        job = call("start_baseline", client.post("/baseline/experiments", json={"version_id":item["version_id"],"seed":42,"test_size":.25}), 202).json()
        job = wait(f"/baseline/experiments/{job['experiment_id']}")
        metric = job["metrics"]
        assert metric["train_count"] > 0 and metric["test_count"] > 0 and metric["classes"] and 0 <= metric["accuracy"] <= 1
        predictions = [json.loads(line) for line in call("prediction_download", client.get(f"/baseline/experiments/{job['experiment_id']}/files/predictions.jsonl")).text.splitlines() if line]
        split = call("split_download", client.get(f"/baseline/experiments/{job['experiment_id']}/files/split.json")).json()
        assert not set(split["train_ids"]) & set(split["test_ids"]) and len(predictions) == metric["test_count"]
        assert abs(sum(r["actual"] == r["predicted"] for r in predictions) / len(predictions) - metric["accuracy"]) < 1e-12
        classes = metric["classes"]
        matrix = [[sum(r["actual"] == actual and r["predicted"] == predicted for r in predictions) for predicted in classes] for actual in classes]
        assert matrix == metric["confusion_matrix"]
        f1 = sum((2 * matrix[i][i]) / (sum(matrix[i]) + sum(row[i] for row in matrix)) if (sum(matrix[i]) + sum(row[i] for row in matrix)) else 0 for i in range(len(classes))) / len(classes)
        assert abs(f1 - metric["macro_f1"]) < 1e-12
        model = call("model_download", client.get(f"/baseline/experiments/{job['experiment_id']}/files/model.joblib")).content
        report = call("report_download", client.get(f"/baseline/experiments/{job['experiment_id']}/files/report.md")).content
        call("errors_download", client.get(f"/baseline/experiments/{job['experiment_id']}/files/errors.jsonl"))
        assert model and report and job["logs"]
        exported = RUN / "model-verification.joblib"; exported.write_bytes(model)
        samples_path = RUN / "predictions-verification.json"; samples_path.write_text(json.dumps(predictions, ensure_ascii=False), encoding="utf-8")
        verify_code = """import os,sys,json,pathlib
handles=[]
if os.name=='nt':
 for p in [pathlib.Path(sys.base_prefix)/'Library'/'bin',pathlib.Path(sys.base_prefix)/'DLLs']:
  if p.is_dir(): handles.append(os.add_dll_directory(str(p))); os.environ['PATH']=str(p)+os.pathsep+os.environ.get('PATH','')
import joblib
rows=json.loads(pathlib.Path(sys.argv[2]).read_text(encoding='utf-8'))
assert joblib.load(sys.argv[1]).predict([r['text'] for r in rows]).tolist()==[r['predicted'] for r in rows]
print('MODEL_RELOAD_PASS')"""
        runtime = ROOT / "data/runtime/baseline-env/Scripts/python.exe"
        verified = subprocess.run([str(runtime), "-c", verify_code, str(exported), str(samples_path)], capture_output=True, text=True, timeout=60)
        assert verified.returncode == 0 and "MODEL_RELOAD_PASS" in verified.stdout, verified.stderr
        events.append({"step":"reload_model_and_reproduce_predictions", "status":"passed"})
        other = call("other_login", client.post("/auth/login", json={"username":"baseline_other", "password":"", "source":"web"})).json()["token"]
        headers = {"Authorization":"Bearer " + other}
        call("other_experiment_denied", client.get(f"/baseline/experiments/{job['experiment_id']}", headers=headers), 404)
        call("other_model_denied", client.get(f"/baseline/experiments/{job['experiment_id']}/files/model.joblib", headers=headers), 404)
        stop(); start()
        restored = call("restart_experiment", client.get(f"/baseline/experiments/{job['experiment_id']}")).json()
        assert restored["status"] == "completed" and restored["metrics"] == metric
        restored_default = call("restart_prepare", client.post("/preproject-data/examples/bootstrap")).json()
        assert restored_default["classification_version"]["version_id"] == item["version_id"]
        record = {"result":"BASELINE_TRAINING_PASS", "events":events, "source_count":source["sample_count"],
                  "governance_input":result["statistics"]["raw_sample_count"], "governance_qualified":result["statistics"]["final_retained_count"], "synthetic_governance_outcome":qa_result["outcome"],
                  "experiment_id":job["experiment_id"], "model_version_id":item["version_id"], "metrics":metric, "error_count":len(job["errors"]),
                  "execution_summary":"python -u scripts/train_text_baseline.py --seed 42 --test-size 0.25", "reported_metrics_independently_recomputed":True,
                  "model_sha256":hashlib.sha256(model).hexdigest(), "model_bytes":len(model), "report_sha256":hashlib.sha256(report).hexdigest(),
                  "model_training_kind":"synthetic supervised classification baseline", "llm_or_proxy_training":False, "browser_tested":False}
        (RUN.parent / "acceptance_results.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(record, ensure_ascii=False))
finally:
    stop(); log.close()
