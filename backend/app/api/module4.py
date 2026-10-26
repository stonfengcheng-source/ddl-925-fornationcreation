"""通过平台后端启动模块4任务，沿用平台登录与角色校验。"""
import csv
import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.auth import get_current_user
from app.models.user import User
from app.services.module4 import PROJECT_ROOT, TASKS, artifact_status, build_action_command, dataset_selection, available_evaluation_models, configured_evaluation_models


def require_operator(user: User = Depends(get_current_user)) -> User:
    if user.user_type not in {"buyer", "admin"}:
        raise HTTPException(status_code=403, detail="当前角色无权运行模型验证任务")
    return user


router = APIRouter(dependencies=[Depends(require_operator)])


class RunRequest(BaseModel):
    action: str = Field(min_length=1, max_length=64)
    config: dict[str, Any] = Field(default_factory=dict)


@router.get("/status")
def get_status():
    active, pending = dataset_selection()
    artifacts = artifact_status()
    progress, parameters = TASKS.progress(artifacts, configured_evaluation_models())
    return {"task": TASKS.snapshot(), "artifacts": artifacts, "progress": progress,
            "progress_parameters": parameters, "available_variants": active, "pending_variants": pending,
            "available_models": available_evaluation_models()}


@router.post("/run")
def run_task(body: RunRequest):
    try:
        command, label = build_action_command(body.action, body.config)
        TASKS.start(command, label, body.action, body.config)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"ok": True, "message": f"已启动：{label}"}


@router.post("/stop")
def stop_task():
    stopped = TASKS.stop()
    return {"ok": True, "message": "已发送停止请求" if stopped else "当前没有运行中的任务"}


@router.post("/clear")
def clear_logs():
    TASKS.clear()
    return {"ok": True}


@router.get("/results")
def get_results():
    path = PROJECT_ROOT / "experiments" / "module4" / "results" / "summary.csv"
    if not path.is_file():
        return {"rows": []}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    metadata_path = path.with_suffix(".metadata.json")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.is_file() else {}
    manifest_path = PROJECT_ROOT / "experiments" / "module4" / "evaluation" / "eval_manifest.json"
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {"rows": [], "metadata": metadata}
        if manifest.get("protocol_version", 0) < 3 or any(
            metadata.get(key) != manifest.get(key) for key in ("protocol_version", "max_out_len", "run_dir")
        ):
            return {"rows": [], "metadata": metadata}
    active, pending = dataset_selection()
    if pending:
        rows = [row for row in rows if row.get("model") in {"base", *active}]
    return {"rows": rows, "metadata": metadata, "pending_variants": pending}
