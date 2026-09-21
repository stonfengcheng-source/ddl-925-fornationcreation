"""
认证相关的 API 路由
(最终修复版：使用 HTTPBearer 解决 Swagger 无法粘贴 Token 的问题)
"""
from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials # 【核心修改】导入 HTTPBearer
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
    WeChatLoginRequest
)
from app.services.auth import AuthService
from app.models.user import User
from app.core.exceptions import APIException
import jwt
from jwt import PyJWTError
import os

# 创建路由器
router = APIRouter(
    prefix="/auth",
    tags=["认证"],
)

# ==========================================
# 1. 【核心修复】认证依赖 (解决 Swagger 弹窗问题)
# ==========================================
# 使用 HTTPBearer，Swagger UI 会提供一个简单的输入框让你粘贴 Token
security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    解析 Token 并获取当前登录用户
    """
    # 从请求头中提取 Token 字符串
    token = credentials.credentials

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # 确保这里的密钥与生成 Token 时的一致
        SECRET_KEY = os.getenv("SECRET_KEY", "dev_secret_key_123")
        ALGORITHM = "HS256"

        # 解码 Token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")

        if user_id is None:
            raise credentials_exception

    except PyJWTError:
        raise credentials_exception

    # 从数据库查找用户
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception

    return user


# ==========================================
# 2. 账号密码登录
# ==========================================
@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="用户登录",
    description="使用用户名/邮箱和密码登录"
)
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
) -> LoginResponse:
    user, auth_error = AuthService.authenticate_user(db, request.username, request.password)

    if auth_error == 'not_found':
        raise APIException(
            status_code=401,
            error_code="USER_NOT_FOUND",
            message="该用户未注册"
        )
    if auth_error == 'wrong_password':
        raise APIException(
            status_code=401,
            error_code="WRONG_PASSWORD",
            message="密码错误"
        )

    # 登录来源检查：source 字段区分 web / desktop
    source = request.source or 'web'
    if source == 'web' and user.user_type == 'provider':
        raise APIException(
            status_code=403,
            error_code="ROLE_NOT_ALLOWED",
            message="数据提供方请使用桌面客户端登录"
        )
    if source == 'desktop' and user.user_type not in ('provider',):
        raise APIException(
            status_code=403,
            error_code="ROLE_NOT_ALLOWED",
            message="该账号类型请使用网页端登录"
        )

    access_token = AuthService.create_access_token(user_id=str(user.id))

    return LoginResponse(
        user=AuthService.user_to_response(user),
        token=access_token,
        token_type="bearer"
    )


# ==========================================
# 3. 用户注册
# ==========================================
@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="用户注册"
)
async def register(
    request: RegisterRequest,
    db: Session = Depends(get_db)
) -> RegisterResponse:
    user = AuthService.create_user(
        db=db,
        username=request.username,
        email=request.email,
        password=request.password,
        user_type=request.user_type
    )

    return RegisterResponse(
        message="注册成功",
        user=AuthService.user_to_response(user)
    )


# ==========================================
# 4. 微信登录 (支持扫码/模拟)
# ==========================================
@router.post(
    "/wechat/login",
    response_model=LoginResponse,
    summary="微信PC扫码登录",
    description="前端传 code，后端换 openid 并自动登录/注册"
)
async def wechat_login(
    request: WeChatLoginRequest,
    db: Session = Depends(get_db)
) -> LoginResponse:
    # 1. 换取 OpenID
    wechat_data = await AuthService.get_wechat_user_info(request.code)

    if not wechat_data or "openid" not in wechat_data:
        raise APIException(
            status_code=400,
            error_code="WECHAT_AUTH_FAIL",
            message="微信授权失败"
        )

    # 2. 登录或注册
    user = AuthService.login_or_register_by_wechat(
        db,
        wechat_data["openid"],
        request.user_type
    )

    # 3. 生成 Token
    access_token = AuthService.create_access_token(user_id=str(user.id))

    return LoginResponse(
        user=AuthService.user_to_response(user),
        token=access_token,
        token_type="bearer"
    )