from __future__ import annotations

import pytest

from app.core.exceptions import (
    ApplicationError,
    BusinessRuleError,
    ConfigurationError,
    ConflictError,
    DatabaseError,
    LMSError,
    NotFoundError,
    RepositoryError,
    ValidationError,
)


@pytest.mark.unit
def test_base_exception() -> None:
    error = LMSError("Test error", code="TEST_ERROR")
    assert str(error) == "Test error"
    assert error.message == "Test error"
    assert error.code == "TEST_ERROR"


@pytest.mark.unit
def test_exception_hierarchy() -> None:
    exceptions = [
        ConfigurationError("config error"),
        DatabaseError("db error"),
        RepositoryError("repo error"),
        ValidationError("validation error"),
        NotFoundError("not found"),
        ConflictError("conflict"),
        BusinessRuleError("rule violation"),
        ApplicationError("app error"),
    ]

    for exc in exceptions:
        assert isinstance(exc, LMSError)
        assert isinstance(exc, Exception)


@pytest.mark.unit
def test_exception_can_be_raised_and_caught() -> None:
    with pytest.raises(ValidationError) as exc_info:
        raise ValidationError("Invalid input", code="INVALID_INPUT")

    assert exc_info.value.message == "Invalid input"
    assert exc_info.value.code == "INVALID_INPUT"
