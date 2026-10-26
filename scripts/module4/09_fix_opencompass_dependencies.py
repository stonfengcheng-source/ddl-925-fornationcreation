"""修复模块4的 OpenCompass 评测依赖兼容性。

只修改用户指定的独立评测虚拟环境，不触碰训练环境或项目其他模块。
"""
from __future__ import annotations

import argparse
import importlib.metadata
import os
import subprocess
import sys
from pathlib import Path


COMPATIBLE_TRANSFORMERS = "4.44.2"


def configure_output() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8", errors="replace", line_buffering=True)


def python_from_env(env_dir: Path) -> Path:
    candidates = (env_dir / "python.exe", env_dir / "Scripts" / "python.exe", env_dir / "bin" / "python")
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    raise FileNotFoundError(f"评测环境中没有找到 Python。已检查：{list(candidates)}")


def version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "未安装"


def main() -> None:
    configure_output()
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-dir", default=r"D:\opencompass_env")
    args = parser.parse_args()

    env_dir = Path(args.env_dir).resolve()
    env_python = python_from_env(env_dir)
    if Path(sys.executable).resolve() != env_python:
        raise RuntimeError(
            "修复脚本必须由评测环境自己的 Python 启动，当前解释器不正确："
            f"{sys.executable}"
        )

    print("===== OpenCompass（开放式模型评测平台）依赖修复 =====")
    print(f"评测环境：{env_dir}")
    print(f"修复前 Transformers（模型工具库）：{version('transformers')}")
    print(f"目标版本：{COMPATIBLE_TRANSFORMERS}")
    print("正在安装兼容版本；只修改独立评测环境，请稍候……")

    environment = os.environ.copy()
    environment.update({"PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"})
    command = [
        str(env_python),
        "-m",
        "pip",
        "install",
        "--upgrade",
        f"transformers=={COMPATIBLE_TRANSFORMERS}",
    ]
    subprocess.run(command, env=environment, check=True)

    check_code = (
        "import importlib.metadata as m; import opencompass; import torch; import transformers; "
        "from transformers import Qwen2Tokenizer; "
        "assert hasattr(Qwen2Tokenizer, 'batch_encode_plus'), "
        "'Qwen2Tokenizer 仍缺少 batch_encode_plus'; "
        "print('OpenCompass:', m.version('opencompass')); "
        "print('Transformers:', transformers.__version__); "
        "print('Tokenizers:', m.version('tokenizers')); "
        "print('PyTorch:', torch.__version__); "
        "print('GPU可用:', torch.cuda.is_available()); "
        "print('兼容接口 batch_encode_plus: 可用')"
    )
    subprocess.run(
        [str(env_python), "-X", "faulthandler", "-c", check_code],
        env=environment,
        check=True,
    )
    dependency_check = subprocess.run(
        [str(env_python), "-m", "pip", "check"], env=environment, check=False
    )
    if dependency_check.returncode:
        print("提示：pip（Python 包安装工具）发现其他包仍有依赖提示，但本次评测核心接口已通过。")
    print("评测核心依赖修复和兼容接口检查全部通过。")
    print("下一步：先点击“检查评测环境”，再进行 Base 试运行和正式评测。")


if __name__ == "__main__":
    main()
