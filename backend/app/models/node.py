"""节点模型"""
from sqlalchemy import Column, String, DateTime, Integer, Float, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base


class Node(Base):
    __tablename__ = "nodes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    node_name = Column(String(100), nullable=False)
    status = Column(String(20), default="offline")  # online/offline/busy/maintenance
    node_type = Column(String(20), default="training")  # training/validation/hybrid
    ip_address = Column(String(45), nullable=True)
    port = Column(Integer, nullable=True)
    province = Column(String(50), nullable=True)
    city = Column(String(50), nullable=True)
    location = Column(String(100), nullable=True)

    # 资源
    cpu_cores = Column(Integer, nullable=True)
    cpu_usage = Column(Float, default=0)
    memory_total = Column(String(20), nullable=True)
    memory_usage = Column(Float, default=0)
    disk_usage = Column(Float, default=0)
    gpu_info = Column(String(200), nullable=True)
    network_bandwidth = Column(Float, default=0)

    # 历史统计
    total_tasks = Column(Integer, default=0)
    completed_tasks = Column(Integer, default=0)
    avg_contribution = Column(Float, default=0)
    health_score = Column(Integer, default=100)

    # 网络配置
    protocol = Column(String(20), default="grpc")
    ssl_enabled = Column(String(10), default="false")

    owner_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    last_heartbeat = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联
    owner = relationship("User", back_populates="nodes")
    datasets = relationship("Dataset", back_populates="node")
    assignments = relationship("TaskNodeAssignment", back_populates="node")
