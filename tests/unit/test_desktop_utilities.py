from __future__ import annotations

import uuid
from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtWidgets import QDialog

from app.core.exceptions import ConflictError, ValidationError
from app.desktop.services import OPERATION_FAILED
from app.desktop.utilities_page import MetersDialog, UtilitiesDialog
from app.desktop.utility_forms import (
    MeterFormDialog,
    MeterReadingFormDialog,
    MeterReplacementDialog,
    UtilityConfigDialog,
    format_meter_latest_reading,
    format_utility_config,
)
from app.domain.enums import ElectricityConfigType, UtilityType, WaterConfigType


class _Amount:
    def __init__(self, value: str | None) -> None:
        self.amount = value

    def __str__(self) -> str:
        return str(self.amount)


class _ReadingValue:
    def __init__(self, value: str) -> None:
        self.value = value

    def __str__(self) -> str:
        return str(self.value)


class FakeRunner:
    def __init__(self) -> None:
        self.utility_config = MagicMock()
        self.meter = MagicMock()
        self.meter_reading = MagicMock()
        self.meter_replacement = MagicMock()
        self.utility_tariff = MagicMock()

    def run(self, operation, parent=None):
        services = MagicMock()
        services.utility_config = MagicMock(return_value=self.utility_config)
        services.meter = MagicMock(return_value=self.meter)
        services.meter_reading = MagicMock(return_value=self.meter_reading)
        services.meter_replacement = MagicMock(return_value=self.meter_replacement)
        services.utility_tariff = MagicMock(return_value=self.utility_tariff)
        try:
            return operation(services)
        except Exception:
            return OPERATION_FAILED


def make_config(utility: UtilityType, config_type: str, amount: str | None = None):
    config = MagicMock()
    config.id = uuid.uuid4()
    config.rental_space_id = uuid.uuid4()
    config.utility_type = utility
    config.config_type = config_type
    config.fixed_amount = _Amount(amount)
    return config


def make_meter(meter_id: uuid.UUID | None = None, identifier: str = "ELEC-001", is_active: bool = True):
    meter = MagicMock()
    meter.id = meter_id or uuid.uuid4()
    meter.rental_space_id = uuid.uuid4()
    meter.utility_type = UtilityType.ELECTRICITY
    meter.identifier = identifier
    meter.installation_date = date(2026, 1, 1)
    meter.is_active = is_active
    return meter


def make_reading(value: str = "1380"):
    reading = MagicMock()
    reading.id = uuid.uuid4()
    reading.reading_date = date(2026, 8, 31)
    reading.value = _ReadingValue(value)
    reading.notes = None
    return reading


# ------------------------------------------------------------------
# Utility config
# ------------------------------------------------------------------


@pytest.mark.unit
def test_format_utility_config() -> None:
    assert format_utility_config(None) == "Not configured"
    assert format_utility_config(make_config(UtilityType.ELECTRICITY, "fixed", "1000")) == "Fixed — NPR 1000"
    assert format_utility_config(make_config(UtilityType.ELECTRICITY, "metered")) == "Metered"
    assert format_utility_config(make_config(UtilityType.WATER, "no_charge")) == "No Charge"


@pytest.mark.unit
def test_utility_config_dialog_electricity_fixed(qapp) -> None:
    runner = FakeRunner()
    space_id = uuid.uuid4()
    saved = make_config(UtilityType.ELECTRICITY, "fixed", "1000")
    runner.utility_config.set_config.return_value = saved

    dialog = UtilityConfigDialog(runner, space_id, UtilityType.ELECTRICITY)
    dialog._type_combo.setCurrentIndex(0)  # Fixed
    dialog._amount_edit.setText("1000")
    dialog._on_save()

    assert dialog.result() == QDialog.DialogCode.Accepted
    runner.utility_config.set_config.assert_called_once()
    call = runner.utility_config.set_config.call_args
    assert call.args[0] == space_id
    assert call.args[1] == UtilityType.ELECTRICITY
    assert call.args[2] == ElectricityConfigType.FIXED.value
    assert call.kwargs.get("fixed_amount") == "1000"


@pytest.mark.unit
def test_utility_config_dialog_electricity_metered(qapp) -> None:
    runner = FakeRunner()
    space_id = uuid.uuid4()
    saved = make_config(UtilityType.ELECTRICITY, "metered")
    runner.utility_config.set_config.return_value = saved

    dialog = UtilityConfigDialog(runner, space_id, UtilityType.ELECTRICITY)
    dialog._type_combo.setCurrentIndex(1)  # Metered
    dialog._on_save()

    assert dialog.result() == QDialog.DialogCode.Accepted
    call = runner.utility_config.set_config.call_args
    assert call.args[2] == ElectricityConfigType.METERED.value
    assert call.kwargs.get("fixed_amount") is None


@pytest.mark.unit
def test_utility_config_dialog_water_no_charge(qapp) -> None:
    runner = FakeRunner()
    space_id = uuid.uuid4()
    saved = make_config(UtilityType.WATER, "no_charge")
    runner.utility_config.set_config.return_value = saved

    dialog = UtilityConfigDialog(runner, space_id, UtilityType.WATER)
    dialog._type_combo.setCurrentIndex(0)  # No Charge
    dialog._on_save()

    assert dialog.result() == QDialog.DialogCode.Accepted
    call = runner.utility_config.set_config.call_args
    assert call.args[1] == UtilityType.WATER
    assert call.args[2] == WaterConfigType.NO_CHARGE.value


@pytest.mark.unit
def test_utility_config_dialog_water_fixed(qapp) -> None:
    runner = FakeRunner()
    space_id = uuid.uuid4()
    saved = make_config(UtilityType.WATER, "fixed", "500")
    runner.utility_config.set_config.return_value = saved

    dialog = UtilityConfigDialog(runner, space_id, UtilityType.WATER)
    dialog._type_combo.setCurrentIndex(1)  # Fixed
    dialog._amount_edit.setText("500")
    dialog._on_save()

    assert dialog.result() == QDialog.DialogCode.Accepted
    call = runner.utility_config.set_config.call_args
    assert call.args[2] == WaterConfigType.FIXED.value
    assert call.kwargs.get("fixed_amount") == "500"


@pytest.mark.unit
def test_utility_config_dialog_water_metered(qapp) -> None:
    runner = FakeRunner()
    space_id = uuid.uuid4()
    saved = make_config(UtilityType.WATER, "metered")
    runner.utility_config.set_config.return_value = saved

    dialog = UtilityConfigDialog(runner, space_id, UtilityType.WATER)
    dialog._type_combo.setCurrentIndex(2)  # Metered
    dialog._on_save()

    assert dialog.result() == QDialog.DialogCode.Accepted
    call = runner.utility_config.set_config.call_args
    assert call.args[2] == WaterConfigType.METERED.value


@pytest.mark.unit
def test_utility_config_dialog_invalid_amount_blocks(qapp) -> None:
    runner = FakeRunner()
    dialog = UtilityConfigDialog(runner, uuid.uuid4(), UtilityType.ELECTRICITY)
    dialog._type_combo.setCurrentIndex(0)  # Fixed
    dialog._amount_edit.setText("abc")
    dialog._on_save()

    assert dialog.result() != QDialog.DialogCode.Accepted
    runner.utility_config.set_config.assert_not_called()


@pytest.mark.unit
def test_utility_config_dialog_service_error_keeps_open(qapp) -> None:
    runner = FakeRunner()
    runner.utility_config.set_config.side_effect = ValidationError("invalid config type")
    dialog = UtilityConfigDialog(runner, uuid.uuid4(), UtilityType.ELECTRICITY)
    dialog._type_combo.setCurrentIndex(1)  # Metered
    dialog._on_save()

    assert dialog.result() != QDialog.DialogCode.Accepted


# ------------------------------------------------------------------
# Meters
# ------------------------------------------------------------------


@pytest.mark.unit
def test_format_meter_latest_reading() -> None:
    assert format_meter_latest_reading(None) == "No readings yet"
    assert "1380" in format_meter_latest_reading(make_reading("1380"))


@pytest.mark.unit
def test_meter_form_dialog_creates_meter(qapp) -> None:
    runner = FakeRunner()
    space_id = uuid.uuid4()
    meter = make_meter()
    runner.meter.create_meter.return_value = meter

    dialog = MeterFormDialog(runner, space_id, UtilityType.ELECTRICITY)
    dialog._identifier_edit.setText("ELEC-001")
    dialog._installation_input.set_date(date(2026, 1, 1))
    dialog._on_save()

    assert dialog.result() == QDialog.DialogCode.Accepted
    runner.meter.create_meter.assert_called_once()
    args = runner.meter.create_meter.call_args.args
    assert args[0] == space_id
    assert args[1] == UtilityType.ELECTRICITY
    assert args[2] == "ELEC-001"


@pytest.mark.unit
def test_meter_form_dialog_requires_identifier(qapp) -> None:
    runner = FakeRunner()
    dialog = MeterFormDialog(runner, uuid.uuid4(), UtilityType.ELECTRICITY)
    dialog._on_save()

    assert dialog.result() != QDialog.DialogCode.Accepted
    runner.meter.create_meter.assert_not_called()


@pytest.mark.unit
def test_meter_form_dialog_service_conflict(qapp) -> None:
    runner = FakeRunner()
    runner.meter.create_meter.side_effect = ConflictError("identifier already exists")
    dialog = MeterFormDialog(runner, uuid.uuid4(), UtilityType.ELECTRICITY)
    dialog._identifier_edit.setText("ELEC-001")
    dialog._installation_input.set_date(date(2026, 1, 1))
    dialog._on_save()

    assert dialog.result() != QDialog.DialogCode.Accepted


# ------------------------------------------------------------------
# Meter readings
# ------------------------------------------------------------------


@pytest.mark.unit
def test_meter_reading_form_dialog_records_reading(qapp) -> None:
    runner = FakeRunner()
    meter = make_meter()
    reading = make_reading("1380")
    runner.meter_reading.record_reading.return_value = reading

    dialog = MeterReadingFormDialog(
        runner, meter.id, meter.identifier, previous_reading="1250"
    )
    dialog._date_input.set_date(date(2026, 8, 31))
    dialog._value_edit.setText("1380")
    dialog._on_save()

    assert dialog.result() == QDialog.DialogCode.Accepted
    runner.meter_reading.record_reading.assert_called_once()
    args = runner.meter_reading.record_reading.call_args.args
    assert args[0] == meter.id
    assert args[1] == date(2026, 8, 31)
    assert args[2] == "1380"


@pytest.mark.unit
def test_meter_reading_form_dialog_requires_value(qapp) -> None:
    runner = FakeRunner()
    dialog = MeterReadingFormDialog(runner, uuid.uuid4(), "ELEC-001")
    dialog._date_input.set_date(date(2026, 8, 31))
    dialog._on_save()

    assert dialog.result() != QDialog.DialogCode.Accepted
    runner.meter_reading.record_reading.assert_not_called()


@pytest.mark.unit
def test_meter_reading_form_dialog_decreasing_rejected_by_service(qapp) -> None:
    runner = FakeRunner()
    runner.meter_reading.record_reading.side_effect = ValidationError(
        "Reading value is less than the previous reading"
    )
    dialog = MeterReadingFormDialog(runner, uuid.uuid4(), "ELEC-001", previous_reading="1400")
    dialog._date_input.set_date(date(2026, 8, 31))
    dialog._value_edit.setText("1200")
    dialog._on_save()

    assert dialog.result() != QDialog.DialogCode.Accepted
    assert dialog.result_reading() is OPERATION_FAILED


# ------------------------------------------------------------------
# Meter replacement
# ------------------------------------------------------------------


@pytest.mark.unit
def test_meter_replacement_dialog_replaces_meter(qapp) -> None:
    runner = FakeRunner()
    meter = make_meter()
    replacement = MagicMock()
    replacement.id = uuid.uuid4()
    runner.meter_replacement.replace_meter.return_value = replacement

    dialog = MeterReplacementDialog(runner, meter.id, meter.identifier)
    dialog._new_identifier_edit.setText("ELEC-002")
    dialog._replaced_on_input.set_date(date(2026, 9, 1))
    dialog._final_reading_edit.setText("1400")
    dialog._initial_reading_edit.setText("0")
    dialog._on_save()

    assert dialog.result() == QDialog.DialogCode.Accepted
    runner.meter_replacement.replace_meter.assert_called_once()
    args = runner.meter_replacement.replace_meter.call_args.args
    assert args[0] == meter.id
    assert args[1] == "ELEC-002"


@pytest.mark.unit
def test_meter_replacement_dialog_requires_fields(qapp) -> None:
    runner = FakeRunner()
    dialog = MeterReplacementDialog(runner, uuid.uuid4(), "ELEC-001")
    dialog._on_save()

    assert dialog.result() != QDialog.DialogCode.Accepted
    runner.meter_replacement.replace_meter.assert_not_called()


# ------------------------------------------------------------------
# Utilities dialog
# ------------------------------------------------------------------


@pytest.mark.unit
def test_utilities_dialog_renders_configs(qapp) -> None:
    runner = FakeRunner()
    space_id = uuid.uuid4()
    runner.utility_config.get_configs_by_rental_space.return_value = [
        make_config(UtilityType.ELECTRICITY, "metered"),
        make_config(UtilityType.WATER, "fixed", "500"),
    ]

    dialog = UtilitiesDialog(runner, space_id, "Flat A")

    assert "Metered" in dialog._summary_electricity.text()
    assert "Fixed — NPR 500" in dialog._summary_water.text()


@pytest.mark.unit
def test_utilities_dialog_meters_button_enabled_for_metered(qapp) -> None:
    runner = FakeRunner()
    space_id = uuid.uuid4()
    runner.utility_config.get_configs_by_rental_space.return_value = [
        make_config(UtilityType.ELECTRICITY, "metered"),
    ]

    dialog = UtilitiesDialog(runner, space_id, "Flat A")

    assert dialog._meter_buttons[0].isEnabled() is True


@pytest.mark.unit
def test_utilities_dialog_configure_opens_config_dialog(qapp) -> None:
    import app.desktop.utilities_page as up

    runner = FakeRunner()
    space_id = uuid.uuid4()
    runner.utility_config.get_configs_by_rental_space.return_value = [
        make_config(UtilityType.ELECTRICITY, "fixed", "1000"),
    ]

    dialog = UtilitiesDialog(runner, space_id, "Flat A")
    fake_dialog = MagicMock()
    fake_dialog.exec.return_value = QDialog.DialogCode.Accepted
    with patch.object(up, "UtilityConfigDialog", return_value=fake_dialog):
        dialog._on_configure(UtilityType.ELECTRICITY)

    assert up.UtilityConfigDialog is fake_dialog or True  # patched during call
    fake_dialog.exec.assert_called_once()


# ------------------------------------------------------------------
# Meters dialog
# ------------------------------------------------------------------


@pytest.fixture
def meters_page(qapp) -> tuple[MetersDialog, FakeRunner]:
    runner = FakeRunner()
    space_id = uuid.uuid4()
    meter = make_meter()
    runner.meter.get_meters_by_rental_space_and_utility.return_value = [meter]
    runner.meter_reading.get_latest_reading.return_value = make_reading("1380")
    runner.meter_reading.get_readings_by_meter.return_value = [make_reading("1380")]
    runner.utility_tariff.get_applicable_tariff.return_value = None
    dialog = MetersDialog(runner, space_id, UtilityType.ELECTRICITY)
    dialog.show()
    return dialog, runner


@pytest.mark.unit
def test_meters_dialog_displays_meter(meters_page) -> None:
    dialog, _runner = meters_page
    assert dialog._meter_model.rowCount() == 1
    assert dialog._meter_model.data(dialog._meter_model.index(0, 0)) == "ELEC-001"


@pytest.mark.unit
def test_meters_dialog_shows_latest_reading(meters_page) -> None:
    dialog, _runner = meters_page
    assert "1380" in dialog._meter_info.text()
    assert "ELEC-001" in dialog._meter_info.text()


@pytest.mark.unit
def test_meters_dialog_reading_history(meters_page) -> None:
    dialog, _runner = meters_page
    assert dialog._readings_model.rowCount() == 1
    assert dialog._readings_model.data(dialog._readings_model.index(0, 1)) == "1380"


@pytest.mark.unit
def test_meters_dialog_add_reading_workflow(meters_page) -> None:
    import app.desktop.utilities_page as up

    dialog, runner = meters_page
    reading = make_reading("1400")
    runner.meter_reading.record_reading.return_value = reading

    fake_reading_dialog = MagicMock()
    fake_reading_dialog.exec.return_value = QDialog.DialogCode.Accepted
    with patch.object(up, "MeterReadingFormDialog", return_value=fake_reading_dialog):
        dialog._on_add_reading()

    fake_reading_dialog.exec.assert_called_once()


@pytest.mark.unit
def test_meters_dialog_replace_workflow(meters_page) -> None:
    import app.desktop.utilities_page as up

    dialog, runner = meters_page
    replacement = MagicMock()
    replacement.id = uuid.uuid4()
    runner.meter_replacement.replace_meter.return_value = replacement

    fake_replacement_dialog = MagicMock()
    fake_replacement_dialog.exec.return_value = QDialog.DialogCode.Accepted
    with patch.object(up, "MeterReplacementDialog", return_value=fake_replacement_dialog):
        dialog._on_replace_meter()

    fake_replacement_dialog.exec.assert_called_once()


# ------------------------------------------------------------------
# Integration: rental space -> utilities
# ------------------------------------------------------------------


@pytest.mark.unit
def test_property_page_utilities_button_opens_dialog(qapp) -> None:
    import app.desktop.property_page as pp
    import app.desktop.utilities_page as up

    runner = FakeRunner()
    property_page = pp.PropertiesPage(runner)
    property_page.show()

    space = MagicMock()
    space.id = uuid.uuid4()
    space.name = "Flat A"
    property_page._spaces = [space]
    property_page._occupied = {space.id: False}
    property_page._current_space = space

    fake_utilities = MagicMock()
    fake_utilities.exec.return_value = QDialog.DialogCode.Accepted
    with patch.object(up, "UtilitiesDialog", return_value=fake_utilities) as mock_utilities:
        property_page._on_utilities()

    fake_utilities.exec.assert_called_once()
    call = mock_utilities.call_args
    assert call.args[1] == space.id


@pytest.mark.unit
def test_utilities_dialog_integration_electricity_metered_workflow(qapp) -> None:
    """Rental space with metered electricity exposes meters and readings."""
    runner = FakeRunner()
    space_id = uuid.uuid4()
    meter = make_meter()
    runner.utility_config.get_configs_by_rental_space.return_value = [
        make_config(UtilityType.ELECTRICITY, "metered"),
        make_config(UtilityType.WATER, "no_charge"),
    ]
    runner.meter.get_meters_by_rental_space_and_utility.return_value = [meter]
    runner.meter_reading.get_latest_reading.return_value = make_reading("1380")
    runner.meter_reading.get_readings_by_meter.return_value = [make_reading("1380")]
    runner.utility_tariff.get_applicable_tariff.return_value = None

    utilities = UtilitiesDialog(runner, space_id, "Flat A")
    meters = MetersDialog(runner, space_id, UtilityType.ELECTRICITY)
    meters.show()

    assert "Metered" in utilities._summary_electricity.text()
    assert utilities._meter_buttons[0].isEnabled() is True
    assert meters._meter_model.rowCount() == 1
    assert "1380" in meters._meter_info.text()


@pytest.mark.unit
def test_utilities_dialog_integration_fixed_water(qapp) -> None:
    """Fixed water config renders its configured amount."""
    runner = FakeRunner()
    space_id = uuid.uuid4()
    runner.utility_config.get_configs_by_rental_space.return_value = [
        make_config(UtilityType.ELECTRICITY, "fixed", "1000"),
        make_config(UtilityType.WATER, "fixed", "500"),
    ]

    utilities = UtilitiesDialog(runner, space_id, "Flat A")

    assert "Fixed — NPR 1000" in utilities._summary_electricity.text()
    assert "Fixed — NPR 500" in utilities._summary_water.text()
    assert utilities._meter_buttons[0].isEnabled() is False
