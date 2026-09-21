"""
心脏病诊断模型 — 三层全连接网络
输入: 13维特征 (UCI Cleveland) → 输出: 2类(无心脏病/有心脏病)
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class HeartDiseaseNet(nn.Module):
    """心脏病诊断模型 — 三层全连接网络"""

    def __init__(self, input_dim: int = 13, num_classes: int = 2):
        super().__init__()
        self.fc1 = nn.Linear(input_dim, 64)
        self.fc2 = nn.Linear(64, 32)
        self.fc3 = nn.Linear(32, num_classes)
        self.dropout = nn.Dropout(0.3)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = F.relu(self.fc1(x))
        x = self.dropout(x)
        x = F.relu(self.fc2(x))
        x = self.dropout(x)
        x = self.fc3(x)
        return x
