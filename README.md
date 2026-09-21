# 科研数据联邦流通平台

一个由 React/Vite 前端、FastAPI 后端、SQLAlchemy 数据层和 Flower 联邦学习模块组成的科研数据协作平台。平台覆盖数据资产、任务发布、节点管理、质量规则、语义匹配、隐私预算、联邦训练和管理后台等功能。

## 当前本地开发约定

- 数据库默认使用 `backend/data_task.db`（SQLite），不需要 PostgreSQL 用户密码。
- 登录默认使用本地免密模式：在登录页输入 `admin` 即可进入全权限管理后台；也可以输入 `buyer` 或 `provider` 体验对应角色。
- 免密模式只适合本机开发，启动脚本绑定 `127.0.0.1`，不要直接暴露到公网。
- JWT 仍用于维持前端会话，但它是内部会话签名，不是用户登录密码。
- 语义向量服务和联邦学习依赖均为可选能力；未配置 API Key 时，基础平台仍可启动。

## 项目结构

```text
clean/
├─ backend/                       # FastAPI API 服务
│  ├─ app/
│  │  ├─ api/                     # 路由：认证、任务、数据集、节点、训练、管理后台等
│  │  ├─ models/                  # SQLAlchemy ORM 模型
│  │  ├─ schemas/                 # Pydantic 请求/响应模型
│  │  ├─ services/                # 认证、语义匹配、预评估、通知等业务服务
│  │  └─ core/                    # 配置、数据库、异常处理
│  ├─ alembic/                    # 数据库迁移脚本
│  ├─ scripts/                    # pgvector 和语义检索辅助脚本
│  ├─ seed_test_data.py           # 本地测试数据
│  ├─ requirements.txt            # 后端运行依赖
│  └─ .env.example                # 环境变量模板
├─ frontend/                      # React + TypeScript + Vite 前端
│  ├─ src/pages/                  # 页面模块
│  ├─ src/components/             # 通用组件
│  ├─ src/services/               # API 请求封装
│  ├─ src/store/                  # Zustand 状态
│  └─ package.json                # 前端脚本和依赖
├─ federated-learning/            # Flower 联邦学习实验模块
│  ├─ models/                     # 六类表格数据模型
│  ├─ datasets/                   # 数据集加载和分区
│  ├─ simulation.py               # 单机模拟入口
│  ├─ server.py / run_client.py   # 多进程服务端/客户端入口
│  └─ requirements.txt            # 联邦学习依赖
├─ scripts/                       # Windows 启动、初始化和说明
├─ CONTRIBUTING.md                # Git 协作规范
└─ README.md                     # 本文件
```

## 快速启动（Windows + PyCharm）

### 1. 准备解释器

项目当前 PyCharm 配置指向 `pytorch_env`。如果该解释器不存在，请在 PyCharm 中为 `backend` 选择一个 Python 3.10–3.12 解释器，或在项目根目录执行：

```powershell
py -3.11 -m venv backend\.venv
```

如果 `py` 也不可用，需要先安装 Python，并在安装时勾选加入 PATH；不要把缺失环境当成代码问题。

### 2. 安装平台依赖

```powershell
cd D:\PythonProject\clean
backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
cd frontend
npm ci
```

也可以双击 `scripts\setup.bat`。该脚本只配置本地 SQLite、后端依赖、前端依赖和测试数据，不再写入 PostgreSQL 密码。

### 3. 启动服务

最简单的方式是双击：

```text
scripts\start-dev.bat
```

或者打开两个 PyCharm Terminal：

```powershell
# Terminal 1：后端
cd backend
$env:AUTH_MODE = "passwordless"
$env:USE_SQLITE = "true"
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# Terminal 2：前端
cd frontend
npm run dev
```

访问地址：

- 前端：http://localhost:5173
- 后端健康检查：http://localhost:8000/health
- Swagger：http://localhost:8000/docs

### 4. 登录

在首页或管理员入口输入以下用户名之一，密码留空：

| 用户名 | 角色 | 用途 |
|---|---|---|
| `admin` | 管理员 | 全部管理权限，推荐自查使用 |
| `buyer` | 需求方 | 任务发布和需求方页面 |
| `provider` | 数据提供方 | 数据资产和节点页面 |

首次启动时，后端会自动创建缺少的本地开发账号；也可以执行 `backend\seed_test_data.py` 创建完整演示数据。

## PyCharm 数据库连接

PyCharm 的 Database 工具负责浏览和执行 SQL，FastAPI 运行时仍通过 SQLAlchemy 连接数据库，不能直接复用 IDE 内部连接池。当前两者使用的是同一个 SQLite 文件：

1. 先启动一次后端，使 `backend/data_task.db` 创建出来。
2. 在 PyCharm 右侧 Database 窗口选择 `+` → `Data Source` → `SQLite`。
3. 数据库文件选择项目中的 `backend/data_task.db`。
4. 连接后即可查看 `users`、`tasks`、`datasets`、`nodes` 等表。

如确实要使用 PostgreSQL，在 `backend/.env` 设置 `USE_SQLITE=false` 和 `DATABASE_URL`。是否免密码由 PostgreSQL 自己的认证策略决定，项目不会再内置或写死数据库密码。

## 检查与测试

```powershell
# 前端类型检查和生产构建
cd frontend
npm run build

# 前端单元测试
npm test

# 后端测试（安装 pytest、pytest-asyncio 后）
cd ..\backend
.venv\Scripts\python.exe -m pytest
```

联邦学习单机验证：

```powershell
cd federated-learning
py -3.11 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe generate_csv_datasets.py
.venv\Scripts\python.exe simulation.py --rounds 2 --num-clients 2 --model-type breast_cancer
```

## 配置说明

后端配置参考 [backend/.env.example](backend/.env.example)，前端配置参考 [frontend/.env.example](frontend/.env.example)。重要开关：

| 变量 | 默认值 | 说明 |
|---|---|---|
| `AUTH_MODE` | `passwordless` | `passwordless` 为本地免密；`password` 启用密码认证 |
| `DEV_AUTH_USERNAME` | `admin` | 无 Token 访问时使用的本地账号 |
| `USE_SQLITE` | 自动启用 | 本地无需数据库密码 |
| `DATABASE_URL` | SQLite 文件 | 仅在切换 PostgreSQL 时设置 |
| `EMBEDDING_PROVIDER` | `openai` | 未配置 Key 时向量生成会跳过，不影响基础启动 |

## 已知边界

- `federated-learning` 是独立实验模块，不是后端启动的硬依赖。
- pgvector 只在 PostgreSQL 模式下启用；SQLite 模式会把 embedding 保存为文本，基础 CRUD 可用，但不提供向量索引。
- 生产环境必须关闭免密模式、设置强随机 `SECRET_KEY`、配置真实 CORS 来源，并启用数据库认证。
- 如果 PyCharm 中看不到 Python 解释器或 Node/npm，先按上面的环境准备步骤安装，项目本身不会自动下载系统级运行时。
