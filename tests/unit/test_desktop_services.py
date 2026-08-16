from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.desktop.services import (
    OPERATION_FAILED,
    DatabaseSession,
    Repositories,
    ServiceRunner,
    Services,
)
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


@pytest.mark.unit
def test_service_runner_returns_operation_result() -> None:
    database_session = MagicMock()
    services = MagicMock()
    database_session.services.return_value.__enter__.return_value = services
    services.owner().get_all_owners.return_value = ["owner1"]

    runner = ServiceRunner(database_session)
    result = runner.run(lambda s: s.owner().get_all_owners())

    assert result == ["owner1"]
    database_session.services.assert_called_once()


@pytest.mark.unit
def test_service_runner_returns_failed_on_lms_error(qapp) -> None:
    from app.core.exceptions import ValidationError
    from app.desktop import error_handler

    database_session = MagicMock()
    services = MagicMock()
    database_session.services.return_value.__enter__.return_value = services
    services.property().create_property.side_effect = ValidationError("bad name")

    runner = ServiceRunner(database_session)
    with (
        patch.object(error_handler, "_show_message") as mock_show,
        patch.object(error_handler.logger, "warning"),
    ):
        result = runner.run(lambda s: s.property().create_property())

    assert result is OPERATION_FAILED
    mock_show.assert_called_once()


@pytest.mark.unit
def test_service_runner_returns_failed_on_unexpected_error(qapp) -> None:
    from app.desktop import error_handler

    database_session = MagicMock()
    services = MagicMock()
    database_session.services.return_value.__enter__.return_value = services
    services.property().get_all_properties.side_effect = RuntimeError("boom")

    runner = ServiceRunner(database_session)
    with (
        patch.object(error_handler, "_show_message") as mock_show,
        patch.object(error_handler.logger, "error"),
    ):
        result = runner.run(lambda s: s.property().get_all_properties())

    assert result is OPERATION_FAILED
    mock_show.assert_called_once()
