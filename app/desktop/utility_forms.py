from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Any, cast

from PySide6.QtWidgets import (
    QComboBox,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.desktop.components.buttons import PrimaryButton, SecondaryButton
from app.desktop.components.dialogs import BaseDialog
from app.desktop.components.form import FormWidget
from app.desktop.dates import DateInput, format_date_display
from app.desktop.services import OPERATION_FAILED, ServiceRunner
from app.desktop.validation import is_decimal
from app.domain.enums import ElectricityConfigType, UtilityType, WaterConfigType

_ELECTRICITY_TYPES: list[tuple[str, str]] = [
    (ElectricityConfigType.FIXED.value, "Fixed"),
    (ElectricityConfigType.METERED.value, "Metered"),
]

_WATER_TYPES: list[tuple[str, str]] = [
    (WaterConfigType.NO_CHARGE.value, "No Charge"),
    (WaterConfigType.FIXED.value, "Fixed"),
    (WaterConfigType.METERED.value, "Metered"),
]

_UTILITY_LABELS: dict[UtilityType, str] = {
    UtilityType.ELECTRICITY: "Electricity",
    UtilityType.WATER: "Water",
}


def _config_type_options(utility_type: UtilityType) -> list[tuple[str, str]]:
    if utility_type == UtilityType.ELECTRICITY:
        return _ELECTRICITY_TYPES
    return _WATER_TYPES


def format_utility_config(config: Any) -> str:
    """Render a human-readable summary of a utility config."""
    if config is None:
        return "Not configured"
    config_type = str(config.config_type)
    if config_type in (ElectricityConfigType.FIXED.value, WaterConfigType.FIXED.value):
        amount = config.fixed_amount
        return f"Fixed — NPR {amount}" if amount is not None else "Fixed"
    if config_type in (ElectricityConfigType.METERED.value, WaterConfigType.METERED.value):
        return "Metered"
    if config_type == WaterConfigType.NO_CHARGE.value:
        return "No Charge"
    return config_type.capitalize()


class UtilityConfigDialog(BaseDialog):
    """Configure the electricity or water utility for a rental space.

    The utility type and config options come directly from the locked domain
    enums. All validation (valid config types, required fixed amounts, etc.)
    is delegated to UtilityConfigService.
    """

    def __init__(
        self,
        runner: ServiceRunner,
        rental_space_id: uuid.UUID,
        utility_type: UtilityType,
        config_data: dict[str, Any] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        label = _UTILITY_LABELS.get(utility_type, utility_type.value.capitalize())
        super().__init__(f"Configure {label}", parent=parent)
        self._runner = runner
        self._rental_space_id = rental_space_id
        self._utility_type = utility_type
        self._config_data = config_data or {}
        self._result: Any = None

        form = FormWidget()
        self._type_combo = QComboBox()
        self._type_combo.setObjectName("configTypeCombo")
        for value, text in _config_type_options(utility_type):
            self._type_combo.addItem(text, value)
        self._type_combo.currentIndexChanged.connect(self._on_type_changed)

        self._amount_edit = QLineEdit()
        self._amount_edit.setPlaceholderText("e.g. 1000 (per billing period)")

        form.add_field("config_type", "Billing Type", self._type_combo, required=True)
        form.add_field("fixed_amount", "Fixed Amount (NPR)", self._amount_edit)

        self._form = form
        cast(QVBoxLayout, self.layout()).insertWidget(2, form)

        cancel = SecondaryButton("Cancel")
        cancel.clicked.connect(self.reject)
        self.add_button(cancel)

        self._save_button = PrimaryButton("Save")
        self._save_button.setDefault(True)
        self._save_button.clicked.connect(self._on_save)
        self.add_button(self._save_button)

        self._populate_from_data()

    def _on_type_changed(self) -> None:
        is_fixed = self._type_combo.currentData() in (
            ElectricityConfigType.FIXED.value,
            WaterConfigType.FIXED.value,
        )
        self._amount_edit.setVisible(is_fixed)

    def _populate_from_data(self) -> None:
        config_type = self._config_data.get("config_type")
        if config_type:
            index = self._type_combo.findData(config_type)
            if index >= 0:
                self._type_combo.setCurrentIndex(index)
        amount = self._config_data.get("fixed_amount")
        if amount is not None:
            self._amount_edit.setText(str(amount))
        self._on_type_changed()

    def _on_save(self) -> None:
        self._form.clear_errors()
        config_type = self._type_combo.currentData()
        if config_type is None:
            self._form.set_error("config_type", "A billing type is required.")
            return
        fixed_text = self._amount_edit.text().strip()
        fixed_amount: str | None = fixed_text if fixed_text else None
        if fixed_amount is not None and not is_decimal(fixed_amount):
            self._form.set_error("fixed_amount", "Enter a valid amount.")
            return

        config_id = self._config_data.get("id")
        if config_id is not None:
            self._result = self._runner.run(
                lambda s: s.utility_config().update_config(
                    config_id,
                    config_type=config_type,
                    fixed_amount=fixed_amount,
                ),
                parent=self,
            )
        else:
            self._result = self._runner.run(
                lambda s: s.utility_config().set_config(
                    self._rental_space_id,
                    self._utility_type,
                    config_type,
                    fixed_amount=fixed_amount,
                ),
                parent=self,
            )
        if self._result is OPERATION_FAILED:
            return
        self.accept()

    def result_config(self) -> Any:
        return self._result


class MeterFormDialog(BaseDialog):
    """Add a meter to a rental space for a given utility via MeterService."""

    def __init__(
        self,
        runner: ServiceRunner,
        rental_space_id: uuid.UUID,
        utility_type: UtilityType,
        parent: QWidget | None = None,
    ) -> None:
        label = _UTILITY_LABELS.get(utility_type, utility_type.value.capitalize())
        super().__init__(f"Add {label} Meter", parent=parent)
        self._runner = runner
        self._rental_space_id = rental_space_id
        self._utility_type = utility_type
        self._result: Any = None

        form = FormWidget()
        self._identifier_edit = QLineEdit()
        self._identifier_edit.setPlaceholderText("e.g. ELEC-001")
        self._installation_input = DateInput()
        self._notes_edit = QTextEdit()
        self._notes_edit.setMaximumHeight(80)

        form.add_field("identifier", "Meter Identifier", self._identifier_edit, required=True)
        form.add_field("installation_date", "Installation Date", self._installation_input)
        form.add_field("notes", "Notes", self._notes_edit)

        self._form = form
        cast(QVBoxLayout, self.layout()).insertWidget(2, form)

        cancel = SecondaryButton("Cancel")
        cancel.clicked.connect(self.reject)
        self.add_button(cancel)

        self._save_button = PrimaryButton("Save")
        self._save_button.setDefault(True)
        self._save_button.clicked.connect(self._on_save)
        self.add_button(self._save_button)

    def _on_save(self) -> None:
        self._form.clear_errors()
        identifier = self._identifier_edit.text().strip()
        if not identifier:
            self._form.set_error("identifier", "A meter identifier is required.")
            return
        installation_date = self._installation_input.value()
        if not self._installation_input.is_valid():
            self._form.set_error("installation_date", "Enter a valid installation date.")
            return
        if installation_date is None:
            installation_date = date.today()

        self._result = self._runner.run(
            lambda s: s.meter().create_meter(
                self._rental_space_id,
                self._utility_type,
                identifier,
                installation_date,
                notes=self._notes_edit.toPlainText().strip() or None,
            ),
            parent=self,
        )
        if self._result is OPERATION_FAILED:
            return
        self.accept()

    def result_meter(self) -> Any:
        return self._result


class MeterReadingFormDialog(BaseDialog):
    """Record a meter reading via MeterReadingService.

    Sequence validation and decreasing-reading rejection are handled entirely by
    the service; the UI simply collects the meter, date, and value.
    """

    def __init__(
        self,
        runner: ServiceRunner,
        meter_id: uuid.UUID,
        meter_label: str,
        previous_reading: Decimal | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(f"Add Reading — {meter_label}", parent=parent)
        self._runner = runner
        self._meter_id = meter_id
        self._result: Any = None

        form = FormWidget()
        self._date_input = DateInput()
        self._value_edit = QLineEdit()
        self._value_edit.setPlaceholderText("e.g. 1380")
        self._notes_edit = QTextEdit()
        self._notes_edit.setMaximumHeight(80)

        hint = None
        if previous_reading is not None:
            hint = f"Previous reading: {previous_reading}"
        form.add_field("reading_date", "Reading Date", self._date_input, required=True)
        form.add_field("value", "Reading Value", self._value_edit, required=True, hint=hint)
        form.add_field("notes", "Notes", self._notes_edit)

        self._form = form
        cast(QVBoxLayout, self.layout()).insertWidget(2, form)

        cancel = SecondaryButton("Cancel")
        cancel.clicked.connect(self.reject)
        self.add_button(cancel)

        self._save_button = PrimaryButton("Save Reading")
        self._save_button.setDefault(True)
        self._save_button.clicked.connect(self._on_save)
        self.add_button(self._save_button)

    def _on_save(self) -> None:
        self._form.clear_errors()
        reading_date = self._date_input.value()
        if not self._date_input.is_valid():
            self._form.set_error("reading_date", "Enter a valid reading date.")
            return
        if reading_date is None:
            self._form.set_error("reading_date", "A reading date is required.")
            return
        value = self._value_edit.text().strip()
        if not value:
            self._form.set_error("value", "A reading value is required.")
            return
        if not is_decimal(value):
            self._form.set_error("value", "Enter a valid reading value.")
            return

        self._result = self._runner.run(
            lambda s: s.meter_reading().record_reading(
                self._meter_id,
                reading_date,
                value,
                notes=self._notes_edit.toPlainText().strip() or None,
            ),
            parent=self,
        )
        if self._result is OPERATION_FAILED:
            return
        self.accept()

    def result_reading(self) -> Any:
        return self._result


class MeterReplacementDialog(BaseDialog):
    """Replace an active meter via MeterReplacementService.

    The service records the final reading on the old meter, deactivates it, and
    creates the new meter with its initial reading. The UI never bypasses the
    controlled replacement path.
    """

    def __init__(
        self,
        runner: ServiceRunner,
        old_meter_id: uuid.UUID,
        old_meter_label: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(f"Replace Meter — {old_meter_label}", parent=parent)
        self._runner = runner
        self._old_meter_id = old_meter_id
        self._result: Any = None

        form = FormWidget()
        self._new_identifier_edit = QLineEdit()
        self._new_identifier_edit.setPlaceholderText("e.g. ELEC-002")
        self._replaced_on_input = DateInput()
        self._final_reading_edit = QLineEdit()
        self._final_reading_edit.setPlaceholderText("Final reading on the old meter")
        self._initial_reading_edit = QLineEdit()
        self._initial_reading_edit.setPlaceholderText("Initial reading on the new meter")
        self._notes_edit = QTextEdit()
        self._notes_edit.setMaximumHeight(80)

        form.add_field("new_identifier", "New Meter Identifier", self._new_identifier_edit, required=True)
        form.add_field("replaced_on", "Replaced On", self._replaced_on_input, required=True)
        form.add_field("final_reading", "Final Reading", self._final_reading_edit, required=True)
        form.add_field("initial_reading", "Initial Reading", self._initial_reading_edit, required=True)
        form.add_field("notes", "Notes", self._notes_edit)

        self._form = form
        cast(QVBoxLayout, self.layout()).insertWidget(2, form)

        cancel = SecondaryButton("Cancel")
        cancel.clicked.connect(self.reject)
        self.add_button(cancel)

        self._save_button = PrimaryButton("Replace Meter")
        self._save_button.setDefault(True)
        self._save_button.clicked.connect(self._on_save)
        self.add_button(self._save_button)

    def _on_save(self) -> None:
        self._form.clear_errors()
        new_identifier = self._new_identifier_edit.text().strip()
        replaced_on = self._replaced_on_input.value()
        final_reading = self._final_reading_edit.text().strip()
        initial_reading = self._initial_reading_edit.text().strip()

        valid = True
        if not new_identifier:
            self._form.set_error("new_identifier", "A new meter identifier is required.")
            valid = False
        if not self._replaced_on_input.is_valid():
            self._form.set_error("replaced_on", "Enter a valid replacement date.")
            valid = False
        elif replaced_on is None:
            self._form.set_error("replaced_on", "A replacement date is required.")
            valid = False
        if not final_reading:
            self._form.set_error("final_reading", "A final reading is required.")
            valid = False
        elif not is_decimal(final_reading):
            self._form.set_error("final_reading", "Enter a valid reading.")
            valid = False
        if not initial_reading:
            self._form.set_error("initial_reading", "An initial reading is required.")
            valid = False
        elif not is_decimal(initial_reading):
            self._form.set_error("initial_reading", "Enter a valid reading.")
            valid = False
        if not valid:
            return

        self._result = self._runner.run(
            lambda s: s.meter_replacement().replace_meter(
                self._old_meter_id,
                new_identifier,
                replaced_on,
                final_reading,
                initial_reading,
                notes=self._notes_edit.toPlainText().strip() or None,
            ),
            parent=self,
        )
        if self._result is OPERATION_FAILED:
            return
        self.accept()

    def result_replacement(self) -> Any:
        return self._result


def format_meter_latest_reading(latest: Any) -> str:
    """Render the latest reading of a meter, or a placeholder when absent."""
    if latest is None:
        return "No readings yet"
    return f"{latest.value} on {format_date_display(latest.reading_date)}"
