"""消息相关的 Pydantic 模型。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


class MessageCreate(BaseModel):
    """发送消息请求体。"""

    content: str

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("消息内容不能为空")
        if len(v) > 10000:
            raise ValueError("消息内容不能超过 10000 字符")
        return v


class MessageResponse(BaseModel):
    """消息响应（不含 token_count 时用于详情展示）。"""

    id: int
    role: str
    content: str
    token_count: int | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SSECompletePayload(BaseModel):
    """SSE 流式结束时的汇总数据。"""

    message_id: int
    token_count: int
