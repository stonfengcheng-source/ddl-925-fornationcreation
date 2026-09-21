"""
数据库连接配置
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 数据库连接配置
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:159357@localhost:5432/data_task_platform"
)

# 是否使用 SQLite（自动检测或强制指定）
USE_SQLITE = os.getenv("USE_SQLITE", "").lower() in ("1", "true", "yes")

def get_engine():
    """创建数据库引擎，支持 PostgreSQL 和 SQLite"""
    global DATABASE_URL, USE_SQLITE

    # 如果 PostgreSQL 不可用，自动回退到 SQLite
    if not USE_SQLITE and DATABASE_URL.startswith("postgresql"):
        try:
            import psycopg2
            conn = psycopg2.connect(DATABASE_URL, connect_timeout=3)
            conn.close()
        except Exception:
            print("[数据库] PostgreSQL 不可用，自动回退到 SQLite")
            USE_SQLITE = True

    if USE_SQLITE:
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data_task.db")
        DATABASE_URL = f"sqlite:///{db_path}"
        return create_engine(
            DATABASE_URL,
            echo=False,
            connect_args={"check_same_thread": False},
        )

    return create_engine(
        DATABASE_URL,
        pool_pre_ping=False,
        echo=True,
        connect_args={'connect_timeout': 10}
    )

# 创建数据库引擎
engine = get_engine()

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 声明基类
Base = declarative_base()

def init_db_extensions():
    """
    初始化数据库扩展（如 pgvector）
    在 create_all 之前调用，确保 PostgreSQL 扩展已安装
    """
    if USE_SQLITE:
        return
    try:
        with engine.connect() as conn:
            conn.execute(
                __import__('sqlalchemy').text("CREATE EXTENSION IF NOT EXISTS vector")
            )
            conn.commit()
            print("[数据库] pgvector 扩展已就绪")
    except Exception as e:
        print(f"[数据库] pgvector 扩展创建跳过: {e}")
        print("[数据库] 如需语义匹配功能，请手动执行: CREATE EXTENSION vector;")


def ensure_schema_up_to_date():
    """
    自动为已存在的表补齐缺失列（兼容旧数据库）
    create_all() 只会创建不存在的表，不会修改已有表。
    此函数在 create_all() 之后调用，确保旧表也包含新增列。
    """
    from sqlalchemy import text

    if USE_SQLITE:
        # SQLite 用 ALTER TABLE ADD COLUMN（不支持 IF NOT EXISTS，需 try/except）
        alter_statements = [
            # tasks 表 — 差分隐私字段
            "ALTER TABLE tasks ADD COLUMN dp_enabled INTEGER DEFAULT 0",
            "ALTER TABLE tasks ADD COLUMN dp_epsilon FLOAT",
            "ALTER TABLE tasks ADD COLUMN dp_delta FLOAT",
            "ALTER TABLE tasks ADD COLUMN dp_noise_multiplier FLOAT",
            "ALTER TABLE tasks ADD COLUMN dp_clipping_norm FLOAT",
            "ALTER TABLE tasks ADD COLUMN dp_adaptive INTEGER DEFAULT 0",
            "ALTER TABLE tasks ADD COLUMN dp_epsilon_consumed FLOAT DEFAULT 0.0",
            # tasks 表 — embedding
            "ALTER TABLE tasks ADD COLUMN embedding TEXT",
            # datasets 表 — embedding
            "ALTER TABLE datasets ADD COLUMN embedding TEXT",
        ]
        with engine.connect() as conn:
            for stmt in alter_statements:
                try:
                    conn.execute(text(stmt))
                except Exception:
                    pass  # 列已存在，跳过
            conn.commit()
    else:
        # PostgreSQL 支持 ADD COLUMN IF NOT EXISTS
        alter_statements = [
            # tasks 表 — 差分隐私字段
            "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS dp_enabled INTEGER DEFAULT 0",
            "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS dp_epsilon FLOAT",
            "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS dp_delta FLOAT",
            "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS dp_noise_multiplier FLOAT",
            "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS dp_clipping_norm FLOAT",
            "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS dp_adaptive INTEGER DEFAULT 0",
            "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS dp_epsilon_consumed FLOAT DEFAULT 0.0",
        ]
        with engine.connect() as conn:
            for stmt in alter_statements:
                try:
                    conn.execute(text(stmt))
                except Exception:
                    pass
            conn.commit()
    print("[数据库] 表结构同步检查完成")


def get_db():
    """
    获取数据库会话（依赖注入）
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
