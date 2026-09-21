@echo off
chcp 65001 >nul
title 数据提供方客户端启动器
echo ==========================================
echo   数据提供方桌面客户端启动
echo ==========================================
echo.

set PROJECT_DIR=%~dp0..
cd /d %PROJECT_DIR%\client

echo 启动客户端...
echo.
echo 首次运行会自动安装依赖，请耐心等待
echo.

if not exist venv (
    echo 创建虚拟环境...
    python -m venv venv
)

echo 安装/检查依赖...
venv\Scripts\pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

echo.
echo 启动客户端 GUI...
venv\Scripts\pythonw client_app.pyw

if %errorlevel% neq 0 (
    echo.
    echo 启动失败，尝试使用控制台模式...
    venv\Scripts\python client_app.pyw
)

echo.
pause
