from __future__ import annotations

import os
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import Settings, get_project_root


@pytest.mark.unit
def test_settings_loads_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "testing")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:pass@localhost:5432/testdb")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    settings = Settings()

    assert settings.app_env == "testing"
    assert str(settings.database_url) == "postgresql+psycopg://user:pass@localhost:5432/testdb"
    assert settings.log_level == "DEBUG"
    assert settings.is_testing is True
    assert settings.is_development is False
    assert settings.is_production is False


@pytest.mark.unit
def test_settings_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)

    # Disable dotenv so a local .env file cannot satisfy the required DATABASE_URL.
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


@pytest.mark.unit
def test_get_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:pass@localhost:5432/lms_dev")
    monkeypatch.setenv("TEST_DATABASE_URL", "postgresql+psycopg://user:pass@localhost:5432/lms_test")

    from app.core.config import get_settings

    # The settings cache may already be populated by other tests; clear it so the
    # environment set above is reflected.
    get_settings.cache_clear()
    settings = get_settings()

    assert settings.get_database_url(testing=False) == "postgresql+psycopg://user:pass@localhost:5432/lms_dev"
    assert settings.get_database_url(testing=True) == "postgresql+psycopg://user:pass@localhost:5432/lms_test"


@pytest.mark.unit
def test_project_root() -> None:
    root = get_project_root()
    assert root.name == "LandlordManagementSystem"
    assert (root / "pyproject.toml").exists()


@pytest.mark.unit
def test_settings_backup_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PG_BIN_DIR", raising=False)
    monkeypatch.delenv("BACKUP_DIR", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:pass@localhost:5432/testdb")

    settings = Settings(_env_file=None)

    assert settings.pg_bin_dir is None
    assert settings.backup_dir is None


@pytest.mark.unit
def test_settings_backup_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:pass@localhost:5432/testdb")
    monkeypatch.setenv("PG_BIN_DIR", r"C:\PostgreSQL\17\bin")
    monkeypatch.setenv("BACKUP_DIR", r"C:\data\lms-backups")

    settings = Settings(_env_file=None)

    assert settings.pg_bin_dir == r"C:\PostgreSQL\17\bin"
    assert settings.backup_dir == r"C:\data\lms-backups"


@pytest.mark.unit
def test_default_backup_dir_is_user_data(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import get_default_backup_dir

    monkeypatch.setenv("LOCALAPPDATA", r"C:\Users\tester\AppData\Local")

    backup_dir = get_default_backup_dir()

    assert str(backup_dir).lower().endswith("lms" + os.sep + "backups") or "backups" in str(backup_dir)


@pytest.mark.unit
def test_app_data_dir_uses_local_app_data_on_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import get_app_data_dir

    monkeypatch.setenv("LOCALAPPDATA", r"C:\Users\tester\AppData\Local")

    app_data = get_app_data_dir()

    assert str(app_data).lower().endswith("local" + os.sep + "lms")


@pytest.mark.unit
def test_config_dir_is_working_directory_when_not_frozen(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import get_config_dir

    assert get_config_dir() == Path.cwd()


@pytest.mark.unit
def test_env_file_resolution_points_at_dot_env_when_not_frozen(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import _resolve_env_file

    assert _resolve_env_file() == Path(os.getcwd()) / ".env"
