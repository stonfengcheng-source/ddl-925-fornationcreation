"""
FastAPI 应用主入口
"""
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.api import tasks, auth, datasets, nodes, training, wallet, profile, notifications, admin
from app.core.database import engine, Base, init_db_extensions, ensure_schema_up_to_date
from app.core.exceptions import APIException
from datetime import datetime

# 显式导入所有模型，确保 Base.metadata 包含全部表定义
import app.models  # noqa: F401

# 初始化数据库扩展（pgvector）并创建表
try:
    init_db_extensions()
    Base.metadata.create_all(bind=engine)
    ensure_schema_up_to_date()
    print("[启动] 数据库表创建/检查完成")
except Exception as e:
    print(f"[启动] 数据库表创建失败: {e}")
    print("[启动] 请检查:")
    print("  1. PostgreSQL 是否已创建数据库 data_task_platform")
    print("  2. 是否已安装 pgvector 扩展 (SQL: CREATE EXTENSION vector)")
    print("  3. 或设置环境变量 USE_SQLITE=true 使用 SQLite")
    raise

app = FastAPI(
    title="数据任务交易平台 API",
    description="基于联邦学习的数据任务交易平台 RESTful API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源（测试环境）
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router, prefix="/api")
app.include_router(tasks.router, prefix="/api/tasks", tags=["任务"])
app.include_router(datasets.router, prefix="/api/datasets", tags=["数据集"])
app.include_router(nodes.router, prefix="/api/nodes", tags=["节点"])
app.include_router(training.router, prefix="/api/training", tags=["联邦训练"])
app.include_router(wallet.router, prefix="/api/wallet", tags=["钱包"])
app.include_router(profile.router, prefix="/api/profile", tags=["个人资料"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["通知"])
app.include_router(admin.router, prefix="/api/admin", tags=["管理后台"])

@app.get("/")
async def root():
    return {
        "message": "数据任务交易平台 API",
        "docs": "/docs",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "healthy"}


# 全局异常处理
@app.exception_handler(APIException)
async def api_exception_handler(request: Request, exc: APIException):
    """自定义异常处理"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.detail.get("error", {}).get("message", str(exc.detail)),
                "details": exc.details or []
            },
            "meta": {
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """参数验证错误处理"""
    details = []
    for error in exc.errors():
        field_path = ".".join(str(loc) for loc in error["loc"][1:])
        details.append({
            "field": field_path,
            "message": error["msg"]
        })
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "请求参数验证失败",
                "details": details
            },
            "meta": {
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """未捕获异常处理"""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "服务器内部错误"
            },
            "meta": {
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        }
    )
