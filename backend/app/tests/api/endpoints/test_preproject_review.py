"""Isolated review recovery, concurrency and public response checks."""
import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from app.api import preproject_data as api


def test_public_response_removes_internal_paths():
    result = api._public({"task_dir": "C:\\private\\job", "nested": {"raw_file_path": "/private/data", "error": "failed '/tmp/private/file'"}, "source_url": "https://example.com/data"})
    assert "task_dir" not in result and "raw_file_path" not in result["nested"]
    assert "/tmp/private" not in result["nested"]["error"]
    assert result["source_url"] == "https://example.com/data"
    assert api._public({"source_url": "file:///private/local.csv"})["source_url"] == "[本地路径]"


def test_review_lock_rejects_concurrent_worker(tmp_path):
    with api._review_lock(tmp_path):
        with pytest.raises(HTTPException) as exc:
            with api._review_lock(tmp_path):
                pass
    assert exc.value.status_code == 409
    with api._review_lock(tmp_path):
        pass


def test_stale_review_revision_is_rejected(tmp_path):
    output = tmp_path / "output"; output.mkdir()
    (output / "review_queue.jsonl").write_text(json.dumps({"sample_id": "fixture", "status": "review", "reasons": []}) + "\n", encoding="utf-8")
    (tmp_path / "review_state.json").write_text(json.dumps({"items": {}, "revision": 2, "rebuild_status": "completed"}), encoding="utf-8")
    task = {"task_id": "a" * 32, "task_dir": str(tmp_path), "status": "completed"}
    with patch.object(api, "_get_task", return_value=task):
        with pytest.raises(HTTPException) as exc:
            api.submit_review(task["task_id"], api.ReviewRequest(sample_id="fixture", decision="accept", expected_revision=1), SimpleNamespace(id="reviewer"))
    assert exc.value.status_code == 409


def test_review_failure_persists_pending_and_can_rebuild(tmp_path):
    output = tmp_path / "output"
    output.mkdir()
    (output / "review_queue.jsonl").write_text(json.dumps({"sample_id": "fixture", "status": "review", "reasons": ["near_duplicate_requires_review"]}) + "\n", encoding="utf-8")
    task = {"task_id": "a" * 32, "task_dir": str(tmp_path), "status": "completed", "source_id": "source", "version_id": "old"}
    user = SimpleNamespace(id="TEST-ONLY")
    normalized = {"sample_id": "fixture", "instruction": "q", "input": "", "output": "a", "system": "", "processing_status": "review", "processing_reasons": [], "status_history": [], "cleaning_changes": [], "_source_fields": {}}
    request = api.ReviewRequest(sample_id="fixture", decision="accept", expected_revision=0)
    with patch.object(api, "_get_task", return_value=task), patch.object(api, "_safe_normalized_sample", return_value=normalized), patch.object(api, "_store_task"), patch.object(api, "_rebuild_reviewed_version", side_effect=RuntimeError("fixture failure")):
        with pytest.raises(HTTPException) as exc:
            api.submit_review(task["task_id"], request, user)
        assert exc.value.status_code == 500
    state = json.loads((tmp_path / "review_state.json").read_text(encoding="utf-8"))
    assert state["revision"] == 1 and state["rebuild_status"] == "pending"
    assert len(state["events"]) == 1 and task["review_rebuild_status"] == "pending"
    with patch.object(api, "_get_task", return_value=task), patch.object(api, "_store_task"), patch.object(api, "_rebuild_reviewed_version", return_value={"version_id": "reviewed_fixture"}):
        result = api.retry_review_rebuild(task["task_id"], user)
    assert result["quality_recomputed"] is True
    assert json.loads((tmp_path / "review_state.json").read_text(encoding="utf-8"))["rebuild_status"] == "completed"


def test_formal_environment_rejects_insecure_defaults():
    import os
    import subprocess
    import sys
    env = {**os.environ, "APP_ENV": "production", "AUTH_MODE": "passwordless", "SECRET_KEY": "local-development-only-secret"}
    completed = subprocess.run([sys.executable, "-c", "import app.core.config"], env=env, capture_output=True, timeout=20)
    assert completed.returncode != 0
