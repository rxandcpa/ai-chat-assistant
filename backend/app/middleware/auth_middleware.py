"""JWT 认证中间件：从请求头提取 Token 并解析当前用户。"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.services.auth_service import AuthService

# HTTPBearer 自动从 Authorization header 提取 Bearer token
security_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: Session = Depends(get_db),
) -> User:
    """FastAPI 依赖注入：校验 JWT 并返回当前登录用户。

    用法：
        @router.get("/me")
        async def me(user: User = Depends(get_current_user)):
            ...

    Args:
        credentials: 从 Authorization header 提取的 Bearer token。
        db: 数据库会话。

    Returns:
        当前登录的 User 实例。

    Raises:
        HTTPException 401: token 无效、过期，或用户不存在。
    """
    service = AuthService(db)
    return service.get_current_user(credentials.credentials)
