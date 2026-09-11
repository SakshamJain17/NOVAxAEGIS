from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AEGIS"
    version: str = "0.1.0"
    environment: str = "development"

    host: str = "127.0.0.1"
    port: int = 8000

    model_provider: str = "ollama"
    model_name: str = "qwen3:8b"

    database_url: str = "sqlite:///./aegis.db"

    rime_api_key: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


settings = Settings()