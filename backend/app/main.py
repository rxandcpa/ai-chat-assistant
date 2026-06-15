"""FastAPI 应用入口。"""

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import engine
from app.models import Conversation, Message, User  # noqa: F401
from app.models.base import Base
from app.routers import auth, conversations, models, users

# 前端静态文件路径（相对于 backend/ 目录）
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "frontend")


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

# API 路由（优先注册，确保 /api/* 不被静态文件覆盖）
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(conversations.router)
app.include_router(models.router)


@app.get("/api/health", tags=["系统"])
async def health() -> dict[str, str]:
    """健康检查。"""
    return {"status": "ok", "app": settings.app_name, "version": "0.1.0"}


# 静态文件（最后注册：匹配不到 API 路由的请求回退到前端文件）
if os.path.isdir(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
