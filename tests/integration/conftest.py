from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from dotenv import load_dotenv
from sqlalchemy import text

PROJECT_ROOT = Path(__file__).parent.parent.parent

EXPECTED_DATABASE = "landlord_test"

# Every application table managed by the Alembic migration chain.
MODEL_TABLES = [
    "owners",
    "properties",
    "rental_spaces",
    "tenants",
    "agreements",
    "utility_configs",
    "meters",
    "meter_readings",
    "utility_tariffs",
    "meter_replacements",
    "bills",
    "bill_lines",
    "payments",
    "payment_allocations",
    "deposits",
    "deposit_settlements",
    "deposit_deductions",
    "expenses",
]


def _configure_test_environment() -> None:
    """Point the suite at the isolated landlord_test database configured in the
    local .env file. Credentials stay in .env and are never committed."""
    load_dotenv(PROJECT_ROOT / ".env", override=True)
    os.environ["APP_ENV"] = "testing"
    os.environ["TEST_DATABASE_URL"] = os.environ["DATABASE_URL"]


def _upgrade_head() -> None:
    from alembic import command
    from alembic.config import Config

    cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", "migrations")
    command.upgrade(cfg, "head")


@pytest.fixture(scope="session")
def database():
    """Session-scoped real PostgreSQL Database at the Alembic head revision."""
    from app.core.config import get_settings
    from app.infrastructure.database import close_database, init_database

    _configure_test_environment()
    get_settings.cache_clear()
    db = init_database(testing=True)

    with db.engine.connect() as conn:
        actual = conn.execute(text("SELECT current_database()")).scalar()
    if actual != EXPECTED_DATABASE:
        close_database()
        pytest.exit(
            f"Refusing to run integration tests against database {actual!r}; "
            f"expected isolated test database {EXPECTED_DATABASE!r}"
        )

    _upgrade_head()
    yield db
    close_database()


@pytest.fixture(autouse=True)
def clean_db(database):
    """Remove any data left by a test so integration tests never depend on
    data written by another test (controlled-cleanup isolation on landlord_test).
    """
    yield
    with database.engine.begin() as conn:
        conn.execute(
            text("TRUNCATE TABLE " + ", ".join(MODEL_TABLES) + " RESTART IDENTITY CASCADE")
        )


@pytest.fixture
def session(database):
    """A fresh real session for repository-level tests. Commits are controlled
    per test; the autouse cleanup removes all rows afterwards."""
    s = database.session_factory()
    try:
        yield s
    finally:
        s.close()


@pytest.fixture
def repositories(session):
    from app.desktop.services import Repositories

    return Repositories(session)


@pytest.fixture
def services(repositories):
    from app.desktop.services import Services

    return Services(repositories)


@pytest.fixture
def run_with_services(database):
    """Run an operation(services) inside the application's normal session model
    (Database.session(): commit on success, rollback on failure)."""
    from app.desktop.services import DatabaseSession

    ds = DatabaseSession(database)

    def _run(operation: Callable[[Any], Any]) -> Any:
        with ds.services() as services:
            return operation(services)

    return _run


@pytest.fixture
def runner(database):
    """A real ServiceRunner wired to the landlord_test database.

    This is the same wiring the desktop UI uses: ServiceRunner ->
    DatabaseSession -> application services -> repositories -> PostgreSQL.
    """
    from app.desktop.services import DatabaseSession, ServiceRunner

    return ServiceRunner(DatabaseSession(database))


@pytest.fixture
def app_window(qapp, database):
    """A real MainWindow wired to the landlord_test database."""
    from app.desktop.main_window import MainWindow
    from app.desktop.services import DatabaseSession

    return MainWindow(database_session=DatabaseSession(database))
