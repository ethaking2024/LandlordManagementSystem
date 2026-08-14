from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: Literal["development", "testing", "production"] = Field(
        default="development", validation_alias="APP_ENV"
    )
    app_debug: bool = Field(default=True, validation_alias="APP_DEBUG")
    app_name: str = Field(default="Landlord Management System", validation_alias="APP_NAME")

    database_url: PostgresDsn = Field(validation_alias="DATABASE_URL")
    test_database_url: PostgresDsn | None = Field(default=None, validation_alias="TEST_DATABASE_URL")

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="DEBUG", validation_alias="LOG_LEVEL"
    )
    log_format: Literal["json", "text"] = Field(default="json", validation_alias="LOG_FORMAT")

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def is_testing(self) -> bool:
        return self.app_env == "testing"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    def get_database_url(self, testing: bool = False) -> str:
        if testing and self.test_database_url:
            return str(self.test_database_url)
        return str(self.database_url)


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


def get_project_root() -> Path:
    return Path(__file__).parent.parent.parent
