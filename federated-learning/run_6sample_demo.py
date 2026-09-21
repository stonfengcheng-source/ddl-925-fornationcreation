"""
6样本联邦学习演示脚本
两个节点各3条数据，使用 breast_cancer 模型（BreastCancerNet）
支持跨机器访问：服务端监听 0.0.0.0

用法1: 单机模拟（一条命令全搞定）
    python run_6sample_demo.py

用法2: 分机器运行
    本机（服务端）:  python run_6sample_demo.py --role server
    另一台电脑A:     python run_6sample_demo.py --role client --node-id 0 --server <本机IP>:8080
    另一台电脑B:     python run_6sample_demo.py --role client --node-id 1 --server <本机IP>:8080
"""

import argparse
import os
import sys
import time
import subprocess
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from collections import OrderedDict
from torch.utils.data import DataLoader, TensorDataset
from sklearn.preprocessing import StandardScaler
from sklearn.datasets import load_breast_cancer

_fl_dir = os.path.dirname(os.path.abspath(__file__))
if _fl_dir not in sys.path:
    sys.path.insert(0, _fl_dir)

# ── 生成6条示例数据 ──────────────────────────────────────────
def generate_6samples():
    """从 sklearn 乳腺癌数据集中抽取6条（良恶性混合），写入CSV"""
    save_dir = os.path.join(_fl_dir, "test_6samples")
    os.makedirs(save_dir, exist_ok=True)

    data = load_breast_cancer()
    df = pd.DataFrame(data.data, columns=data.feature_names)
    df["target"] = data.target

    # 选4个良性 + 2个恶性，打乱
    benign = df[df["target"] == 1].head(4)
    malign = df[df["target"] == 0].head(2)
    selected = pd.concat([benign, malign]).sample(frac=1, random_state=42)

    node_a = selected.iloc[:3]
    node_b = selected.iloc[3:]

    path_a = os.path.join(save_dir, "node_a_3samples.csv")
    path_b = os.path.join(save_dir, "node_b_3samples.csv")
    node_a.to_csv(path_a, index=False)
    node_b.to_csv(path_b, index=False)

    print(f"  Node A: {path_a}  (标签: {node_a['target'].tolist()})")
    print(f"  Node B: {path_b}  (标签: {node_b['target'].tolist()})")
    return path_a, path_b


# ── 加载CSV数据（适配极小样本） ─────────────────────────────
def load_csv_tiny(csv_path, batch_size=2):
    """加载CSV，所有数据同时用于训练和测试（样本极少时）"""
    df = pd.read_csv(csv_path)
    X = df.iloc[:, :-1].values.astype(np.float32)
    y = df.iloc[:, -1].values.astype(np.int64)

    scaler = StandardScaler()
    X = scaler.fit_transform(X)

    X_t = torch.FloatTensor(X)
    y_t = torch.LongTensor(y)

    ds = TensorDataset(X_t, y_t)
    loader = DataLoader(ds, batch_size=batch_size, shuffle=True)
    return loader, loader, len(X), len(X)


# ── Flower 客户端 ────────────────────────────────────────────
import flwr as fl

class TinyFlowerClient(fl.client.NumPyClient):
    """极小样本 Flower 客户端"""

    def __init__(self, node_id, csv_path):
        super().__init__()
        self.node_id = node_id
        self.device = torch.device("cpu")

        from models.breast_cancer import BreastCancerNet
        self.model = BreastCancerNet(input_dim=30, num_classes=2).to(self.device)
        self.trainloader, self.testloader, self.num_train, self.num_test = load_csv_tiny(csv_path)
        print(f"  [节点 {node_id}] 加载 {self.num_train} 条数据")

    def get_parameters(self, config):
        return [val.cpu().numpy() for _, val in self.model.state_dict().items()]

    def set_parameters(self, parameters):
        params_dict = zip(self.model.state_dict().keys(), parameters)
        state_dict = OrderedDict({k: torch.tensor(v, dtype=torch.float32) for k, v in params_dict})
        self.model.load_state_dict(state_dict, strict=True)

    def fit(self, parameters, config):
        self.set_parameters(parameters)
        optimizer = torch.optim.Adam(self.model.parameters(), lr=0.01)
        criterion = nn.CrossEntropyLoss()
        self.model.train()
        total_loss = 0.0
        for epoch in range(5):  # 小数据多训几轮
            for X_b, y_b in self.trainloader:
                optimizer.zero_grad()
                out = self.model(X_b)
                loss = criterion(out, y_b)
                loss.backward()
                optimizer.step()
                total_loss += loss.item()
        avg_loss = total_loss / max(5 * len(self.trainloader), 1)
        print(f"  [节点 {self.node_id}] 训练完成 | 平均损失: {avg_loss:.4f}")
        return self.get_parameters(config={}), self.num_train, {"train_loss": avg_loss}

    def evaluate(self, parameters, config):
        self.set_parameters(parameters)
        self.model.eval()
        criterion = nn.CrossEntropyLoss()
        total_loss, correct, total = 0.0, 0, 0
        with torch.no_grad():
            for X_b, y_b in self.testloader:
                out = self.model(X_b)
                total_loss += criterion(out, y_b).item() * y_b.size(0)
                _, pred = torch.max(out, 1)
                correct += (pred == y_b).sum().item()
                total += y_b.size(0)
        acc = correct / max(total, 1)
        avg_loss = total_loss / max(total, 1)
        print(f"  [节点 {self.node_id}] 评估 | 准确率: {acc:.2%} | 损失: {avg_loss:.4f}")
        return avg_loss, self.num_test, {"accuracy": acc}


# ── 服务端 ───────────────────────────────────────────────────
def run_server(address="0.0.0.0:8080", num_rounds=5, min_clients=2):
    """启动 Flower 服务端（协调器）"""
    from models.breast_cancer import BreastCancerNet
    from train import evaluate as eval_fn

    model = BreastCancerNet(input_dim=30, num_classes=2)
    initial_params = fl.common.ndarrays_to_parameters(
        [val.cpu().numpy() for _, val in model.state_dict().items()]
    )

    # 服务端评估函数（用完整乳腺癌测试集）
    data = load_breast_cancer()
    X = StandardScaler().fit_transform(data.data).astype(np.float32)
    y = data.target.astype(np.int64)
    test_ds = TensorDataset(torch.FloatTensor(X), torch.LongTensor(y))
    test_loader = DataLoader(test_ds, batch_size=32)

    def evaluate_fn(server_round, parameters, config):
        m = BreastCancerNet(input_dim=30, num_classes=2)
        params_dict = zip(m.state_dict().keys(), parameters)
        state_dict = {k: torch.tensor(v, dtype=torch.float32) for k, v in params_dict}
        m.load_state_dict(state_dict, strict=True)
        loss, acc = eval_fn(m, test_loader, torch.device("cpu"), task_type="classification")
        print(f"\n{'='*50}")
        print(f"  [服务端] 第 {server_round} 轮全局评估")
        print(f"  损失: {loss:.4f} | 准确率: {acc:.4f} ({acc*100:.1f}%)")
        print(f"{'='*50}\n")
        return loss, {"accuracy": acc}

    strategy = fl.server.strategy.FedAvg(
        fraction_fit=1.0,
        fraction_evaluate=1.0,
        min_fit_clients=min_clients,
        min_evaluate_clients=min_clients,
        min_available_clients=min_clients,
        initial_parameters=initial_params,
        evaluate_fn=evaluate_fn,
    )

    print("=" * 60)
    print("  科研数据联邦流通平台 — 6样本联邦学习演示")
    print(f"  监听地址: {address}")
    print(f"  训练轮次: {num_rounds}")
    print(f"  最少节点: {min_clients}")
    print(f"  模型: BreastCancerNet (30→64→32→2)")
    print("=" * 60)

    fl.server.start_server(
        server_address=address,
        config=fl.server.ServerConfig(num_rounds=num_rounds),
        strategy=strategy,
    )


# ── 客户端启动 ───────────────────────────────────────────────
def run_client(node_id, server_address, csv_path):
    """启动 Flower 客户端"""
    print(f"\n  [节点 {node_id}] 连接服务端: {server_address}")
    print(f"  [节点 {node_id}] 数据文件: {csv_path}")
    client = TinyFlowerClient(node_id=node_id, csv_path=csv_path)
    fl.client.start_client(
        server_address=server_address,
        client=client.to_client(),
    )
    print(f"\n  [节点 {node_id}] 联邦训练结束")


# ── 单机模拟（子进程模式） ───────────────────────────────────
def run_simulation(num_rounds=5):
    """一键模拟：启动服务端 + 2个客户端子进程"""
    print("\n[步骤1] 生成6条示例数据...")
    path_a, path_b = generate_6samples()

    python_exe = sys.executable
    script = os.path.abspath(__file__)
    server_addr = "0.0.0.0:8080"
    client_addr = "127.0.0.1:8080"

    processes = []
    try:
        # 启动服务端
        print(f"\n[步骤2] 启动 Flower 服务端 ({server_addr})...")
        server_proc = subprocess.Popen(
            [python_exe, script, "--role", "server",
             "--address", server_addr, "--rounds", str(num_rounds)],
            cwd=_fl_dir,
        )
        processes.append(server_proc)
        print("  等待服务端启动 (5秒)...")
        time.sleep(5)

        # 启动客户端A
        print(f"\n[步骤3] 启动客户端节点 #0 (3条数据)...")
        proc_a = subprocess.Popen(
            [python_exe, script, "--role", "client",
             "--node-id", "0", "--server", client_addr, "--data", path_a],
            cwd=_fl_dir,
        )
        processes.append(proc_a)
        time.sleep(1)

        # 启动客户端B
        print(f"[步骤4] 启动客户端节点 #1 (3条数据)...")
        proc_b = subprocess.Popen(
            [python_exe, script, "--role", "client",
             "--node-id", "1", "--server", client_addr, "--data", path_b],
            cwd=_fl_dir,
        )
        processes.append(proc_b)

        # 等待完成
        print(f"\n[训练中...] {num_rounds} 轮联邦训练\n")
        server_proc.wait()
        for p in processes[1:]:
            p.wait(timeout=30)

        print("\n" + "=" * 60)
        print("  6样本联邦学习训练完成！")
        print("=" * 60)

    except KeyboardInterrupt:
        print("\n收到中断信号，正在停止...")
    finally:
        for p in processes:
            if p.poll() is None:
                p.terminate()
                p.wait(timeout=5)


# ── 主入口 ───────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="6样本联邦学习演示")
    parser.add_argument("--role", choices=["server", "client", "simulate"],
                        default="simulate", help="运行角色 (默认: simulate 单机模拟)")
    parser.add_argument("--address", default="0.0.0.0:8080", help="服务端监听地址")
    parser.add_argument("--server", default="127.0.0.1:8080", help="客户端连接的服务端地址")
    parser.add_argument("--node-id", type=int, default=0, help="客户端节点ID")
    parser.add_argument("--data", default="", help="CSV数据文件路径")
    parser.add_argument("--rounds", type=int, default=5, help="训练轮次")
    args = parser.parse_args()

    if args.role == "server":
        run_server(address=args.address, num_rounds=args.rounds)
    elif args.role == "client":
        csv_path = args.data
        if not csv_path:
            # 自动生成并使用对应节点的数据
            path_a, path_b = generate_6samples()
            csv_path = path_a if args.node_id == 0 else path_b
        run_client(node_id=args.node_id, server_address=args.server, csv_path=csv_path)
    else:
        run_simulation(num_rounds=args.rounds)
