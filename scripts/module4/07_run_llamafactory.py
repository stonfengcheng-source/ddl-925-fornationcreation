"""以稳定的 Python 入口运行 LLaMA-Factory 训练或模型合并。

项目此前生成的 CLI（命令行接口）入口在部分 Windows 环境中会静默退出，
因此控制台通过官方 Python 函数 run_exp/export_model 执行同一份 YAML 配置。
"""
from __future__ import annotations

import argparse
import gc
import json
import os
import subprocess
import sys
from pathlib import Path

from common import TRAIN_VARIANTS
from model_compat import lora_update_status, normalize_export_config


PROJECT_ROOT = Path(__file__).resolve().parents[2]
VARIANTS = TRAIN_VARIANTS


def configure_output() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(encoding="utf-8", errors="replace", line_buffering=True)


def run_single(mode: str, variant: str, config_dir: Path) -> None:
    os.environ.setdefault("HF_DATASETS_CACHE", str(PROJECT_ROOT / ".cache" / "huggingface" / "datasets"))
    import yaml
    from llamafactory.train.tuner import export_model, run_exp

    suffix = "lora" if mode == "train" else "merge"
    config_path = (config_dir / f"{variant}_{suffix}.yaml").resolve()
    if not config_path.exists():
        raise FileNotFoundError(f"配置文件不存在：{config_path}")
    with config_path.open("r", encoding="utf-8") as handle:
        arguments = yaml.safe_load(handle)
    print(f"\n===== {variant.upper()} {'训练' if mode == 'train' else '模型合并'}开始 =====")
    print(f"配置：{config_path}")
    if mode == "train":
        run_exp(arguments)
        output = Path(arguments["output_dir"])
        audit = lora_update_status(output / "adapter_model.safetensors")
        (output / "training_audit.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
        if not audit["has_update"]:
            raise RuntimeError("训练结束但 LoRA B 矩阵仍全部为零。请重新生成训练配置，检查预热步数和实际训练步数。")
        print(f"[校验通过] {audit['nonzero_lora_b_matrices']} 个 LoRA B 矩阵产生了更新")
    else:
        adapter = Path(arguments["adapter_name_or_path"]) / "adapter_model.safetensors"
        if not lora_update_status(adapter)["has_update"]:
            raise RuntimeError("适配器没有有效更新，请用修复后的配置重新训练后再合并。")
        export_model(arguments)
        normalize_export_config(Path(arguments["export_dir"]))
        print("[校验通过] 导出配置已保留旧版评测环境所需的 RoPE 和精度参数")
    print(f"===== {variant.upper()} {'训练' if mode == 'train' else '模型合并'}完成 =====\n")
    gc.collect()
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except ImportError:
        pass


def main() -> None:
    configure_output()
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("train", "merge"))
    parser.add_argument("--variants", nargs="+", default=["all"])
    parser.add_argument("--config-dir", default="configs/module4")
    parser.add_argument("--single-process", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()

    config_dir = (PROJECT_ROOT / args.config_dir).resolve()
    manifest_path = config_dir / "training_manifest.json"
    available = list(VARIANTS)
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        available = [name for name in VARIANTS if name in manifest.get("train_configs", {})]
    variants = available if "all" in args.variants else args.variants
    invalid = sorted(set(variants).difference(VARIANTS))
    if invalid:
        raise ValueError(f"未知模型组：{', '.join(invalid)}")
    pending = sorted(set(variants).difference(available))
    if pending:
        raise ValueError(f"以下组尚未接入数据，本次留空：{', '.join(pending)}")
    if not variants:
        raise ValueError("没有可运行的训练配置，请先生成已有数据组的配置")

    # 多组任务分别使用独立 Python 进程，确保上一组释放显存后再开始下一组。
    if len(variants) > 1 and not args.single_process:
        for variant in variants:
            command = [
                sys.executable,
                "-u",
                str(Path(__file__).resolve()),
                args.mode,
                "--variants",
                variant,
                "--config-dir",
                str(config_dir),
                "--single-process",
            ]
            result = subprocess.run(command, cwd=PROJECT_ROOT, check=False)
            if result.returncode:
                raise SystemExit(result.returncode)
        return

    for variant in variants:
        run_single(args.mode, variant, config_dir)


if __name__ == "__main__":
    main()
