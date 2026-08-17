from __future__ import annotations

import os

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
def test_get_database_url() -> None:
    os.environ["DATABASE_URL"] = "postgresql+psycopg://user:pass@localhost:5432/lms_dev"
    os.environ["TEST_DATABASE_URL"] = "postgresql+psycopg://user:pass@localhost:5432/lms_test"

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
