"""五维质量画像。所有结果都附定义、分子、分母和适用范围。"""
from __future__ import annotations

import math
from collections import Counter
from datetime import datetime, timezone
from typing import Any


REQUIRED_FIELDS = (
    "sample_id", "dataset_id", "task_id", "source_id", "source_url", "license", "modality",
    "task_type", "version_id", "content_hash", "collected_at", "processing_status", "instruction", "output",
)


def _metric(definition: str, formula: str, numerator: int | float | None, denominator: int | float | None,
            value: Any, scope: str, anomalies: list[Any] | None = None,
            not_measurable_reason: str | None = None) -> dict[str, Any]:
    return {
        "definition": definition,
        "formula": formula,
        "numerator": numerator,
        "denominator": denominator,
        "value": value,
        "scope": scope,
        "anomalies": anomalies or [],
        "not_measurable_reason": not_measurable_reason,
    }


def infer_topic(record: dict[str, Any], config: dict[str, Any]) -> str:
    text = " ".join(str(record.get(field, "")) for field in ("instruction", "input", "output")).casefold()
    for label, keywords in config.get("topic_keywords", {}).items():
        if any(str(keyword).casefold() in text for keyword in keywords):
            return str(label)
    return "other_unclassified"


def _parse_date(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return None


def calculate_quality(
    records: list[dict[str, Any]], *, parse_error_count: int, nonblank_line_count: int,
    dedup_report: dict[str, Any], privacy_report: dict[str, Any], config: dict[str, Any],
    evaluated_at: datetime | None = None,
) -> dict[str, Any]:
    evaluated_at = evaluated_at or datetime.now(timezone.utc)
    count = len(records)
    present_fields = sum(1 for row in records for field in REQUIRED_FIELDS if row.get(field) not in (None, ""))
    complete_samples = sum(all(row.get(field) not in (None, "") for field in REQUIRED_FIELDS) for row in records)
    complete_field_cells = count * len(REQUIRED_FIELDS)
    missing = [
        {"sample_id": row.get("sample_id"), "fields": [field for field in REQUIRED_FIELDS if row.get(field) in (None, "")]}
        for row in records if any(row.get(field) in (None, "") for field in REQUIRED_FIELDS)
    ]
    parseable_rate = count / nonblank_line_count if nonblank_line_count else 0.0
    task_labelled = sum(bool(str(row.get("output", "")).strip()) for row in records)
    schema_valid = sum(
        all(isinstance(row.get(field), str) for field in ("sample_id", "dataset_id", "instruction", "output"))
        and bool(row.get("sample_id")) and bool(row.get("instruction")) and bool(row.get("output"))
        for row in records
    )
    conflict_samples = {sample for item in dedup_report.get("answer_conflicts", []) for sample in item.get("sample_ids", [])}
    conflict_group_count = int(dedup_report.get("answer_conflict_count", 0))
    repeated_question_groups = int(dedup_report.get("repeated_question_group_count", 0))
    records_after_exact = [row for row in records if "exact_duplicate" not in row.get("processing_reasons", [])
                           and "normalized_duplicate" not in row.get("processing_reasons", [])
                           and row.get("processing_status") != "quarantine"]
    topics = Counter(infer_topic(row, config) for row in records_after_exact)
    total_topics = sum(topics.values())
    topic_probs = [value / total_topics for value in topics.values()] if total_topics else []
    entropy = -sum(prob * math.log(prob) for prob in topic_probs if prob > 0)
    normalized_entropy = entropy / math.log(len(topics)) if len(topics) > 1 else 0.0
    long_tail_threshold = float(config.get("long_tail_share_threshold", 0.05))
    long_tail_topics = [name for name, value in topics.items() if total_topics and value / total_topics <= long_tail_threshold]
    topic_result = {
        "classification": "heuristic_estimate",
        "source": "config.topic_keywords; rule-based and not human-verified",
        "counts": dict(sorted(topics.items())),
        "observed_category_count": len(topics),
    }
    category_diversity = _metric(
        "Category coverage among the configured inferred topic labels.",
        "observed inferred categories / configured categories",
        len(topics), len(config.get("topic_keywords", {})) + 1,
        (len(topics) / (len(config.get("topic_keywords", {})) + 1)) if config.get("topic_keywords") else None,
        "deduplicated, non-quarantined parsed candidates",
        not_measurable_reason=None if config.get("topic_keywords") else "No topic taxonomy configured.",
    )

    valid_reference = config.get("reference_distribution")
    if isinstance(valid_reference, dict) and valid_reference and total_topics:
        names = set(topics) | set(valid_reference)
        actual = {name: topics.get(name, 0) / total_topics for name in names}
        ref_sum = sum(float(value) for value in valid_reference.values())
        if ref_sum > 0:
            reference = {name: float(valid_reference.get(name, 0)) / ref_sum for name in names}
            tvd = 0.5 * sum(abs(actual[name] - reference[name]) for name in names)
            unbiasedness = _metric(
                "Distribution difference from the configured reference; lower total variation distance is closer.",
                "0.5 * sum(abs(actual_share[c] - reference_share[c]))",
                round(tvd, 8), 1.0, round(tvd, 8), "deduplicated, non-quarantined parsed candidates",
            )
        else:
            unbiasedness = _metric("Reference distribution difference.", "N/A", None, None, None, "dataset",
                                    not_measurable_reason="Configured reference distribution sums to zero.")
    else:
        unbiasedness = _metric(
            "Difference from a reliable external reference distribution.", "N/A", None, None, None, "dataset",
            not_measurable_reason="No reliable reference distribution was supplied; no unbiasedness score is inferred.",
        )

    published = [_parse_date(row.get("published_at")) for row in records]
    date_covered = sum(value is not None for value in published)
    future_ids = [row.get("sample_id") for row, value in zip(records, published)
                  if value is not None and value > evaluated_at]
    ages = [(evaluated_at - value).total_seconds() / 86400 for value in published if value is not None]
    stale_days = float(config.get("stale_after_days", 730))
    known_expired = sum(age > stale_days for age in ages)
    time_anomalies = [row.get("sample_id") for row, value in zip(records, published)
                      if row.get("published_at") and value is None]
    date_coverage = date_covered / count if count else 0.0
    if date_covered:
        expired_value: Any = known_expired / date_covered
        expired_reason = None
    else:
        expired_value = None
        expired_reason = "No valid published_at timestamps; missing publication time is not treated as expired."

    metrics = {
        "completeness": {
            "valid_sft_structure_rate": _metric(
                "Share of normalized records with a non-empty instruction and assistant target.",
                "valid normalized instruction/target pairs / parsed records", schema_valid, count,
                schema_valid / count if count else None, "all parseable records"),
            "required_field_completeness_rate": _metric(
                "Share of task samples containing every configured required field; optional context is excluded.",
                "samples with all required fields / samples checked",
                complete_samples, count,
                complete_samples / count if count else 0.0,
                "all parseable JSON records before duplicate removal", missing[:100],
            ),
            "required_field_cell_presence_rate": _metric(
                "Share of required schema field cells that contain a value.",
                "non-empty required field cells / (parsed samples * required field count)",
                present_fields, complete_field_cells,
                present_fields / complete_field_cells if complete_field_cells else 0.0,
                "all parseable records before duplicate removal", missing[:100],
            ),
            "parseable_sample_rate": _metric(
                "Share of nonblank input records parsed as JSON objects.",
                "parsed JSON objects / nonblank input records", count, nonblank_line_count,
                parseable_rate, "input file", ["parse_issues: %d" % parse_error_count],
            ),
            "necessary_label_coverage": _metric(
                "Share of parsed SFT records with a non-empty assistant target.", "records with assistant target / parsed records",
                task_labelled, count, task_labelled / count if count else 0.0,
                "all parseable JSON records", [],
            ),
        },
        "consistency": {
            "schema_consistency_rate": _metric(
                "Share of parsed records with string sample_id, instruction, and output fields.",
                "schema-valid records / parsed records", schema_valid, count,
                schema_valid / count if count else 0.0, "all parseable JSON records",
                ["invalid_sample_ids: %d" % dedup_report.get("sample_id_conflict_count", 0)],
            ),
            "answer_conflict_groups": _metric(
                "Repeated normalized questions with multiple answer variants; suspected conflicts require review.",
                "conflict groups / groups with repeated normalized questions", conflict_group_count, repeated_question_groups,
                conflict_group_count / repeated_question_groups if repeated_question_groups else None,
                "all parseable records before deduplication",
                dedup_report.get("answer_conflicts", [])[:100],
                "No authoritative answer key or human adjudication is available; this is not an error count.",
            ),
            "cross_modal_match_rate": _metric(
                "Share of paired cross-modal records whose linked content is aligned.", "N/A", None, None, None,
                "EduChat text-only sample", [], "No paired image/audio assets are present in this text-only source.",
            ),
            "reviewer_agreement_rate": _metric(
                "Agreement rate between independent human reviewers.", "N/A", None, None, None,
                "all records", [], "No independent double-review labels are available.",
            ),
        },
        "diversity": {
            "category_coverage": category_diversity,
            "category_distribution": topic_result,
            "normalized_category_entropy": _metric(
                "Normalized Shannon entropy over observed inferred categories; heuristic labels only.",
                "-sum(p[c] * ln(p[c])) / ln(observed category count)",
                round(entropy, 8), round(math.log(len(topics)), 8) if len(topics) > 1 else 0,
                round(normalized_entropy, 8), "deduplicated, non-quarantined parsed candidates",
                [], "No categories observed." if not topics else None,
            ),
            "long_tail_category_coverage": _metric(
                "Count of inferred categories whose share is at or below the configured long-tail threshold.",
                f"count(categories with share <= {long_tail_threshold})", len(long_tail_topics), len(topics),
                {"count": len(long_tail_topics), "categories": sorted(long_tail_topics), "share_threshold": long_tail_threshold},
                "deduplicated, non-quarantined parsed candidates", [],
            ),
            "near_duplicate_ratio": _metric(
                "Unique parsed records flagged as near-duplicate candidates.",
                "near-duplicate sample count / parsed sample count",
                dedup_report.get("near_duplicate_sample_count", 0), count,
                dedup_report.get("near_duplicate_sample_count", 0) / count if count else 0.0,
                "all parseable records before exact/normalized duplicate removal",
                dedup_report.get("near_duplicate_pairs", [])[:100],
            ),
        },
        "unbiasedness": {
            "reference_distribution_difference": unbiasedness,
            "source_distribution": {
                "definition": "Counts and shares of records by source_id.", "formula": "count(source_id) / parsed sample count",
                "numerator": count, "denominator": count, "value": dict(sorted(Counter(str(r.get("source_id", "unknown")) for r in records).items())),
                "scope": "all parseable records", "anomalies": [], "not_measurable_reason": None,
                "counts": dict(sorted(Counter(str(r.get("source_id", "unknown")) for r in records).items())),
                "source_count": len({str(r.get("source_id", "unknown")) for r in records}),
            },
        },
        "timeliness": {
            "published_at_coverage": _metric(
                "Share of parsed records with a valid published_at timestamp.",
                "valid publication timestamps / parsed records", date_covered, count, date_coverage,
                "all parseable records", time_anomalies[:100],
            ),
            "data_age_days": {
                "definition": "Age from published_at to processing time.", "formula": "processed_at - published_at",
                "numerator": len(ages), "denominator": count,
                "value": ( {"min": round(min(ages), 2), "median": round(sorted(ages)[len(ages)//2], 2),
                            "max": round(max(ages), 2)} if ages else None),
                "scope": "records with valid published_at", "anomalies": future_ids[:100],
                "not_measurable_reason": None if ages else "No valid publication timestamps.",
            },
            "confirmed_expired_ratio": _metric(
                "Share of records confirmed expired using an explicit validity date.",
                "confirmed expired records / records with verifiable validity", None, None,
                None, "all parsed records", [], "Publication age alone does not establish expiration; no validity evidence was supplied.",
            ),
            "older_than_threshold_ratio": _metric(
                "Share with publication age above the configured threshold; age does not prove expiration.",
                f"known dates older than {stale_days} days / records with valid published_at",
                known_expired if date_covered else None, date_covered if date_covered else None,
                expired_value, "records with valid published_at", [], expired_reason,
            ),
            "time_anomalies": {
                "definition": "Invalid or future publication timestamps.", "formula": "count(invalid or future timestamps)",
                "numerator": len(time_anomalies) + len(future_ids), "denominator": count,
                "value": {"invalid_date_count": len(time_anomalies), "future_date_count": len(future_ids)},
                "scope": "all parseable records", "anomalies": (time_anomalies + future_ids)[:100],
                "not_measurable_reason": None,
            },
            "version_conflict_count": dedup_report.get("sample_id_conflict_count", 0),
        },
    }
    definitions_version = "preproject-five-dimensions-v1"
    for dimension, section in metrics.items():
        if not isinstance(section, dict):
            continue
        for metric_name, item in section.items():
            if not isinstance(item, dict) or "value" not in item:
                continue
            issue_ids: set[str] = set()
            for anomaly in item.get("anomalies", []):
                if isinstance(anomaly, dict):
                    if anomaly.get("sample_id"):
                        issue_ids.add(str(anomaly["sample_id"]))
                    issue_ids.update(str(value) for value in anomaly.get("sample_ids", []) if value)
            item.update({
                "dimension": dimension,
                "metric": metric_name,
                "status": "measured" if item.get("value") is not None else "not_measurable",
                "reason": item.get("not_measurable_reason"),
                "method": item.get("formula") or item.get("definition") or "rule_based_v1",
                "version": definitions_version,
                "issue_sample_ids": sorted(issue_ids),
            })
    return {
        "definitions_version": definitions_version,
        "scope": {
            "parsed_sample_count": count,
            "nonblank_input_line_count": nonblank_line_count,
            "parse_error_count": parse_error_count,
            "near_duplicate_policy": "review only; no automatic deletion",
        },
        "metrics": metrics,
    }
