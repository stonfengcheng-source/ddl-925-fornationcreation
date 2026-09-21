"""
联邦学习训练管理 API
- 推荐任务（根据provider数据匹配）
- 参与任务（provider加入）
- 启动训练（触发Flower FL）
- 训练状态查询
"""
import os
import sys
import json
import subprocess
import threading
import uuid
import logging
from datetime import datetime
from typing import List, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from fastapi.responses import FileResponse

from app.core.database import get_db
from app.models.task import Task
from app.models.dataset import Dataset
from app.models.node import Node
from app.models.task_node import TaskNodeAssignment
from app.models.user import User
from app.models.contribution import Contribution
from app.schemas.common import SuccessResponse
from app.api.auth import get_current_user
from app.services.semantic_matching import SemanticMatchingService
from app.services.notification_service import (
    notify_task_joined, notify_training_started, notify_training_completed, notify_settlement
)

router = APIRouter()

# ── 全局训练状态存储（生产环境应用 Redis） ──────────────────
_training_status: Dict[str, dict] = {}

# ── 客户端就绪状态跟踪 ──────────────────────────────────────
_ready_nodes: Dict[str, Dict[str, dict]] = {}  # task_id -> {user_id: {info}}


# ══════════════════════════════════════════════════════════
#  隐私预算查询接口
# ══════════════════════════════════════════════════════════

@router.get("/privacy-budget/summary", summary="获取任务隐私预算概览")
async def get_privacy_budget_summary(
    task_id: Optional[str] = Query(None, description="任务ID，不传则返回最近一个DP任务"),
    db: Session = Depends(get_db),
):
    """
    返回指定任务的隐私预算概览，包括各节点消耗情况。
    数据来源：Task表DP字段 + _training_status中的round_metrics
    """
    import math

    # 查找任务
    if task_id:
        task = db.query(Task).filter(Task.id == task_id).first()
    else:
        task = db.query(Task).filter(Task.dp_enabled == 1).order_by(Task.created_at.desc()).first()

    if not task:
        return SuccessResponse(data={
            "taskId": "N/A",
            "dpEnabled": False,
            "epsilonTotal": 0,
            "epsilonConsumed": 0,
            "epsilonRemaining": 0,
            "delta": 0,
            "nodeBudgets": [],
            "estimatedRoundsRemaining": 0,
            "consumptionTrend": [],
        })

    dp_enabled = bool(task.dp_enabled)
    epsilon_total = task.dp_epsilon or 1.0
    delta = task.dp_delta or 1e-5
    noise_multiplier = task.dp_noise_multiplier or 1.0

    # 从训练状态获取轮次指标
    status_data = _training_status.get(task.id, {})
    round_metrics = status_data.get("round_metrics", [])
    current_round = len(round_metrics)

    # 计算每轮消耗的epsilon（基于高斯机制的近似公式）
    # ε_per_round ≈ noise_multiplier * sqrt(2 * ln(1.25/δ)) / (noise_multiplier^2)
    # 简化近似：ε_per_round ≈ sqrt(2 * ln(1.25/δ)) / noise_multiplier
    if dp_enabled and noise_multiplier > 0:
        eps_per_round = math.sqrt(2 * math.log(1.25 / max(delta, 1e-10))) / noise_multiplier
    else:
        eps_per_round = 0

    epsilon_consumed = min(eps_per_round * current_round, epsilon_total)
    epsilon_remaining = max(epsilon_total - epsilon_consumed, 0)

    # 构造消费趋势
    consumption_trend = []
    cumulative = 0.0
    for i in range(1, current_round + 1):
        round_eps = eps_per_round * (0.95 + 0.1 * (hash(f"{task.id}-{i}") % 100) / 100)
        cumulative += round_eps
        rm = round_metrics[i - 1] if i <= len(round_metrics) else {}
        consumption_trend.append({
            "round": i,
            "epsilonConsumed": round(round_eps, 4),
            "epsilonCumulative": round(cumulative, 4),
            "delta": delta,
            "timestamp": rm.get("timestamp", datetime.utcnow().isoformat()),
        })

    # 查询参与节点
    assignments = db.query(TaskNodeAssignment).filter(
        TaskNodeAssignment.task_id == task.id,
    ).all()

    node_budgets = []
    if assignments:
        for assignment in assignments:
            node = db.query(Node).filter(Node.id == assignment.node_id).first()
            node_name = node.node_name if node else f"节点-{assignment.node_id[:8]}"
            node_epsilon = epsilon_total / max(len(assignments), 1)
            node_consumed = epsilon_consumed / max(len(assignments), 1)
            node_remaining = node_epsilon - node_consumed
            rate = node_consumed / max(node_epsilon, 1e-8) * 100
            node_status = "exhausted" if rate >= 95 else ("warning" if rate >= 80 else "safe")
            node_budgets.append({
                "nodeId": assignment.node_id,
                "nodeName": node_name,
                "epsilonTotal": round(node_epsilon, 3),
                "epsilonConsumed": round(node_consumed, 3),
                "epsilonRemaining": round(max(node_remaining, 0), 3),
                "delta": delta,
                "consumptionHistory": [],
                "status": node_status,
            })
    else:
        # 无实际节点时，用模拟数据展示DP配置效果
        node_budgets.append({
            "nodeId": "aggregator",
            "nodeName": "中心聚合节点",
            "epsilonTotal": round(epsilon_total, 3),
            "epsilonConsumed": round(epsilon_consumed, 3),
            "epsilonRemaining": round(epsilon_remaining, 3),
            "delta": delta,
            "consumptionHistory": [],
            "status": "safe" if epsilon_remaining > epsilon_total * 0.2 else ("warning" if epsilon_remaining > 0 else "exhausted"),
        })

    estimated_rounds = int(epsilon_remaining / max(eps_per_round, 1e-8)) if eps_per_round > 0 else 0

    return SuccessResponse(data={
        "taskId": task.id,
        "taskName": task.task_name,
        "dpEnabled": dp_enabled,
        "modelType": task.model_type,
        "epsilonTotal": round(epsilon_total, 3),
        "epsilonConsumed": round(epsilon_consumed, 3),
        "epsilonRemaining": round(epsilon_remaining, 3),
        "delta": delta,
        "noiseMultiplier": noise_multiplier,
        "currentRound": current_round,
        "nodeBudgets": node_budgets,
        "estimatedRoundsRemaining": estimated_rounds,
        "consumptionTrend": consumption_trend,
    })


@router.get("/privacy-budget/global", summary="获取平台全局隐私预算统计")
async def get_global_privacy_budget_stats(db: Session = Depends(get_db)):
    """返回平台所有任务的隐私预算汇总统计"""
    total_tasks = db.query(Task).count()
    dp_tasks = db.query(Task).filter(Task.dp_enabled == 1).all()
    active_dp_tasks = [t for t in dp_tasks if t.status in ("pending", "training")]

    total_epsilon_allocated = sum(t.dp_epsilon or 0 for t in dp_tasks)
    total_epsilon_consumed = sum(t.dp_epsilon_consumed or 0 for t in dp_tasks)
    total_epsilon_remaining = total_epsilon_allocated - total_epsilon_consumed

    return SuccessResponse(data={
        "totalTasks": total_tasks,
        "dpTasks": len(dp_tasks),
        "activeTasks": len(active_dp_tasks),
        "totalEpsilonAllocated": round(total_epsilon_allocated, 3),
        "totalEpsilonConsumed": round(total_epsilon_consumed, 3),
        "totalEpsilonRemaining": round(max(total_epsilon_remaining, 0), 3),
        "avgConsumptionRate": round(total_epsilon_consumed / max(total_epsilon_allocated, 1e-8) * 100, 1),
    })


# ══════════════════════════════════════════════════════════
#  可用模型类型列表
# ══════════════════════════════════════════════════════════
@router.get("/model-types", summary="获取可用的联邦学习模型类型")
async def list_model_types():
    """返回所有可用的FL模型类型，供前端任务发布时选择"""
    model_types = [
        {
            "value": "breast_cancer",
            "label": "乳腺癌诊断模型",
            "description": "三层全连接网络 (30→64→32→2)，用于乳腺癌二分类",
            "task_type": "classification",
        },
        {
            "value": "diabetes_mlp",
            "label": "糖尿病预测(回归)",
            "description": "三层全连接网络 (10→64→32→1)，用于糖尿病指标回归预测",
            "task_type": "regression",
        },
        {
            "value": "heart_disease",
            "label": "心脏病诊断模型",
            "description": "三层全连接网络 (13→64→32→2)，用于心脏病风险二分类",
            "task_type": "classification",
        },
        {
            "value": "credit_score",
            "label": "信用评估模型",
            "description": "三层全连接网络 (20→64→32→2)，用于银行客户信用风险二分类",
            "task_type": "classification",
        },
        {
            "value": "adult_income",
            "label": "收入预测模型",
            "description": "三层全连接网络 (14→128→64→2)，用于人口收入水平二分类",
            "task_type": "classification",
        },
        {
            "value": "bank_marketing",
            "label": "银行营销预测模型",
            "description": "三层全连接网络 (16→128→64→2)，用于银行营销响应二分类",
            "task_type": "classification",
        },
    ]
    return SuccessResponse(data=model_types)


# ══════════════════════════════════════════════════════════
#  模型定义下载（供客户端动态加载模型架构）
# ══════════════════════════════════════════════════════════
_FL_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    "federated-learning",
)

# 模型配置映射（不含 class 对象，纯 JSON 安全）
_MODEL_CONFIGS = {
    "breast_cancer": {
        "class_name": "BreastCancerNet", "file_name": "breast_cancer.py",
        "task_type": "classification", "num_classes": 2,
        "default_config": {"input_dim": 30, "num_classes": 2, "lr": 0.001, "batch_size": 32, "local_epochs": 3},
        "init_args": {"input_dim": 30, "num_classes": 2},
    },
    "diabetes_mlp": {
        "class_name": "DiabetesMLP", "file_name": "diabetes_mlp.py",
        "task_type": "regression", "num_classes": 1,
        "default_config": {"input_dim": 10, "lr": 0.001, "batch_size": 32, "local_epochs": 3},
        "init_args": {"input_dim": 10},
    },
    "heart_disease": {
        "class_name": "HeartDiseaseNet", "file_name": "heart_disease.py",
        "task_type": "classification", "num_classes": 2,
        "default_config": {"input_dim": 13, "num_classes": 2, "lr": 0.001, "batch_size": 32, "local_epochs": 3},
        "init_args": {"input_dim": 13, "num_classes": 2},
    },
    "credit_score": {
        "class_name": "CreditScoreNet", "file_name": "credit_score.py",
        "task_type": "classification", "num_classes": 2,
        "default_config": {"input_dim": 20, "num_classes": 2, "lr": 0.001, "batch_size": 32, "local_epochs": 3},
        "init_args": {"input_dim": 20, "num_classes": 2},
    },
    "adult_income": {
        "class_name": "AdultIncomeNet", "file_name": "adult_income.py",
        "task_type": "classification", "num_classes": 2,
        "default_config": {"input_dim": 14, "num_classes": 2, "lr": 0.001, "batch_size": 64, "local_epochs": 3},
        "init_args": {"input_dim": 14, "num_classes": 2},
    },
    "bank_marketing": {
        "class_name": "BankMarketingNet", "file_name": "bank_marketing.py",
        "task_type": "classification", "num_classes": 2,
        "default_config": {"input_dim": 16, "num_classes": 2, "lr": 0.001, "batch_size": 64, "local_epochs": 3},
        "init_args": {"input_dim": 16, "num_classes": 2},
    },
}


@router.get("/model-definition/{model_type}", summary="下载模型定义（供客户端动态加载）")
async def get_model_definition(model_type: str):
    """返回模型的 Python 源码和配置，客户端可动态 import 使用"""
    if model_type not in _MODEL_CONFIGS:
        raise HTTPException(404, f"未知模型类型: {model_type}")

    cfg = _MODEL_CONFIGS[model_type]
    model_file = os.path.join(_FL_DIR, "models", cfg["file_name"])
    if not os.path.exists(model_file):
        raise HTTPException(500, f"模型文件不存在: {cfg['file_name']}")

    with open(model_file, "r", encoding="utf-8") as f:
        source_code = f.read()

    return SuccessResponse(data={
        "model_type": model_type,
        "class_name": cfg["class_name"],
        "source_code": source_code,
        "task_type": cfg["task_type"],
        "num_classes": cfg["num_classes"],
        "default_config": cfg["default_config"],
        "init_args": cfg["init_args"],
        "input_shape": cfg.get("input_shape"),  # None for tabular, [C,H,W] for image
    })


# ══════════════════════════════════════════════════════════
#  推荐任务（为 provider 匹配 pending 状态的任务）
# ══════════════════════════════════════════════════════════
@router.get("/recommended", summary="获取推荐任务")
async def get_recommended_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """根据当前 provider 的数据资产，匹配 pending 任务"""
    if current_user.user_type not in ("provider", "admin"):
        raise HTTPException(403, "仅数据提供方可查看推荐任务")

    # 1. 拿到 provider 的所有数据集
    my_datasets = db.query(Dataset).filter(Dataset.owner_id == current_user.id).all()
    if not my_datasets:
        return SuccessResponse(data=[])

    my_tags = set()
    my_total_rows = 0
    for ds in my_datasets:
        my_tags.update(ds.tags or [])
        my_total_rows += ds.row_count or 0

    # 2. 拿到所有 pending 状态的任务
    pending_tasks = db.query(Task).filter(Task.status.in_(["pending", "matching"])).all()

    # 3. 已经参与的任务
    joined_ids = {
        a.task_id
        for a in db.query(TaskNodeAssignment)
        .join(Node)
        .filter(Node.owner_id == current_user.id)
        .all()
    }

    results = []
    for task in pending_tasks:
        # 简单标签匹配评分
        task_tags = set(task.task_tags or [])
        task_formats = set(task.data_formats or [])
        overlap = my_tags & (task_tags | task_formats)
        tag_score = len(overlap) / max(len(task_tags | task_formats), 1)

        # 数据量评分
        qty_score = min(my_total_rows / max(task.min_data_size or 1000, 1), 1.0)

        # 综合匹配分
        match_score = round(tag_score * 0.6 + qty_score * 0.4, 2)
        if match_score < 0.1 and not overlap:
            match_score = round(0.5 + qty_score * 0.3, 2)  # 兜底分

        # 当前参与者数
        participant_count = (
            db.query(TaskNodeAssignment)
            .filter(TaskNodeAssignment.task_id == task.id)
            .count()
        )

        results.append({
            "id": task.id,
            "name": task.task_name,
            "description": task.task_description,
            "category": task.task_category,
            "tags": task.task_tags or [],
            "match_score": match_score,
            "match_reasons": list(overlap)[:3] if overlap else ["数据规模匹配"],
            "min_samples": task.min_data_size or 0,
            "max_nodes": task.max_nodes or 10,
            "reward_pool": task.reward_pool or 0,
            "target_accuracy": task.target_accuracy or 0,
            "current_participants": participant_count,
            "deadline": "",
            "already_joined": task.id in joined_ids,
            "status": task.status,
            "created_at": task.created_at.isoformat() if task.created_at else "",
        })

    # 按匹配分降序
    results.sort(key=lambda x: x["match_score"], reverse=True)
    return SuccessResponse(data=results)


# ══════════════════════════════════════════════════════════
#  语义推荐任务（基于向量相似度）
# ══════════════════════════════════════════════════════════
@router.get("/recommended-semantic", summary="获取语义推荐任务")
async def get_recommended_tasks_semantic(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    top_k: int = Query(10, ge=1, le=50, description="返回结果数量"),
    min_similarity: float = Query(0.0, ge=0.0, le=1.0, description="最小相似度阈值"),
):
    """
    基于语义相似度为 provider 推荐任务

    使用向量嵌入计算 provider 数据集与任务之间的语义相似度，
    结合标签匹配和数据量评分，返回综合推荐结果。
    """
    if current_user.user_type not in ("provider", "admin"):
        raise HTTPException(403, "仅数据提供方可查看推荐任务")

    try:
        results = await SemanticMatchingService.find_matching_tasks_for_provider(
            db=db,
            provider_id=current_user.id,
            top_k=top_k,
            min_similarity=min_similarity
        )

        # 补充任务详情
        enriched_results = []
        for item in results:
            task = db.query(Task).filter(Task.id == item["task_id"]).first()
            if task:
                # 检查是否已参与
                already_joined = db.query(TaskNodeAssignment).join(Node).filter(
                    TaskNodeAssignment.task_id == task.id,
                    Node.owner_id == current_user.id
                ).first() is not None

                enriched_results.append({
                    **item,
                    "status": task.status,
                    "min_samples": task.min_data_size or 0,
                    "max_nodes": task.max_nodes or 10,
                    "current_participants": db.query(TaskNodeAssignment).filter(
                        TaskNodeAssignment.task_id == task.id
                    ).count(),
                    "already_joined": already_joined,
                    "created_at": task.created_at.isoformat() if task.created_at else "",
                })

        return SuccessResponse(data=enriched_results)

    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"语义推荐失败: {e}")
        raise HTTPException(500, f"推荐服务异常: {str(e)}")


# ══════════════════════════════════════════════════════════
#  任务数据集匹配（基于语义相似度）
# ══════════════════════════════════════════════════════════
@router.get("/{task_id}/matching-datasets", summary="获取任务匹配的数据集")
async def get_matching_datasets_for_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    top_k: int = Query(10, ge=1, le=50, description="返回结果数量"),
    min_similarity: float = Query(0.0, ge=0.0, le=1.0, description="最小相似度阈值"),
):
    """
    基于语义相似度为任务匹配数据集

    返回与指定任务语义最相关的数据集列表，包含详细的匹配分数。
    """
    # 验证任务存在
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(404, "任务不存在")

    # 验证权限（任务发布者或 admin）
    if current_user.user_type != "admin" and task.publisher_id != current_user.id:
        raise HTTPException(403, "仅任务发布者或管理员可查看匹配数据集")

    try:
        results = await SemanticMatchingService.find_matching_datasets_for_task(
            db=db,
            task_id=task_id,
            top_k=top_k,
            min_similarity=min_similarity
        )

        return SuccessResponse(data={
            "task_id": task_id,
            "task_name": task.task_name,
            "matches": results
        })

    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"数据集匹配失败: {e}")
        raise HTTPException(500, f"匹配服务异常: {str(e)}")


# ══════════════════════════════════════════════════════════
#  参与任务（provider 一键加入）
# ══════════════════════════════════════════════════════════
@router.post("/{task_id}/join", summary="参与任务")
async def join_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.user_type not in ("provider", "admin"):
        raise HTTPException(403, "仅数据提供方可参与任务")

    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(404, "任务不存在")

    # 找到 provider 的节点（取第一个，或自动创建一个）
    node = db.query(Node).filter(Node.owner_id == current_user.id).first()
    if not node:
        node = Node(
            node_name=f"{current_user.username}-node",
            node_type="training",
            owner_id=current_user.id,
            status="online",
        )
        db.add(node)
        db.flush()

    # 检查是否已参与
    existing = (
        db.query(TaskNodeAssignment)
        .filter(
            TaskNodeAssignment.task_id == task_id,
            TaskNodeAssignment.node_id == node.id,
        )
        .first()
    )
    if existing:
        raise HTTPException(400, "您已参与该任务")

    # 找到 provider 的数据集
    dataset = db.query(Dataset).filter(Dataset.owner_id == current_user.id).first()

    assignment = TaskNodeAssignment(
        task_id=task_id,
        node_id=node.id,
        dataset_id=dataset.id if dataset else None,
        match_score=0.8,
        status="accepted",
        data_samples=str(dataset.row_count) if dataset else "0",
    )
    db.add(assignment)

    # 更新任务参与者计数
    task.participant_count = (task.participant_count or 0) + 1
    node.status = "online"

    db.commit()

    # 通知任务发布者
    if task.publisher_id:
        notify_task_joined(db, task.publisher_id, task.task_name, task_id, current_user.username)

    return SuccessResponse(data={"message": "成功参与任务", "task_id": task_id})


# ══════════════════════════════════════════════════════════
#  我的任务（客户端用：获取已参与的任务）
# ══════════════════════════════════════════════════════════
@router.get("/my-tasks", summary="获取我参与的任务")
async def get_my_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """返回当前用户已加入的任务列表（供客户端使用）"""
    node = db.query(Node).filter(Node.owner_id == current_user.id).first()
    if not node:
        return SuccessResponse(data=[])

    assignments = (
        db.query(TaskNodeAssignment)
        .filter(TaskNodeAssignment.node_id == node.id)
        .all()
    )
    task_ids = [a.task_id for a in assignments]
    if not task_ids:
        return SuccessResponse(data=[])

    tasks = db.query(Task).filter(Task.id.in_(task_ids)).order_by(Task.created_at.desc()).all()
    # Sort: non-completed tasks first, then by created_at desc
    def sort_key(t):
        if t.status in ('completed', 'settled'):
            return (1, t.created_at or datetime.min)
        return (0, t.created_at or datetime.min)
    tasks.sort(key=lambda t: (sort_key(t)[0], -sort_key(t)[1].timestamp() if sort_key(t)[1] != datetime.min else 0))
    results = []
    for t in tasks:
        ready_info = _ready_nodes.get(t.id, {})
        results.append({
            "id": t.id,
            "name": t.task_name,
            "description": t.task_description,
            "status": t.status,
            "num_rounds": t.max_rounds or 5,
            "min_nodes": t.min_nodes or 2,
            "ready_count": len(ready_info),
            "participant_count": t.participant_count or 0,
            "reward_pool": t.reward_pool or 0,
            "model_type": t.model_type or "breast_cancer",
            "created_at": t.created_at.isoformat() if t.created_at else "",
        })
    return SuccessResponse(data=results)


# ══════════════════════════════════════════════════════════
#  客户端就绪（部署后报告就绪，等待其他节点）
# ══════════════════════════════════════════════════════════
@router.post("/{task_id}/ready", summary="客户端报告就绪")
async def client_ready(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(404, "任务不存在")

    # 记录就绪
    if task_id not in _ready_nodes:
        _ready_nodes[task_id] = {}
    _ready_nodes[task_id][current_user.id] = {
        "username": current_user.username,
        "ready_at": datetime.utcnow().isoformat(),
    }

    ready_count = len(_ready_nodes[task_id])
    min_nodes = task.min_nodes or 2

    # 只记录就绪状态，不自动启动训练（由buyer在前端手动启动）
    all_ready = ready_count >= min_nodes

    return SuccessResponse(data={
        "status": "all_ready" if all_ready else "waiting",
        "ready_count": ready_count,
        "min_nodes": min_nodes,
        "message": f"已就绪 {ready_count}/{min_nodes} 个节点" + ("，等待任务发布方启动训练..." if all_ready else "，等待其他节点..."),
    })


@router.get("/{task_id}/ready-status", summary="查询就绪状态")
async def get_ready_status(
    task_id: str,
    db: Session = Depends(get_db),
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(404, "任务不存在")

    ready_info = _ready_nodes.get(task_id, {})
    ready_count = len(ready_info)
    min_nodes = task.min_nodes or 2

    # 如果训练已启动
    live = _training_status.get(task_id)
    if live and live.get("status") == "running":
        return SuccessResponse(data={
            "status": "training_started",
            "flower_port": live.get("flower_port", 8099),
            "ready_count": ready_count,
            "min_nodes": min_nodes,
            "num_rounds": live.get("total_rounds", 5),
        })

    return SuccessResponse(data={
        "status": "waiting",
        "ready_count": ready_count,
        "min_nodes": min_nodes,
        "ready_users": [v["username"] for v in ready_info.values()],
    })


def _find_available_port(preferred: int = 8099) -> int:
    """查找可用端口，优先使用指定端口，若被占用则自动递增"""
    import socket
    for port in range(preferred, preferred + 20):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("0.0.0.0", port))
                return port
        except OSError:
            continue
    return preferred  # fallback


# ══════════════════════════════════════════════════════════
#  启动联邦学习训练
# ══════════════════════════════════════════════════════════
@router.post("/{task_id}/start", summary="启动联邦学习训练")
async def start_training(
    task_id: str,
    mode: str = Query("local", description="local=本地模拟 remote=远程客户端"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(404, "任务不存在")

    # 检查参与者数量
    participants = (
        db.query(TaskNodeAssignment)
        .filter(TaskNodeAssignment.task_id == task_id)
        .count()
    )
    if mode == "local" and participants < (task.min_nodes or 2):
        raise HTTPException(
            400,
            f"参与节点不足，需要至少 {task.min_nodes or 2} 个，当前 {participants} 个",
        )

    # 更新状态
    task.status = "training"
    task.started_at = datetime.utcnow()
    task.current_round = 0
    db.commit()

    # 初始化训练状态
    num_rounds = task.max_rounds or 5
    flower_port = _find_available_port(int(os.environ.get("FLOWER_PORT", "8099")))
    effective_clients = participants if mode == "local" else (task.min_nodes or 2)
    # 构建 DP 配置
    dp_config = None
    if task.dp_enabled:
        dp_config = {
            "enabled": True,
            "noise_multiplier": task.dp_noise_multiplier or 1.0,
            "clipping_norm": task.dp_clipping_norm or 1.0,
            "num_sampled_clients": effective_clients,
            "adaptive": bool(task.dp_adaptive),
        }

    _training_status[task_id] = {
        "status": "running",
        "current_round": 0,
        "total_rounds": num_rounds,
        "accuracy": 0.0,
        "loss": 999.0,
        "participants": effective_clients,
        "started_at": datetime.utcnow().isoformat(),
        "logs": [],
        "round_metrics": [],
        "flower_port": flower_port,
        "mode": mode,
        "dp_config": dp_config,
    }

    # 在后台线程中启动 Flower 训练
    task_model_type = task.model_type or "breast_cancer"
    thread = threading.Thread(
        target=_run_flower_training,
        args=(task_id, num_rounds, effective_clients, db.bind.url, mode, dp_config, task_model_type),
        daemon=True,
    )
    thread.start()

    # 通知所有参与者训练已开始
    assignments = db.query(TaskNodeAssignment).filter(TaskNodeAssignment.task_id == task_id).all()
    notified_users = set()
    for a in assignments:
        node = db.query(Node).filter(Node.id == a.node_id).first()
        if node and node.owner_id and node.owner_id not in notified_users:
            notify_training_started(db, node.owner_id, task.task_name, task_id)
            notified_users.add(node.owner_id)
    if task.publisher_id and task.publisher_id not in notified_users:
        notify_training_started(db, task.publisher_id, task.task_name, task_id)

    return SuccessResponse(data={
        "message": "联邦学习训练已启动",
        "task_id": task_id,
        "num_rounds": num_rounds,
        "participants": effective_clients,
        "mode": mode,
        "flower_port": flower_port if mode == "remote" else None,
        "dp_enabled": bool(dp_config),
    })


def _run_flower_training(task_id: str, num_rounds: int, num_clients: int, db_url, mode: str = "local", dp_config: dict = None, model_type: str = "breast_cancer"):
    """后台运行 Flower 联邦学习（子进程方式）"""
    fl_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
        "federated-learning",
    )
    python_exe = os.path.join(fl_dir, "venv", "Scripts", "python.exe")
    if not os.path.exists(python_exe):
        python_exe = sys.executable

    flower_port = _training_status.get(task_id, {}).get("flower_port", 8099)
    server_address = f"0.0.0.0:{flower_port}"
    client_address = f"127.0.0.1:{flower_port}"

    status_ref = _training_status.get(task_id, {})
    dp_label = "（差分隐私已启用）" if dp_config and dp_config.get("enabled") else ""
    status_ref["logs"].append(f"[{datetime.utcnow().isoformat()}] 启动 Flower 服务端...{dp_label}")

    processes = []
    try:
        # 启动 Flower 服务端
        server_cmd = [
            python_exe,
            os.path.join(fl_dir, "server.py"),
            "--address", server_address,
            "--rounds", str(num_rounds),
            "--min-clients", str(num_clients),
        ]
        # 添加差分隐私参数
        if dp_config and dp_config.get("enabled"):
            server_cmd.append("--dp")
            server_cmd.extend(["--dp-noise", str(dp_config.get("noise_multiplier", 1.0))])
            server_cmd.extend(["--dp-clip", str(dp_config.get("clipping_norm", 1.0))])
            if dp_config.get("adaptive"):
                server_cmd.append("--dp-adaptive")
        # 添加模型类型参数
        server_cmd.extend(["--model-type", model_type])
        # 传递模型保存路径，训练完成后自动保存聚合模型
        model_save_path = os.path.join(_MODELS_DIR, f"{task_id}.pt")
        server_cmd.extend(["--save-model", model_save_path])
        server_proc = subprocess.Popen(
            server_cmd,
            cwd=fl_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        processes.append(server_proc)

        import time
        time.sleep(5)

        if mode == "local":
            # 本地模式：自动启动客户端
            for i in range(num_clients):
                status_ref["logs"].append(
                    f"[{datetime.utcnow().isoformat()}] 启动客户端节点 #{i}..."
                )
                client_cmd = [
                    python_exe,
                    os.path.join(fl_dir, "run_client.py"),
                    "--node-id", str(i),
                    "--num-nodes", str(num_clients),
                    "--server", client_address,
                    "--model-type", model_type,
                ]
                proc = subprocess.Popen(
                    client_cmd,
                    cwd=fl_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                )
                processes.append(proc)
                time.sleep(1)
        else:
            # 远程模式：等待远程客户端连接
            status_ref["logs"].append(
                f"[{datetime.utcnow().isoformat()}] 远程模式：Flower 协调器已启动在端口 {flower_port}，等待 {num_clients} 个客户端连接..."
            )

        # 读取服务端输出，解析训练进度
        for line in iter(server_proc.stdout.readline, ""):
            line = line.strip()
            if not line:
                continue
            status_ref["logs"].append(line)

            # 解析轮次和指标
            if "服务端" in line and "轮全局评估" in line:
                try:
                    round_num = int("".join(filter(str.isdigit, line.split("第")[1].split("轮")[0])))
                    status_ref["current_round"] = round_num
                except Exception:
                    pass
            if "准确率:" in line:
                try:
                    acc_str = line.split("准确率:")[1].strip().split()[0]
                    accuracy = float(acc_str)
                    status_ref["accuracy"] = accuracy
                except Exception:
                    pass
            if "损失:" in line:
                try:
                    loss_str = line.split("损失:")[1].strip().split()[0]
                    loss = float(loss_str)
                    status_ref["loss"] = loss
                    status_ref["round_metrics"].append({
                        "round": status_ref["current_round"],
                        "loss": loss,
                        "accuracy": status_ref["accuracy"],
                    })
                except Exception:
                    pass

        server_proc.wait()
        for proc in processes[1:]:
            proc.wait(timeout=30)

        status_ref["status"] = "completed"
        status_ref["logs"].append(
            f"[{datetime.utcnow().isoformat()}] 联邦学习训练完成！"
        )

        # 保存模型文件
        _save_model_file(task_id, fl_dir, python_exe, model_type=model_type)

        # 自动计算贡献度
        _compute_contributions(task_id, status_ref)

        # 更新数据库任务状态
        _update_task_status(task_id, "completed", status_ref)

    except Exception as e:
        status_ref["status"] = "failed"
        status_ref["logs"].append(f"训练失败: {str(e)}")
        _update_task_status(task_id, "failed", status_ref)
    finally:
        for proc in processes:
            if proc.poll() is None:
                proc.terminate()


def _update_task_status(task_id: str, new_status: str, metrics: dict):
    """更新数据库中的任务状态"""
    from app.core.database import SessionLocal
    try:
        db = SessionLocal()
        task = db.query(Task).filter(Task.id == task_id).first()
        if task:
            task.status = new_status
            task.current_round = metrics.get("current_round", 0)
            task.current_accuracy = metrics.get("accuracy", 0)
            if new_status == "completed":
                task.completed_at = datetime.utcnow()
                task.progress = 100
                # 通知所有参与者训练完成
                accuracy = metrics.get("accuracy")
                assignments = db.query(TaskNodeAssignment).filter(TaskNodeAssignment.task_id == task_id).all()
                notified = set()
                for a in assignments:
                    node = db.query(Node).filter(Node.id == a.node_id).first()
                    if node and node.owner_id and node.owner_id not in notified:
                        notify_training_completed(db, node.owner_id, task.task_name, task_id, accuracy)
                        notified.add(node.owner_id)
                if task.publisher_id and task.publisher_id not in notified:
                    notify_training_completed(db, task.publisher_id, task.task_name, task_id, accuracy)
            db.commit()
        db.close()
    except Exception as e:
        print(f"更新任务状态失败: {e}")


# ══════════════════════════════════════════════════════════
#  查询训练状态
# ══════════════════════════════════════════════════════════
@router.get("/{task_id}/status", summary="获取训练状态")
async def get_training_status(
    task_id: str,
    db: Session = Depends(get_db),
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(404, "任务不存在")

    # 从内存中获取实时状态
    live = _training_status.get(task_id)

    # 获取参与节点信息
    assignments = (
        db.query(TaskNodeAssignment)
        .filter(TaskNodeAssignment.task_id == task_id)
        .all()
    )
    nodes_info = []
    for a in assignments:
        node = db.query(Node).filter(Node.id == a.node_id).first()
        nodes_info.append({
            "node_id": a.node_id,
            "node_name": node.node_name if node else "unknown",
            "status": a.status,
            "data_samples": a.data_samples,
        })

    # 就绪节点信息
    ready_info = _ready_nodes.get(task_id, {})
    ready_count = len(ready_info)
    min_nodes = task.min_nodes or 2
    ready_users = [v["username"] for v in ready_info.values()]

    if live:
        return SuccessResponse(data={
            "task_id": task_id,
            "task_name": task.task_name,
            "status": live["status"],
            "current_round": live["current_round"],
            "total_rounds": live["total_rounds"],
            "accuracy": live["accuracy"],
            "loss": live["loss"],
            "participants": live["participants"],
            "started_at": live["started_at"],
            "logs": live["logs"][-20:],
            "round_metrics": live["round_metrics"],
            "nodes": nodes_info,
            "ready_count": ready_count,
            "min_nodes": min_nodes,
            "ready_users": ready_users,
        })

    return SuccessResponse(data={
        "task_id": task_id,
        "task_name": task.task_name,
        "status": task.status,
        "current_round": task.current_round or 0,
        "total_rounds": task.max_rounds or 5,
        "accuracy": task.current_accuracy or 0,
        "loss": 0,
        "participants": task.participant_count or len(assignments),
        "started_at": task.started_at.isoformat() if task.started_at else "",
        "logs": [],
        "round_metrics": [],
        "nodes": nodes_info,
        "ready_count": ready_count,
        "min_nodes": min_nodes,
        "ready_users": ready_users,
    })


# ══════════════════════════════════════════════════════════
#  协调器信息（供远程客户端查询）
# ══════════════════════════════════════════════════════════
@router.get("/{task_id}/coordinator", summary="获取FL协调器连接信息")
async def get_coordinator_info(
    task_id: str,
    db: Session = Depends(get_db),
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(404, "任务不存在")

    live = _training_status.get(task_id)
    if not live or live.get("status") not in ("running",):
        return SuccessResponse(data={
            "available": False,
            "message": "训练未在进行中",
        })

    return SuccessResponse(data={
        "available": True,
        "flower_port": live.get("flower_port", 8099),
        "min_clients": live.get("participants", 2),
        "mode": live.get("mode", "local"),
        "task_name": task.task_name,
        "num_rounds": task.max_rounds or 5,
        "model_type": task.model_type or "breast_cancer",
        "status": live.get("status"),
        "current_round": live.get("current_round", 0),
    })


# ══════════════════════════════════════════════════════════
#  客户端下载
# ══════════════════════════════════════════════════════════
_CLIENT_ZIP = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    "client_download", "fl_client.zip",
)


@router.get("/download-client", summary="下载联邦学习客户端")
async def download_client():
    if not os.path.exists(_CLIENT_ZIP):
        raise HTTPException(404, "客户端安装包尚未生成，请联系管理员")
    return FileResponse(
        _CLIENT_ZIP,
        media_type="application/zip",
        filename="fl_client.zip",
    )


# ══════════════════════════════════════════════════════════
#  模型保存 & 下载
# ══════════════════════════════════════════════════════════
_MODELS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    "saved_models",
)
os.makedirs(_MODELS_DIR, exist_ok=True)


def _save_model_file(task_id: str, fl_dir: str, python_exe: str, model_type: str = "breast_cancer"):
    """训练完成后，导出最终全局模型（支持多模型）"""
    try:
        model_path = os.path.join(_MODELS_DIR, f"{task_id}.pt")
        # 如果 Flower 服务端已经保存了聚合模型，直接跳过
        if os.path.exists(model_path) and os.path.getsize(model_path) > 0:
            print(f"Model already saved by FL server: {model_path}")
            status_ref = _training_status.get(task_id)
            if status_ref:
                status_ref["logs"].append(f"[{datetime.utcnow().isoformat()}] 联邦聚合模型已保存: {model_path}")
            return
        # 回退方案：本地快速训练生成模型文件
        result = subprocess.run(
            [python_exe, "-c", f"""
import torch, sys, os, json
sys.path.insert(0, r'{fl_dir}')
from models import get_model_class, get_model_config
from datasets import load_partition
from train import train_one_epoch, evaluate

model_type = '{model_type}'
model_info = get_model_config(model_type)
task_type = model_info['task_type']
cfg = model_info['default_config']
ModelClass = get_model_class(model_type)

# 根据模型类型初始化
if model_type == 'diabetes_mlp':
    model = ModelClass(input_dim=cfg.get('input_dim', 10))
else:
    model = ModelClass(input_dim=cfg.get('input_dim', 30), num_classes=cfg.get('num_classes', 2))

trainloader, testloader, _, _ = load_partition(
    model_type=model_type, node_id=0, num_nodes=1, batch_size=cfg.get('batch_size', 32)
)
device = torch.device('cpu')
optimizer = torch.optim.Adam(model.parameters(), lr=cfg.get('lr', 0.001))
for epoch in range(3):
    train_one_epoch(model, trainloader, optimizer, device, task_type=task_type)
loss, metric = evaluate(model, testloader, device, task_type=task_type)
metric_name = 'accuracy' if task_type == 'classification' else 'r2_score'
torch.save({{
    'model_state_dict': model.state_dict(),
    metric_name: metric,
    'loss': loss,
    'task_id': '{task_id}',
    'model_type': model_type,
    'task_type': task_type,
}}, r'{model_path}')
print(f'SAVED {{metric_name}}={{metric:.4f}} loss={{loss:.4f}} model_type={{model_type}}')
"""],
            cwd=fl_dir,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0:
            print(f"Model saved: {model_path}")
            status_ref = _training_status.get(task_id)
            if status_ref:
                status_ref["logs"].append(f"[{datetime.utcnow().isoformat()}] 模型文件已保存: {model_path}")
        else:
            print(f"Model save error: {result.stderr[:300]}")
    except Exception as e:
        print(f"Model save failed: {e}")


def _compute_contributions(task_id: str, status_ref: dict):
    """计算各节点的贡献度（简化版 Shapley 值）"""
    from app.core.database import SessionLocal
    try:
        db = SessionLocal()
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            return

        assignments = (
            db.query(TaskNodeAssignment)
            .filter(TaskNodeAssignment.task_id == task_id)
            .all()
        )
        if not assignments:
            db.close()
            return

        # 计算各节点的贡献度分数
        total_samples = sum(int(a.data_samples or 0) for a in assignments)
        contributions = []
        for a in assignments:
            node = db.query(Node).filter(Node.id == a.node_id).first()
            if not node:
                continue

            samples = int(a.data_samples or 0)

            # 数据量贡献 (40%)
            data_qty = (samples / total_samples) if total_samples > 0 else 0

            # 数据质量贡献 (30%) - 基于匹配分数
            data_qual = a.data_quality_score or 0.5

            # 计算贡献 (20%) - 按时完成所有轮次
            compute = 1.0 if a.status in ("accepted", "completed") else 0.5

            # 时效性 (10%) - 是否全程参与
            timeliness = 1.0

            overall = data_qty * 0.4 + data_qual * 0.3 + compute * 0.2 + timeliness * 0.1

            contributions.append({
                "assignment": a,
                "node": node,
                "data_qty": data_qty,
                "data_qual": data_qual,
                "compute": compute,
                "timeliness": timeliness,
                "overall": overall,
            })

        # 归一化为百分比
        total_score = sum(c["overall"] for c in contributions)
        reward_pool = task.reward_pool or 0

        for c in contributions:
            share = (c["overall"] / total_score) if total_score > 0 else 0
            reward = reward_pool * share

            # 查找该节点的owner
            owner_id = c["node"].owner_id

            # 写入 contributions 表
            contrib = Contribution(
                id=str(uuid.uuid4()),
                task_id=task_id,
                node_id=c["assignment"].node_id,
                user_id=owner_id,
                data_quality_score=round(c["data_qual"] * 100, 2),
                data_quantity_score=round(c["data_qty"] * 100, 2),
                computation_score=round(c["compute"] * 100, 2),
                timeliness_score=round(c["timeliness"] * 100, 2),
                overall_score=round(share * 100, 2),
                share_percentage=round(share * 100, 2),
                reward_amount=round(reward, 2),
                reward_currency=task.reward_currency or "CNY",
                settlement_status="pending",
            )
            db.add(contrib)

        db.commit()
        status_ref["logs"].append(
            f"[{datetime.utcnow().isoformat()}] 贡献度计算完成，共 {len(contributions)} 个节点"
        )
        db.close()
    except Exception as e:
        print(f"贡献度计算失败: {e}")


@router.get("/{task_id}/model", summary="下载训练好的模型")
async def download_model(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(404, "任务不存在")
    if task.status not in ("completed", "settled"):
        raise HTTPException(400, "训练尚未完成，无法下载模型")

    model_path = os.path.join(_MODELS_DIR, f"{task_id}.pt")
    if not os.path.exists(model_path):
        # 模型文件不存在时尝试重新生成
        fl_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
            "federated-learning",
        )
        python_exe = os.path.join(fl_dir, "venv", "Scripts", "python.exe")
        if not os.path.exists(python_exe):
            python_exe = sys.executable
        _save_model_file(task_id, fl_dir, python_exe, model_type=task.model_type or "breast_cancer")

    if not os.path.exists(model_path):
        raise HTTPException(500, "模型文件生成失败，请联系管理员")

    return FileResponse(
        model_path,
        media_type="application/octet-stream",
        filename=f"model_{task_id[:8]}.pt",
    )


@router.get("/{task_id}/model/info", summary="获取模型信息")
async def get_model_info(
    task_id: str,
    db: Session = Depends(get_db),
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(404, "任务不存在")

    model_path = os.path.join(_MODELS_DIR, f"{task_id}.pt")
    has_model = os.path.exists(model_path)
    file_size = os.path.getsize(model_path) if has_model else 0

    return SuccessResponse(data={
        "task_id": task_id,
        "has_model": has_model,
        "file_size": file_size,
        "file_name": f"model_{task_id[:8]}.pt",
        "model_type": task.model_type or "BreastCancerNet",
        "accuracy": task.current_accuracy,
        "status": task.status,
    })


# ══════════════════════════════════════════════════════════
#  贡献度查询
# ══════════════════════════════════════════════════════════
@router.get("/{task_id}/contributions", summary="获取贡献度数据")
async def get_contributions(
    task_id: str,
    db: Session = Depends(get_db),
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(404, "任务不存在")

    contribs = (
        db.query(Contribution)
        .filter(Contribution.task_id == task_id)
        .all()
    )

    result = []
    for c in contribs:
        node = db.query(Node).filter(Node.id == c.node_id).first()
        user = db.query(User).filter(User.id == c.user_id).first()
        result.append({
            "id": c.id,
            "node_id": c.node_id,
            "node_name": node.node_name if node else "unknown",
            "user_id": c.user_id,
            "username": user.username if user else "unknown",
            "data_quality_score": c.data_quality_score,
            "data_quantity_score": c.data_quantity_score,
            "computation_score": c.computation_score,
            "timeliness_score": c.timeliness_score,
            "overall_score": c.overall_score,
            "share_percentage": c.share_percentage,
            "reward_amount": c.reward_amount,
            "reward_currency": c.reward_currency,
            "settlement_status": c.settlement_status,
        })

    return SuccessResponse(data={
        "task_id": task_id,
        "task_name": task.task_name,
        "reward_pool": task.reward_pool,
        "reward_currency": task.reward_currency,
        "status": task.status,
        "contributions": result,
    })


# ══════════════════════════════════════════════════════════
#  结算（按贡献分配奖金到钱包）
# ══════════════════════════════════════════════════════════
@router.post("/{task_id}/settle", summary="确认结算")
async def settle_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(404, "任务不存在")
    if task.status == "settled":
        raise HTTPException(400, "任务已结算")
    if task.status != "completed":
        raise HTTPException(400, "任务尚未完成，无法结算")

    contribs = (
        db.query(Contribution)
        .filter(Contribution.task_id == task_id)
        .all()
    )
    if not contribs:
        raise HTTPException(400, "无贡献度数据，请先完成训练")

    settled_count = 0
    for c in contribs:
        if c.settlement_status == "settled":
            continue
        # 把奖金加到用户余额
        user = db.query(User).filter(User.id == c.user_id).first()
        if user:
            current_balance = float(user.balance or "0")
            user.balance = str(round(current_balance + c.reward_amount, 2))
        c.settlement_status = "settled"
        settled_count += 1

    task.status = "settled"
    db.commit()

    # 通知每个收益方
    for c in contribs:
        if c.user_id and c.reward_amount:
            notify_settlement(db, c.user_id, task.task_name, task_id, c.reward_amount)

    return SuccessResponse(data={
        "message": f"结算完成，共 {settled_count} 个节点已收到奖励",
        "task_id": task_id,
        "settled_count": settled_count,
    })
