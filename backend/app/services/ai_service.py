"""大模型 API 服务：对接 DeepSeek / 通义千问，支持流式输出。"""

from collections.abc import Generator

from openai import OpenAI

from app.config import settings

# 模型配置表
MODELS = {
    "deepseek-chat": {
        "id": "deepseek-chat",
        "name": "DeepSeek Chat",
        "provider": "deepseek",
        "description": "通用对话模型，性价比高，适合日常使用",
        "base_url": settings.deepseek_base_url,
        "api_key": settings.deepseek_api_key,
    },
    "qwen-turbo": {
        "id": "qwen-turbo",
        "name": "通义千问 Turbo",
        "provider": "alibaba",
        "description": "阿里云大模型，中文能力强",
        "base_url": settings.qwen_base_url,
        "api_key": settings.qwen_api_key,
    },
}

DEFAULT_MODEL = "deepseek-chat"

# 系统提示词
SYSTEM_PROMPT = """你是一个友好、专业的 AI 助手。请用简洁清晰的中文回答用户问题。
回答问题时请遵循以下原则：
1. 回答准确、有条理
2. 对于代码问题，给出可运行的示例
3. 如果不确定，坦诚说明"""


def get_available_models() -> list[dict]:
    """返回可用模型列表（含默认模型标记）。"""
    results = []
    for model_id, model_info in MODELS.items():
        results.append({
            "id": model_info["id"],
            "name": model_info["name"],
            "provider": model_info["provider"],
            "description": model_info["description"],
        })
    return results


def _get_client(model_name: str) -> OpenAI:
    """根据模型名获取对应的 OpenAI 客户端。"""
    model_info = MODELS.get(model_name, MODELS[DEFAULT_MODEL])
    return OpenAI(
        api_key=model_info["api_key"],
        base_url=model_info["base_url"],
    )


def chat_stream(
    model_name: str,
    messages: list[dict],
) -> Generator[str, None, None]:
    """向大模型 API 发送多轮对话消息并流式返回。

    Args:
        model_name: 模型 ID，如 deepseek-chat。
        messages: 消息列表，格式 [{"role": "user", "content": "..."}, ...]。

    Yields:
        每个 chunk 的文本增量（delta），流结束后自动停止。
    """
    client = _get_client(model_name)

    # 在消息列表最前面插入系统提示词
    full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages

    response = client.chat.completions.create(
        model=model_name,
        messages=full_messages,
        stream=True,
        temperature=0.7,
        max_tokens=4096,
    )

    for chunk in response:
        delta = chunk.choices[0].delta
        if delta.content:
            yield delta.content


def estimate_token_count(messages: list[dict]) -> int:
    """粗略估算 token 数（中英文混合，按字符数 / 2 估算）。

    Args:
        messages: 消息列表。

    Returns:
        估算的 token 数量。
    """
    total_chars = 0
    for msg in messages:
        total_chars += len(msg.get("content", ""))
    # 中英文混合经验值：约 2 字符 = 1 token
    return max(1, total_chars // 2)
