"""
启动 Flower 客户端节点
用法:
    python run_client.py --node-id 0 --server 127.0.0.1:8080
    python run_client.py --node-id 1 --server 127.0.0.1:8080
"""

import argparse
import sys
import os

_fl_dir = os.path.dirname(os.path.abspath(__file__))
if _fl_dir not in sys.path:
    sys.path.insert(0, _fl_dir)

import flwr as fl
from client import create_client
from models import MODEL_REGISTRY


def main():
    parser = argparse.ArgumentParser(description="Flower 联邦学习客户端（数据提供方节点）")
    parser.add_argument("--node-id", type=int, required=True,
                        help="节点编号 (从0开始，如: 0, 1)")
    parser.add_argument("--num-nodes", type=int, default=2,
                        help="总节点数 (默认: 2)")
    parser.add_argument("--server", type=str, default="127.0.0.1:8080",
                        help="服务端地址 (默认: 127.0.0.1:8080)")
    parser.add_argument("--model-type", type=str, default="breast_cancer",
                        help="模型类型 (默认: breast_cancer)，可选: " + ", ".join(MODEL_REGISTRY.keys()))
    args = parser.parse_args()

    print("=" * 60)
    print(f"  科研数据联邦流通平台 — 节点客户端 #{args.node_id}")
    print(f"  连接服务端: {args.server}")
    print(f"  总节点数: {args.num_nodes}")
    print(f"  模型类型: {args.model_type}")
    print("=" * 60)

    # 创建客户端
    client = create_client(node_id=args.node_id, num_nodes=args.num_nodes, model_type=args.model_type)

    # 连接服务端并开始联邦训练
    fl.client.start_client(
        server_address=args.server,
        client=client.to_client(),
    )

    print(f"\n[节点 {args.node_id}] 联邦训练结束")


if __name__ == "__main__":
    main()
