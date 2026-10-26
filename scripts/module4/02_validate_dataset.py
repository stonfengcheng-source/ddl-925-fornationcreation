"""校验五组训练数据的数量、结构、ID 与内容重复情况。"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from common import DISPLAY_NAMES, content_digest, dataset_variants, read_jsonl, sample_label

REQUIRED = ("id", "instruction", "output")


def validate(path: Path, expected: int, raw_variant: bool = False):
    rows = read_jsonl(path)
    errors: list[str] = []
    warnings: list[str] = []
    if len(rows) != expected:
        errors.append(f"样本数={len(rows)}，期望={expected}")
    ids = [str(row.get("id", "")).strip() for row in rows]
    missing_ids = sum(not sample_id for sample_id in ids)
    if missing_ids:
        errors.append(f"存在 {missing_ids} 条空 ID")
    duplicate_ids = [sample_id for sample_id, count in Counter(ids).items() if sample_id and count > 1]
    if duplicate_ids:
        errors.append(f"存在重复 ID，例如 {duplicate_ids[:5]}")

    for index, row in enumerate(rows, 1):
        for key in REQUIRED:
            if not str(row.get(key, "")).strip():
                errors.append(f"第 {index} 条缺少 {key}")
                break

    if not errors:
        hashes = [content_digest(row) for row in rows]
        duplicate_content = len(hashes) - len(set(hashes))
        if duplicate_content:
            message = f"存在 {duplicate_content} 条完全重复内容"
            if raw_variant:
                warnings.append(message + "；Raw 组保留该现象用于对照")
            else:
                errors.append(message)
    return rows, errors, warnings


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="experiments/module4/data")
    parser.add_argument("--n", type=int, default=2000)
    parser.add_argument("--report", default=None)
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    label = sample_label(args.n)
    report = {"expected_count": args.n, "equal_sample_count": True, "variants": {}}
    active, pending = dataset_variants(data_dir, args.n)
    report["pending_variants"] = pending
    for name, reason in pending.items():
        print(f"[待接入] {DISPLAY_NAMES[name]}：{reason}，本次不参与校验")
    counts = set()
    all_ok = True
    for variant in active:
        filename = f"{variant}_{label}.jsonl"
        path = data_dir / filename
        try:
            rows, errors, warnings = validate(path, args.n, raw_variant=variant == "raw")
        except (FileNotFoundError, ValueError) as exc:
            rows, errors, warnings = [], [str(exc)], []
        counts.add(len(rows))
        report["variants"][variant] = {
            "path": str(path.resolve()),
            "count": len(rows),
            "errors": errors,
            "warnings": warnings,
        }
        if errors:
            all_ok = False
            print(f"[FAIL] {DISPLAY_NAMES[variant]}：{filename}")
            for error in errors[:20]:
                print("  -", error)
        else:
            print(f"[OK] {DISPLAY_NAMES[variant]}：{filename}，{len(rows)} 条")
        for warning in warnings:
            print("  [WARN]", warning)

    report["equal_sample_count"] = len(counts) == 1 and counts == {args.n}
    if not report["equal_sample_count"]:
        all_ok = False
    report["passed"] = all_ok
    report_path = Path(args.report) if args.report else data_dir / f"validation_report_{label}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"校验报告: {report_path.resolve()}")
    raise SystemExit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
