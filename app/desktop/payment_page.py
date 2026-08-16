from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QDialog, QHBoxLayout, QWidget

from app.desktop.components.buttons import PrimaryButton, SecondaryButton
from app.desktop.components.page import Page
from app.desktop.components.table import DataTableView, SimpleTableModel
from app.desktop.components.widgets import EmptyState
from app.desktop.dates import format_date_display
from app.desktop.payment_forms import (
    AllocatePaymentDialog,
    ApplyCreditDialog,
    PaymentDetailDialog,
    RecordPaymentDialog,
    format_money,
    format_payment_method,
    format_payment_status,
)
from app.desktop.services import OPERATION_FAILED, ServiceRunner
from app.domain.enums import PaymentStatus


class PaymentsPage(Page):
    """Payment list and lifecycle management page.

    Shows all recorded payments and lets the user record a new payment, allocate
    a payment to a bill, apply tenant credit, view payment details, or void a
    payment. All operations go through PaymentService via the ServiceRunner; the
    UI never calculates balances or allocations.
    """

    def __init__(
        self,
        runner: ServiceRunner,
        title: str = "Payments",
        subtitle: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(title, subtitle, parent)
        self._runner = runner
        self._payments: list[Any] = []

        toolbar = QHBoxLayout()
        self._record_button = PrimaryButton("Record Payment")
        self._record_button.clicked.connect(self._on_record)
        self._allocate_button = SecondaryButton("Allocate")
        self._allocate_button.clicked.connect(self._on_allocate)
        self._credit_button = SecondaryButton("Apply Credit")
        self._credit_button.clicked.connect(self._on_apply_credit)
        self._refresh_button = SecondaryButton("Refresh")
        self._refresh_button.clicked.connect(self.refresh)
        self._view_button = SecondaryButton("Details")
        self._view_button.clicked.connect(self._on_view_payment)
        self._void_button = SecondaryButton("Void")
        self._void_button.setObjectName("dangerButton")
        self._void_button.clicked.connect(self._on_void_payment)
        for button in (
            self._record_button,
            self._allocate_button,
            self._credit_button,
            self._refresh_button,
            self._view_button,
            self._void_button,
        ):
            toolbar.addWidget(button)
        toolbar.addStretch()
        self.content_layout.addLayout(toolbar)

        self._payment_table = DataTableView()
        self._payment_model = SimpleTableModel(
            ["Date", "Tenant", "Amount", "Payment Method", "Status", "Allocated", "Remaining"],
            parent=self._payment_table,
        )
        self._payment_table.setModel(self._payment_model)
        self._payment_table.doubleClicked.connect(self._on_view_payment)
        self.content_layout.addWidget(self._payment_table, stretch=1)

        self._list_empty = EmptyState(
            title="No payments yet",
            message="Record a payment from a tenant to start tracking payments.",
        )
        self.content_layout.addWidget(self._list_empty)

    def refresh(self) -> None:
        def _load(services) -> list[tuple[Any, str, Any, Any]]:
            payments = services.payment().get_all_payments()
            rows: list[tuple[Any, str, Any, Any]] = []
            for payment in payments:
                tenant = services.tenant().get_tenant(payment.tenant_id)
                allocated = services.payment().calculate_payment_allocated(payment.id)
                remaining = services.payment().calculate_payment_unused(payment.id)
                rows.append((payment, tenant.full_name or "", allocated, remaining))
            return rows

        result = self._runner.run(_load)
        if result is OPERATION_FAILED:
            return
        self._payments = [entry[0] for entry in result]
        self._render_rows(result)

    def _render_rows(self, rows: list[tuple[Any, str, Any, Any]]) -> None:
        table_rows: list[tuple[str, ...]] = [
            (
                format_date_display(payment.payment_date),
                tenant_name,
                format_money(payment.amount),
                format_payment_method(payment.payment_method),
                format_payment_status(payment.status),
                format_money(allocated),
                format_money(remaining),
            )
            for payment, tenant_name, allocated, remaining in rows
        ]
        self._payment_model.set_rows(table_rows)
        self._payment_table.resize_columns_to_contents()
        has_rows = bool(table_rows)
        self._payment_table.setVisible(has_rows)
        self._list_empty.setVisible(not has_rows)
        self._allocate_button.setEnabled(has_rows)
        self._view_button.setEnabled(has_rows)
        self._void_button.setEnabled(has_rows)

    def _selected_payment(self) -> Any | None:
        index = self._payment_table.currentIndex()
        row = index.row() if index.isValid() else -1
        if row < 0 or row >= len(self._payments):
            return None
        return self._payments[row]

    def _on_record(self) -> None:
        dialog = RecordPaymentDialog(self._runner, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def _on_allocate(self) -> None:
        payment = self._selected_payment()
        if payment is None or payment.status != PaymentStatus.RECORDED:
            return
        dialog = AllocatePaymentDialog(self._runner, payment.id, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def _on_apply_credit(self) -> None:
        dialog = ApplyCreditDialog(self._runner, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def _on_view_payment(self, *_args) -> None:
        payment = self._selected_payment()
        if payment is None:
            return
        dialog = PaymentDetailDialog(self._runner, payment.id, parent=self)
        dialog.exec()

    def _on_void_payment(self) -> None:
        payment = self._selected_payment()
        if payment is None or payment.status != PaymentStatus.RECORDED:
            return
        dialog = PaymentDetailDialog(self._runner, payment.id, parent=self)
        dialog.exec()
        self.refresh()
