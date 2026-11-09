"""来源字段到统一教育 SFT Schema 的映射。"""
from __future__ import annotations

import hashlib
import html
import json
import re
from datetime import datetime, timezone
from typing import Any


def _stable_sample_id(dataset_id: str, revision: str, split: str, record_key: str) -> str:
    material = "\x1f".join((dataset_id, revision, split, record_key))
    return "edu_" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]


def _canonical_digest(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _first_text(record: dict[str, Any], names: tuple[str, ...]) -> tuple[str, str | None]:
    for name in names:
        value = record.get(name)
        if isinstance(value, str) and value.strip():
            return value, name
    return "", None


def _conversation_qa(sequence: Any) -> tuple[str, str, str | None, str]:
    """保留完整历史，仅以最后一个完整 user/assistant 回合作为监督目标。"""
    if not isinstance(sequence, list) or not sequence:
        return "", "", None, ""
    if all(isinstance(item, dict) for item in sequence):
        pairs: list[tuple[str, str]] = []
        pending_user: str | None = None
        for item in sequence:
            role = str(item.get("role", "")).casefold()
            content = item.get("content", "")
            if role in {"system", "developer"}:
                continue
            if not isinstance(content, str):
                return "", "", "sequence", ""
            if role in {"user", "human"}:
                if pending_user is not None:
                    return "", "", "sequence", ""
                pending_user = content
            elif role in {"assistant", "gpt"}:
                if pending_user is None:
                    return "", "", "sequence", ""
                pairs.append((pending_user, content))
                pending_user = None
            else:
                return "", "", "sequence", ""
        if pending_user is not None or not pairs:
            return "", "", "sequence", ""
        history = "\n".join(f"用户：{question}\n助手：{answer}" for question, answer in pairs[:-1])
        return pairs[-1][0], pairs[-1][1], "sequence", history
    if all(isinstance(item, str) for item in sequence) and len(sequence) >= 2 and len(sequence) % 2 == 0:
        pairs = list(zip(sequence[::2], sequence[1::2]))
        history = "\n".join(f"用户：{question}\n助手：{answer}" for question, answer in pairs[:-1])
        return pairs[-1][0], pairs[-1][1], "sequence", history
    return "", "", "sequence", ""


def _labelled_qa(value: str) -> tuple[str, str]:
    value = html.unescape(value)
    value = re.sub(r"(?i)<\s*br\s*/?\s*>", "\n", value)
    value = re.sub(r"(?i)</?p\b[^>]*>", "\n", value)
    value = re.sub(r"<[^>]+>", " ", value)
    match = re.fullmatch(
        r"\s*(?:题目|问题)\s*[:：]\s*(?P<question>.*?)\n\s*答案\s*[:：]\s*"
        r"(?P<answer>.*?)(?:\n\s*解析\s*[:：]\s*(?P<analysis>.*?))?\s*",
        value, re.DOTALL,
    )
    if not match:
        return "", ""
    question, answer = match.group("question").strip(), match.group("answer").strip()
    analysis = (match.group("analysis") or "").strip()
    if analysis:
        answer += f"\n解析：{analysis}"
    return question, answer


def normalize_record(
    source_record: dict[str, Any],
    *,
    defaults: dict[str, Any],
    line_number: int,
    collected_at: str | None = None,
) -> dict[str, Any]:
    """映射数据集行，不把未筛查的原始字段复制进处理结果。"""
    dataset_id = str(defaults.get("dataset_id") or "local-unknown")
    revision = str(defaults.get("revision") or "unversioned")
    split = str(defaults.get("split") or "local")

    instruction, instruction_key = _first_text(source_record, ("instruction", "question", "prompt", "query"))
    output, output_key = _first_text(source_record, ("output", "answer", "response", "target"))
    input_text, input_key = _first_text(source_record, ("input", "context"))
    system, system_key = _first_text(source_record, ("system", "system_prompt"))
    sequence_key = None
    sequence_context = ""
    incomplete_conversation_source = None
    if not instruction or not output:
        for candidate_key in ("sequence", "data"):
            candidate_instruction, candidate_output, candidate_source, candidate_context = _conversation_qa(
                source_record.get(candidate_key)
            )
            if candidate_instruction.strip() and candidate_output.strip():
                instruction, output = candidate_instruction, candidate_output
                sequence_key, sequence_context = candidate_key, candidate_context
                incomplete_conversation_source = None
                break
            if source_record.get(candidate_key) is not None:
                incomplete_conversation_source = candidate_key
        if sequence_key:
            instruction_key, output_key = f"{sequence_key}[last_user]", f"{sequence_key}[last_assistant]"
            if not input_text and sequence_context:
                input_text, input_key = sequence_context, f"{sequence_key}[history]"
    if not instruction or not output:
        raw_text, raw_key = _first_text(source_record, ("raw_text", "clean_text", "masked_text"))
        if raw_text:
            question, answer = _labelled_qa(raw_text)
            instruction = instruction or question or raw_text
            output = output or answer
            instruction_key = instruction_key or raw_key
            output_key = output_key or (f"{raw_key}:答案" if answer else None)

    # A standalone document has no invented question or answer. The fixed label
    # identifies its content field and keeps it out of the SFT training bridge.
    document_text, document_key = _first_text(source_record, ("text",))
    is_document = bool(document_text and not instruction and not output)
    if is_document:
        instruction, output = "原始文本", document_text
        instruction_key, output_key = "document_label", document_key

    source_row_id = source_record.get("hf_row_idx", source_record.get("row_idx", source_record.get("id", line_number)))
    existing_id = source_record.get("sample_id")
    sample_id = str(existing_id).strip() if existing_id else _stable_sample_id(dataset_id, revision, split, str(source_row_id))
    record_payload = {key: value for key, value in source_record.items() if not str(key).startswith("_")}
    source_fields = {
        key: value for key, value in source_record.items()
        if not str(key).startswith("_") and key not in {"hf_row_idx", "row_idx"}
    }
    field_mapping = {key: value for key, value in {
        "instruction": instruction_key,
        "input": input_key,
        "output": output_key,
        "system": system_key,
    }.items() if value}

    time_value = collected_at or source_record.get("collected_at") or datetime.now(timezone.utc).isoformat()
    result = {
        "sample_id": sample_id,
        "dataset_id": dataset_id,
        "data_subset_id": str(defaults.get("data_subset_id") or dataset_id),
        "task_id": str(defaults.get("task_id") or "preproject-education-sft"),
        "source_id": str(defaults.get("source_id") or dataset_id),
        "source_url": str(defaults.get("source_url") or ""),
        "source_record_id": str(source_row_id),
        "license": str(defaults.get("license") or source_record.get("license") or "unknown"),
        "modality": str(defaults.get("modality") or "text"),
        "task_type": "text_document" if is_document else str(source_record.get("task_type") or "educational_qa"),
        "version_id": str(defaults.get("version_id") or f"{dataset_id}@{revision}"),
        "source_revision": revision,
        "source_split": split,
        "raw_record_sha256": _canonical_digest(record_payload),
        "instruction": instruction,
        "input": input_text,
        "output": output,
        "system": system,
        "published_at": source_record.get("published_at") or source_record.get("created_at"),
        "collected_at": str(time_value),
        "source_field_mapping": field_mapping,
        "_source_fields": source_fields,
        "_source_record": source_record,
        "processing_status": "keep",
        "status_history": [],
        "processing_reasons": ([f"incomplete_conversation:{incomplete_conversation_source}"]
                               if incomplete_conversation_source else []),
        "cleaning_changes": [],
        "privacy_hits": {},
        "privacy_masked": {},
        "near_duplicate_sample_ids": [],
    }
    # Preserve only an explicitly supplied, constrained categorical label.
    # Labels are not inferred from content and arbitrary source fields remain private.
    label = source_record.get("classification_label")
    if source_record.get("task_type") == "text_classification" and isinstance(label, str) and re.fullmatch(r"[a-z][a-z0-9_-]{0,31}", label):
        result["classification_label"] = label
    return result


def public_record(record: dict[str, Any]) -> dict[str, Any]:
    """移除流水线内部携带的原始字段，导出不含未筛查源值的记录。"""
    return {key: value for key, value in record.items() if not key.startswith("_")}
