"""数据库连接与会话管理。"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

engine = create_engine(
    settings.mysql_url,
    pool_size=10,
    max_overflow=20,
    echo=settings.app_debug,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI 依赖注入：提供数据库会话，请求结束时自动关闭。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
