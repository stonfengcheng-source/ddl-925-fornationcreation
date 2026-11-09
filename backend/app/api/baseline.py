"""User-scoped, persistent supervised text-classification experiments."""
from __future__ import annotations

import json
import math
import os
import re
import subprocess
import threading
import time
import uuid
import unicodedata
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.api import preproject_data as data
from app.api.module4 import _candidate_version, require_operator
from app.models.user import User
from data_pipeline.pipeline import sha256_file

router = APIRouter(dependencies=[Depends(require_operator)])
ROOT = data.PROJECT_ROOT
PYTHON = Path(os.environ.get("BASELINE_PYTHON") or (ROOT / "data/runtime/baseline-env" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")))
ALLOWED = {"model.joblib", "metrics.json", "split.json", "config.json", "errors.jsonl", "predictions.jsonl", "report.md"}
_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="baseline")
_active: set[str] = set()
_lock = threading.RLock()
_probe: tuple[float, dict[str, Any]] = (0, {})


class ExperimentRequest(BaseModel):
    version_id: str = Field(min_length=1, max_length=100)
    seed: int = Field(default=42, ge=0, le=2**31-1)
    test_size: float = Field(default=.25, ge=.1, le=.4)


def _environment() -> dict[str, Any]:
    global _probe
    if time.monotonic() - _probe[0] < 60: return _probe[1]
    result: dict[str, Any] = {"ready": False, "kind": "independent_python_baseline", "message": "轻量训练环境尚未准备。"}
    if PYTHON.is_file():
        try:
            process = subprocess.run([str(PYTHON), str(ROOT / "scripts/check_baseline_env.py")], capture_output=True, text=True, timeout=30, check=False)
            if process.returncode == 0:
                info = json.loads(process.stdout.strip().splitlines()[-1])
                result = {"ready": True, "kind": "independent_python_baseline", "message": "轻量监督学习环境已就绪。", **info}
            else: result["message"] = "轻量训练环境缺少依赖，请按资源准备说明安装。"
        except (OSError, ValueError, IndexError, subprocess.SubprocessError):
            result["message"] = "轻量训练环境检查失败，请查看资源准备说明。"
    _probe = (time.monotonic(), result)
    return result


def _jobs_root(user: User) -> Path:
    return data._user_root(user) / "baseline_experiments"


def _job_path(user: User, job_id: str) -> Path:
    if not re.fullmatch(r"[0-9a-f]{32}", job_id): raise HTTPException(status_code=404, detail="实验不存在。")
    folder = _jobs_root(user) / job_id
    if not (folder / "state.json").is_file(): raise HTTPException(status_code=404, detail="实验不存在。")
    return folder


def _read_state(user: User, job_id: str) -> tuple[Path, dict[str, Any]]:
    path = _job_path(user, job_id)
    state = data._read_json(path / "state.json")
    with _lock:
        if state.get("status") in {"pending", "running"} and job_id not in _active:
            state.update(status="failed", error="服务重启，实验已中断；可重新创建实验。", ended_at=data._now())
            data._atomic_json(path / "state.json", state)
    return path, state


def _safe_state(path: Path, state: dict[str, Any]) -> dict[str, Any]:
    public = {key: state.get(key) for key in ("experiment_id", "version_id", "dataset_id", "status", "created_at", "started_at", "ended_at", "error", "seed", "test_size", "sample_count")}
    public.update(algorithm="TF-IDF + Logistic Regression", training_kind="supervised_classification_baseline",
                  notice="轻量监督分类基线；不是大模型 SFT、LoRA 或 Proxy 结果。")
    if (path / "metrics.json").is_file(): public["metrics"] = data._read_json(path / "metrics.json")
    if (path / "errors.jsonl").is_file(): public["errors"] = data._jsonl_rows(path / "errors.jsonl")[:100]
    public["files"] = sorted(name for name in ALLOWED if (path / name).is_file())
    log_path = path / "run.log"
    if log_path.is_file():
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
        safe = []
        for line in lines:
            if "Traceback" in line: break
            if not line.startswith("Execution command:") and not any(mark in line for mark in ("File ", ":\\", "/Users/")):
                safe.append(line)
        public["logs"] = safe[-15:]
    return public


def _classification_input(user: User, version_id: str) -> tuple[dict[str, Any], list[dict[str, str]]]:
    version, _path, rows = _candidate_version(user, version_id)
    manifest, _ = data._load_source(user, str(version.get("source_id") or ""))
    synthetic = manifest.get("source_type") == "test_fixture" and manifest.get("is_classification_dataset") is True
    authorized = version.get("authorization_status") == "authorized" and version.get("license_verification_status") == "verified"
    prepared = []
    for row in rows:
        label = row.get("classification_label")
        if row.get("task_type") != "text_classification" or not isinstance(label, str) or not re.fullmatch(r"[a-z][a-z0-9_-]{0,31}", label):
            raise HTTPException(status_code=409, detail="此版本没有明确保存的分类标签；问答数据不能自动转换为分类标签。")
        prepared.append({"sample_id": str(row["sample_id"]), "text": str(row["instruction"]), "label": label})
    if not (synthetic or authorized):
        raise HTTPException(status_code=409, detail="分类数据来源或训练许可尚未核验。")
    counts = Counter(item["label"] for item in prepared)
    if len(counts) < 2 or min(counts.values()) < 2:
        raise HTTPException(status_code=409, detail="至少需要两个类别，且每类至少两个合格样本。")
    normalized = ["".join(unicodedata.normalize("NFKC", item["text"]).casefold().split()) for item in prepared]
    if len(normalized) != len(set(normalized)):
        raise HTTPException(status_code=409, detail="数据包含重复文本，请先去重以避免训练与测试泄漏。")
    return version, prepared


@router.get("/environment")
def environment() -> dict[str, Any]:
    return _environment()


@router.get("/versions")
def versions(user: User = Depends(require_operator)) -> dict[str, Any]:
    from app.api.module4 import candidate_versions
    result = []
    for version in candidate_versions(user)["items"]:
        try:
            _version, rows = _classification_input(user, version["version_id"])
            compatible, reason, count = True, "标签与许可条件已检查。", len(rows)
            source, _ = data._load_source(user, str(_version.get("source_id") or ""))
            task = data._get_task(user, str(_version.get("task_id") or ""))
            is_default = bool(source.get("is_classification_dataset") and task.get("parameters", {}).get("version_name") == "平台分类基础版本")
            distribution = dict(sorted(Counter(row["label"] for row in rows).items()))
        except HTTPException as exc:
            compatible, reason, count = False, str(exc.detail), version.get("sample_count", 0)
            is_default, distribution = False, {}
        result.append({**version, "compatible": compatible, "reason": reason, "sample_count":count, "is_default":is_default, "label_distribution":distribution, "governance_status":"已完成"})
    return {"items":result}


@router.post("/prepare-default")
async def prepare_default(user: User = Depends(require_operator), db = Depends(data.get_db)) -> dict[str, Any]:
    if data.APP_ENV in {"production", "prod"} or not data.PASSWORDLESS_AUTH or os.getenv("PLATFORM_DEMO_MODE") != "1":
        raise HTTPException(status_code=403, detail="内置训练数据准备仅适用于本机演示环境。")
    source = await data._ensure_classification_source(user, db)
    return await data._prepare_classification_candidate(user, source)


def _worker(path: Path, state: dict[str, Any]) -> None:
    job_id = state["experiment_id"]
    try:
        state.update(status="running", started_at=data._now()); data._atomic_json(path / "state.json", state)
        command = [str(PYTHON), "-u", str(ROOT / "scripts/train_text_baseline.py"), "--input", str(path / "input.jsonl"),
                   "--output", str(path), "--version-id", state["version_id"], "--seed", str(state["seed"]), "--test-size", str(state["test_size"])]
        # The full execution command and subprocess output remain in user-scoped local storage.
        with (path / "run.log").open("w", encoding="utf-8") as log:
            log.write("Execution command: " + json.dumps(command, ensure_ascii=False) + "\n"); log.flush()
            completed = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=600, check=False)
        if completed.returncode != 0 or not all((path / name).is_file() for name in ("model.joblib", "metrics.json", "split.json", "report.md")):
            state.update(status="failed", error="基线训练未完成，请检查数据和运行日志后重试。")
        else: state.update(status="completed", error=None)
    except (OSError, subprocess.SubprocessError):
        state.update(status="failed", error="无法启动或完成训练，请检查轻量环境。")
    finally:
        state["ended_at"] = data._now(); data._atomic_json(path / "state.json", state)
        with _lock: _active.discard(job_id)


@router.post("/experiments", status_code=202)
def create_experiment(body: ExperimentRequest, user: User = Depends(require_operator)) -> dict[str, Any]:
    if not _environment()["ready"]: raise HTTPException(status_code=409, detail="轻量训练环境尚未就绪，请先准备依赖。")
    version, rows = _classification_input(user, body.version_id)
    class_count = len({row["label"] for row in rows})
    test_count = math.ceil(len(rows) * body.test_size)
    if test_count < class_count or len(rows) - test_count < class_count:
        raise HTTPException(status_code=409, detail="当前样本规模无法进行分层拆分，请调整测试比例。")
    job_id = uuid.uuid4().hex
    path = _jobs_root(user) / job_id
    path.mkdir(parents=True, exist_ok=False)
    (path / "input.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    state = {"experiment_id":job_id, "version_id":body.version_id, "dataset_id":version.get("dataset_id"),
             "status":"pending", "created_at":data._now(), "started_at":None, "ended_at":None, "error":None,
             "seed":body.seed, "test_size":body.test_size, "sample_count":len(rows), "input_sha256":sha256_file(path / "input.jsonl")}
    data._atomic_json(path / "state.json", state)
    with _lock: _active.add(job_id)
    _pool.submit(_worker, path, state)
    return _safe_state(path, state)


@router.get("/experiments")
def list_experiments(user: User = Depends(require_operator)) -> dict[str, Any]:
    results = []
    for path in _jobs_root(user).glob("*/state.json"):
        try:
            folder, state = _read_state(user, path.parent.name)
            results.append(_safe_state(folder, state))
        except HTTPException: continue
    return {"items":sorted(results, key=lambda item:item.get("created_at") or "", reverse=True)}


@router.get("/experiments/{job_id}")
def get_experiment(job_id: str, user: User = Depends(require_operator)) -> dict[str, Any]:
    path, state = _read_state(user, job_id)
    return _safe_state(path, state)


@router.get("/experiments/{job_id}/files/{filename}")
def download(job_id: str, filename: str, user: User = Depends(require_operator)) -> FileResponse:
    path, state = _read_state(user, job_id)
    if state.get("status") != "completed" or filename not in ALLOWED or not (path / filename).is_file():
        raise HTTPException(status_code=404, detail="实验文件不存在。")
    return FileResponse(path / filename, filename=filename)
