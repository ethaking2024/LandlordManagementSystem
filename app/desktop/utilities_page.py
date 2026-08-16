from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Any, cast

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from app.desktop.components.buttons import PrimaryButton, SecondaryButton
from app.desktop.components.dialogs import BaseDialog
from app.desktop.components.table import DataTableView, SimpleTableModel
from app.desktop.dates import format_date_display
from app.desktop.services import OPERATION_FAILED, ServiceRunner
from app.desktop.utility_forms import (
    MeterFormDialog,
    MeterReadingFormDialog,
    MeterReplacementDialog,
    UtilityConfigDialog,
    format_meter_latest_reading,
    format_utility_config,
)
from app.domain.enums import UtilityType

_UTILITY_LABELS: dict[UtilityType, str] = {
    UtilityType.ELECTRICITY: "Electricity",
    UtilityType.WATER: "Water",
}


class UtilitiesDialog(BaseDialog):
    """The 'Utilities' section for a rental space.

    Shows the electricity and water configuration for a rental space and lets
    the user configure each utility or manage its meters. All operations go
    through the application services via the ServiceRunner.
    """

    def __init__(
        self,
        runner: ServiceRunner,
        rental_space_id: uuid.UUID,
        rental_space_label: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(f"Utilities — {rental_space_label}", parent=parent)
        self._runner = runner
        self._rental_space_id = rental_space_id
        self._rental_space_label = rental_space_label
        self._configs: dict[UtilityType, Any] = {}
        self._meter_buttons: list[SecondaryButton] = []

        self._summary_label = QLabel("")
        self._summary_label.setObjectName("dialogMessage")
        self._summary_label.setWordWrap(True)
        self._summary_label.setTextInteractionFlags(
            self._summary_label.textInteractionFlags() | Qt.TextInteractionFlag.TextSelectableByMouse
        )

        layout = cast(QVBoxLayout, self.layout())
        layout.insertWidget(2, self._summary_label)

        self._electricity_row = self._build_utility_row(UtilityType.ELECTRICITY)
        self._water_row = self._build_utility_row(UtilityType.WATER)
        layout.insertWidget(3, self._electricity_row)
        layout.insertWidget(4, self._water_row)

        close = SecondaryButton("Close")
        close.clicked.connect(self.accept)
        self.add_button(close)

        self._load()

    def _build_utility_row(self, utility_type: UtilityType) -> QWidget:
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(8)

        label = QLabel(f"{_UTILITY_LABELS.get(utility_type, utility_type.value)}:")
        label.setObjectName("utilityRowLabel")
        row_layout.addWidget(label)

        summary = QLabel("Not configured")
        summary.setObjectName("utilityRowSummary")
        summary.setWordWrap(True)
        row_layout.addWidget(summary, 1)

        configure = SecondaryButton("Configure")
        configure.clicked.connect(lambda: self._on_configure(utility_type))
        row_layout.addWidget(configure)

        meters = SecondaryButton("Meters")
        meters.clicked.connect(lambda: self._on_meters(utility_type))
        meters.setEnabled(False)
        self._meter_buttons.append(meters)
        row_layout.addWidget(meters)

        setattr(self, f"_summary_{utility_type.value}", summary)
        return row

    def _load(self) -> None:
        def _load_data(services) -> dict[UtilityType, Any]:
            configs = services.utility_config().get_configs_by_rental_space(self._rental_space_id)
            return {config.utility_type: config for config in configs}

        result = self._runner.run(_load_data, parent=self)
        if result is OPERATION_FAILED:
            self._summary_label.setText("Could not load utility configuration.")
            return
        self._configs = result
        self._render()

    def _render(self) -> None:
        for utility_type in (UtilityType.ELECTRICITY, UtilityType.WATER):
            config = self._configs.get(utility_type)
            summary = getattr(self, f"_summary_{utility_type.value}")
            summary.setText(format_utility_config(config))
            is_metered = config is not None and config.config_type == "metered"
            button = self._meter_buttons[0 if utility_type == UtilityType.ELECTRICITY else 1]
            button.setEnabled(is_metered)

    def _on_configure(self, utility_type: UtilityType) -> None:
        config = self._configs.get(utility_type)
        dialog = UtilityConfigDialog(
            self._runner,
            self._rental_space_id,
            utility_type,
            config_data={
                "id": config.id,
                "config_type": config.config_type,
                "fixed_amount": config.fixed_amount.amount if config.fixed_amount else None,
            }
            if config
            else None,
            parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._load()

    def _on_meters(self, utility_type: UtilityType) -> None:
        dialog = MetersDialog(
            self._runner,
            self._rental_space_id,
            utility_type,
            parent=self,
        )
        dialog.exec()


class MetersDialog(BaseDialog):
    """Manage the meters of one utility type for a rental space.

    Lists the meters, shows the latest reading and applicable tariff for the
    selected meter, and provides add reading, reading history and meter
    replacement workflows. All business rules stay in the services.
    """

    def __init__(
        self,
        runner: ServiceRunner,
        rental_space_id: uuid.UUID,
        utility_type: UtilityType,
        parent: QWidget | None = None,
    ) -> None:
        label = _UTILITY_LABELS.get(utility_type, utility_type.value.capitalize())
        super().__init__(f"{label} Meters", parent=parent)
        self._runner = runner
        self._rental_space_id = rental_space_id
        self._utility_type = utility_type
        self._meters: list[Any] = []
        self._current_meter: Any = None
        self._latest: Any = None

        layout = cast(QVBoxLayout, self.layout())

        self._meter_table = DataTableView()
        self._meter_model = SimpleTableModel(
            ["Identifier", "Installed", "Status"],
            parent=self._meter_table,
        )
        self._meter_table.setModel(self._meter_model)
        self._meter_table.selectionModel().currentRowChanged.connect(self._on_meter_row_changed)
        layout.insertWidget(2, self._meter_table)

        self._meter_info = QLabel("")
        self._meter_info.setObjectName("dialogMessage")
        self._meter_info.setWordWrap(True)
        layout.insertWidget(3, self._meter_info)

        self._readings_table = DataTableView()
        self._readings_model = SimpleTableModel(
            ["Reading Date", "Value", "Notes"],
            parent=self._readings_table,
        )
        self._readings_table.setModel(self._readings_model)
        layout.insertWidget(4, self._readings_table)

        actions = QHBoxLayout()
        self._add_meter_button = PrimaryButton("Add Meter")
        self._add_meter_button.clicked.connect(self._on_add_meter)
        self._add_reading_button = SecondaryButton("Add Reading")
        self._add_reading_button.clicked.connect(self._on_add_reading)
        self._replace_button = SecondaryButton("Replace Meter")
        self._replace_button.clicked.connect(self._on_replace_meter)
        for button in (self._add_meter_button, self._add_reading_button, self._replace_button):
            actions.addWidget(button)
        actions.addStretch()
        layout.insertLayout(5, actions)

        close = SecondaryButton("Close")
        close.clicked.connect(self.accept)
        self.add_button(close)

        self._load_meters()

    def _load_meters(self) -> None:
        result = self._runner.run(
            lambda s: s.meter().get_meters_by_rental_space_and_utility(
                self._rental_space_id, self._utility_type
            ),
            parent=self,
        )
        if result is OPERATION_FAILED:
            self._meter_info.setText("Could not load meters.")
            return
        self._meters = result
        self._current_meter = None
        self._latest = None
        self._render_meters()

    def _render_meters(self) -> None:
        rows: list[tuple[str, ...]] = [
            (
                meter.identifier or "",
                format_date_display(meter.installation_date),
                "Active" if meter.is_active else "Inactive",
            )
            for meter in self._meters
        ]
        self._meter_model.set_rows(rows)
        self._meter_table.resize_columns_to_contents()
        has_rows = bool(rows)
        self._add_reading_button.setEnabled(False)
        self._replace_button.setEnabled(False)
        self._meter_info.setText("")
        self._readings_model.set_rows([])
        if has_rows:
            self._meter_table.selectRow(0)

    def _on_meter_row_changed(self, current, _previous) -> None:
        if current is None:
            self._current_meter = None
            self._add_reading_button.setEnabled(False)
            self._replace_button.setEnabled(False)
            self._meter_info.setText("")
            self._readings_model.set_rows([])
            return
        row = current.row()
        if row < 0 or row >= len(self._meters):
            return
        meter = self._meters[row]
        self._current_meter = meter
        self._add_reading_button.setEnabled(meter.is_active)
        self._replace_button.setEnabled(meter.is_active)
        self._load_meter_detail(meter)

    def _load_meter_detail(self, meter: Any) -> None:
        def _load(services) -> tuple[Any, Any, list[Any]]:
            latest = services.meter_reading().get_latest_reading(meter.id)
            tariff = services.utility_tariff().get_applicable_tariff(
                self._utility_type, date.today()
            )
            readings = services.meter_reading().get_readings_by_meter(meter.id)
            return latest, tariff, readings

        result = self._runner.run(_load, parent=self)
        if result is OPERATION_FAILED:
            return
        latest, tariff, readings = result
        self._latest = latest
        self._render_meter_detail(meter, latest, tariff, readings)

    def _render_meter_detail(
        self,
        meter: Any,
        latest: Any,
        tariff: Any,
        readings: list[Any],
    ) -> None:
        lines = [
            f"Meter: {meter.identifier or ''}",
            f"Latest reading: {format_meter_latest_reading(latest)}",
        ]
        if tariff is not None:
            lines.append(f"Applicable rate: NPR {tariff.rate} from {format_date_display(tariff.effective_from)}")
        self._meter_info.setText("\n".join(lines))

        reading_rows: list[tuple[str, ...]] = [
            (
                format_date_display(reading.reading_date),
                str(reading.value),
                reading.notes or "",
            )
            for reading in readings
        ]
        self._readings_model.set_rows(reading_rows)
        self._readings_table.resize_columns_to_contents()

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_add_meter(self) -> None:
        dialog = MeterFormDialog(
            self._runner,
            self._rental_space_id,
            self._utility_type,
            parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._load_meters()

    def _on_add_reading(self) -> None:
        if self._current_meter is None:
            return
        previous = self._latest.value if self._latest is not None else None
        dialog = MeterReadingFormDialog(
            self._runner,
            self._current_meter.id,
            self._current_meter.identifier or "meter",
            previous_reading=Decimal(str(previous)) if previous is not None else None,
            parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._load_meter_detail(self._current_meter)

    def _on_replace_meter(self) -> None:
        if self._current_meter is None:
            return
        dialog = MeterReplacementDialog(
            self._runner,
            self._current_meter.id,
            self._current_meter.identifier or "meter",
            parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._load_meters()
