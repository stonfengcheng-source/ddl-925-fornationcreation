"""Exercise synthetic and real governance workflows against an isolated HTTP server."""
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "tmp/product-r11" / uuid.uuid4().hex[:8]
RUN.mkdir(parents=True, exist_ok=True)
env = {**os.environ, "APP_ENV": "development", "AUTH_MODE": "passwordless", "DEV_AUTH_USERNAME": "admin",
       "DATABASE_URL": "sqlite:///" + (RUN / "test.db").as_posix(), "PREPROJECT_DATA_DIR": str(RUN / "storage")}
events = []
with (RUN / "server.log").open("w", encoding="utf-8") as log:
    server = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "18887"], cwd=ROOT / "backend", env=env, stdout=log, stderr=log)
    try:
        with httpx.Client(base_url="http://127.0.0.1:18887/api", timeout=90, trust_env=False) as client:
            for _ in range(100):
                try:
                    if client.get("/preproject-data/sources").status_code == 200: break
                except httpx.TransportError: pass
                if server.poll() is not None: raise RuntimeError("server exited; see isolated log")
                time.sleep(.25)
            else: raise RuntimeError("isolated service did not start")
            def call(step, response, status=200):
                events.append({"step": step, "status": response.status_code})
                if response.status_code != status: raise RuntimeError(f"{step}: {response.status_code}: {response.text[:800]}")
                return response
            def wait_task(task_id):
                for _ in range(480):
                    task = client.get(f"/preproject-data/tasks/{task_id}").json()
                    if task["status"] in {"completed", "failed", "cancelled"}:
                        if task["status"] != "completed": raise RuntimeError(f"task failed: {task.get('error')}")
                        return task
                    time.sleep(.25)
                raise RuntimeError("task timed out")
            login = call("login", client.post("/auth/login", json={"username": "admin", "password": "", "source": "web"})).json()
            client.headers["Authorization"] = "Bearer " + login["token"]
            assert not call("empty_sources", client.get("/preproject-data/sources")).json()["items"]
            empty = call("empty_overview", client.get("/preproject-data/overview")).json()
            assert empty["asset_count"] == 0 and empty["qualified_versions"] == 0 and empty["experiment_count"] is None
            resources = call("resources", client.get("/preproject-data/resources")).json()
            assert resources["data"]["synthetic_example"] and resources["environments"][0]["ready"]
            call("missing_model_rejected", client.post("/preproject-data/resources/models", json={"name":"missing", "path":str(RUN / "absent-model"), "license_status":"unverified"}), 422)
            call("foreign_model_rejected", client.post("/module4/preflight", json={"action":"inspect", "config":{"base_model":"managed:" + "0" * 32}}), 404)
            assert len(call("templates", client.get("/preproject-data/templates")).json()["items"]) == 2
            example = call("create_synthetic_example", client.post("/preproject-data/examples/governance-task"), 202).json()
            assert example["synthetic"] and example["source"]["source_type"] == "test_fixture"
            task = wait_task(example["task"]["task_id"]); task_id = task["task_id"]
            report = call("example_quality", client.get(f"/preproject-data/tasks/{task_id}/results")).json()
            stats = report["statistics"]
            expected = sum(1 for line in (ROOT / "demo-datasets/governance-example.jsonl").read_text(encoding="utf-8").splitlines() if line.strip())
            assert stats["raw_sample_count"] == expected and not report["gate"]["release_eligible"]
            assert call("example_problem_samples", client.get(f"/preproject-data/tasks/{task_id}/samples")).json()["items"]
            queue = call("example_review_queue", client.get(f"/preproject-data/tasks/{task_id}/review-items")).json()
            review_count = queue["pending_count"]
            for item in queue["items"]:
                if item["decision"] == "pending":
                    call("review_example", client.post(f"/preproject-data/tasks/{task_id}/reviews", json={"sample_id": item["sample_id"], "decision": "reject", "expected_revision": queue["revision"]}), 201)
                    queue = client.get(f"/preproject-data/tasks/{task_id}/review-items").json()
            assert queue["pending_count"] == 0
            call("example_versions", client.get("/preproject-data/versions"))
            linked = call("example_model_candidates", client.get("/module4/candidate-versions")).json()["items"]
            assert any(item["task_id"] == task_id for item in linked)
            overview = call("populated_overview", client.get("/preproject-data/overview")).json()
            assert overview["asset_count"] == 1 and overview["pending_reviews"] == 0 and overview["qualified_versions"] > 0
            call("download_example", client.get(f"/preproject-data/tasks/{task_id}/files/qualified.jsonl"))
            assets = call("my_assets", client.get("/datasets/my")).json()["data"]
            assert any(item["id"] == example["source"]["source_id"] for item in assets)
            other = call("second_user_login", client.post("/auth/login", json={"username": "product_buyer", "password": "", "source": "web"})).json()["token"]
            other_headers = {"Authorization": "Bearer " + other}
            call("other_asset_denied", client.get(f"/datasets/{example['source']['source_id']}", headers=other_headers), 404)
            call("other_asset_update_denied", client.put(f"/datasets/{example['source']['source_id']}", headers=other_headers, json={"name":"not permitted"}), 404)
            call("other_asset_delete_denied", client.delete(f"/datasets/{example['source']['source_id']}", headers=other_headers), 404)
            call("other_task_denied", client.get(f"/preproject-data/tasks/{task_id}", headers=other_headers), 404)
            assert not call("other_versions", client.get("/module4/candidate-versions", headers=other_headers)).json()["items"]
            text_input = b'Synthetic document: water freezes at zero degrees Celsius.\n'
            source = call("import_general_text", client.post("/preproject-data/sources/upload", files={"file": ("text.txt", text_input, "text/plain")}, data={"dataset_id":"synthetic-text-test", "source_url":"synthetic", "license":"test-only", "revision":"synthetic", "split":"test"}), 201).json()
            validation = call("validate_general_text", client.post(f"/preproject-data/sources/{source['source_id']}/validate")).json()
            assert validation["valid"]
            generic = call("run_general_template", client.post("/preproject-data/tasks", json={"source_id":source["source_id"], "template_id":"general_text", "version_name":"synthetic-text"}), 202).json()["task"]
            generic = wait_task(generic["task_id"])
            generic_result = call("general_text_quality", client.get(f"/preproject-data/tasks/{generic['task_id']}/results")).json()
            assert generic_result["statistics"]["raw_sample_count"] == 1
            candidates = call("general_text_not_sft", client.get("/module4/candidate-versions")).json()["items"]
            assert all(item["task_id"] != generic["task_id"] for item in candidates)
            summary = {"events": events, "example_input": stats["raw_sample_count"], "example_review_count": review_count,
                       "example_qualified": stats["final_retained_count"], "example_release_eligible": report["gate"]["release_eligible"],
                       "training_ready": resources["environments"][1]["ready"], "browser_tested": False,
                       "real_training_or_evaluation": False}
            (RUN.parent / "product_results.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps(summary, ensure_ascii=False))
    finally:
        server.terminate()
        try: server.wait(timeout=10)
        except subprocess.TimeoutExpired: server.kill(); server.wait()
