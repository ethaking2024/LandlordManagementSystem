from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import app.packaging as packaging


@pytest.mark.unit
def test_is_frozen_is_false_under_tests() -> None:
    assert packaging.is_frozen() is False


@pytest.mark.unit
def test_resource_path_points_at_repository_root() -> None:
    root = packaging.resource_path(".")
    assert (root / "alembic.ini").is_file()
    assert (root / "migrations").is_dir()


@pytest.mark.unit
def test_run_database_migrations_uses_alembic_upgrade(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    ini = tmp_path / "alembic.ini"
    ini.write_text("[alembic]\nscript_location = migrations\n")
    migrations = tmp_path / "migrations"
    migrations.mkdir()

    fake_settings = MagicMock()
    fake_settings.get_database_url.return_value = "postgresql+psycopg://user:pass@localhost:5432/db"

    monkeypatch.setattr(packaging, "resource_path", lambda name: tmp_path / name)
    monkeypatch.setattr(packaging, "get_settings", lambda: fake_settings)

    upgrade = MagicMock()
    monkeypatch.setattr("alembic.command.upgrade", upgrade)

    assert packaging.run_database_migrations() == 0
    upgrade.assert_called_once()
    assert upgrade.call_args.args[1] == "head"


@pytest.mark.unit
def test_run_database_migrations_fails_when_bundle_missing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    missing = tmp_path / "absent"
    monkeypatch.setattr(packaging, "resource_path", lambda name: missing / name)

    assert packaging.run_database_migrations() == 2


@pytest.mark.unit
def test_self_check_reports_pass_and_writes_json(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    report_path = tmp_path / "self-check.json"

    fake_settings = MagicMock()
    fake_settings.app_env = "production"
    fake_settings.get_database_url.return_value = "postgresql+psycopg://user:pass@localhost:5432/db"
    fake_settings.pg_bin_dir = None
    fake_settings.backup_dir = None

    fake_engine = MagicMock()
    fake_connect = fake_engine.connect.return_value.__enter__.return_value
    fake_connect.execute.return_value = MagicMock()

    fake_tool = MagicMock()
    fake_tool.check_connection.return_value = True

    monkeypatch.setattr(packaging, "get_settings", lambda: fake_settings)
    monkeypatch.setattr(packaging, "create_engine", lambda *a, **k: fake_engine)
    monkeypatch.setattr(packaging, "text", lambda s: s)
    monkeypatch.setattr(packaging, "make_url", lambda s: s)
    monkeypatch.setattr("app.infrastructure.backup.discover_pg_bin_dir", lambda: None)
    monkeypatch.setattr("app.infrastructure.backup.PostgresBackup", lambda url, pg_bin_dir=None: fake_tool)

    exit_code = packaging.run_self_check(str(report_path))

    assert exit_code == 0
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["exit_code"] == 0
    names = {check["name"] for check in payload["checks"]}
    assert names == {
        "configuration",
        "database_connection",
        "backup_tools",
        "backup_directory",
        "backup_restore_availability",
    }


@pytest.mark.unit
def test_self_check_fails_without_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom() -> object:
        raise RuntimeError("missing DATABASE_URL")

    monkeypatch.setattr(packaging, "get_settings", boom)

    assert packaging.run_self_check() == 1
