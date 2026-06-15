"""数据库连接与会话管理。"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

# SQLite 需要额外参数，MySQL 需要连接池
_connect_args = {}
_engine_kwargs = {"echo": settings.app_debug}
if "sqlite" in settings.database_url:
    _connect_args["check_same_thread"] = False
else:
    _engine_kwargs["pool_size"] = 10
    _engine_kwargs["max_overflow"] = 20

engine = create_engine(
    settings.database_url,
    connect_args=_connect_args,
    **_engine_kwargs,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI 依赖注入：提供数据库会话，请求结束时自动关闭。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
