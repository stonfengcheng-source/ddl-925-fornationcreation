"""预立项数据源、处理任务及安全下载 API。"""
from __future__ import annotations

import copy
import asyncio
import io
from contextlib import contextmanager
import hashlib
import json
import os
import re
import shutil
import sys
import threading
import time
import uuid
from collections import Counter
from typing import Literal
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from data_pipeline.cleaning import clean_record
from data_pipeline.deduplication import deduplicate
from data_pipeline.pipeline import (
    PipelineCancelled, _apply_license_boundary, _build_quality_report, _load_and_verify_source_manifest, _read_local_source, run_pipeline, sha256_file,
)
from data_pipeline.privacy import inspect_and_mask
from data_pipeline.quality import calculate_quality
from data_pipeline.schema import _stable_sample_id, normalize_record, public_record
from data_pipeline.governance_outcome import summarize_governance
from data_pipeline.source import DatasetViewerClient
from app.api.auth import get_current_user
from app.core.database import SessionLocal, get_db
from app.core.config import APP_ENV, PASSWORDLESS_AUTH
from app.models.dataset import Dataset
from app.models.user import User

router = APIRouter()
DATA_ROOT = Path(os.getenv("PREPROJECT_DATA_DIR", str(PROJECT_ROOT / "backend" / "data" / "preproject"))).resolve()
MAX_UPLOAD_BYTES = 100 * 1024 * 1024
MAX_SOURCE_ROWS = 100_000
ALLOWED_SUFFIXES = {".txt", ".jsonl", ".json", ".parquet", ".pq"}
DOWNLOADABLE = {
    "processed.jsonl", "qualified.jsonl", "processing_actions.jsonl", "statistics.json", "quality_metrics.json", "quality_report.md",
    "dataset_manifest.json", "dedup_report.json", "privacy_report.json", "review_queue.jsonl",
    "reviewed_all.jsonl", "reviewed_processed.jsonl", "reviewed_statistics.json", "reviewed_quality_metrics.json",
    "reviewed_quality_report.md", "reviewed_manifest.json",
}
_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="preproject-data")
_lock = threading.RLock()
_tasks: dict[str, dict[str, Any]] = {}
_cancel_events: dict[str, threading.Event] = {}
_fetch_jobs: dict[str, dict[str, Any]] = {}


def _public(value: Any) -> Any:
    """Remove storage implementation details from API responses, including nested reports."""
    if isinstance(value, dict):
        return {key: _public(item) for key, item in value.items()
                if key not in {"owner_key", "task_dir", "path", "stored_filename", "file_mtime_ns", "sample_ids", "source_record_ids"}
                and not key.endswith("_path")}
    if isinstance(value, list):
        return [_public(item) for item in value]
    if isinstance(value, str):
        if value.startswith("/") or re.match(r"^(?:[A-Za-z]:[\\/]|file://)", value, re.IGNORECASE):
            return "[本地路径]"
        value = re.sub(r"(?<![A-Za-z0-9])[A-Za-z]:[\\/][^'\"\r\n]+", "[本地路径]", value)
        return re.sub(r"(?<=['\"])/(?:[^\s'\"]+/)*[^\s'\"]+", "[本地路径]", value)
    return value


@contextmanager
def _review_lock(task_dir: Path):
    """Cross-process task lock; operating system releases it if a worker exits."""
    lock_path = task_dir / "review.lock"
    with lock_path.open("a+b") as handle:
        handle.seek(0, os.SEEK_END)
        if handle.tell() == 0:
            handle.write(b"0"); handle.flush()
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise HTTPException(status_code=409, detail="该任务正在复核，请刷新后重试。") from None
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == "nt":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _owner_key(user: User) -> str:
    return hashlib.sha256(str(user.id).encode("utf-8")).hexdigest()[:24]


def _require_operator(user: User = Depends(get_current_user)) -> User:
    if getattr(user, "user_type", None) not in {"buyer", "admin"}:
        raise HTTPException(status_code=403, detail="当前角色无权管理预立项数据")
    return user


def _user_root(user: User) -> Path:
    return DATA_ROOT / "users" / _owner_key(user)


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    try:
        for attempt in range(8):
            try:
                temporary.replace(path)
                break
            except PermissionError:
                if attempt == 7: raise
                time.sleep(0.025 * (attempt + 1))
    finally:
        temporary.unlink(missing_ok=True)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=500, detail=f"任务或数据源记录不可读取：{type(exc).__name__}") from None
    if not isinstance(value, dict):
        raise HTTPException(status_code=500, detail="任务或数据源记录格式错误")
    return value


def _source_path(user: User, source_id: str) -> Path:
    if not re.fullmatch(r"[0-9a-f]{32}", source_id):
        raise HTTPException(status_code=404, detail="数据源不存在")
    directory = _user_root(user) / "sources" / source_id
    manifest_path = directory / "source_manifest.json"
    if not manifest_path.is_file():
        raise HTTPException(status_code=404, detail="数据源不存在")
    return directory


def _load_source(user: User, source_id: str) -> tuple[dict[str, Any], Path]:
    directory = _source_path(user, source_id)
    manifest = _read_json(directory / "source_manifest.json")
    input_path = directory / str(manifest.get("stored_filename", ""))
    if not input_path.is_file() or input_path.parent.resolve() != directory.resolve():
        raise HTTPException(status_code=410, detail="数据源文件已不存在")
    return manifest, input_path


def _task_path(user: User, task_id: str) -> Path:
    if not re.fullmatch(r"[0-9a-f]{32}", task_id):
        raise HTTPException(status_code=404, detail="处理任务不存在")
    path = _user_root(user) / "tasks" / task_id / "task.json"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="处理任务不存在")
    return path


def _get_task(user: User, task_id: str) -> dict[str, Any]:
    with _lock:
        task = _tasks.get(task_id)
    if task is None or task.get("status") not in {"pending", "running"}:
        with _lock:
            task = _read_json(_task_path(user, task_id))
        if task.get("status") in {"pending", "running"}:
            task.update(status="failed", current_step="interrupted", ended_at=_now(),
                        error="后端进程已重启，任务未自动续跑；请检查数据后重试。")
            _store_task(task)
    if task.get("owner_key") != _owner_key(user):
        raise HTTPException(status_code=404, detail="处理任务不存在")
    return task


def _store_task(task: dict[str, Any]) -> None:
    with _lock:
        _tasks[task["task_id"]] = task
        directory = Path(task["task_dir"])
        _atomic_json(directory / "task.json", task)


def _load_pipeline_config() -> dict[str, Any]:
    return json.loads((PROJECT_ROOT / "configs" / "preproject_pipeline.json").read_text(encoding="utf-8"))


def _jsonl_rows(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as stream:
        for line in stream:
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                rows.append(value)
    return rows


def _safe_normalized_sample(user: User, task: dict[str, Any], sample_id: str,
                            source_rows: list[tuple[int, dict[str, Any]]] | None = None) -> dict[str, Any] | None:
    """Load one source row, normalize it, clean it, and mask PII before preview/review."""
    source_manifest, input_path = _load_source(user, str(task["source_id"]))
    rows = source_rows
    if rows is None:
        rows, _issues, _nonblank, _errors = _read_local_source(input_path)
    source_row = None
    for line_number, row in rows:
        row_key = row.get("id", row.get("hf_row_idx", row.get("row_idx", line_number)))
        derived_id = str(row.get("sample_id") or _stable_sample_id(
            str(source_manifest.get("dataset_id", "local-unknown")), str(source_manifest.get("revision", "unversioned")),
            str(source_manifest.get("split", "local")), str(row_key)))
        if derived_id == sample_id:
            source_row = row
            break
    if source_row is None:
        return None
    config = _load_pipeline_config()
    task_parameters = task.get("parameters", {})
    defaults = {
        "dataset_id": source_manifest.get("dataset_id"),
        "source_id": f"local-upload:{source_manifest.get('source_id')}",
        "source_url": source_manifest.get("source_url", ""),
        "license": source_manifest.get("license", "unknown"),
        "revision": source_manifest.get("revision", "unknown"),
        "split": source_manifest.get("split", "local"),
        "data_subset_id": task_parameters.get("version_name", "reviewed"),
        "version_id": source_manifest.get("version_id", "raw"),
    }
    record = normalize_record(source_row, defaults=defaults, line_number=1)
    if task_parameters.get("cleaning_enabled", True):
        clean_record(record, config.get("engineering_screens", {}))
    else:
        record["status_history"].append({"stage": "cleaning", "status": "skipped_by_config"})
    inspect_and_mask(record, config.get("privacy", {}))
    return record


def _version_record_path(user: User, version_id: str) -> Path:
    if not re.fullmatch(r"(?:raw|processed|reviewed|candidate)_[0-9a-f]{20,64}", version_id):
        raise HTTPException(status_code=404, detail="数据版本不存在")
    root = _user_root(user)
    matches = list(root.glob(f"sources/*/versions/{version_id}.json")) + list(root.glob(f"tasks/*/versions/{version_id}.json"))
    if not matches:
        raise HTTPException(status_code=404, detail="数据版本不存在")
    return matches[0]


def _unchanged_since_hash(path: Path, manifest: dict[str, Any]) -> bool | None:
    recorded_size = manifest.get("file_size_bytes")
    recorded_mtime = manifest.get("file_mtime_ns")
    if recorded_size is None or recorded_mtime is None:
        return None
    stat = path.stat()
    return stat.st_size == int(recorded_size) and stat.st_mtime_ns == int(recorded_mtime)


def _rebuild_reviewed_version(user: User, task: dict[str, Any], states: dict[str, Any]) -> dict[str, Any]:
    """Re-run the source pipeline with persisted reviewer decisions into a separate immutable version."""
    source_manifest, input_path = _load_source(user, str(task["source_id"]))
    config = _load_pipeline_config()
    parameters = task.get("parameters", {})
    config["source"] = {
        "enabled": False, "dataset_id": source_manifest["dataset_id"],
        "source_id": f"local-upload:{source_manifest['source_id']}",
        "source_url": source_manifest.get("source_url", ""), "license": source_manifest.get("license", "unknown"),
        "revision": source_manifest.get("revision", "unknown"), "split": source_manifest.get("split", "local"),
    }
    config["data_subset_id"] = parameters.get("version_name", "reviewed")
    config["cleaning_enabled"] = bool(parameters.get("cleaning_enabled", True))
    config["deduplication"]["near_duplicate_enabled"] = bool(parameters.get("near_duplicate_enabled", True))
    config["deduplication"]["near_duplicate_hamming_distance"] = int(parameters.get("near_duplicate_hamming_distance", 3))
    config["privacy_enabled"] = True
    if source_manifest.get("source_type") == "test_fixture":
        config["license_policy"]["licenses_allowed_for_local_processing"].append("test-only")

    rows, parse_issues, nonblank, parse_errors = _read_local_source(input_path)
    records: list[dict[str, Any]] = []
    state_by_sample = states.get("items", {}) if isinstance(states.get("items"), dict) else {}
    for line_number, source_row in rows:
        record = normalize_record(source_row, defaults={**config["source"], "data_subset_id": config["data_subset_id"]},
                                  line_number=line_number)
        state = state_by_sample.get(str(record.get("sample_id")), {})
        edits = state.get("edited_content") if isinstance(state, dict) else None
        if isinstance(edits, dict):
            for key in ("instruction", "input", "output", "system"):
                if key in edits:
                    record[key] = str(edits[key])
            record["status_history"].append({"stage": "human_edit", "status": "recheck"})
        _apply_license_boundary(record, config.get("license_policy", {}))
        if config["cleaning_enabled"] or isinstance(edits, dict):
            clean_record(record, config.get("engineering_screens", {}))
        else:
            record["status_history"].append({"stage": "cleaning", "status": "skipped_by_config"})
        records.append(record)

    dedup_report = deduplicate(records, config.get("deduplication", {}))
    for record in records:
        record["status_history"].append({"stage": "deduplication", "status": record["processing_status"]})
    detected: dict[str, int] = {}
    masked: dict[str, int] = {}
    residual: dict[str, int] = {}
    for record in records:
        hits, replacements, leftovers = inspect_and_mask(record, config.get("privacy", {}))
        for key, count in hits.items(): detected[key] = detected.get(key, 0) + count
        for key, count in replacements.items(): masked[key] = masked.get(key, 0) + count
        for key, count in leftovers.items(): residual[key] = residual.get(key, 0) + count
        record["content_hash"] = hashlib.sha256("\x1f".join(str(record.get(key, "") or "") for key in ("instruction", "input", "output")).encode("utf-8")).hexdigest()

    state_to_status = {"accept": "keep", "quarantine": "quarantine", "reject": "drop"}
    for record in records:
        state = state_by_sample.get(str(record.get("sample_id")))
        if not isinstance(state, dict):
            continue
        wanted = state_to_status.get(str(state.get("decision")))
        if wanted and wanted in {"keep", "review", "quarantine", "drop"}:
            if wanted == "keep" and record.get("processing_status") == "review":
                record["processing_status"] = "keep"
                record["processing_reasons"].append("human_review_accepted")
            elif wanted == "review" and record.get("processing_status") not in {"drop", "quarantine"}:
                record["processing_status"] = "review"
                record["processing_reasons"].append("edited_content_requires_full_recheck")
            elif wanted in {"quarantine", "drop"}:
                record["processing_status"] = wanted
            if isinstance(record.get("privacy_audit"), dict):
                record["privacy_audit"]["status"] = record["processing_status"]
            record["status_history"].append({"stage": "human_review", "status": record["processing_status"]})

    privacy_report = {"detected_counts": detected, "masked_counts": masked, "residual_counts": residual,
                      "residual_scan_passed": not any(residual.values()), "patterns_version": "privacy-patterns-v1",
                      "plaintext_sensitive_values_logged": False}
    quality = calculate_quality(records, parse_error_count=parse_errors, nonblank_line_count=nonblank,
                                dedup_report=dedup_report, privacy_report=privacy_report,
                                config=config.get("quality", {}))
    status_counts: dict[str, int] = {}
    for record in records:
        status = str(record.get("processing_status", "quarantine"))
        status_counts[status] = status_counts.get(status, 0) + 1
    status_counts["quarantine"] = status_counts.get("quarantine", 0) + parse_errors
    eligible = [record for record in records if record.get("processing_status") == "keep"
                and isinstance(record.get("instruction"), str) and record["instruction"].strip()
                and isinstance(record.get("output"), str) and record["output"].strip()]
    eligible.sort(key=lambda record: str(record["sample_id"]))
    version_material = json.dumps({key: {"decision": value.get("decision"), "edited_content": value.get("edited_content")}
                                   for key, value in sorted(state_by_sample.items()) if isinstance(value, dict)},
                                  ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    version_id = "reviewed_" + hashlib.sha256(
        f"{source_manifest.get('file_sha256', '')}:{task.get('config_fingerprint', '')}:{version_material}".encode("utf-8")
    ).hexdigest()[:24]
    version_dir = Path(task["task_dir"]) / "versions" / version_id
    version_dir.mkdir(parents=True, exist_ok=True)
    output_path = version_dir / "reviewed_processed.jsonl"
    comparison_path = version_dir / "reviewed_all.jsonl"
    with comparison_path.open("w", encoding="utf-8", newline="\n") as stream:
        for record in sorted(records, key=lambda value: str(value.get("sample_id", ""))):
            stream.write(json.dumps(public_record(record), ensure_ascii=False, sort_keys=True) + "\n")
    temporary = output_path.with_suffix(".jsonl.tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as stream:
        for record in eligible:
            stream.write(json.dumps(public_record(record), ensure_ascii=False, sort_keys=True) + "\n")
    temporary.replace(output_path)
    output_stats = dict(task.get("statistics") or {})
    status_total = sum(status_counts.values())
    if status_total != nonblank:
        raise ValueError(f"复核版本样本状态不守恒：输入 {nonblank}，终态 {status_total}。")
    output_stats.update({"raw_sample_count": len(records), "parse_error_count": parse_errors,
                         "status_counts": dict(sorted(status_counts.items())), "review_count": status_counts.get("review", 0),
                         "quarantine_count": status_counts.get("quarantine", 0), "drop_count": status_counts.get("drop", 0),
                         "final_retained_count": len(eligible), "manual_review_decision_count": len(state_by_sample),
                         "status_count_total": status_total, "status_count_conserved": True,
                         "five_dimensions": quality["metrics"]})
    output_stats.update({"exact_duplicate_count":dedup_report.get("exact_duplicate_count", 0), "normalized_duplicate_count":dedup_report.get("normalized_duplicate_count", 0),
                         "near_duplicate_sample_count":dedup_report.get("near_duplicate_sample_count", 0),
                         "privacy_hit_count":sum(detected.values()), "privacy_masked_count":sum(masked.values()), "privacy_residual_count":sum(residual.values())})
    reviewed_stats_path = version_dir / "reviewed_statistics.json"
    _atomic_json(reviewed_stats_path, output_stats)
    reviewed_quality_path = version_dir / "reviewed_quality_metrics.json"
    _atomic_json(reviewed_quality_path, quality)
    reviewed_dedup_path = version_dir / "reviewed_dedup_report.json"
    _atomic_json(reviewed_dedup_path, dedup_report)
    reviewed_privacy_path = version_dir / "reviewed_privacy_report.json"
    _atomic_json(reviewed_privacy_path, privacy_report)
    gate = dict(task.get("gate") or {})
    report = _build_quality_report(source=source_manifest, statistics=output_stats, quality=quality,
                                   dedup=dedup_report, privacy=privacy_report,
                                   processing_flow=["原始数据重新读取", "人工复核决策应用", "清洗与去重重跑",
                                                    "脱敏与残留复检重跑", "五维质量重新计算", "复核版本导出"], gate=gate, records=records, review_state=states)
    report_path = version_dir / "reviewed_quality_report.md"
    report_path.write_text(report, encoding="utf-8")
    sample_ids_path = version_dir / "sample_ids.jsonl"
    sample_ids_path.write_text("".join(json.dumps(row["sample_id"], ensure_ascii=False) + "\n" for row in eligible), encoding="utf-8")
    manifest = {"manifest_version": 1, "version_id": version_id, "parent_version_id": task.get("version_id"),
                "version_type": "reviewed_processed", "source_id": task["source_id"], "task_id": task["task_id"],
                "sample_count": len(eligible), "sample_ids_path": str(sample_ids_path.resolve()),
                "raw_sha256": source_manifest.get("file_sha256"), "processed_sha256": sha256_file(output_path),
                "processed_path": str(output_path.resolve()),
                "comparison_file_path": str(comparison_path.resolve()),
                "statistics_path": str(reviewed_stats_path.resolve()), "quality_metrics_path": str(reviewed_quality_path.resolve()),
                "quality_report_path": str(report_path.resolve()), "status": "reviewed_candidate",
                "quality_gate": gate, "license": source_manifest.get("license", "unknown"),
                "license_verification_status": "verified" if source_manifest.get("license_verified") else "unverified",
                "revision": source_manifest.get("revision", "unknown"),
                "revision_verification_status": "verified" if source_manifest.get("revision_verified") else "unverified",
                "authorization_status": "unverified_or_not_authorized", "created_at": _now()}
    _atomic_json(Path(task["task_dir"]) / "versions" / f"{version_id}.json", manifest)
    task["reviewed_version_id"] = version_id
    _store_task(task)
    return manifest


class CreateTaskRequest(BaseModel):
    source_id: str = Field(min_length=32, max_length=32)
    template_id: Literal["education_qa", "general_text"] = "education_qa"
    cleaning_enabled: bool = True
    near_duplicate_enabled: bool = True
    near_duplicate_hamming_distance: int = Field(default=3, ge=0, le=64)
    near_duplicate_action: str = Field(default="review_only", pattern="^review_only$")
    privacy_enabled: bool = True
    version_name: str = Field(default="preproject-run", min_length=1, max_length=80)


class FetchRequest(BaseModel):
    count: Literal[200, 5000]


class ModelResourceRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    path: str = Field(min_length=1, max_length=1024)
    license_status: Literal["unverified", "user_attested"] = "unverified"


class ReviewRequest(BaseModel):
    sample_id: str = Field(min_length=1, max_length=160)
    decision: Literal["accept", "edit", "quarantine", "reject"]
    issue_type: str = Field(default="", max_length=160)
    edited_content: dict[str, str] | None = None
    notes: str = Field(default="", max_length=2000)
    expected_revision: int = Field(default=0, ge=0)


def _run_fetch(fetch_id: str, user_id: str, owner_key: str, count: int, source_id: str, directory: Path) -> None:
    with _lock:
        job = _fetch_jobs[fetch_id]
        job.update(status="running", started_at=_now(), current_step="official_metadata_and_license")
        _atomic_json(directory / "fetch_job.json", job)
    try:
        config_path = PROJECT_ROOT / "configs" / "preproject_pipeline.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        source = dict(config["source"])
        source["sample_count"] = count
        source["cache_dir"] = str(DATA_ROOT / "users" / owner_key / "cache")
        target = directory / ("educhat_raw_200.jsonl" if count == 200 else "educhat_raw_5k.jsonl")
        with _lock:
            job = _fetch_jobs[fetch_id]
            job.update(current_step="fetching_official_rows", total=count)
            _atomic_json(directory / "fetch_job.json", job)
        report = DatasetViewerClient(source, source["cache_dir"]).sample(source, target)
        raw_version_id = str(report.get("version_id") or f"raw_{str(report['file_sha256'])[:24]}")
        report.update({"source_id": source_id, "stored_filename": target.name, "file": target.name,
                       "source_type": "official_api", "version_id": raw_version_id,
                       "raw_file_path": str(target.resolve()), "created_at": _now(), "status": "imported",
                       "license_verification_status": "verified" if report.get("license_verified") else "unverified",
                       "revision_verification_status": "verified" if report.get("revision_verified") else "unverified"})
        manifest_path = directory / "source_manifest.json"
        _atomic_json(manifest_path, report)
        _atomic_json(directory / "versions" / f"{raw_version_id}.json", {
            "version_id": raw_version_id, "parent_version_id": None, "version_type": "raw",
            "source_id": source_id, "dataset_id": report.get("dataset_id"),
            "sample_count": report.get("sample_count"), "sample_ids_path": str((directory / "sample_ids.jsonl").resolve()),
            "raw_file_path": str(target.resolve()), "sha256": report.get("file_sha256"),
            "license": report.get("license", "unknown"),
            "license_verification_status": "verified" if report.get("license_verified") else "unverified",
            "revision": report.get("revision", "unknown"),
            "revision_verification_status": "verified" if report.get("revision_verified") else "unverified",
            "authorization_status": "authorized" if report.get("redistribution_authorized") else "unverified_or_not_authorized",
            "status": "imported", "created_at": report.get("acquired_at", _now()),
        })
        (directory / "sample_ids.jsonl").write_text(
            "".join(json.dumps(sample_id, ensure_ascii=False) + "\n" for sample_id in report.get("sample_ids", [])),
            encoding="utf-8")
        db = SessionLocal()
        try:
            db.add(Dataset(id=source_id, name=str(report.get("dataset_id", "EduChat"))[:200],
                           description="官方接口采集来源；核验状态以采集清单为准。", data_type="json", status="ready",
                           size_bytes=target.stat().st_size, row_count=int(report.get("sample_count", 0)),
                           column_count=len(report.get("field_names", [])), tags=["preproject", "raw", "official_fetch"],
                           columns_info={"source_id": source_id, "version_id": raw_version_id,
                                         "revision_verification_status": "verified" if report.get("revision_verified") else "unverified",
                                         "license_verification_status": "verified" if report.get("license_verified") else "unverified"},
                           owner_id=user_id))
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
        with _lock:
            job = _fetch_jobs[fetch_id]
            job.update(status="completed", current_step="completed", processed=count, ended_at=_now(),
                        source_id=source_id, sample_count=count, file_sha256=report["file_sha256"], error=None)
            _atomic_json(directory / "fetch_job.json", job)
    except Exception as exc:
        with _lock:
            job = _fetch_jobs[fetch_id]
            job.update(status="failed", current_step="failed", ended_at=_now(),
                        error=f"{type(exc).__name__}: {str(exc)[:500]}")
            _atomic_json(directory / "fetch_job.json", job)


def _run_task(task_id: str, user_key: str, source_manifest: dict[str, Any], input_path: Path,
              task_dir: Path, request: CreateTaskRequest) -> None:
    with _lock:
        task = _tasks[task_id]
        event = _cancel_events[task_id]
        if event.is_set():
            task.update(status="cancelled", current_step="cancelled", ended_at=_now())
            _store_task(task)
            return
        task.update(status="running", current_step="starting", started_at=_now())
        _store_task(task)

    config_path = PROJECT_ROOT / "configs" / "preproject_pipeline.json"
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
        config["source"] = {
            "enabled": False,
            "dataset_id": source_manifest["dataset_id"],
            "source_id": f"local-upload:{source_manifest['source_id']}",
            "source_url": source_manifest["source_url"],
            "license": source_manifest["license"],
            "revision": source_manifest["revision"],
            "split": source_manifest["split"],
        }
        if source_manifest.get("source_type") == "test_fixture":
            config["license_policy"]["licenses_allowed_for_local_processing"].append("test-only")
        config["data_subset_id"] = request.version_name
        config["cleaning_enabled"] = request.cleaning_enabled
        config["deduplication"]["near_duplicate_enabled"] = request.near_duplicate_enabled
        config["deduplication"]["near_duplicate_hamming_distance"] = request.near_duplicate_hamming_distance
        config["deduplication"]["near_duplicate_action"] = request.near_duplicate_action
        config["privacy_enabled"] = request.privacy_enabled
        task.update(current_step="processing", total=source_manifest["sample_count"], processed=0)
        task["logs"] = [{"time": _now(), "stage": "processing", "message": "数据处理任务开始"}]
        _store_task(task)

        def progress(event: dict[str, Any]) -> None:
            stage = event.get("stage", "processing")
            processed = event.get("processed", task.get("processed", 0))
            should_log = stage != task.get("current_step") or processed == 0 or processed == event.get("total") or processed % 1000 == 0
            task.update(current_step=stage,
                        processed=processed,
                        total=event.get("total", task.get("total", 0)))
            if should_log:
                logs = task.setdefault("logs", [])
                logs.append({"time": _now(), "stage": stage, "processed": processed,
                             "total": event.get("total", task.get("total", 0))})
                del logs[:-200]
            _store_task(task)

        result = run_pipeline(
            input_path=input_path, output_dir=task_dir / "output", config=config, config_path=config_path,
            source_manifest_path=input_path.parent / "source_manifest.json",
            progress_callback=progress, cancel_check=event.is_set,
        )
        if event.is_set():
            raise PipelineCancelled("任务已取消。")
        output_dir = task_dir / "output"
        output_manifest = json.loads((output_dir / "dataset_manifest.json").read_text(encoding="utf-8"))
        output_rows = _jsonl_rows(output_dir / "processed.jsonl")
        source_version_id = str(source_manifest.get("version_id") or "")
        version_seed = f"{source_manifest.get('file_sha256', '')}:{task.get('config_fingerprint', '')}:{task_id}"
        processed_version_id = "processed_" + hashlib.sha256(version_seed.encode("utf-8")).hexdigest()[:24]
        version_dir = task_dir / "versions"
        version_dir.mkdir(parents=True, exist_ok=True)
        sample_ids_path = version_dir / f"{processed_version_id}_sample_ids.jsonl"
        sample_ids_path.write_text("".join(f"{json.dumps(row.get('sample_id'), ensure_ascii=False)}\n" for row in output_rows), encoding="utf-8")
        _atomic_json(version_dir / f"{processed_version_id}.json", {
            "version_id": processed_version_id, "parent_version_id": source_version_id or None,
            "version_type": "processed", "source_id": source_manifest.get("source_id"),
            "task_id": task_id, "dataset_id": source_manifest.get("dataset_id"),
            "sample_count": len(output_rows), "sample_ids_path": str(sample_ids_path.resolve()),
            "raw_file_path": str(input_path.resolve()), "processed_file_path": str((output_dir / "processed.jsonl").resolve()),
            "qualified_file_path": str((output_dir / "qualified.jsonl").resolve()),
            "raw_sha256": source_manifest.get("file_sha256"),
            "processed_sha256": (output_manifest.get("output") or {}).get("sha256"),
            "config_fingerprint": task.get("config_fingerprint"),
            "quality_report_path": str((output_dir / "quality_report.md").resolve()),
            "quality_metrics_path": str((output_dir / "quality_metrics.json").resolve()),
            "statistics_path": str((output_dir / "statistics.json").resolve()),
            "license": source_manifest.get("license", "unknown"),
            "license_verification_status": "verified" if source_manifest.get("license_verified") else "unverified",
            "revision": source_manifest.get("revision", "unknown"),
            "revision_verification_status": "verified" if source_manifest.get("revision_verified") else "unverified",
            "authorization_status": "authorized" if source_manifest.get("redistribution_authorized") else "unverified_or_not_authorized",
            "quality_gate": result["gate"], "status": "processed_candidate", "created_at": _now(),
        })
        with _lock:
            if event.is_set():
                raise PipelineCancelled("任务已取消。")
            task.update(status="completed", current_step="completed", processed=task.get("total", 0),
                        ended_at=_now(), statistics=result["statistics"], quality=result["quality"],
                        raw_version_id=source_version_id or None, version_id=processed_version_id,
                        gate=result["gate"], error=None)
            _store_task(task)
    except PipelineCancelled:
        task.update(status="cancelled", current_step="cancelled", ended_at=_now(), error=None)
    except Exception as exc:
        task.update(status="failed", current_step="failed", ended_at=_now(),
                    error=f"{type(exc).__name__}: {str(exc)[:500]}")
    _store_task(task)


@router.get("/catalog", dependencies=[Depends(_require_operator)])
def catalog() -> dict[str, Any]:
    return {"items": [{"dataset_id": "ecnu-icalk/educhat-sft-002-data-osm",
                       "source_url": "https://huggingface.co/datasets/ecnu-icalk/educhat-sft-002-data-osm",
                       "license": "cc-by-nc-4.0", "revision": "289618b953588bbd1b2a6e217cdd2c53e9cbcf49",
                       "revision_verified": False, "network_status": "not_verified_in_current_environment",
                       "field_schema": {"sequence": "list[str] (alternating question/answer)", "system_prompt": "str"},
                       "local_processing_only": True}]}


@router.get("/templates", dependencies=[Depends(_require_operator)])
def governance_templates() -> dict[str, Any]:
    common = ["格式验证", "基础清洗", "精确及近似去重", "敏感信息脱敏", "五维质量评价"]
    return {"items": [
        {"id": "education_qa", "name": "教育问答标准治理", "description": "问答、指令数据和多轮对话", "rules": common},
        {"id": "general_text", "name": "通用文本治理", "description": "文本 JSONL、问答 JSONL 和指令数据；普通文本不直接进入问答训练", "rules": common},
    ]}


def _model_resources(user: User) -> list[dict[str, Any]]:
    path = _user_root(user) / "resources" / "models.json"
    value = _read_json(path) if path.is_file() else {}
    return value.get("items", []) if isinstance(value.get("items", []), list) else []


@router.post("/resources/models", status_code=201)
def register_model_resource(body: ModelResourceRequest, user: User = Depends(_require_operator)) -> dict[str, Any]:
    from app.services.module4 import local_model_status
    path = Path(body.path).expanduser().resolve()
    ready, message = local_model_status(str(path))
    if not ready:
        raise HTTPException(status_code=422, detail=message)
    items = _model_resources(user)
    item = {"id": uuid.uuid4().hex, "name": body.name.strip(), "path": str(path), "license_status": body.license_status, "created_at": _now()}
    items.append(item)
    _atomic_json(_user_root(user) / "resources" / "models.json", {"items": items})
    return {"id": item["id"], "name": item["name"], "license_status": item["license_status"], "ready": True}


@router.get("/resources")
def platform_resources(user: User = Depends(_require_operator), db: Session = Depends(get_db)) -> dict[str, Any]:
    from app.api.module4 import training_environment_status
    from app.api.baseline import _environment as baseline_environment
    from app.services.module4 import evaluation_preflight, local_model_status
    training = training_environment_status()
    evaluation = evaluation_preflight({})
    model_ready, model_message = local_model_status("Qwen/Qwen2.5-0.5B-Instruct")
    cpu_ready = (PROJECT_ROOT / "configs/preproject_pipeline.json").is_file() and callable(run_pipeline)
    models = [{"name": "Qwen2.5 0.5B 配置模板", "ready": model_ready, "message": model_message, "license_status": "需自行核验"}]
    for item in _model_resources(user):
        ready, message = local_model_status(item.get("path"))
        models.append({"id": item["id"], "name": item["name"], "ready": ready, "message": message, "license_status": item.get("license_status", "unverified")})
    return {"data": {"assets": len(list_sources(user, db)["items"]), "synthetic_example": (PROJECT_ROOT / "demo-datasets/governance-example.jsonl").is_file()},
            "templates": governance_templates()["items"],
            "models": models,
            "environments": [{"name": "基础数据治理", "kind": "cpu", "ready": cpu_ready, "message": "内置 CPU 数据处理能力" if cpu_ready else "基础治理配置或执行器缺失"},
                             {"name": "模型训练", "kind": "training", "ready": bool(training and training.get("training_ready")), "details": training},
                             {"name": "模型评测", "kind": "evaluation", "ready": evaluation["ready"], "checks": evaluation["checks"]},
                             {"name": "轻量基线训练", "kind": "baseline", "ready": baseline_environment()["ready"], "details": baseline_environment()}]}


@router.get("/overview")
def governance_overview(user: User = Depends(_require_operator), db: Session = Depends(get_db)) -> dict[str, Any]:
    from app.api.module4 import candidate_versions, training_environment_status
    from app.api.baseline import list_experiments
    tasks = list_tasks(user)["items"]
    pending = 0
    for task in tasks:
        if task.get("status") == "completed":
            try:
                pending += int(review_items(task["task_id"], offset=0, limit=1, issue_type=None, user=user)["pending_count"])
            except (HTTPException, OSError, ValueError):
                pending = None
                break
    training = training_environment_status()
    return {"asset_count": db.query(Dataset).filter(Dataset.owner_id == str(user.id)).count(),
            "running_tasks": sum(item.get("status") in {"pending", "running"} for item in tasks),
            "pending_reviews": pending, "qualified_versions": len(candidate_versions(user)["items"]),
            "experiment_count": len(list_experiments(user)["items"]), "training_ready": bool(training and training.get("training_ready")),
            "recent_tasks": tasks[:5]}


@router.get("/asset-summary")
def asset_summary(user: User = Depends(_require_operator), db: Session = Depends(get_db)) -> dict[str, Any]:
    sources = list_sources(user, db)["items"]
    tasks = list_tasks(user)["items"]
    paths = list(_user_root(user).glob("sources/*/versions/*.json")) + list(_user_root(user).glob("tasks/*/versions/*.json"))
    version_rows = [_read_json(path) for path in paths]
    example_ids = [s["source_id"] for s in sources if s.get("is_platform_default") or s.get("dataset_id") == "TEST-ONLY/demo"]
    result = []
    for source in sources:
        source_id = source["source_id"]
        related = example_ids if source_id in example_ids else [source_id]
        associated = [v for v in version_rows if v.get("source_id") in related]
        source_tasks = [t for t in tasks if t.get("source_id") in related]
        result.append({"source_id":source_id, "related_source_ids":related,
                       "version_count":len(associated), "governed_count":sum(v.get("version_type") in {"processed", "reviewed_processed"} for v in associated),
                       "latest_status":source_tasks[0].get("status") if source_tasks else None})
    return {"items": result}


@router.post("/sources/fetch", status_code=202)
def fetch_official_source(body: FetchRequest, user: User = Depends(_require_operator)) -> dict[str, Any]:
    fetch_id, source_id = uuid.uuid4().hex, uuid.uuid4().hex
    directory = _user_root(user) / "sources" / source_id
    directory.mkdir(parents=True, exist_ok=False)
    job = {"fetch_id": fetch_id, "owner_key": _owner_key(user), "source_id": source_id,
           "status": "pending", "current_step": "queued", "processed": 0, "total": body.count,
           "created_at": _now(), "started_at": None, "ended_at": None, "error": None}
    with _lock:
        _fetch_jobs[fetch_id] = job
        _atomic_json(directory / "fetch_job.json", job)
    _pool.submit(_run_fetch, fetch_id, str(user.id), _owner_key(user), body.count, source_id, directory)
    return _public(job)


@router.get("/sources/fetch/{fetch_id}", dependencies=[Depends(_require_operator)])
def get_fetch_status(fetch_id: str, user: User = Depends(_require_operator)) -> dict[str, Any]:
    if not re.fullmatch(r"[0-9a-f]{32}", fetch_id):
        raise HTTPException(status_code=404, detail="采集任务不存在")
    with _lock:
        job = _fetch_jobs.get(fetch_id)
    if job is None:
        matches = list((_user_root(user) / "sources").glob("*/fetch_job.json"))
        job = next((_read_json(path) for path in matches if _read_json(path).get("fetch_id") == fetch_id), None)
    if not job or job.get("owner_key") != _owner_key(user):
        raise HTTPException(status_code=404, detail="采集任务不存在")
    return _public(job)


@router.get("/sources", dependencies=[Depends(_require_operator)])
def list_sources(user: User = Depends(_require_operator), db: Session = Depends(get_db)) -> dict[str, Any]:
    directory = _user_root(user) / "sources"
    items = [_read_json(path) for path in directory.glob("*/source_manifest.json")] if directory.is_dir() else []
    assets = {asset.id: asset for asset in db.query(Dataset).filter(Dataset.owner_id == str(user.id)).all()}
    result = []
    for item in sorted(items, key=lambda value: value.get("acquired_at", ""), reverse=True):
        public = _public(item)
        asset = assets.get(item.get("source_id"))
        public["asset_registered"] = asset is not None
        public["asset_status"] = asset.status if asset else None
        if item.get("is_platform_default") or item.get("is_classification_dataset"):
            try:
                expected_path = PROJECT_ROOT / ("demo-datasets/education-classification-synthetic.sha256" if item.get("is_classification_dataset") else "demo-datasets/governance-example.sha256")
                expected = expected_path.read_text(encoding="ascii").strip()
                public["default_ready"] = bool(validate_source(item["source_id"], user)["valid"] and sha256_file(_load_source(user, item["source_id"])[1]) == expected and item.get("file_sha256") == expected)
            except (HTTPException, OSError, ValueError):
                public["default_ready"] = False
        result.append(public)
    return {"items": result}


@router.post("/sources/upload", status_code=201)
async def upload_source(
    file: UploadFile = File(...), dataset_id: str = Form(...), source_url: str = Form(...),
    license: str = Form(...), revision: str = Form(...), split: str = Form("local"),
    user: User = Depends(_require_operator),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    filename = Path(file.filename or "data.jsonl").name
    suffix = Path(filename).suffix.casefold()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(status_code=400, detail="仅支持文本、JSONL、JSON 或 Parquet 文件")
    source_id = uuid.uuid4().hex
    directory = _user_root(user) / "sources" / source_id
    directory.mkdir(parents=True, exist_ok=False)
    target = directory / f"source{suffix}"
    size = 0
    try:
        with target.open("wb") as output:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    raise HTTPException(status_code=413, detail="上传文件超过 100 MiB 限制")
                output.write(chunk)
        rows, issues, _nonblank, _parse_errors = _read_local_source(target)
        if not rows:
            raise HTTPException(status_code=400, detail="文件中没有可读取的对象记录")
        if len(rows) > MAX_SOURCE_ROWS:
            raise HTTPException(status_code=413, detail="单个数据源最多导入 100,000 条记录")
        if issues:
            raise HTTPException(status_code=400, detail=f"文件包含 {len(issues)} 条不可解析记录，请先修复后再导入")
        source_ids = [str(row.get("id", row.get("hf_row_idx", row.get("row_idx", line)))) for line, row in rows]
        sample_ids = [str(row.get("sample_id") or _stable_sample_id(dataset_id, revision, split, source_id_value))
                      for (_line, row), source_id_value in zip(rows, source_ids)]
        fields = sorted({str(key) for _line, row in rows for key in row})
        field_types = {field: sorted({type(row.get(field)).__name__ for _line, row in rows if field in row})
                       for field in fields}
        file_hash = sha256_file(target)
        raw_version_id = f"raw_{file_hash[:24]}"
        fields_set = set(fields)
        if "data" in fields_set:
            field_mapping = {"instruction": "data[last_user]", "output": "data[last_assistant]",
                             "input": "data[history_turns]", "system": "system_prompt" if "system_prompt" in fields_set else None}
        elif "sequence" in fields_set:
            field_mapping = {"instruction": "sequence[last_user]", "output": "sequence[last_assistant]",
                             "input": "sequence[history_turns]", "system": "system_prompt" if "system_prompt" in fields_set else None}
        else:
            field_mapping = {"instruction": "instruction|question|prompt", "output": "output|answer|response",
                             "input": "input|context", "system": "system|system_prompt"}
        manifest = {
            "manifest_version": 1, "source_id": source_id, "dataset_id": dataset_id.strip(),
            "source_url": source_url.strip(), "license": license.strip().casefold(),
            "revision": revision.strip(), "split": split.strip() or "local",
            "sample_count": len(rows), "sample_ids": sample_ids, "source_record_ids": source_ids,
            "field_names": fields, "field_types": field_types, "stored_filename": target.name,
            "field_mapping": field_mapping,
            "file": target.name, "file_sha256": file_hash, "sha256": file_hash,
            "raw_file_path": str(target.resolve()), "file_size_bytes": size,
            "file_mtime_ns": target.stat().st_mtime_ns,
            "acquired_at": _now(), "sampling_method": "user_provided_local_file; no sampling performed by API",
            "provenance_method": "user_attested_local_import", "revision_verified": False,
            "license_verified": False, "redistribution_authorized": False,
            "source_type": "local_file", "license_verification_status": "unverified",
            "revision_verification_status": "unverified", "created_at": _now(),
            "version_id": raw_version_id, "status": "imported",
        }
        _atomic_json(directory / "source_manifest.json", manifest)
        version_dir = directory / "versions"
        version_dir.mkdir(parents=True, exist_ok=True)
        sample_ids_path = version_dir / f"{raw_version_id}_sample_ids.jsonl"
        sample_ids_path.write_text("".join(json.dumps(sample_id, ensure_ascii=False) + "\n" for sample_id in sample_ids), encoding="utf-8")
        _atomic_json(version_dir / f"{raw_version_id}.json", {
            "version_id": raw_version_id, "parent_version_id": None, "version_type": "raw",
            "source_id": source_id, "dataset_id": dataset_id.strip(), "sample_count": len(rows),
            "sample_ids_path": str(sample_ids_path.resolve()), "raw_file_path": str(target.resolve()), "sha256": file_hash,
            "license": license.strip().casefold(), "license_verification_status": "unverified",
            "revision": revision.strip(), "revision_verification_status": "unverified",
            "authorization_status": "unverified", "status": "imported", "created_at": manifest["created_at"],
        })
        asset = Dataset(
            id=source_id,
            name=dataset_id.strip()[:200],
            description="本地数据资产；来源版本和许可待核验。",
            data_type="parquet" if suffix in {".parquet", ".pq"} else "text" if suffix == ".txt" else "json",
            status="ready",
            size_bytes=size,
            row_count=len(rows),
            column_count=len(fields),
            tags=["preproject", "raw", "local_import", "provenance_unverified"],
            columns_info={"source_id": source_id, "version_id": raw_version_id, "field_names": fields,
                          "field_types": field_types, "license_verification_status": "unverified",
                          "revision_verification_status": "unverified"},
            owner_id=str(user.id),
        )
        db.add(asset)
        db.commit()
        return _public(manifest)
    except HTTPException:
        shutil.rmtree(directory, ignore_errors=True)
        raise
    except Exception as exc:
        db.rollback()
        shutil.rmtree(directory, ignore_errors=True)
        raise HTTPException(status_code=400, detail=f"数据文件验证失败：{type(exc).__name__}") from None
    finally:
        await file.close()


@router.post("/sources/demo-fixture", status_code=201)
async def import_demo_fixture(user: User = Depends(_require_operator), db: Session = Depends(get_db)) -> dict[str, Any]:
    if APP_ENV in {"production", "prod"} or not PASSWORDLESS_AUTH:
        raise HTTPException(status_code=403, detail="TEST-ONLY 初始化仅限本机演示模式。")
    path = PROJECT_ROOT / "demo-datasets" / "preproject-test-only.jsonl"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="TEST-ONLY 演示文件不存在。")
    upload = UploadFile(filename="test-only.jsonl", file=io.BytesIO(path.read_bytes()))
    source = await upload_source(file=upload, dataset_id="TEST-ONLY/demo", source_url="local-test-fixture",
                                 license="test-only", revision="TEST-ONLY", split="demo", user=user, db=db)
    manifest_path = _source_path(user, source["source_id"]) / "source_manifest.json"
    manifest = _read_json(manifest_path)
    manifest["source_type"] = "test_fixture"
    _atomic_json(manifest_path, manifest)
    return _public(manifest)


async def _ensure_example_source(user: User, db: Session) -> dict[str, Any]:
    path = PROJECT_ROOT / "demo-datasets" / "governance-example.jsonl"
    checksum_path = path.with_suffix(".sha256")
    if not path.is_file() or not checksum_path.is_file():
        raise HTTPException(status_code=404, detail="平台示例数据缺失，请检查安装文件。")
    digest = sha256_file(path)
    if not re.fullmatch(r"[0-9a-f]{64}", checksum_path.read_text(encoding="ascii").strip()) or digest != checksum_path.read_text(encoding="ascii").strip():
        raise HTTPException(status_code=409, detail="平台示例数据完整性校验失败，请恢复安装文件。")
    rows, issues, count, _errors = _read_local_source(path)
    ids = [str(row.get("sample_id") or "") for _, row in rows]
    if issues or not rows or count != len(rows) or len(set(ids)) != len(ids) or any(not value for value in ids):
        raise HTTPException(status_code=409, detail="平台示例数据格式无效，请恢复安装文件。")
    if any(not normalize_record(row, defaults={}, line_number=line).get("instruction") or not normalize_record(row, defaults={}, line_number=line).get("output") for line, row in rows):
        raise HTTPException(status_code=409, detail="平台示例包含无效问答记录。")
    root = _user_root(user)
    root.mkdir(parents=True, exist_ok=True)
    with _review_lock(root):
        return await _register_example_locked(user, db, path, digest)


async def _register_example_locked(user: User, db: Session, path: Path, digest: str) -> dict[str, Any]:
    sources = list_sources(user, db)["items"]
    source = next((item for item in sources if item.get("source_type") == "test_fixture" and item.get("dataset_id") == "平台合成示例" and item.get("file_sha256") == digest and item.get("asset_registered")), None)
    if not source:
        upload = UploadFile(filename="example.jsonl", file=io.BytesIO(path.read_bytes()))
        source = await upload_source(file=upload, dataset_id="平台合成示例", source_url="platform-synthetic-example",
                                     license="test-only", revision="synthetic-v1", split="example", user=user, db=db)
        manifest_path = _source_path(user, source["source_id"]) / "source_manifest.json"
        manifest = _read_json(manifest_path)
        manifest["source_type"] = "test_fixture"
        manifest["is_platform_default"] = True
        manifest["default_template"] = "education_qa"
        _atomic_json(manifest_path, manifest)
        asset = db.query(Dataset).filter(Dataset.id == source["source_id"], Dataset.owner_id == str(user.id)).first()
        if asset:
            asset.tags = ["preproject", "synthetic_example"]
            asset.description = "平台示例数据 · 合成数据 · 用于功能体验"
            db.commit()
        source = _public(manifest)
    validation = validate_source(source["source_id"], user)
    if not validation["valid"] or sha256_file(_load_source(user, source["source_id"])[1]) != digest:
        raise HTTPException(status_code=409, detail="平台示例未通过格式验证，请检查安装文件。")
    return source


@router.post("/examples/bootstrap")
async def bootstrap_example(user: User = Depends(_require_operator), db: Session = Depends(get_db)) -> dict[str, Any]:
    if APP_ENV in {"production", "prod"} or not PASSWORDLESS_AUTH or os.getenv("PLATFORM_DEMO_MODE") != "1":
        raise HTTPException(status_code=403, detail="自动初始化仅适用于本机演示模式。")
    source = await _ensure_example_source(user, db)
    classification = await _ensure_classification_source(user, db)
    candidate = await _prepare_classification_candidate(user, classification)
    return {"source": source, "classification_source": classification, "classification_version": candidate, "ready": True, "template": "education_qa", "synthetic": True}


async def _ensure_classification_source(user: User, db: Session) -> dict[str, Any]:
    path = PROJECT_ROOT / "demo-datasets/education-classification-synthetic.jsonl"
    checksum = path.with_suffix(".sha256")
    if not path.is_file() or not checksum.is_file() or sha256_file(path) != checksum.read_text(encoding="ascii").strip():
        raise HTTPException(status_code=409, detail="内置分类数据完整性校验失败。")
    parsed, issues, count, _ = _read_local_source(path)
    ids = [str(row.get("sample_id") or "") for _, row in parsed]
    labels = [row.get("classification_label") for _, row in parsed]
    if issues or count != len(parsed) or len(set(ids)) != len(ids) or any(not value for value in ids) or len(set(labels)) < 2 or any(not isinstance(v, str) or not re.fullmatch(r"[a-z][a-z0-9_-]{0,31}", v) for v in labels):
        raise HTTPException(status_code=409, detail="内置分类数据标签或结构无效。")
    root = _user_root(user); root.mkdir(parents=True, exist_ok=True)
    with _review_lock(root):
        source = next((item for item in list_sources(user, db)["items"] if item.get("is_classification_dataset") and item.get("file_sha256") == sha256_file(path) and item.get("asset_registered")), None)
        if not source:
            upload = UploadFile(filename="classification.jsonl", file=io.BytesIO(path.read_bytes()))
            source = await upload_source(file=upload, dataset_id="教育文本分类基础数据集", source_url="platform-synthetic-classification", license="test-only", revision="synthetic-v1", split="all", user=user, db=db)
            manifest_path = _source_path(user, source["source_id"]) / "source_manifest.json"
            manifest = _read_json(manifest_path)
            manifest.update(source_type="test_fixture", is_classification_dataset=True, is_platform_builtin=True)
            _atomic_json(manifest_path, manifest)
            asset = db.query(Dataset).filter(Dataset.id == source["source_id"], Dataset.owner_id == str(user.id)).first()
            if asset:
                asset.tags = ["preproject", "synthetic_classification"]
                asset.description = "合成教育文本，包含明确的分类标签，仅用于基线实验。"
                db.commit()
            source = _public(manifest)
    if not validate_source(source["source_id"], user)["valid"]:
        raise HTTPException(status_code=409, detail="内置分类数据验证失败。")
    return source


async def _prepare_classification_candidate(user: User, source: dict[str, Any]) -> dict[str, Any]:
    """Prepare one verified synthetic candidate through the normal CPU task pipeline."""
    from app.api.baseline import _classification_input
    root = _user_root(user)
    root.mkdir(parents=True, exist_ok=True)
    with _review_lock(root):
        tasks = [item for item in list_tasks(user)["items"] if item.get("source_id") == source["source_id"] and item.get("parameters", {}).get("version_name") == "平台分类基础版本"]
        for task in tasks:
            if task.get("status") == "completed" and task.get("version_id"):
                try:
                    version, rows = _classification_input(user, task["version_id"])
                    return {"version_id":version["version_id"], "task_id":task["task_id"], "sample_count":len(rows), "reused":True}
                except HTTPException:
                    continue
        active = next((item for item in tasks if item.get("status") in {"pending", "running"}), None)
        task = active or create_task(CreateTaskRequest(source_id=source["source_id"], template_id="general_text", version_name="平台分类基础版本"), user)["task"]
        for _ in range(600):
            task = _get_task(user, task["task_id"])
            if task.get("status") in {"completed", "failed", "cancelled"}: break
            await asyncio.sleep(.1)
        if task.get("status") != "completed" or not task.get("version_id"):
            raise HTTPException(status_code=503, detail="基础分类数据治理未完成，请检查任务后重试。")
        version, rows = _classification_input(user, task["version_id"])
        return {"version_id":version["version_id"], "task_id":task["task_id"], "sample_count":len(rows), "reused":False}


@router.get("/examples/default")
def example_status(user: User = Depends(_require_operator), db: Session = Depends(get_db)) -> dict[str, Any]:
    source = next((item for item in list_sources(user, db)["items"] if item.get("is_platform_default")), None)
    if not source: return {"ready": False, "source": None, "task": None}
    tasks = [task for task in list_tasks(user)["items"] if task.get("source_id") == source["source_id"] and task.get("parameters", {}).get("version_name") == "合成示例治理"]
    return {"ready": bool(source.get("default_ready")), "source": source, "task": tasks[0] if tasks else None, "template": "education_qa"}


@router.post("/examples/governance-task", status_code=202)
async def create_example_task(rerun: bool = False, user: User = Depends(_require_operator), db: Session = Depends(get_db)) -> dict[str, Any]:
    """Reuse the latest example run unless the user explicitly requests another."""
    source = await _ensure_example_source(user, db)
    tasks = [task for task in list_tasks(user)["items"] if task.get("source_id") == source["source_id"] and task.get("parameters", {}).get("version_name") == "合成示例治理"]
    if tasks and not rerun:
        return {"source": source, "task": tasks[0], "template": "education_qa", "synthetic": True, "resumed": True}
    result = create_task(CreateTaskRequest(source_id=source["source_id"], version_name="合成示例治理", near_duplicate_action="review_only"), user)
    return {"source": source, "task": result["task"], "template": "education_qa", "synthetic": True, "duplicate_submission": result["duplicate_submission"], "resumed": False}


@router.get("/sources/local-educhat/status")
def local_educhat_status(user: User = Depends(_require_operator)) -> dict[str, Any]:
    folder = PROJECT_ROOT / "data" / "preproject" / "incoming" / "200"
    available = (folder / "educhat_raw_200.jsonl").is_file() and (folder / "educhat_manifest.json").is_file()
    return {"available": available, "message": "发现本地 EduChat 输入，可登记到当前用户。" if available else "未找到本地输入；请使用下方文件上传。"}


@router.post("/sources/local-educhat", status_code=201)
async def import_local_educhat(user: User = Depends(_require_operator), db: Session = Depends(get_db)) -> dict[str, Any]:
    folder = PROJECT_ROOT / "data" / "preproject" / "incoming" / "200"
    source_path, manifest_path = folder / "educhat_raw_200.jsonl", folder / "educhat_manifest.json"
    if not source_path.is_file() or not manifest_path.is_file():
        raise HTTPException(status_code=404, detail="未找到本地 EduChat 文件及其来源清单，请选择文件上传。")
    try:
        manifest = _load_and_verify_source_manifest(manifest_path, source_path)
        rows, issues, count, _errors = _read_local_source(source_path)
        if issues or not rows or len(rows) != count or len(rows) != manifest.get("sample_count"):
            raise ValueError("来源清单样本数量与输入文件不一致")
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=f"本地数据校验失败：{type(exc).__name__}") from None
    digest = sha256_file(source_path)
    for path in (_user_root(user) / "sources").glob("*/source_manifest.json"):
        item = _read_json(path)
        if item.get("file_sha256") == digest and item.get("dataset_id") == manifest.get("dataset_id"):
            return {**_public(item), "already_registered": True}
    upload = UploadFile(filename=source_path.name, file=io.BytesIO(source_path.read_bytes()))
    source = await upload_source(file=upload, dataset_id=str(manifest.get("dataset_id") or "local-educhat"),
                                 source_url=str(manifest.get("source_url") or "local-import"),
                                 license=str(manifest.get("license") or "unknown"),
                                 revision=str(manifest.get("revision") or "unverified"),
                                 split=str(manifest.get("split") or "local"), user=user, db=db)
    target_manifest = _source_path(user, source["source_id"]) / "source_manifest.json"
    registered = _read_json(target_manifest)
    registered.update(source_type="local_educhat", revision_verified=False, license_verified=False,
                      provenance_method="local_manifest_hash_verified; official_revision_and_license_unverified")
    _atomic_json(target_manifest, registered)
    return {**_public(registered), "already_registered": False}


@router.get("/sources/{source_id}", dependencies=[Depends(_require_operator)])
def get_source(source_id: str, user: User = Depends(_require_operator)) -> dict[str, Any]:
    manifest, path = _load_source(user, source_id)
    unchanged = _unchanged_since_hash(path, manifest)
    return {"source": _public(manifest),
            "file_unchanged_since_import_hash": unchanged,
            "preview": {"field_names": manifest.get("field_names", []), "row_count": manifest.get("sample_count")}}


@router.get("/sources/{source_id}/preview", dependencies=[Depends(_require_operator)])
def preview_source(source_id: str, offset: int = Query(default=0, ge=0), limit: int = Query(default=10, ge=1, le=100),
                   user: User = Depends(_require_operator)) -> dict[str, Any]:
    manifest, path = _load_source(user, source_id)
    rows, issues, _nonblank, _errors = _read_local_source(path)
    task_stub = {"source_id": source_id, "parameters": {"version_name": "raw-preview", "cleaning_enabled": True}}
    preview_fields = ("sample_id", "source_record_id", "instruction", "input", "output", "system",
                      "source_field_mapping", "processing_status", "processing_reasons")
    samples = []
    for line_number, row in rows[offset:offset + limit]:
        row_key = row.get("id", row.get("hf_row_idx", row.get("row_idx", line_number)))
        sample_id = str(row.get("sample_id") or _stable_sample_id(
            str(manifest.get("dataset_id", "local-unknown")), str(manifest.get("revision", "unversioned")),
            str(manifest.get("split", "local")), str(row_key)))
        normalized = _safe_normalized_sample(user, task_stub, sample_id, rows)
        if normalized:
            samples.append({key: normalized.get(key) for key in preview_fields})
    return {"source_id": source_id, "version_id": manifest.get("version_id"), "offset": offset,
            "limit": limit, "total": len(rows), "parse_issue_count": len(issues), "samples": samples,
            "privacy_engine": "privacy-patterns-v1", "privacy_residual_scan": "passed for displayed fields"}


@router.get("/versions", dependencies=[Depends(_require_operator)])
def list_versions(offset: int = Query(default=0, ge=0), limit: int = Query(default=50, ge=1, le=200),
                  user: User = Depends(_require_operator)) -> dict[str, Any]:
    root = _user_root(user)
    paths = list(root.glob("sources/*/versions/*.json")) + list(root.glob("tasks/*/versions/*.json"))
    versions = [_read_json(path) for path in paths]
    versions.sort(key=lambda value: value.get("created_at", ""), reverse=True)
    return {"items": _public(versions[offset:offset + limit]), "total": len(versions), "offset": offset, "limit": limit}


@router.get("/versions/{version_id}", dependencies=[Depends(_require_operator)])
def get_version(version_id: str, user: User = Depends(_require_operator)) -> dict[str, Any]:
    return {"version": _public(_read_json(_version_record_path(user, version_id)))}


@router.get("/version-comparison", dependencies=[Depends(_require_operator)])
def compare_versions(left: str, right: str, user: User = Depends(_require_operator)) -> dict[str, Any]:
    versions = [_read_json(_version_record_path(user, key)) for key in (left, right)]
    def load(version: dict[str, Any]) -> dict[str, dict[str, Any]]:
        path = version.get("comparison_file_path") or version.get("processed_file_path") or version.get("processed_path")
        if path and Path(path).is_file():
            return {str(row["sample_id"]): row for row in _jsonl_rows(Path(path)) if row.get("sample_id")}
        ids = version.get("sample_ids_path")
        if ids and Path(ids).is_file():
            return {str(json.loads(line)): {} for line in Path(ids).read_text(encoding="utf-8").splitlines() if line.strip()}
        raise HTTPException(status_code=410, detail="版本样本文件不存在")
    before, after = [load(version) for version in versions]
    left_ids, right_ids = set(before), set(after)
    common = left_ids & right_ids
    comparable = all(before[key] and after[key] for key in common)
    fields = ("instruction", "input", "output", "system")
    changed = sorted(key for key in common if any(before[key].get(f) != after[key].get(f) for f in fields)) if comparable else []
    state_changed = sorted(key for key in common if before[key].get("processing_status") != after[key].get("processing_status")) if comparable else []
    def get_file(version: dict[str, Any], key: str) -> dict[str, Any] | None:
        path = version.get(key)
        return _read_json(Path(path)) if path and Path(path).is_file() else None
    quality_left, quality_right = [get_file(version, "quality_metrics_path") for version in versions]
    metrics = []
    if quality_left and quality_right:
        for dimension, section in quality_left.get("metrics", {}).items():
            for metric, item in section.items():
                other = quality_right.get("metrics", {}).get(dimension, {}).get(metric)
                if isinstance(item, dict) and isinstance(other, dict) and "value" in item and "value" in other:
                    metrics.append({"dimension": dimension, "metric": metric, "left": item["value"], "right": other["value"],
                                    "reason": item.get("not_measurable_reason") or other.get("not_measurable_reason")})
    stats = [get_file(version, "statistics_path") for version in versions]
    qualified = [s.get("final_retained_count") if s else None for s in stats]
    return {"left": left, "right": right, "added_count": len(right_ids-left_ids), "removed_count": len(left_ids-right_ids),
            "changed_count": len(changed) if comparable else None, "status_changed_count": len(state_changed) if comparable else None,
            "added_sample_ids": sorted(right_ids-left_ids)[:100], "removed_sample_ids": sorted(left_ids-right_ids)[:100],
            "changed_sample_ids": changed[:100], "reason": None if comparable else "原始版本仅登记样本 ID，内容差异不可直接比较。",
            "metrics": metrics, "metrics_reason": None if quality_left and quality_right else "至少一个版本缺少可比较的质量报告。",
            "qualified_change": {"left": qualified[0], "right": qualified[1]},
            "authorization": {"left": versions[0].get("authorization_status", "unknown"), "right": versions[1].get("authorization_status", "unknown")},
            "source_verification": [{"revision": v.get("revision_verification_status"), "license": v.get("license_verification_status")} for v in versions]}


@router.post("/versions/{version_id}/release-candidate", dependencies=[Depends(_require_operator)])
def create_release_candidate(version_id: str, user: User = Depends(_require_operator)) -> dict[str, Any]:
    version_path = _version_record_path(user, version_id)
    version = _read_json(version_path)
    reasons = []
    if version.get("revision_verification_status") != "verified":
        reasons.append("revision未通过官方核验")
    if version.get("license_verification_status") != "verified":
        reasons.append("许可未通过官方核验")
    if version.get("authorization_status") != "authorized":
        reasons.append("未取得再分发授权")
    gate = version.get("quality_gate") or {}
    if gate.get("release_eligible") is not True:
        reasons.append("质量准入门未允许发布")
    if reasons:
        raise HTTPException(status_code=409, detail={"message": "当前数据版本不能生成发布候选", "reasons": reasons})
    candidate_id = "candidate_" + hashlib.sha256(version_id.encode("utf-8")).hexdigest()[:24]
    qualified_path = version.get("qualified_file_path")
    if not qualified_path or not Path(qualified_path).is_file():
        raise HTTPException(status_code=409, detail="合格数据池不存在，无法生成发布候选")
    candidate = {**version, "processed_file_path": qualified_path, "version_id": candidate_id, "parent_version_id": version_id,
                 "version_type": "release_candidate", "status": "candidate_ready", "created_at": _now()}
    candidate_dir = version_path.parent
    _atomic_json(candidate_dir / f"{candidate_id}.json", candidate)
    return {"version": _public(candidate)}


@router.post("/sources/{source_id}/validate", dependencies=[Depends(_require_operator)])
def validate_source(source_id: str, user: User = Depends(_require_operator)) -> dict[str, Any]:
    manifest, path = _load_source(user, source_id)
    rows, issues, _nonblank, _errors = _read_local_source(path)
    unchanged = _unchanged_since_hash(path, manifest)
    source_defaults = {"dataset_id": manifest.get("dataset_id"), "revision": manifest.get("revision"),
                       "split": manifest.get("split"), "license": manifest.get("license"),
                       "source_id": manifest.get("source_id")}
    schema_issue_count = 0
    for line_number, row in rows:
        normalized = normalize_record(row, defaults=source_defaults, line_number=line_number)
        if not isinstance(normalized.get("instruction"), str) or not normalized["instruction"].strip() or \
           not isinstance(normalized.get("output"), str) or not normalized["output"].strip():
            schema_issue_count += 1
    source_valid = bool(rows) and not issues and schema_issue_count == 0 and unchanged is not False
    if unchanged is True:
        message = "记录可读且SFT结构有效；文件大小/修改时间与导入时一致。哈希只在导入时计算，来源和许可仍为用户声明。"
    elif unchanged is False:
        message = "文件大小或修改时间与导入时不同；请重新导入以生成新的来源版本。"
    else:
        message = "记录可读且SFT结构有效；旧来源未保存修改时间，哈希只在导入时计算，来源和许可仍为用户声明。"
    return {"valid": source_valid, "row_count": len(rows),
            "parse_issue_count": len(issues), "schema_issue_count": schema_issue_count,
            "file_unchanged_since_import_hash": unchanged,
            "hash_recorded_at_import": bool(manifest.get("file_sha256")),
            "revision_verified": False, "license_verified": False,
            "message": message}


@router.get("/tasks", dependencies=[Depends(_require_operator)])
def list_tasks(user: User = Depends(_require_operator)) -> dict[str, Any]:
    directory = _user_root(user) / "tasks"
    items = [_read_json(path) for path in directory.glob("*/task.json")] if directory.is_dir() else []
    for task in items:
        if task.get("status") in {"pending", "running"} and task.get("task_id") not in _tasks:
            task.update(status="failed", current_step="interrupted", ended_at=_now(),
                        error="后端进程已重启，任务未自动续跑；请检查数据后重试。")
            _atomic_json(Path(task["task_dir"]) / "task.json", task)
    return {"items": [_public(task) for task in sorted(items, key=lambda value: value.get("created_at", ""), reverse=True)]}


@router.post("/tasks", status_code=202)
def create_task(body: CreateTaskRequest, user: User = Depends(_require_operator)) -> dict[str, Any]:
    manifest, input_path = _load_source(user, body.source_id)
    if not validate_source(body.source_id, user)["valid"]:
        raise HTTPException(status_code=422, detail="数据验证未通过，请检查格式后重新导入。")
    if not body.privacy_enabled:
        raise HTTPException(status_code=400, detail="预立项数据任务要求启用隐私检测与脱敏")
    config_fingerprint = hashlib.sha256(json.dumps(body.model_dump(), sort_keys=True).encode()).hexdigest()
    existing = [task for task in list_tasks(user)["items"]
                if task.get("source_id") == body.source_id and task.get("config_fingerprint") == config_fingerprint
                and task.get("status") in {"pending", "running"}]
    if existing:
        return {"task": existing[0], "duplicate_submission": True}
    task_id = uuid.uuid4().hex
    task_dir = _user_root(user) / "tasks" / task_id
    task_dir.mkdir(parents=True, exist_ok=False)
    task = {"task_id": task_id, "owner_key": _owner_key(user), "task_dir": str(task_dir),
            "source_id": body.source_id, "status": "pending", "current_step": "queued", "processed": 0,
            "total": manifest["sample_count"], "created_at": _now(), "started_at": None, "ended_at": None,
            "error": None, "config_fingerprint": config_fingerprint,
            "parameters": {key: value for key, value in body.model_dump().items() if key != "source_id"}}
    event = threading.Event()
    with _lock:
        _tasks[task_id] = task
        _cancel_events[task_id] = event
        _atomic_json(task_dir / "task.json", task)
    _pool.submit(_run_task, task_id, _owner_key(user), manifest, input_path, task_dir, body)
    return {"task": _public(task),
            "duplicate_submission": False}


@router.get("/tasks/{task_id}", dependencies=[Depends(_require_operator)])
def get_task(task_id: str, user: User = Depends(_require_operator)) -> dict[str, Any]:
    task = _get_task(user, task_id)
    return _public(task)


@router.post("/tasks/{task_id}/cancel", dependencies=[Depends(_require_operator)])
def cancel_task(task_id: str, user: User = Depends(_require_operator)) -> dict[str, Any]:
    task = _get_task(user, task_id)
    with _lock:
        task = _tasks.get(task_id, task)
        if task.get("status") not in {"pending", "running"}:
            raise HTTPException(status_code=409, detail="仅 pending 或 running 任务可以取消")
        event = _cancel_events.get(task_id)
        if event:
            event.set()
        else:
            task.update(status="cancelled", current_step="cancelled", ended_at=_now())
            _store_task(task)
    return {"task_id": task_id, "cancel_requested": True}


@router.post("/tasks/{task_id}/retry", status_code=202, dependencies=[Depends(_require_operator)])
def retry_task(task_id: str, user: User = Depends(_require_operator)) -> dict[str, Any]:
    task = _get_task(user, task_id)
    if task.get("status") != "failed":
        raise HTTPException(status_code=409, detail="只有失败任务可以重试")
    params = dict(task.get("parameters", {}))
    params["source_id"] = task["source_id"]
    return create_task(CreateTaskRequest(**params), user)


@router.get("/tasks/{task_id}/results", dependencies=[Depends(_require_operator)])
def task_results(task_id: str, user: User = Depends(_require_operator)) -> dict[str, Any]:
    task = _get_task(user, task_id)
    if task.get("status") != "completed":
        raise HTTPException(status_code=409, detail="任务尚未完成")
    output_dir = Path(task["task_dir"]) / "output"
    issues_path = output_dir / "review_queue.jsonl"
    issues = []
    if issues_path.is_file():
        for line in issues_path.read_text(encoding="utf-8").splitlines()[:100]:
            try:
                issues.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    state_file = Path(task["task_dir"]) / "review_state.json"
    review_state = _read_json(state_file) if state_file.is_file() else {}
    pending_rebuild = review_state.get("rebuild_status") == "pending"
    visible_reviewed_id = review_state.get("previous_version_id") if pending_rebuild else task.get("reviewed_version_id")
    version_dir = Path(task["task_dir"]) / "versions" / str(visible_reviewed_id or "")
    files = [name for name in sorted(DOWNLOADABLE) if (output_dir / name).is_file()]
    files.extend(name for name in sorted(DOWNLOADABLE) if name.startswith("reviewed_") and (version_dir / name).is_file())
    statistics = task.get("statistics")
    quality = task.get("quality")
    gate = task.get("gate")
    reviewed_quality_path = version_dir / "reviewed_quality_metrics.json"
    reviewed_stats_path = version_dir / "reviewed_statistics.json"
    if reviewed_quality_path.is_file() and reviewed_stats_path.is_file():
        quality = _read_json(reviewed_quality_path)
        statistics = _read_json(reviewed_stats_path)
        version_record = _read_json(Path(task["task_dir"]) / "versions" / f"{visible_reviewed_id}.json")
        gate = version_record.get("quality_gate", gate)
    all_records_path = version_dir / "reviewed_all.jsonl" if visible_reviewed_id and (version_dir / "reviewed_all.jsonl").is_file() else output_dir / "processed.jsonl"
    issue_counts: Counter[str] = Counter()
    records: list[dict[str, Any]] = []
    if all_records_path.is_file():
        records = _jsonl_rows(all_records_path)
        for row in records:
            issue_counts.update(set(row.get("processing_reasons", [])))
            if any(row.get("privacy_hits", {}).values()): issue_counts["privacy_hit"] += 1
    source_manifest, _ = _load_source(user, str(task["source_id"]))
    outcome = summarize_governance(records, statistics or {}, gate or {}, source_manifest, review_state)
    return {"statistics": _public(statistics), "quality": _public(quality), "gate": _public(gate), "outcome":_public(outcome),
            "reviewed_version_id": visible_reviewed_id, "review_rebuild_status": review_state.get("rebuild_status"), "review_samples": issues, "files": files, "issue_counts": dict(issue_counts)}


@router.get("/tasks/{task_id}/samples", dependencies=[Depends(_require_operator)])
def task_samples(task_id: str, offset: int = Query(default=0, ge=0), limit: int = Query(default=10, ge=1, le=50),
                 issue: str | None = Query(default=None, max_length=160), user: User = Depends(_require_operator)) -> dict[str, Any]:
    task = _get_task(user, task_id)
    if task.get("status") != "completed":
        raise HTTPException(status_code=409, detail="任务尚未完成")
    output_path = Path(task["task_dir"]) / "output" / "processed.jsonl"
    state_file = Path(task["task_dir"]) / "review_state.json"
    review_state = _read_json(state_file) if state_file.is_file() else {}
    reviewed_id = review_state.get("previous_version_id") if review_state.get("rebuild_status") == "pending" else task.get("reviewed_version_id")
    reviewed_all = Path(task["task_dir"]) / "versions" / str(reviewed_id or "") / "reviewed_all.jsonl"
    if reviewed_id and reviewed_all.is_file():
        output_path = reviewed_all
    if not output_path.is_file():
        raise HTTPException(status_code=404, detail="处理结果文件不存在")
    records = _jsonl_rows(output_path)
    if issue:
        if issue.startswith("sample:"):
            records = [row for row in records if row.get("sample_id") == issue[7:]]
            issue = None
    if issue:
        if issue == "stage:read_schema":
            parse_items = [row for row in _jsonl_rows(Path(task["task_dir"]) / "output" / "issue_samples.jsonl") if not row.get("sample_id")]
            return {"items": [{"sample_id": f"line:{row.get('line_number', '?')}", "source_record_id": row.get("line_number"),
                               "before": None, "after": {}, "status": row.get("status", "quarantine"),
                               "reasons": [row.get("reason", "invalid_record")], "cleaning_changes": [], "privacy_hits": {}}
                              for row in parse_items[offset:offset + limit]], "total": len(parse_items), "offset": offset, "limit": limit,
                    "notice": "解析失败的原始内容不在页面显示。"}
        stage_reasons = {"stage:deduplication": {"exact_duplicate", "normalized_duplicate", "near_duplicate_requires_review", "answer_conflict_requires_review", "sample_id_version_conflict"},
                         "stage:normalize_clean": {"missing_instruction_or_output", "replacement_character_encoding_suspected", "extreme_text_length", "placeholder_only_content"},
                         "stage:privacy_and_rescan": {"personal_information_masked", "personal_information_residual_after_masking", "configured_sensitive_source_field_removed"}}
        selected_reasons = stage_reasons.get(issue, {issue})
        records = [row for row in records if (issue == "stage:quality_admission" and row.get("processing_status") != "keep")
                   or (issue == "structure_conversion" and any(value and str(value) != key for key,value in (row.get("source_field_mapping") or {}).items()))
                   or (issue == "cleaning_modified" and (row.get("cleaning_audit") or {}).get("action") == "repair")
                   or (issue == "pending_review" and row.get("processing_status") == "review")
                   or (issue in {"privacy_hit", "stage:privacy_and_rescan"} and any(row.get("privacy_hits", {}).values()))
                   or (issue == "stage:normalize_clean" and any(str(reason).startswith(("incomplete_conversation:", "non_string_")) for reason in row.get("processing_reasons", [])))
                   or bool(selected_reasons.intersection(row.get("processing_reasons", [])))]
    _manifest, input_path = _load_source(user, str(task["source_id"]))
    source_rows, _issues, _count, _errors = _read_local_source(input_path)
    task_stub = {**task, "parameters": {**task.get("parameters", {}), "cleaning_enabled": False}}
    fields = ("instruction", "input", "output", "system")
    samples = []
    for row in records[offset:offset+limit]:
        before = _safe_normalized_sample(user, task_stub, str(row["sample_id"]), source_rows)
        before_view = {key: before.get(key, "") for key in fields} if before else None
        after_view = {key: row.get(key, "") for key in fields}
        review = (review_state.get("items") or {}).get(str(row["sample_id"]), {})
        mapping = row.get("source_field_mapping") or {}
        samples.append({"sample_id": row["sample_id"], "source_record_id": row.get("source_record_id"),
                        "before": before_view, "after": after_view, "status": row.get("processing_status"),
                        "reasons": row.get("processing_reasons", []), "cleaning_changes": row.get("cleaning_changes", []),
                        "duplicate_type": row.get("duplicate_type"), "privacy_hits": row.get("privacy_hits", {}),
                        "source_mapping": {key:str(value) for key,value in mapping.items() if key in fields and value},
                        "changed_fields": [key for key in fields if before_view and before_view.get(key) != after_view.get(key)],
                        "review_decision": review.get("decision"), "review_recheck": review_state.get("rebuild_status") if review else None,
                        "change_kind": "人工修改并重检" if review.get("decision") == "edit" and reviewed_id else "自动规则处理"})
    return {"items": samples, "total": len(records), "offset": offset, "limit": limit,
            "notice": "对比两侧均经隐私规则处理；来源侧为标准化后的脱敏预览。"}


@router.get("/tasks/{task_id}/delivery-preview", dependencies=[Depends(_require_operator)])
def delivery_preview(task_id: str, kind: Literal["processed", "qualified"] = "qualified", limit: int = Query(default=10, ge=1, le=10),
                     user: User = Depends(_require_operator)) -> dict[str, Any]:
    task = _get_task(user, task_id)
    if task.get("status") != "completed": raise HTTPException(status_code=409, detail="任务尚未完成。")
    root = Path(task["task_dir"])
    state = _read_json(root / "review_state.json") if (root / "review_state.json").is_file() else {}
    reviewed_id = state.get("previous_version_id") if state.get("rebuild_status") == "pending" else task.get("reviewed_version_id")
    if reviewed_id:
        base = root / "versions" / str(reviewed_id)
        filename = "reviewed_all.jsonl" if kind == "processed" else "reviewed_processed.jsonl"
    else:
        base = root / "output"
        filename = "processed.jsonl" if kind == "processed" else "qualified.jsonl"
    path = (base / filename).resolve()
    if path.parent != base.resolve() or not path.is_file(): raise HTTPException(status_code=404, detail="结果文件不存在。")
    rows = _jsonl_rows(path)
    preview = []
    for row in rows[:limit]:
        safe = copy.deepcopy(row)
        _hits, _masks, residual = inspect_and_mask(safe, _load_pipeline_config().get("privacy", {}))
        preview.append({"sample_id":safe.get("sample_id"), "instruction": "[存在隐私残留，已隐藏]" if any(residual.values()) else safe.get("instruction", ""),
                        "output":"[存在隐私残留，已隐藏]" if any(residual.values()) else safe.get("output", ""),
                        "status":safe.get("processing_status"), "reasons":safe.get("processing_reasons", [])})
    return {"kind":kind, "version_id":reviewed_id or task.get("version_id"), "filename":filename, "total":len(rows), "items":preview,
            "notice":"预览再次执行脱敏；下载文件按当前版本交付。"}


@router.get("/tasks/{task_id}/governance-report", dependencies=[Depends(_require_operator)])
def governance_report(task_id: str, user: User = Depends(_require_operator)) -> Response:
    from data_pipeline.governance_report import render_governance_report
    task = _get_task(user, task_id)
    results = task_results(task_id, user)
    source, _ = _load_source(user, str(task["source_id"]))
    version_dir = Path(task["task_dir"]) / "versions" / str(results.get("reviewed_version_id") or "")
    reviewed_all = version_dir / "reviewed_all.jsonl"
    records = _jsonl_rows(reviewed_all if results.get("reviewed_version_id") and reviewed_all.is_file() else Path(task["task_dir"]) / "output" / "processed.jsonl")
    content = render_governance_report(_public(source), results["statistics"], results["quality"], results["outcome"], records)
    return Response(content=content, media_type="text/markdown", headers={"Content-Disposition": 'attachment; filename="governance_report.md"'})


@router.get("/tasks/{task_id}/review-items", dependencies=[Depends(_require_operator)])
def review_items(task_id: str, offset: int = Query(default=0, ge=0), limit: int = Query(default=20, ge=1, le=100),
                 issue_type: str | None = Query(default=None, max_length=160),
                 user: User = Depends(_require_operator)) -> dict[str, Any]:
    task = _get_task(user, task_id)
    if task.get("status") != "completed":
        raise HTTPException(status_code=409, detail="任务尚未完成")
    items = _jsonl_rows(Path(task["task_dir"]) / "output" / "review_queue.jsonl")
    state_path = Path(task["task_dir"]) / "review_state.json"
    states = _read_json(state_path) if state_path.is_file() else {"items": {}}
    state_map = states.get("items", {}) if isinstance(states.get("items"), dict) else {}
    if issue_type:
        items = [item for item in items if issue_type in item.get("reasons", [])]
    _manifest, input_path = _load_source(user, str(task["source_id"]))
    rows, _issues, _nonblank, _errors = _read_local_source(input_path)
    page = []
    for item in items[offset:offset + limit]:
        sample_id = str(item.get("sample_id") or "")
        state = state_map.get(sample_id, {})
        record = {key: item.get(key) for key in ("sample_id", "line_number", "status", "reasons", "source_record_id", "near_duplicate_sample_ids")}
        record["decision"] = state.get("decision", "pending")
        normalized = _safe_normalized_sample(user, task, sample_id, rows) if sample_id else None
        if normalized:
            record["preview"] = {key: normalized.get(key) for key in ("instruction", "input", "output", "system", "source_field_mapping")}
            if state.get("decision") == "edit" and isinstance(state.get("edited_content"), dict):
                record["preview"].update(state["edited_content"])
        page.append(record)
    reviewed_id = task.get("reviewed_version_id")
    reviewed_path = Path(task["task_dir"]) / "versions" / str(reviewed_id or "") / "reviewed_processed.jsonl"
    reviewed_ids = {str(row.get("sample_id")) for row in _jsonl_rows(reviewed_path)} if reviewed_id else set()
    pending = sum(1 for item in items if (state_map.get(str(item.get("sample_id", "")), {}).get("decision") is None
                  or (state_map.get(str(item.get("sample_id", "")), {}).get("decision") == "edit"
                      and str(item.get("sample_id", "")) not in reviewed_ids)))
    return {"items": page, "total": len(items), "offset": offset, "limit": limit, "pending_count": pending,
            "revision": int(states.get("revision", 0)), "rebuild_status": states.get("rebuild_status")}


@router.get("/tasks/{task_id}/reviews", dependencies=[Depends(_require_operator)])
def review_history(task_id: str, offset: int = Query(default=0, ge=0), limit: int = Query(default=50, ge=1, le=200),
                   user: User = Depends(_require_operator)) -> dict[str, Any]:
    task = _get_task(user, task_id)
    state_path = Path(task["task_dir"]) / "review_state.json"
    state = _read_json(state_path) if state_path.is_file() else {}
    items = _jsonl_rows(Path(task["task_dir"]) / "reviews.jsonl") + list(state.get("events", []))
    items.sort(key=lambda row: row.get("reviewed_at", ""), reverse=True)
    return {"items": items[offset:offset + limit], "total": len(items), "offset": offset, "limit": limit}


@router.post("/tasks/{task_id}/reviews", status_code=201, dependencies=[Depends(_require_operator)])
def submit_review(task_id: str, body: ReviewRequest, user: User = Depends(_require_operator)) -> dict[str, Any]:
    task = _get_task(user, task_id)
    with _review_lock(Path(task["task_dir"])):
        return _submit_review_locked(task_id, body, user)


def _submit_review_locked(task_id: str, body: ReviewRequest, user: User) -> dict[str, Any]:
    task = _get_task(user, task_id)
    if task.get("status") != "completed":
        raise HTTPException(status_code=409, detail="任务尚未完成")
    task_dir = Path(task["task_dir"])
    issue = next((item for item in _jsonl_rows(task_dir / "output" / "review_queue.jsonl")
                  if item.get("sample_id") == body.sample_id), None)
    if issue is None:
        raise HTTPException(status_code=404, detail="样本不在该任务的待复核队列中")
    prior_path = task_dir / "review_state.json"
    states = _read_json(prior_path) if prior_path.is_file() else {"items": {}, "revision": 0, "events": []}
    if states.get("rebuild_status") == "pending":
        raise HTTPException(status_code=409, detail="上次复检尚未完成，请先重试复检。")
    if int(states.get("revision", 0)) != body.expected_revision:
        raise HTTPException(status_code=409, detail="审核队列已被其他用户更新，请刷新后重试。")
    prior = states.get("items", {}).get(body.sample_id, {})
    normalized = _safe_normalized_sample(user, task, body.sample_id)
    if normalized is None:
        raise HTTPException(status_code=404, detail="原始样本不存在")
    content_fields = ("instruction", "input", "output", "system")
    before_content = {key: normalized.get(key, "") for key in content_fields}
    before_hash = hashlib.sha256(json.dumps(before_content, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    edited = prior.get("edited_content") if isinstance(prior.get("edited_content"), dict) else None
    if body.decision == "edit":
        if not body.edited_content:
            raise HTTPException(status_code=422, detail="编辑复核必须提交 edited_content")
        if set(body.edited_content) - set(content_fields):
            raise HTTPException(status_code=422, detail="仅允许编辑 instruction、input、output、system 字段")
        config = _load_pipeline_config()
        draft = {**normalized, "processing_status": "keep", "processing_reasons": [], "status_history": [],
                 "_source_fields": {}}
        draft.update(body.edited_content)
        clean_record(draft, config.get("engineering_screens", {}))
        _hits, _masks, edit_residual = inspect_and_mask(draft, config.get("privacy", {}))
        if any(edit_residual.values()):
            raise HTTPException(status_code=422, detail="编辑内容脱敏后仍有敏感信息残留，未保存")
        edited = {key: str(draft.get(key, "")) for key in content_fields}
    safe_notes_record = {**normalized, "instruction": body.notes, "input": "", "output": "", "system": "",
                         "processing_status": "keep", "processing_reasons": [], "status_history": [], "_source_fields": {}}
    inspect_and_mask(safe_notes_record, _load_pipeline_config().get("privacy", {}))
    safe_notes = str(safe_notes_record.get("instruction", ""))
    after_content = edited or before_content
    reviewed_at = _now()
    event = {"sample_id": body.sample_id, "task_id": task_id, "version_id": task.get("version_id"),
             "reviewer_id": str(user.id), "issue_type": body.issue_type or (issue.get("reasons") or ["unspecified"])[0],
             "decision": body.decision, "before_hash": before_hash,
             "after_hash": hashlib.sha256(json.dumps(after_content, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest(),
             "reviewed_at": reviewed_at, "notes": safe_notes}
    state_path = task_dir / "review_state.json"
    states.setdefault("items", {})[body.sample_id] = {
        "decision": body.decision, "edited_content": edited, "original_status": issue.get("status", "review"),
        "issue_type": event["issue_type"], "reviewed_at": reviewed_at,
    }
    states["revision"] = int(states.get("revision", 0)) + 1
    event["revision"] = states["revision"]
    states.setdefault("events", []).append(event)
    states["rebuild_status"] = "pending"
    states["previous_version_id"] = task.get("reviewed_version_id")
    _atomic_json(state_path, states)
    task["review_committed_version_id"] = task.get("reviewed_version_id")
    task["review_rebuild_status"] = "pending"
    _store_task(task)
    try:
        version = _rebuild_reviewed_version(user, task, states)
    except Exception as exc:
        task["review_rebuild_error"] = f"{type(exc).__name__}: {str(exc)[:300]}"
        _store_task(task)
        raise HTTPException(status_code=500, detail="复核记录已保存，但重新处理和质量复算失败；请查看任务错误后重试。") from None
    states["rebuild_status"] = "completed"
    _atomic_json(state_path, states)
    task["review_rebuild_status"] = "completed"; task["review_committed_version_id"] = version["version_id"]
    task.pop("review_rebuild_error", None); _store_task(task)
    return {"review": event, "version": _public(version), "quality_recomputed": True, "revision": states["revision"]}


@router.post("/tasks/{task_id}/reviews/rebuild", dependencies=[Depends(_require_operator)])
def retry_review_rebuild(task_id: str, user: User = Depends(_require_operator)) -> dict[str, Any]:
    task = _get_task(user, task_id); task_dir = Path(task["task_dir"])
    with _review_lock(task_dir):
        task = _get_task(user, task_id)
        state_path = task_dir / "review_state.json"
        if not state_path.is_file(): raise HTTPException(status_code=404, detail="没有可重试的复核记录。")
        states = _read_json(state_path)
        if task.get("review_rebuild_status") != "pending" and states.get("rebuild_status") != "pending":
            raise HTTPException(status_code=409, detail="没有待重试的复检。")
        try: version = _rebuild_reviewed_version(user, task, states)
        except Exception:
            raise HTTPException(status_code=500, detail="复检仍未完成，请稍后重试。") from None
        states["rebuild_status"] = "completed"; _atomic_json(state_path, states)
        task["review_rebuild_status"] = "completed"; task["review_committed_version_id"] = version["version_id"]
        task.pop("review_rebuild_error", None); _store_task(task)
        return {"version": _public(version), "quality_recomputed": True, "revision": states.get("revision", 0)}


@router.get("/tasks/{task_id}/files/{filename}", dependencies=[Depends(_require_operator)])
def download_result(task_id: str, filename: str, user: User = Depends(_require_operator)) -> FileResponse:
    task = _get_task(user, task_id)
    if task.get("status") != "completed" or filename not in DOWNLOADABLE:
        raise HTTPException(status_code=404, detail="结果文件不存在")
    state_file = Path(task["task_dir"]) / "review_state.json"
    state = _read_json(state_file) if state_file.is_file() else {}
    reviewed_id = state.get("previous_version_id") if state.get("rebuild_status") == "pending" else task.get("reviewed_version_id")
    base_dir = (Path(task["task_dir"]) / "versions" / str(reviewed_id or "")
                if filename.startswith("reviewed_") else Path(task["task_dir"]) / "output")
    path = (base_dir / filename).resolve()
    if path.parent != base_dir.resolve() or not path.is_file():
        raise HTTPException(status_code=404, detail="结果文件不存在")
    media_type = "application/x-ndjson" if filename.endswith(".jsonl") else "application/json" if filename.endswith(".json") else "text/markdown"
    return FileResponse(path, media_type=media_type, filename=filename)
