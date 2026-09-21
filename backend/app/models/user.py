"""用户模型"""
from sqlalchemy import Column, String, DateTime, Boolean, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=True)
    password = Column(String(200), nullable=True)
    user_type = Column(String(20), nullable=False, default="buyer")  # buyer / provider / admin
    nickname = Column(String(100), nullable=True)
    avatar = Column(String(500), nullable=True)
    phone = Column(String(20), nullable=True)
    bio = Column(Text, nullable=True)
    gender = Column(String(10), nullable=True)
    location = Column(String(100), nullable=True)
    real_name = Column(String(50), nullable=True)
    verified = Column(Boolean, default=False)
    status = Column(String(20), default="active")  # active / inactive / suspended
    wechat_openid = Column(String(100), unique=True, nullable=True)
    balance = Column(String(20), default="0")
    last_login_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联
    tasks = relationship("Task", back_populates="publisher", foreign_keys="Task.publisher_id")
    nodes = relationship("Node", back_populates="owner")
    datasets = relationship("Dataset", back_populates="owner")
    notifications = relationship("Notification", back_populates="user")
