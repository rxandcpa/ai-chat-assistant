"""对话路由：创建、列表、详情、删除、发送消息（SSE 流式）。"""

import asyncio
import json
import threading
from collections.abc import AsyncGenerator
from queue import Empty, Queue

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth_middleware import get_current_user
from app.models.user import User
from app.schemas.conversation import (
    ConversationCreate,
    ConversationDetail,
    ConversationListResponse,
    ConversationResponse,
)
from app.schemas.message import MessageCreate
from app.services.conversation_service import ConversationService

router = APIRouter(prefix="/api/conversations", tags=["对话"])


@router.post(
    "",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建新对话",
)
async def create_conversation(
    data: ConversationCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConversationResponse:
    """为当前用户创建一个新的 AI 对话。可选择指定标题和模型。"""
    service = ConversationService(db)
    return service.create_conversation(user.id, data)


@router.get(
    "",
    response_model=ConversationListResponse,
    summary="获取对话列表",
)
async def list_conversations(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=50, description="每页数量"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConversationListResponse:
    """分页获取当前用户的对话列表，按最近活跃排序。"""
    service = ConversationService(db)
    return service.list_conversations(user.id, page=page, page_size=page_size)


@router.get(
    "/{conversation_id}",
    response_model=ConversationDetail,
    summary="获取对话详情",
)
async def get_conversation(
    conversation_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConversationDetail:
    """获取指定对话的详情，包含完整消息历史。"""
    service = ConversationService(db)
    return service.get_conversation(user.id, conversation_id)


@router.delete(
    "/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除对话",
)
async def delete_conversation(
    conversation_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除指定对话及其所有消息。"""
    service = ConversationService(db)
    service.delete_conversation(user.id, conversation_id)


@router.post(
    "/{conversation_id}/messages",
    summary="发送消息（SSE 流式）",
)
async def send_message(
    conversation_id: int,
    data: MessageCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """向 AI 发送消息，返回 SSE 流式响应。

    事件类型：
        event: delta  →  {"content": "..."}  逐字增量
        event: done   →  {"message_id": N, "token_count": N}
        event: error  →  {"detail": "..."}
    """
    service = ConversationService(db)
    queue: Queue = Queue()

    async def sse_generator() -> AsyncGenerator[str, None]:
        """从队列中读取事件并转换为 SSE 格式。"""
        # 在独立线程中运行同步阻塞的 AI 调用
        thread = threading.Thread(
            target=service.send_message_stream,
            args=(user.id, conversation_id, data, queue),
            daemon=True,
        )
        thread.start()

        while True:
            # 使用 asyncio 等待，避免阻塞事件循环
            try:
                item = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: queue.get(timeout=0.1)
                )
            except Empty:
                # 线程已完成且队列为空 → 退出
                if not thread.is_alive():
                    break
                continue

            if item is None:  # 终止信号
                break

            event = item["event"]
            if event == "delta":
                payload = json.dumps({"content": item["content"]}, ensure_ascii=False)
                yield f"event: delta\ndata: {payload}\n\n"
            elif event == "done":
                payload = json.dumps(
                    {"message_id": item["message_id"], "token_count": item["token_count"]}
                )
                yield f"event: done\ndata: {payload}\n\n"
            elif event == "error":
                payload = json.dumps({"detail": item["detail"]}, ensure_ascii=False)
                yield f"event: error\ndata: {payload}\n\n"

        thread.join()

    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
