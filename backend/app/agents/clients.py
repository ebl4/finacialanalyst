from functools import lru_cache

from langchain_openai import ChatOpenAI

from app.core.config import get_settings


@lru_cache
def get_chat_model() -> ChatOpenAI:
    settings = get_settings()
    if not settings.openai_api_key or not settings.openai_api_key.get_secret_value().strip():
        raise RuntimeError("OPENAI_API_KEY is required to run financial analysis.")
    return ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key.get_secret_value(),
        temperature=0,
    )
