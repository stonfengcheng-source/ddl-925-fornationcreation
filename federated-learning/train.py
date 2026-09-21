"""
本地训练与评估函数
供 Flower Client 调用，执行本地模型训练和测试
"""

import torch
import torch.nn as nn
from torch.utils.data import DataLoader


def train_one_epoch(
    model: nn.Module,
    trainloader: DataLoader,
    optimizer: torch.optim.Optimizer,
    device: torch.device,
    task_type: str = "classification",
) -> float:
    """
    训练一个 epoch

    参数:
        task_type: "classification" 或 "regression"
    返回: 平均训练损失
    """
    model.train()
    criterion = nn.CrossEntropyLoss() if task_type == "classification" else nn.MSELoss()
    total_loss = 0.0
    num_batches = 0

    for X_batch, y_batch in trainloader:
        X_batch, y_batch = X_batch.to(device), y_batch.to(device)

        optimizer.zero_grad()
        outputs = model(X_batch)
        loss = criterion(outputs, y_batch)
        loss.backward()
        optimizer.step()

        total_loss += loss.item()
        num_batches += 1

    avg_loss = total_loss / max(num_batches, 1)
    return avg_loss


def evaluate(
    model: nn.Module,
    testloader: DataLoader,
    device: torch.device,
    task_type: str = "classification",
) -> tuple[float, float]:
    """
    在测试集上评估模型

    参数:
        task_type: "classification" 或 "regression"
    返回:
        分类: (平均损失, 准确率)
        回归: (平均损失, R²分数)
    """
    model.eval()
    criterion = nn.CrossEntropyLoss() if task_type == "classification" else nn.MSELoss()
    total_loss = 0.0
    correct = 0
    total = 0
    all_targets = []
    all_predictions = []

    with torch.no_grad():
        for X_batch, y_batch in testloader:
            X_batch, y_batch = X_batch.to(device), y_batch.to(device)

            outputs = model(X_batch)
            loss = criterion(outputs, y_batch)

            total_loss += loss.item() * y_batch.size(0)
            total += y_batch.size(0)

            if task_type == "classification":
                _, predicted = torch.max(outputs, 1)
                correct += (predicted == y_batch).sum().item()
            else:
                all_targets.extend(y_batch.cpu().numpy())
                all_predictions.extend(outputs.cpu().numpy())

    avg_loss = total_loss / max(total, 1)

    if task_type == "classification":
        metric = correct / max(total, 1)  # accuracy
    else:
        # R² score for regression
        import numpy as np
        targets = np.array(all_targets)
        preds = np.array(all_predictions)
        ss_res = np.sum((targets - preds) ** 2)
        ss_tot = np.sum((targets - np.mean(targets)) ** 2)
        metric = 1 - (ss_res / max(ss_tot, 1e-8))  # R²

    return avg_loss, metric
