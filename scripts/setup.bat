@echo off
chcp 65001 >nul
title 科研数据联邦流通平台 - 环境配置脚本
echo ==========================================
echo   科研数据联邦流通平台 - 一键环境配置
echo ==========================================
echo.

set PROJECT_DIR=%~dp0..
cd /d %PROJECT_DIR%

:: 设置 PostgreSQL 密码
set PGPASSWORD=159357

echo [1/5] 检查 PostgreSQL 服务状态...
psql -U postgres -c "SELECT 1;" >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] 无法连接到 PostgreSQL，请确保服务已启动
    echo     尝试启动 PostgreSQL 服务...
    net start postgresql-x64-15 >nul 2>&1
    net start postgresql-x64-16 >nul 2>&1
    net start postgresql-x64-17 >nul 2>&1
    net start postgresql >nul 2>&1
    timeout /t 2 >nul
)

echo [2/5] 创建数据库...
psql -U postgres -c "CREATE DATABASE data_task_platform;" >nul 2>&1
if %errorlevel% equ 0 (
    echo [✓] 数据库创建成功
) else (
    echo [!] 数据库已存在或创建失败，继续执行...
)

echo.
echo [3/5] 配置后端环境...
cd %PROJECT_DIR%\backend
if not exist venv (
    echo     创建虚拟环境...
    python -m venv venv
)
echo     安装后端依赖...
venv\Scripts\pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
if %errorlevel% equ 0 (
    echo [✓] 后端依赖安装完成
) else (
    echo [✗] 后端依赖安装失败
)

echo.
echo [4/5] 配置联邦学习环境...
cd %PROJECT_DIR%\federated-learning
if not exist venv (
    echo     创建虚拟环境...
    python -m venv venv
)
echo     安装联邦学习依赖（较大，请耐心等待）...
venv\Scripts\pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu -i https://pypi.tuna.tsinghua.edu.cn/simple
venv\Scripts\pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
if %errorlevel% equ 0 (
    echo [✓] 联邦学习依赖安装完成
) else (
    echo [✗] 联邦学习依赖安装失败
)

echo.
echo [5/5] 生成测试数据...
cd %PROJECT_DIR%\backend
venv\Scripts\python seed_test_data.py
if %errorlevel% equ 0 (
    echo [✓] 测试数据生成完成
) else (
    echo [!] 测试数据生成失败，可能已存在
)

echo.
echo ==========================================
echo   环境配置完成！
echo ==========================================
echo.
echo 下一步：运行 scripts\start-dev.bat 启动服务
echo.
pause
