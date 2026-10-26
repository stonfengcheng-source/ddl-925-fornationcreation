"""从评测清单运行 OpenCompass，避免依赖终端 PATH（环境变量搜索路径）。"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from common import EVAL_MODELS


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODELS = EVAL_MODELS


def configure_output() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8", errors="replace", line_buffering=True)


def executable_from_env(env_dir: Path) -> Path:
    candidates = [
        env_dir / "Scripts" / "opencompass.exe",
        env_dir / "bin" / "opencompass",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        f"没有找到 OpenCompass（开放式模型评测平台）程序。已检查：{candidates}"
    )


def python_from_env(env_dir: Path) -> Path:
    candidates = [
        env_dir / "python.exe",
        env_dir / "Scripts" / "python.exe",
        env_dir / "bin" / "python",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"没有找到评测环境 Python。已检查：{candidates}")


def check_tokenizer_compatibility(env_python: Path, environment: dict[str, str]) -> None:
    code = (
        "import transformers; from transformers import Qwen2Tokenizer; "
        "print('Transformers（模型工具库）:', transformers.__version__); "
        "assert hasattr(Qwen2Tokenizer, 'batch_encode_plus'), "
        "'Qwen2Tokenizer 缺少 batch_encode_plus 接口'"
    )
    result = subprocess.run(
        [str(env_python), "-c", code],
        env=environment,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    if result.stdout:
        print(result.stdout.rstrip())
    if result.returncode:
        if result.stderr:
            print(result.stderr.rstrip())
        raise RuntimeError(
            "评测环境依赖不兼容。请返回模块4网页，在“运行环境”区域点击"
            "“修复评测依赖”，修复完成后再开始评测。"
        )


def latest_prediction_timestamp(workspace_dir: Path, model: str, run_root: Path | None = None) -> str:
    """返回该模型最新且确实含预测JSON的运行时间戳。"""
    model_root = (run_root or workspace_dir / "runs") / model
    candidates = []
    if model_root.is_dir():
        for run_dir in model_root.iterdir():
            predictions = run_dir / "predictions"
            if run_dir.is_dir() and predictions.is_dir() and any(predictions.rglob("*.json")):
                candidates.append(run_dir)
    if not candidates:
        raise FileNotFoundError(
            f"{model.upper()} 没有可复用的预测答案。请先对该模型执行一次正式评测。"
        )
    return max(candidates, key=lambda path: (path.name, path.stat().st_mtime)).name


def main() -> None:
    configure_output()
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("dry-run", "run", "score"))
    parser.add_argument("--models", nargs="+", default=["all"])
    parser.add_argument("--manifest", default="experiments/module4/evaluation/eval_manifest.json")
    parser.add_argument("--env-dir", default=r"D:\opencompass_env")
    args = parser.parse_args()

    invalid = sorted(set(args.models).difference((*MODELS, "all")))
    if invalid:
        raise ValueError(f"未知模型：{', '.join(invalid)}")

    manifest_path = (PROJECT_ROOT / args.manifest).resolve()
    if not manifest_path.exists():
        raise FileNotFoundError(f"评测清单不存在，请先生成评测配置：{manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("protocol_version", 0) < 3:
        raise ValueError("评测配置尚未采用新的输出长度隔离。请重新生成评测配置并开始评测，不能直接复用旧预测。")
    available = [name for name in MODELS if name in manifest.get("commands", {})]
    models = available if "all" in args.models else args.models
    missing = sorted(set(models).difference(available))
    if missing:
        raise ValueError(f"以下组尚未接入评测，本次留空：{', '.join(missing)}")
    if not models:
        raise ValueError("评测清单没有可验证的模型")
    workspace_dir = Path(manifest.get("workspace_dir", PROJECT_ROOT)).resolve()
    if any(ord(char) > 127 for char in str(workspace_dir)):
        raise ValueError(
            "评测工作目录包含中文字符。请在网页控制台中重新点击“生成评测配置”，"
            "使用 D:\\module4_opencompass。"
        )
    workspace_dir.mkdir(parents=True, exist_ok=True)
    env_dir = Path(args.env_dir)
    opencompass = executable_from_env(env_dir)
    environment = os.environ.copy()
    environment.update(
        {
            "PYTHONUTF8": "1",
            "PYTHONIOENCODING": "utf-8",
            "HF_HUB_DISABLE_SYMLINKS_WARNING": "1",
        }
    )
    check_tokenizer_compatibility(python_from_env(env_dir), environment)
    model_paths = [manifest["models"][model]["path"] for model in models if model != "base"]
    subprocess.run(
        [str(python_from_env(env_dir)), str(Path(__file__).with_name("model_compat.py")),
         "--base-model", manifest["base_model"], "--models", *model_paths],
        env=environment, check=True,
    )

    for model in models:
        configured = manifest.get("commands", {}).get(model)
        if not configured:
            raise KeyError(f"评测清单中没有 {model} 的命令")
        command = [str(opencompass), *map(str, configured[1:])]
        label = {"dry-run": "试运行", "run": "正式评测", "score": "仅重新评分"}[args.mode]
        commands = [command]
        if args.mode == "dry-run":
            commands = [[*command, "--dry-run"]]
        elif args.mode == "score":
            timestamp = latest_prediction_timestamp(workspace_dir, model, Path(manifest.get("run_dir", workspace_dir / "runs")))
            print(f"{model.upper()}：复用运行记录 {timestamp}")
            commands = [
                [*command, "--mode", "eval", "--reuse", timestamp],
                [*command, "--mode", "viz", "--reuse", timestamp],
            ]
        print(f"\n===== {model.upper()} {label}开始 =====")
        print(f"OpenCompass：{opencompass}")
        print(f"评测工作目录：{workspace_dir}")
        for stage, stage_command in enumerate(commands, 1):
            if args.mode == "score":
                stage_label = "计算评分" if stage == 1 else "重新生成汇总表"
                print(f"{model.upper()}：{stage_label}，复用最新预测答案。")
            result = subprocess.run(stage_command, cwd=workspace_dir, env=environment, check=False)
            if result.returncode:
                print(f"{model} 执行失败，退出码：{result.returncode}")
                raise SystemExit(result.returncode)
        print(f"===== {model.upper()} {label}完成 =====\n")


if __name__ == "__main__":
    main()
