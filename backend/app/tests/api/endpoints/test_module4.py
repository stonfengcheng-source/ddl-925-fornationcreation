"""验证主平台 API 能启动真实的小数据任务，并隔离各测试的产物。"""
import json
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import module4
from app.api.auth import get_current_user
from app.services import module4 as runtime


@pytest.fixture
def client(tmp_path, monkeypatch):
    app = FastAPI()
    app.include_router(module4.router, prefix="/api/module4")
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(user_type="admin")
    manager = runtime.TaskManager()
    monkeypatch.setattr(module4, "TASKS", manager)
    monkeypatch.setattr(module4, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(runtime, "PROJECT_ROOT", tmp_path)
    with TestClient(app) as connection:
        yield connection, app, manager
    manager.stop()


def wait_for_task(connection):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        task = connection.get("/api/module4/status").json()["task"]
        if task["status"] not in {"running", "stopping"}:
            return task
        time.sleep(0.02)
    pytest.fail("Task did not finish")


def test_platform_starts_and_validates_real_dataset_job(client, tmp_path):
    connection, _, _ = client
    project = Path(__file__).resolve().parents[5]
    rows = [json.loads(line) for line in (project / "demo-datasets/education-synthetic/raw_5k.jsonl").read_text(encoding="utf-8").splitlines()[:6]]
    fixtures = tmp_path / "incoming"
    fixtures.mkdir()
    paths = {"raw_path": "candidates.jsonl", "evaluated_path": "quality_evaluated.jsonl", "datajuicer_path": "datajuicer_output.jsonl"}
    for field, filename in paths.items():
        values = [{**row, "rule_pass": True, "quality_score": 0.9} for row in rows] if field == "evaluated_path" else rows
        (fixtures / filename).write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in values), encoding="utf-8")
    response = connection.post("/api/module4/run", json={
        "action": "build_data",
        "config": {
            **{field: str(fixtures / filename) for field, filename in paths.items()},
            "sample_count": 4,
        },
    })
    assert response.status_code == 200
    task = wait_for_task(connection)
    assert task["status"] == "success", task["logs"]
    assert "生成完成" in task["logs"]
    assert (tmp_path / "experiments/module4/data/raw_4.jsonl").exists()
    assert connection.post("/api/module4/run", json={"action": "validate_data", "config": {"sample_count": 4}}).status_code == 200
    assert wait_for_task(connection)["status"] == "success"
    assert connection.get("/api/module4/status").json()["artifacts"]["validation"]


def test_platform_validates_100_raw_samples_with_pending_groups_left_blank(client, tmp_path):
    connection, _, _ = client
    project = Path(__file__).resolve().parents[5]
    response = connection.post("/api/module4/run", json={
        "action": "build_data",
        "config": {"raw_path": str(project / "demo-datasets/education-synthetic/raw_5k.jsonl"),
                   "evaluated_path": "", "datajuicer_path": "", "sample_count": 100},
    })
    assert response.status_code == 200
    task = wait_for_task(connection)
    assert task["status"] == "success", task["logs"]
    state = connection.get("/api/module4/status").json()
    assert state["available_variants"] == ["raw"]
    assert {"rule", "ours"}.issubset(state["pending_variants"])
    training_command, _ = runtime.build_action_command("train", {"sample_count": 100, "variant": "all"})
    assert training_command[training_command.index("--variants") + 1:] == ["raw"]
    eval_command, _ = runtime.build_action_command("eval_dry", {"sample_count": 100, "eval_model": "all"})
    assert eval_command[eval_command.index("--models") + 1:eval_command.index("--env-dir")] == ["base"]
    assert connection.post("/api/module4/run", json={"action": "train", "config": {"sample_count": 100, "variant": "ours"}}).status_code == 400
    assert not (tmp_path / "experiments/module4/data/ours_100.jsonl").exists()
    assert connection.post("/api/module4/run", json={"action": "validate_data", "config": {"sample_count": 100}}).status_code == 200
    assert wait_for_task(connection)["status"] == "success"
    summary = tmp_path / "experiments/module4/results/summary.csv"
    summary.parent.mkdir(parents=True)
    summary.write_text("model,benchmark,mean_score\nraw,test,35\nours,test,90\nrule,test,90\n", encoding="utf-8")
    assert [row["model"] for row in connection.get("/api/module4/results").json()["rows"]] == ["raw"]




def test_invalid_action_and_duplicate_start(client):
    connection, _, manager = client
    assert connection.post("/api/module4/run", json={"action": "arbitrary_command"}).status_code == 400
    manager.status = "stopping"
    assert connection.post("/api/module4/run", json={"action": "validate_data"}).status_code == 409
    manager.status = "idle"


def test_existing_platform_roles_are_enforced(client):
    connection, app, _ = client
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(user_type="provider")
    assert connection.get("/api/module4/status").status_code == 403
    assert connection.post("/api/module4/run", json={"action": "build_data"}).status_code == 403


def test_stop_pending_job_before_process_creation(monkeypatch):
    class PendingThread:
        def __init__(self, **_kwargs):
            pass

        def start(self):
            pass

    monkeypatch.setattr(runtime.threading, "Thread", PendingThread)
    manager = runtime.TaskManager()
    manager.start([sys.executable, "-c", "raise AssertionError('must not run')"], "待启动任务")
    assert manager.stop()
    with pytest.raises(RuntimeError):
        manager.start([], "重复任务")
    manager._worker(["must-not-be-executed"])
    assert manager.snapshot()["status"] == "stopped"


def test_stop_running_job_and_clear_logs(client):
    connection, _, manager = client
    manager.start([sys.executable, "-u", "-c", "import time; print('ready'); time.sleep(30)"], "可停止任务")
    deadline = time.monotonic() + 5
    while "ready" not in manager.snapshot()["logs"] and time.monotonic() < deadline:
        time.sleep(0.02)
    assert "ready" in manager.snapshot()["logs"]
    assert connection.post("/api/module4/stop").status_code == 200
    assert wait_for_task(connection)["status"] == "stopped"
    assert connection.post("/api/module4/clear").status_code == 200
    assert connection.get("/api/module4/status").json()["task"]["logs"] == ""


def test_summary_results_are_read_in_platform(client, tmp_path):
    connection, _, _ = client
    assert connection.get("/api/module4/results").json() == {"rows": []}
    report = tmp_path / "experiments/module4/results/summary.csv"
    report.parent.mkdir(parents=True)
    report.write_text("model,benchmark,mean_score,delta_score\nours,ceval_macro,60,5\n", encoding="utf-8-sig")
    report.with_suffix(".metadata.json").write_text(json.dumps({"sample_count": 4}), encoding="utf-8")
    assert connection.get("/api/module4/results").json()["rows"][0]["model"] == "ours"
    assert connection.get("/api/module4/results").json()["metadata"]["sample_count"] == 4


def test_progress_requires_successful_adapter_audit(client, tmp_path):
    connection, _, _ = client
    folder = tmp_path / "experiments/module4/checkpoints/ours"
    folder.mkdir(parents=True)
    (folder / "adapter_model.safetensors").write_bytes(b"placeholder")
    audit = folder / "training_audit.json"
    audit.write_text(json.dumps({"has_update": False}), encoding="utf-8")
    assert not connection.get("/api/module4/status").json()["artifacts"]["checkpoints"]["ours"]
    audit.write_text(json.dumps({"has_update": True}), encoding="utf-8")
    assert connection.get("/api/module4/status").json()["artifacts"]["checkpoints"]["ours"]


def test_badcase_export_uses_selected_python_and_model(client, tmp_path):
    connection, _, _ = client
    predictions = tmp_path / "predictions.jsonl"
    predictions.write_text(json.dumps({"id": "sample-1", "question": "Q", "prediction": "A", "reference": "B", "correct": False}) + "\n", encoding="utf-8")
    response = connection.post("/api/module4/run", json={
        "action": "export_badcases",
        "config": {"training_python": sys.executable, "predictions_path": str(predictions), "badcase_model": "ours"},
    })
    assert response.status_code == 200
    task = wait_for_task(connection)
    assert task["status"] == "success", task["logs"]
    output = tmp_path / "experiments/module4/results/ours_badcases.jsonl"
    assert json.loads(output.read_text(encoding="utf-8").strip())["sample_id"] == "sample-1"
    assert connection.post("/api/module4/run", json={"action": "train", "config": {"training_python": str(tmp_path / "missing.exe")}}).status_code == 400










def test_generates_base_only_evaluation_when_raw_is_not_merged(client, tmp_path):
    connection, _, _ = client
    response = connection.post("/api/module4/run", json={
        "action": "make_eval_manifest",
        "config": {"training_python": sys.executable, "eval_model": "all", "base_model": "local/test-model",
                   "eval_workspace": str(tmp_path / "ascii_workspace")},
    })
    assert response.status_code == 200
    task = wait_for_task(connection)
    assert task["status"] == "success", task["logs"]
    manifest = json.loads((tmp_path / "experiments/module4/evaluation/eval_manifest.json").read_text(encoding="utf-8"))
    assert set(manifest["models"]) == {"base"}
    assert manifest["max_out_len"] == 512
    assert connection.get("/api/module4/status").json()["available_models"] == ["base"]
    rejected = connection.post("/api/module4/run", json={"action": "make_eval_manifest", "config": {"eval_model": "raw"}})
    assert rejected.status_code == 400
    assert "训练和合并" in rejected.json()["detail"]


def test_custom_evaluation_generates_selected_subjects_and_rejects_stale_manifest(client, tmp_path):
    connection, _, _ = client
    config = {
        "training_python": sys.executable, "eval_model": "base", "base_model": "local/test-model",
        "eval_workspace": str(tmp_path / "ascii_workspace"), "eval_mode": "custom",
        "eval_subjects": ["ceval:law", "cmmlu:education"], "eval_samples_per_subject": 7,
    }
    response = connection.post("/api/module4/run", json={"action": "make_eval_manifest", "config": config})
    assert response.status_code == 200
    task = wait_for_task(connection)
    assert task["status"] == "success", task["logs"]
    manifest = json.loads((tmp_path / "experiments/module4/evaluation/eval_manifest.json").read_text(encoding="utf-8"))
    assert manifest["selected_subjects"] == config["eval_subjects"]
    assert manifest["evaluation_profile"]["max_questions_per_model"] == 14
    command, _ = runtime.build_action_command("eval_run", config)
    assert "run" in command
    for changed in [{"eval_samples_per_subject": 8}, {"eval_subjects": ["ceval:law"]}, {"eval_all_questions": True}]:
        response = connection.post("/api/module4/run", json={"action": "eval_run", "config": {**config, **changed}})
        assert response.status_code == 400
        assert "重新生成评测配置" in response.json()["detail"]


@pytest.mark.parametrize("changed", [
    {"eval_subjects": []}, {"eval_subjects": ["ceval:invalid"]}, {"eval_samples_per_subject": 0},
    {"eval_samples_per_subject": 1.5}, {"eval_samples_per_subject": True}, {"eval_samples_per_subject": 10001},
])
def test_custom_evaluation_rejects_invalid_selection(client, changed):
    connection, _, manager = client
    response = connection.post("/api/module4/run", json={"action": "make_eval_manifest", "config": {
        "eval_mode": "custom", "eval_subjects": ["ceval:law"], "eval_samples_per_subject": 7, **changed,
    }})
    assert response.status_code == 400
    assert manager.status == "idle"


def test_results_from_old_output_limits_are_not_displayed_as_current(client, tmp_path):
    connection, _, _ = client
    result_dir = tmp_path / "experiments/module4/results"
    result_dir.mkdir(parents=True)
    (result_dir / "summary.csv").write_text("model,benchmark,mean_score\nbase,cmmlu-machine_learning,35\n", encoding="utf-8")
    manifest_dir = tmp_path / "experiments/module4/evaluation"
    manifest_dir.mkdir(parents=True)
    current = {"protocol_version": 3, "max_out_len": 512, "run_dir": "new_output_512"}
    (manifest_dir / "eval_manifest.json").write_text(json.dumps(current), encoding="utf-8")
    metadata = result_dir / "summary.metadata.json"
    metadata.write_text(json.dumps({"protocol_version": 2, "max_out_len": 64, "run_dir": "old_output_64"}), encoding="utf-8")
    assert connection.get("/api/module4/results").json()["rows"] == []
    metadata.write_text(json.dumps(current), encoding="utf-8")
    assert len(connection.get("/api/module4/results").json()["rows"]) == 1
    metadata.write_text(json.dumps({**current, "max_out_len": 1024}), encoding="utf-8")
    assert connection.get("/api/module4/results").json()["rows"] == []


def test_progress_requires_fresh_output_and_is_independent_of_previous_steps(client, tmp_path, monkeypatch):
    connection, _, manager = client
    results = tmp_path / "experiments/module4/results"
    results.mkdir(parents=True)
    summary = results / "summary.csv"
    summary.write_text("old result", encoding="utf-8")
    state = connection.get("/api/module4/status").json()
    assert state["artifacts"]["summary"]
    assert not state["progress"]["summary"]

    def run(action, code):
        manager.start([sys.executable, "-c", code], action, action, {"sample_count": 100})
        return wait_for_task(connection)

    assert run("compare_results", "pass")["status"] == "success"
    assert not connection.get("/api/module4/status").json()["progress"]["summary"]
    write_summary = "import csv; from pathlib import Path; f=Path('experiments/module4/results/summary.csv').open('w'); w=csv.writer(f); w.writerow(['model','benchmark','mean_score']); w.writerow(['base','overall_macro',35]); f.close()"
    assert run("compare_results", write_summary)["status"] == "success"
    completed = connection.get("/api/module4/status").json()["progress"]
    assert completed["summary"]
    assert not completed["environment_report"]
    assert not completed["datasets"]
    assert run("check_training_env", "from pathlib import Path; Path('experiments/module4/environment_report.json').write_text('{}')")["status"] == "success"
    assert run("check_eval_env", "pass")["status"] == "success"
    assert connection.get("/api/module4/status").json()["progress"]["summary"]
    assert run("check_training_env", "raise SystemExit(1)")["status"] == "failed"
    failed = connection.get("/api/module4/status").json()["progress"]
    assert not failed["environment_report"]
    assert failed["summary"]

    class PendingThread:
        def __init__(self, **_kwargs):
            pass

        def start(self):
            pass

    with monkeypatch.context() as patch:
        patch.setattr(runtime.threading, "Thread", PendingThread)
        manager.start([sys.executable, "-c", write_summary], "重新汇总", "compare_results", {"sample_count": 100})
        running = connection.get("/api/module4/status").json()
        assert running["task"]["status"] == "running"
        assert not running["progress"]["summary"]
        assert manager.stop()
        manager._worker(["must-not-run"])
    assert manager.snapshot()["status"] == "stopped"
    assert not connection.get("/api/module4/status").json()["progress"]["summary"]
    monkeypatch.setattr(module4, "TASKS", runtime.TaskManager())
    restarted = connection.get("/api/module4/status").json()
    assert restarted["artifacts"]["summary"]
    assert not restarted["progress"]["summary"]


def test_model_progress_requires_fresh_outputs_from_every_active_member(client, tmp_path):
    connection, _, manager = client
    experiment = tmp_path / "experiments/module4"
    (experiment / "data").mkdir(parents=True)
    (experiment / "data/dataset_manifest_100.json").write_text(json.dumps({"variants": {"raw": {}, "rule": {}}}), encoding="utf-8")
    for name in ("raw", "rule"):
        folder = experiment / "checkpoints" / name
        folder.mkdir(parents=True)
        (folder / "adapter_model.safetensors").write_bytes(b"old weights")
        (folder / "training_audit.json").write_text('{"has_update":true}', encoding="utf-8")
    before = connection.get("/api/module4/status").json()
    assert all(before["artifacts"]["checkpoints"].values())
    assert not any(before["progress"]["checkpoints"].values())
    for name in ("raw", "rule"):
        code = f"from pathlib import Path; p=Path('experiments/module4/checkpoints/{name}'); (p/'adapter_model.safetensors').write_bytes(b'new weights'); (p/'training_audit.json').write_text('{{\"has_update\":true}}')"
        manager.start([sys.executable, "-c", code, "--variants", name], "训练", "train", {"sample_count": 100})
        assert wait_for_task(connection)["status"] == "success"
        progress = connection.get("/api/module4/status").json()["progress"]["checkpoints"]
        assert progress["raw"]
        assert progress["rule"] is (name == "rule")


def test_progress_requires_fresh_output_and_is_independent_of_previous_steps(client, tmp_path, monkeypatch):
    connection, _, manager = client
    results = tmp_path / "experiments/module4/results"
    results.mkdir(parents=True)
    summary = results / "summary.csv"
    summary.write_text("old result", encoding="utf-8")
    state = connection.get("/api/module4/status").json()
    assert state["artifacts"]["summary"]
    assert not state["progress"]["summary"]

    def run(action, code):
        manager.start([sys.executable, "-c", code], action, action, {"sample_count": 100})
        return wait_for_task(connection)

    assert run("compare_results", "pass")["status"] == "success"
    assert not connection.get("/api/module4/status").json()["progress"]["summary"]
    write_summary = "import csv; from pathlib import Path; f=Path('experiments/module4/results/summary.csv').open('w'); w=csv.writer(f); w.writerow(['model','benchmark','mean_score']); w.writerow(['base','overall_macro',35]); f.close()"
    assert run("compare_results", write_summary)["status"] == "success"
    completed = connection.get("/api/module4/status").json()["progress"]
    assert completed["summary"]
    assert not completed["environment_report"]
    assert not completed["datasets"]
    assert run("check_training_env", "from pathlib import Path; Path('experiments/module4/environment_report.json').write_text('{}')")["status"] == "success"
    assert run("check_eval_env", "pass")["status"] == "success"
    assert connection.get("/api/module4/status").json()["progress"]["summary"]
    assert run("check_training_env", "raise SystemExit(1)")["status"] == "failed"
    failed = connection.get("/api/module4/status").json()["progress"]
    assert not failed["environment_report"]
    assert failed["summary"]

    class PendingThread:
        def __init__(self, **_kwargs):
            pass

        def start(self):
            pass

    with monkeypatch.context() as patch:
        patch.setattr(runtime.threading, "Thread", PendingThread)
        manager.start([sys.executable, "-c", write_summary], "重新汇总", "compare_results", {"sample_count": 100})
        running = connection.get("/api/module4/status").json()
        assert running["task"]["status"] == "running"
        assert not running["progress"]["summary"]
        assert manager.stop()
        manager._worker(["must-not-run"])
    assert manager.snapshot()["status"] == "stopped"
    assert not connection.get("/api/module4/status").json()["progress"]["summary"]
    monkeypatch.setattr(module4, "TASKS", runtime.TaskManager())
    restarted = connection.get("/api/module4/status").json()
    assert restarted["artifacts"]["summary"]
    assert not restarted["progress"]["summary"]


def test_model_progress_requires_fresh_outputs_from_every_active_member(client, tmp_path):
    connection, _, manager = client
    experiment = tmp_path / "experiments/module4"
    (experiment / "data").mkdir(parents=True)
    (experiment / "data/dataset_manifest_100.json").write_text(json.dumps({"variants": {"raw": {}, "rule": {}}}), encoding="utf-8")
    for name in ("raw", "rule"):
        folder = experiment / "checkpoints" / name
        folder.mkdir(parents=True)
        (folder / "adapter_model.safetensors").write_bytes(b"old weights")
        (folder / "training_audit.json").write_text('{"has_update":true}', encoding="utf-8")
    before = connection.get("/api/module4/status").json()
    assert all(before["artifacts"]["checkpoints"].values())
    assert not any(before["progress"]["checkpoints"].values())
    for name in ("raw", "rule"):
        code = f"from pathlib import Path; p=Path('experiments/module4/checkpoints/{name}'); (p/'adapter_model.safetensors').write_bytes(b'new weights'); (p/'training_audit.json').write_text('{{\"has_update\":true}}')"
        manager.start([sys.executable, "-c", code, "--variants", name], "训练", "train", {"sample_count": 100})
        assert wait_for_task(connection)["status"] == "success"
        progress = connection.get("/api/module4/status").json()["progress"]["checkpoints"]
        assert progress["raw"]
        assert progress["rule"] is (name == "rule")
