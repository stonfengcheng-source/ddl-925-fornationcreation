"""数据集相关 Pydantic 模型"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class DatasetCreate(BaseModel):
    """创建/上传数据集元信息"""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    data_type: str = Field(..., description="csv/json/parquet/dicom/image")
    size_bytes: Optional[int] = None
    row_count: Optional[int] = None
    column_count: Optional[int] = None
    tags: Optional[List[str]] = Field(default=[])
    quality_score: Optional[float] = None
    node_id: Optional[str] = None
    columns_info: Optional[list] = None


class DatasetResponse(BaseModel):
    """数据集响应"""
    id: str
    name: str
    description: Optional[str] = None
    data_type: str
    status: str = "processing"
    size_bytes: Optional[int] = None
    row_count: Optional[int] = None
    column_count: Optional[int] = None
    tags: List[str] = []
    quality_score: Optional[float] = None
    usage_count: int = 0
    columns_info: Optional[list] = None
    node_id: Optional[str] = None
    owner_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DatasetUpdate(BaseModel):
    """更新数据集"""
    name: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    status: Optional[str] = None
    quality_score: Optional[float] = None
