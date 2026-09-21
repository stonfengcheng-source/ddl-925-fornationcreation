"""
糖尿病预测(回归) — MLP全连接网络
输入: 10维特征 (sklearn Diabetes) → 输出: 1维回归值
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class DiabetesMLP(nn.Module):
    """sklearn Diabetes 糖尿病预测回归MLP"""

    def __init__(self, input_dim: int = 10):
        super().__init__()
        self.fc1 = nn.Linear(input_dim, 64)
        self.fc2 = nn.Linear(64, 32)
        self.fc3 = nn.Linear(32, 1)
        self.dropout = nn.Dropout(0.2)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = F.relu(self.fc1(x))
        x = self.dropout(x)
        x = F.relu(self.fc2(x))
        x = self.dropout(x)
        x = self.fc3(x)
        return x.squeeze(-1)
