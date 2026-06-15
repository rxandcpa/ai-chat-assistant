"""JWT Token 创建与解析工具。"""

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.config import settings


def create_access_token(user_id: int) -> str:
    """为用户生成 JWT access token。

    Args:
        user_id: 用户 ID。

    Returns:
        签名的 JWT 字符串。
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {
        "sub": str(user_id),
        "iat": datetime.now(timezone.utc),
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> int | None:
    """解析 JWT token，返回用户 ID。

    Args:
        token: JWT 字符串。

    Returns:
        用户 ID；token 无效或过期时返回 None。
    """
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        return int(payload.get("sub"))
    except (JWTError, ValueError, TypeError):
        return None
