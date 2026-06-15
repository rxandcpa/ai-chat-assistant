"""用户相关的 Pydantic 模型。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator


class UserCreate(BaseModel):
    """注册请求体。"""

    username: str
    email: EmailStr
    password: str

    @field_validator("username")
    @classmethod
    def username_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("用户名不能为空")
        if len(v) < 2:
            raise ValueError("用户名至少 2 个字符")
        if len(v) > 50:
            raise ValueError("用户名最多 50 个字符")
        return v

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("密码至少 6 位")
        return v


class UserLogin(BaseModel):
    """登录请求体。"""

    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """用户信息响应（不含密码）。"""

    id: int
    username: str
    email: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
