"""
Flower 模拟运行脚本（单机模拟多节点）
用一台电脑同时模拟服务端 + 2个客户端，快速验证联邦学习流程
无需开多个终端，一键运行即可（使用子进程，完全隔离）

用法:
    python simulation.py
    python simulation.py --rounds 20 --num-clients 3
"""

import argparse
import sys
import os
import time
import subprocess

_fl_dir = os.path.dirname(os.path.abspath(__file__))
if _fl_dir not in sys.path:
    sys.path.insert(0, _fl_dir)


def run_simulation(num_rounds: int = 10, num_clients: int = 2, model_type: str = "breast_cancer",
                   dp_enabled: bool = False, dp_noise: float = 1.0, dp_clip: float = 1.0, dp_adaptive: bool = False):
    """
    运行联邦学习模拟（子进程模式）

    启动独立的服务端进程和客户端进程，完全避免线程/信号问题
    """
    server_address = "0.0.0.0:8099"
    client_address = "127.0.0.1:8099"
    script_dir = os.path.dirname(os.path.abspath(__file__))
    python_exe = sys.executable

    print("=" * 60)
    print("  科研数据联邦流通平台 — 联邦学习模拟")
    print(f"  模拟节点数: {num_clients}")
    print(f"  训练轮次: {num_rounds}")
    print(f"  数据集: sklearn 乳腺癌数据集 (569样本, 30特征)")
    print(f"  模型: BreastCancerNet (30->64->32->2)")
    print(f"  聚合策略: FedAvg")
    print(f"  模型类型: {model_type}")
    print(f"  差分隐私: {'已启用 (noise=' + str(dp_noise) + ', clip=' + str(dp_clip) + ')' if dp_enabled else '未启用'}")
    print(f"  Python: {python_exe}")
    print("=" * 60)

    processes = []

    try:
        # 1. 启动服务端进程
        print("\n[模拟] 启动 Flower 服务端...")
        server_cmd = [
            python_exe, os.path.join(script_dir, "server.py"),
            "--address", server_address,
            "--rounds", str(num_rounds),
            "--min-clients", str(num_clients),
            "--model-type", model_type,
        ]
        if dp_enabled:
            server_cmd.append("--dp")
            server_cmd.extend(["--dp-noise", str(dp_noise)])
            server_cmd.extend(["--dp-clip", str(dp_clip)])
            if dp_adaptive:
                server_cmd.append("--dp-adaptive")
        server_proc = subprocess.Popen(
            server_cmd, cwd=script_dir,
            stdout=None, stderr=None,  # 直接输出到控制台
        )
        processes.append(server_proc)

        # 等待服务端就绪
        print("[模拟] 等待服务端启动 (5秒)...")
        time.sleep(5)

        # 2. 依次启动客户端进程
        client_procs = []
        for i in range(num_clients):
            print(f"[模拟] 启动客户端节点 #{i}...")
            client_cmd = [
                python_exe, os.path.join(script_dir, "run_client.py"),
                "--node-id", str(i),
                "--num-nodes", str(num_clients),
                "--server", client_address,
                "--model-type", model_type,
            ]
            proc = subprocess.Popen(
                client_cmd, cwd=script_dir,
                stdout=None, stderr=None,
            )
            client_procs.append(proc)
            processes.append(proc)
            time.sleep(1)

        # 3. 等待服务端完成（服务端在所有轮次跑完后会自动退出）
        print(f"\n[模拟] 联邦训练进行中... ({num_rounds} 轮)")
        server_proc.wait()

        # 4. 等待客户端退出
        for proc in client_procs:
            proc.wait(timeout=30)

        print("\n" + "=" * 60)
        print("  联邦训练完成！")
        print("=" * 60)

    except KeyboardInterrupt:
        print("\n[模拟] 收到中断信号，正在停止...")
    finally:
        # 清理所有进程
        for proc in processes:
            if proc.poll() is None:
                proc.terminate()
                proc.wait(timeout=5)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="联邦学习模拟（单机运行）")
    parser.add_argument("--rounds", type=int, default=10,
                        help="训练轮次 (默认: 10)")
    parser.add_argument("--num-clients", type=int, default=2,
                        help="模拟客户端数量 (默认: 2)")
    parser.add_argument("--model-type", type=str, default="breast_cancer",
                        help="模型类型 (默认: breast_cancer)")
    parser.add_argument("--dp", action="store_true", default=False,
                        help="启用差分隐私")
    parser.add_argument("--dp-noise", type=float, default=1.0,
                        help="噪声倍数 (默认: 1.0)")
    parser.add_argument("--dp-clip", type=float, default=1.0,
                        help="裁剪范数 (默认: 1.0)")
    parser.add_argument("--dp-adaptive", action="store_true", default=False,
                        help="使用自适应裁剪")
    args = parser.parse_args()

    run_simulation(
        num_rounds=args.rounds, num_clients=args.num_clients,
        model_type=args.model_type,
        dp_enabled=args.dp, dp_noise=args.dp_noise,
        dp_clip=args.dp_clip, dp_adaptive=args.dp_adaptive,
    )
