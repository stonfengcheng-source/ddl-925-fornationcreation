"""贡献度模型"""
from sqlalchemy import Column, String, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base


class Contribution(Base):
    __tablename__ = "contributions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String(36), ForeignKey("tasks.id"), nullable=False)
    node_id = Column(String(36), ForeignKey("nodes.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)

    data_quality_score = Column(Float, default=0)
    data_quantity_score = Column(Float, default=0)
    computation_score = Column(Float, default=0)
    timeliness_score = Column(Float, default=0)
    overall_score = Column(Float, default=0)

    share_percentage = Column(Float, default=0)
    reward_amount = Column(Float, default=0)
    reward_currency = Column(String(10), default="CNY")
    settlement_status = Column(String(20), default="pending")  # pending/settled

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    task = relationship("Task", back_populates="contributions")
