"""生成 Base 与五组微调模型的 OpenCompass 统一评测清单与命令。"""
from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path

from common import TRAIN_VARIANTS
from evaluation import EVAL_PROFILES, resolve_selection, selection_fingerprint
from model_compat import normalize_export_config


def bat_quote(value) -> str:
    return '"' + str(value).replace('"', '""') + '"'


def ps_quote(value) -> str:
    return '"' + str(value).replace('"', '`"') + '"'


def require_ascii_absolute(path: Path, name: str) -> Path:
    """OpenCompass 在 Windows 子进程中无法可靠处理中文工作路径。"""
    path = path.expanduser().resolve()
    if not path.is_absolute():
        raise ValueError(f"{name}必须是绝对路径：{path}")
    if any(ord(char) > 127 for char in str(path)):
        raise ValueError(f"{name}只能包含英文字母、数字和英文符号：{path}")
    return path


def link_or_copy(source: str, destination: str) -> str:
    """优先创建硬链接以节省磁盘；不支持时退回复制。"""
    source_path = Path(source)
    destination_path = Path(destination)
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    if destination_path.exists():
        try:
            if os.path.samefile(source_path, destination_path):
                return str(destination_path)
        except OSError:
            pass
        destination_path.unlink()
    try:
        os.link(source_path, destination_path)
    except OSError:
        shutil.copy2(source_path, destination_path)
    return str(destination_path)


def mirror_model(source: Path, destination: Path) -> None:
    if not source.is_dir():
        raise FileNotFoundError(f"合并模型不存在：{source}")
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        source,
        destination,
        dirs_exist_ok=True,
        copy_function=link_or_copy,
    )


def validate_merged_model(path: Path, name: str) -> None:
    """确认目录是可独立加载的完整模型，而不只是LoRA适配器。"""
    if not (path / "config.json").is_file():
        raise FileNotFoundError(f"{name.upper()} 合并模型缺少 config.json：{path}")
    weights = [
        *path.glob("*.safetensors"),
        *path.glob("pytorch_model*.bin"),
    ]
    if not weights:
        raise FileNotFoundError(
            f"{name.upper()} 合并模型缺少模型权重：{path}。"
            "请先在网页的‘训练与模型合并’区域点击‘合并模型’。"
        )


def write_model_config(
    config_root: Path,
    name: str,
    model_path: str,
    tokenizer_path: str,
    batch_size: int,
    max_seq_len: int,
    max_out_len: int,
    num_gpus: int,
    torch_dtype: str = "bfloat16",
) -> str:
    """写入带安全简称的模型配置，避免Windows绝对路径污染输出路径。"""
    config_name = f"module4_{name}_hf"
    safe_abbr = name.replace("_", "-")
    config_dir = config_root / "models" / "module4"
    config_dir.mkdir(parents=True, exist_ok=True)
    content = f'''# 由模块4自动生成；模型简称不得使用Windows绝对路径。
from opencompass.models import HuggingFacewithChatTemplate

models = [
    dict(
        type=HuggingFacewithChatTemplate,
        abbr={f"module4-{safe_abbr}-hf"!r},
        path={str(model_path)!r},
        # 五组微调模型沿用同一个基础模型分词器，保证公平且避免合并目录中
        # tokenizer.json 与独立评测环境的Rust快速分词器版本不兼容。
        tokenizer_path={str(tokenizer_path)!r},
        tokenizer_kwargs=dict(
            padding_side="left",
            truncation_side="left",
            trust_remote_code=True,
            use_fast=False,
        ),
        model_kwargs=dict(device_map="auto", trust_remote_code=True, torch_dtype={torch_dtype!r}),
        generation_kwargs=dict(do_sample=False),
        max_seq_len={int(max_seq_len)},
        max_out_len={int(max_out_len)},
        batch_size={int(batch_size)},
        run_cfg=dict(num_gpus={int(num_gpus)}),
    )
]
'''
    (config_dir / f"{config_name}.py").write_text(content, encoding="utf-8")
    return config_name


def write_limited_dataset_config(
    config_root: Path,
    benchmark: str,
    mode: str,
    subjects: list[str],
    sample_limit: int | None,
) -> str:
    """按精确科目名称过滤；加载时检查当前 OpenCompass 是否支持所选科目。"""
    family = benchmark.removesuffix("_gen")
    if family not in {"ceval", "cmmlu"}:
        raise ValueError(f"暂不支持基准：{benchmark}")
    variable = f"{family}_datasets"
    config_name = f"module4_{mode}_{family}_gen"
    config_dir = config_root / "datasets" / "module4"
    config_dir.mkdir(parents=True, exist_ok=True)
    content = f'''# 由模块4自动生成；不要修改OpenCompass安装目录。
from mmengine.config import read_base

with read_base():
    from opencompass.configs.datasets.{family}.{family}_gen import {variable}

_subjects = {subjects!r}
_by_name = {{str(_dataset.get("name", "")): _dataset for _dataset in {variable}}}
_missing = [name for name in _subjects if name not in _by_name]
if _missing:
    raise ValueError("当前 OpenCompass 缺少所选科目：" + ", ".join(_missing))
{variable} = [dict(_by_name[name]) for name in _subjects]
for _dataset in {variable}:
    _dataset["reader_cfg"] = dict(_dataset["reader_cfg"])
    _dataset["reader_cfg"].pop("test_range", None)
'''
    if sample_limit is not None:
        content += f'    _dataset["reader_cfg"]["test_range"] = "[0:{sample_limit}]"\n'
    (config_dir / f"{config_name}.py").write_text(content, encoding="utf-8")
    return config_name


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-model", required=True)
    parser.add_argument("--benchmarks", nargs="+", default=["ceval_gen", "cmmlu_gen"])
    parser.add_argument("--eval-mode", choices=(*EVAL_PROFILES, "custom"), default="quick")
    parser.add_argument("--subjects", nargs="+", help="自选科目，格式 ceval:computer_network")
    parser.add_argument("--samples-per-subject", type=int, default=10)
    parser.add_argument("--all-questions", action="store_true")
    parser.add_argument("--merged-dir", default="experiments/module4/merged_models")
    parser.add_argument("--variants", nargs="*", choices=TRAIN_VARIANTS, default=list(TRAIN_VARIANTS), help="本次已有数据的模型组；缺失组留空")
    parser.add_argument("--out-dir", default="experiments/module4/evaluation")
    parser.add_argument(
        "--workspace-dir",
        default=r"D:\module4_opencompass",
        help="OpenCompass 专用纯英文工作目录",
    )
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--max-seq-len", type=int, default=2048)
    parser.add_argument("--max-out-len", type=int, default=512)
    parser.add_argument("--hf-num-gpus", type=int, default=1)
    parser.add_argument("--max-num-workers", type=int, default=1)
    parser.add_argument("--torch-dtype", choices=("bfloat16", "float16", "float32"), default="bfloat16")
    args = parser.parse_args()
    if not 0 < args.max_out_len < args.max_seq_len:
        raise ValueError("最大输出长度必须大于 0，且小于模型上下文长度")

    subjects, sample_limit = resolve_selection(
        args.eval_mode, args.subjects, args.samples_per_subject, args.all_questions,
    )
    families = {benchmark.removesuffix("_gen") for benchmark in args.benchmarks}
    if not families <= {"ceval", "cmmlu"}:
        raise ValueError("仅支持 ceval_gen 与 cmmlu_gen 基准")
    if args.eval_mode == "custom" and any(subject.split(":")[0] not in families for subject in subjects):
        raise ValueError("所选科目不属于本次评测基准")
    subjects = [subject for subject in subjects if subject.split(":")[0] in families]
    if not subjects:
        raise ValueError("请至少选择一个评测科目")
    fingerprint = selection_fingerprint(subjects, sample_limit)
    output_dir = Path(args.out_dir).resolve()
    merged_dir = Path(args.merged_dir).resolve()
    workspace_dir = require_ascii_absolute(Path(args.workspace_dir), "评测工作目录")
    model_alias_dir = workspace_dir / "models"
    namespace = f"protocol_v3_{args.eval_mode}_{fingerprint}_out{args.max_out_len}_{args.torch_dtype}"
    run_dir = workspace_dir / "runs" / namespace
    generated_config_root = workspace_dir / "module4_configs" / namespace
    workspace_dir.mkdir(parents=True, exist_ok=True)
    run_dir.mkdir(parents=True, exist_ok=True)

    models = {"base": args.base_model}
    for name in args.variants:
        source = merged_dir / name
        destination = model_alias_dir / name
        validate_merged_model(source, name)
        print(f"正在准备 {name} 的纯英文模型路径：{destination}")
        mirror_model(source, destination)
        normalize_export_config(destination)
        models[name] = str(destination)
    commands = {}
    bat_lines = ["@echo off", "setlocal"]
    dry_bat_lines = ["@echo off", "setlocal"]
    ps_lines = ["$ErrorActionPreference = 'Stop'"]
    dry_ps_lines = ["$ErrorActionPreference = 'Stop'"]

    profile = {
        "label": EVAL_PROFILES[args.eval_mode]["label"] if args.eval_mode != "custom" else "自定义评测",
        "subjects": subjects,
        "subject_count": len(subjects),
        "samples_per_subject": sample_limit,
        "max_questions_per_model": len(subjects) * sample_limit if sample_limit is not None else None,
        "description": f"{len(subjects)} 科目，" + (f"每科最多 {sample_limit} 题" if sample_limit is not None else "每科全部题目"),
    }
    selected_benchmarks = []
    for benchmark in dict.fromkeys(args.benchmarks):
        family = benchmark.removesuffix("_gen")
        family_subjects = [subject.split(":", 1)[1] for subject in subjects if subject.startswith(f"{family}:")]
        if family_subjects:
            selected_benchmarks.append(write_limited_dataset_config(
                generated_config_root, benchmark, args.eval_mode, family_subjects, sample_limit,
            ))

    for name, model_path in models.items():
        model_config = write_model_config(
            generated_config_root,
            name,
            model_path,
            args.base_model,
            args.batch_size,
            args.max_seq_len,
            args.max_out_len,
            args.hf_num_gpus,
            args.torch_dtype,
        )
        command = [
            "opencompass",
            "--models",
            model_config,
            "--datasets",
            *selected_benchmarks,
            "--work-dir",
            str(run_dir / name),
            "--config-dir",
            str(generated_config_root),
        ]
        if args.max_num_workers > 1:
            command.extend(["--max-num-workers", str(args.max_num_workers)])
        commands[name] = command
        bat_command = " ".join(bat_quote(value) for value in command)
        ps_command = "& " + " ".join(ps_quote(value) for value in command)
        bat_lines.append(f"call {bat_command} || exit /b 1")
        dry_bat_lines.append(f"call {bat_command} --dry-run || exit /b 1")
        ps_lines.append(ps_command)
        dry_ps_lines.append(ps_command + " --dry-run")

    output_dir.mkdir(parents=True, exist_ok=True)
    files = {
        "run_opencompass.bat": bat_lines,
        "run_opencompass_dry_run.bat": dry_bat_lines,
        "run_opencompass.ps1": ps_lines,
        "run_opencompass_dry_run.ps1": dry_ps_lines,
    }
    for filename, lines in files.items():
        (output_dir / filename).write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = {
        "protocol_version": 3,
        "inference_dtype": args.torch_dtype,
        "max_out_len": args.max_out_len,
        "max_seq_len": args.max_seq_len,
        "config_dir": str(generated_config_root),
        "base_model": args.base_model,
        "models": {
            name: {
                "path": path,
                "exists_locally": True if name == "base" else Path(path).exists(),
            }
            for name, path in models.items()
        },
        "benchmarks": args.benchmarks,
        "selected_benchmark_configs": selected_benchmarks,
        "evaluation_mode": args.eval_mode,
        "evaluation_profile": profile,
        "selected_subjects": subjects,
        "samples_per_subject": sample_limit,
        "selection_fingerprint": fingerprint,
        "workspace_dir": str(workspace_dir),
        "run_dir": str(run_dir),
        "commands": commands,
        "fairness_constraints": {
            "same_base_model": True,
            "same_benchmarks": True,
            "same_inference_parameters": True,
            "same_training_hyperparameters": True,
            "same_training_sample_count": True,
        },
    }
    manifest_path = output_dir / "eval_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"评测清单: {manifest_path}")
    print(f"纯英文评测工作目录: {workspace_dir}")
    print(f"评测模式: {profile['label']}（{profile['description']}）")
    print(f"先检查配置: {output_dir / 'run_opencompass_dry_run.bat'}")


if __name__ == "__main__":
    main()
