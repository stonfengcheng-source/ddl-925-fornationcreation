"""生成可直接运行的 LLaMA-Factory 数据注册、训练、合并配置和批处理脚本。"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from common import dataset_variants, sample_label, training_schedule


def scalar(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(str(value), ensure_ascii=False)


def write_yaml(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(f"{key}: {scalar(value)}" for key, value in rows) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, help="例如 Qwen/Qwen2.5-0.5B-Instruct")
    parser.add_argument("--template", default="qwen")
    parser.add_argument("--data-dir", default="experiments/module4/data")
    parser.add_argument("--out-dir", default="configs/module4")
    parser.add_argument("--experiment-dir", default="experiments/module4")
    parser.add_argument("--n", type=int, default=2000)
    parser.add_argument("--cutoff-len", type=int, default=2048)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--grad-acc", type=int, default=8)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--epochs", type=float, default=3.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--precision", choices=("bf16", "fp16"), default="bf16")
    parser.add_argument("--warmup-ratio", type=float, default=0.1)
    args = parser.parse_args()
    schedule = training_schedule(args.n, args.batch_size, args.grad_acc, args.epochs, args.warmup_ratio)

    output_dir = Path(args.out_dir)
    data_registry_dir = output_dir / "llamafactory_data"
    data_registry_dir.mkdir(parents=True, exist_ok=True)
    experiment_dir = Path(args.experiment_dir).resolve()
    label = sample_label(args.n)
    active, pending = dataset_variants(args.data_dir, args.n)
    groups = {
        name: Path(args.data_dir).resolve() / f"{name}_{label}.jsonl"
        for name in active
    }
    missing = [str(path) for path in groups.values() if not path.exists()]
    if missing:
        raise FileNotFoundError("请先生成训练集，缺少：\n" + "\n".join(missing))

    dataset_info = {}
    train_configs = {}
    merge_configs = {}
    for group, dataset_path in groups.items():
        dataset_name = f"module4_{group}_{label}"
        # 将训练数据复制到只含 ASCII 字符的自包含注册目录，并只登记文件名。
        # 部分 Windows 中文系统上的第三方依赖会用系统编码读取 dataset_info.json，
        # 中文绝对路径可能因此被解码为乱码并触发 "File not found"。
        registered_dataset_path = data_registry_dir / dataset_path.name
        shutil.copy2(dataset_path, registered_dataset_path)
        dataset_info[dataset_name] = {
            "file_name": registered_dataset_path.name,
            "columns": {
                "prompt": "instruction",
                "query": "input",
                "response": "output",
                "system": "system",
            },
        }
        checkpoint_dir = experiment_dir / "checkpoints" / group
        merged_dir = experiment_dir / "merged_models" / group
        train_path = output_dir / f"{group}_lora.yaml"
        train_rows = [
            ("model_name_or_path", args.model),
            ("trust_remote_code", True),
            ("stage", "sft"),
            ("do_train", True),
            ("finetuning_type", "lora"),
            ("lora_target", "all"),
            ("dataset", dataset_name),
            ("dataset_dir", str(data_registry_dir.resolve())),
            ("template", args.template),
            ("cutoff_len", args.cutoff_len),
            ("overwrite_cache", True),
            ("preprocessing_num_workers", 1 if args.n < 100 else 4),
            ("output_dir", str(checkpoint_dir)),
            ("logging_steps", min(10, schedule["estimated_optimizer_steps"])),
            ("save_steps", 200),
            ("plot_loss", True),
            ("overwrite_output_dir", True),
            ("save_only_model", False),
            ("per_device_train_batch_size", args.batch_size),
            ("gradient_accumulation_steps", args.grad_acc),
            ("gradient_checkpointing", True),
            ("learning_rate", args.lr),
            ("num_train_epochs", args.epochs),
            ("lr_scheduler_type", "cosine"),
            ("warmup_steps", schedule["warmup_steps"]),
            ("bf16", args.precision == "bf16"),
            ("fp16", args.precision == "fp16"),
            ("seed", args.seed),
            ("report_to", "none"),
        ]
        write_yaml(train_path, train_rows)
        train_configs[group] = str(train_path.resolve())

        merge_path = output_dir / f"{group}_merge.yaml"
        write_yaml(
            merge_path,
            [
                ("model_name_or_path", args.model),
                ("adapter_name_or_path", str(checkpoint_dir)),
                ("template", args.template),
                ("finetuning_type", "lora"),
                ("trust_remote_code", True),
                ("export_dir", str(merged_dir)),
                ("export_size", 2),
                ("export_device", "cpu"),
                ("export_legacy_format", False),
            ],
        )
        merge_configs[group] = str(merge_path.resolve())

    dataset_info_path = data_registry_dir / "dataset_info.json"
    dataset_info_path.write_text(
        json.dumps(dataset_info, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    # 兼容旧路径，方便检查配置内容；训练实际读取上面的自包含目录。
    (output_dir / "dataset_info.module4.json").write_text(
        json.dumps(dataset_info, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    runner = Path(__file__).with_name("07_run_llamafactory.py").resolve()
    for mode in ("train", "merge"):
        command = f'"{sys.executable}" -u "{runner}" {mode} --variants all --config-dir "{output_dir.resolve()}"'
        bat = ["@echo off", "chcp 65001 >nul", "setlocal", command, "exit /b %errorlevel%"]
        ps1 = ["$ErrorActionPreference = 'Stop'", "& " + command, "exit $LASTEXITCODE"]
        (output_dir / f"run_{mode}.bat").write_text("\n".join(bat) + "\n", encoding="utf-8", newline="\r\n")
        (output_dir / f"run_{mode}.ps1").write_text("\n".join(ps1) + "\n", encoding="utf-8-sig")

    manifest = {
        "model": args.model,
        "template": args.template,
        "sample_count": args.n,
        "seed": args.seed,
        "precision": args.precision,
        "schedule": schedule,
        "dataset_info": str(dataset_info_path.resolve()),
        "train_configs": train_configs,
        "merge_configs": merge_configs,
        "pending_variants": pending,
    }
    manifest_path = output_dir / "training_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"已生成配置: {output_dir.resolve()}")
    print(f"预计优化器更新 {schedule['estimated_optimizer_steps']} 步，预热 {schedule['warmup_steps']} 步")
    if args.n < 100:
        print("[提示] 当前是小样本流程验证，不用于判断筛选方法的效果。")
    print("也可直接运行以下脚本：")
    print(f"  {output_dir / 'run_train.bat'}")
    print(f"  {output_dir / 'run_merge.bat'}")


if __name__ == "__main__":
    main()
