from __future__ import annotations

import json
import sys
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from app.core.config import get_default_backup_dir, get_settings
from app.core.logging import get_logger
from app.core.version import RELEASE_LABEL, VERSION

logger = get_logger(__name__)

# Packaging and release support for the LMS desktop application.
#
# This module contains operations needed only during release builds, first-run
# setup, and packaged-app validation. It is not part of the normal user
# workflow:
#
# * is_frozen / resource_path - locate bundled resources.
# * run_database_migrations - apply Alembic migrations (``LMS.exe --migrate``).
# * run_self_check - validate a packaged build (``LMS.exe --self-check``).


def is_frozen() -> bool:
    """True when running inside a PyInstaller bundle."""
    return bool(getattr(sys, "frozen", False))


def resource_path(name: str) -> Path:
    """Absolute path to a bundled resource.

    Frozen builds read from the PyInstaller ``_MEIPASS`` directory; development
    reads from the repository root.
    """
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base / name


def run_database_migrations() -> int:
    """Apply Alembic migrations to the configured database. Returns an exit code."""
    from alembic import command
    from alembic.config import Config

    settings = get_settings()
    ini = resource_path("alembic.ini")
    migrations = resource_path("migrations")
    if not ini.is_file() or not migrations.is_dir():
        logger.error(
            "Alembic files missing from application bundle",
            extra={"extra_fields": {"ini": str(ini), "migrations": str(migrations)}},
        )
        print("ERROR: Alembic configuration was not found in the application bundle.")
        return 2

    cfg = Config(str(ini))
    cfg.set_main_option("script_location", str(migrations))
    cfg.set_main_option("sqlalchemy.url", settings.get_database_url())
    logger.info(
        "Applying database migrations",
        extra={"extra_fields": {"script_location": str(migrations)}},
    )
    command.upgrade(cfg, "head")
    print("Database migrations applied successfully.")
    return 0


def _write_report(report_path: str | None, checks: list[dict[str, object]], exit_code: int) -> None:
    payload = {
        "version": VERSION,
        "release": RELEASE_LABEL,
        "frozen": is_frozen(),
        "exit_code": exit_code,
        "checks": checks,
    }
    if report_path:
        Path(report_path).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    status = "PASS" if exit_code == 0 else "FAIL"
    print(f"self-check {status} ({exit_code})")
    for check in checks:
        marker = "ok" if check["ok"] else "!!"
        print(f"  [{marker}] {check['name']}: {check['detail']}")


def run_self_check(report_path: str | None = None) -> int:
    """Validate a packaged build and return a process exit code.

    The database configuration and connectivity are required. Missing PostgreSQL
    client tools are reported as a warning because the rest of the application
    remains usable; only backup/restore needs them.
    """
    checks: list[dict[str, object]] = []

    def record(name: str, ok: bool, detail: str) -> None:
        checks.append({"name": name, "ok": bool(ok), "detail": detail})

    try:
        settings = get_settings()
        record("configuration", True, f"app_env={settings.app_env}")
    except Exception as exc:  # noqa: BLE001 - report any configuration failure
        record("configuration", False, str(exc))
        _write_report(report_path, checks, 1)
        return 1

    database_url = settings.get_database_url()
    engine = None
    try:
        engine = create_engine(database_url, connect_args={"connect_timeout": 5})
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        record("database_connection", True, "SELECT 1 succeeded")
    except Exception as exc:  # noqa: BLE001 - report connection failure detail
        record("database_connection", False, f"could not connect: {exc}")
        _write_report(report_path, checks, 1)
        return 1
    finally:
        if engine is not None:
            engine.dispose()

    from app.infrastructure.backup import PostgresBackup, discover_pg_bin_dir

    pg_bin_dir = discover_pg_bin_dir()
    record(
        "backup_tools",
        pg_bin_dir is not None or settings.pg_bin_dir is not None,
        f"pg bin dir: {settings.pg_bin_dir or pg_bin_dir or 'not found (set PG_BIN_DIR)'}",
    )

    backup_dir = Path(settings.backup_dir) if settings.backup_dir else get_default_backup_dir()
    record("backup_directory", True, str(backup_dir))

    try:
        tool = PostgresBackup(url=make_url(database_url), pg_bin_dir=settings.pg_bin_dir)
        reachable = tool.check_connection()
        record("backup_restore_availability", reachable, "psql connection OK" if reachable else "psql could not connect")
    except Exception as exc:  # noqa: BLE001 - backup tooling must never block startup
        record("backup_restore_availability", False, str(exc))

    _write_report(report_path, checks, 0)
    return 0
