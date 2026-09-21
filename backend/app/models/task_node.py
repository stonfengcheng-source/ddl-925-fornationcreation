"""任务-节点关联模型（匹配结果）"""
from sqlalchemy import Column, String, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base


class TaskNodeAssignment(Base):
    __tablename__ = "task_node_assignments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String(36), ForeignKey("tasks.id"), nullable=False)
    node_id = Column(String(36), ForeignKey("nodes.id"), nullable=False)
    dataset_id = Column(String(36), ForeignKey("datasets.id"), nullable=True)

    # 匹配打分
    match_score = Column(Float, default=0)
    tag_match_score = Column(Float, default=0)
    data_quantity_score = Column(Float, default=0)
    data_quality_score = Column(Float, default=0)
    resource_score = Column(Float, default=0)
    history_score = Column(Float, default=0)

    # 训练状态
    status = Column(String(20), default="assigned")  # assigned/accepted/training/completed/failed
    data_samples = Column(String(20), nullable=True)
    current_round = Column(String(20), nullable=True)

    assigned_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联
    task = relationship("Task", back_populates="assignments")
    node = relationship("Node", back_populates="assignments")
