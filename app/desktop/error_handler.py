from __future__ import annotations

import traceback
from typing import Any

from PySide6.QtWidgets import QMessageBox, QWidget

from app.core.exceptions import (
    ConflictError,
    DatabaseError,
    LMSError,
    NotFoundError,
    ValidationError,
)
from app.core.logging import get_logger

logger = get_logger(__name__)

_MESSAGE_TITLES: dict[type[LMSError], str] = {
    ValidationError: "Invalid Input",
    NotFoundError: "Not Found",
    ConflictError: "Conflict",
    DatabaseError: "Database Error",
}


def user_message(error: BaseException) -> str:
    """Translate an exception into a user-friendly message string."""
    if isinstance(error, LMSError):
        if isinstance(error, DatabaseError) and _is_constraint_violation(error):
            return "This action could not be completed because related records exist."
        return error.message
    return "An unexpected error occurred. Please try again."


def _is_constraint_violation(error: DatabaseError) -> bool:
    """Detect a foreign-key/unique constraint failure caused by related records."""
    cause = error.__cause__
    if cause is None:
        return False
    name = type(cause).__name__
    return name == "IntegrityError" or "IntegrityError" in name


def user_title(error: BaseException) -> str:
    """Translate an exception into a short user-facing title."""
    if isinstance(error, LMSError):
        return _MESSAGE_TITLES.get(type(error), "Error")
    return "Unexpected Error"


def handle_exception(
    error: BaseException,
    parent: QWidget | None = None,
    *,
    log_unexpected: bool = True,
) -> None:
    """Present an exception to the user and log unexpected ones.

    Known LMS errors are shown directly with their message. Anything else is
    logged via the application logger and shown as a generic unexpected error so
    that Python tracebacks are never exposed to normal users.
    """
    if isinstance(error, LMSError):
        logger.warning(
            "Application error shown to user",
            extra={"extra_fields": {"code": error.code, "message": error.message}},
        )
    else:
        if log_unexpected:
            logger.error(
                "Unexpected error in desktop application",
                extra={
                    "extra_fields": {
                        "error_type": type(error).__name__,
                        "traceback": "".join(
                            traceback.format_exception(type(error), error, error.__traceback__)
                        ),
                    }
                },
            )

    _show_message(parent, user_title(error), user_message(error))


def _show_message(parent: QWidget | None, title: str, message: str) -> None:
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setText(message)
    box.setStandardButtons(QMessageBox.StandardButton.Ok)
    box.exec()


def install_global_exception_handler() -> None:
    """Route uncaught Python exceptions to the desktop error handler.

    Prevents the PySide6 event loop from silently swallowing exceptions in slots.
    """
    import sys

    def excepthook(exc_type: type[BaseException], exc_value: BaseException, exc_tb: Any) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        handle_exception(exc_value)

    sys.excepthook = excepthook
