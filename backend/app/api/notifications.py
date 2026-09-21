"""通知管理API路由"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.core.database import get_db
from app.models.notification import Notification
from app.models.user import User
from app.schemas.common import SuccessResponse
from app.core.exceptions import ResourceNotFound
from app.api.auth import get_current_user

router = APIRouter()


@router.get("", summary="获取通知列表")
async def list_notifications(
    type_filter: Optional[str] = Query(None, alias="type"),
    is_read: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Notification).filter(Notification.user_id == current_user.id)
    if type_filter:
        query = query.filter(Notification.type == type_filter)
    if is_read is not None:
        query = query.filter(Notification.is_read == is_read)
    notifications = query.order_by(Notification.created_at.desc()).all()
    result = []
    for n in notifications:
        result.append({
            "id": n.id,
            "type": n.type,
            "title": n.title,
            "content": n.content,
            "isRead": n.is_read,
            "priority": n.priority,
            "createdAt": n.created_at.isoformat() if n.created_at else "",
            "actionUrl": n.action_url,
            "relatedId": n.related_id,
        })
    return SuccessResponse(data=result)


@router.get("/stats", summary="通知统计")
async def notification_stats(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    total = db.query(Notification).filter(Notification.user_id == current_user.id).count()
    unread = db.query(Notification).filter(Notification.user_id == current_user.id, Notification.is_read == False).count()
    return SuccessResponse(data={"total": total, "unread": unread})


@router.put("/{notification_id}/read", summary="标记已读")
async def mark_as_read(notification_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    notif = db.query(Notification).filter(Notification.id == notification_id, Notification.user_id == current_user.id).first()
    if not notif:
        raise ResourceNotFound(resource="通知")
    notif.is_read = True
    db.commit()
    return SuccessResponse(data={"message": "标记已读成功"})


@router.put("/read-all", summary="全部标记已读")
async def mark_all_as_read(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    count = db.query(Notification).filter(
        Notification.user_id == current_user.id, Notification.is_read == False
    ).update({"is_read": True})
    db.commit()
    return SuccessResponse(data={"message": "全部标记已读成功", "markedCount": count})


@router.delete("/{notification_id}", summary="删除通知")
async def delete_notification(notification_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    notif = db.query(Notification).filter(Notification.id == notification_id, Notification.user_id == current_user.id).first()
    if not notif:
        raise ResourceNotFound(resource="通知")
    db.delete(notif)
    db.commit()
    return SuccessResponse(data={"message": "删除成功"})
