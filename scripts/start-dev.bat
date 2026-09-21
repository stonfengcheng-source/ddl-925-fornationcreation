@echo off
chcp 65001 >nul
title 科研数据联邦流通平台 - 本地开发

set "PROJECT_DIR=%~dp0.."
cd /d "%PROJECT_DIR%"

if not exist "%PROJECT_DIR%\backend\.venv\Scripts\python.exe" (
    echo [错误] 未找到 backend\.venv\Scripts\python.exe
    echo 请先在 PyCharm 为 backend 配置 Python 解释器，或运行 scripts\setup.bat。
    pause
    exit /b 1
)

if not exist "%PROJECT_DIR%\frontend\node_modules\.bin\vite.cmd" (
    echo [错误] 前端依赖未安装，请先运行：cd frontend ^&^& npm ci
    pause
    exit /b 1
)

echo [1/2] 启动后端（SQLite + 本地免密）...
start "后端服务" cmd /k "cd /d %PROJECT_DIR%\backend ^&^& set AUTH_MODE=passwordless ^&^& set USE_SQLITE=true ^&^& %PROJECT_DIR%\backend\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

timeout /t 2 >nul

echo [2/2] 启动前端...
start "前端服务" cmd /k "cd /d %PROJECT_DIR%\frontend ^&^& npm run dev"

echo.
echo 前端:   http://localhost:5173
echo 后端:   http://localhost:8000
echo 文档:   http://localhost:8000/docs
echo 登录:   输入 admin，无需密码
echo.
pause
