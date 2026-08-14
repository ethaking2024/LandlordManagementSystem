from __future__ import annotations

import logging

import pytest

from app.core.logging import JSONFormatter, TextFormatter, get_logger, setup_logging


@pytest.mark.unit
def test_setup_logging() -> None:
    setup_logging()
    root_logger = logging.getLogger()
    assert root_logger.level == logging.DEBUG
    assert len(root_logger.handlers) == 1


@pytest.mark.unit
def test_get_logger() -> None:
    logger = get_logger("test.module")
    assert logger.name == "test.module"


@pytest.mark.unit
def test_json_formatter() -> None:
    formatter = JSONFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=1,
        msg="Test message",
        args=(),
        exc_info=None,
    )
    output = formatter.format(record)
    assert "Test message" in output
    assert '"level": "INFO"' in output
    assert '"logger": "test"' in output


@pytest.mark.unit
def test_text_formatter() -> None:
    formatter = TextFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.WARNING,
        pathname="",
        lineno=1,
        msg="Warning message",
        args=(),
        exc_info=None,
    )
    output = formatter.format(record)
    assert "Warning message" in output
    assert "WARNING" in output
    assert "test" in output
