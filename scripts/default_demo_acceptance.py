"""Validate the default demonstration with an isolated local service and database."""
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
RUN = ROOT / "tmp/default-demo-v12" / uuid.uuid4().hex[:10]
RUN.mkdir(parents=True, exist_ok=True)
env = {**os.environ, "APP_ENV":"development", "AUTH_MODE":"passwordless", "DEV_AUTH_USERNAME":"admin", "PLATFORM_DEMO_MODE":"1",
       "DATABASE_URL":"sqlite:///" + (RUN / "demo.db").as_posix(), "PREPROJECT_DATA_DIR":str(RUN / "storage")}
events = []
log = (RUN / "server.log").open("w", encoding="utf-8")
server = None

def start():
    global server
    server = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "18888"], cwd=ROOT / "backend", env=env, stdout=log, stderr=log)
    for _ in range(120):
        try:
            if client.get("http://127.0.0.1:18888/health").status_code == 200: return
        except httpx.TransportError: pass
        if server.poll() is not None: raise RuntimeError("service failed; inspect isolated server log")
        time.sleep(.25)
    raise RuntimeError("service did not become healthy")

def stop():
    if server and server.poll() is None:
        server.terminate()
        try: server.wait(timeout=10)
        except subprocess.TimeoutExpired: server.kill(); server.wait()

def check(label, response, expected=200):
    events.append({"step": label, "status": response.status_code})
    if response.status_code != expected: raise RuntimeError(f"{label}: {response.status_code}: {response.text[:600]}")
    return response

try:
    with httpx.Client(base_url="http://127.0.0.1:18888/api", timeout=90, trust_env=False) as client:
        start()
        assert not check("initial_empty", client.get("/preproject-data/sources")).json()["items"]
        source = check("bootstrap", client.post("/preproject-data/examples/bootstrap")).json()["source"]
        same = check("bootstrap_idempotent", client.post("/preproject-data/examples/bootstrap")).json()["source"]
        expected_count = sum(1 for line in (ROOT / "demo-datasets/governance-example.jsonl").read_text(encoding="utf-8").splitlines() if line.strip())
        assert source["source_id"] == same["source_id"] and source["sample_count"] == expected_count
        login = check("login", client.post("/auth/login", json={"username":"admin", "password":"", "source":"web"})).json()
        client.headers["Authorization"] = "Bearer " + login["token"]
        default = check("default_asset", client.get("/preproject-data/examples/default")).json()
        assert default["ready"] and default["source"]["source_id"] == source["source_id"] and default["template"] == "education_qa"
        assets = check("registered_asset", client.get("/datasets/my")).json()["data"]
        assert len([asset for asset in assets if asset["id"] == source["source_id"]]) == 1
        assert check("validated", client.post(f"/preproject-data/sources/{source['source_id']}/validate")).json()["valid"]
        created = check("start_real_task", client.post("/preproject-data/examples/governance-task"), 202).json()
        task_id = created["task"]["task_id"]
        for _ in range(480):
            task = check("poll", client.get(f"/preproject-data/tasks/{task_id}")).json()
            if task["status"] in {"completed", "failed", "cancelled"}: break
            time.sleep(.25)
        if task["status"] != "completed": raise RuntimeError(f"processing did not complete: {task.get('error')}")
        results = check("quality", client.get(f"/preproject-data/tasks/{task_id}/results")).json()
        stats = results["statistics"]
        assert stats["raw_sample_count"] == expected_count and stats["final_retained_count"] > 0
        assert len(results["quality"]["metrics"]) >= 5 and not results["gate"]["release_eligible"]
        assert stats["privacy_hit_count"] > 0 and stats["privacy_residual_count"] == 0
        assert stats["cleaning_modified_count"] > 0
        assert stats["exact_duplicate_count"] > 0 and stats["normalized_duplicate_count"] > 0 and stats["near_duplicate_sample_count"] > 0
        assert stats["review_count"] > 0
        stage_names = {stage["stage"] for stage in stats.get("stages", [])}
        assert {"normalize_clean", "deduplication", "privacy_and_rescan", "quality_admission"}.issubset(stage_names), stage_names
        samples = check("samples", client.get(f"/preproject-data/tasks/{task_id}/samples")).json()
        assert samples["items"] and "before" in samples["items"][0] and "after" in samples["items"][0]
        check("versions", client.get("/preproject-data/versions"))
        data = check("download_jsonl", client.get(f"/preproject-data/tasks/{task_id}/files/qualified.jsonl")).content
        report = check("download_report", client.get(f"/preproject-data/tasks/{task_id}/files/quality_report.md")).content
        records = [json.loads(line) for line in data.decode("utf-8").splitlines() if line]
        assert len(records) == stats["final_retained_count"] and report and b"13800138000" not in data and b"teacher@example.invalid" not in data
        stop(); start()
        restored = check("restart_bootstrap", client.post("/preproject-data/examples/bootstrap")).json()
        assert restored["source"]["source_id"] == source["source_id"]
        last = check("restart_history", client.get("/preproject-data/examples/default")).json()
        assert last["ready"] and last["task"]["task_id"] == task_id and last["task"]["status"] == "completed"
        resumed = check("resume_without_duplicate", client.post("/preproject-data/examples/governance-task"), 202).json()
        assert resumed["task"]["task_id"] == task_id and resumed["resumed"]
        rerun = check("explicit_rerun", client.post("/preproject-data/examples/governance-task?rerun=true"), 202).json()
        assert rerun["task"]["task_id"] != task_id
        for _ in range(480):
            rerun_task = check("rerun_poll", client.get(f"/preproject-data/tasks/{rerun['task']['task_id']}")).json()
            if rerun_task["status"] in {"completed", "failed", "cancelled"}: break
            time.sleep(.25)
        assert rerun_task["status"] == "completed" and rerun_task["version_id"] != task["version_id"]
        environment = check("optional_resources", client.get("/preproject-data/resources")).json()
        record = {"result":"DEFAULT_DEMO_PASS", "events":events, "input_count":stats["raw_sample_count"],
                  "qualified_count":stats["final_retained_count"], "review_count":stats["review_count"],
                  "cleaning_modified":stats["cleaning_modified_count"],
                  "exact_duplicates":stats["exact_duplicate_count"], "normalized_duplicates":stats["normalized_duplicate_count"],
                  "near_duplicates":stats["near_duplicate_sample_count"], "privacy_hits":stats["privacy_hit_count"],
                  "privacy_residual":stats["privacy_residual_count"], "stages":stats.get("stages"),
                  "metrics":list(results["quality"]["metrics"]), "report_sha256":hashlib.sha256(report).hexdigest(),
                  "qualified_sha256":hashlib.sha256(data).hexdigest(), "training_ready":environment["environments"][1]["ready"],
                  "browser_tested":False, "model_training_executed":False}
        (RUN.parent / "acceptance_results.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(record, ensure_ascii=False))
finally:
    stop(); log.close()
