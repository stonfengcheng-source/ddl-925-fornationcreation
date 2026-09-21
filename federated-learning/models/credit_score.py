"""
信用评估模型 — 三层全连接网络
输入: 20维特征 (UCI German Credit) → 输出: 2类(信用良好/信用不良)
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class CreditScoreNet(nn.Module):
    """信用评估模型 — 三层全连接网络"""

    def __init__(self, input_dim: int = 20, num_classes: int = 2):
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
