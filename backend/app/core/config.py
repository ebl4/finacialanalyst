from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="", extra="ignore")

    database_url: str = "postgresql+psycopg://financial:financial@localhost:5432/financial"
    jwt_issuer: str = ""
    jwt_audience: str = ""
    jwt_public_key: SecretStr | None = None
    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    s3_endpoint_url: str = ""
    s3_bucket: str = "financial-reports"
    s3_access_key_id: SecretStr | None = None
    s3_secret_access_key: SecretStr | None = None
    max_upload_bytes: int = 20 * 1024 * 1024
    cors_origins: list[str] = ["http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
