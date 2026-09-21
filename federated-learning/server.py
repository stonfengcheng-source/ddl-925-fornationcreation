"""
Flower 服务端实现（协调器）
运行在平台服务器上，负责：
1. 初始化全局模型
2. 将模型参数下发给各个客户端节点
3. 收集各节点训练后的参数更新
4. 使用 FedAvg 算法聚合参数
5. 重复上述过程 N 轮，直到达到目标准确率或最大轮次
"""

import sys
import os

# 确保 federated-learning 目录在 sys.path 中
_fl_dir = os.path.dirname(os.path.abspath(__file__))
if _fl_dir not in sys.path:
    sys.path.insert(0, _fl_dir)

import flwr as fl
from flwr.server.strategy import (
    FedAvg,
    DifferentialPrivacyServerSideFixedClipping,
    DifferentialPrivacyServerSideAdaptiveClipping,
)
import torch
import numpy as np
from typing import List, Tuple, Optional, Dict

from models import get_model_class, get_model_config, MODEL_REGISTRY
from datasets import load_partition as load_dataset_partition
from train import evaluate

# 当前使用的模型类型（模块级变量，由 start_server 设置）
_current_model_type: str = "breast_cancer"


def get_initial_parameters(model_type: str = None):
    """获取初始全局模型参数（随机初始化）"""
    mt = model_type or _current_model_type
    ModelClass = get_model_class(mt)
    cfg = get_model_config(mt)["default_config"]
    # 根据模型类型传递初始化参数
    if mt == "diabetes_mlp":
        model = ModelClass(input_dim=cfg.get("input_dim", 10))
    else:
        model = ModelClass(input_dim=cfg.get("input_dim", 30), num_classes=cfg.get("num_classes", 2))
    return [val.cpu().numpy() for _, val in model.state_dict().items()]


# 全局模型保存路径（由 start_server 设置）
_save_model_path: Optional[str] = None


def get_evaluate_fn(model_type: str = None):
    """
    返回一个服务端集中评估函数
    每轮聚合后，用一份独立的测试集评估全局模型效果
    """
    mt = model_type or _current_model_type
    model_info = get_model_config(mt)
    task_type = model_info["task_type"]
    cfg = model_info["default_config"]

    # 加载一份测试数据用于服务端评估
    _, testloader, _, _ = load_dataset_partition(
        model_type=mt, node_id=0, num_nodes=1, batch_size=cfg.get("batch_size", 32)
    )
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    def evaluate_fn(
        server_round: int,
        parameters: fl.common.NDArrays,
        config: Dict[str, fl.common.Scalar],
    ) -> Optional[Tuple[float, Dict[str, fl.common.Scalar]]]:
        """每轮聚合后在服务端评估全局模型"""
        ModelClass = get_model_class(mt)
        if mt == "diabetes_mlp":
            model = ModelClass(input_dim=cfg.get("input_dim", 10)).to(device)
        else:
            model = ModelClass(input_dim=cfg.get("input_dim", 30), num_classes=cfg.get("num_classes", 2)).to(device)

        # 加载聚合后的全局参数
        params_dict = zip(model.state_dict().keys(), parameters)
        state_dict = {
            k: torch.tensor(v, dtype=torch.float32) for k, v in params_dict
        }
        model.load_state_dict(state_dict, strict=True)

        # 评估
        loss, metric = evaluate(model, testloader, device, task_type=task_type)
        metric_name = "准确率" if task_type == "classification" else "R²"
        print(f"\n{'='*50}")
        print(f"  [服务端] 第 {server_round} 轮全局评估")
        print(f"  损失: {loss:.4f} | {metric_name}: {metric:.4f} ({metric*100:.1f}%)")
        print(f"{'='*50}\n")

        # 保存聚合模型（每轮覆写，最终保留最后一轮的结果）
        if _save_model_path:
            try:
                os.makedirs(os.path.dirname(_save_model_path), exist_ok=True)
                metric_key = 'accuracy' if task_type == 'classification' else 'r2_score'
                torch.save({
                    'model_state_dict': model.state_dict(),
                    metric_key: metric,
                    'loss': loss,
                    'round': server_round,
                    'model_type': mt,
                    'task_type': task_type,
                }, _save_model_path)
                print(f"  [保存] 模型已保存: {_save_model_path}")
            except Exception as e:
                print(f"  [警告] 模型保存失败: {e}")

        return loss, {"accuracy": metric}

    return evaluate_fn


def create_strategy(
    num_rounds: int = 10,
    min_fit_clients: int = 2,
    min_evaluate_clients: int = 2,
    min_available_clients: int = 2,
    fraction_fit: float = 1.0,
    fraction_evaluate: float = 1.0,
    dp_config: Optional[Dict] = None,
) -> FedAvg:
    """
    创建 FedAvg 聚合策略，可选启用差分隐私

    参数:
        num_rounds: 联邦训练总轮次
        min_fit_clients: 每轮训练最少需要几个客户端
        min_evaluate_clients: 每轮评估最少需要几个客户端
        min_available_clients: 启动训练前最少需要几个客户端连上
        fraction_fit: 每轮参与训练的客户端比例 (1.0 = 全部参与)
        fraction_evaluate: 每轮参与评估的客户端比例
        dp_config: 差分隐私配置，示例:
            {
                "enabled": True,
                "noise_multiplier": 1.0,
                "clipping_norm": 1.0,
                "num_sampled_clients": 2,
                "adaptive": False,  # True 则使用自适应裁剪
            }
    """
    # 获取初始模型参数
    initial_parameters = fl.common.ndarrays_to_parameters(get_initial_parameters(_current_model_type))

    strategy = FedAvg(
        fraction_fit=fraction_fit,
        fraction_evaluate=fraction_evaluate,
        min_fit_clients=min_fit_clients,
        min_evaluate_clients=min_evaluate_clients,
        min_available_clients=min_available_clients,
        initial_parameters=initial_parameters,
        evaluate_fn=get_evaluate_fn(_current_model_type),
    )

    # 如果启用差分隐私，用 DP 策略包裹 FedAvg
    if dp_config and dp_config.get("enabled"):
        noise_multiplier = dp_config.get("noise_multiplier", 1.0)
        clipping_norm = dp_config.get("clipping_norm", 1.0)
        num_sampled = dp_config.get("num_sampled_clients", min_fit_clients)
        adaptive = dp_config.get("adaptive", False)

        if adaptive:
            # clipped_count_stddev 默认值为 num_sampled/20，当客户端数少时过小会报错
            # 设置为 max(num_sampled/20, noise_multiplier + 0.01) 以确保有效
            stddev = max(num_sampled / 20.0, noise_multiplier + 0.01)
            strategy = DifferentialPrivacyServerSideAdaptiveClipping(
                strategy,
                noise_multiplier=noise_multiplier,
                num_sampled_clients=num_sampled,
                initial_clipping_norm=clipping_norm,
                clipped_count_stddev=stddev,
            )
            print(f"  [DP] 已启用差分隐私（自适应裁剪）")
        else:
            strategy = DifferentialPrivacyServerSideFixedClipping(
                strategy,
                noise_multiplier=noise_multiplier,
                clipping_norm=clipping_norm,
                num_sampled_clients=num_sampled,
            )
            print(f"  [DP] 已启用差分隐私（固定裁剪）")

        print(f"  [DP] noise_multiplier={noise_multiplier}, clipping_norm={clipping_norm}")
        print(f"  [DP] num_sampled_clients={num_sampled}")

    return strategy


def start_server(
    server_address: str = "0.0.0.0:8080",
    num_rounds: int = 10,
    min_clients: int = 2,
    dp_config: Optional[Dict] = None,
    model_type: str = "breast_cancer",
    save_model: Optional[str] = None,
):
    """
    启动 Flower 服务端

    参数:
        server_address: 服务端监听地址 (默认 0.0.0.0:8080)
        num_rounds: 联邦训练总轮次
        min_clients: 最少需要几个客户端才开始训练
        dp_config: 差分隐私配置 (None 表示不启用)
        model_type: 模型类型 (默认 breast_cancer)
    """
    global _current_model_type, _save_model_path
    _current_model_type = model_type
    _save_model_path = save_model
    model_info = get_model_config(model_type)

    print("=" * 60)
    print("  科研数据联邦流通平台 — Flower 协调器")
    print(f"  监听地址: {server_address}")
    print(f"  训练轮次: {num_rounds}")
    print(f"  最少节点: {min_clients}")
    print(f"  模型类型: {model_info['name']} ({model_type})")
    print(f"  任务类型: {model_info['task_type']}")
    print(f"  差分隐私: {'已启用' if dp_config and dp_config.get('enabled') else '未启用'}")
    print("=" * 60)

    strategy = create_strategy(
        num_rounds=num_rounds,
        min_fit_clients=min_clients,
        min_evaluate_clients=min_clients,
        min_available_clients=min_clients,
        dp_config=dp_config,
    )

    fl.server.start_server(
        server_address=server_address,
        config=fl.server.ServerConfig(num_rounds=num_rounds),
        strategy=strategy,
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Flower 联邦学习服务端（协调器）")
    parser.add_argument("--address", type=str, default="0.0.0.0:8080",
                        help="监听地址 (默认: 0.0.0.0:8080)")
    parser.add_argument("--rounds", type=int, default=10,
                        help="训练轮次 (默认: 10)")
    parser.add_argument("--min-clients", type=int, default=2,
                        help="最少客户端数 (默认: 2)")
    # 差分隐私参数
    parser.add_argument("--dp", action="store_true", default=False,
                        help="启用差分隐私")
    parser.add_argument("--dp-noise", type=float, default=1.0,
                        help="噪声倍数 (默认: 1.0)")
    parser.add_argument("--dp-clip", type=float, default=1.0,
                        help="裁剪范数 (默认: 1.0)")
    parser.add_argument("--dp-adaptive", action="store_true", default=False,
                        help="使用自适应裁剪")
    # 模型类型
    parser.add_argument("--model-type", type=str, default="breast_cancer",
                        help="模型类型 (默认: breast_cancer)，可选: " + ", ".join(MODEL_REGISTRY.keys()))
    parser.add_argument("--save-model", type=str, default=None,
                        help="训练完成后模型保存路径")
    args = parser.parse_args()

    dp_config = None
    if args.dp:
        dp_config = {
            "enabled": True,
            "noise_multiplier": args.dp_noise,
            "clipping_norm": args.dp_clip,
            "num_sampled_clients": args.min_clients,
            "adaptive": args.dp_adaptive,
        }

    start_server(
        server_address=args.address,
        num_rounds=args.rounds,
        min_clients=args.min_clients,
        dp_config=dp_config,
        model_type=args.model_type,
        save_model=args.save_model,
    )
