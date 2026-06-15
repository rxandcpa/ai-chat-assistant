"""ORM 基类。"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """SQLAlchemy 声明式基类，所有模型继承自此。"""
    pass
