"""用户资料API路由"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional
from app.core.database import get_db
from app.models.user import User
from app.schemas.common import SuccessResponse
from app.api.auth import get_current_user
from app.services.auth import AuthService
from app.core.config import PASSWORDLESS_AUTH

router = APIRouter()


class ProfileUpdate(BaseModel):
    nickname: Optional[str] = None
    avatar: Optional[str] = None
    phone: Optional[str] = None
    bio: Optional[str] = None
    gender: Optional[str] = None
    location: Optional[str] = None


@router.get("", summary="获取个人资料")
async def get_profile(current_user: User = Depends(get_current_user)):
    return SuccessResponse(data={
        "id": current_user.id,
        "username": current_user.username,
        "nickname": current_user.nickname or current_user.username,
        "avatar": current_user.avatar or "",
        "email": current_user.email or "",
        "phone": current_user.phone or "",
        "bio": current_user.bio or "",
        "gender": current_user.gender,
        "location": current_user.location or "",
        "userType": current_user.user_type,
        "verified": current_user.verified,
        "balance": current_user.balance or "0",
        "createdAt": current_user.created_at.isoformat() if current_user.created_at else "",
        "lastLoginAt": current_user.last_login_at.isoformat() if current_user.last_login_at else "",
    })


@router.put("", summary="更新个人资料")
async def update_profile(profile: ProfileUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    for key, value in profile.model_dump(exclude_unset=True).items():
        setattr(current_user, key, value)
    db.commit()
    db.refresh(current_user)
    return SuccessResponse(data={"message": "个人资料更新成功"})


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6)


@router.put("/password", summary="修改密码")
async def change_password(
    req: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if PASSWORDLESS_AUTH:
        return SuccessResponse(data={"message": "本地免密模式无需设置密码"})

    if not AuthService.verify_password(req.current_password, current_user.password):
        raise HTTPException(status_code=400, detail="当前密码错误")
    current_user.password = AuthService.get_password_hash(req.new_password)
    db.commit()
    return SuccessResponse(data={"message": "密码修改成功"})
