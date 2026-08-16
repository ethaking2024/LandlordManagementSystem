from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any, cast

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.desktop.components.buttons import PrimaryButton, SecondaryButton
from app.desktop.components.dialogs import BaseDialog, ConfirmationDialog
from app.desktop.components.form import FormWidget
from app.desktop.dates import DateInput, format_date_display
from app.desktop.services import OPERATION_FAILED, ServiceRunner
from app.domain.enums import DepositStatus
from app.domain.value_objects import Money


def format_deposit_status(status: DepositStatus) -> str:
    return status.value.capitalize()


def format_money(amount: Any) -> str:
    if amount is None:
        return ""
    return f"NPR {amount}"


def _is_decimal(text: str) -> bool:
    try:
        Decimal(text)
        return True
    except Exception:
        return False


class RecordDepositDialog(BaseDialog):
    """Record a security deposit for an agreement via DepositService.

    The deposit always belongs to an agreement; the UI requires a valid agreement
    selection and shows the tenant, space and agreement for confirmation.
    """

    def __init__(self, runner: ServiceRunner, parent: QWidget | None = None) -> None:
        super().__init__("Record Deposit", parent=parent)
        self._runner = runner
        self._agreements: list[Any] = []
        self._result: Any = None
        self._saved = False

        self._form_widget = FormWidget()
        self._agreement_combo = QComboBox()
        self._agreement_combo.setObjectName("agreementCombo")
        self._agreement_info = QLabel("")
        self._agreement_info.setObjectName("dialogMessage")
        self._agreement_info.setWordWrap(True)
        self._amount_edit = QLineEdit()
        self._amount_edit.setPlaceholderText("e.g. 50000")
        self._received_date_input = DateInput()
        self._reference_edit = QLineEdit()
        self._reference_edit.setPlaceholderText("e.g. DEP receipt")
        self._notes_edit = QTextEdit()
        self._notes_edit.setMaximumHeight(80)

        self._form_widget.add_field("agreement", "Agreement", self._agreement_combo, required=True)
        self._form_widget.add_field("agreement_info", "Tenant / Space", self._agreement_info)
        self._form_widget.add_field("amount", "Deposit Amount (NPR)", self._amount_edit, required=True)
        self._form_widget.add_field("received_date", "Received Date", self._received_date_input, required=True)
        self._form_widget.add_field("reference", "Reference", self._reference_edit)
        self._form_widget.add_field("notes", "Notes", self._notes_edit)

        cast(QVBoxLayout, self.layout()).insertWidget(2, self._form_widget)

        cancel = SecondaryButton("Cancel")
        cancel.clicked.connect(self.reject)
        self.add_button(cancel)

        self._save_button = PrimaryButton("Record Deposit")
        self._save_button.setDefault(True)
        self._save_button.clicked.connect(self._on_save)
        self.add_button(self._save_button)

        self._load_agreements()

    def _load_agreements(self) -> None:
        def _load(services) -> list[tuple[Any, str, str]]:
            agreements = services.agreement().get_all_agreements()
            rows: list[tuple[Any, str, str]] = []
            for agreement in agreements:
                tenant = services.tenant().get_tenant(agreement.tenant_id)
                space = services.rental_space().get_rental_space(agreement.rental_space_id)
                rows.append((agreement, tenant.full_name or "", space.name or ""))
            return rows

        result = self._runner.run(_load, parent=self)
        if result is OPERATION_FAILED:
            return
        self._agreements = [entry[0] for entry in result]
        self._agreement_combo.clear()
        for agreement, tenant_name, space_name in result:
            label = f"{tenant_name} — {space_name}"
            self._agreement_combo.addItem(label, agreement.id)
        self._on_agreement_changed()

    def _on_agreement_changed(self, *_args) -> None:
        agreement_id = self._agreement_combo.currentData()
        if agreement_id is None:
            self._agreement_info.setText("No agreement selected.")
            return
        agreement = next((a for a in self._agreements if a.id == agreement_id), None)
        if agreement is None:
            self._agreement_info.setText("")
            return
        lines = [
            f"Start: {format_date_display(agreement.start_date)}",
        ]
        if agreement.end_date:
            lines.append(f"End: {format_date_display(agreement.end_date)}")
        lines.append(f"Status: {agreement.status.value.capitalize()}")
        self._agreement_info.setText("\n".join(lines))

    def _on_save(self) -> None:
        self._form_widget.clear_errors()
        agreement_id = self._agreement_combo.currentData()
        amount_text = self._amount_edit.text().strip()
        received_date = self._received_date_input.value()

        valid = True
        if agreement_id is None:
            self._form_widget.set_error("agreement", "An agreement is required.")
            valid = False
        if not amount_text:
            self._form_widget.set_error("amount", "A deposit amount is required.")
            valid = False
        elif not _is_decimal(amount_text):
            self._form_widget.set_error("amount", "Enter a valid amount.")
            valid = False
        if not self._received_date_input.is_valid():
            self._form_widget.set_error("received_date", "Enter a valid received date.")
            valid = False
        elif received_date is None:
            self._form_widget.set_error("received_date", "A received date is required.")
            valid = False
        if not valid:
            return

        amount = Money(Decimal(amount_text))
        reference = self._reference_edit.text().strip() or None
        notes = self._notes_edit.toPlainText().strip() or None
        self._result = self._runner.run(
            lambda s: s.deposit().record_deposit(
                agreement_id,
                amount,
                received_date,
                reference=reference,
                notes=notes,
            ),
            parent=self,
        )
        if self._result is OPERATION_FAILED:
            return
        self._saved = True
        self.accept()

    def result_deposit(self) -> Any:
        return self._result

    @property
    def saved(self) -> bool:
        return self._saved


class DeductionRow(QWidget):
    """A single settlement deduction row (reason + amount)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self._reason_edit = QLineEdit()
        self._reason_edit.setPlaceholderText("Reason (e.g. Cleaning)")
        self._amount_edit = QLineEdit()
        self._amount_edit.setPlaceholderText("Amount (NPR)")
        self._amount_edit.setFixedWidth(140)
        self._remove_button = SecondaryButton("Remove")

        layout.addWidget(self._reason_edit, 1)
        layout.addWidget(self._amount_edit)
        layout.addWidget(self._remove_button)

    def reason(self) -> str:
        return self._reason_edit.text().strip()

    def amount_text(self) -> str:
        return self._amount_edit.text().strip()

    def set_remove_callback(self, callback) -> None:
        self._remove_button.clicked.connect(callback)


class SettlementDialog(BaseDialog):
    """Settle a held deposit with deductions and a refund.

    The UI collects deduction reasons and amounts and displays the expected
    settlement summary. DepositService remains the sole authority over the
    refund + deductions == deposit rule and the active-agreement restriction.
    """

    def __init__(
        self,
        runner: ServiceRunner,
        deposit_id: uuid.UUID,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__("Settle Deposit", parent=parent)
        self._runner = runner
        self._deposit_id = deposit_id
        self._deposit: Any = None
        self._deduction_rows: list[DeductionRow] = []
        self._result: Any = None
        self._settled = False

        self._summary_label = QLabel("")
        self._summary_label.setObjectName("dialogMessage")
        self._summary_label.setWordWrap(True)
        self._summary_label.setTextInteractionFlags(
            self._summary_label.textInteractionFlags() | Qt.TextInteractionFlag.TextSelectableByMouse
        )

        self._deductions_label = QLabel("Deductions:")
        self._deductions_label.setObjectName("fieldLabel")
        self._deductions_container = QWidget()
        self._deductions_layout = QVBoxLayout(self._deductions_container)
        self._deductions_layout.setContentsMargins(0, 0, 0, 0)
        self._deductions_layout.setSpacing(6)

        self._add_deduction_button = SecondaryButton("Add Deduction")
        self._add_deduction_button.clicked.connect(self._on_add_deduction)

        self._settlement_date_input = DateInput()
        self._form_widget = FormWidget()
        self._form_widget.add_field("settlement_date", "Settlement Date", self._settlement_date_input, required=True)

        self._expected_label = QLabel("")
        self._expected_label.setObjectName("dialogMessage")
        self._expected_label.setWordWrap(True)
        self._expected_label.setTextInteractionFlags(
            self._expected_label.textInteractionFlags() | Qt.TextInteractionFlag.TextSelectableByMouse
        )

        layout = cast(QVBoxLayout, self.layout())
        layout.insertWidget(2, self._summary_label)
        layout.insertWidget(3, self._deductions_label)
        layout.insertWidget(4, self._deductions_container)
        layout.insertWidget(5, self._add_deduction_button)
        layout.insertWidget(6, self._form_widget)
        layout.insertWidget(7, self._expected_label)

        cancel = SecondaryButton("Cancel")
        cancel.clicked.connect(self.reject)
        self.add_button(cancel)

        self._settle_button = PrimaryButton("Complete Settlement")
        self._settle_button.setDefault(True)
        self._settle_button.clicked.connect(self._on_settle)
        self.add_button(self._settle_button)

        self._load()

    def _load(self) -> None:
        result = self._runner.run(
            lambda s: s.deposit().get_deposit(self._deposit_id),
            parent=self,
        )
        if result is OPERATION_FAILED:
            self._summary_label.setText("Could not load deposit details.")
            return
        self._deposit = result
        self._summary_label.setText(
            f"Deposit: {format_money(self._deposit.amount)} received on "
            f"{format_date_display(self._deposit.received_date)}"
        )
        self._on_add_deduction()

    def _on_add_deduction(self) -> None:
        row = DeductionRow()
        row.set_remove_callback(lambda: self._remove_deduction(row))
        self._deduction_rows.append(row)
        self._deductions_layout.addWidget(row)
        self._update_expected()

    def _remove_deduction(self, row: DeductionRow) -> None:
        if row in self._deduction_rows:
            self._deduction_rows.remove(row)
        row.setParent(None)
        row.deleteLater()
        self._update_expected()

    def _deduction_pairs(self) -> list[tuple[Decimal, str]]:
        pairs: list[tuple[Decimal, str]] = []
        for row in self._deduction_rows:
            reason = row.reason()
            amount_text = row.amount_text()
            if not reason and not amount_text:
                continue
            if reason and _is_decimal(amount_text) and Decimal(amount_text) > 0:
                pairs.append((Decimal(amount_text), reason))
        return pairs

    def _update_expected(self) -> None:
        if self._deposit is None:
            return
        total_deductions = sum((amount for amount, _reason in self._deduction_pairs()), Decimal("0"))
        expected_refund = self._deposit.amount.amount - total_deductions
        lines = [
            f"Deposit: {format_money(self._deposit.amount)}",
            f"Total deductions: {format_money(Money(total_deductions))}",
            f"Expected refund: {format_money(Money(expected_refund))}",
        ]
        self._expected_label.setText("\n".join(lines))

    def _on_settle(self) -> None:
        if self._deposit is None:
            return
        settlement_date = self._settlement_date_input.value()
        if not self._settlement_date_input.is_valid():
            self._form_widget.set_error("settlement_date", "Enter a valid settlement date.")
            return
        if settlement_date is None:
            self._form_widget.set_error("settlement_date", "A settlement date is required.")
            return

        invalid = [row for row in self._deduction_rows if row.reason() and not _is_decimal(row.amount_text())]
        if invalid:
            self._expected_label.setText("Enter a valid amount for every deduction reason.")
            return

        deductions = self._deduction_pairs()
        notes = None

        def _settle(services):
            settlement = services.deposit().create_settlement(
                self._deposit_id,
                settlement_date,
                deductions,
                notes=notes,
            )
            total_deductions = settlement.total_deductions
            refund = Money(self._deposit.amount.amount - total_deductions.amount)
            return services.deposit().complete_settlement(self._deposit_id, refund)

        self._result = self._runner.run(_settle, parent=self)
        if self._result is OPERATION_FAILED:
            return
        self._settled = True
        self.accept()

    def result_settlement(self) -> Any:
        return self._result

    @property
    def settled(self) -> bool:
        return self._settled


class DepositDetailDialog(BaseDialog):
    """Deposit details with settlement history and void where allowed."""

    def __init__(
        self,
        runner: ServiceRunner,
        deposit_id: uuid.UUID,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__("Deposit Details", parent=parent)
        self._runner = runner
        self._deposit_id = deposit_id
        self._deposit: Any = None

        self._details_label = QLabel("")
        self._details_label.setObjectName("dialogMessage")
        self._details_label.setWordWrap(True)
        self._details_label.setTextInteractionFlags(
            self._details_label.textInteractionFlags() | Qt.TextInteractionFlag.TextSelectableByMouse
        )

        layout = cast(QVBoxLayout, self.layout())
        layout.insertWidget(2, self._details_label)

        self._settle_button = SecondaryButton("Settle Deposit")
        self._settle_button.clicked.connect(self._on_settle)
        self._void_button = SecondaryButton("Void Deposit")
        self._void_button.setObjectName("dangerButton")
        self._void_button.clicked.connect(self._on_void)
        self.add_button(self._void_button)
        self.add_button(self._settle_button)

        close = SecondaryButton("Close")
        close.clicked.connect(self.accept)
        self.add_button(close)

        self._load()

    def _load(self) -> None:
        def _load_data(services) -> tuple[Any, str, str, Any, Any | None]:
            deposit = services.deposit().get_deposit(self._deposit_id)
            agreement = services.agreement().get_agreement(deposit.agreement_id)
            tenant = services.tenant().get_tenant(deposit.tenant_id)
            space = services.rental_space().get_rental_space(agreement.rental_space_id)
            settlement = services.deposit().get_settlement_by_deposit(deposit.id)
            return deposit, tenant.full_name or "", space.name or "", agreement, settlement

        result = self._runner.run(_load_data, parent=self)
        if result is OPERATION_FAILED:
            self._details_label.setText("Could not load deposit details.")
            return
        deposit, tenant_name, space_name, agreement, settlement = result
        self._deposit = deposit
        self._render(deposit, tenant_name, space_name, agreement, settlement)

    def _render(
        self,
        deposit: Any,
        tenant_name: str,
        space_name: str,
        agreement: Any,
        settlement: Any | None,
    ) -> None:
        lines = [
            f"Tenant: {tenant_name}",
            f"Rental Space: {space_name}",
            f"Status: {format_deposit_status(deposit.status)}",
            f"Received Date: {format_date_display(deposit.received_date)}",
            f"Amount: {format_money(deposit.amount)}",
            f"Agreement Start: {format_date_display(agreement.start_date)}",
            f"Agreement Status: {agreement.status.value.capitalize()}",
        ]
        if deposit.reference:
            lines.append(f"Reference: {deposit.reference}")
        if deposit.notes:
            lines.append(f"Notes: {deposit.notes}")

        if settlement is not None:
            lines.append("")
            lines.append(f"Settlement: {format_date_display(settlement.settlement_date)}")
            for deduction in settlement.deductions:
                lines.append(f"  Deduction — {deduction.reason}: {format_money(deduction.amount)}")
            if settlement.refund_amount is not None:
                lines.append(f"Refund: {format_money(settlement.refund_amount)}")
            lines.append(f"Total deductions: {format_money(settlement.total_deductions)}")
            if settlement.notes:
                lines.append(f"Settlement notes: {settlement.notes}")
        self._details_label.setText("\n".join(lines))

        is_held = deposit.status == DepositStatus.HELD
        self._settle_button.setEnabled(is_held)
        self._void_button.setEnabled(is_held)

    def _on_settle(self) -> None:
        if self._deposit is None or self._deposit.status != DepositStatus.HELD:
            return
        dialog = SettlementDialog(self._runner, self._deposit_id, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._load()

    def _on_void(self) -> None:
        if self._deposit is None or self._deposit.status != DepositStatus.HELD:
            return
        confirm = ConfirmationDialog(
            "Void Deposit",
            "Void this deposit? The deposit is marked void and kept in history.",
            parent=self,
            confirm_text="Void",
            danger=True,
        )
        if confirm.exec() != QDialog.DialogCode.Accepted or not confirm.confirmed:
            return
        result = self._runner.run(lambda s: s.deposit().void_deposit(self._deposit_id), parent=self)
        if result is OPERATION_FAILED:
            return
        self._load()
