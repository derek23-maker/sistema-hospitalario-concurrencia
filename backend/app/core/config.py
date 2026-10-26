from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Valores de configuración leídos desde el entorno o un archivo .env."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    db_host: str = "127.0.0.1"
    db_port: int = Field(default=3306, ge=1, le=65535)
    db_name: str = "sistema_hospitalario"
    db_user: str = "hospital_app"
    db_password: str
    db_pool_size: int = Field(default=10, ge=1, le=32)
    db_pool_reset_session: bool = True

    api_title: str = "Sistema Hospitalario - API de Citas"
    api_cors_origins: str = "http://localhost,http://127.0.0.1"

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.api_cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
