"""节点相关 Pydantic 模型"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class NodeCreate(BaseModel):
    """注册节点"""
    node_name: str = Field(..., min_length=1, max_length=100)
    node_type: str = Field(default="training")
    ip_address: Optional[str] = None
    port: Optional[int] = None
    province: Optional[str] = None
    city: Optional[str] = None
    location: Optional[str] = None
    cpu_cores: Optional[int] = None
    memory_total: Optional[str] = None
    gpu_info: Optional[str] = None
    protocol: str = Field(default="grpc")
    ssl_enabled: str = Field(default="false")


class NodeResponse(BaseModel):
    """节点响应"""
    id: str
    node_name: str
    status: str = "offline"
    node_type: str = "training"
    ip_address: Optional[str] = None
    port: Optional[int] = None
    province: Optional[str] = None
    city: Optional[str] = None
    location: Optional[str] = None
    cpu_cores: Optional[int] = None
    cpu_usage: float = 0
    memory_total: Optional[str] = None
    memory_usage: float = 0
    disk_usage: float = 0
    gpu_info: Optional[str] = None
    network_bandwidth: float = 0
    total_tasks: int = 0
    completed_tasks: int = 0
    avg_contribution: float = 0
    health_score: int = 100
    owner_id: Optional[str] = None
    last_heartbeat: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class NodeHeartbeat(BaseModel):
    """节点心跳上报"""
    cpu_usage: float = 0
    memory_usage: float = 0
    disk_usage: float = 0
    network_bandwidth: float = 0
    status: str = "online"


class NodeUpdate(BaseModel):
    """更新节点"""
    node_name: Optional[str] = None
    node_type: Optional[str] = None
    ip_address: Optional[str] = None
    port: Optional[int] = None
    location: Optional[str] = None
    status: Optional[str] = None
