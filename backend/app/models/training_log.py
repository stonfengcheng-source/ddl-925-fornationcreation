"""训练日志模型"""
from sqlalchemy import Column, String, DateTime, Integer, Float, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base


class TrainingLog(Base):
    __tablename__ = "training_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String(36), ForeignKey("tasks.id"), nullable=False)
    round_number = Column(Integer, nullable=False)
    accuracy = Column(Float, nullable=True)
    loss = Column(Float, nullable=True)
    participants = Column(Integer, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    message = Column(Text, nullable=True)
    level = Column(String(10), default="info")  # info/warning/error
    created_at = Column(DateTime, default=datetime.utcnow)

    task = relationship("Task", back_populates="training_logs")
