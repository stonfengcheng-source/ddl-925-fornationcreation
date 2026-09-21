"""
通知服务 - 在关键业务节点自动创建通知
"""
import logging
from sqlalchemy.orm import Session
from app.models.notification import Notification

logger = logging.getLogger(__name__)


def create_notification(
    db: Session,
    user_id: str,
    title: str,
    content: str,
    type: str = "system",
    priority: str = "normal",
    action_url: str = None,
    related_id: str = None,
) -> None:
    """创建一条通知记录"""
    try:
        notif = Notification(
            user_id=user_id,
            type=type,
            title=title,
            content=content,
            priority=priority,
            action_url=action_url,
            related_id=related_id,
        )
        db.add(notif)
        db.commit()
    except Exception as e:
        logger.error(f"创建通知失败: {e}")
        db.rollback()


def notify_task_published(db: Session, publisher_id: str, task_name: str, task_id: str) -> None:
    """任务发布成功通知"""
    create_notification(
        db=db,
        user_id=publisher_id,
        title="任务发布成功",
        content=f"您的任务「{task_name}」已成功发布，等待数据提供方参与。",
        type="task",
        priority="normal",
        action_url=f"/tasks/{task_id}",
        related_id=task_id,
    )


def notify_task_joined(db: Session, publisher_id: str, task_name: str, task_id: str, participant_name: str) -> None:
    """有人加入任务通知（通知发布者）"""
    create_notification(
        db=db,
        user_id=publisher_id,
        title="新参与者加入任务",
        content=f"数据提供方「{participant_name}」已加入您的任务「{task_name}」。",
        type="task",
        priority="normal",
        action_url=f"/tasks/{task_id}",
        related_id=task_id,
    )


def notify_training_started(db: Session, user_id: str, task_name: str, task_id: str) -> None:
    """训练开始通知"""
    create_notification(
        db=db,
        user_id=user_id,
        title="联邦训练已开始",
        content=f"任务「{task_name}」的联邦学习训练已启动。",
        type="task",
        priority="high",
        action_url=f"/federated/training/{task_id}",
        related_id=task_id,
    )


def notify_training_completed(db: Session, user_id: str, task_name: str, task_id: str, accuracy: float = None) -> None:
    """训练完成通知"""
    acc_text = f"，最终准确率 {accuracy:.1%}" if accuracy else ""
    create_notification(
        db=db,
        user_id=user_id,
        title="联邦训练已完成",
        content=f"任务「{task_name}」的联邦学习训练已完成{acc_text}。",
        type="task",
        priority="high",
        action_url=f"/federated/training/{task_id}",
        related_id=task_id,
    )


def notify_settlement(db: Session, user_id: str, task_name: str, task_id: str, amount: float) -> None:
    """结算通知（通知收益方）"""
    create_notification(
        db=db,
        user_id=user_id,
        title="收益已结算",
        content=f"任务「{task_name}」的贡献收益 ¥{amount:.2f} 已结算到您的钱包。",
        type="reward",
        priority="high",
        action_url="/profile/wallet",
        related_id=task_id,
    )
