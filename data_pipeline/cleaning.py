"""确定性文本修复和可替换的低成本工程初筛接口。"""
from __future__ import annotations

import html
import hashlib
import re
import unicodedata
from collections.abc import Callable
from typing import Any


def clean_text(value: str) -> tuple[str, list[str]]:
    original = value
    text = unicodedata.normalize("NFC", value.replace("\r\n", "\n").replace("\r", "\n"))
    text = html.unescape(text)
    text = re.sub(r"(?i)<\s*(?:p|/p|div|/div|br\s*/?|li|/li|ul|/ul|ol|/ol)\s*[^>]*>", "\n", text)
    text = re.sub(r"(?i)</?[a-z][a-z0-9]*(?:\s+[^<>]*?)?\s*/?>", " ", text)
    text = "".join(ch for ch in text if ch in "\n\t" or unicodedata.category(ch) != "Cc")
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[\t\f\v ]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    changes = ["unicode_whitespace_html_control_cleanup"] if text != original else []
    return text, changes


def _screen_schema(record: dict[str, Any], _config: dict[str, Any]) -> tuple[str, str] | None:
    if not record.get("instruction", "").strip() or not record.get("output", "").strip():
        return "drop", "missing_instruction_or_output"
    return None


def _screen_integrity(record: dict[str, Any], _config: dict[str, Any]) -> tuple[str, str] | None:
    combined = record.get("instruction", "") + record.get("input", "") + record.get("output", "")
    if "\ufffd" in combined:
        return "review", "replacement_character_encoding_suspected"
    return None


def _screen_placeholder(record: dict[str, Any], config: dict[str, Any]) -> tuple[str, str] | None:
    placeholders = [str(value).casefold() for value in config.get("placeholders", [])]
    if not placeholders:
        placeholders = ["待补充", "暂无内容", "无内容", "placeholder", "todo", "n/a"]
    text = " ".join(record.get(key, "") for key in ("instruction", "input", "output")).strip().casefold()
    if text and any(text == token for token in placeholders):
        return "drop", "placeholder_only_content"
    return None


def _screen_length(record: dict[str, Any], config: dict[str, Any]) -> tuple[str, str] | None:
    lengths = {key: len(record.get(key, "")) for key in ("instruction", "output")}
    maxima = config.get("max_chars", {})
    if lengths["instruction"] > int(maxima.get("instruction", 20000)) or lengths["output"] > int(maxima.get("output", 40000)):
        return "review", "extreme_text_length"
    return None


SCREENERS: dict[str, Callable[[dict[str, Any], dict[str, Any]], tuple[str, str] | None]] = {
    "schema_completeness": _screen_schema,
    "text_integrity": _screen_integrity,
    "placeholder_content": _screen_placeholder,
    "extreme_length": _screen_length,
}


def clean_record(record: dict[str, Any], config: dict[str, Any]) -> None:
    before_payload = "\x1f".join(record.get(key, "") for key in ("instruction", "input", "output", "system"))
    before_hash = hashlib.sha256(before_payload.encode("utf-8")).hexdigest()
    for key in ("instruction", "input", "output", "system"):
        value = record.get(key, "")
        if not isinstance(value, str):
            record["processing_status"] = "quarantine"
            record["processing_reasons"].append(f"non_string_{key}")
            continue
        cleaned, changes = clean_text(value)
        if changes:
            record["cleaning_changes"].extend(f"{key}:{change}" for change in changes)
            record[key] = cleaned
    content_payload = "\x1f".join(record.get(key, "") for key in ("instruction", "input", "output"))
    record["content_hash"] = hashlib.sha256(content_payload.encode("utf-8")).hexdigest()

    screens = config.get("engineering_screens", config)
    screen_results: list[dict[str, Any]] = []
    for name in screens.get("enabled", list(SCREENERS)):
        screener = SCREENERS.get(name)
        if not screener:
            record["processing_reasons"].append(f"unknown_screen:{name}")
            screen_results.append({"method": name, "result": "not_configured"})
            continue
        issue = screener(record, screens)
        if not issue:
            screen_results.append({"method": name, "result": "pass"})
            continue
        status, reason = issue
        screen_results.append({"method": name, "result": status, "reason": reason})
        record["processing_reasons"].append(reason)
        if status == "drop" or record["processing_status"] == "keep":
            record["processing_status"] = status

    # A completed, deterministic cleanup is an action, not an unresolved defect.
    record["engineering_screen_results"] = screen_results
    after_payload = "\x1f".join(record.get(key, "") for key in ("instruction", "input", "output", "system"))
    after_hash = hashlib.sha256(after_payload.encode("utf-8")).hexdigest()
    record["content_hash_before_cleaning"] = before_hash
    record["content_hash_after_cleaning"] = after_hash
    triggered = list(dict.fromkeys(record.get("cleaning_changes", []) + [
        item.get("reason", item.get("method", "")) for item in screen_results if item.get("result") not in {"pass", "not_configured"}
    ]))
    record["cleaning_audit"] = {
        "rules": [rule for rule in triggered if rule],
        "action": "repair" if before_hash != after_hash else record["processing_status"],
        "status": record["processing_status"],
        "before_hash": before_hash,
        "after_hash": after_hash,
        "safe_diff_summary": "文本规则命中数量与字段名已记录；未保存原文差异。" if triggered else None,
    }
    record["status_history"].append({"stage": "cleaning", "status": record["processing_status"]})
