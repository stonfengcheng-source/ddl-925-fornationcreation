"""模块4任务执行服务，由现有 FastAPI 后端托管。"""
from __future__ import annotations

import os
import json
import importlib.util
import subprocess
import sys
import threading
import time
from collections import deque
from pathlib import Path
from typing import Any

TRAIN_VARIANTS = ("raw", "rule", "llm_only", "datajuicer", "ours")
MODEL_NAMES = ("base", *TRAIN_VARIANTS)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
MODULE_DIR = PROJECT_ROOT / "scripts" / "module4"
# 复用命令行的选择校验，避免网页与脚本的科目、题量规则不一致。
_selection_spec = importlib.util.spec_from_file_location("module4_evaluation", MODULE_DIR / "evaluation.py")
_selection = importlib.util.module_from_spec(_selection_spec)
_selection_spec.loader.exec_module(_selection)
PYTHON = Path(sys.executable).resolve()
TRAINING_PYTHON_CANDIDATES = (
    *((Path(os.environ["MODULE4_TRAINING_PYTHON"]),) if os.getenv("MODULE4_TRAINING_PYTHON") else ()),
    PROJECT_ROOT / ".venv-lora" / "Scripts" / "python.exe",
    PROJECT_ROOT / ".venv-lora" / "bin" / "python",
)
TRAINING_PYTHON = next(
    (candidate.resolve() for candidate in TRAINING_PYTHON_CANDIDATES if candidate.exists()),
    PYTHON,
)
VARIANTS = {*TRAIN_VARIANTS, "all"}
EVAL_MODELS = {*MODEL_NAMES, "all"}
EVAL_MODES = {*_selection.EVAL_PROFILES, "custom"}
PROGRESS_ACTIONS = {
    "environment_report": ("check_training_env", "check_eval_env"),
    "datasets": ("build_data",),
    "validation": ("validate_data",),
    "configs": ("prepare_configs",),
    "checkpoints": ("train",),
    "merged": ("merge",),
    "eval_manifest": ("make_eval_manifest",),
    "summary": ("compare_results",),
}
DATA_PARAMETERS = ("raw_path", "evaluated_path", "datajuicer_path", "sample_count", "seed")
TRAIN_PARAMETERS = (*DATA_PARAMETERS, "training_python", "base_model", "template", "epochs", "precision")
EVAL_PARAMETERS = (*TRAIN_PARAMETERS, "opencompass_env", "eval_workspace", "eval_mode", "eval_batch_size", "eval_max_out_len",
                   "eval_subjects", "eval_samples_per_subject", "eval_all_questions")
PROGRESS_PARAMETERS = {
    "environment_report": ("training_python", "opencompass_env"),
    "datasets": DATA_PARAMETERS, "validation": DATA_PARAMETERS,
    "configs": TRAIN_PARAMETERS, "checkpoints": TRAIN_PARAMETERS, "merged": TRAIN_PARAMETERS,
    "eval_manifest": EVAL_PARAMETERS, "summary": EVAL_PARAMETERS,
}


def _windows_job(process):
    """将任务及其子进程放在一个 Windows Job 中，停止时一起结束。"""
    if os.name != "nt":
        return None
    import ctypes
    from ctypes import wintypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    kernel.CreateJobObjectW.restype = wintypes.HANDLE
    kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel.AssignProcessToJobObject.restype = wintypes.BOOL
    kernel.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
    kernel.TerminateJobObject.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.CreateJobObjectW(None, None)
    if handle and kernel.AssignProcessToJobObject(handle, int(process._handle)):
        return kernel, handle
    if handle:
        kernel.CloseHandle(handle)
    return None


def _integer(value: Any, name: str, minimum: int = 1, maximum: int = 1_000_000) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} 必须是整数") from exc
    if not minimum <= number <= maximum:
        raise ValueError(f"{name} 必须在 {minimum} 到 {maximum} 之间")
    return number


def _float(value: Any, name: str, minimum: float, maximum: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} 必须是数字") from exc
    if not minimum <= number <= maximum:
        raise ValueError(f"{name} 必须在 {minimum} 到 {maximum} 之间")
    return number


def _text(value: Any, name: str) -> str:
    result = str(value or "").strip()
    if not result or "\x00" in result:
        raise ValueError(f"{name} 不能为空")
    return result


def dataset_selection(sample_count: int | None = None) -> tuple[list[str], dict[str, str]]:
    data_dir = PROJECT_ROOT / "experiments" / "module4" / "data"
    if sample_count is None:
        paths = sorted(data_dir.glob("dataset_manifest_*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    else:
        label = f"{sample_count // 1000}k" if sample_count % 1000 == 0 else str(sample_count)
        paths = [data_dir / f"dataset_manifest_{label}.json"]
    for path in paths:
        if path.is_file():
            manifest = json.loads(path.read_text(encoding="utf-8"))
            return [name for name in TRAIN_VARIANTS if name in manifest.get("variants", {})], manifest.get("pending_variants", {})
    return list(TRAIN_VARIANTS), {}


def merged_model_ready(name: str) -> bool:
    path = PROJECT_ROOT / "experiments" / "module4" / "merged_models" / name
    return (path / "config.json").is_file() and bool([*path.glob("*.safetensors"), *path.glob("pytorch_model*.bin")])


def available_evaluation_models(sample_count: int | None = None) -> list[str]:
    active, _ = dataset_selection(sample_count)
    return ["base", *(name for name in active if merged_model_ready(name))]


def configured_evaluation_models() -> list[str]:
    path = PROJECT_ROOT / "experiments" / "module4" / "evaluation" / "eval_manifest.json"
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
        return [name for name in MODEL_NAMES if name in manifest.get("commands", {})]
    except (OSError, ValueError):
        return []


def select_evaluation_models(config: dict[str, Any], sample_count: int, use_manifest: bool = False) -> list[str]:
    model = str(config.get("eval_model", "all")).lower()
    if model not in EVAL_MODELS:
        raise ValueError("请选择 Base 或可用的微调模型")
    available = available_evaluation_models(sample_count)
    if model != "all" and model not in available:
        raise ValueError(f"{model.upper()} 尚未完成训练和合并，请先完成这两步，或选择 Base 进行验证。")
    selected = available if model == "all" else [model]
    configured = configured_evaluation_models() if use_manifest else []
    if configured:
        if model != "all" and model not in configured:
            raise ValueError("所选模型尚未加入评测配置，请重新生成评测配置。")
        selected = [name for name in selected if name in configured]
    return selected


def build_action_command(action: str, config: dict[str, Any]) -> tuple[list[str], str]:
    """将前端动作转换为参数列表，不经过 shell 解释。"""
    # 即使网页后台由系统 Python 启动，训练动作也固定使用项目训练环境。
    configured_python = str(config.get("training_python") or "").strip()
    py = str(TRAINING_PYTHON)
    if configured_python:
        interpreter = Path(configured_python).expanduser()
        if not interpreter.is_file() or not interpreter.name.lower().startswith("python"):
            raise ValueError("训练 Python 必须指向后端电脑上已有的 Python 解释器")
        py = str(interpreter.resolve())
    scripts = MODULE_DIR
    sample_count = _integer(config.get("sample_count", 100), "样本数")
    seed = _integer(config.get("seed", 42), "随机种子", 0, 2_147_483_647)

    if action == "check_training_env":
        return [py, "-u", str(scripts / "00_check_environment.py"), "--strict"], "检查训练环境"
    if action == "check_eval_env":
        env_dir = Path(_text(config.get("opencompass_env", r"D:\opencompass_env"), "评测环境路径"))
        env_python = env_dir / ("python.exe" if os.name == "nt" else "bin/python")
        code = (
            "import importlib.metadata as m; import sentencepiece as spm; import torch; import opencompass; "
            "import transformers; from transformers import Qwen2Tokenizer; "
            "print('OpenCompass:',m.version('opencompass')); print('SentencePiece:',spm.__version__); "
            "print('Transformers:',transformers.__version__); "
            "print('兼容接口 batch_encode_plus:',hasattr(Qwen2Tokenizer,'batch_encode_plus')); "
            "print('PyTorch:',torch.__version__); print('GPU可用:',torch.cuda.is_available()); "
            "assert hasattr(Qwen2Tokenizer,'batch_encode_plus'), "
            "'评测依赖不兼容，请点击“修复评测依赖”'; print('全部核心组件导入成功')"
        )
        return [str(env_python), "-X", "faulthandler", "-c", code], "检查评测环境"
    if action == "fix_eval_dependencies":
        env_dir = Path(_text(config.get("opencompass_env", r"D:\opencompass_env"), "评测环境路径"))
        env_python = env_dir / ("python.exe" if os.name == "nt" else "bin/python")
        return [
            str(env_python), "-u", str(scripts / "09_fix_opencompass_dependencies.py"),
            "--env-dir", str(env_dir),
        ], "修复 OpenCompass 评测依赖"
    if action == "build_data":
        command = [
            py, "-u", str(scripts / "01_build_datasets.py"),
            "--raw", _text(config.get("raw_path", "demo-datasets/education-synthetic/raw_5k.jsonl"), "原始数据路径"),
            "--n", str(sample_count), "--seed", str(seed),
        ]
        for field, flag in (("evaluated_path", "--evaluated"), ("datajuicer_path", "--datajuicer")):
            value = str(config.get(field) or "").strip()
            if value:
                command.extend([flag, value])
        return command, "生成已有组的验证数据，未接入组留空"
    if action == "validate_data":
        return [py, "-u", str(scripts / "02_validate_dataset.py"), "--n", str(sample_count)], "校验已有验证数据"
    if action == "prepare_configs":
        precision = str(config.get("precision", "bf16"))
        if precision not in {"bf16", "fp16"}:
            raise ValueError("训练精度只能是 bf16 或 fp16")
        return [
            py, "-u", str(scripts / "03_prepare_llamafactory.py"),
            "--model", _text(config.get("base_model", "Qwen/Qwen2.5-0.5B-Instruct"), "基础模型"),
            "--template", _text(config.get("template", "qwen"), "模型模板"),
            "--n", str(sample_count), "--seed", str(seed),
            "--precision", precision,
            "--epochs", str(_float(config.get("epochs", 1), "训练轮数", 0.01, 100)),
        ], "生成 LLaMA-Factory 训练配置"
    if action in {"train", "merge"}:
        variant = str(config.get("variant", "all")).lower()
        if variant not in VARIANTS:
            raise ValueError("模型组只能是 Raw、Rule、LLM-only、Data-Juicer、Ours 或全部")
        active, _ = dataset_selection(sample_count)
        selected = active if variant == "all" else [variant]
        if not selected or any(name not in active for name in selected):
            raise ValueError("所选模型组尚未接入数据，请选择已有验证数据的组")
        label = "LoRA（低秩适配微调）训练" if action == "train" else "合并模型"
        return [
            py, "-u", str(scripts / "07_run_llamafactory.py"), action,
            "--variants", *selected,
        ], f"{label}：{variant}"
    if action == "make_eval_manifest":
        eval_mode = str(config.get("eval_mode", "quick")).lower()
        subjects, sample_limit = _selection.resolve_selection(
            eval_mode, config.get("eval_subjects"), config.get("eval_samples_per_subject", 10),
            config.get("eval_all_questions", False),
        )
        selection_args = []
        if eval_mode == "custom":
            selection_args = ["--subjects", *subjects]
            selection_args += ["--all-questions"] if sample_limit is None else ["--samples-per-subject", str(sample_limit)]
        selected = select_evaluation_models(config, sample_count)
        return [
            py, "-u", str(scripts / "04_make_eval_manifest.py"),
            "--base-model", _text(config.get("base_model", "Qwen/Qwen2.5-0.5B-Instruct"), "基础模型"),
            "--benchmarks", "ceval_gen", "cmmlu_gen",
            "--eval-mode", eval_mode,
            *selection_args,
            "--batch-size", str(_integer(config.get("eval_batch_size", 1), "评测批量大小", 1, 128)),
            "--max-out-len", str(_integer(config.get("eval_max_out_len", 512), "单题最大输出长度", 64, 1024)),
            "--torch-dtype", "float16" if config.get("precision") == "fp16" else "bfloat16",
            "--workspace-dir", _text(
                config.get("eval_workspace", r"D:\module4_opencompass"),
                "纯英文评测工作目录",
            ),
            "--variants", *(name for name in selected if name != "base"),
        ], f"生成 OpenCompass 评测清单：{eval_mode}（{', '.join(selected)}）"
    if action in {"eval_dry", "eval_run", "eval_score"}:
        manifest_path = PROJECT_ROOT / "experiments/module4/evaluation/eval_manifest.json"
        if manifest_path.is_file():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            subjects, sample_limit = _selection.resolve_selection(
                str(config.get("eval_mode", "quick")).lower(), config.get("eval_subjects"),
                config.get("eval_samples_per_subject", 10), config.get("eval_all_questions", False),
            )
            if (manifest.get("selection_fingerprint") != _selection.selection_fingerprint(subjects, sample_limit)
                    or manifest.get("max_out_len") != _integer(config.get("eval_max_out_len", 512), "单题最大输出长度", 64, 1024)):
                raise ValueError("评测科目、题量或输出长度已变更，请先重新生成评测配置")
        model = str(config.get("eval_model", "all")).lower()
        if model not in EVAL_MODELS:
            raise ValueError(
                "评测模型只能是 Base、Raw、Rule、LLM-only、Data-Juicer、Ours 或全部"
            )
        selected = select_evaluation_models(config, sample_count, use_manifest=True)
        mode = {"eval_dry": "dry-run", "eval_run": "run", "eval_score": "score"}[action]
        action_label = {
            "dry-run": "试运行",
            "run": "正式评测",
            "score": "仅重新评分",
        }[mode]
        return [
            py, "-u", str(scripts / "08_run_opencompass.py"), mode,
            "--models", *selected,
            "--env-dir", _text(config.get("opencompass_env", r"D:\opencompass_env"), "评测环境路径"),
        ], f"OpenCompass {action_label}：{model}"
    if action == "compare_results":
        return [
            py, "-u", str(scripts / "05_compare_results.py"),
            "--require-manifest",
            "--workspace", _text(
                config.get("eval_workspace", r"D:\module4_opencompass"),
                "纯英文评测工作目录",
            ),
        ], "汇总评测结果"
    if action == "export_badcases":
        model = str(config.get("badcase_model", "ours")).lower()
        if model not in MODEL_NAMES:
            raise ValueError("请选择 Base 或五组微调模型之一")
        return [
            py, "-u", str(scripts / "06_badcase_template.py"),
            "--input", _text(config.get("predictions_path"), "预测结果 JSONL 路径"),
            "--model", model,
            "--output", str(PROJECT_ROOT / "experiments" / "module4" / "results" / f"{model}_badcases.jsonl"),
        ], f"导出错误样本：{model}"
    raise ValueError(f"不支持的操作：{action}")


class TaskManager:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.process: subprocess.Popen[str] | None = None
        self.job = None
        self.logs: deque[str] = deque(maxlen=4000)
        self.status = "idle"
        self.label = "尚未运行任务"
        self.exit_code: int | None = None
        self.started_at: float | None = None
        self.finished_at: float | None = None
        self.completed_actions: dict[str, set[str]] = {}
        self.progress_parameters: dict[str, dict[str, Any]] = {}
        self.current_action: str | None = None
        self.current_targets: set[str] = set()
        self.current_config: dict[str, Any] = {}
        self.outputs_before: dict[str, tuple] = {}

    def _output_stamps(self) -> dict[str, tuple]:
        """仅记录产物元数据，确认本次进程确实更新了文件。"""
        def stamp(path: Path):
            try:
                stat = path.stat()
                return (stat.st_mtime_ns, stat.st_size) if path.is_file() else None
            except OSError:
                return None

        experiment = PROJECT_ROOT / "experiments" / "module4"
        count = int(self.current_config.get("sample_count", 100))
        label = f"{count // 1000}k" if count % 1000 == 0 else str(count)
        paths = {
            "check_training_env": experiment / "environment_report.json",
            "build_data": experiment / "data" / f"dataset_manifest_{label}.json",
            "validate_data": experiment / "data" / f"validation_report_{label}.json",
            "prepare_configs": PROJECT_ROOT / "configs/module4/training_manifest.json",
            "make_eval_manifest": experiment / "evaluation/eval_manifest.json",
            "compare_results": experiment / "results/summary.csv",
        }
        if self.current_action in paths:
            return {"done": (stamp(paths[self.current_action]),)}
        result = {}
        for name in self.current_targets:
            if self.current_action == "train":
                folder = experiment / "checkpoints" / name
                result[name] = (stamp(folder / "adapter_model.safetensors"), stamp(folder / "training_audit.json"))
            elif self.current_action == "merge":
                folder = experiment / "merged_models" / name
                weights = sorted([*folder.glob("*.safetensors"), *folder.glob("pytorch_model*.bin")])
                result[name] = (stamp(folder / "config.json"), tuple((path.name, stamp(path)) for path in weights))
        return result

    def _begin_progress(self, action: str | None, config: dict[str, Any], command: list[str]) -> None:
        """重置本步；改写上游产物时撤销依赖步骤，检查任务不影响其他项。"""
        self.current_action = action
        self.current_config = dict(config)
        self.current_targets = set()
        if action in {"train", "merge", "eval_run", "eval_score"}:
            flag = "--variants" if action in {"train", "merge"} else "--models"
            if flag in command:
                for value in command[command.index(flag) + 1:]:
                    if value.startswith("--"):
                        break
                    if value in MODEL_NAMES:
                        self.current_targets.add(value)
        self.outputs_before = self._output_stamps()
        if action in {"eval_run", "eval_score"}:
            parameters = {key: config[key] for key in EVAL_PARAMETERS if key in config}
            if self.progress_parameters.get("evaluation") != parameters:
                self.completed_actions.pop("evaluation", None)
            self.progress_parameters["evaluation"] = parameters
            self.completed_actions.setdefault("evaluation", set()).difference_update(self.current_targets)
            self.completed_actions.pop("compare_results", None)
            return
        effective = "check_eval_env" if action == "fix_eval_dependencies" else action
        stage = next((key for key, actions in PROGRESS_ACTIONS.items() if effective in actions), None)
        if stage is None:
            return
        parameters = {key: config[key] for key in PROGRESS_PARAMETERS[stage] if key in config}
        if self.progress_parameters.get(stage) != parameters:
            for name in PROGRESS_ACTIONS[stage]:
                self.completed_actions.pop(name, None)
        self.progress_parameters[stage] = parameters
        if effective in {"train", "merge"}:
            self.completed_actions.setdefault(effective, set()).difference_update(self.current_targets)
        else:
            self.completed_actions.pop(effective, None)
        stages = list(PROGRESS_ACTIONS)
        later_stages = [] if effective in {"check_training_env", "check_eval_env", "validate_data"} else stages[stages.index(stage) + 1:]
        for later in later_stages:
            for name in PROGRESS_ACTIONS[later]:
                self.completed_actions.pop(name, None)
            self.progress_parameters.pop(later, None)
        if later_stages:
            self.completed_actions.pop("evaluation", None)

    def progress(self, artifacts: dict[str, Any], evaluation_models: list[str] | None = None) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
        with self.lock:
            completed = {key: set(value) for key, value in self.completed_actions.items()}
            parameters = {key: dict(value) for key, value in self.progress_parameters.items()}
        result: dict[str, Any] = {}
        for stage, actions in PROGRESS_ACTIONS.items():
            artifact = artifacts.get(stage)
            if stage in {"checkpoints", "merged"}:
                result[stage] = {
                    name: ready is True and name in completed.get(actions[0], set())
                    for name, ready in (artifact or {}).items()
                }
            else:
                result[stage] = artifact is True and all(completed.get(action) for action in actions)
        return result, parameters

    def append(self, message: str) -> None:
        with self.lock:
            self.logs.append(message.rstrip("\r\n"))

    def start(self, command: list[str], label: str, action: str | None = None, config: dict[str, Any] | None = None) -> None:
        with self.lock:
            if self.status in {"running", "stopping"}:
                raise RuntimeError(f"已有任务正在运行：{self.label}")
            self._begin_progress(action, dict(config or {}), command)
            self.logs.clear()
            self.logs.append(f"准备执行：{label}")
            self.logs.append(f"工作目录：{PROJECT_ROOT}")
            self.status = "running"
            self.label = label
            self.exit_code = None
            self.started_at = time.time()
            self.finished_at = None
        threading.Thread(target=self._worker, args=(command,), daemon=True).start()

    def _worker(self, command: list[str]) -> None:
        environment = os.environ.copy()
        environment.update({"PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"})
        creationflags = 0
        if os.name == "nt":
            creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        try:
            with self.lock:
                if self.status == "stopping":
                    self.status = "stopped"
                    self.finished_at = time.time()
                    self.logs.append("任务已停止。")
                    return
                process = subprocess.Popen(
                    command,
                    cwd=PROJECT_ROOT,
                    env=environment,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    bufsize=1,
                    creationflags=creationflags,
                )
                self.process = process
                self.job = _windows_job(process)
            assert process.stdout is not None
            for line in process.stdout:
                self.append(line)
            code = process.wait()
            with self.lock:
                if self.status == "stopping":
                    self.status = "stopped"
                    self.logs.append("任务已停止。")
                elif code == 0:
                    self.status = "success"
                    self.logs.append("任务执行成功。")
                else:
                    self.status = "failed"
                    self.logs.append(f"任务执行失败，退出码：{code}")
                self.exit_code = code
                self.finished_at = time.time()
                self.process = None
                if self.job:
                    kernel, handle = self.job
                    kernel.CloseHandle(handle)
                    self.job = None
                if self.status == "success" and self.current_action:
                    action = self.current_action
                    outputs_after = self._output_stamps()
                    fresh = {name for name, stamps in outputs_after.items()
                             if all(value and value != before for value, before in zip(stamps, self.outputs_before.get(name, (None,) * len(stamps))))}
                    if action in {"train", "merge", "eval_run", "eval_score"}:
                        key = "evaluation" if action in {"eval_run", "eval_score"} else action
                        targets = self.current_targets if key == "evaluation" else self.current_targets.intersection(fresh)
                        self.completed_actions.setdefault(key, set()).update(targets)
                    elif any(action in actions for actions in PROGRESS_ACTIONS.values()):
                        if action == "check_eval_env" or "done" in fresh:
                            self.completed_actions[action] = {"done"}
                        else:
                            self.logs.append("未检测到本次更新的产物，实验进度不会按旧文件标记完成。")
        except Exception as exc:  # 后台线程必须把错误返回网页
            with self.lock:
                self.status = "failed"
                self.logs.append(f"无法启动任务：{type(exc).__name__}: {exc}")
                self.exit_code = -1
                self.finished_at = time.time()
                self.process = None
                if self.job:
                    kernel, handle = self.job
                    kernel.TerminateJobObject(handle, 1)
                    kernel.CloseHandle(handle)
                    self.job = None

    def stop(self) -> bool:
        with self.lock:
            process = self.process
            if self.status != "running":
                return False
            self.status = "stopping"
            self.logs.append("正在停止当前任务……")
            if self.job:
                kernel, handle = self.job
                if kernel.TerminateJobObject(handle, 1):
                    return True
        if process is None:
            return True
        if os.name == "nt":
            result = subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if result.returncode and process.poll() is None:
                process.terminate()
        else:
            try:
                process.terminate()
            except ProcessLookupError:
                pass
        return True

    def clear(self) -> None:
        with self.lock:
            if self.status not in {"running", "stopping"}:
                self.logs.clear()

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            return {
                "status": self.status,
                "label": self.label,
                "exit_code": self.exit_code,
                "started_at": self.started_at,
                "finished_at": self.finished_at,
                "logs": "\n".join(self.logs),
            }


TASKS = TaskManager()


def artifact_status() -> dict[str, Any]:
    experiment = PROJECT_ROOT / "experiments" / "module4"
    configs = PROJECT_ROOT / "configs" / "module4"
    checkpoints = {}
    active, _ = dataset_selection()
    for name in active:
        folder = experiment / "checkpoints" / name
        try:
            audit = json.loads((folder / "training_audit.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            audit = {}
        checkpoints[name] = (folder / "adapter_model.safetensors").exists() and audit.get("has_update") is True
    return {
        "environment_report": (experiment / "environment_report.json").exists(),
        "datasets": bool(list((experiment / "data").glob("dataset_manifest_*.json"))),
        "validation": bool(list((experiment / "data").glob("validation_report_*.json"))),
        "configs": (configs / "training_manifest.json").exists(),
        "checkpoints": checkpoints,
        "merged": {
            name: merged_model_ready(name)
            for name in active
        },
        "eval_manifest": (experiment / "evaluation" / "eval_manifest.json").exists(),
        "summary": (experiment / "results" / "summary.csv").exists(),
    }
