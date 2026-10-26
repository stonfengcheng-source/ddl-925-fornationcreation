"""把评测错误样本整理为可回流给任务二、任务三的统一 JSONL。"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from common import get_text, parse_bool, read_jsonl, write_jsonl


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--model", default="ours")
    parser.add_argument("--output", default="experiments/module4/results/ours_badcases.jsonl")
    args = parser.parse_args()

    rows = read_jsonl(args.input)
    badcases = []
    for index, row in enumerate(rows, 1):
        row_model = str(row.get("model", args.model)).strip().lower()
        if row_model != args.model.lower():
            continue
        correct_value = row.get("correct", row.get("is_correct"))
        if correct_value is None:
            prediction = get_text(row, ["prediction", "pred", "output"])
            reference = get_text(row, ["reference", "gold", "answer", "target"])
            if not prediction or not reference:
                continue
            is_correct = " ".join(prediction.casefold().split()) == " ".join(reference.casefold().split())
        else:
            is_correct = parse_bool(correct_value)
        if is_correct:
            continue
        badcases.append(
            {
                "sample_id": str(row.get("item_id") or row.get("id") or f"{args.model}-{index}"),
                "model": args.model,
                "benchmark": str(row.get("benchmark") or row.get("dataset") or "unknown"),
                "subject": str(row.get("subject") or row.get("category") or "unknown"),
                "question": get_text(row, ["question", "prompt", "instruction"]),
                "prediction": get_text(row, ["prediction", "pred", "output"]),
                "reference": get_text(row, ["reference", "gold", "answer", "target"]),
                "failure_type": "benchmark_incorrect",
                "recommended_action": "复查清洗、答案正确性、题答一致性和该学科覆盖情况",
            }
        )

    output_path = Path(args.output)
    write_jsonl(output_path, badcases)
    subjects = Counter(row["subject"] for row in badcases)
    summary = {
        "model": args.model,
        "badcase_count": len(badcases),
        "subject_distribution": dict(subjects.most_common()),
        "output": str(output_path.resolve()),
    }
    summary_path = output_path.with_suffix(".summary.json")
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{args.model} Bad Case: {len(badcases)}")
    for subject, count in subjects.most_common():
        print(f"  {subject}: {count}")
    print(f"回流文件: {output_path.resolve()}")


if __name__ == "__main__":
    main()
