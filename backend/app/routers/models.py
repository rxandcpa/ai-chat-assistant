"""模型路由：获取可用 AI 模型列表。"""

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.ai_service import DEFAULT_MODEL, get_available_models

router = APIRouter(prefix="/api/models", tags=["模型"])


class ModelsResponse(BaseModel):
    """可用模型列表响应。"""

    models: list[dict]
    default: str


@router.get(
    "",
    response_model=ModelsResponse,
    summary="获取可用 AI 模型列表",
)
async def list_models() -> ModelsResponse:
    """返回所有可用的大模型及其信息。"""
    return ModelsResponse(
        models=get_available_models(),
        default=DEFAULT_MODEL,
    )
