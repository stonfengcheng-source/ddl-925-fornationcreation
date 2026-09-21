"""
Flower 客户端实现
每个数据提供方节点运行一个 FlowerClient 实例
负责：接收全局模型参数 → 本地训练 → 返回更新后的参数
"""

import sys
import os

_fl_dir = os.path.dirname(os.path.abspath(__file__))
if _fl_dir not in sys.path:
    sys.path.insert(0, _fl_dir)

import flwr as fl
import torch
import numpy as np
from collections import OrderedDict

from models import get_model_class, get_model_config
from datasets import load_partition as load_dataset_partition
from train import train_one_epoch, evaluate


class FlowerClient(fl.client.NumPyClient):
    """
    Flower 联邦学习客户端

    每个客户端代表一个数据提供方节点，持有自己的本地数据，
    接收服务端下发的全局模型参数，用本地数据训练后，
    只将模型参数（不是数据！）返回给服务端。
    """

    def __init__(self, node_id: int, num_nodes: int = 2, local_epochs: int = 3,
                 learning_rate: float = 0.001, batch_size: int = 32,
                 model_type: str = "breast_cancer"):
        super().__init__()
        self.node_id = node_id
        self.local_epochs = local_epochs
        self.learning_rate = learning_rate
        self.model_type = model_type
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # 获取模型配置
        model_info = get_model_config(model_type)
        self.task_type = model_info["task_type"]
        cfg = model_info["default_config"]

        # 初始化模型
        ModelClass = get_model_class(model_type)
        if model_type == "diabetes_mlp":
            self.model = ModelClass(input_dim=cfg.get("input_dim", 10)).to(self.device)
        else:
            self.model = ModelClass(input_dim=cfg.get("input_dim", 30), num_classes=cfg.get("num_classes", 2)).to(self.device)

        # 加载本节点的数据分区
        self.trainloader, self.testloader, self.num_train, self.num_test = \
            load_dataset_partition(model_type=model_type, node_id=node_id, num_nodes=num_nodes, batch_size=batch_size)

        print(f"[节点 {node_id}] 客户端初始化完成 | 模型: {model_info['name']} | 设备: {self.device}")

    def get_parameters(self, config):
        """将模型参数转为 NumPy 数组列表，发送给服务端"""
        return [val.cpu().numpy() for _, val in self.model.state_dict().items()]

    def set_parameters(self, parameters):
        """接收服务端下发的全局模型参数，加载到本地模型"""
        params_dict = zip(self.model.state_dict().keys(), parameters)
        state_dict = OrderedDict(
            {k: torch.tensor(v, dtype=torch.float32) for k, v in params_dict}
        )
        self.model.load_state_dict(state_dict, strict=True)

    def fit(self, parameters, config):
        """
        本地训练（Flower 每轮会调用这个方法）

        流程：
        1. 接收全局模型参数
        2. 用本地数据训练 local_epochs 轮
        3. 返回更新后的参数 + 训练样本数 + 训练指标
        """
        # 加载全局参数
        self.set_parameters(parameters)

        # 本地训练
        optimizer = torch.optim.Adam(
            self.model.parameters(), lr=self.learning_rate
        )

        total_loss = 0.0
        for epoch in range(self.local_epochs):
            loss = train_one_epoch(self.model, self.trainloader, optimizer, self.device, task_type=self.task_type)
            total_loss += loss

        avg_loss = total_loss / self.local_epochs
        print(f"[节点 {self.node_id}] 本地训练完成 | 平均损失: {avg_loss:.4f}")

        # 返回：更新后的参数、训练样本数、额外指标
        return self.get_parameters(config={}), self.num_train, {"train_loss": avg_loss}

    def evaluate(self, parameters, config):
        """
        本地评估（Flower 每轮结束后可选调用）

        流程：
        1. 接收全局聚合后的模型参数
        2. 在本地测试集上评估
        3. 返回损失、测试样本数、准确率
        """
        self.set_parameters(parameters)
        loss, metric = evaluate(self.model, self.testloader, self.device, task_type=self.task_type)
        metric_name = "准确率" if self.task_type == "classification" else "R²"
        print(f"[节点 {self.node_id}] 评估 | 损失: {loss:.4f} | {metric_name}: {metric:.4f}")
        return loss, self.num_test, {"accuracy": metric}


def create_client(node_id: int, num_nodes: int = 2, model_type: str = "breast_cancer") -> FlowerClient:
    """工厂函数：创建一个 Flower 客户端实例"""
    cfg = get_model_config(model_type)["default_config"]
    return FlowerClient(
        node_id=node_id,
        num_nodes=num_nodes,
        local_epochs=cfg.get("local_epochs", 3),
        learning_rate=cfg.get("learning_rate", 0.001),
        batch_size=cfg.get("batch_size", 32),
        model_type=model_type,
    )
