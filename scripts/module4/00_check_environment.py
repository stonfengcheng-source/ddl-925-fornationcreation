"""检查第四模块本地训练与评测环境，不安装或修改任何依赖。"""
from __future__ import annotations

import argparse
import importlib.metadata
import importlib.util
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path


def package_status(import_name: str, distribution_name: str | None = None):
    available = importlib.util.find_spec(import_name) is not None
    version = None
    if available:
        try:
            version = importlib.metadata.version(distribution_name or import_name)
        except importlib.metadata.PackageNotFoundError:
            version = "unknown"
    return {"available": available, "version": version}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="experiments/module4/environment_report.json")
    parser.add_argument("--strict", action="store_true", help="训练依赖缺失时返回非零退出码")
    args = parser.parse_args()

    packages = {
        "torch": package_status("torch"),
        "transformers": package_status("transformers"),
        "datasets": package_status("datasets"),
        "peft": package_status("peft"),
        "llamafactory": package_status("llamafactory", "llamafactory"),
    }
    cuda = {"available": False, "device_count": 0, "devices": []}
    if packages["torch"]["available"]:
        import torch

        cuda["available"] = bool(torch.cuda.is_available())
        cuda["device_count"] = int(torch.cuda.device_count())
        cuda["devices"] = [torch.cuda.get_device_name(index) for index in range(torch.cuda.device_count())]
        cuda["torch_cuda_version"] = torch.version.cuda

    script_dir = Path(sys.executable).resolve().parent
    llamafactory_candidates = (
        script_dir / "llamafactory-cli.exe",
        script_dir / "llamafactory-cli",
    )
    local_llamafactory = next(
        (str(candidate) for candidate in llamafactory_candidates if candidate.exists()),
        None,
    )
    commands = {
        "llamafactory-cli": local_llamafactory or shutil.which("llamafactory-cli"),
        "opencompass": shutil.which("opencompass"),
        "nvidia-smi": shutil.which("nvidia-smi"),
    }
    nvidia_smi = {"available": bool(commands["nvidia-smi"]), "gpus": [], "error": None}
    if commands["nvidia-smi"]:
        try:
            result = subprocess.run(
                [
                    commands["nvidia-smi"],
                    "--query-gpu=name,memory.total,driver_version",
                    "--format=csv,noheader",
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                nvidia_smi["gpus"] = [line.strip() for line in result.stdout.splitlines() if line.strip()]
            else:
                nvidia_smi["error"] = result.stderr.strip() or f"exit={result.returncode}"
        except (OSError, subprocess.SubprocessError) as exc:
            nvidia_smi["error"] = str(exc)
    report = {
        "python": {
            "version": platform.python_version(),
            "executable": sys.executable,
            "platform": platform.platform(),
        },
        "packages": packages,
        "commands": commands,
        "cuda": cuda,
        "nvidia_smi": nvidia_smi,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Python: {report['python']['version']} ({sys.executable})")
    for name, status in packages.items():
        version = status["version"] or "未安装"
        marker = "OK" if status["available"] else "MISSING"
        print(f"[{marker}] {name}: {version}")
    if cuda["available"]:
        print(f"[OK] CUDA（统一计算设备架构）: {', '.join(cuda['devices'])}")
    else:
        print("[MISSING] CUDA（统一计算设备架构）当前不可用")
    if nvidia_smi["gpus"]:
        for gpu in nvidia_smi["gpus"]:
            print(f"[GPU] {gpu}")
    print(f"报告: {output.resolve()}")

    required = ("torch", "transformers", "datasets", "peft", "llamafactory")
    ready = all(packages[name]["available"] for name in required) and commands["llamafactory-cli"]
    if args.strict and not ready:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
