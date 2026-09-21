"""数据集模型"""
from sqlalchemy import Column, String, DateTime, Integer, Float, Text, JSON, ForeignKey, BigInteger, Index
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base, USE_SQLITE

try:
    from pgvector.sqlalchemy import Vector as _Vector
    _HAS_PGVECTOR = True
except ImportError:
    _HAS_PGVECTOR = False


class Dataset(Base):
    __tablename__ = "datasets"

    # 表级配置：HNSW 向量索引（仅 PostgreSQL）
    __table_args__ = (
        (Index(
            'idx_datasets_embedding',
            'embedding',
            postgresql_using='hnsw',
            postgresql_ops={'embedding': 'vector_cosine_ops'}
        ),) if (_HAS_PGVECTOR and not USE_SQLITE) else ()
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    data_type = Column(String(20), nullable=False)  # csv/json/parquet/dicom/image
    status = Column(String(20), default="processing")  # ready/processing/error
    size_bytes = Column(BigInteger, nullable=True)
    row_count = Column(Integer, nullable=True)
    column_count = Column(Integer, nullable=True)
    tags = Column(JSON, default=list)
    quality_score = Column(Float, nullable=True)
    usage_count = Column(Integer, default=0)
    columns_info = Column(JSON, nullable=True)

    node_id = Column(String(36), ForeignKey("nodes.id"), nullable=True)
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=False)

    # 向量嵌入 (用于语义匹配)
    embedding = Column(_Vector(1536) if (_HAS_PGVECTOR and not USE_SQLITE) else Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联
    node = relationship("Node", back_populates="datasets")
    owner = relationship("User", back_populates="datasets")
