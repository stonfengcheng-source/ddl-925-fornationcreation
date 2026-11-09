"""Render a human-readable report using actual governance evidence only."""
from __future__ import annotations
import hashlib
from typing import Any

DIMENSIONS = {"completeness":"完整性", "consistency":"一致性", "diversity":"多元性", "unbiasedness":"无偏性", "timeliness":"时效性"}
NAMES = {"valid_sft_structure_rate":"问答结构有效率", "required_field_completeness_rate":"必要字段完整样本率", "required_field_cell_presence_rate":"必要字段填充率", "parseable_sample_rate":"记录可解析率", "necessary_label_coverage":"回答字段覆盖率", "schema_consistency_rate":"结构一致率", "answer_conflict_groups":"疑似冲突组占比", "cross_modal_match_rate":"跨模态匹配率", "reviewer_agreement_rate":"复核者一致率", "category_coverage":"主题覆盖率", "category_distribution":"主题估计分布", "normalized_category_entropy":"主题分布归一化熵", "long_tail_category_coverage":"长尾主题覆盖", "near_duplicate_ratio":"近重复候选比例", "reference_distribution_difference":"参考分布差异", "source_distribution":"来源分布", "published_at_coverage":"发布时间覆盖率", "data_age_days":"数据时间跨度", "confirmed_expired_ratio":"确认过期比例", "older_than_threshold_ratio":"超过时间阈值比例", "time_anomalies":"时间异常", "version_conflict_count":"版本冲突数"}
RATIOS = {"valid_sft_structure_rate", "required_field_completeness_rate", "required_field_cell_presence_rate", "parseable_sample_rate", "necessary_label_coverage", "schema_consistency_rate", "answer_conflict_groups", "cross_modal_match_rate", "reviewer_agreement_rate", "category_coverage", "near_duplicate_ratio", "published_at_coverage", "confirmed_expired_ratio", "older_than_threshold_ratio"}
NA_REASONS = {"reference_distribution_difference":"缺少可靠参考分布，不能判断无偏性。", "data_age_days":"缺少有效发布时间，不能判断数据年龄。", "confirmed_expired_ratio":"缺少明确有效期证据，不能判断是否过期。", "older_than_threshold_ratio":"缺少有效发布时间，不能判断是否超过时间阈值。", "cross_modal_match_rate":"纯文本数据缺少图像或音频配对。", "reviewer_agreement_rate":"缺少独立双人复核记录。", "answer_conflict_groups":"没有可比较的重复问题组。"}


def _value(name: str, value: Any) -> str:
    if value is None: return "N/A（暂无可靠评价依据）"
    if isinstance(value, dict):
        translated = {"min":"最小", "median":"中位", "max":"最大", "invalid_date_count":"无效日期", "future_date_count":"未来日期", "count":"数量", "categories":"类别", "share_threshold":"占比阈值", "language":"语言", "mathematics":"数学", "science":"科学", "programming":"编程", "other_unclassified":"其他或未分类"}
        return "；".join(f"{translated.get(str(key), str(key))}：{'、'.join(translated.get(str(entry), str(entry)) for entry in item) if isinstance(item, list) else item}" for key,item in value.items())
    if isinstance(value, (int,float)) and not isinstance(value, bool):
        return f"{value * 100:.2f}%" if name in RATIOS else f"{value:.6g}"
    return str(value)


def render_governance_report(source: dict[str, Any], stats: dict[str, Any], quality: dict[str, Any], outcome: dict[str, Any], records: list[dict[str, Any]]) -> str:
    actions = outcome["actions"]; engineering = outcome["engineering"]; publication = outcome["publication"]
    def safe(value: Any) -> str:
        return str(value or "未提供").replace("|", "\\|").replace("\n", " ")[:180]
    rows = ["# 数据治理质量报告", "", "## 执行摘要", "",
            f"本次读取 {stats.get('input_nonblank_lines', 'N/A')} 条记录，处理 {stats.get('raw_sample_count', 'N/A')} 条，合格候选 {engineering['candidate_count']} 条，待复核 {engineering['pending_review']} 条。",
            f"结构转换 {actions['structure_conversion_records']} 条，字段规范化 {actions['field_normalization_records']} 条，重复剔除 {actions['duplicate_removed_records']} 条，隐私处理 {actions['privacy_masked_records']} 条。各类动作可能重叠。", "",
            "## 数据来源与使用边界", "", f"- 数据集：{safe(source.get('dataset_id'))}", f"- 来源：{safe(source.get('source_url'))}",
            f"- 来源版本：{safe(source.get('revision'))}；许可：{safe(source.get('license'))}", "- 来源声明不等于已核验，也不自动授予训练或发布权。", "",
            "## 输入与输出统计", "", f"- 可解析记录：{stats.get('raw_sample_count', 'N/A')}；解析失败：{stats.get('parse_error_count', 'N/A')}",
            f"- 合格候选：{engineering['candidate_count']}；待复核：{engineering['pending_review']}；隔离：{stats.get('quarantine_count', 'N/A')}；剔除：{stats.get('drop_count', 'N/A')}", "",
            "## 主要治理发现", "", f"- 精确重复：{stats.get('exact_duplicate_count', 'N/A')}；归一化重复：{stats.get('normalized_duplicate_count', 'N/A')}；近重复候选：{stats.get('near_duplicate_sample_count', 'N/A')}",
            f"- 隐私规则命中：{actions['privacy_hit_events']} 次；残留复检：{stats.get('privacy_residual_count', 'N/A')} 次。", "- 文本语义错误未由本流程自动修复。", "",
            "## 典型处理案例", ""]
    examples = []
    for row in records:
        reasons = row.get("processing_reasons") or []
        flags = []
        if any(value and str(value) != key for key,value in (row.get("source_field_mapping") or {}).items()): flags.append("结构转换")
        if (row.get("cleaning_audit") or {}).get("action") == "repair": flags.append("字段规范化")
        if row.get("duplicate_type"): flags.append("重复处理")
        if any((row.get("privacy_hits") or {}).values()): flags.append("隐私规则命中")
        if flags:
            token = hashlib.sha256(str(row.get("sample_id", "")).encode()).hexdigest()[:10]
            examples.append(f"- 案例标识 {token}：{'、'.join(flags)}；准入状态 {safe(row.get('processing_status'))}。")
        if len(examples) == 5: break
    rows += examples or ["- 本批次没有可列举的结构转换或规则命中案例。"]
    rows += ["", "案例内容及处理前后差异请在平台脱敏样本视图中查看。", "", "## 五维质量结果", ""]
    for dimension, section in quality.get("metrics", {}).items():
        rows += [f"### {DIMENSIONS.get(dimension, '其他质量指标')}", "", "| 指标 | 实际结果 | 分子 / 分母 | 评价限制 |", "|---|---|---|---|"]
        for key, item in section.items():
            if key not in NAMES: continue
            if isinstance(item, dict) and "value" in item:
                value, numerator, denominator = item.get("value"), item.get("numerator"), item.get("denominator")
            elif key == "category_distribution" and isinstance(item, dict): value, numerator, denominator = item.get("counts", {}), None, None
            elif isinstance(item, (int,float)): value, numerator, denominator = item, None, None
            else: continue
            limitation = NA_REASONS.get(key, "缺少可靠评价依据。") if value is None else ("规则估计，不是人工标签。" if key in {"category_distribution", "category_coverage", "normalized_category_entropy", "long_tail_category_coverage"} else "")
            rows.append(f"| {NAMES[key]} | {safe(_value(key,value))} | {numerator if numerator is not None else 'N/A'} / {denominator if denominator is not None else 'N/A'} | {limitation} |")
        rows.append("")
    rows += ["## 未解决的问题", "", *[f"- {safe(reason)}" for reason in publication["reasons"]], "",
             "## 工程质量认定", "", engineering["summary"], engineering["scope"], "",
             "## 专业内容认定", "", "尚未进行专业内容正确性认证；工程规则与人工处理记录不等于专家认证。", "",
             "## 发布授权认定", "", "满足当前发布条件。" if publication["release_eligible"] else "尚不满足发布条件。",
             f"来源版本核验：{'已核验' if publication['revision_verified'] else '未核验'}；许可核验：{'已核验' if publication['license_verified'] else '未核验'}；再分发授权：{'已确认' if publication['redistribution_authorized'] else '未确认'}。", "",
             "## 处理后数据及相关文件", "", "可在当前任务的版本与交付页面预览和下载处理后数据、合格候选及版本清单。", ""]
    return "\n".join(rows)
