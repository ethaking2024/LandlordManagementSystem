from __future__ import annotations

from datetime import date

import pytest

from app.desktop.dates import (
    DateInput,
    format_bs_display,
    format_date_display,
    parse_ad_date,
)


@pytest.mark.unit
def test_format_date_display_includes_both_calendars() -> None:
    text = format_date_display(date(2026, 8, 10))
    assert "2026-08-10" in text
    assert "2083" in text


@pytest.mark.unit
def test_format_bs_display() -> None:
    assert format_bs_display(date(2026, 8, 10)) == "Shrawan 25, 2083"


@pytest.mark.unit
def test_parse_ad_date_valid() -> None:
    assert parse_ad_date("2026-08-10") == date(2026, 8, 10)


@pytest.mark.unit
def test_parse_ad_date_invalid() -> None:
    assert parse_ad_date("not-a-date") is None
    assert parse_ad_date("") is None


@pytest.mark.unit
def test_date_input_empty_is_valid(qapp) -> None:
    field = DateInput()
    assert field.value() is None
    assert field.is_valid() is True


@pytest.mark.unit
def test_date_input_ad_entry(qapp) -> None:
    field = DateInput()
    field.set_date(date(2026, 8, 10))
    assert field.value() == date(2026, 8, 10)
    assert "BS: Shrawan 25, 2083" in field._converted_label.text()


@pytest.mark.unit
def test_date_input_bs_entry(qapp) -> None:
    field = DateInput()
    field._calendar_combo.setCurrentIndex(1)  # BS
    field._date_edit.setText("2083-04-25")
    assert field.value() == date(2026, 8, 10)
    assert field._converted_label.text() == "AD: 2026-08-10"


@pytest.mark.unit
def test_date_input_invalid_bs(qapp) -> None:
    field = DateInput()
    field._calendar_combo.setCurrentIndex(1)  # BS
    field._date_edit.setText("2083-13-01")
    assert field.is_valid() is False
    assert field.value() is None
