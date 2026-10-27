"""Environment-driven settings. Defaults run on SQLite + demo LLM so a fresh
clone boots with zero setup; docker-compose overrides via env."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "School-MS"
    database_url: str = "sqlite:///./school_ms.db"  # Postgres in compose

    # JWT
    jwt_secret: str = "change-me-in-prod"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 15
    refresh_token_days: int = 7

    # LLM adapter: demo (deterministic, offline, default) | ollama | openrouter
    llm_backend: str = "demo"
    ollama_base_url: str = "http://localhost:11434"
    openrouter_api_key: str = ""
    openrouter_model: str = "meta-llama/llama-3.1-8b-instruct"

    # Comms gateway (V1): log (offline demo) | sms (HTTP gateway)
    comms_backend: str = "log"
    sms_base_url: str = ""
    sms_api_key: str = ""
    sms_channel: str = "sms"

    # deterministic seed
    seed: int = 42

    class Config:
        env_prefix = "SCHOOLMS_"
        env_file = ".env"


settings = Settings()
