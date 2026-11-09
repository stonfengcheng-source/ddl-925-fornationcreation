"""Conservative, evidence-based governance summary for reports and API DTOs."""
from __future__ import annotations
from typing import Any


def summarize_governance(records: list[dict[str, Any]], statistics: dict[str, Any], gate: dict[str, Any],
                         source: dict[str, Any] | None = None, review_state: dict[str, Any] | None = None) -> dict[str, Any]:
    source, review_state = source or {}, review_state or {}
    structure = 0
    for record in records:
        mapping = record.get("source_field_mapping") or {}
        if isinstance(mapping, dict) and any(value and str(value) != key for key, value in mapping.items()):
            structure += 1
    field_changes = sum((record.get("cleaning_audit") or {}).get("action") == "repair" for record in records)
    privacy_records = sum(any((record.get("privacy_masked") or {}).values()) for record in records)
    reviews = review_state.get("items") if isinstance(review_state.get("items"), dict) else {}
    pending = int(statistics.get("review_count") or 0)
    privacy_residual = statistics.get("privacy_residual_count")
    parse_errors = statistics.get("parse_error_count")
    stages = {stage.get("stage"): stage.get("status") for stage in statistics.get("stages", []) if isinstance(stage, dict)}
    stages_checked = all(stages.get(name) == "completed" for name in ("read_schema", "deduplication", "privacy_and_rescan"))
    eligible = int(statistics.get("final_retained_count") or 0)
    completeness = statistics.get("five_dimensions", {}).get("completeness", {})
    structure_rate = (completeness.get("valid_sft_structure_rate") or {}).get("value")
    fields_rate = (completeness.get("required_field_completeness_rate") or {}).get("value")
    quarantine = statistics.get("quarantine_count")
    evidence_complete = all(value is not None for value in (privacy_residual, parse_errors, structure_rate, fields_rate, quarantine)) and stages_checked
    engineering_ok = (evidence_complete and privacy_residual == 0 and parse_errors == 0 and structure_rate == 1
                      and fields_rate == 1 and quarantine == 0 and eligible > 0 and pending == 0)
    reasons = list(gate.get("reasons") or [])
    if pending and not any("复核" in reason for reason in reasons): reasons.append(f"仍有 {pending} 条样本需要复核。")
    if not evidence_complete: reasons.append("历史任务缺少完整阶段或隐私复检证据，需重新治理后确认。")
    release = bool(gate.get("release_eligible") and engineering_ok)
    if not release and not reasons: reasons.append("尚未提供完整发布授权及工程准入证据。")
    return {
        "actions": {"structure_conversion_records": structure, "field_normalization_records":field_changes,
                    "semantic_repair_records":None, "duplicate_removed_records":int(statistics.get("exact_duplicate_count") or 0) + int(statistics.get("normalized_duplicate_count") or 0),
                    "near_duplicate_review_records":int(statistics.get("near_duplicate_sample_count") or 0),
                    "privacy_masked_records":privacy_records, "privacy_hit_events":int(statistics.get("privacy_hit_count") or 0),
                    "human_reviewed_records":len(reviews), "note":"结构、字段、重复和隐私事件可重叠；文本语义正确性未自动修复。"},
        "engineering": {"status":"passed" if engineering_ok else "pending" if evidence_complete else "unknown", "candidate_count":eligible,
                        "parse_errors":parse_errors, "privacy_residual":privacy_residual, "pending_review":pending,
                        "structure_valid_rate":structure_rate, "required_fields_rate":fields_rate, "quarantine_count":quarantine,
                        "summary":f"{eligible} 条通过当前工程规则进入合格候选池。" + ("仍有问题待复核。" if pending else ""),
                        "scope":"工程规则筛查，不代表专业内容正确。"},
        "professional": {"status":"unverified", "summary":"尚未进行专业内容正确性认证。", "expert_review_evidence":False,
                         "manual_reviewed":len(reviews), "pending_review":pending},
        "publication": {"status":"eligible" if release else "blocked", "release_eligible":release, "reasons":reasons,
                        "revision_verified":bool(source.get("revision_verified")), "license_verified":bool(source.get("license_verified")),
                        "redistribution_authorized":bool(source.get("redistribution_authorized"))},
    }
