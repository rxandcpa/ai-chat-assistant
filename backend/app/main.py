"""FastAPI 应用入口。"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine
from app.models import Conversation, Message, User  # noqa: F401  确保 create_all 发现所有表
from app.models.base import Base
from app.routers import auth, conversations, models, users


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时自动创建数据库表。"""
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="AI 智能对话助手 — 支持多轮对话、流式输出的 Web 应用",
    lifespan=lifespan,
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://127.0.0.1:8080"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

# 注册路由
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(conversations.router)
app.include_router(models.router)


@app.get("/", tags=["系统"])
async def root():
    """健康检查。"""
    return {"status": "ok", "app": settings.app_name, "version": "0.1.0"}
