from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ENV = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(str(_REPO_ENV), ".env"), extra="ignore")

    database_url: str = "postgresql+psycopg://catalogue:catalogue@localhost:5433/catalogue"
    cors_origins: str = "http://localhost:5173"
    hf_token: str = ""
    hf_embedding_model: str = "intfloat/multilingual-e5-small"
    groq_api_key: str = ""
    groq_order_model: str = "openai/gpt-oss-120b"
    sparse_embedding_model: str = "Qdrant/bm25"
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "catalogue_products"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
