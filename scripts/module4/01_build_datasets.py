"""从上游结果生成五组等量训练集与可追溯清单。"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List

from common import (
    DISPLAY_NAMES,
    TRAIN_VARIANTS,
    deduplicate_content,
    ensure_unique_ids,
    file_sha256,
    normalize_for_training,
    parse_bool,
    read_jsonl,
    sample_label,
    write_jsonl,
)


def score_value(row: Dict[str, Any], field: str) -> float:
    try:
        return float(row.get(field, 0) or 0)
    except (TypeError, ValueError):
        return 0.0


def composite_score(row: Dict[str, Any], args: argparse.Namespace) -> float:
    return (
        score_value(row, args.score_field) * args.quality_weight
        + score_value(row, args.task_match_field) * args.task_match_weight
        + score_value(row, args.coverage_field) * args.coverage_weight
    )


def sample_n(rows: Iterable[Dict[str, Any]], count: int, seed: int, group_name: str) -> List[Dict[str, Any]]:
    rows = list(rows)
    if len(rows) < count:
        raise ValueError(f"{group_name} 可用样本仅 {len(rows)} 条，少于要求的 {count} 条")
    random.Random(seed).shuffle(rows)
    return rows[:count]


def score_top_n(
    rows: Iterable[Dict[str, Any]], count: int, score_field: str, group_name: str
) -> List[Dict[str, Any]]:
    """按单一大模型总分取 Top-K，不使用规则、任务匹配或覆盖平衡。"""
    rows = list(rows)
    if len(rows) < count:
        raise ValueError(f"{group_name} 可用样本仅 {len(rows)} 条，少于要求的 {count} 条")
    rows.sort(key=lambda row: (-score_value(row, score_field), str(row.get("id", ""))))
    return rows[:count]


def balanced_top_n(
    rows: Iterable[Dict[str, Any]], count: int, seed: int, args: argparse.Namespace
) -> List[Dict[str, Any]]:
    """各学科轮流取综合分最高样本，避免 Ours 被单一学科占满。"""
    rows = list(rows)
    if len(rows) < count:
        raise ValueError(f"Ours 可用 keep 样本仅 {len(rows)} 条，少于 {count} 条")
    groups: dict[str, list[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        group = subject_value(row, args.group_field)
        groups[group].append(row)
    for group_rows in groups.values():
        group_rows.sort(
            key=lambda row: (-composite_score(row, args), str(row.get("id", "")))
        )
    group_names = sorted(groups)
    random.Random(seed).shuffle(group_names)
    selected: List[Dict[str, Any]] = []
    while len(selected) < count:
        added = False
        for group_name in group_names:
            if groups[group_name] and len(selected) < count:
                selected.append(groups[group_name].pop(0))
                added = True
        if not added:
            break
    return selected


def id_digest(rows: Iterable[Dict[str, Any]]) -> str:
    ids = sorted(str(row.get("id", "")) for row in rows)
    return hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest()


def subject_value(row: Dict[str, Any], field: str) -> str:
    meta = row.get("meta")
    nested_value = meta.get(field) if isinstance(meta, dict) else None
    return str(row.get(field) or nested_value or "unknown").strip()


def subject_counts(rows: Iterable[Dict[str, Any]], field: str) -> Dict[str, int]:
    counts = Counter(subject_value(row, field) for row in rows)
    return dict(sorted(counts.items()))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", required=True, help="原始候选池 JSONL")
    parser.add_argument("--evaluated", default="", help="可选：规则与大模型质量评价结果 JSONL，留空则跳过对应组")
    parser.add_argument(
        "--datajuicer",
        default="",
        help="可选：Data-Juicer 独立处理后的候选池 JSONL，留空则跳过该组",
    )
    parser.add_argument("--out-dir", default="experiments/module4/data")
    parser.add_argument("--n", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--rule-field", default="rule_pass")
    parser.add_argument("--decision-field", default="decision")
    parser.add_argument("--score-field", default="quality_score")
    parser.add_argument("--llm-score-field", default="quality_score")
    parser.add_argument("--task-match-field", default="task_match_score")
    parser.add_argument("--coverage-field", default="coverage_score")
    parser.add_argument("--group-field", default="subject")
    parser.add_argument("--quality-weight", type=float, default=0.7)
    parser.add_argument("--task-match-weight", type=float, default=0.2)
    parser.add_argument("--coverage-weight", type=float, default=0.1)
    args = parser.parse_args()

    if args.n <= 0:
        raise ValueError("--n 必须大于 0")
    if args.quality_weight + args.task_match_weight + args.coverage_weight <= 0:
        raise ValueError("三个评分权重之和必须大于 0")

    raw = ensure_unique_ids(read_jsonl(args.raw), "Raw 候选池")
    evaluated = ensure_unique_ids(read_jsonl(args.evaluated), "质量评价结果") if args.evaluated else []
    datajuicer = ensure_unique_ids(read_jsonl(args.datajuicer), "Data-Juicer 结果") if args.datajuicer else []
    for row in [*raw, *evaluated, *datajuicer]:
        normalize_for_training(row)

    rule_pool = [row for row in evaluated if parse_bool(row.get(args.rule_field))]
    rule_pool, rule_duplicates = deduplicate_content(rule_pool)

    # LLM-only 只按大模型给出的单一总分取 Top-K，不读取规则结果，也不做覆盖平衡。
    llm_pool, llm_duplicates = deduplicate_content(evaluated)

    # Data-Juicer 组必须来自其独立处理输出，避免把 Rule 组冒充为开源基线。
    datajuicer_pool, datajuicer_duplicates = deduplicate_content(datajuicer)

    ours_pool = [
        row
        for row in evaluated
        if parse_bool(row.get(args.rule_field))
        and str(row.get(args.decision_field, "")).strip().lower() == "keep"
    ]
    ours_pool, ours_duplicates = deduplicate_content(ours_pool)

    # 检查全部输入后再抽样，避免只报第一组不足，掩盖其他输入仍是测试文件。
    pools = {"raw": raw, "rule": rule_pool, "llm_only": llm_pool,
             "datajuicer": datajuicer_pool, "ours": ours_pool}
    pending = {}
    if not args.evaluated:
        pending.update({name: "尚未提供质量评价结果" for name in ("rule", "llm_only", "ours")})
    else:
        if not any(args.rule_field in row for row in evaluated):
            pending.update({name: f"尚未提供 {args.rule_field} 规则结果" for name in ("rule", "ours")})
        if not any(args.llm_score_field in row for row in evaluated):
            pending["llm_only"] = f"尚未提供 {args.llm_score_field} 评分"
        if not any(args.decision_field in row for row in evaluated):
            pending["ours"] = f"尚未提供 {args.decision_field} 筛选决策"
    if not args.datajuicer:
        pending["datajuicer"] = "尚未提供 Data-Juicer 独立处理结果"
    pools = {name: pool for name, pool in pools.items() if name not in pending}
    sources = {"raw": args.raw, "rule": args.evaluated, "llm_only": args.evaluated,
               "datajuicer": args.datajuicer, "ours": args.evaluated}
    print(f"输入数量：原始候选 {len(raw)} 条；质量评价 {len(evaluated)} 条；Data-Juicer 结果 {len(datajuicer)} 条")
    print("各组可用数量：" + "；".join(f"{DISPLAY_NAMES[name]} {len(pool)} 条" for name, pool in pools.items()))
    for name, reason in pending.items():
        print(f"[待接入] {DISPLAY_NAMES[name]}：{reason}，本次留空")
    insufficient = [
        f"{DISPLAY_NAMES[name]} 可用 {len(pool)} 条（来源：{sources[name]}）"
        for name, pool in pools.items() if len(pool) < args.n
    ]
    if insufficient:
        raise ValueError(
            f"无法生成每组 {args.n} 条数据：\n" + "\n".join(insufficient)
            + "\n请提供足量的对应输入数据。更换原始候选池不会自动生成质量评价或 Data-Juicer 处理结果。"
        )

    # Raw 保留原始内容重复现象，只保证训练必需字段存在和 ID 唯一。
    raw_group = sample_n(raw, args.n, args.seed, "Raw")

    output_dir = Path(args.out_dir)
    label = sample_label(args.n)
    selected_groups = {"raw": raw_group}
    if "rule" in pools:
        selected_groups["rule"] = sample_n(rule_pool, args.n, args.seed, "Rule")
    if "llm_only" in pools:
        selected_groups["llm_only"] = score_top_n(llm_pool, args.n, args.llm_score_field, "LLM-only")
    if "datajuicer" in pools:
        selected_groups["datajuicer"] = sample_n(datajuicer_pool, args.n, args.seed, "Data-Juicer")
    if "ours" in pools:
        selected_groups["ours"] = balanced_top_n(ours_pool, args.n, args.seed, args)
    output_paths: dict[str, Path] = {}
    for name, rows in selected_groups.items():
        path = output_dir / f"{name}_{label}.jsonl"
        write_jsonl(path, [normalize_for_training(row) for row in rows])
        output_paths[name] = path

    audit_rows = []
    for name, rows in selected_groups.items():
        for rank, row in enumerate(rows, 1):
            audit_rows.append(
                {
                    "variant": name,
                    "rank": rank,
                    "id": str(row.get("id", "")),
                    "subject": subject_value(row, args.group_field),
                    "quality_score": score_value(row, args.score_field),
                    "task_match_score": score_value(row, args.task_match_field),
                    "coverage_score": score_value(row, args.coverage_field),
                    "selection_score": (
                        score_value(row, args.llm_score_field)
                        if name == "llm_only"
                        else composite_score(row, args) if name == "ours" else None
                    ),
                }
            )
    audit_path = output_dir / f"selection_audit_{label}.jsonl"
    write_jsonl(audit_path, audit_rows)

    manifest = {
        "schema_version": 1,
        "sample_count_per_variant": args.n,
        "seed": args.seed,
        "sources": {
            "raw": str(Path(args.raw).resolve()),
            "evaluated": str(Path(args.evaluated).resolve()) if args.evaluated else None,
            "datajuicer": str(Path(args.datajuicer).resolve()) if args.datajuicer else None,
        },
        "pending_variants": pending,
        "selection": {
            "raw": "固定随机抽样，保留原始内容重复",
            "rule": f"{args.rule_field}=true 后精确去重并随机抽样",
            "llm_only": f"不使用规则，仅按 {args.llm_score_field} 单一总分 Top-K",
            "datajuicer": "从 Data-Juicer 独立处理结果中精确去重并随机抽样",
            "ours": "规则通过且 decision=keep，按综合分与学科覆盖平衡选择",
            "score_weights": {
                args.score_field: args.quality_weight,
                args.task_match_field: args.task_match_weight,
                args.coverage_field: args.coverage_weight,
            },
            "group_field": args.group_field,
        },
        "candidate_counts": {
            "raw": len(raw),
            "rule_after_filter": len(rule_pool),
            "llm_only_after_dedup": len(llm_pool),
            "datajuicer_after_dedup": len(datajuicer_pool),
            "ours_after_filter": len(ours_pool),
            "rule_exact_duplicates_removed": rule_duplicates,
            "llm_only_exact_duplicates_removed": llm_duplicates,
            "datajuicer_exact_duplicates_removed": datajuicer_duplicates,
            "ours_exact_duplicates_removed": ours_duplicates,
        },
        "variants": {
            name: {
                "path": str(path.resolve()),
                "count": len(selected_groups[name]),
                "file_sha256": file_sha256(path),
                "ids_sha256": id_digest(selected_groups[name]),
                "subject_distribution": subject_counts(selected_groups[name], args.group_field),
            }
            for name, path in output_paths.items()
        },
        "selection_audit": str(audit_path.resolve()),
    }
    manifest_path = output_dir / f"dataset_manifest_{label}.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("生成完成：")
    for name in selected_groups:
        print(f"  {DISPLAY_NAMES[name]:11}: {len(selected_groups[name])} -> {output_paths[name]}")
    print(f"  清单 : {manifest_path}")
    print(f"输出目录: {output_dir.resolve()}")


if __name__ == "__main__":
    try:
        main()
    except ValueError as exc:
        raise SystemExit(f"数据生成失败：{exc}") from None
