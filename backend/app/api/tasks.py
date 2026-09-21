"""
任务相关API路由
"""
from fastapi import APIRouter, Depends, status, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.models.task import Task
from app.models.user import User
from app.models.task_node import TaskNodeAssignment
from app.models.node import Node
from app.models.dataset import Dataset
from app.schemas.task import TaskCreate, TaskResponse, PreEstimateResponse, ProviderPreEstimate
from app.schemas.common import SuccessResponse
from app.core.exceptions import ResourceNotFound
from app.api.auth import get_current_user
from app.services.pre_estimate import estimate_contributions, ProviderData
from app.services.embedding_hooks import schedule_task_embedding
from app.services.notification_service import notify_task_published

router = APIRouter()


@router.post(
    "",
    response_model=SuccessResponse[TaskResponse],
    status_code=status.HTTP_201_CREATED,
    summary="创建任务",
    description="接收前端提交的任务信息并存储到数据库（需要登录）"
)
async def create_task(
    task: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    创建新任务
    """
    # 检查：只有 "buyer" (需求方) 才能发任务？(可选逻辑)
    if current_user.user_type != "buyer":
         raise HTTPException(status_code=403, detail="只有需求方(Buyer)可以发布任务")

    try:
        db_task = Task(
            task_name=task.task_name,
            task_category=task.task_category,
            task_description=task.task_description,
            task_tags=task.task_tags or [],
            model_type=task.model_type or "breast_cancer",
            publisher_id=current_user.id,
        )
        # 数据要求
        if task.data_requirements:
            db_task.min_data_size = task.data_requirements.min_samples
            db_task.data_formats = task.data_requirements.types
            db_task.privacy_level = "medium"
        # 预算
        if task.budget:
            db_task.reward_pool = task.budget.total_reward
            db_task.settlement_cycle = task.budget.settlement_cycle
            db_task.target_accuracy = (task.budget.target_accuracy or 85) / 100.0
        # 差分隐私配置
        if task.dp_config and task.dp_config.enabled:
            db_task.dp_enabled = 1
            db_task.dp_epsilon = task.dp_config.epsilon
            db_task.dp_delta = task.dp_config.delta
            db_task.dp_noise_multiplier = task.dp_config.noise_multiplier
            db_task.dp_clipping_norm = task.dp_config.clipping_norm
            db_task.dp_adaptive = 1 if task.dp_config.adaptive else 0

        db.add(db_task)
        db.commit()
        db.refresh(db_task)
        # 异步生成 embedding 用于语义匹配
        schedule_task_embedding(db_task.id)
        # 通知发布者
        notify_task_published(db, current_user.id, db_task.task_name, db_task.id)
        return SuccessResponse(data=TaskResponse.model_validate(db_task))
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建任务失败: {str(e)}"
        )


@router.get("", response_model=SuccessResponse[List[TaskResponse]], summary="获取任务列表")
async def list_tasks(
    status_filter: Optional[str] = Query(None, alias="status"),
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(Task)
    if status_filter:
        query = query.filter(Task.status == status_filter)
    if category:
        query = query.filter(Task.task_category == category)
    if search:
        query = query.filter(Task.task_name.contains(search))
    tasks = query.order_by(Task.created_at.desc()).all()
    return SuccessResponse(data=[TaskResponse.model_validate(t) for t in tasks])


@router.get("/stats", summary="任务统计")
async def task_stats(db: Session = Depends(get_db)):
    total = db.query(Task).count()
    pending = db.query(Task).filter(Task.status == "pending").count()
    training = db.query(Task).filter(Task.status == "training").count()
    completed = db.query(Task).filter(Task.status == "completed").count()
    return SuccessResponse(data={
        "total": total, "pending": pending, "training": training, "completed": completed,
    })


@router.get(
    "/{task_id}/pre-estimate",
    response_model=SuccessResponse[PreEstimateResponse],
    summary="获取任务训练前数据价值预评估",
    description="基于各Provider已上传的数据统计特征（data_volume、quality_score）计算预评估贡献度"
)
async def get_pre_estimate(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取任务训练前数据价值预评估

    流程:
    1. 查询任务信息（验证存在、获取reward_pool）
    2. 查询所有已接受(accepted)或已分配(assigned)状态的Provider
    3. 关联Node和Dataset获取名称、数据量、质量分
    4. 调用estimate_contributions计算
    5. 返回预评估结果
    """
    # 1. 查询任务
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise ResourceNotFound(resource="任务")

    # 2. 查询已接受的Provider
    assignments = db.query(TaskNodeAssignment).filter(
        TaskNodeAssignment.task_id == task_id,
        TaskNodeAssignment.status.in_(["accepted", "assigned"])
    ).all()

    if not assignments:
        # 没有已接受的Provider，返回空结果
        return SuccessResponse(data=PreEstimateResponse(
            task_id=task_id,
            reward_pool=task.reward_pool or 0,
            providers=[]
        ))

    # 3. 构建Provider数据
    provider_data_list = []
    for assignment in assignments:
        # 获取Node信息
        node = db.query(Node).filter(Node.id == assignment.node_id).first()
        if not node:
            continue

        # 获取Dataset信息
        data_volume = 0
        quality_score = 0.0

        if assignment.dataset_id:
            dataset = db.query(Dataset).filter(Dataset.id == assignment.dataset_id).first()
            if dataset:
                data_volume = dataset.row_count or 0
                quality_score = dataset.quality_score or 0.0
        else:
            # 如果没有关联dataset，使用assignment中的数据
            data_volume = int(assignment.data_samples) if assignment.data_samples else 0
            quality_score = assignment.data_quality_score or 0.0

        provider_data_list.append(ProviderData(
            provider_id=node.id,
            provider_name=node.node_name,
            data_volume=data_volume,
            quality_score=quality_score
        ))

    # 4. 调用预评估算法
    estimates = estimate_contributions(
        providers=provider_data_list,
        reward_pool=task.reward_pool or 0
    )

    # 5. 构建响应
    provider_estimates = [
        ProviderPreEstimate(
            provider_id=e.provider_id,
            provider_name=e.provider_name,
            data_volume=e.data_volume,
            quality_score=e.quality_score,
            diversity_score=e.diversity_score,
            estimated_ratio=e.estimated_ratio,
            estimated_amount=e.estimated_amount
        )
        for e in estimates
    ]

    return SuccessResponse(data=PreEstimateResponse(
        task_id=task_id,
        reward_pool=task.reward_pool or 0,
        providers=provider_estimates
    ))


@router.get("/{task_id}", response_model=SuccessResponse[TaskResponse], summary="获取任务详情")
async def get_task(task_id: str, db: Session = Depends(get_db)):
    db_task = db.query(Task).filter(Task.id == task_id).first()
    if not db_task:
        raise ResourceNotFound(resource="任务")
    return SuccessResponse(data=TaskResponse.model_validate(db_task))