"""对话服务：创建、查询、删除对话，管理消息历史，对接 AI 流式回复。"""

import json

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.conversation import Conversation, Message
from app.schemas.conversation import (
    ConversationCreate,
    ConversationDetail,
    ConversationListItem,
    ConversationListResponse,
    ConversationResponse,
)
from app.schemas.message import MessageCreate
from app.services.ai_service import chat_stream, estimate_token_count


class ConversationService:
    """对话与消息管理业务逻辑。"""

    def __init__(self, db: Session):
        self.db = db

    # ─── 对话 CRUD ─────────────────────────────────────────

    def create_conversation(
        self,
        user_id: int,
        data: ConversationCreate,
    ) -> ConversationResponse:
        """为用户创建一个新对话。"""
        conv = Conversation(
            user_id=user_id,
            title=data.title or "新对话",
            model_name=data.model_name or "deepseek-chat",
        )
        self.db.add(conv)
        self.db.commit()
        self.db.refresh(conv)
        return ConversationResponse.model_validate(conv)

    def list_conversations(
        self,
        user_id: int,
        page: int = 1,
        page_size: int = 10,
    ) -> ConversationListResponse:
        """分页获取用户的对话列表，含消息数量和最后一条消息预览。"""
        total = (
            self.db.query(Conversation)
            .filter(Conversation.user_id == user_id)
            .count()
        )

        conversations = (
            self.db.query(Conversation)
            .filter(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        items = []
        for conv in conversations:
            # 消息数量
            message_count = (
                self.db.query(Message)
                .filter(Message.conversation_id == conv.id)
                .count()
            )
            # 最后一条 AI 回复的预览
            last_msg = (
                self.db.query(Message)
                .filter(
                    Message.conversation_id == conv.id,
                    Message.role == "assistant",
                )
                .order_by(Message.created_at.desc())
                .first()
            )
            items.append(
                ConversationListItem(
                    id=conv.id,
                    title=conv.title,
                    model_name=conv.model_name,
                    message_count=message_count,
                    last_message=last_msg.content[:100] if last_msg else None,
                    updated_at=conv.updated_at,
                )
            )

        return ConversationListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )

    def get_conversation(
        self,
        user_id: int,
        conversation_id: int,
    ) -> ConversationDetail:
        """获取对话详情，含完整消息历史。"""
        conv = self._get_conv_and_check_owner(user_id, conversation_id)

        messages = (
            self.db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .all()
        )

        detail = ConversationDetail.model_validate(conv)
        detail.messages = [
            {
                "id": msg.id,
                "role": msg.role,
                "content": msg.content,
                "token_count": msg.token_count,
                "created_at": msg.created_at,
            }
            for msg in messages
        ]
        return detail

    def delete_conversation(
        self,
        user_id: int,
        conversation_id: int,
    ) -> None:
        """删除对话及其下所有消息（CASCADE）。"""
        conv = self._get_conv_and_check_owner(user_id, conversation_id)
        self.db.delete(conv)
        self.db.commit()

    # ─── 消息处理 ───────────────────────────────────────────

    def send_message_stream(
        self,
        user_id: int,
        conversation_id: int,
        data: MessageCreate,
        queue,
    ):
        """发送消息并流式获取 AI 回复，通过 queue 跨线程传输。

        流程：
        1. 保存用户消息
        2. 查询历史消息构建上下文
        3. 调用 AI 流式接口
        4. 每个 token chunk 通过 queue.put 发送
        5. 流结束后保存 AI 回复，并通过 queue.put 发送完成信号
        6. queue.put(None) 表示流结束
        """
        try:
            conv = self._get_conv_and_check_owner(user_id, conversation_id)

            # 1. 保存用户消息
            user_msg = Message(
                conversation_id=conversation_id,
                role="user",
                content=data.content,
                token_count=0,
            )
            self.db.add(user_msg)
            self.db.commit()

            # 2. 构建历史消息上下文
            history = (
                self.db.query(Message)
                .filter(Message.conversation_id == conversation_id)
                .order_by(Message.created_at.asc())
                .all()
            )
            api_messages = [
                {"role": msg.role, "content": msg.content} for msg in history
            ]

            # 3. 流式调用 AI
            accumulated = []
            for chunk in chat_stream(conv.model_name, api_messages):
                accumulated.append(chunk)
                queue.put({"event": "delta", "content": chunk})

            # 4. 保存 AI 回复
            ai_content = "".join(accumulated)
            token_count = estimate_token_count(api_messages)
            ai_msg = Message(
                conversation_id=conversation_id,
                role="assistant",
                content=ai_content,
                token_count=token_count,
            )
            self.db.add(ai_msg)
            self.db.commit()

            # 发送完成信号（带 AI 消息 ID）
            queue.put({
                "event": "done",
                "message_id": ai_msg.id,
                "token_count": token_count,
            })
        except Exception as exc:
            queue.put({"event": "error", "detail": str(exc)})
        finally:
            queue.put(None)  # 终止信号

    # ─── 权限检查 ───────────────────────────────────────────

    def _get_conv_and_check_owner(
        self,
        user_id: int,
        conversation_id: int,
    ) -> Conversation:
        """获取对话并校验归属权。

        Returns:
            Conversation 实例。

        Raises:
            HTTPException 404: 对话不存在。
            HTTPException 403: 对话不属于当前用户。
        """
        conv = self.db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()
        if conv is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="对话不存在",
            )
        if conv.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权访问此对话",
            )
        return conv
