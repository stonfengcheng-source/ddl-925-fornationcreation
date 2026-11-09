from data_pipeline.governance_outcome import summarize_governance
from data_pipeline.governance_report import render_governance_report


def _statistics():
    return {"input_nonblank_lines": 2, "raw_sample_count": 2, "final_retained_count": 2,
            "review_count": 0, "quarantine_count": 0, "parse_error_count": 0, "privacy_residual_count": 0,
            "stages": [{"stage": name, "status": "completed"} for name in ("read_schema", "deduplication", "privacy_and_rescan")],
            "five_dimensions": {"completeness": {"valid_sft_structure_rate": {"value": 1}, "required_field_completeness_rate": {"value": 1}}}}


def test_engineering_does_not_imply_professional_or_publication_approval():
    stats = _statistics()
    result = summarize_governance([], stats, {"release_eligible": False, "reasons": ["许可未核验"]})
    assert result["engineering"]["status"] == "passed"
    assert result["professional"]["status"] == "unverified"
    assert result["publication"]["status"] == "blocked"
    stats["five_dimensions"]["completeness"]["required_field_completeness_rate"]["value"] = .5
    assert summarize_governance([], stats, {})["engineering"]["status"] == "pending"
    del stats["five_dimensions"]
    assert summarize_governance([], stats, {})["engineering"]["status"] == "unknown"


def test_report_distinguishes_na_ratios_and_non_ratio_values():
    stats = _statistics()
    outcome = summarize_governance([], stats, {})
    quality = {"metrics": {"unbiasedness": {"reference_distribution_difference": {"value": None}},
                           "diversity": {"normalized_category_entropy": {"value": .75}},
                           "completeness": {"valid_sft_structure_rate": {"value": 1}}}}
    report = render_governance_report({}, stats, quality, outcome, [])
    assert "暂无可靠评价依据" in report and "0.75" in report and "100.00%" in report
    assert "专业内容认定" in report and "发布授权认定" in report
