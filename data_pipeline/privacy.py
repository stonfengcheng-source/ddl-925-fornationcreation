"""个人信息检测、类型占位符脱敏与残留复检。"""
from __future__ import annotations

import re
import hashlib
from collections import Counter
from typing import Any


DEFAULT_PATTERNS = {
    "email": r"(?<![A-Za-z0-9._%+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?![A-Za-z0-9._%+-])",
    "id_number": r"(?<!\d)[1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[0-9Xx](?!\d)",
    "phone": r"(?<!\d)(?:\+?86[\s-]?)?1[3-9](?:[\s-]?\d){9}(?!\d)",
}
DEFAULT_REPLACEMENTS = {"email": "[EMAIL]", "id_number": "[ID_NUMBER]", "phone": "[PHONE]"}


def _compile_rules(config: dict[str, Any]) -> list[tuple[str, re.Pattern[str], str]]:
    patterns = {**DEFAULT_PATTERNS, **config.get("patterns", {})}
    replacements = {**DEFAULT_REPLACEMENTS, **config.get("replacements", {})}
    return [(name, re.compile(pattern, re.IGNORECASE), str(replacements.get(name, "[REDACTED]"))) for name, pattern in patterns.items()]


def inspect_and_mask(record: dict[str, Any], config: dict[str, Any]) -> tuple[Counter[str], Counter[str], Counter[str]]:
    before_hash = hashlib.sha256("\x1f".join(
        str(record.get(field, "") or "") for field in ("instruction", "input", "output", "system")
    ).encode("utf-8")).hexdigest()
    rules = _compile_rules(config)
    hits: Counter[str] = Counter()
    masked: Counter[str] = Counter()
    residual: Counter[str] = Counter()
    text_fields = list(config.get("text_fields", ["instruction", "input", "output", "system"]))
    sensitive_fields = {str(name).casefold() for name in config.get("sensitive_fields", [])}

    for field in text_fields:
        value = record.get(field)
        if not isinstance(value, str):
            continue
        updated = value
        for kind, pattern, replacement in rules:
            matches = list(pattern.finditer(updated))
            hits[kind] += len(matches)
            updated, count = pattern.subn(replacement, updated)
            masked[kind] += count
        if updated != value:
            record[field] = updated
            record["processing_reasons"].append("personal_information_masked")

    source_fields = record.get("_source_fields", {})
    if isinstance(source_fields, dict):
        for name, value in source_fields.items():
            if str(name).casefold() in sensitive_fields and value not in (None, ""):
                hits[f"sensitive_field:{name}"] += 1
                masked[f"sensitive_field:{name}"] += 1
                record["processing_reasons"].append("configured_sensitive_source_field_removed")

    for field in text_fields:
        value = record.get(field)
        if not isinstance(value, str):
            continue
        for kind, pattern, _replacement in rules:
            residual[kind] += len(list(pattern.finditer(value)))
    if any(residual.values()) and record["processing_status"] not in {"drop", "quarantine"}:
        record["processing_status"] = "quarantine"
        record["processing_reasons"].append("personal_information_residual_after_masking")
    record["privacy_hits"] = dict(hits)
    record["privacy_masked"] = dict(masked)
    after_hash = hashlib.sha256("\x1f".join(
        str(record.get(field, "") or "") for field in ("instruction", "input", "output", "system")
    ).encode("utf-8")).hexdigest()
    record["privacy_audit"] = {
        "engine": "privacy-patterns-v1",
        "rules": sorted(kind for kind, count in hits.items() if count),
        "action": "masked" if before_hash != after_hash else "no_change",
        "status": record["processing_status"],
        "before_hash": before_hash,
        "after_hash": after_hash,
        "residual_counts": dict(residual),
    }
    record["status_history"].append({"stage": "privacy_rescan", "status": record["processing_status"]})
    return hits, masked, residual
