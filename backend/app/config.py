from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    backend_host: str = "127.0.0.1"
    backend_port: int = 8000
    vlm_provider_url: str | None = None
    vlm_provider_api_key: str | None = Field(default=None, repr=False)
    vlm_provider_timeout_seconds: float = 10.0
    nvidia_api_key: str | None = Field(default=None, repr=False)
    nvidia_api_url: str = "https://integrate.api.nvidia.com/v1/chat/completions"
    nvidia_model: str = "meta/llama-3.2-11b-vision-instruct"
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
