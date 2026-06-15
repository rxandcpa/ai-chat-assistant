"""FastAPI 应用入口。"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine
from app.models import Conversation, Message, User  # noqa: F401  确保 create_all 发现所有表
from app.models.base import Base
from app.routers import auth, conversations, models, users


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """应用生命周期：启动时自动创建数据库表。"""
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="AI 智能对话助手 — 支持多轮对话、流式输出的 Web 应用",
    lifespan=lifespan,
)

# CORS 配置（开发模式：允许本地前端从任意地址访问）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# 注册路由
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(conversations.router)
app.include_router(models.router)


@app.get("/", tags=["系统"])
async def root() -> dict[str, str]:
    """健康检查。"""
    return {"status": "ok", "app": settings.app_name, "version": "0.1.0"}
