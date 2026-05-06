from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = Field(default="local", alias="APP_ENV")
    port: int = Field(default=8000, alias="PORT")

    database_url: str = Field(
        default="postgresql+psycopg://insightsync:insightsync@localhost:5432/insightsync",
        alias="DATABASE_URL",
    )
    sqlite_source_path: Path = Field(
        default=Path("insightsync/data/storage/demo/insightsync_demo.db"),
        alias="SQLITE_SOURCE_PATH",
    )

    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_chat_model: str = Field(default="gpt-4o-mini", alias="OPENAI_CHAT_MODEL")
    openai_embedding_model: str = Field(default="text-embedding-3-small", alias="OPENAI_EMBEDDING_MODEL")
    embedding_dimensions: int = Field(default=1536, alias="EMBEDDING_DIMENSIONS")

    llm_provider: str = Field(default="bigmodel", alias="LLM_PROVIDER")
    llm_api_key: str | None = Field(default=None, alias="LLM_API_KEY")
    llm_base_url: str | None = Field(default="https://open.bigmodel.cn/api/paas/v4", alias="LLM_BASE_URL")
    llm_chat_model: str = Field(default="glm-4.7-flash", alias="LLM_CHAT_MODEL")
    embedding_provider: str = Field(default="fallback", alias="EMBEDDING_PROVIDER")

    rag_top_k: int = Field(default=6, alias="RAG_TOP_K")
    rag_min_score: float = Field(default=0.15, alias="RAG_MIN_SCORE")
    enable_llm_generation: bool = Field(default=False, alias="ENABLE_LLM_GENERATION")

    cors_allow_origins_raw: str = Field(default="*", alias="CORS_ALLOW_ORIGINS")

    api_keys_raw: str = Field(default="", alias="API_KEYS")
    rate_limit_per_minute: int = Field(default=0, alias="RATE_LIMIT_PER_MINUTE")

    @property
    def cors_allow_origins(self) -> list[str]:
        """Parse CORS_ALLOW_ORIGINS (comma-separated) into a list."""

        raw = self.cors_allow_origins_raw.strip()
        if not raw or raw == "*":
            return ["*"]
        return [origin.strip() for origin in raw.split(",") if origin.strip()]

    @property
    def api_keys(self) -> set[str]:
        """Parse API_KEYS (comma-separated). Empty means auth disabled."""

        return {key.strip() for key in self.api_keys_raw.split(",") if key.strip()}

    @property
    def llm_enabled(self) -> bool:
        """Return whether real LLM calls are allowed."""

        return bool(self.enable_llm_generation and self.chat_api_key)

    @property
    def chat_api_key(self) -> str | None:
        """Return the configured chat API key with legacy OpenAI fallback."""

        return self.llm_api_key or self.openai_api_key

    @property
    def chat_model(self) -> str:
        """Return the configured chat model with legacy OpenAI fallback."""

        return self.llm_chat_model or self.openai_chat_model


@lru_cache
def get_settings() -> Settings:
    """Return cached runtime settings."""

    return Settings()
