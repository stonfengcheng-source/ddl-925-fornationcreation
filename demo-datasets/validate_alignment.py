# -*- coding: utf-8 -*-
"""
对接校验：验证 demo-datasets 下的两份 JSONL 是否可被平台按 data_type=json 入库。

仅用标准库，不依赖项目环境；在仓库根目录或本目录均可运行：
    python demo-datasets/validate_alignment.py
"""
import json
import os
import sys

REQUIRED_KEYS = [
    "sample_id", "modality", "raw_text", "meta", "clean_text",
    "masked_text", "hash", "flags", "decision", "version", "stage_trace",
]

# 数据集定义：(相对本文件的路径, 注册名, 领域标签)
DATASETS = [
    ("education-synthetic/raw_5k.jsonl", "教育合成语料-5k", ["synthetic", "education", "task2-demo"]),
    ("government-synthetic/gov_synthetic_300.jsonl", "政务合成演示语料-300", ["synthetic", "government", "task2-demo"]),
]


def validate_file(rel_path):
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, rel_path)
    if not os.path.exists(path):
        return None, f"文件不存在: {path}"
    rows = 0
    bad_lines = 0
    key_sets = set()
    sample_keys = None
    with open(path, encoding="utf-8") as f:
        for ln, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                bad_lines += 1
                continue
            rows += 1
            ks = frozenset(obj.keys())
            key_sets.add(ks)
            if sample_keys is None:
                sample_keys = sorted(obj.keys())
    if bad_lines:
        return None, f"{bad_lines} 行 JSON 解析失败"
    if rows == 0:
        return None, "空文件"
    # 检查所有行是否都含齐 REQUIRED_KEYS
    missing = set()
    for ks in key_sets:
        missing |= (set(REQUIRED_KEYS) - ks)
    if missing:
        return None, f"部分行缺少字段: {sorted(missing)}"
    column_count = len(REQUIRED_KEYS)
    payload = {
        "data_type": "json",
        "row_count": rows,
        "column_count": column_count,
        "columns_info": REQUIRED_KEYS,
    }
    return payload, None


def main():
    print("=== 对接校验（Schema v1 -> 平台 DatasetCreate）===\n")
    ok = True
    for rel, name, tags in DATASETS:
        payload, err = validate_file(rel)
        if err:
            ok = False
            print(f"[FAIL] {name} ({rel})\n        {err}")
            continue
        payload["name"] = name
        payload["tags"] = tags
        payload["description"] = f"{name}，license=synthetic，任务二演示输入"
        print(f"[OK]   {name} ({rel})")
        print(f"        row_count={payload['row_count']}  column_count={payload['column_count']}  data_type={payload['data_type']}")
    print()
    if ok:
        print("结论：两份数据集均为合法 JSONL，字段齐备，可作为 data_type=json 数据集注册到平台。")
        return 0
    print("结论：存在不通过项，请检查上方 FAIL。")
    return 1


if __name__ == "__main__":
    sys.exit(main())
