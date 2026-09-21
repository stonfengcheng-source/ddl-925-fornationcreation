"""任务模型"""
from sqlalchemy import Column, String, DateTime, Integer, Float, Text, JSON, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base, USE_SQLITE

try:
    from pgvector.sqlalchemy import Vector as _Vector
    _HAS_PGVECTOR = True
except ImportError:
    _HAS_PGVECTOR = False

def _embedding_col():
    if _HAS_PGVECTOR and not USE_SQLITE:
        return Column(Vector(1536), nullable=True)
    return Column(Text, nullable=True)


class Task(Base):
    __tablename__ = "tasks"

    # 表级配置：HNSW 向量索引（仅 PostgreSQL）
    __table_args__ = (
        (Index(
            'idx_tasks_embedding',
            'embedding',
            postgresql_using='hnsw',
            postgresql_ops={'embedding': 'vector_cosine_ops'}
        ),) if (_HAS_PGVECTOR and not USE_SQLITE) else ()
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_name = Column(String(200), nullable=False)
    task_category = Column(String(50), nullable=False)
    task_description = Column(Text, nullable=False)
    task_tags = Column(JSON, default=list)
    status = Column(String(20), default="pending")  # pending/matching/training/completed/failed/cancelled/settled

    # 数据要求
    min_data_size = Column(Integer, default=1000)
    min_nodes = Column(Integer, default=2)
    max_nodes = Column(Integer, default=10)
    data_formats = Column(JSON, default=list)
    privacy_level = Column(String(20), default="medium")

    # 训练配置
    model_type = Column(String(50), nullable=True)
    optimizer = Column(String(20), nullable=True)
    learning_rate = Column(Float, nullable=True)
    batch_size = Column(Integer, nullable=True)
    local_epochs = Column(Integer, nullable=True)
    aggregation_strategy = Column(String(20), default="fedavg")
    target_accuracy = Column(Float, nullable=True)
    max_rounds = Column(Integer, nullable=True)
    current_round = Column(Integer, default=0)
    current_accuracy = Column(Float, nullable=True)

    # 差分隐私配置
    dp_enabled = Column(Integer, default=0)          # 0=关闭, 1=启用
    dp_epsilon = Column(Float, nullable=True)         # 隐私预算 ε
    dp_delta = Column(Float, nullable=True)           # 隐私失败概率 δ
    dp_noise_multiplier = Column(Float, nullable=True) # 噪声倍数
    dp_clipping_norm = Column(Float, nullable=True)   # 梯度裁剪范数
    dp_adaptive = Column(Integer, default=0)           # 0=固定裁剪, 1=自适应裁剪
    dp_epsilon_consumed = Column(Float, default=0.0)   # 已消耗的隐私预算

    # 预算
    reward_pool = Column(Float, default=0)
    reward_currency = Column(String(10), default="CNY")
    payment_method = Column(String(20), nullable=True)
    settlement_cycle = Column(String(20), nullable=True)

    # 进度
    progress = Column(Integer, default=0)
    participant_count = Column(Integer, default=0)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # 发布者
    publisher_id = Column(String(36), ForeignKey("users.id"), nullable=False)

    # 向量嵌入 (用于语义匹配)
    embedding = Column(_Vector(1536) if (_HAS_PGVECTOR and not USE_SQLITE) else Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联
    publisher = relationship("User", back_populates="tasks", foreign_keys=[publisher_id])
    assignments = relationship("TaskNodeAssignment", back_populates="task")
    training_logs = relationship("TrainingLog", back_populates="task")
    contributions = relationship("Contribution", back_populates="task")
