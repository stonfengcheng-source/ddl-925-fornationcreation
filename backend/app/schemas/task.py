"""
任务相关的 Pydantic 模型（请求/响应）
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class DataRequirementsCreate(BaseModel):
    """数据需求（前端第2步）"""
    types: Optional[List[str]] = []
    min_samples: Optional[int] = 1000
    quality_score: Optional[int] = 80
    description: Optional[str] = ""


class BudgetCreate(BaseModel):
    """预算设置（前端第3步）"""
    total_reward: Optional[float] = 10000
    settlement_cycle: Optional[str] = "monthly"
    target_accuracy: Optional[float] = 85


class DPConfigCreate(BaseModel):
    """差分隐私配置（可选）"""
    enabled: Optional[bool] = False
    epsilon: Optional[float] = 1.0          # 隐私预算 ε
    delta: Optional[float] = 1e-5           # 隐私失败概率 δ
    noise_multiplier: Optional[float] = 1.0 # 噪声倍数
    clipping_norm: Optional[float] = 1.0    # 裁剪范数
    adaptive: Optional[bool] = False        # 自适应裁剪


class TaskCreate(BaseModel):
    """
    创建任务请求模型 — 匹配前端3步向导提交的字段
    """
    task_name: str = Field(..., min_length=1, max_length=200)
    task_category: str = Field(default="其他")
    task_domain: Optional[str] = None
    task_description: str = Field(..., min_length=1)
    task_tags: Optional[List[str]] = []
    model_type: Optional[str] = "breast_cancer"
    data_requirements: Optional[DataRequirementsCreate] = None
    budget: Optional[BudgetCreate] = None
    dp_config: Optional[DPConfigCreate] = None


class TaskResponse(BaseModel):
    """
    任务响应模型
    """
    id: str
    task_name: str
    task_category: str
    task_description: str
    task_tags: List[str] = []
    model_type: Optional[str] = None
    status: Optional[str] = "pending"
    reward_pool: Optional[float] = 0
    reward_currency: Optional[str] = "CNY"
    participant_count: Optional[int] = 0
    current_round: Optional[int] = 0
    max_rounds: Optional[int] = None
    current_accuracy: Optional[float] = None
    target_accuracy: Optional[float] = None
    min_data_size: Optional[int] = None
    min_nodes: Optional[int] = None
    max_nodes: Optional[int] = None
    dp_enabled: Optional[int] = 0
    dp_epsilon: Optional[float] = None
    dp_delta: Optional[float] = None
    dp_noise_multiplier: Optional[float] = None
    dp_clipping_norm: Optional[float] = None
    dp_epsilon_consumed: Optional[float] = 0.0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TaskUpdate(BaseModel):
    """
    更新任务请求模型（部分更新）
    """
    task_name: Optional[str] = Field(None, min_length=1, max_length=200)
    task_category: Optional[str] = None
    task_description: Optional[str] = None
    task_tags: Optional[List[str]] = None


class ProviderPreEstimate(BaseModel):
    """
    Provider预评估结果
    """
    provider_id: str
    provider_name: str
    data_volume: int
    quality_score: float
    diversity_score: float
    estimated_ratio: float
    estimated_amount: float

    class Config:
        from_attributes = True


class PreEstimateResponse(BaseModel):
    """
    预评估响应模型
    """
    task_id: str
    reward_pool: float
    providers: List[ProviderPreEstimate]
