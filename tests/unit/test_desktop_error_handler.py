from __future__ import annotations

from unittest.mock import patch

import pytest

from app.core.exceptions import (
    ConflictError,
    DatabaseError,
    LMSError,
    NotFoundError,
    ValidationError,
)
from app.desktop import error_handler


@pytest.mark.unit
def test_lms_error_message_used() -> None:
    error = ValidationError("Name is required")
    assert error_handler.user_message(error) == "Name is required"


@pytest.mark.unit
def test_unknown_error_gets_generic_message() -> None:
    error = RuntimeError("boom")
    assert error_handler.user_message(error) == "An unexpected error occurred. Please try again."


@pytest.mark.unit
@pytest.mark.parametrize(
    ("error", "expected_title"),
    [
        (ValidationError("x"), "Invalid Input"),
        (NotFoundError("x"), "Not Found"),
        (ConflictError("x"), "Conflict"),
        (DatabaseError("x"), "Database Error"),
        (LMSError("x"), "Error"),
        (RuntimeError("x"), "Unexpected Error"),
    ],
)
def test_user_titles(error, expected_title: str) -> None:
    assert error_handler.user_title(error) == expected_title


@pytest.mark.unit
def test_handle_known_error_logs_warning_not_exception() -> None:
    with (
        patch.object(error_handler.logger, "warning") as mock_warning,
        patch.object(error_handler.logger, "error") as mock_error,
        patch.object(error_handler, "_show_message") as mock_show,
    ):
        error_handler.handle_exception(ValidationError("bad"))

    mock_warning.assert_called_once()
    mock_error.assert_not_called()
    mock_show.assert_called_once()


@pytest.mark.unit
def test_handle_unexpected_error_logs_exception() -> None:
    with (
        patch.object(error_handler.logger, "error") as mock_error,
        patch.object(error_handler, "_show_message") as mock_show,
    ):
        error_handler.handle_exception(RuntimeError("boom"))

    mock_error.assert_called_once()
    mock_show.assert_called_once()


@pytest.mark.unit
def test_handle_exception_suppress_logging() -> None:
    with (
        patch.object(error_handler.logger, "error") as mock_error,
        patch.object(error_handler, "_show_message"),
    ):
        error_handler.handle_exception(RuntimeError("boom"), log_unexpected=False)

    mock_error.assert_not_called()


@pytest.mark.unit
def test_database_error_from_integrity_error_gets_friendly_message() -> None:
    from sqlalchemy.exc import IntegrityError

    cause = IntegrityError("stmt", {}, ValueError("foreign key violation"))
    error = DatabaseError("Database operation failed: foreign key violation")
    error.__cause__ = cause
    assert (
        error_handler.user_message(error)
        == "This action could not be completed because related records exist."
    )


@pytest.mark.unit
def test_plain_database_error_keeps_its_message() -> None:
    error = DatabaseError("Database operation failed: connection lost")
    assert error_handler.user_message(error) == "Database operation failed: connection lost"


@pytest.mark.unit
def test_global_exception_handler_installs(qapp) -> None:
    import sys

    original = sys.excepthook
    try:
        error_handler.install_global_exception_handler()
        assert sys.excepthook is not original
    finally:
        sys.excepthook = original
