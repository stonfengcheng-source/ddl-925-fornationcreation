"""Validate and merge user-provided Hugging Face Dataset Viewer /rows responses."""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .pipeline import sha256_file


def _atomic_write(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
        if path.exists():
            raise FileExistsError(f"拒绝覆盖已存在文件：{path}")
        temporary.rename(path)
    finally:
        temporary.unlink(missing_ok=True)


def import_viewer_pages(
    pages: list[tuple[int, int, Path]], *, output_path: Path, config: dict[str, Any],
) -> dict[str, Any]:
    """Validate page files and write a stable, provenance-recorded source JSONL."""
    if not pages:
        raise ValueError("至少需要一个 Dataset Viewer 页面文件。")
    output_path = Path(output_path)
    manifest_path = output_path.with_name("educhat_manifest.json")
    collection_log_path = output_path.with_name("collection_log.jsonl")
    import_log_path = output_path.with_name("import_log.jsonl")
    for candidate in (output_path, manifest_path, collection_log_path, import_log_path):
        if candidate.exists():
            raise FileExistsError(f"拒绝覆盖已存在文件：{candidate}")

    source = dict(config.get("source", {}))
    dataset_id = str(source.get("dataset_id") or "ecnu-icalk/educhat-sft-002-data-osm")
    source_url = str(source.get("source_url") or f"https://huggingface.co/datasets/{dataset_id}")
    license_name = str(source.get("license") or "unknown").casefold()
    revision_claim = str(source.get("revision") or "unversioned")
    split = str(source.get("split") or "train")
    configured_seed = int(source.get("seed", 20260924))
    expected_fields = source.get("expected_fields", {"data": "list", "system_prompt": "str"})

    source_file_reports: list[dict[str, Any]] = []
    row_items: list[tuple[int, dict[str, Any]]] = []
    declared_totals: set[int] = set()
    field_types: dict[str, set[str]] = {}
    data_lengths: Counter[int] = Counter()
    content_hashes: Counter[str] = Counter()
    page_specs_seen: set[tuple[int, int]] = set()

    for offset, length, page_path in sorted(pages, key=lambda item: item[0]):
        page_path = Path(page_path)
        if length < 1 or length > 100:
            raise ValueError("Dataset Viewer 每次最多请求 100 条。")
        if offset < 0 or (offset, length) in page_specs_seen:
            raise ValueError("页码 offset 无效或重复。")
        page_specs_seen.add((offset, length))
        if not page_path.is_file():
            raise FileNotFoundError(f"页面文件不存在：{page_path}")
        raw_bytes = page_path.read_bytes()
        try:
            response = json.loads(raw_bytes.decode("utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"页面文件不是完整合法 JSON：{page_path.name}（{type(exc).__name__}）") from None
        if not isinstance(response, dict) or response.get("error"):
            raise ValueError(f"页面文件不是 Dataset Viewer rows 响应：{page_path.name}")
        rows = response.get("rows")
        if not isinstance(rows, list):
            raise ValueError(f"页面响应缺少 rows 数组：{page_path.name}")
        total = response.get("num_rows_total")
        if not isinstance(total, int) or total <= 0:
            raise ValueError(f"页面响应缺少有效 num_rows_total：{page_path.name}")
        declared_totals.add(total)
        expected_page_count = min(length, max(total - offset, 0))
        if len(rows) != expected_page_count:
            raise ValueError(f"页面记录数不符：{page_path.name} 应有 {expected_page_count} 条，实际 {len(rows)} 条。")

        page_indices: list[int] = []
        truncated_count = 0
        for item in rows:
            if not isinstance(item, dict) or isinstance(item.get("row_idx"), bool) or not isinstance(item.get("row_idx"), int):
                raise ValueError(f"页面包含无效 row_idx：{page_path.name}")
            row_index = item["row_idx"]
            row = item.get("row")
            if not isinstance(row, dict):
                raise ValueError(f"页面包含非对象 row：{page_path.name}，索引 {row_index}")
            if not offset <= row_index < offset + length:
                raise ValueError(f"row_idx 超出请求范围：{page_path.name}，索引 {row_index}")
            if item.get("truncated_cells"):
                truncated_count += 1
                raise ValueError(f"页面含被截断字段，拒绝导入：{page_path.name}，索引 {row_index}")
            page_indices.append(row_index)
            for name, value in row.items():
                field_types.setdefault(str(name), set()).add(type(value).__name__)
            data = row.get("data")
            if isinstance(data, list):
                data_lengths[len(data)] += 1
            digest = hashlib.sha256(json.dumps(row, ensure_ascii=False, sort_keys=True,
                                                separators=(",", ":"), default=str).encode("utf-8")).hexdigest()
            content_hashes[digest] += 1
            row_items.append((row_index, row))
        if len(page_indices) != len(set(page_indices)):
            raise ValueError(f"页面内 row_idx 重复：{page_path.name}")
        if set(page_indices) != set(range(offset, offset + expected_page_count)):
            raise ValueError(f"页面 row_idx 不连续或缺失：{page_path.name}")

        features = response.get("features")
        feature_types: dict[str, str] = {}
        if isinstance(features, list):
            for feature in features:
                if not isinstance(feature, dict) or not isinstance(feature.get("name"), str):
                    continue
                kind = feature.get("type")
                feature_types[feature["name"]] = json.dumps(kind, ensure_ascii=False, sort_keys=True)
        source_file_reports.append({
            "file": page_path.name,
            "sha256": hashlib.sha256(raw_bytes).hexdigest(),
            "size_bytes": len(raw_bytes),
            "query_parameters": {"offset": offset, "length": length, "revision": None},
            "revision_query_parameter_present": False,
            "requested_row_count": length,
            "response_row_count": len(rows),
            "num_rows_total": total,
            "viewer_partial": response.get("partial"),
            "truncated_row_count": truncated_count,
            "row_idx_min": min(page_indices) if page_indices else None,
            "row_idx_max": max(page_indices) if page_indices else None,
            "feature_types": feature_types,
            "response_shape_verified": True,
        })

    if len(declared_totals) != 1:
        raise ValueError("不同页面的 num_rows_total 不一致。")
    row_items.sort(key=lambda item: item[0])
    indices = [index for index, _row in row_items]
    if len(indices) != len(set(indices)):
        raise ValueError("跨页面发现重复 row_idx。")
    for field, expected_type in expected_fields.items():
        observed = field_types.get(str(field), set())
        type_ok = (expected_type == "list" and bool(observed) and all(value == "list" for value in observed)) or (
            expected_type == "str" and bool(observed) and all(value == "str" for value in observed)
        )
        if not type_ok:
            raise ValueError(f"字段结构与配置不符：{field} expected={expected_type}, observed={sorted(observed)}")
    for _row_index, row in row_items:
        data = row.get("data")
        if not isinstance(data, list) or not all(isinstance(item, str) for item in data):
            raise ValueError("EduChat data 字段必须为字符串列表。")
        if not isinstance(row.get("system_prompt"), str):
            raise ValueError("EduChat system_prompt 字段必须为字符串。")

    if not row_items:
        raise ValueError("页面中没有可导入记录。")
    page_hash_material = json.dumps({
        "dataset_id": dataset_id,
        "split": split,
        "source_files": [{"sha256": item["sha256"], "offset": item["query_parameters"]["offset"],
                          "length": item["query_parameters"]["length"]} for item in source_file_reports],
    }, sort_keys=True, separators=(",", ":")).encode("utf-8")
    batch_id = hashlib.sha256(page_hash_material).hexdigest()[:20]
    collected_at = datetime.now(timezone.utc).isoformat()

    sample_ids: list[str] = []
    normalized_rows: list[dict[str, Any]] = []
    for row_index, source_row in row_items:
        row = dict(source_row)
        if any(key in row for key in ("sample_id", "hf_row_idx", "collected_at", "acquisition_batch_id")):
            raise ValueError(f"来源行包含保留元数据字段，拒绝覆盖：row_idx={row_index}")
        sample_key = "\x1f".join((dataset_id, batch_id, split, str(row_index)))
        sample_id = "edu_" + hashlib.sha256(sample_key.encode("utf-8")).hexdigest()[:24]
        row.update({"hf_row_idx": row_index, "sample_id": sample_id,
                    "acquisition_batch_id": batch_id, "collected_at": collected_at})
        sample_ids.append(sample_id)
        normalized_rows.append(row)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    raw_temp: Path | None = None
    try:
        fd, raw_temp_name = tempfile.mkstemp(prefix=f".{output_path.name}.", suffix=".tmp", dir=output_path.parent)
        raw_temp = Path(raw_temp_name)
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            for row in normalized_rows:
                handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        if any(path.exists() for path in (output_path, manifest_path, collection_log_path, import_log_path)):
            raise FileExistsError("导入产物已存在；为避免覆盖，请使用新的输出目录。")
        raw_temp.rename(output_path)
    finally:
        if raw_temp is not None:
            raw_temp.unlink(missing_ok=True)

    output_hash = sha256_file(output_path)
    now = datetime.now(timezone.utc).isoformat()
    manifest = {
        "manifest_version": 1,
        "dataset_id": dataset_id,
        "source_url": source_url,
        "license": license_name,
        "license_basis": "project configuration; Viewer rows response did not include license metadata",
        "license_verified": False,
        "revision": revision_claim,
        "revision_verified": False,
        "revision_query_parameter_present": False,
        "split": split,
        "config": source.get("config"),
        "sampling_method": "sequential Dataset Viewer rows offsets; no random sampling performed",
        "seed": configured_seed,
        "seed_used": False,
        "requested_offsets": [item["query_parameters"]["offset"] for item in source_file_reports],
        "requested_page_length": 100,
        "sample_count": len(normalized_rows),
        "sample_ids": sample_ids,
        "source_record_ids": [str(index) for index in indices],
        "actual_row_indices": indices,
        "collection_batch_id": batch_id,
        "source_files": source_file_reports,
        "field_names": sorted(field_types),
        "field_types": {name: sorted(values) for name, values in sorted(field_types.items())},
        "data_list_length_counts": {str(length): count for length, count in sorted(data_lengths.items())},
        "source_field_mapping": {
            "data[0::2]": "user turns; the last user turn becomes instruction",
            "data[1::2]": "assistant turns; the last assistant turn becomes output",
            "data[0:-2]": "complete preceding turns become input history",
            "system_prompt": "system",
        },
        "mapping_evidence": {
            "all_rows_data_is_two_strings": all(len(row["data"]) == 2 for _index, row in row_items),
            "position_0_question_mark_count": sum("?" in row["data"][0] or "？" in row["data"][0] for _i, row in row_items),
            "position_1_explanation_marker_count": sum(
                any(token in row["data"][1] for token in ("答案", "解：", "解析", "首先", "因此", "综上"))
                for _i, row in row_items
            ),
            "interpretation": "position 0 is treated as user/instruction and position 1 as assistant/output; verify against dataset documentation when available",
        },
        "response_partial_flags": [item["viewer_partial"] for item in source_file_reports],
        "all_rows_untruncated": all(item["truncated_row_count"] == 0 for item in source_file_reports),
        "response_structure_verified": True,
        "provenance_method": "user_provided_dataset_viewer_rows_response; response structure and row indices validated locally",
        "source_origin_independently_authenticated": False,
        "acquired_at": collected_at,
        "imported_at": now,
        "file": output_path.name,
        "file_sha256": output_hash,
        "raw_page_duplicate_content_count": sum(value - 1 for value in content_hashes.values() if value > 1),
        "redistribution_authorized": False,
        "license_boundary": "Local research processing only under the configured CC BY-NC 4.0 claim; license and exact revision were not independently verified from these response files.",
    }
    collection_lines = [json.dumps({"event": "viewer_page_imported", **item,
                                     "log_basis": "metadata derived from supplied response file and declared query offset; not a captured live request log"},
                                    ensure_ascii=False, sort_keys=True) for item in source_file_reports]
    import_entry = {
        "event": "rows_merged_to_jsonl", "timestamp": now, "output_file": output_path.name,
        "sample_count": len(normalized_rows), "unique_sample_id_count": len(set(sample_ids)),
        "file_sha256": output_hash, "collection_batch_id": batch_id,
    }
    _atomic_write(manifest_path, json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    _atomic_write(collection_log_path, "\n".join(collection_lines) + "\n")
    _atomic_write(import_log_path, json.dumps(import_entry, ensure_ascii=False, sort_keys=True) + "\n")
    return {"manifest": manifest_path.name, "collection_log": collection_log_path.name,
            "import_log": import_log_path.name, "sample_count": len(normalized_rows),
            "unique_row_idx_count": len(set(indices)), "file_sha256": output_hash,
            "field_types": manifest["field_types"], "collection_batch_id": batch_id}
