"""
认证相关的 Pydantic 模型（请求/响应）
"""
from pydantic import BaseModel, Field, field_validator, EmailStr
from typing import Optional, Literal
from datetime import datetime


class UserTypeEnum(str):
    """用户类型"""
    BUYER = "buyer"
    PROVIDER = "provider"


# ============ 请求模型 ============

class LoginRequest(BaseModel):
    """
    登录请求模型
    """
    username: str = Field(
        ...,
        min_length=1,
        max_length=120,
        description="用户名或邮箱",
        example="john_doe"
    )

    password: Optional[str] = Field(
        default="",
        description="密码；本地开发免密模式可留空",
        example=""
    )

    source: Optional[str] = Field(
        "web",
        description="登录来源：web（网页端）或 desktop（桌面客户端）",
        example="web"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "username": "john_doe",
                "password": "",
                "source": "web"
            }
        }


class RegisterRequest(BaseModel):
    """
    注册请求模型
    """
    username: str = Field(
        ...,
        min_length=3,
        max_length=20,
        description="用户名（3-20个字符，只能包含字母、数字和下划线）",
        example="john_doe"
    )

    email: EmailStr = Field(
        ...,
        description="邮箱地址",
        example="john@example.com"
    )

    password: Optional[str] = Field(
        default=None,
        min_length=8,
        description="密码（密码模式下至少8位，免密模式可留空）",
        example=None
    )

    user_type: Literal["buyer", "provider", "admin"] = Field(
        ...,
        description="用户类型：buyer（采购方）或 provider（数据提供方）",
        example="buyer"
    )

    @field_validator('username')
    @classmethod
    def validate_username(cls, v: str) -> str:
        """验证用户名格式"""
        if not v.replace('_', '').isalnum():
            raise ValueError('用户名只能包含字母、数字和下划线')
        return v

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: Optional[str]) -> Optional[str]:
        """验证密码强度"""
        if not v:
            return v
        if not any(c.isupper() for c in v):
            raise ValueError('密码必须包含至少一个大写字母')
        if not any(c.islower() for c in v):
            raise ValueError('密码必须包含至少一个小写字母')
        if not any(c.isdigit() for c in v):
            raise ValueError('密码必须包含至少一个数字')
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "username": "john_doe",
                "email": "john@example.com",
                "password": "MyPassword123",
                "user_type": "buyer"
            }
        }


# ============ 响应模型 ============

class UserResponse(BaseModel):
    """
    用户响应模型（不包含密码）
    """
    id: str = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")
    # 【修改】这里加上了 Optional 和 None，允许邮箱为空
    email: Optional[str] = Field(None, description="邮箱地址")
    user_type: str = Field(..., description="用户类型")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    """
    登录响应模型
    """
    user: UserResponse = Field(..., description="用户信息")
    token: str = Field(..., description="访问令牌（JWT）")
    token_type: str = Field(default="bearer", description="令牌类型")

    class Config:
        json_schema_extra = {
            "example": {
                "user": {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "username": "john_doe",
                    "email": "john@example.com",
                    "user_type": "buyer",
                    "created_at": "2023-01-01T00:00:00Z",
                    "updated_at": "2023-01-01T00:00:00Z"
                },
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer"
            }
        }


class RegisterResponse(BaseModel):
    """
    注册响应模型
    """
    message: str = Field(..., description="操作结果消息")
    user: UserResponse = Field(..., description="新创建的用户信息")

    class Config:
        json_schema_extra = {
            "example": {
                "message": "注册成功",
                "user": {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "username": "john_doe",
                    "email": "john@example.com",
                    "user_type": "buyer",
                    "created_at": "2023-01-01T00:00:00Z",
                    "updated_at": "2023-01-01T00:00:00Z"
                }
            }
        }

class WeChatLoginRequest(BaseModel):
    """
    微信登录请求模型
    """
    code: str = Field(..., description="微信前端获取的临时登录凭证 code")
    user_type: Optional[str] = Field("buyer", description="如果是新用户，默认注册类型")

    class Config:
        json_schema_extra = {
            "example": {
                "code": "081ZgVFa1zxxxx...",
                "user_type": "buyer"
            }
        }
