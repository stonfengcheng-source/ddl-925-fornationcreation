from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

PROJECT_ROOT = Path(__file__).resolve().parent
BACKEND_DIR = PROJECT_ROOT / "backend"
FRONTEND_DIR = PROJECT_ROOT / "frontend"
FL_DIR = PROJECT_ROOT / "federated-learning"


class StartupError(RuntimeError):
    """可直接向开发者展示的启动配置错误。"""


@dataclass
class ProcessHandle:
    """记录由本启动器创建的进程，便于退出时成组清理。"""

    name: str
    process: subprocess.Popen


def _print(message: str = "") -> None:
    """统一输出，保证 Windows 控制台下中文尽量及时显示。"""
    print(message, flush=True)


def _module_available(python_exe: Path, module: str) -> bool:
    """判断指定解释器是否安装了某个模块。"""
    try:
        result = subprocess.run(
            [str(python_exe), "-c", f"import {module}"],
            cwd=BACKEND_DIR if module == "uvicorn" else FL_DIR,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=8,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


def _existing_paths(paths: Iterable[Path]) -> list[Path]:
    """过滤空路径和不存在的路径，同时保持候选顺序。"""
    result: list[Path] = []
    seen: set[Path] = set()
    for path in paths:
        if not path:
            continue
        resolved = path.expanduser().resolve()
        if resolved not in seen and resolved.exists():
            result.append(resolved)
            seen.add(resolved)
    return result


def resolve_backend_python(explicit: Optional[str] = None) -> Path:
    """寻找能导入 uvicorn 的后端 Python。"""
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit))
    candidates.extend(
        [
            BACKEND_DIR / ".venv" / "Scripts" / "python.exe",
            BACKEND_DIR / ".venv" / "bin" / "python",
            PROJECT_ROOT / ".venv" / "Scripts" / "python.exe",
            PROJECT_ROOT / ".venv" / "bin" / "python",
            Path(sys.executable),
        ]
    )

    existing = _existing_paths(candidates)
    for python_exe in existing:
        if _module_available(python_exe, "uvicorn"):
            return python_exe

    expected = "\n".join(f"  - {path}" for path in existing) or "  - 未找到 Python 解释器"
    raise StartupError(
        "没有找到已安装 uvicorn 的 Python。候选解释器：\n"
        f"{expected}\n\n"
        "请先执行 scripts\\setup.bat，或在 backend 的 PyCharm 解释器中安装 "
        "backend\\requirements.txt。也可以用 --python 指定解释器。"
    )


def resolve_fl_python(backend_python: Path) -> Optional[Path]:
    """寻找联邦学习解释器；找不到时返回 None，不影响基础平台启动。"""
    candidates = _existing_paths(
        [
            FL_DIR / ".venv" / "Scripts" / "python.exe",
            FL_DIR / "venv" / "Scripts" / "python.exe",
            FL_DIR / ".venv" / "bin" / "python",
            FL_DIR / "venv" / "bin" / "python",
            backend_python,
            Path(sys.executable),
        ]
    )
    for python_exe in candidates:
        if _module_available(python_exe, "flwr"):
            return python_exe
    return None


def resolve_npm(explicit: Optional[str] = None) -> str:
    """寻找 npm 可执行文件。"""
    if explicit:
        npm = Path(explicit).expanduser()
        if npm.exists():
            return str(npm.resolve())
        raise StartupError(f"指定的 npm 不存在：{npm}")

    names = ["npm.cmd", "npm"] if os.name == "nt" else ["npm"]
    for name in names:
        found = shutil.which(name)
        if found:
            return found
    raise StartupError("没有找到 npm，请先安装 Node.js，或使用 --npm 指定 npm 路径。")


def check_project_files() -> None:
    """检查不会因环境不同而变化的项目结构。"""
    required = {
        "后端入口": BACKEND_DIR / "app" / "main.py",
        "前端配置": FRONTEND_DIR / "package.json",
        "前端入口": FRONTEND_DIR / "src" / "main.tsx",
    }
    missing = [f"{label}: {path}" for label, path in required.items() if not path.exists()]
    if missing:
        raise StartupError("项目结构不完整：\n" + "\n".join(f"  - {item}" for item in missing))


def check_frontend_dependencies() -> None:
    """Vite 是前端启动的必要依赖，避免 npm 启动后才给出模糊错误。"""
    vite_names = ["vite.cmd", "vite"] if os.name == "nt" else ["vite"]
    if not any((FRONTEND_DIR / "node_modules" / ".bin" / name).exists() for name in vite_names):
        raise StartupError(
            "没有找到前端依赖。请先执行：\n"
            "  cd frontend\n"
            "  npm ci"
        )


def _port_url(host: str, port: int, path: str) -> str:
    check_host = "127.0.0.1" if host in {"0.0.0.0", "::"} else host
    return f"http://{check_host}:{port}{path}"


def wait_for_health(process: subprocess.Popen, url: str, timeout: float = 30.0) -> bool:
    """等待后端健康接口；进程已退出时立即返回失败。"""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            return False
        try:
            with urllib.request.urlopen(url, timeout=1.5) as response:
                if 200 <= response.status < 300:
                    return True
        except (urllib.error.URLError, TimeoutError, OSError):
            time.sleep(0.5)
    return False


def process_creation_flags() -> int:
    """让 Windows 可以对每个进程组进行清理，其他平台不设置特殊标志。"""
    if os.name != "nt":
        return 0
    return getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)


def start_process(name: str, command: list[str], cwd: Path, env: dict[str, str]) -> ProcessHandle:
    """启动并返回一个由启动器负责的子进程。"""
    _print(f"[启动] {name}: {' '.join(command)}")
    try:
        process = subprocess.Popen(
            command,
            cwd=str(cwd),
            env=env,
            stdin=None,
            stdout=None,
            stderr=None,
            creationflags=process_creation_flags(),
        )
    except OSError as exc:
        raise StartupError(f"无法启动 {name}: {exc}") from exc
    return ProcessHandle(name, process)


def stop_process(handle: ProcessHandle) -> None:
    """停止进程及其子进程，不触碰项目文件。"""
    process = handle.process
    if process.poll() is not None:
        return

    _print(f"[停止] {handle.name}")
    if os.name == "nt":
        try:
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=8,
                check=False,
            )
            return
        except (OSError, subprocess.SubprocessError):
            pass

    try:
        process.terminate()
        process.wait(timeout=8)
    except (OSError, subprocess.TimeoutExpired):
        try:
            process.kill()
        except OSError:
            pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="科研数据联邦流通平台的一键开发启动器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "默认同时启动 FastAPI 和 Vite。联邦学习按任务启动；需要单机演示时加 --with-fl-demo。"
        ),
    )
    parser.add_argument("--check", action="store_true", help="只检查环境，不启动服务")
    parser.add_argument("--backend-only", action="store_true", help="只启动 FastAPI")
    parser.add_argument("--frontend-only", action="store_true", help="只启动 Vite")
    parser.add_argument("--with-fl-demo", action="store_true", help="额外启动一次 Flower 单机演示")
    parser.add_argument("--seed", action="store_true", help="启动前写入本地演示数据")
    parser.add_argument("--open", action="store_true", help="启动后打开前端地址")
    parser.add_argument("--no-reload", action="store_true", help="关闭后端 uvicorn 热重载")
    parser.add_argument("--python", help="指定后端 Python 解释器")
    parser.add_argument("--npm", help="指定 npm 可执行文件")
    parser.add_argument("--host", default="127.0.0.1", help="监听地址，默认 127.0.0.1")
    parser.add_argument("--backend-port", type=int, default=8000, help="FastAPI 端口，默认 8000")
    parser.add_argument("--frontend-port", type=int, default=5173, help="Vite 端口，默认 5173")
    parser.add_argument("--fl-rounds", type=int, default=2, help="Flower 演示轮次，默认 2")
    return parser.parse_args()


def build_env(fl_python: Optional[Path]) -> dict[str, str]:
    """生成只影响子进程的开发环境，不改写用户的全局环境。"""
    env = os.environ.copy()
    env.update(
        {
            "AUTH_MODE": "passwordless",
            "USE_SQLITE": "true",
            "PYTHONUNBUFFERED": "1",
        }
    )
    if fl_python:
        env["FL_PYTHON"] = str(fl_python)
    return env


def run_seed(python_exe: Path, env: dict[str, str]) -> None:
    """可选地初始化完整的本地演示数据。"""
    _print("[准备] 初始化本地演示数据...")
    result = subprocess.run(
        [str(python_exe), "seed_test_data.py"],
        cwd=str(BACKEND_DIR),
        env=env,
        check=False,
    )
    if result.returncode != 0:
        raise StartupError(f"演示数据初始化失败，返回码：{result.returncode}")


def run_check(args: argparse.Namespace) -> int:
    """执行启动前检查并输出清晰结果。"""
    check_project_files()
    backend_python = None
    if not args.frontend_only:
        backend_python = resolve_backend_python(args.python)
        _print(f"[通过] 后端 Python: {backend_python}")
    if not args.backend_only:
        npm = resolve_npm(args.npm)
        check_frontend_dependencies()
        _print(f"[通过] npm: {npm}")
    if args.with_fl_demo:
        if not backend_python:
            backend_python = resolve_backend_python(args.python)
        fl_python = resolve_fl_python(backend_python)
        if not fl_python:
            raise StartupError(
                "未找到安装 flwr 的 Python。请按 federated-learning\\README.md 安装联邦学习依赖。"
            )
        _print(f"[通过] 联邦学习 Python: {fl_python}")
    _print("[通过] 项目结构和运行依赖检查完成")
    return 0


def run(args: argparse.Namespace) -> int:
    if args.backend_only and args.frontend_only:
        raise StartupError("--backend-only 和 --frontend-only 不能同时使用。")

    check_project_files()
    backend_python = None if args.frontend_only else resolve_backend_python(args.python)
    npm = None if args.backend_only else resolve_npm(args.npm)
    if not args.backend_only:
        check_frontend_dependencies()

    fl_python = resolve_fl_python(backend_python) if backend_python else None
    if args.with_fl_demo and not fl_python:
        raise StartupError(
            "未找到安装 flwr 的 Python。请先安装 federated-learning\\requirements.txt。"
        )

    env = build_env(fl_python)
    handles: list[ProcessHandle] = []
    core_handles: list[ProcessHandle] = []

    try:
        if args.seed and backend_python:
            run_seed(backend_python, env)

        if backend_python:
            backend_command = [
                str(backend_python),
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                args.host,
                "--port",
                str(args.backend_port),
            ]
            if not args.no_reload:
                backend_command.append("--reload")
            backend = start_process("FastAPI 后端", backend_command, BACKEND_DIR, env)
            handles.append(backend)
            core_handles.append(backend)

            health_url = _port_url(args.host, args.backend_port, "/health")
            _print(f"[等待] 后端健康检查: {health_url}")
            if not wait_for_health(backend.process, health_url):
                if backend.process.poll() is not None:
                    raise StartupError(
                        f"后端启动失败，返回码：{backend.process.returncode}。请查看上面的后端日志。"
                    )
                _print("[警告] 后端暂未响应健康检查，将继续启动前端；请留意后端日志。")
            else:
                _print("[就绪] FastAPI 已启动")

        if npm:
            frontend_command = [
                npm,
                "run",
                "dev",
                "--",
                "--host",
                args.host,
                "--port",
                str(args.frontend_port),
            ]
            frontend = start_process("React/Vite 前端", frontend_command, FRONTEND_DIR, env)
            handles.append(frontend)
            core_handles.append(frontend)

        if args.with_fl_demo:
            fl_command = [
                str(fl_python),
                str(FL_DIR / "simulation.py"),
                "--rounds",
                str(args.fl_rounds),
                "--num-clients",
                "2",
                "--model-type",
                "breast_cancer",
            ]
            handles.append(start_process("Flower 单机演示", fl_command, FL_DIR, env))

        _print("")
        _print("=" * 64)
        _print("平台已启动，按 Ctrl+C 可同时停止本次启动的全部进程")
        if not args.backend_only:
            _print(f"前端: http://{args.host}:{args.frontend_port}")
        if not args.frontend_only:
            _print(f"后端: http://{args.host}:{args.backend_port}")
            _print(f"文档: http://{args.host}:{args.backend_port}/docs")
        _print("登录: admin（本地免密开发模式）")
        _print("=" * 64)

        if args.open and not args.backend_only:
            webbrowser.open(f"http://{args.host}:{args.frontend_port}")

        while True:
            for handle in core_handles:
                return_code = handle.process.poll()
                if return_code is not None:
                    raise StartupError(f"{handle.name}已退出，返回码：{return_code}。")
            time.sleep(0.5)
    except KeyboardInterrupt:
        _print("\n[退出] 收到 Ctrl+C，正在停止服务...")
        return 0
    finally:
        for handle in reversed(handles):
            stop_process(handle)


def main() -> int:
    args = parse_args()
    try:
        if args.check:
            return run_check(args)
        return run(args)
    except StartupError as exc:
        _print(f"[错误] {exc}")
        return 1
    except KeyboardInterrupt:
        _print("\n[退出] 已取消。")
        return 130

if __name__ == "__main__":
    raise SystemExit(main())
