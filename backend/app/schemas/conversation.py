"""对话相关的 Pydantic 模型。"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

from app.schemas.message import MessageResponse


class ConversationCreate(BaseModel):
    """创建对话请求体。"""

    title: Optional[str] = "新对话"
    model_name: Optional[str] = "deepseek-chat"

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str | None) -> str:
        if v is None:
            return "新对话"
        v = v.strip()
        return v if v else "新对话"


class ConversationResponse(BaseModel):
    """对话响应（列表项）。"""

    id: int
    title: str
    model_name: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationDetail(ConversationResponse):
    """对话详情（含消息列表）。"""

    messages: list[MessageResponse]


class ConversationListItem(BaseModel):
    """对话列表项（含最后一条消息预览）。"""

    id: int
    title: str
    model_name: str
    message_count: int
    last_message: str | None
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationListResponse(BaseModel):
    """对话列表分页响应。"""

    items: list[ConversationListItem]
    total: int
    page: int
    page_size: int
