"""
钱包 API
- 查询余额
- 交易记录（收益明细）
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.models.contribution import Contribution
from app.models.task import Task
from app.models.node import Node
from app.schemas.common import SuccessResponse
from app.api.auth import get_current_user

router = APIRouter()


@router.get("/balance", summary="查询钱包余额")
async def get_balance(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    balance = float(current_user.balance or "0")

    # 统计待结算金额
    pending_amount = 0.0
    pending_contribs = (
        db.query(Contribution)
        .filter(
            Contribution.user_id == current_user.id,
            Contribution.settlement_status == "pending",
        )
        .all()
    )
    for c in pending_contribs:
        pending_amount += c.reward_amount or 0

    # 统计已结算总额
    settled_contribs = (
        db.query(Contribution)
        .filter(
            Contribution.user_id == current_user.id,
            Contribution.settlement_status == "settled",
        )
        .all()
    )
    total_earned = sum(c.reward_amount or 0 for c in settled_contribs)

    return SuccessResponse(data={
        "balance": balance,
        "pending_amount": round(pending_amount, 2),
        "total_earned": round(total_earned, 2),
        "currency": "CNY",
    })


@router.get("/transactions", summary="交易记录")
async def get_transactions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    contribs = (
        db.query(Contribution)
        .filter(Contribution.user_id == current_user.id)
        .order_by(Contribution.created_at.desc())
        .all()
    )

    records = []
    for c in contribs:
        task = db.query(Task).filter(Task.id == c.task_id).first()
        node = db.query(Node).filter(Node.id == c.node_id).first()
        records.append({
            "id": c.id,
            "task_id": c.task_id,
            "task_name": task.task_name if task else "unknown",
            "node_name": node.node_name if node else "unknown",
            "amount": c.reward_amount,
            "currency": c.reward_currency,
            "share_percentage": c.share_percentage,
            "status": c.settlement_status,
            "created_at": c.created_at.isoformat() if c.created_at else "",
        })

    return SuccessResponse(data={
        "transactions": records,
        "total": len(records),
    })
