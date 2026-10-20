from functools import lru_cache

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI

from app.core.config import get_ai_api_key, get_settings


@lru_cache
def get_chat_model() -> BaseChatModel:
    settings = get_settings()
    api_key = get_ai_api_key(settings)
    if settings.ai_provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            google_api_key=api_key,
            temperature=0,
        )
    return ChatOpenAI(model=settings.openai_model, api_key=api_key, temperature=0)
