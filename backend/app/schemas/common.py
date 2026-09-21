"""
通用响应格式
"""
from typing import Generic, TypeVar, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

T = TypeVar('T')

class Meta(BaseModel):
    """响应元数据"""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: Optional[str] = None

class Pagination(BaseModel):
    """分页信息"""
    page: int
    per_page: int
    total: int
    total_pages: int
    links: Optional[Dict[str, str]] = None

class PaginationMeta(Meta):
    """带分页的元数据"""
    pagination: Pagination

class SuccessResponse(BaseModel, Generic[T]):
    """成功响应格式"""
    data: T
    meta: Meta = Field(default_factory=Meta)

class ErrorDetail(BaseModel):
    """错误详情"""
    field: Optional[str] = None
    message: str

class ErrorResponse(BaseModel):
    """错误响应格式"""
    error: Dict[str, Any]  # {"code": "ERROR_CODE", "message": "...", "details": [...]}
    meta: Meta = Field(default_factory=Meta)

class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应格式"""
    data: list[T]
    meta: PaginationMeta
