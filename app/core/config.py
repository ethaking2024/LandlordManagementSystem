from __future__ import annotations

import os
import sys
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


def get_project_root() -> Path:
    return Path(__file__).parent.parent.parent


def get_app_data_dir() -> Path:
    """User-data directory for LMS, kept outside the application/executable folder.

    This is where per-user configuration and derived user data live so they
    survive application upgrades. On Windows this is ``%LOCALAPPDATA%\\LMS`` and
    elsewhere ``~/.lms``.
    """
    home = Path.home()
    if os.name == "nt":
        local_app_data = Path(os.environ.get("LOCALAPPDATA", str(home / "AppData" / "Local")))
        return local_app_data / "LMS"
    return home / ".lms"


def get_config_dir() -> Path:
    """Directory that owns the application's ``.env`` file.

    In a packaged (frozen) build this is the folder containing the executable so
    a landlord can edit configuration next to the program they launch. In
    development it is the current working directory, matching the historical
    behaviour of loading ``.env`` from the project root.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path.cwd()


def _resolve_env_file() -> Path:
    """Locate the ``.env`` file used by :class:`Settings`.

    Frozen builds first look next to the executable and then fall back to the
    per-user application data directory; development uses ``.env`` in the
    working directory.
    """
    config_dir = get_config_dir()
    env_file = config_dir / ".env"
    if env_file.exists():
        return env_file
    if getattr(sys, "frozen", False):
        user_env = get_app_data_dir() / ".env"
        if user_env.exists():
            return user_env
    return env_file


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_resolve_env_file(),
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

    pg_bin_dir: str | None = Field(default=None, validation_alias="PG_BIN_DIR")
    backup_dir: str | None = Field(default=None, validation_alias="BACKUP_DIR")

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


def get_default_backup_dir() -> Path:
    """User-data directory for backups, kept separate from application files.

    Backups are user data and must survive application upgrades, so they live
    outside the installation folder.
    """
    return get_app_data_dir() / "Backups"
