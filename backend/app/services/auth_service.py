"""用户认证服务：处理注册、登录、Token 签发与验证。"""

import bcrypt
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.user import UserCreate, UserLogin, UserResponse
from app.utils.token_helper import create_access_token, decode_access_token


class AuthService:
    """认证业务逻辑。"""

    def __init__(self, db: Session):
        self.db = db

    def register(self, data: UserCreate) -> UserResponse:
        """注册新用户。

        Args:
            data: 注册表单数据。

        Returns:
            创建成功的用户信息。

        Raises:
            HTTPException 400: 用户名或邮箱已存在。
        """
        # 检查用户名是否已存在
        existing = self.db.query(User).filter(
            (User.username == data.username) | (User.email == data.email)
        ).first()
        if existing:
            if existing.username == data.username:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="用户名已存在",
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="邮箱已被注册",
                )

        # 创建用户
        user = User(
            username=data.username,
            email=data.email,
            hashed_password=_hash_password(data.password),
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return UserResponse.model_validate(user)

    def login(self, data: UserLogin) -> dict:
        """用户登录。

        Args:
            data: 登录表单数据。

        Returns:
            包含 access_token、token_type、user 的字典。

        Raises:
            HTTPException 401: 邮箱或密码错误。
        """
        user = self.db.query(User).filter(User.email == data.email).first()
        if not user or not _verify_password(data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="邮箱或密码错误",
            )

        token = create_access_token(user.id)
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": UserResponse.model_validate(user),
        }

    def get_current_user(self, token: str) -> User:
        """通过 JWT token 获取当前用户。

        Args:
            token: Bearer token 字符串。

        Returns:
            当前登录的 User 实例。

        Raises:
            HTTPException 401: token 无效或过期。
        """
        user_id = decode_access_token(token)
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token 无效或已过期",
            )
        user = self.db.query(User).filter(User.id == user_id).first()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户不存在或已被删除",
            )
        return user


def _hash_password(password: str) -> str:
    """对密码进行 bcrypt 哈希。"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def _verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码是否匹配。"""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )
