from __future__ import annotations

import uuid
from datetime import date
from typing import Any, cast

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QLabel,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.desktop.components.buttons import PrimaryButton, SecondaryButton
from app.desktop.components.dialogs import BaseDialog, ConfirmationDialog
from app.desktop.components.form import FormWidget
from app.desktop.dates import DateInput, format_date_display
from app.desktop.services import OPERATION_FAILED, ServiceRunner
from app.domain.enums import BillCategory, BillStatus

_CATEGORY_LABELS: dict[BillCategory, str] = {
    BillCategory.RENT: "Rent",
    BillCategory.ELECTRICITY: "Electricity",
    BillCategory.WATER: "Water",
}


def format_bill_status(status: BillStatus) -> str:
    return status.value.capitalize()


def format_money(amount: Any) -> str:
    if amount is None:
        return ""
    return f"NPR {amount}"


class GenerateBillDialog(BaseDialog):
    """Generate a bill for an agreement and billing period via BillingService.

    The user selects the agreement and the billing period; BillingService remains
    the sole authority over rent, proration, consumption, tariffs and totals. On
    success the generated bill is displayed in a read-only preview.
    """

    def __init__(self, runner: ServiceRunner, parent: QWidget | None = None) -> None:
        super().__init__("Generate Bill", parent=parent)
        self._runner = runner
        self._agreements: list[Any] = []
        self._result: Any = None
        self._generated = False

        self._form_widget = FormWidget()
        self._agreement_combo = QComboBox()
        self._agreement_combo.setObjectName("agreementCombo")
        self._period_start_input = DateInput()
        self._period_end_input = DateInput()
        self._notes_edit = QTextEdit()
        self._notes_edit.setMaximumHeight(80)

        self._form_widget.add_field("agreement", "Tenant / Agreement", self._agreement_combo, required=True)
        self._form_widget.add_field("period_start", "Billing Period Start", self._period_start_input, required=True)
        self._form_widget.add_field("period_end", "Billing Period End", self._period_end_input, required=True)
        self._form_widget.add_field("notes", "Notes", self._notes_edit)

        self._preview_label = QLabel("")
        self._preview_label.setObjectName("dialogMessage")
        self._preview_label.setWordWrap(True)
        self._preview_label.setTextInteractionFlags(
            self._preview_label.textInteractionFlags() | Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self._preview_label.hide()

        layout = cast(QVBoxLayout, self.layout())
        layout.insertWidget(2, self._form_widget)
        layout.insertWidget(3, self._preview_label)

        cancel = SecondaryButton("Cancel")
        cancel.clicked.connect(self.reject)
        self.add_button(cancel)

        self._generate_button = PrimaryButton("Generate Bill")
        self._generate_button.setDefault(True)
        self._generate_button.clicked.connect(self._on_generate)
        self.add_button(self._generate_button)

        self._load_agreements()

    def _load_agreements(self) -> None:
        def _load(services) -> list[tuple[Any, str]]:
            agreements = services.agreement().get_all_agreements()
            rows: list[tuple[Any, str]] = []
            for agreement in agreements:
                tenant = services.tenant().get_tenant(agreement.tenant_id)
                space = services.rental_space().get_rental_space(agreement.rental_space_id)
                tenant_name = tenant.full_name or ""
                space_name = space.name or ""
                label = f"{tenant_name} — {space_name}"
                rows.append((agreement, label))
            return rows

        result = self._runner.run(_load, parent=self)
        if result is OPERATION_FAILED:
            return
        self._agreements = [entry[0] for entry in result]
        self._agreement_combo.clear()
        for agreement, label in result:
            self._agreement_combo.addItem(label, agreement.id)

    def _on_generate(self) -> None:
        self._form_widget.clear_errors()
        agreement_id = self._agreement_combo.currentData()
        period_start = self._period_start_input.value()
        period_end = self._period_end_input.value()

        valid = True
        if agreement_id is None:
            self._form_widget.set_error("agreement", "An agreement is required.")
            valid = False
        if not self._period_start_input.is_valid():
            self._form_widget.set_error("period_start", "Enter a valid period start date.")
            valid = False
        elif period_start is None:
            self._form_widget.set_error("period_start", "A period start date is required.")
            valid = False
        if not self._period_end_input.is_valid():
            self._form_widget.set_error("period_end", "Enter a valid period end date.")
            valid = False
        elif period_end is None:
            self._form_widget.set_error("period_end", "A period end date is required.")
            valid = False
        if not valid:
            return

        billing_date = date.today()
        notes = self._notes_edit.toPlainText().strip() or None
        self._result = self._runner.run(
            lambda s: s.billing().generate_bill(
                agreement_id,
                period_start,
                period_end,
                billing_date,
                notes=notes,
            ),
            parent=self,
        )
        if self._result is OPERATION_FAILED:
            return
        self._generated = True
        self._show_preview(self._result)

    def _show_preview(self, bill: Any) -> None:
        self._preview_label.setText(self._preview_text(bill))
        self._preview_label.show()
        self._form_widget.setEnabled(False)
        self._generate_button.setText("Close")

    @staticmethod
    def _preview_text(bill: Any) -> str:
        lines = [
            "Bill generated successfully.",
            f"Period: {format_date_display(bill.period.start)} to {format_date_display(bill.period.end)}",
        ]
        for line in bill.lines:
            category = _CATEGORY_LABELS.get(line.category, line.category.value.capitalize())
            lines.append(f"{category}: {format_money(line.amount)}")
        lines.append(f"TOTAL: {format_money(bill.total)}")
        return "\n".join(lines)

    def result_bill(self) -> Any:
        return self._result

    @property
    def generated(self) -> bool:
        return self._generated


class BillDetailDialog(BaseDialog):
    """Read-only bill details with confirm/void actions where allowed."""

    def __init__(
        self,
        runner: ServiceRunner,
        bill_id: uuid.UUID,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__("Bill Details", parent=parent)
        self._runner = runner
        self._bill_id = bill_id
        self._bill: Any = None

        self._details_label = QLabel("")
        self._details_label.setObjectName("dialogMessage")
        self._details_label.setWordWrap(True)
        self._details_label.setTextInteractionFlags(
            self._details_label.textInteractionFlags() | Qt.TextInteractionFlag.TextSelectableByMouse
        )

        layout = cast(QVBoxLayout, self.layout())
        layout.insertWidget(2, self._details_label)

        self._confirm_button = SecondaryButton("Confirm Bill")
        self._confirm_button.clicked.connect(self._on_confirm)
        self._void_button = SecondaryButton("Void Bill")
        self._void_button.setObjectName("dangerButton")
        self._void_button.clicked.connect(self._on_void)
        self.add_button(self._void_button)
        self.add_button(self._confirm_button)

        close = SecondaryButton("Close")
        close.clicked.connect(self.accept)
        self.add_button(close)

        self._load()

    def _load(self) -> None:
        def _load_data(services) -> tuple[Any, str, str]:
            bill = services.billing().get_bill(self._bill_id)
            tenant = services.tenant().get_tenant(bill.tenant_id)
            space = services.rental_space().get_rental_space(bill.rental_space_id)
            return bill, tenant.full_name or "", space.name or ""

        result = self._runner.run(_load_data, parent=self)
        if result is OPERATION_FAILED:
            self._details_label.setText("Could not load bill details.")
            return
        bill, tenant_name, space_name = result
        self._bill = bill
        self._render(bill, tenant_name, space_name)

    def _render(self, bill: Any, tenant_name: str, space_name: str) -> None:
        lines = [
            f"Tenant: {tenant_name}",
            f"Rental Space: {space_name}",
            f"Status: {format_bill_status(bill.status)}",
            f"Billing Date: {format_date_display(bill.billing_date)}",
            f"Period: {format_date_display(bill.period.start)} to {format_date_display(bill.period.end)}",
        ]
        lines.append("")
        lines.append("Line items:")
        for line in bill.lines:
            category = _CATEGORY_LABELS.get(line.category, line.category.value.capitalize())
            lines.append(f"  {category}: {format_money(line.amount)}")
        lines.append(f"TOTAL: {format_money(bill.total)}")
        if bill.notes:
            lines.append(f"Notes: {bill.notes}")
        self._details_label.setText("\n".join(lines))

        is_draft = bill.status == BillStatus.DRAFT
        self._confirm_button.setEnabled(is_draft)
        self._void_button.setEnabled(bill.status != BillStatus.VOID)

    def _on_confirm(self) -> None:
        if self._bill is None or self._bill.status != BillStatus.DRAFT:
            return
        confirm = ConfirmationDialog(
            "Confirm Bill",
            "Confirm this bill? The amounts are frozen as a historical record.",
            parent=self,
            confirm_text="Confirm",
        )
        if confirm.exec() != QDialog.DialogCode.Accepted or not confirm.confirmed:
            return
        result = self._runner.run(lambda s: s.billing().confirm_bill(self._bill_id), parent=self)
        if result is OPERATION_FAILED:
            return
        self._load()

    def _on_void(self) -> None:
        if self._bill is None or self._bill.status == BillStatus.VOID:
            return
        confirm = ConfirmationDialog(
            "Void Bill",
            "Void this bill? The bill is marked void and excluded from billing.",
            parent=self,
            confirm_text="Void",
            danger=True,
        )
        if confirm.exec() != QDialog.DialogCode.Accepted or not confirm.confirmed:
            return
        result = self._runner.run(lambda s: s.billing().void_bill(self._bill_id), parent=self)
        if result is OPERATION_FAILED:
            return
        self._load()
