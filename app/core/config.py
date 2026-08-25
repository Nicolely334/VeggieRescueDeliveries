from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Veggie Rescue Deliveries API"
    app_environment: Literal["development", "test", "production"] = "development"
    debug: bool = False
    database_url: str = (
        "postgresql+psycopg://veggie_rescue:veggie_rescue@localhost:5432/veggie_rescue"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
