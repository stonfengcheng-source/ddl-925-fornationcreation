# FastAPI 后端

后端是项目的统一 API 服务，负责认证、任务、数据资产、边缘节点、联邦训练、通知、钱包和管理后台。

## 本地启动

默认配置为 SQLite + 本地免密模式，不需要创建 PostgreSQL 数据库：

```powershell
cd backend
.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:AUTH_MODE = "passwordless"
$env:USE_SQLITE = "true"
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

API 文档：http://localhost:8000/docs

项目首次启动会自动创建 `backend/data_task.db` 和 ORM 表。测试数据可选：

```powershell
.venv\Scripts\python.exe seed_test_data.py
```

免密开发账号：`admin`、`buyer`、`provider`。输入用户名即可登录，`admin` 默认拥有全部管理权限。

## 配置

复制 `.env.example` 为 `.env` 后按需修改。常用配置：

```env
APP_ENV=development
AUTH_MODE=passwordless
USE_SQLITE=true
DEV_AUTH_USERNAME=admin
```

密码认证模式使用 `AUTH_MODE=password`，此时登录接口会校验密码。PostgreSQL 仅作为可选生产/向量检索数据库：

```env
USE_SQLITE=false
DATABASE_URL=postgresql+psycopg2://postgres@localhost:5432/data_task_platform
```

PyCharm Database 工具不能作为 FastAPI 的运行时连接池；本地开发时请让 PyCharm SQLite 数据源直接打开 `data_task.db`。应用连接始终由 `DATABASE_URL`/`USE_SQLITE` 决定。

## 目录职责

```text
app/
├─ api/       路由和权限入口
├─ models/    SQLAlchemy ORM 模型
├─ schemas/   Pydantic 请求/响应结构
├─ services/  业务服务和异步任务
└─ core/      配置、数据库、异常处理
alembic/      可选数据库迁移
scripts/      pgvector 和语义检索辅助脚本
```

## 检查

```powershell
.venv\Scripts\python.exe -m compileall app
.venv\Scripts\python.exe -m pytest
```

后端没有安装 Python 时，先在 PyCharm 为 `backend` 选择可用解释器，再执行依赖安装；不要把 `.idea` 中的解释器名称当作系统命令。
