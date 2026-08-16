from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any, cast

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QLabel,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.desktop.components.buttons import PrimaryButton, SecondaryButton
from app.desktop.components.dialogs import BaseDialog, ConfirmationDialog
from app.desktop.components.form import FormWidget
from app.desktop.components.table import DataTableView, SimpleTableModel
from app.desktop.dates import DateInput, format_date_display
from app.desktop.services import OPERATION_FAILED, ServiceRunner
from app.domain.enums import PaymentMethod, PaymentStatus
from app.domain.value_objects import Money


def format_payment_status(status: PaymentStatus) -> str:
    return status.value.capitalize()


def format_payment_method(method: PaymentMethod) -> str:
    return method.value.replace("_", " ").capitalize()


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


class RecordPaymentDialog(BaseDialog):
    """Record money received from a tenant via PaymentService.

    The payment date, amount, method, reference and notes are collected by the
    UI; PaymentService is the sole authority for validating and persisting the
    payment. Money stays a Decimal throughout.
    """

    def __init__(self, runner: ServiceRunner, parent: QWidget | None = None) -> None:
        super().__init__("Record Payment", parent=parent)
        self._runner = runner
        self._tenants: list[Any] = []
        self._result: Any = None
        self._saved = False

        self._form_widget = FormWidget()
        self._tenant_combo = QComboBox()
        self._tenant_combo.setObjectName("tenantCombo")
        self._payment_date_input = DateInput()
        self._amount_edit = QLineEdit()
        self._amount_edit.setPlaceholderText("e.g. 15000")
        self._method_combo = QComboBox()
        self._method_combo.setObjectName("methodCombo")
        for method in PaymentMethod:
            self._method_combo.addItem(format_payment_method(method), method)
        self._reference_edit = QLineEdit()
        self._reference_edit.setPlaceholderText("e.g. receipt number")
        self._notes_edit = QTextEdit()
        self._notes_edit.setMaximumHeight(80)

        self._form_widget.add_field("tenant", "Tenant", self._tenant_combo, required=True)
        self._form_widget.add_field("payment_date", "Payment Date", self._payment_date_input, required=True)
        self._form_widget.add_field("amount", "Amount (NPR)", self._amount_edit, required=True)
        self._form_widget.add_field("method", "Payment Method", self._method_combo, required=True)
        self._form_widget.add_field("reference", "Reference", self._reference_edit)
        self._form_widget.add_field("notes", "Notes", self._notes_edit)

        cast(QVBoxLayout, self.layout()).insertWidget(2, self._form_widget)

        cancel = SecondaryButton("Cancel")
        cancel.clicked.connect(self.reject)
        self.add_button(cancel)

        self._save_button = PrimaryButton("Record Payment")
        self._save_button.setDefault(True)
        self._save_button.clicked.connect(self._on_save)
        self.add_button(self._save_button)

        self._load_tenants()

    def _load_tenants(self) -> None:
        result = self._runner.run(
            lambda s: s.tenant().get_all_tenants(),
            parent=self,
        )
        if result is OPERATION_FAILED:
            return
        self._tenants = result
        self._tenant_combo.clear()
        for tenant in self._tenants:
            self._tenant_combo.addItem(tenant.full_name or "", tenant.id)

    def _on_save(self) -> None:
        self._form_widget.clear_errors()
        tenant_id = self._tenant_combo.currentData()
        payment_date = self._payment_date_input.value()
        amount_text = self._amount_edit.text().strip()
        method = self._method_combo.currentData()

        valid = True
        if tenant_id is None:
            self._form_widget.set_error("tenant", "A tenant is required.")
            valid = False
        if not self._payment_date_input.is_valid():
            self._form_widget.set_error("payment_date", "Enter a valid payment date.")
            valid = False
        elif payment_date is None:
            self._form_widget.set_error("payment_date", "A payment date is required.")
            valid = False
        if not amount_text:
            self._form_widget.set_error("amount", "An amount is required.")
            valid = False
        elif not _is_decimal(amount_text):
            self._form_widget.set_error("amount", "Enter a valid amount.")
            valid = False
        if not valid:
            return

        amount = Money(Decimal(amount_text))
        reference = self._reference_edit.text().strip() or None
        notes = self._notes_edit.toPlainText().strip() or None
        self._result = self._runner.run(
            lambda s: s.payment().record_payment(
                tenant_id,
                payment_date,
                amount,
                method,
                reference=reference,
                notes=notes,
            ),
            parent=self,
        )
        if self._result is OPERATION_FAILED:
            return
        self._saved = True
        self.accept()

    def result_payment(self) -> Any:
        return self._result

    @property
    def saved(self) -> bool:
        return self._saved


class AllocatePaymentDialog(BaseDialog):
    """Allocate a recorded payment to an eligible confirmed bill.

    The UI walks Payment -> Select Bill -> Amount -> Allocate. PaymentService is
    the sole authority over payment status, tenant matching, confirmed-bill
    requirements, allocation limits, duplicate allocations and outstanding
    amounts; the UI never reproduces those rules.
    """

    def __init__(
        self,
        runner: ServiceRunner,
        payment_id: uuid.UUID,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__("Allocate Payment", parent=parent)
        self._runner = runner
        self._payment_id = payment_id
        self._payment: Any = None
        self._tenant_id: uuid.UUID | None = None
        self._bills: list[Any] = []
        self._result: Any = None
        self._allocated = False

        self._summary_label = QLabel("")
        self._summary_label.setObjectName("dialogMessage")
        self._summary_label.setWordWrap(True)
        self._summary_label.setTextInteractionFlags(
            self._summary_label.textInteractionFlags() | Qt.TextInteractionFlag.TextSelectableByMouse
        )

        self._form_widget = FormWidget()
        self._bill_combo = QComboBox()
        self._bill_combo.setObjectName("billCombo")
        self._amount_edit = QLineEdit()
        self._amount_edit.setPlaceholderText("e.g. 8000")

        self._form_widget.add_field("bill", "Bill", self._bill_combo, required=True)
        self._form_widget.add_field("amount", "Allocated Amount (NPR)", self._amount_edit, required=True)

        layout = cast(QVBoxLayout, self.layout())
        layout.insertWidget(2, self._summary_label)
        layout.insertWidget(3, self._form_widget)

        cancel = SecondaryButton("Cancel")
        cancel.clicked.connect(self.reject)
        self.add_button(cancel)

        self._allocate_button = PrimaryButton("Allocate")
        self._allocate_button.setDefault(True)
        self._allocate_button.clicked.connect(self._on_allocate)
        self.add_button(self._allocate_button)

        self._load()

    def _load(self) -> None:
        def _load_data(services) -> tuple[Any, uuid.UUID, list[Any]]:
            payment = services.payment().get_payment(self._payment_id)
            bills = services.payment().get_allocatable_bills(payment.tenant_id)
            return payment, payment.tenant_id, bills

        result = self._runner.run(_load_data, parent=self)
        if result is OPERATION_FAILED:
            self._summary_label.setText("Could not load payment details.")
            return
        payment, tenant_id, bills = result
        self._payment = payment
        self._tenant_id = tenant_id
        self._bills = bills
        self._render()

    def _render(self) -> None:
        payment = self._payment
        self._summary_label.setText(self._summary_text(payment))
        self._bill_combo.clear()
        for bill in self._bills:
            label = (
                f"{format_date_display(bill.period.start)} to {format_date_display(bill.period.end)} "
                f"— Outstanding: {format_money(bill.total)}"
            )
            self._bill_combo.addItem(label, bill.id)

    @staticmethod
    def _summary_text(payment: Any) -> str:
        return (
            f"Payment: {format_money(payment.amount)} on {format_date_display(payment.payment_date)} "
            f"({format_payment_status(payment.status)})"
        )

    def _on_allocate(self) -> None:
        if self._payment is None:
            return
        self._form_widget.clear_errors()
        bill_id = self._bill_combo.currentData()
        amount_text = self._amount_edit.text().strip()

        valid = True
        if bill_id is None:
            self._form_widget.set_error("bill", "A bill is required.")
            valid = False
        if not amount_text:
            self._form_widget.set_error("amount", "An allocated amount is required.")
            valid = False
        elif not _is_decimal(amount_text):
            self._form_widget.set_error("amount", "Enter a valid amount.")
            valid = False
        if not valid:
            return

        amount = Money(Decimal(amount_text))
        self._result = self._runner.run(
            lambda s: s.payment().allocate_payment(self._payment_id, bill_id, amount),
            parent=self,
        )
        if self._result is OPERATION_FAILED:
            return
        self._allocated = True
        self.accept()

    def result_allocation(self) -> Any:
        return self._result

    @property
    def allocated(self) -> bool:
        return self._allocated


class ApplyCreditDialog(BaseDialog):
    """Apply a tenant's available credit to an eligible bill.

    The available credit and eligible bills come from PaymentService. The oldest
    first allocation strategy and all eligibility rules stay in the service.
    """

    def __init__(self, runner: ServiceRunner, parent: QWidget | None = None) -> None:
        super().__init__("Apply Tenant Credit", parent=parent)
        self._runner = runner
        self._tenants: list[Any] = []
        self._bills: list[Any] = []
        self._result: Any = None
        self._applied = False

        self._form_widget = FormWidget()
        self._tenant_combo = QComboBox()
        self._tenant_combo.setObjectName("tenantCombo")
        self._tenant_combo.currentIndexChanged.connect(self._on_tenant_changed)
        self._credit_label = QLabel("")
        self._credit_label.setObjectName("dialogMessage")
        self._credit_label.setWordWrap(True)
        self._bill_combo = QComboBox()
        self._bill_combo.setObjectName("billCombo")
        self._amount_edit = QLineEdit()
        self._amount_edit.setPlaceholderText("e.g. 5000")

        self._form_widget.add_field("tenant", "Tenant", self._tenant_combo, required=True)
        self._form_widget.add_field("credit", "Available Credit", self._credit_label)
        self._form_widget.add_field("bill", "Bill", self._bill_combo, required=True)
        self._form_widget.add_field("amount", "Credit Amount (NPR)", self._amount_edit, required=True)

        cast(QVBoxLayout, self.layout()).insertWidget(2, self._form_widget)

        cancel = SecondaryButton("Cancel")
        cancel.clicked.connect(self.reject)
        self.add_button(cancel)

        self._apply_button = PrimaryButton("Apply Credit")
        self._apply_button.setDefault(True)
        self._apply_button.clicked.connect(self._on_apply)
        self.add_button(self._apply_button)

        self._load_tenants()

    def _load_tenants(self) -> None:
        result = self._runner.run(
            lambda s: s.tenant().get_all_tenants(),
            parent=self,
        )
        if result is OPERATION_FAILED:
            return
        self._tenants = result
        self._tenant_combo.clear()
        for tenant in self._tenants:
            self._tenant_combo.addItem(tenant.full_name or "", tenant.id)
        self._on_tenant_changed()

    def _on_tenant_changed(self, *_args) -> None:
        tenant_id = self._tenant_combo.currentData()
        if tenant_id is None:
            self._credit_label.setText("No tenant selected.")
            self._bill_combo.clear()
            self._bills = []
            return

        def _load(services) -> tuple[Any, list[Any]]:
            credit = services.payment().calculate_tenant_credit(tenant_id)
            bills = services.payment().get_allocatable_bills(tenant_id)
            return credit, bills

        result = self._runner.run(_load, parent=self)
        if result is OPERATION_FAILED:
            return
        credit, bills = result
        self._bills = bills
        self._credit_label.setText(f"Available Credit: {format_money(credit)}")
        self._bill_combo.clear()
        for bill in self._bills:
            label = (
                f"{format_date_display(bill.period.start)} to {format_date_display(bill.period.end)} "
                f"— Total: {format_money(bill.total)}"
            )
            self._bill_combo.addItem(label, bill.id)

    def _on_apply(self) -> None:
        self._form_widget.clear_errors()
        tenant_id = self._tenant_combo.currentData()
        bill_id = self._bill_combo.currentData()
        amount_text = self._amount_edit.text().strip()

        valid = True
        if tenant_id is None:
            self._form_widget.set_error("tenant", "A tenant is required.")
            valid = False
        if bill_id is None:
            self._form_widget.set_error("bill", "A bill is required.")
            valid = False
        if not amount_text:
            self._form_widget.set_error("amount", "A credit amount is required.")
            valid = False
        elif not _is_decimal(amount_text):
            self._form_widget.set_error("amount", "Enter a valid amount.")
            valid = False
        if not valid:
            return

        amount = Money(Decimal(amount_text))
        self._result = self._runner.run(
            lambda s: s.payment().apply_tenant_credit(tenant_id, bill_id, amount),
            parent=self,
        )
        if self._result is OPERATION_FAILED:
            return
        self._applied = True
        self.accept()

    def result_allocations(self) -> Any:
        return self._result

    @property
    def applied(self) -> bool:
        return self._applied


class PaymentDetailDialog(BaseDialog):
    """Payment details with allocation information and void where allowed."""

    def __init__(
        self,
        runner: ServiceRunner,
        payment_id: uuid.UUID,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__("Payment Details", parent=parent)
        self._runner = runner
        self._payment_id = payment_id
        self._payment: Any = None

        self._details_label = QLabel("")
        self._details_label.setObjectName("dialogMessage")
        self._details_label.setWordWrap(True)
        self._details_label.setTextInteractionFlags(
            self._details_label.textInteractionFlags() | Qt.TextInteractionFlag.TextSelectableByMouse
        )

        self._allocations_table = DataTableView()
        self._allocations_model = SimpleTableModel(
            ["Bill Period", "Allocated Amount"],
            parent=self._allocations_table,
        )
        self._allocations_table.setModel(self._allocations_model)

        layout = cast(QVBoxLayout, self.layout())
        layout.insertWidget(2, self._details_label)
        layout.insertWidget(3, self._allocations_table)

        self._void_button = SecondaryButton("Void Payment")
        self._void_button.setObjectName("dangerButton")
        self._void_button.clicked.connect(self._on_void)
        self.add_button(self._void_button)

        close = SecondaryButton("Close")
        close.clicked.connect(self.accept)
        self.add_button(close)

        self._load()

    def _load(self) -> None:
        def _load_data(services) -> tuple[Any, str, list[tuple[Any, Any]], Any, Any]:
            payment = services.payment().get_payment(self._payment_id)
            tenant = services.tenant().get_tenant(payment.tenant_id)
            allocations = services.payment().get_allocations_by_payment(payment.id)
            rows: list[tuple[Any, Any]] = []
            for allocation in allocations:
                bill = services.billing().get_bill(allocation.bill_id)
                rows.append((allocation, bill))
            allocated = services.payment().calculate_payment_allocated(payment.id)
            remaining = services.payment().calculate_payment_unused(payment.id)
            return payment, tenant.full_name or "", rows, allocated, remaining

        result = self._runner.run(_load_data, parent=self)
        if result is OPERATION_FAILED:
            self._details_label.setText("Could not load payment details.")
            return
        payment, tenant_name, rows, allocated, remaining = result
        self._payment = payment
        self._render(payment, tenant_name, rows, allocated, remaining)

    def _render(
        self,
        payment: Any,
        tenant_name: str,
        rows: list[tuple[Any, Any]],
        allocated: Any,
        remaining: Any,
    ) -> None:
        lines = [
            f"Tenant: {tenant_name}",
            f"Payment Date: {format_date_display(payment.payment_date)}",
            f"Amount: {format_money(payment.amount)}",
            f"Payment Method: {format_payment_method(payment.payment_method)}",
            f"Status: {format_payment_status(payment.status)}",
            f"Allocated: {format_money(allocated)}",
            f"Remaining / Unallocated: {format_money(remaining)}",
        ]
        if payment.reference:
            lines.append(f"Reference: {payment.reference}")
        if payment.notes:
            lines.append(f"Notes: {payment.notes}")
        lines.append("")
        lines.append("Allocation history:")
        self._details_label.setText("\n".join(lines))

        allocation_rows: list[tuple[str, ...]] = [
            (
                f"{format_date_display(bill.period.start)} to {format_date_display(bill.period.end)}",
                format_money(allocation.allocated_amount),
            )
            for allocation, bill in rows
        ]
        self._allocations_model.set_rows(allocation_rows)
        self._allocations_table.resize_columns_to_contents()
        self._allocations_table.setVisible(bool(allocation_rows))

        self._void_button.setEnabled(payment.status == PaymentStatus.RECORDED)

    def _on_void(self) -> None:
        if self._payment is None or self._payment.status != PaymentStatus.RECORDED:
            return
        confirm = ConfirmationDialog(
            "Void Payment",
            "Void this payment? The payment is marked void and its allocations no "
            "longer count toward bills. The record is kept for history.",
            parent=self,
            confirm_text="Void",
            danger=True,
        )
        if confirm.exec() != QDialog.DialogCode.Accepted or not confirm.confirmed:
            return
        result = self._runner.run(lambda s: s.payment().void_payment(self._payment_id), parent=self)
        if result is OPERATION_FAILED:
            return
        self._load()
