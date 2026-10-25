from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AG_", env_file=".env", extra="ignore")
    database_url: str = "postgresql+psycopg://agentguard:agentguard@localhost:5432/agentguard"
    console_origins: list[str] = ["http://localhost:3000"]
    secure_cookies: bool = False
    session_hours: int = 8
    max_body_bytes: int = 1_048_576
    approval_seconds: int = 900
    openai_base_url: str = "https://api.openai.com/v1"
    openai_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434/v1"
    provider_timeout: float = 60
    otlp_endpoint: str = ""
    worker_metrics_port: int = 8002


settings = Settings()
