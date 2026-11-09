"""Real local HTTP chains using isolated storage; does not train or evaluate a model."""
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
RUN = ROOT / "tmp" / "functional-r10" / uuid.uuid4().hex[:8]
RUN.mkdir(parents=True, exist_ok=True)
env = {**os.environ, "APP_ENV": "development", "AUTH_MODE": "passwordless", "DEV_AUTH_USERNAME": "admin",
       "DATABASE_URL": "sqlite:///" + (RUN / "test.db").as_posix(), "PREPROJECT_DATA_DIR": str(RUN / "storage")}
events = []
with (RUN / "server.log").open("w", encoding="utf-8") as log:
    server = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "18886"],
                              cwd=ROOT / "backend", env=env, stdout=log, stderr=log)
    try:
        with httpx.Client(base_url="http://127.0.0.1:18886/api", timeout=90, trust_env=False) as client:
            for _ in range(80):
                try:
                    if client.get("/preproject-data/sources").status_code == 200: break
                except httpx.TransportError: pass
                time.sleep(.25)
            else: raise RuntimeError("isolated service did not start")
            def call(name, response, expected=200):
                events.append({"step": name, "status": response.status_code})
                if response.status_code != expected: raise RuntimeError(f"{name}: {response.status_code}: {response.text[:500]}")
                return response
            assert not call("empty_sources", client.get("/preproject-data/sources")).json()["items"]
            assert call("local_input_status", client.get("/preproject-data/sources/local-educhat/status")).json()["available"]
            source = call("recover_local_educhat", client.post("/preproject-data/sources/local-educhat"), 201).json()
            source_id = source["source_id"]
            duplicate = call("recover_is_idempotent", client.post("/preproject-data/sources/local-educhat"), 201).json()
            assert duplicate["already_registered"] and duplicate["source_id"] == source_id
            validated = call("validate_source", client.post(f"/preproject-data/sources/{source_id}/validate")).json()
            assert validated["valid"] and validated["row_count"] == 200
            assert call("preview", client.get(f"/preproject-data/sources/{source_id}/preview")).json()["samples"]
            task = call("create_processing_task", client.post("/preproject-data/tasks", json={"source_id": source_id, "version_name": "functional-r10"}), 202).json()["task"]
            task_id = task["task_id"]
            for _ in range(480):
                task = client.get(f"/preproject-data/tasks/{task_id}").json()
                if task["status"] in {"completed", "failed", "cancelled"}: break
                time.sleep(.25)
            if task["status"] != "completed": raise RuntimeError("processing did not complete: " + str(task.get("error")))
            result = call("quality_results", client.get(f"/preproject-data/tasks/{task_id}/results")).json()
            assert result["statistics"]["final_retained_count"] == 200 and not result["gate"]["release_eligible"]
            assert result["outcome"]["engineering"]["candidate_count"] == 200
            assert result["outcome"]["professional"]["status"] == "unverified" and result["outcome"]["publication"]["status"] == "blocked"
            assert result["statistics"]["action_counts"] == result["outcome"]["actions"]
            processed = call("processed_preview", client.get(f"/preproject-data/tasks/{task_id}/delivery-preview?kind=processed")).json()
            qualified = call("qualified_preview", client.get(f"/preproject-data/tasks/{task_id}/delivery-preview?kind=qualified")).json()
            assert processed["total"] == qualified["total"] == 200 and len(processed["items"]) == len(qualified["items"]) == 10
            governance_report = call("current_governance_report", client.get(f"/preproject-data/tasks/{task_id}/governance-report")).text
            assert "执行摘要" in governance_report and "专业内容认定" in governance_report and "发布授权认定" in governance_report
            (RUN.parent / "educhat_governance_report.md").write_text(governance_report, encoding="utf-8")
            candidate_bytes = call("download_candidate", client.get(f"/preproject-data/tasks/{task_id}/files/qualified.jsonl")).content
            call("download_report", client.get(f"/preproject-data/tasks/{task_id}/files/quality_report.md"))
            versions = call("model_validation_versions", client.get("/module4/candidate-versions")).json()["items"]
            selected = next(item for item in versions if item["task_id"] == task_id)
            assert selected["sample_count"] == 200 and not selected["release_eligible"]
            other_login = call("other_user_login", client.post("/auth/login", json={"username":"functional_buyer", "password":"", "source":"web"})).json()
            other_headers = {"Authorization": "Bearer " + other_login["token"]}
            assert not call("other_user_versions", client.get("/module4/candidate-versions", headers=other_headers)).json()["items"]
            call("other_user_version_denied", client.post("/module4/prepare-candidate-config", headers=other_headers, json={"version_id":selected["version_id"], "base_model":"Qwen/Qwen2.5-0.5B-Instruct"}), 404)
            config = {"data_version_id": selected["version_id"], "base_model": "Qwen/Qwen2.5-0.5B-Instruct", "template": "qwen", "epochs": 1, "precision": "bf16", "seed": 42,
                      "sample_count": 200, "eval_model": "base", "eval_mode": "quick", "eval_batch_size": 1, "eval_max_out_len": 512,
                      "eval_workspace": str(RUN / "eval_workspace"), "opencompass_env": str(RUN / "missing_eval_env")}
            prepared = call("prepare_candidate_training_config", client.post("/module4/prepare-candidate-config", json={"version_id": selected["version_id"], "base_model": config["base_model"], "template": "qwen", "epochs": 1, "precision": "bf16", "seed": 42})).json()
            config["candidate_config_id"] = prepared["config_id"]
            link_path = next((RUN / "storage" / "users").glob(f"*/module4_candidates/{prepared['config_id']}/link.json"))
            link = json.loads(link_path.read_text(encoding="utf-8"))
            assert link["source_sha256"] == hashlib.sha256(candidate_bytes).hexdigest()
            training_manifest = json.loads((link_path.parent / "config/training_manifest.json").read_text(encoding="utf-8"))
            assert training_manifest["sample_count"] == 200
            registered = link_path.parent / "config/llamafactory_data/raw_200.jsonl"
            original_ids = {json.loads(line)["sample_id"] for line in candidate_bytes.decode("utf-8").splitlines() if line}
            linked_ids = {json.loads(line)["id"] for line in registered.read_text(encoding="utf-8").splitlines() if line}
            assert original_ids == linked_ids and len(linked_ids) == 200
            preflight = call("model_preflight", client.post("/module4/preflight", json={"action":"inspect", "config":config})).json()
            assert not preflight["training"]["ready"] and not preflight["evaluation"]["ready"]
            assert any(c["key"] == "manifest" and not c["ready"] for c in preflight["evaluation"]["checks"])
            call("blocked_formal_evaluation", client.post("/module4/run", json={"action":"eval_run", "config":config}), 409)
            call("blocked_training", client.post("/module4/run", json={"action":"train", "config":config}), 409)
            eval_out, eval_workspace = RUN / "evaluation", RUN / "eval_workspace"
            command = [sys.executable, str(ROOT / "scripts/module4/04_make_eval_manifest.py"), "--base-model", config["base_model"], "--variants", "--out-dir", str(eval_out), "--workspace-dir", str(eval_workspace), "--eval-mode", "quick", "--batch-size", "1", "--max-out-len", "512"]
            generated = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
            if generated.returncode: raise RuntimeError("real evaluation configuration generation failed: " + generated.stderr[-1000:])
            manifest_path = eval_out / "eval_manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            assert manifest["protocol_version"] == 3 and not manifest["models"]["base"]["exists_locally"]
            sys.path.insert(0, str(ROOT / "backend"))
            from app.services.module4 import evaluation_preflight
            inspected = evaluation_preflight(config, manifest_path=manifest_path)
            checks = {check["key"]: check["ready"] for check in inspected["checks"]}
            assert checks["manifest"] and checks["generated_configs"] and checks["manifest_matches"] and not checks["base_model"]
            events.append({"step": "generate_and_validate_real_eval_configuration", "status": "configuration_generated_model_missing"})
            report = {"events": events, "input_count": validated["row_count"], "qualified_count": 200, "governance_outcome":result["outcome"],
                      "release_eligible": selected["release_eligible"], "candidate_linked_count": len(linked_ids),
                      "training_ready": preflight["training"]["ready"], "evaluation_ready": preflight["evaluation"]["ready"],
                      "training_blockers": [c["message"] for c in preflight["training"]["checks"] if not c["ready"]],
                      "evaluation_blockers": [c["message"] for c in preflight["evaluation"]["checks"] if not c["ready"]],
                      "eval_config_checks": checks, "training_or_evaluation_executed": False}
            (RUN.parent / "functional_results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps(report, ensure_ascii=False))
    finally:
        server.terminate()
        try: server.wait(timeout=10)
        except subprocess.TimeoutExpired: server.kill(); server.wait()
