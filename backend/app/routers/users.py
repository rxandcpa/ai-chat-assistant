"""用户路由：获取当前用户信息。"""

from fastapi import APIRouter, Depends

from app.middleware.auth_middleware import get_current_user
from app.models.user import User
from app.schemas.user import UserResponse

router = APIRouter(prefix="/api/users", tags=["用户"])


@router.get(
    "/me",
    response_model=UserResponse,
    summary="获取当前用户信息",
)
async def get_me(
    user: User = Depends(get_current_user),
) -> UserResponse:
    """返回当前登录用户的信息（需携带有效的 JWT token）。"""
    return UserResponse.model_validate(user)
