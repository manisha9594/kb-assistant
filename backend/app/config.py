"""Settings loaded from environment variables or backend/.env."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # "openai" for real use; "fake" runs everything offline (tests, CI, demos without a key)
    llm_provider: str = "openai"
    openai_api_key: str = ""
    chat_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"

    # Optional web search (https://tavily.com). Leave empty to disable the web route.
    tavily_api_key: str = ""
    web_results: int = 4

    chroma_dir: str = "./data/chroma"
    collection_name: str = "knowledge_base"
    chunk_size: int = 1000
    chunk_overlap: int = 150
    top_k: int = 4
    # Chunks scoring below this relevance (0-1) are discarded. If none remain,
    # the agent falls back to web search when it is enabled.
    min_relevance: float = 0.25
    max_upload_mb: int = 25

    @property
    def web_enabled(self) -> bool:
        return self.llm_provider == "fake" or bool(self.tavily_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
