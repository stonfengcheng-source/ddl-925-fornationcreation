# 后端服务

数据任务交易平台的后端API服务，基于 FastAPI 和 PostgreSQL。

## 环境要求

- Python 3.9+
- PostgreSQL 15+

## 快速开始

### 1. 安装依赖

```bash
cd backend
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

pip install -r requirements.txt
```

### 2. 配置数据库

创建 `.env` 文件（参考 `.env.example`）：

```bash
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/data_task_platform
```

### 3. 创建数据库

在 PostgreSQL 中创建数据库：

```sql
CREATE DATABASE data_task_platform;
```

### 4. 启动服务

```bash
uvicorn app.main:app --reload --port 8000
```

服务将在 http://localhost:8000 启动

API文档：http://localhost:8000/docs

## 项目结构

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 应用入口
│   ├── api/                 # API 路由层
│   │   └── tasks.py         # 任务相关接口
│   ├── models/              # 数据库 ORM 模型
│   │   └── task.py          # 任务模型
│   ├── schemas/             # Pydantic 数据模型
│   │   ├── common.py        # 通用响应格式
│   │   └── task.py          # 任务相关模型
│   ├── services/            # 业务逻辑层
│   └── core/                # 核心功能
│       ├── database.py      # 数据库连接
│       └── exceptions.py    # 自定义异常
├── requirements.txt         # Python 依赖
├── .env.example             # 环境变量示例
└── README.md                # 本文件
```

## API 端点

### 创建任务

```http
POST /api/tasks
Content-Type: application/json

{
  "task_name": "医疗影像分类模型训练",
  "task_category": "医疗影像分类",
  "task_description": "需要训练一个能够识别肺部CT影像中是否存在病变的深度学习模型",
  "task_tags": ["医疗", "影像", "分类"]
}
```

### 获取任务列表

```http
GET /api/tasks
```

### 获取任务详情

```http
GET /api/tasks/{task_id}
```

## 数据库表结构

### tasks 表

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | UUID | 主键 |
| task_name | VARCHAR(200) | 任务名称 |
| task_category | ENUM | 任务类别 |
| task_description | TEXT | 任务描述 |
| task_tags | ARRAY[VARCHAR] | 任务标签 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

## 开发说明

- 遵循 RESTful API 设计规范
- 使用 SQLAlchemy ORM 进行数据库操作
- 使用 Pydantic 进行数据验证
- 自动生成 API 文档（Swagger UI）
