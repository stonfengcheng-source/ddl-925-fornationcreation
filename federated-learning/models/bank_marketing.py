"""
银行营销预测模型 — 三层全连接网络
输入: 16维特征 (UCI Bank Marketing) → 输出: 2类(未订阅/已订阅)
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class BankMarketingNet(nn.Module):
    """银行营销预测模型 — 三层全连接网络"""

    def __init__(self, input_dim: int = 16, num_classes: int = 2):
        super().__init__()
        self.fc1 = nn.Linear(input_dim, 128)
        self.fc2 = nn.Linear(128, 64)
        self.fc3 = nn.Linear(64, num_classes)
        self.dropout = nn.Dropout(0.3)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = F.relu(self.fc1(x))
        x = self.dropout(x)
        x = F.relu(self.fc2(x))
        x = self.dropout(x)
        x = self.fc3(x)
        return x
