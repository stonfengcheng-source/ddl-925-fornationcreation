"""通知模型"""
from sqlalchemy import Column, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    type = Column(String(20), default="system")  # system/task/message/reward/security
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=True)
    is_read = Column(Boolean, default=False)
    priority = Column(String(10), default="normal")  # high/normal/low
    action_url = Column(String(500), nullable=True)
    related_id = Column(String(36), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="notifications")
