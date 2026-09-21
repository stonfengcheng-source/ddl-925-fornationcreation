"""数据库连接配置。

默认使用 ``backend/data_task.db``，不依赖 PostgreSQL 用户密码。
如果需要 PostgreSQL，可显式设置 ``DATABASE_URL``，并将 ``USE_SQLITE=false``。
"""

from pathlib import Path
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

load_dotenv()

BACKEND_DIR = Path(__file__).resolve().parents[2]
SQLITE_PATH = BACKEND_DIR / "data_task.db"
DEFAULT_SQLITE_URL = f"sqlite:///{SQLITE_PATH.as_posix()}"

configured_database_url = os.getenv("DATABASE_URL", "").strip()
configured_use_sqlite = os.getenv("USE_SQLITE", "").lower() in ("1", "true", "yes")

# 没有显式数据库地址时默认 SQLite；显式设置 USE_SQLITE=true 时也强制使用 SQLite。
USE_SQLITE = (
    configured_use_sqlite
    or not configured_database_url
    or configured_database_url.lower().startswith("sqlite")
)
DATABASE_URL = DEFAULT_SQLITE_URL if USE_SQLITE else configured_database_url


def get_engine():
    """创建 SQLAlchemy 数据库引擎。"""
    sql_echo = os.getenv("SQL_ECHO", "false").lower() == "true"

    if USE_SQLITE:
        return create_engine(
            DATABASE_URL,
            echo=sql_echo,
            connect_args={"check_same_thread": False},
        )

    return create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        echo=sql_echo,
        connect_args={"connect_timeout": 10},
    )


# 创建数据库引擎
engine = get_engine()

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 声明基类
Base = declarative_base()


def init_db_extensions():
    """初始化 PostgreSQL 扩展；SQLite 模式不需要扩展。"""
    if USE_SQLITE:
        return

    try:
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
            print("[数据库] pgvector 扩展已就绪")
    except Exception as exc:
        print(f"[数据库] pgvector 扩展创建跳过: {exc}")
        print("[数据库] 如需语义匹配功能，请手动执行: CREATE EXTENSION vector;")


def ensure_schema_up_to_date():
    """为旧数据库补齐新增字段，兼容已有本地数据库文件。"""
    if USE_SQLITE:
        alter_statements = [
            "ALTER TABLE tasks ADD COLUMN dp_enabled INTEGER DEFAULT 0",
            "ALTER TABLE tasks ADD COLUMN dp_epsilon FLOAT",
            "ALTER TABLE tasks ADD COLUMN dp_delta FLOAT",
            "ALTER TABLE tasks ADD COLUMN dp_noise_multiplier FLOAT",
            "ALTER TABLE tasks ADD COLUMN dp_clipping_norm FLOAT",
            "ALTER TABLE tasks ADD COLUMN dp_adaptive INTEGER DEFAULT 0",
            "ALTER TABLE tasks ADD COLUMN dp_epsilon_consumed FLOAT DEFAULT 0.0",
            "ALTER TABLE tasks ADD COLUMN embedding TEXT",
            "ALTER TABLE datasets ADD COLUMN embedding TEXT",
        ]
    else:
        alter_statements = [
            "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS dp_enabled INTEGER DEFAULT 0",
            "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS dp_epsilon FLOAT",
            "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS dp_delta FLOAT",
            "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS dp_noise_multiplier FLOAT",
            "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS dp_clipping_norm FLOAT",
            "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS dp_adaptive INTEGER DEFAULT 0",
            "ALTER TABLE tasks ADD COLUMN IF NOT EXISTS dp_epsilon_consumed FLOAT DEFAULT 0.0",
        ]

    with engine.connect() as conn:
        for statement in alter_statements:
            try:
                conn.execute(text(statement))
            except Exception:
                # 字段已存在，或旧数据库尚未包含对应表；create_all 会负责新表。
                pass
        conn.commit()

    print("[数据库] 表结构同步检查完成")


def get_db():
    """FastAPI 数据库会话依赖。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
