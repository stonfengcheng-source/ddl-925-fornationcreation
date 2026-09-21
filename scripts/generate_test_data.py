"""
生成6种模型的测试数据（CSV格式），每种分为节点A和节点B两份
所有数据集均为隐私敏感的表格数据，符合联邦学习"数据不出域"场景

运行: python scripts/generate_test_data.py
输出: test_data/<model_type>_nodeA.csv, test_data/<model_type>_nodeB.csv
"""

import os
import sys
import numpy as np
import pandas as pd

# 输出目录
OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "test_data")
os.makedirs(OUT_DIR, exist_ok=True)

# sample_data 目录（由 generate_csv_datasets.py 生成的完整 CSV）
FL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "federated-learning", "sample_data")


def save_split_csv(df, model_type, split_ratio=0.6):
    """将 DataFrame 随机分为两份并保存为 CSV"""
    n = len(df)
    indices = np.random.RandomState(42).permutation(n)
    split = int(n * split_ratio)
    idxA, idxB = indices[:split], indices[split:]

    for suffix, idx in [("nodeA", idxA), ("nodeB", idxB)]:
        path = os.path.join(OUT_DIR, f"{model_type}_{suffix}.csv")
        df.iloc[idx].to_csv(path, index=False)
        print(f"  {suffix}: {len(idx)} 条 -> {path}")


def gen_from_sample(model_type, label):
    """从 sample_data 中读取完整 CSV 并分割"""
    csv_path = os.path.join(FL_DIR, f"{model_type}.csv")
    if not os.path.exists(csv_path):
        print(f"  [跳过] {csv_path} 不存在，请先运行 federated-learning/generate_csv_datasets.py")
        return
    df = pd.read_csv(csv_path)
    print(f"\n[{model_type}] {label} - {len(df)} 条, {len(df.columns)-1} 特征")
    save_split_csv(df, model_type)


if __name__ == "__main__":
    print("=" * 60)
    print("  生成6种模型的测试数据（CSV格式，每种分为节点A/B两份）")
    print("=" * 60)
    gen_from_sample("breast_cancer", "乳腺癌诊断数据")
    gen_from_sample("diabetes", "糖尿病预测数据")
    gen_from_sample("heart_disease", "心脏病诊断数据")
    gen_from_sample("credit_score", "信用评估数据")
    gen_from_sample("adult_income", "收入预测数据")
    gen_from_sample("bank_marketing", "银行营销数据")
    print("\n" + "=" * 60)
    print(f"  所有测试数据已生成到: {OUT_DIR}")
    print("=" * 60)
