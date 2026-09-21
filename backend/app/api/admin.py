"""
管理后台 API
- 仪表盘统计
- 用户/任务/节点/数据集/模型管理
- 删除操作
- 手动推荐任务
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List
import os
import glob

from app.core.database import get_db
from app.models.user import User
from app.models.task import Task
from app.models.node import Node
from app.models.dataset import Dataset
from app.models.task_node import TaskNodeAssignment
from app.models.contribution import Contribution
from app.models.training_log import TrainingLog
from app.schemas.common import SuccessResponse
from app.api.auth import get_current_user

router = APIRouter()


def _require_admin(current_user: User):
    if current_user.user_type != "admin":
        raise HTTPException(403, "仅管理员可访问")


@router.get("/stats", summary="管理后台统计")
async def admin_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)
    total_users = db.query(User).count()
    total_tasks = db.query(Task).count()
    total_nodes = db.query(Node).count()
    online_nodes = db.query(Node).filter(Node.status == "online").count()
    pending_tasks = db.query(Task).filter(Task.status == "pending").count()
    training_tasks = db.query(Task).filter(Task.status == "training").count()
    completed_tasks = db.query(Task).filter(Task.status.in_(["completed", "settled"])).count()

    buyers = db.query(User).filter(User.user_type == "buyer").count()
    providers = db.query(User).filter(User.user_type == "provider").count()
    total_datasets = db.query(Dataset).count()
    # Count model files
    model_count = 0
    if os.path.isdir(_MODELS_DIR):
        model_count = len(glob.glob(os.path.join(_MODELS_DIR, "*.pt")))

    return SuccessResponse(data={
        "totalUsers": total_users,
        "totalTasks": total_tasks,
        "totalNodes": total_nodes,
        "onlineNodes": online_nodes,
        "pendingTasks": pending_tasks,
        "trainingTasks": training_tasks,
        "completedTasks": completed_tasks,
        "buyers": buyers,
        "providers": providers,
        "totalDatasets": total_datasets,
        "totalModels": model_count,
    })


@router.get("/users", summary="用户列表")
async def admin_users(
    search: Optional[str] = Query(None),
    user_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)
    query = db.query(User)
    if search:
        query = query.filter(User.username.contains(search))
    if user_type:
        query = query.filter(User.user_type == user_type)
    users = query.order_by(User.created_at.desc()).all()
    return SuccessResponse(data=[
        {
            "id": u.id,
            "username": u.username,
            "email": u.email or "",
            "userType": u.user_type,
            "status": u.status or "active",
            "balance": u.balance or "0",
            "verified": u.verified,
            "createdAt": u.created_at.isoformat() if u.created_at else "",
            "lastLoginAt": u.last_login_at.isoformat() if u.last_login_at else "",
        }
        for u in users
    ])


@router.get("/tasks", summary="任务列表(管理)")
async def admin_tasks(
    search: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)
    query = db.query(Task)
    if search:
        query = query.filter(Task.task_name.contains(search))
    if status_filter:
        query = query.filter(Task.status == status_filter)
    tasks = query.order_by(Task.created_at.desc()).all()
    result = []
    for t in tasks:
        publisher = db.query(User).filter(User.id == t.publisher_id).first()
        result.append({
            "id": t.id,
            "name": t.task_name,
            "publisher": publisher.username if publisher else "unknown",
            "category": t.task_category or "",
            "status": t.status,
            "rewardPool": t.reward_pool or 0,
            "currentRound": t.current_round or 0,
            "maxRounds": t.max_rounds or 0,
            "createdAt": t.created_at.isoformat() if t.created_at else "",
        })
    return SuccessResponse(data=result)


@router.get("/nodes", summary="节点列表(管理)")
async def admin_nodes(
    search: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)
    query = db.query(Node)
    if search:
        query = query.filter(Node.node_name.contains(search))
    if status_filter:
        query = query.filter(Node.status == status_filter)
    nodes = query.order_by(Node.created_at.desc()).all()
    result = []
    for n in nodes:
        owner = db.query(User).filter(User.id == n.owner_id).first()
        result.append({
            "id": n.id,
            "name": n.node_name,
            "owner": owner.username if owner else "unknown",
            "nodeType": n.node_type or "",
            "status": n.status or "offline",
            "location": n.location or "",
            "cpuCores": n.cpu_cores,
            "memoryTotal": n.memory_total,
            "cpuUsage": n.cpu_usage,
            "memoryUsage": n.memory_usage,
            "createdAt": n.created_at.isoformat() if n.created_at else "",
            "lastHeartbeat": n.last_heartbeat.isoformat() if n.last_heartbeat else "",
        })
    return SuccessResponse(data=result)


# ══════════════════════════════════════════════════════════
#  数据资产列表（管理）
# ══════════════════════════════════════════════════════════
@router.get("/datasets", summary="数据资产列表(管理)")
async def admin_datasets(
    search: Optional[str] = Query(None),
    data_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)
    query = db.query(Dataset)
    if search:
        query = query.filter(Dataset.name.contains(search))
    if data_type:
        query = query.filter(Dataset.data_type == data_type)
    datasets = query.order_by(Dataset.created_at.desc()).all()
    result = []
    for d in datasets:
        owner = db.query(User).filter(User.id == d.owner_id).first()
        result.append({
            "id": d.id,
            "name": d.name,
            "description": d.description or "",
            "dataType": d.data_type,
            "status": d.status or "ready",
            "sizeBytes": d.size_bytes or 0,
            "rowCount": d.row_count or 0,
            "columnCount": d.column_count or 0,
            "qualityScore": d.quality_score,
            "usageCount": d.usage_count or 0,
            "owner": owner.username if owner else "unknown",
            "ownerId": d.owner_id,
            "tags": d.tags or [],
            "createdAt": d.created_at.isoformat() if d.created_at else "",
        })
    return SuccessResponse(data=result)


# ══════════════════════════════════════════════════════════
#  模型文件列表（管理）
# ══════════════════════════════════════════════════════════
_MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "saved_models")

@router.get("/models", summary="模型文件列表(管理)")
async def admin_models(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)
    result = []
    if os.path.isdir(_MODELS_DIR):
        for fpath in glob.glob(os.path.join(_MODELS_DIR, "*.pt")):
            fname = os.path.basename(fpath)
            task_id = fname.replace(".pt", "")
            fsize = os.path.getsize(fpath)
            mtime = os.path.getmtime(fpath)
            task = db.query(Task).filter(Task.id == task_id).first()
            result.append({
                "id": task_id,
                "filename": fname,
                "taskName": task.task_name if task else "未知任务",
                "taskStatus": task.status if task else "unknown",
                "fileSize": fsize,
                "createdAt": __import__("datetime").datetime.fromtimestamp(mtime).isoformat(),
            })
    return SuccessResponse(data=result)


# ══════════════════════════════════════════════════════════
#  删除任务
# ══════════════════════════════════════════════════════════
@router.delete("/tasks/{task_id}", summary="删除任务")
async def admin_delete_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(404, "任务不存在")
    # 删除关联数据
    db.query(TaskNodeAssignment).filter(TaskNodeAssignment.task_id == task_id).delete()
    db.query(Contribution).filter(Contribution.task_id == task_id).delete()
    db.query(TrainingLog).filter(TrainingLog.task_id == task_id).delete()
    db.delete(task)
    db.commit()
    # 删除模型文件
    model_path = os.path.join(_MODELS_DIR, f"{task_id}.pt")
    if os.path.exists(model_path):
        os.remove(model_path)
    return SuccessResponse(data={"message": f"任务 {task.task_name} 已删除"})


# ══════════════════════════════════════════════════════════
#  删除用户
# ══════════════════════════════════════════════════════════
@router.delete("/users/{user_id}", summary="删除用户")
async def admin_delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "用户不存在")
    if user.user_type == "admin":
        raise HTTPException(400, "不能删除管理员账户")
    if user.id == current_user.id:
        raise HTTPException(400, "不能删除自己的账户")
    # 删除用户关联的节点和数据集
    nodes = db.query(Node).filter(Node.owner_id == user_id).all()
    for node in nodes:
        db.query(TaskNodeAssignment).filter(TaskNodeAssignment.node_id == node.id).delete()
        db.query(Dataset).filter(Dataset.node_id == node.id).update({"node_id": None})
        db.delete(node)
    db.query(Dataset).filter(Dataset.owner_id == user_id).delete()
    db.query(Contribution).filter(Contribution.user_id == user_id).delete()
    # 删除用户发布的任务的关联
    user_tasks = db.query(Task).filter(Task.publisher_id == user_id).all()
    for t in user_tasks:
        db.query(TaskNodeAssignment).filter(TaskNodeAssignment.task_id == t.id).delete()
        db.query(Contribution).filter(Contribution.task_id == t.id).delete()
        db.query(TrainingLog).filter(TrainingLog.task_id == t.id).delete()
        db.delete(t)
    db.delete(user)
    db.commit()
    return SuccessResponse(data={"message": f"用户 {user.username} 已删除"})


# ══════════════════════════════════════════════════════════
#  删除数据资产
# ══════════════════════════════════════════════════════════
@router.delete("/datasets/{dataset_id}", summary="删除数据资产")
async def admin_delete_dataset(
    dataset_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(404, "数据资产不存在")
    db.delete(dataset)
    db.commit()
    return SuccessResponse(data={"message": f"数据资产 {dataset.name} 已删除"})


# ══════════════════════════════════════════════════════════
#  删除模型文件
# ══════════════════════════════════════════════════════════
@router.delete("/models/{task_id}", summary="删除模型文件")
async def admin_delete_model(
    task_id: str,
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)
    model_path = os.path.join(_MODELS_DIR, f"{task_id}.pt")
    if not os.path.exists(model_path):
        raise HTTPException(404, "模型文件不存在")
    os.remove(model_path)
    return SuccessResponse(data={"message": "模型文件已删除"})


# ══════════════════════════════════════════════════════════
#  手动推荐任务给数据提供方
# ══════════════════════════════════════════════════════════
class RecommendRequest(BaseModel):
    task_id: str
    provider_ids: List[str]

@router.post("/recommend-task", summary="手动推荐任务给数据提供方")
async def admin_recommend_task(
    req: RecommendRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)
    task = db.query(Task).filter(Task.id == req.task_id).first()
    if not task:
        raise HTTPException(404, "任务不存在")

    added = []
    skipped = []
    for pid in req.provider_ids:
        provider = db.query(User).filter(User.id == pid, User.user_type == "provider").first()
        if not provider:
            skipped.append(pid)
            continue
        node = db.query(Node).filter(Node.owner_id == pid).first()
        if not node:
            skipped.append(provider.username)
            continue
        # 检查是否已经分配
        existing = db.query(TaskNodeAssignment).filter(
            TaskNodeAssignment.task_id == req.task_id,
            TaskNodeAssignment.node_id == node.id,
        ).first()
        if existing:
            skipped.append(provider.username)
            continue
        assignment = TaskNodeAssignment(
            task_id=req.task_id,
            node_id=node.id,
            status="accepted",
            match_score=1.0,
        )
        db.add(assignment)
        added.append(provider.username)
    if added:
        task.participant_count = (task.participant_count or 0) + len(added)
        db.commit()
    return SuccessResponse(data={
        "message": f"已推荐给 {len(added)} 个提供方",
        "added": added,
        "skipped": skipped,
    })


# ══════════════════════════════════════════════════════════
#  获取所有数据提供方（用于推荐选择）
# ══════════════════════════════════════════════════════════
@router.get("/providers", summary="获取所有数据提供方")
async def admin_providers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)
    providers = db.query(User).filter(User.user_type == "provider").order_by(User.created_at.desc()).all()
    result = []
    for p in providers:
        node = db.query(Node).filter(Node.owner_id == p.id).first()
        result.append({
            "id": p.id,
            "username": p.username,
            "email": p.email or "",
            "hasNode": node is not None,
            "nodeName": node.node_name if node else "",
        })
    return SuccessResponse(data=result)
