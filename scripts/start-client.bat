@echo off
chcp 65001 >nul
title 联邦学习客户端节点

set "PROJECT_DIR=%~dp0.."
set "FL_DIR=%PROJECT_DIR%\federated-learning"
cd /d "%FL_DIR%"

if not exist "%FL_DIR%\.venv\Scripts\python.exe" (
    echo [错误] 未找到 federated-learning\.venv
    echo 请先按 federated-learning\README.md 安装联邦学习依赖。
    pause
    exit /b 1
)

echo 示例：run_client.py --node-id 0 --server 127.0.0.1:8080
call "%FL_DIR%\.venv\Scripts\python.exe" run_client.py %*
pause
