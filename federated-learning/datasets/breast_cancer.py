"""
乳腺癌数据集加载与分区
从 CSV 文件加载数据，按节点ID进行横向分区
"""

import os
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import torch
from torch.utils.data import DataLoader, TensorDataset

# 默认 CSV 路径
_DEFAULT_CSV = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sample_data", "breast_cancer.csv")


def load_breast_cancer_partition(node_id: int, num_nodes: int = 2, batch_size: int = 32, csv_path: str = None):
    """
    加载并分区乳腺癌数据集（从CSV文件）

    返回: (trainloader, testloader, num_train, num_test)
    """
    path = csv_path or _DEFAULT_CSV
    df = pd.read_csv(path)

    X = df.drop(columns=["target"]).values.astype(np.float32)
    y = df["target"].values.astype(np.int64)

    scaler = StandardScaler()
    X = scaler.fit_transform(X)

    # 按节点ID切分数据
    total_samples = len(X)
    samples_per_node = total_samples // num_nodes
    start_idx = node_id * samples_per_node
    end_idx = total_samples if node_id == num_nodes - 1 else start_idx + samples_per_node

    X_node = X[start_idx:end_idx]
    y_node = y[start_idx:end_idx]

    X_train, X_test, y_train, y_test = train_test_split(
        X_node, y_node, test_size=0.2, random_state=42, stratify=y_node
    )

    train_ds = TensorDataset(torch.FloatTensor(X_train), torch.LongTensor(y_train))
    test_ds = TensorDataset(torch.FloatTensor(X_test), torch.LongTensor(y_test))

    trainloader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
    testloader = DataLoader(test_ds, batch_size=batch_size, shuffle=False)

    print(f"[节点 {node_id}] 乳腺癌数据集 | 训练: {len(X_train)} | 测试: {len(X_test)}")
    return trainloader, testloader, len(X_train), len(X_test)
