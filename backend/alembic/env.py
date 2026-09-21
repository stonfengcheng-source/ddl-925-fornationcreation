"""Alembic 环境配置"""
import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool, text

from alembic import context

# 添加后端应用目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.core.database import Base, DATABASE_URL
from app.models import (
    user,
    task,
    node,
    dataset,
    task_node,
    training_log,
    contribution,
    notification,
)

# Alembic Config 对象
config = context.config

# 使用数据库 URL 覆盖配置文件中的值
config.set_main_option("sqlalchemy.url", DATABASE_URL)

# 配置日志
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 元数据对象 (用于自动生成迁移)
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """离线模式运行迁移 (生成 SQL 脚本)"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """在线模式运行迁移 (直接操作数据库)"""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # 支持 pgvector 扩展
            include_schemas=True,
        )

        with context.begin_transaction():
            # Try to enable pgvector extension, skip if not available
            try:
                connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                print("pgvector extension enabled successfully")
            except Exception as e:
                # Rollback the failed transaction to allow further operations
                connection.rollback()
                print(f"Note: pgvector extension not available")
                print("Skipping pgvector initialization - embedding features will not work")
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
