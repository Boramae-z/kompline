"""Configuration settings for Kompline."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # OpenAI Configuration
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    openai_base_url: str = "https://api.openai.com/v1"

    # RAG Configuration
    rag_api_url: str = "http://localhost:8000"
    embedding_model: str = "text-embedding-3-small"

    # Agent Configuration
    max_feedback_iterations: int = 3
    confidence_threshold: float = 0.7

    # HITL Configuration
    hitl_enabled: bool = True
    require_auditor_approval_on_fail: bool = True

    # Tracing Configuration
    tracing_enabled: bool = True
    log_level: str = "INFO"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
