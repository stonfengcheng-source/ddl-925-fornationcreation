import os
import jwt
import httpx
import bcrypt
from datetime import datetime, timedelta
from typing import Optional, Union, Any
from sqlalchemy.orm import Session
from fastapi import status
from app.core.exceptions import APIException
from app.models.user import User

# JWT 配置
SECRET_KEY = os.getenv("SECRET_KEY", "dev_secret_key_123")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7天过期


class AuthService:
    # ==========================
    # 基础工具方法
    # ==========================
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        if not hashed_password:
            return False
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )

    @staticmethod
    def get_password_hash(password: str) -> str:
        return bcrypt.hashpw(
            password.encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')

    @staticmethod
    def create_access_token(user_id: Union[str, int], expires_delta: Optional[timedelta] = None) -> str:
        """生成 JWT Token"""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        # 确保 sub 是字符串
        to_encode = {"sub": str(user_id), "exp": expire}
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    @staticmethod
    def user_to_response(user: User) -> dict:
        """格式化返回用户信息"""
        return {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "user_type": user.user_type,
            "created_at": user.created_at,
            "updated_at": user.updated_at
        }

    @staticmethod
    def get_user_by_username(db: Session, username: str):
        return db.query(User).filter(User.username == username).first()

    @staticmethod
    def get_user_by_email(db: Session, email: str):
        return db.query(User).filter(User.email == email).first()

    # ==========================
    # 核心修复：匹配你 API 调用的标准 create_user
    # ==========================
    @staticmethod
    def create_user(db: Session, username: str, password: str, user_type: str, email: str = None) -> User:
        """
        创建新用户
        参数显式定义，完全匹配 api/auth.py 中的调用
        """
        # 1. 检查用户名
        if AuthService.get_user_by_username(db, username):
            raise APIException(
                status_code=status.HTTP_400_BAD_REQUEST,
                error_code="USERNAME_EXISTS",
                message="用户名已存在"
            )

        # 2. 检查邮箱 (如果有)
        if email and AuthService.get_user_by_email(db, email):
            raise APIException(
                status_code=status.HTTP_400_BAD_REQUEST,
                error_code="EMAIL_EXISTS",
                message="邮箱已被注册"
            )

        # 3. 创建用户实例
        db_user = User(
            username=username,
            email=email,
            password=AuthService.get_password_hash(password),  # 只有在这里进行哈希
            user_type=user_type
        )

        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user

    @staticmethod
    def authenticate_user(db: Session, username: str, password: str):
        """
        普通登录验证逻辑
        返回 (user, error) 元组：
          - (user, None) 成功
          - (None, 'not_found') 用户不存在
          - (None, 'wrong_password') 密码错误
        """
        user = AuthService.get_user_by_username(db, username)
        if not user:
            # 也尝试用邮箱查找
            user = AuthService.get_user_by_email(db, username)
        if not user:
            return None, 'not_found'
        if not AuthService.verify_password(password, user.password):
            return None, 'wrong_password'
        return user, None

    # ==========================
    # 微信登录逻辑 (保留)
    # ==========================
    @staticmethod
    async def get_wechat_user_info(code: str) -> Optional[dict]:
        if code == "STUDENT_DEMO":
            print("🚀 [测试模式] 检测到演示代码，跳过微信服务器验证")
            return {
                "openid": "demo_student_openid_001",
                "session_key": "fake_session_key",
                "unionid": "demo_unionid"
            }

        APP_ID = os.getenv("WECHAT_APP_ID")
        APP_SECRET = os.getenv("WECHAT_APP_SECRET")

        if not APP_ID or not APP_SECRET:
            print(f"❌ 错误：未配置微信环境变量，且 Code '{code}' 不是演示代码")
            return None

        url = "https://api.weixin.qq.com/sns/oauth2/access_token"
        params = {
            "appid": APP_ID,
            "secret": APP_SECRET,
            "code": code,
            "grant_type": "authorization_code"
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                data = response.json()

            if "errcode" in data and data["errcode"] != 0:
                print(f"WeChat API Error: {data}")
                return None

            return data
        except Exception as e:
            print(f"Network Error: {str(e)}")
            return None

    @staticmethod
    def login_or_register_by_wechat(db: Session, openid: str, user_type: str = "buyer") -> User:
        user = db.query(User).filter(User.wechat_openid == openid).first()
        if user:
            return user

        import uuid
        random_suffix = str(uuid.uuid4())[:8]
        new_username = f"wx_{random_suffix}"

        new_user = User(
            username=new_username,
            wechat_openid=openid,
            user_type=user_type,
            email=None,
            password=None
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user