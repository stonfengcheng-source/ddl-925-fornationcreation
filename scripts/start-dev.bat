@echo off
chcp 65001 >nul
title 科研数据联邦流通平台 v3.0 - 服务启动
echo ==========================================
echo   科研数据联邦流通平台 v3.0 - 服务启动
echo ==========================================
echo.

set PROJECT_DIR=%~dp0..
cd /d %PROJECT_DIR%

echo [1/2] 启动后端服务 (端口 8000)...
start "后端服务" cmd /k "cd %PROJECT_DIR%\backend && %PROJECT_DIR%\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

timeout /t 3 >nul

echo [2/2] 启动前端服务 (端口 5173)...
start "前端服务" cmd /k "cd %PROJECT_DIR%\frontend && npm run dev"

echo.
echo ==========================================
echo   服务启动完成！
echo ==========================================
echo.
echo 本机访问：
echo   - 前端: http://localhost:5173
echo   - 后端API: http://localhost:8000
echo   - API文档: http://localhost:8000/docs
echo   - 客户端下载: http://localhost:5173/download
echo.
echo 局域网访问（其他电脑）：
echo   请将 localhost 替换为本机IP地址
echo.
echo 测试账户：
echo   - buyer / Buyer123456 (需求方，Web端登录)
echo   - admin / Admin123456 (管理员，Web端 /admin-login)
echo   - provider_a / Provider123456 (数据提供方，桌面客户端登录)
echo   - provider_b / Provider123456 (数据提供方，桌面客户端登录)
echo.
pause
