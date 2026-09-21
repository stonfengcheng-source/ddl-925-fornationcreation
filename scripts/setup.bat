@echo off
chcp 65001 >nul
title 科研数据联邦流通平台 - 本地环境配置

set "PROJECT_DIR=%~dp0.."
cd /d "%PROJECT_DIR%"

echo ==========================================
echo   本地开发环境配置（SQLite + 免密登录）
echo ==========================================
echo.

if not exist "%PROJECT_DIR%\backend\.venv\Scripts\python.exe" (
    echo [1/4] 创建后端虚拟环境...
    py -3 -m venv "%PROJECT_DIR%\backend\.venv"
    if %errorlevel% neq 0 (
        echo [错误] 未找到可用 Python。请在 PyCharm 配置 Python 解释器后重试。
        pause
        exit /b 1
    )
) else (
    echo [1/4] 后端虚拟环境已存在
)

echo [2/4] 安装后端依赖...
call "%PROJECT_DIR%\backend\.venv\Scripts\python.exe" -m pip install -r "%PROJECT_DIR%\backend\requirements.txt"
if %errorlevel% neq 0 (
    echo [错误] 后端依赖安装失败，请检查网络或在 PyCharm Terminal 手动执行。
    pause
    exit /b 1
)

echo [3/4] 安装前端依赖...
cd /d "%PROJECT_DIR%\frontend"
call npm ci
if %errorlevel% neq 0 (
    echo [错误] 前端依赖安装失败，请检查 Node.js/npm 环境。
    pause
    exit /b 1
)

echo [4/4] 初始化本地测试数据...
cd /d "%PROJECT_DIR%\backend"
call "%PROJECT_DIR%\backend\.venv\Scripts\python.exe" seed_test_data.py

echo.
echo ==========================================
echo 配置完成。默认数据库：backend\data_task.db
echo 启动方式：scripts\start-dev.bat
echo 联邦学习环境为可选模块，请参阅 federated-learning\README.md
echo ==========================================
pause
