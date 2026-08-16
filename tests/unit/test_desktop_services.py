from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.desktop.services import DatabaseSession, Repositories, Services
from app.desktop.theme import apply_theme, build_palette, build_stylesheet


@pytest.mark.unit
def test_build_stylesheet_contains_core_rules() -> None:
    stylesheet = build_stylesheet()
    assert "primaryButton" in stylesheet
    assert "sidebarList" in stylesheet
    assert "pageTitle" in stylesheet


@pytest.mark.unit
def test_build_palette() -> None:
    palette = build_palette()
    assert palette is not None


@pytest.mark.unit
def test_apply_theme(qapp) -> None:
    apply_theme(qapp)
    assert qapp.styleSheet() != ""


@pytest.mark.unit
def test_repositories_constructed_per_session() -> None:
    session = MagicMock()
    repos = Repositories(session)
    assert repos.owner is not None
    assert repos.property is not None
    assert repos.expense is not None


@pytest.mark.unit
def test_services_expose_service_factories() -> None:
    session = MagicMock()
    services = Services(Repositories(session))
    assert services.owner() is not None
    assert services.property() is not None
    assert services.expense() is not None
    assert services.billing() is not None
    assert services.deposit() is not None


@pytest.mark.unit
def test_database_session_opens_session_per_scope() -> None:
    database = MagicMock()
    session = MagicMock()
    database.session.return_value.__enter__.return_value = session

    with DatabaseSession(database).services() as services:
        assert services is not None
        assert services.repositories.owner is not None

    database.session.assert_called_once()
