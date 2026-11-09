"""串联接入、标准化、清洗、去重、脱敏、五维画像和可追溯导出。"""
from __future__ import annotations

import hashlib
import json
import re
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from . import __version__
from .cleaning import clean_record
from .deduplication import deduplicate
from .privacy import DEFAULT_PATTERNS, inspect_and_mask
from .quality import calculate_quality, infer_topic
from .schema import normalize_record, public_record
from .governance_outcome import summarize_governance
from .source import DatasetViewerClient


class PipelineCancelled(RuntimeError):
    """流水线收到任务取消请求。"""


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _portable_source_metadata(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _portable_source_metadata(item) for key, item in value.items()
                if key not in {"path", "stored_filename"} and not key.endswith("_path")}
    if isinstance(value, list):
        return [_portable_source_metadata(item) for item in value]
    if isinstance(value, str) and (re.match(r"^[A-Za-z]:[\\/]", value) or value.startswith("/")):
        return "[local-path-redacted]"
    return value


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    temporary.replace(path)


def _read_jsonl(path: Path) -> tuple[list[tuple[int, dict[str, Any]]], list[dict[str, Any]], int, int]:
    records: list[tuple[int, dict[str, Any]]] = []
    issues: list[dict[str, Any]] = []
    nonblank = 0
    with path.open("r", encoding="utf-8-sig") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            nonblank += 1
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                issues.append({"line_number": line_number, "status": "quarantine", "reason": "invalid_json",
                               "raw_line_sha256": hashlib.sha256(line.encode("utf-8")).hexdigest()})
                continue
            if not isinstance(value, dict):
                issues.append({"line_number": line_number, "status": "quarantine", "reason": "json_value_is_not_object",
                               "raw_line_sha256": hashlib.sha256(line.encode("utf-8")).hexdigest()})
                continue
            records.append((line_number, value))
    return records, issues, nonblank, len(issues)


def _read_local_source(path: Path) -> tuple[list[tuple[int, dict[str, Any]]], list[dict[str, Any]], int, int]:
    """读取用户提供的 JSONL、JSON 或 Parquet 文件，不猜测或改写来源信息。"""
    suffix = path.suffix.casefold()
    if suffix == ".txt":
        lines = [(index, {"text": line}) for index, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1) if line.strip()]
        return lines, [], len(lines), 0
    if suffix == ".jsonl":
        return _read_jsonl(path)
    if suffix == ".json":
        text = path.read_text(encoding="utf-8-sig")
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            issue = {"line_number": exc.lineno, "status": "quarantine", "reason": "invalid_json",
                     "raw_line_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()}
            return [], [issue], 1 if text.strip() else 0, 1
        if isinstance(payload, list):
            values = payload
        elif isinstance(payload, dict) and isinstance(payload.get("data"), list):
            values = payload["data"]
        elif isinstance(payload, dict) and isinstance(payload.get("rows"), list):
            values = [({**entry["row"], "hf_row_idx": entry.get("row_idx", index)}
                       if isinstance(entry, dict) and isinstance(entry.get("row"), dict) else entry)
                      for index, entry in enumerate(payload["rows"])]
        elif isinstance(payload, dict):
            values = [payload]
        else:
            values = [payload]
        records: list[tuple[int, dict[str, Any]]] = []
        issues: list[dict[str, Any]] = []
        for index, value in enumerate(values, 1):
            if isinstance(value, dict):
                records.append((index, value))
            else:
                issues.append({"line_number": index, "status": "quarantine", "reason": "json_value_is_not_object",
                               "raw_line_sha256": hashlib.sha256(json.dumps(value, ensure_ascii=False).encode("utf-8")).hexdigest()})
        return records, issues, len(values), len(issues)
    if suffix in {".parquet", ".pq"}:
        try:
            from datasets import load_dataset
        except ImportError as exc:
            raise RuntimeError("Parquet 导入需要 Hugging Face datasets；当前环境未安装该可选依赖。") from exc
        try:
            dataset = load_dataset("parquet", data_files=str(path), split="train")
            records = [(index, dict(row)) for index, row in enumerate(dataset, 1)]
        except Exception as exc:
            raise ValueError(f"Parquet 文件无法读取：{type(exc).__name__}: {exc}") from exc
        return records, [], len(records), 0
    raise ValueError("仅支持 .txt、.jsonl、.json、.parquet 或 .pq 数据文件。")


def _load_and_verify_source_manifest(path: Path, raw_path: Path) -> dict[str, Any] | None:
    """校验用户随本地文件提供的来源清单；不把其声明升级为官方验证。"""
    if not path.is_file():
        raise FileNotFoundError(f"来源清单不存在：{path}")
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"来源清单无效：{type(exc).__name__}") from None
    if not isinstance(manifest, dict):
        raise ValueError("来源清单顶层必须是 JSON 对象。")
    input_section = manifest.get("input") if isinstance(manifest.get("input"), dict) else {}
    expected_hash = str(manifest.get("file_sha256") or input_section.get("sha256") or "").casefold()
    if expected_hash and expected_hash != sha256_file(raw_path).casefold():
        raise ValueError("来源清单中的文件 SHA-256 与输入文件不一致。")
    declared_file = manifest.get("file") or input_section.get("path")
    if declared_file and Path(str(declared_file)).name != raw_path.name:
        raise ValueError("来源清单声明的文件名与输入文件不一致。")
    manifest["local_file_hash_verified"] = bool(expected_hash)
    manifest["official_revision_verified"] = bool(manifest.get("revision_verified"))
    manifest["provenance_validation"] = "file_hash_match" if expected_hash else "source_claims_unverified"
    return manifest


def _apply_license_boundary(record: dict[str, Any], policy: dict[str, Any]) -> None:
    license_name = str(record.get("license", "unknown")).casefold()
    permitted = {str(value).casefold() for value in policy.get("licenses_allowed_for_local_processing", [])}
    if license_name == "unknown" or license_name not in permitted:
        record["processing_status"] = "quarantine"
        record["processing_reasons"].append("license_not_cleared_for_local_processing")
    elif license_name == "cc-by-nc-4.0":
        record["redistribution_authorized"] = False
        record["commercial_use_authorized"] = False
    record["status_history"].append({"stage": "source_license_gate", "status": record["processing_status"]})


def _issue_row(record: dict[str, Any], *, line_number: int | None = None) -> dict[str, Any]:
    return {
        "sample_id": record.get("sample_id"),
        "line_number": line_number,
        "status": record.get("processing_status", "quarantine"),
        "reasons": list(dict.fromkeys(record.get("processing_reasons", []))),
        "source_id": record.get("source_id"),
        "source_record_id": record.get("source_record_id"),
        "content_hash": record.get("content_hash"),
        "raw_record_sha256": record.get("raw_record_sha256"),
        "near_duplicate_sample_ids": record.get("near_duplicate_sample_ids", []),
    }


def _build_quality_report(
    *, source: dict[str, Any], statistics: dict[str, Any], quality: dict[str, Any], dedup: dict[str, Any],
    privacy: dict[str, Any], processing_flow: list[str], gate: dict[str, Any], records: list[dict[str, Any]] | None = None,
    review_state: dict[str, Any] | None = None,
) -> str:
    """Generate the same evidence-based report used for online reading and export."""
    from .governance_report import render_governance_report
    records = records or []
    outcome = summarize_governance(records, statistics, gate, source, review_state)
    return render_governance_report(source, statistics, quality, outcome, records)


def run_pipeline(
    *, input_path: str | Path | None, output_dir: str | Path, config: dict[str, Any],
    config_path: str | Path | None = None, source_manifest_path: str | Path | None = None,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
    cancel_check: Callable[[], bool] | None = None,
) -> dict[str, Any]:
    started = time.monotonic()
    started_at = datetime.now(timezone.utc)
    source = dict(config.get("source", {}))
    out_dir = Path(output_dir)
    raw_path: Path
    source_report: dict[str, Any] | None = source.get("_verified_manifest")
    if input_path:
        raw_path = Path(input_path)
    elif source.get("enabled"):
        raw_path = Path(source.get("raw_output", out_dir.parent / "raw" / "educhat_raw.jsonl"))
        if raw_path.exists():
            raise FileExistsError(f"源原始文件已存在，为保护原始数据未覆盖：{raw_path}")
        cache_dir = Path(source.get("cache_dir", out_dir.parent / "cache"))
        source_report = DatasetViewerClient(source, cache_dir).sample(source, raw_path)
    else:
        raise ValueError("请提供 --input，或在配置中启用 source 采集。")
    if not raw_path.is_file():
        raise FileNotFoundError(f"输入文件不存在：{raw_path}")

    if source_manifest_path:
        source_report = _load_and_verify_source_manifest(Path(source_manifest_path), raw_path)
    elif input_path:
        adjacent_manifest = raw_path.with_name("educhat_manifest.json")
        if not adjacent_manifest.is_file():
            adjacent_manifest = raw_path.with_name("source_manifest.json")
        if adjacent_manifest.is_file():
            source_report = _load_and_verify_source_manifest(adjacent_manifest, raw_path)
    if source_report:
        source.update({key: source_report.get(manifest_key, source.get(key)) for key, manifest_key in (
            ("dataset_id", "dataset_id"), ("source_url", "source_url"), ("license", "license"),
            ("revision", "revision"), ("split", "split"),
        )})

    defaults = {
        **source,
        "source_url": source.get("source_url", ""),
        "source_id": source.get("source_id", source.get("dataset_id", "local-unknown")),
        "revision": source.get("revision", "unversioned"),
        "license": source.get("license", "unknown"),
        "data_subset_id": config.get("data_subset_id", "preproject-education"),
        "task_id": config.get("task_id", "preproject-education-sft"),
        "version_id": config.get("version_id") or f"{source.get('dataset_id', 'local-unknown')}@{source.get('revision', 'unversioned')}",
        "modality": config.get("modality", "text"),
    }
    stages: list[dict[str, Any]] = []
    stage_started = time.monotonic()
    rows, parse_issues, nonblank_line_count, parse_error_count = _read_local_source(raw_path)
    stages.append({"stage": "read_schema", "status": "completed", "input_count": nonblank_line_count,
                   "output_count": len(rows), "processed_count": len(rows), "error_count": parse_error_count,
                   "duration_seconds": round(time.monotonic() - stage_started, 6), "rules": "JSON object parsing", "failure_reason": None})
    stage_started = time.monotonic()
    total_rows = len(rows)
    if progress_callback:
        progress_callback({"stage": "schema_and_cleaning", "processed": 0, "total": total_rows})
    records: list[dict[str, Any]] = []
    fixed_collected_at = config.get("fixed_collected_at")
    for row_index, (line_number, source_record) in enumerate(rows, 1):
        if cancel_check and cancel_check():
            raise PipelineCancelled("任务已取消。")
        try:
            record = normalize_record(source_record, defaults=defaults, line_number=line_number,
                                      collected_at=fixed_collected_at)
        except (TypeError, ValueError):
            parse_issues.append({"line_number": line_number, "status": "quarantine", "reason": "schema_mapping_error",
                                 "raw_line_sha256": hashlib.sha256(json.dumps(source_record, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()})
            parse_error_count += 1
            continue
        _apply_license_boundary(record, config.get("license_policy", {}))
        if config.get("cleaning_enabled", True):
            clean_record(record, config.get("engineering_screens", {}))
        else:
            record["status_history"].append({"stage": "cleaning", "status": "skipped_by_config"})
        records.append(record)
        if progress_callback and (row_index % 100 == 0 or row_index == total_rows):
            progress_callback({"stage": "schema_and_cleaning", "processed": row_index, "total": total_rows})

    stages.append({"stage": "normalize_clean", "status": "completed", "input_count": total_rows,
                   "output_count": len(records), "processed_count": len(records), "error_count": total_rows - len(records),
                   "duration_seconds": round(time.monotonic() - stage_started, 6),
                   "rules": {"normalization": "conversation-to-SFT-v1", "cleaning_enabled": config.get("cleaning_enabled", True),
                             "engineering_screens": config.get("engineering_screens", {})}, "failure_reason": None})

    if cancel_check and cancel_check():
        raise PipelineCancelled("任务已取消。")
    if progress_callback:
        progress_callback({"stage": "deduplication", "processed": 0, "total": len(records)})
    stage_started = time.monotonic()
    dedup_report = deduplicate(records, config.get("deduplication", {}))
    stages.append({"stage": "deduplication", "status": "completed", "input_count": len(records),
                   "output_count": len(records), "processed_count": len(records),
                   "error_count": dedup_report["sample_id_conflict_count"],
                   "duration_seconds": round(time.monotonic() - stage_started, 6),
                   "rules": dedup_report["parameters"], "engine": dedup_report["engine"], "failure_reason": None})
    for record in records:
        record["status_history"].append({"stage": "deduplication", "status": record["processing_status"]})

    detected: Counter[str] = Counter()
    masked: Counter[str] = Counter()
    residual: Counter[str] = Counter()
    privacy_config = config.get("privacy", {})
    stage_started = time.monotonic()
    for row_index, record in enumerate(records, 1):
        if cancel_check and cancel_check():
            raise PipelineCancelled("任务已取消。")
        hits, redactions, leftovers = inspect_and_mask(record, privacy_config)
        detected.update(hits)
        masked.update(redactions)
        residual.update(leftovers)
        record["content_hash"] = hashlib.sha256(
            "\x1f".join(record.get(key, "") for key in ("instruction", "input", "output")).encode("utf-8")
        ).hexdigest()
        if progress_callback and (row_index % 100 == 0 or row_index == len(records)):
            progress_callback({"stage": "privacy", "processed": row_index, "total": len(records)})
    privacy_report = {
        "detected_counts": dict(sorted(detected.items())),
        "masked_counts": dict(sorted(masked.items())),
        "residual_counts": dict(sorted(residual.items())),
        "residual_scan_passed": not any(residual.values()),
        "patterns_version": "privacy-patterns-v1",
        "plaintext_sensitive_values_logged": False,
    }
    stages.append({"stage": "privacy_and_rescan", "status": "completed", "input_count": len(records),
                   "output_count": len(records), "processed_count": len(records), "error_count": sum(residual.values()),
                   "duration_seconds": round(time.monotonic() - stage_started, 6),
                   "rules": {"engine": "privacy-patterns-v1", "patterns": {**DEFAULT_PATTERNS, **privacy_config.get("patterns", {})}},
                   "failure_reason": None})

    stage_started = time.monotonic()
    quality = calculate_quality(
        records, parse_error_count=parse_error_count, nonblank_line_count=nonblank_line_count,
        dedup_report=dedup_report, privacy_report=privacy_report,
        config={**config.get("quality", {}), "topic_keywords": config.get("quality", {}).get("topic_keywords", {})},
        evaluated_at=started_at,
    )
    if progress_callback:
        progress_callback({"stage": "quality_report", "processed": len(records), "total": len(records)})
    stages.append({"stage": "quality_admission", "status": "completed", "input_count": len(records),
                   "output_count": len(records), "processed_count": len(records), "error_count": 0,
                   "duration_seconds": round(time.monotonic() - stage_started, 6),
                   "rules": config.get("quality", {}), "failure_reason": None})
    status_counts = Counter(str(record.get("processing_status", "quarantine")) for record in records)
    status_counts.update(issue.get("status", "quarantine") for issue in parse_issues)
    status_count_total = sum(status_counts.values())
    if status_count_total != nonblank_line_count:
        raise ValueError(
            f"样本状态流转不守恒：非空输入行 {nonblank_line_count}，终态记录数 {status_count_total}。"
        )
    eligible_records = [
        record for record in records
        if record.get("processing_status") == "keep"
        and all(isinstance(record.get(key), str) and record[key].strip() for key in ("sample_id", "instruction", "output"))
    ]
    eligible_records.sort(key=lambda item: str(item["sample_id"]))
    all_ids = [str(record["sample_id"]) for record in records]
    if len(all_ids) != len(set(all_ids)):
        raise ValueError("导出前校验失败：处理后记录中 sample_id 不唯一。")
    ids = [str(record["sample_id"]) for record in eligible_records]
    if len(ids) != len(set(ids)):
        raise ValueError("导出前校验失败：processed.jsonl 中 sample_id 不唯一。")
    rules = privacy_config.get("patterns", {})
    patterns = {**DEFAULT_PATTERNS, **rules}
    for record in eligible_records:
        for field in privacy_config.get("text_fields", ["instruction", "input", "output", "system"]):
            value = record.get(field, "")
            if isinstance(value, str) and any(re.search(pattern, value, re.IGNORECASE) for pattern in patterns.values()):
                raise ValueError("导出前隐私残留复检失败；未写出最终数据。")
        record["quality_features"] = {
            "feature_version": quality["definitions_version"],
            "inferred_topic": infer_topic(record, config.get("quality", {})),
            "duplicate_sample_ratio": (dedup_report["exact_duplicate_count"] + dedup_report["normalized_duplicate_count"])
                                      / max(dedup_report["input_count"], 1),
            "near_duplicate_flag": bool(record.get("near_duplicate_sample_ids")),
            "effective_sample": 1,
            "effective_token_count": None,
            "token_count_method": "not_computed_without_a_pinned_tokenizer",
        }

    stage_started = time.monotonic()
    out_dir.mkdir(parents=True, exist_ok=True)
    processed_path = out_dir / "processed.jsonl"
    for record in records:
        record["quality_status"] = record.get("processing_status")
        record["processing_state"] = "completed"
    _write_jsonl(processed_path, [public_record(record) for record in records])
    _write_jsonl(out_dir / "qualified.jsonl", [public_record(record) for record in eligible_records])
    actions = []
    for record in records:
        for stage, details in (("clean", record.get("cleaning_audit", {})),
                               ("deduplicate", record.get("deduplication_audit", {})),
                               ("redact", record.get("privacy_audit", {}))):
            if details:
                actions.append({"sample_id": record["sample_id"], "action": stage, "details": details})
        actions.append({"sample_id": record["sample_id"], "action": "normalize", "field_mapping": record.get("source_field_mapping", {})})
    _write_jsonl(out_dir / "processing_actions.jsonl", actions)
    issue_rows = [_issue_row(record) for record in records if record.get("processing_status") in {"review", "quarantine", "drop"}]
    issue_rows.extend(parse_issues)
    _write_jsonl(out_dir / "review_queue.jsonl", [row for row in issue_rows if row.get("status") in {"review", "quarantine"}])
    _write_jsonl(out_dir / "issue_samples.jsonl", issue_rows)
    _write_json(out_dir / "quality_metrics.json", quality)
    _write_json(out_dir / "dedup_report.json", dedup_report)
    _write_json(out_dir / "privacy_report.json", privacy_report)
    stages.append({"stage": "export", "status": "completed", "input_count": len(records),
                   "output_count": len(eligible_records), "processed_count": len(records), "error_count": 0,
                   "duration_seconds": round(time.monotonic() - stage_started, 6),
                   "rules": "processed records plus keep-only qualified pool; source authorization checked separately",
                   "failure_reason": None})

    elapsed_seconds = round(time.monotonic() - started, 6)
    statistics = {
        "run_started_at": started_at.isoformat(),
        "run_completed_at": datetime.now(timezone.utc).isoformat(),
        "runtime_seconds": elapsed_seconds,
        "input_path": raw_path.name,
        "input_format": raw_path.suffix.casefold().lstrip("."),
        "input_sha256": sha256_file(raw_path),
        "input_nonblank_lines": nonblank_line_count,
        "raw_sample_count": len(records),
        "parse_error_count": parse_error_count,
        "cleaning_anomaly_count": sum(bool(record.get("cleaning_changes") or record.get("processing_reasons")) for record in records),
        "cleaning_modified_count": sum(record.get("content_hash_before_cleaning") is not None and record.get("content_hash_before_cleaning") != record.get("content_hash_after_cleaning") for record in records),
        "exact_duplicate_count": dedup_report["exact_duplicate_count"],
        "normalized_duplicate_count": dedup_report["normalized_duplicate_count"],
        "near_duplicate_sample_count": dedup_report["near_duplicate_sample_count"],
        "privacy_hit_count": sum(detected.values()),
        "privacy_masked_count": sum(masked.values()),
        "privacy_residual_count": sum(residual.values()),
        "review_count": status_counts["review"],
        "quarantine_count": status_counts["quarantine"],
        "drop_count": status_counts["drop"],
        "status_counts": dict(sorted(status_counts.items())),
        "status_count_total": status_count_total,
        "status_count_conserved": status_count_total == nonblank_line_count,
        "final_retained_count": len(eligible_records),
        "qualified_count": len(eligible_records),
        "automatic_repair_count": sum(bool(record.get("cleaning_changes") or record.get("privacy_masked")) for record in records),
        "stages": stages,
        "five_dimensions": quality["metrics"],
    }
    _write_json(out_dir / "statistics.json", statistics)
    _write_json(out_dir / "run_config.json", {
        "pipeline_version": __version__, "config": config,
        "config_path": str(Path(config_path).resolve()) if config_path else None,
        "input_path": str(raw_path.resolve()), "input_sha256": statistics["input_sha256"],
        "source_fetch_manifest": source_report,
    })

    license_name = str(defaults.get("license", "unknown")).casefold()
    redistributable_licenses = {"cc-by-4.0", "cc0-1.0", "mit", "apache-2.0"}
    release_eligible = bool(
        license_name in redistributable_licenses
        and source_report
        and source_report.get("license_verified") and source_report.get("revision_verified")
        and source_report.get("redistribution_authorized")
    )
    gate_reasons: list[str] = []
    if not privacy_report["residual_scan_passed"]:
        gate_reasons.append("存在脱敏残留样本，隔离后停止准入。")
    if not eligible_records:
        gate_reasons.append("没有通过当前工程质量规则的可导出样本。")
    if status_counts["review"]:
        gate_reasons.append(f"仍有 {status_counts['review']} 条样本等待人工复核。")
    source_verified = bool(source_report and source_report.get("revision_verified") and source_report.get("license_verified"))
    if not source_verified:
        gate_reasons.append("来源 revision 或许可未通过官方核验；本次输出仅可视为本地导入的待核实候选。")
    if not release_eligible:
        gate_reasons.append("未同时满足许可核验、可再分发许可和明确再分发授权；输出不是可发布数据版本。")
    gate = {"decision": "local_research_candidate" if eligible_records else "not_admitted",
            "reasons": gate_reasons, "release_eligible": release_eligible,
            "commercial_use_authorized": False if license_name == "cc-by-nc-4.0" else None}
    outcome = summarize_governance(records, statistics, gate, source_report or {})
    statistics["action_counts"] = outcome["actions"]
    statistics["publication_blocked_count"] = 0 if release_eligible else len(eligible_records)
    statistics["publication_blocked_reasons"] = [] if release_eligible else gate_reasons
    eligible_ids = {id(record) for record in eligible_records}
    for record in records:
        record["publication_status"] = "eligible" if release_eligible and id(record) in eligible_ids else "blocked"
    # Include publication state in both exports before calculating their hashes.
    _write_jsonl(processed_path, [public_record(record) for record in records])
    _write_jsonl(out_dir / "qualified.jsonl", [public_record(record) for record in eligible_records])
    _write_json(out_dir / "statistics.json", statistics)
    _write_json(out_dir / "dataset_manifest.json", {
        "manifest_version": 1,
        "pipeline_version": __version__,
        "data_subset_id": config.get("data_subset_id", "preproject-education"),
        "dataset_id": defaults.get("dataset_id"), "task_id": defaults.get("task_id"),
        "source_id": defaults.get("source_id"), "source_url": defaults.get("source_url"),
        "license": defaults.get("license", "unknown"), "source_revision": defaults.get("revision", "unknown"),
        "source_split": defaults.get("split", "unknown"),
        "usage_boundary": gate,
        "source_revision_verified": source_verified,
        "source_license_verified": bool(source_report and source_report.get("license_verified")),
        "source_fetch_manifest": _portable_source_metadata(source_report),
        "input": {"path": raw_path.name, "sample_count": len(records), "sha256": statistics["input_sha256"]},
        "version_id": out_dir.name, "parent_version": config.get("parent_version", "source:" + str(defaults.get("revision", "unknown"))),
        "output": {"path": processed_path.name, "sample_count": len(records),
                   "sha256": sha256_file(processed_path), "schema": "normalized-education-sft-v1"},
        "run_parameters": {"seed": source.get("seed"), "config_sha256": hashlib.sha256(
            json.dumps(config, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest(),
            "quality_feature_version": quality["definitions_version"], "privacy_rules_version": "privacy-patterns-v1"},
    })
    (out_dir / "quality_report.md").write_text(
        _build_quality_report(source={**defaults, **{key: (source_report or {}).get(key, False) for key in ("license_verified", "revision_verified", "redistribution_authorized")}}, statistics=statistics, quality=quality, dedup=dedup_report,
                              privacy=privacy_report, processing_flow=[
                                  "数据接入", "Schema 标准化", "确定性清洗", "完全/归一化/近似去重",
                                  "敏感信息脱敏", "残留复检", "五维质量画像", "质量准入", "JSONL 导出",
                              ], gate=gate, records=records), encoding="utf-8")
    manifest_path = out_dir / "dataset_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["artifacts"] = {path.name: {"sha256": sha256_file(path), "size_bytes": path.stat().st_size}
                             for path in sorted(out_dir.iterdir()) if path.is_file() and path != manifest_path}
    _write_json(manifest_path, manifest)
    _write_json(out_dir / "statistics.json", statistics)
    return {"statistics": statistics, "quality": quality, "dedup": dedup_report,
            "privacy": privacy_report, "gate": gate, "output_dir": str(out_dir.resolve())}
