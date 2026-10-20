from functools import lru_cache
from typing import Literal

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="", extra="ignore")

    app_env: Literal["development", "test", "production"] = "production"
    demo_mode: bool = False
    demo_auth_secret: SecretStr | None = None

    database_url: str = "postgresql+psycopg://financial:financial@localhost:5432/financial"
    jwt_issuer: str = ""
    jwt_audience: str = ""
    jwt_public_key: SecretStr | None = None
    ai_provider: Literal["openai", "gemini"] = "openai"
    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    google_api_key: SecretStr | None = None
    gemini_model: str = "gemini-2.5-flash"
    gemini_embedding_model: str = "gemini-embedding-001"
    s3_endpoint_url: str = ""
    s3_bucket: str = "financial-reports"
    s3_access_key_id: SecretStr | None = None
    s3_secret_access_key: SecretStr | None = None
    max_upload_bytes: int = 20 * 1024 * 1024
    cors_origins: list[str] = ["http://localhost:5173"]

    @model_validator(mode="after")
    def validate_demo_mode(self) -> "Settings":
        if self.demo_mode:
            if self.app_env == "production":
                raise ValueError("Demo mode is only allowed in development or test environments.")
            if not self.demo_auth_secret or len(self.demo_auth_secret.get_secret_value()) < 32:
                raise ValueError("DEMO_AUTH_SECRET must contain at least 32 characters.")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_ai_api_key(settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    if settings.ai_provider == "gemini":
        env_name = "GOOGLE_API_KEY"
        api_key = settings.google_api_key
    else:
        env_name = "OPENAI_API_KEY"
        api_key = settings.openai_api_key

    if not api_key or not api_key.get_secret_value().strip():
        raise RuntimeError(f"{env_name} must be configured for the selected AI provider.")
    return api_key.get_secret_value()
