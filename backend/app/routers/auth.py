"""认证路由：注册、登录。"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.user import UserCreate, UserLogin, UserResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="用户注册",
)
async def register(
    data: UserCreate,
    db: Session = Depends(get_db),
) -> UserResponse:
    """创建新用户账号。用户名和邮箱必须全局唯一。"""
    service = AuthService(db)
    return service.register(data)


@router.post(
    "/login",
    summary="用户登录",
)
async def login(
    data: UserLogin,
    db: Session = Depends(get_db),
) -> dict:
    """使用邮箱和密码登录，返回 JWT access token。"""
    service = AuthService(db)
    return service.login(data)
