"""通过平台后端启动模块4任务，沿用平台登录与角色校验。"""
import csv
import json
import os
import hashlib
import subprocess
import sys
import time
import shutil
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.auth import get_current_user
from app.models.user import User
from app.api import preproject_data as preproject
from data_pipeline.pipeline import _write_jsonl, sha256_file
from app.services.module4 import PROJECT_ROOT, TASKS, TRAINING_PYTHON, artifact_status, build_action_command, dataset_selection, available_evaluation_models, configured_evaluation_models, evaluation_preflight, local_model_status


def require_operator(user: User = Depends(get_current_user)) -> User:
    if user.user_type not in {"buyer", "admin"}:
        raise HTTPException(status_code=403, detail="当前角色无权运行模型验证任务")
    return user


def _resolve_model(value: Any, user: User) -> str:
    model = str(value or "")
    if not model.startswith("managed:"):
        return model
    model_id = model.removeprefix("managed:")
    item = next((entry for entry in preproject._model_resources(user) if entry.get("id") == model_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="模型资源不存在或不属于当前用户。")
    ready, message = local_model_status(item.get("path"))
    if not ready:
        raise HTTPException(status_code=409, detail=message)
    return str(item["path"])


router = APIRouter(dependencies=[Depends(require_operator)])


def training_environment_status(training_python: str | None = None) -> dict[str, Any] | None:
    """Return a safe, concise view of the last training-environment check."""
    report_path = PROJECT_ROOT / "experiments" / "module4" / "environment_report.json"
    if not report_path.is_file():
        if training_python and not os.path.isfile(training_python):
            return {"checked": False, "training_ready": False, "interpreter_exists": False,
                    "message": "所选训练 Python 不存在，请选择有效的独立训练环境。"}
        return None
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"checked": False, "training_ready": False, "message": "环境检查报告无法读取，请重新检查。"}

    python_info = report.get("python") if isinstance(report.get("python"), dict) else {}
    packages = report.get("packages") if isinstance(report.get("packages"), dict) else {}
    required = ("torch", "transformers", "datasets", "peft", "llamafactory")
    missing = [name for name in required if not (packages.get(name) or {}).get("available")]
    commands = report.get("commands") if isinstance(report.get("commands"), dict) else {}
    cli_available = bool(commands.get("llamafactory-cli"))
    reported_python = str(python_info.get("executable") or "")
    requested_python = str(training_python or TRAINING_PYTHON)
    interpreter_exists = os.path.isfile(requested_python)
    runtime_matches = bool(reported_python) and os.path.normcase(os.path.abspath(reported_python)) == os.path.normcase(os.path.abspath(requested_python))
    cuda = report.get("cuda") if isinstance(report.get("cuda"), dict) else {}
    report_current = time.time() - report_path.stat().st_mtime <= 3600
    ready = interpreter_exists and runtime_matches and report_current and not missing and cli_available and bool(cuda.get("available"))
    if not interpreter_exists:
        message = "所选训练 Python 不存在，请选择有效的独立训练环境。"
    elif not runtime_matches:
        message = "检查报告对应的 Python 与当前训练环境不同，请重新检查。"
    elif missing:
        message = "训练环境缺少必需依赖：" + ", ".join(missing)
    elif not cli_available:
        message = "未找到 llamafactory-cli，暂不能开始训练。"
    elif not cuda.get("available"):
        message = "训练环境的 PyTorch 无法使用 CUDA，请检查驱动、PyTorch CUDA 版本及运行时。"
    elif not report_current:
        message = "训练环境检查已过期，请重新检查后再启动。"
    else:
        message = "训练依赖检查通过。"

    nvidia_smi = report.get("nvidia_smi") if isinstance(report.get("nvidia_smi"), dict) else {}
    return {
        "checked": True,
        "checked_at": report_path.stat().st_mtime,
        "report_current": report_current,
        "python_version": python_info.get("version"),
        "interpreter_matches": runtime_matches,
        "interpreter_exists": interpreter_exists,
        "training_ready": ready,
        "missing_packages": missing,
        "package_versions": {
            name: (packages.get(name) or {}).get("version")
            for name in required
            if (packages.get(name) or {}).get("available")
        },
        "training_cli_available": cli_available,
        "cuda_available": bool(cuda.get("available")),
        "cuda_state": cuda.get("state") or ("not_checked_without_torch" if "torch" in missing else "available" if cuda.get("available") else "unavailable"),
        "torch_cuda_version": cuda.get("torch_cuda_version"),
        "driver_detected": bool(nvidia_smi.get("gpus")),
        "gpus": nvidia_smi.get("gpus", []),
        "message": message,
    }


class RunRequest(BaseModel):
    action: str = Field(min_length=1, max_length=64)
    config: dict[str, Any] = Field(default_factory=dict)


class CandidateConfigRequest(BaseModel):
    version_id: str = Field(min_length=1, max_length=100)
    base_model: str = Field(min_length=1, max_length=500)
    template: str = Field(default="qwen", min_length=1, max_length=80)
    epochs: float = Field(default=1, gt=0, le=100)
    precision: str = Field(default="bf16", pattern="^(bf16|fp16)$")
    seed: int = Field(default=42, ge=0, le=2147483647)


def _candidate_version(user: User, version_id: str) -> tuple[dict[str, Any], Path, list[dict[str, Any]]]:
    version = preproject._read_json(preproject._version_record_path(user, version_id))
    if version.get("version_type") not in {"processed", "reviewed_processed"}:
        raise HTTPException(status_code=409, detail="请选择经过质量准入的处理版本。")
    task = preproject._get_task(user, str(version.get("task_id") or ""))
    if task.get("status") != "completed":
        raise HTTPException(status_code=409, detail="处理任务尚未完成。")
    state_path = Path(task["task_dir"]) / "review_state.json"
    state = preproject._read_json(state_path) if state_path.is_file() else {}
    if version.get("version_type") == "reviewed_processed" and state.get("rebuild_status") == "pending":
        raise HTTPException(status_code=409, detail="复核版本仍在等待复检，请先恢复复检。")
    raw_path = version.get("qualified_file_path") if version.get("version_type") == "processed" else version.get("processed_path")
    if not raw_path:
        raise HTTPException(status_code=409, detail="合格候选文件不存在，请重新处理数据。")
    path = Path(raw_path).resolve()
    if not path.is_relative_to(preproject._user_root(user).resolve()) or not path.is_file():
        raise HTTPException(status_code=404, detail="当前用户的合格候选文件不存在。")
    if version.get("version_type") == "processed":
        manifest = preproject._read_json(Path(task["task_dir"]) / "output" / "dataset_manifest.json")
        expected = (manifest.get("artifacts", {}).get("qualified.jsonl") or {}).get("sha256")
    else:
        expected = version.get("processed_sha256")
    if not expected or sha256_file(path) != expected:
        raise HTTPException(status_code=409, detail="合格候选文件哈希不匹配，请重新处理。")
    parsed_rows, issues, count, _errors = preproject._read_local_source(path)
    if issues or len(parsed_rows) != count:
        raise HTTPException(status_code=409, detail="候选池包含无法解析的记录。")
    rows = [row for _line, row in parsed_rows]
    if sha256_file(path) != expected:
        raise HTTPException(status_code=409, detail="候选文件读取期间发生变化，请重新处理。")
    ids = [str(row.get("sample_id") or "") for row in rows]
    if not rows or any(not sample_id for sample_id in ids) or len(set(ids)) != len(ids) or any(row.get("processing_status") != "keep" or not str(row.get("instruction") or "").strip() or not str(row.get("output") or "").strip() for row in rows):
        raise HTTPException(status_code=409, detail="候选池为空或包含未通过准入的记录。")
    if any(row.get("task_type") == "text_document" for row in rows):
        raise HTTPException(status_code=409, detail="普通文本可完成治理，但不能直接作为问答微调数据；请先构建适合训练的问答版本。")
    return version, path, rows


@router.get("/candidate-versions")
def candidate_versions(user: User = Depends(require_operator)) -> dict[str, Any]:
    root = preproject._user_root(user)
    result = []
    for path in root.glob("tasks/*/versions/*.json"):
        version = preproject._read_json(path)
        if version.get("version_type") not in {"processed", "reviewed_processed"}: continue
        try:
            version, _data, rows = _candidate_version(user, str(version.get("version_id", "")))
        except HTTPException: continue
        result.append({"version_id": version["version_id"], "dataset_id": version.get("dataset_id"),
                       "source_id": version.get("source_id"), "task_id": version.get("task_id"),
                       "sample_count": len(rows), "authorization_status": version.get("authorization_status", "unverified"),
                       "license_verification_status": version.get("license_verification_status", "unverified"),
                       "revision_verification_status": version.get("revision_verification_status", "unverified"),
                       "release_eligible": bool((version.get("quality_gate") or {}).get("release_eligible"))})
    return {"items": result}


@router.post("/prepare-candidate-config")
def prepare_candidate_config(body: CandidateConfigRequest, user: User = Depends(require_operator)) -> dict[str, Any]:
    body = body.model_copy(update={"base_model": _resolve_model(body.base_model, user)})
    version, source_path, rows = _candidate_version(user, body.version_id)
    source_sha = sha256_file(source_path)
    material = json.dumps({**body.model_dump(), "source_sha256": source_sha}, sort_keys=True, ensure_ascii=False)
    config_id = hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]
    root = preproject._user_root(user) / "module4_candidates" / config_id
    data_dir, config_dir = root / "data", root / "config"
    data_dir.mkdir(parents=True, exist_ok=True)
    label = f"{len(rows)//1000}k" if len(rows) % 1000 == 0 else str(len(rows))
    normalized = [{"id": str(row["sample_id"]), "instruction": row["instruction"], "input": row.get("input", ""),
                   "output": row["output"], "system": row.get("system", "")} for row in rows]
    _write_jsonl(data_dir / f"raw_{label}.jsonl", normalized)
    preproject._atomic_json(data_dir / f"dataset_manifest_{label}.json", {"sample_count_per_variant": len(rows),
        "variants": {"raw": {"count": len(rows)}}, "pending_variants": {"other": "仅接入合格候选版本，未构造其他对照组。"}})
    command = [sys.executable, str(PROJECT_ROOT / "scripts/module4/03_prepare_llamafactory.py"),
               "--model", body.base_model, "--template", body.template, "--n", str(len(rows)), "--seed", str(body.seed),
               "--precision", body.precision, "--epochs", str(body.epochs), "--data-dir", str(data_dir),
               "--out-dir", str(config_dir), "--experiment-dir", str(root / "experiment")]
    try:
        result = subprocess.run(command, cwd=PROJECT_ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60, check=False)
    except (OSError, subprocess.SubprocessError) as exc:
        raise HTTPException(status_code=500, detail=f"训练配置生成失败：{type(exc).__name__}") from None
    if result.returncode or not (config_dir / "training_manifest.json").is_file():
        raise HTTPException(status_code=500, detail="训练配置生成失败，请检查输入与参数。")
    preproject._atomic_json(root / "link.json", {"version_id": body.version_id, "source_sha256": source_sha,
        "config_id": config_id, "sample_count": len(rows), "base_model": body.base_model, "config": body.model_dump(),
        "config_sha256": sha256_file(config_dir / "raw_lora.yaml"),
        "data_sha256": sha256_file(config_dir / "llamafactory_data" / f"raw_{label}.jsonl")})
    return {"config_id": config_id, "version_id": body.version_id, "sample_count": len(rows),
            "quality_status": "candidate", "release_eligible": bool((version.get("quality_gate") or {}).get("release_eligible")),
            "message": "已生成隔离的候选数据训练配置；不代表训练已运行，来源与许可仍须核验。"}


def _linked_candidate_config(user: User, config: dict[str, Any]) -> Path:
    config_id = str(config.get("candidate_config_id") or "")
    if not __import__("re").fullmatch(r"[0-9a-f]{24}", config_id):
        raise HTTPException(status_code=409, detail="请先为所选合格版本生成训练配置。")
    root = preproject._user_root(user) / "module4_candidates" / config_id
    metadata_path = root / "link.json"
    if not metadata_path.is_file(): raise HTTPException(status_code=409, detail="训练配置不存在，请重新生成。")
    link = preproject._read_json(metadata_path)
    if link.get("version_id") != config.get("data_version_id") or link.get("base_model") != config.get("base_model"):
        raise HTTPException(status_code=409, detail="所选数据版本或模型已变化，请重新生成训练配置。")
    linked = link.get("config") or {}
    try:
        same_parameters = (str(linked.get("template")) == str(config.get("template", "qwen"))
                           and str(linked.get("precision")) == str(config.get("precision", "bf16"))
                           and float(linked.get("epochs")) == float(config.get("epochs", 1))
                           and int(linked.get("seed")) == int(config.get("seed", 42)))
    except (ValueError, TypeError): same_parameters = False
    if not same_parameters:
        raise HTTPException(status_code=409, detail="训练参数已变化，请重新生成训练配置。")
    _version, source, rows = _candidate_version(user, str(link["version_id"]))
    label = f"{len(rows)//1000}k" if len(rows) % 1000 == 0 else str(len(rows))
    config_dir = root / "config"; yaml_path = config_dir / "raw_lora.yaml"
    registered = config_dir / "llamafactory_data" / f"raw_{label}.jsonl"
    if (not yaml_path.is_file() or not registered.is_file() or sha256_file(source) != link.get("source_sha256")
        or sha256_file(yaml_path) != link.get("config_sha256") or sha256_file(registered) != link.get("data_sha256")):
        raise HTTPException(status_code=409, detail="候选数据或训练配置已变化，请重新生成配置。")
    return config_dir


def _global_training_config_ready(config: dict[str, Any]) -> bool:
    manifest_path = PROJECT_ROOT / "configs/module4/training_manifest.json"
    if not manifest_path.is_file(): return False
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("model") != config.get("base_model") or int(manifest.get("sample_count", -1)) != int(config.get("sample_count", 100)):
            return False
        info_path = Path(manifest["dataset_info"]).resolve()
        if not info_path.is_relative_to(PROJECT_ROOT.resolve()) or not info_path.is_file(): return False
        info = json.loads(info_path.read_text(encoding="utf-8"))
        configs = manifest.get("train_configs") or {}
        return bool(info and configs) and all((info_path.parent / value["file_name"]).resolve().is_relative_to(info_path.parent.resolve()) and (info_path.parent / value["file_name"]).is_file() for value in info.values()) and all(Path(value).resolve().is_relative_to(PROJECT_ROOT.resolve()) and Path(value).is_file() for value in configs.values())
    except (ValueError, KeyError, TypeError, OSError): return False


@router.post("/preflight")
def preflight(body: RunRequest, user: User = Depends(require_operator)) -> dict[str, Any]:
    if body.config.get("base_model"):
        body.config["base_model"] = _resolve_model(body.config["base_model"], user)
    training = training_environment_status(str(body.config.get("training_python") or "") or None)
    model_ok, model_message = local_model_status(body.config.get("base_model"))
    data_ready = False; config_ready = False; authorization_ready = False
    data_message = "请先在数据处理模块选择并处理数据，或选择一个合格候选版本。"
    version_id = str(body.config.get("data_version_id") or "")
    if version_id:
        try:
            _version, _path, rows = _candidate_version(user, version_id)
            data_ready = bool(rows); data_message = f"合格候选数据已就绪：{len(rows)} 条；来源与许可状态独立核验。"
            authorization_ready = _version.get("authorization_status") == "authorized" and _version.get("license_verification_status") == "verified"
        except HTTPException as exc: data_message = str(exc.detail)
        try:
            _linked_candidate_config(user, body.config); config_ready = True
        except HTTPException: pass
    else:
        config_ready = _global_training_config_ready(body.config)
        data_ready = bool(dataset_selection(int(body.config.get("sample_count", 100)))[0]) and config_ready
        if data_ready: data_message = "已找到现有训练配置；请确认来源。"
    checks = [{"key": "environment", "ready": bool(training and training.get("training_ready")),
               "message": training.get("message", "请先检查训练环境。") if training else "尚未检查训练环境。"},
              {"key": "model", "ready": model_ok, "message": model_message},
              {"key": "data", "ready": data_ready, "message": data_message},
              {"key": "config", "ready": config_ready, "message": "训练配置已生成" if config_ready else "训练配置不存在或参数已变更，请重新生成。"},
              {"key": "authorization", "ready": authorization_ready, "message": "数据使用授权已核验" if authorization_ready else "数据训练使用授权或许可尚未核验，不能启动训练。"},
              {"key": "storage", "ready": shutil.disk_usage(PROJECT_ROOT).free >= 1024 ** 3, "message": "已检查至少 1 GiB 可用空间；实际需求取决于模型和配置。" if shutil.disk_usage(PROJECT_ROOT).free >= 1024 ** 3 else "可用存储空间不足 1 GiB。"}]
    evaluation = evaluation_preflight(body.config)
    evaluation["dry_run_ready"] = TASKS.dry_run_matches(body.config)
    evaluation["score_ready"] = _evaluation_predictions_exist(body.config)
    return {"evaluation": evaluation, "training_environment": training,
            "base_model": {"ready": model_ok, "message": model_message}, "training": {"ready": all(item["ready"] for item in checks), "checks": checks}}


def _evaluation_predictions_exist(config: dict[str, Any]) -> bool:
    path = PROJECT_ROOT / "experiments/module4/evaluation/eval_manifest.json"
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
        requested = str(config.get("eval_model", "all"))
        names = list(manifest.get("commands", {})) if requested == "all" else [requested]
        run_root = Path(manifest["run_dir"])
        return bool(names) and all((run_root / name).is_dir() and any((run_root / name).glob("*/predictions/**/*.json")) for name in names)
    except (OSError, ValueError, KeyError, TypeError): return False


@router.get("/status")
def get_status():
    active, pending = dataset_selection()
    artifacts = artifact_status()
    progress, parameters = TASKS.progress(artifacts, configured_evaluation_models())
    return {"task": TASKS.snapshot(), "artifacts": artifacts, "progress": progress,
            "progress_parameters": parameters, "available_variants": active, "pending_variants": pending,
            "available_models": available_evaluation_models(),
            "training_environment": training_environment_status()}


@router.post("/run")
def run_task(body: RunRequest, user: User = Depends(require_operator)):
    try:
        if body.action == "fix_eval_dependencies" and body.config.get("confirm_install") is not True:
            raise HTTPException(status_code=400, detail="安装依赖前需要明确确认。")
        if body.config.get("base_model"):
            body.config["base_model"] = _resolve_model(body.config["base_model"], user)
        if body.action in {"eval_dry", "eval_run", "eval_score"}:
            checked = evaluation_preflight(body.config)
            failures = [item["message"] for item in checked["checks"] if not item["ready"]]
            if failures:
                raise HTTPException(status_code=409, detail={"message": "评测前置条件尚未满足", "reasons": failures})
            if body.action == "eval_run" and not TASKS.dry_run_matches(body.config):
                raise HTTPException(status_code=409, detail={"message": "请先完成当前配置的评测试运行", "reasons": ["正式评测前必须用相同清单和参数完成试运行。"]})
            if body.action == "eval_score":
                if not _evaluation_predictions_exist(body.config):
                    raise HTTPException(status_code=409, detail={"message": "尚无可复用的预测结果", "reasons": ["请先完成所选模型的正式评测。"]})
        linked_dir = None
        if body.action in {"train", "merge"}:
            training = training_environment_status(str(body.config.get("training_python") or "") or None)
            model_ok, model_message = local_model_status(body.config.get("base_model"))
            reasons = []
            if not training or not training.get("training_ready"): reasons.append(training.get("message") if training else "尚未检查训练环境。")
            if not model_ok: reasons.append(model_message)
            if shutil.disk_usage(PROJECT_ROOT).free < 1024 ** 3: reasons.append("可用存储空间不足 1 GiB。")
            if body.config.get("data_version_id"):
                linked_dir = _linked_candidate_config(user, body.config)
                version, _path, _rows = _candidate_version(user, str(body.config["data_version_id"]))
                if version.get("authorization_status") != "authorized" or version.get("license_verification_status") != "verified":
                    reasons.append("数据训练使用授权或许可尚未核验，不能启动训练。")
                if body.action == "merge":
                    audit_path = linked_dir.parent / "experiment/checkpoints/raw/training_audit.json"
                    if not audit_path.is_file() or not preproject._read_json(audit_path).get("has_update"):
                        reasons.append("尚无完成训练且通过检查的适配器，不能合并。")
            else:
                if not _global_training_config_ready(body.config): reasons.append("训练配置或数据不存在，或与当前参数不一致，请重新生成。")
                reasons.append("旧式路径数据未关联可核验的使用授权，请选择已授权的数据版本。")
            if reasons: raise HTTPException(status_code=409, detail={"message": "训练条件尚未满足", "reasons": reasons})
        if linked_dir is not None:
            python_path = str(body.config.get("training_python") or TRAINING_PYTHON)
            command = [python_path, "-u", str(PROJECT_ROOT / "scripts/module4/07_run_llamafactory.py"), body.action,
                       "--variants", "raw", "--config-dir", str(linked_dir)]
            label = "候选数据训练" if body.action == "train" else "候选模型合并"
        else:
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
