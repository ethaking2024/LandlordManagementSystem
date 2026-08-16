from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QWidget,
)

from app.desktop.billing_forms import BillDetailDialog, GenerateBillDialog, format_bill_status
from app.desktop.components.buttons import PrimaryButton, SecondaryButton
from app.desktop.components.page import Page
from app.desktop.components.table import DataTableView, SimpleTableModel
from app.desktop.components.widgets import EmptyState
from app.desktop.dates import format_date_display
from app.desktop.services import OPERATION_FAILED, ServiceRunner
from app.domain.enums import BillStatus


class BillingPage(Page):
    """Bill list and lifecycle management page.

    Shows all generated bills and lets the user generate a new bill, view bill
    details, confirm a draft, or void a bill. All operations go through
    BillingService via the ServiceRunner; the UI never calculates bill amounts.
    """

    def __init__(
        self,
        runner: ServiceRunner,
        title: str = "Billing",
        subtitle: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(title, subtitle, parent)
        self._runner = runner
        self._bills: list[Any] = []

        toolbar = QHBoxLayout()
        self._generate_button = PrimaryButton("Generate Bill")
        self._generate_button.clicked.connect(self._on_generate)
        self._refresh_button = SecondaryButton("Refresh")
        self._refresh_button.clicked.connect(self.refresh)
        self._view_button = SecondaryButton("Details")
        self._view_button.clicked.connect(self._on_view_bill)
        self._confirm_button = SecondaryButton("Confirm")
        self._confirm_button.clicked.connect(self._on_confirm_bill)
        self._void_button = SecondaryButton("Void")
        self._void_button.setObjectName("dangerButton")
        self._void_button.clicked.connect(self._on_void_bill)
        for button in (
            self._generate_button,
            self._refresh_button,
            self._view_button,
            self._confirm_button,
            self._void_button,
        ):
            toolbar.addWidget(button)
        toolbar.addStretch()
        self.content_layout.addLayout(toolbar)

        self._bill_table = DataTableView()
        self._bill_model = SimpleTableModel(
            ["Bill Period", "Tenant", "Space", "Total", "Status"],
            parent=self._bill_table,
        )
        self._bill_table.setModel(self._bill_model)
        self._bill_table.doubleClicked.connect(self._on_view_bill)
        self.content_layout.addWidget(self._bill_table, stretch=1)

        self._list_empty = EmptyState(
            title="No bills yet",
            message="Generate a bill for an active agreement to start billing.",
        )
        self.content_layout.addWidget(self._list_empty)

    def refresh(self) -> None:
        def _load(services) -> list[tuple[Any, str, str]]:
            bills = services.billing().get_all_bills()
            rows: list[tuple[Any, str, str]] = []
            for bill in bills:
                tenant = services.tenant().get_tenant(bill.tenant_id)
                space = services.rental_space().get_rental_space(bill.rental_space_id)
                rows.append((bill, tenant.full_name or "", space.name or ""))
            return rows

        result = self._runner.run(_load)
        if result is OPERATION_FAILED:
            return
        self._bills = [entry[0] for entry in result]
        self._render_rows(result)

    def _render_rows(self, rows: list[tuple[Any, str, str]]) -> None:
        table_rows: list[tuple[str, ...]] = [
            (
                f"{format_date_display(bill.period.start)} — {format_date_display(bill.period.end)}",
                tenant_name,
                space_name,
                str(bill.total),
                format_bill_status(bill.status),
            )
            for bill, tenant_name, space_name in rows
        ]
        self._bill_model.set_rows(table_rows)
        self._bill_table.resize_columns_to_contents()
        has_rows = bool(table_rows)
        self._bill_table.setVisible(has_rows)
        self._list_empty.setVisible(not has_rows)
        self._view_button.setEnabled(has_rows)
        self._confirm_button.setEnabled(has_rows)
        self._void_button.setEnabled(has_rows)

    def _selected_bill(self) -> Any | None:
        index = self._bill_table.currentIndex()
        row = index.row() if index.isValid() else -1
        if row < 0 or row >= len(self._bills):
            return None
        return self._bills[row]

    def _on_generate(self) -> None:
        dialog = GenerateBillDialog(self._runner, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh()
            bill = dialog.result_bill()
            if bill is not None:
                detail = BillDetailDialog(self._runner, bill.id, parent=self)
                detail.exec()

    def _on_view_bill(self, *_args) -> None:
        bill = self._selected_bill()
        if bill is None:
            return
        dialog = BillDetailDialog(self._runner, bill.id, parent=self)
        dialog.exec()

    def _on_confirm_bill(self) -> None:
        bill = self._selected_bill()
        if bill is None or bill.status != BillStatus.DRAFT:
            return
        dialog = BillDetailDialog(self._runner, bill.id, parent=self)
        dialog.exec()
        self.refresh()

    def _on_void_bill(self) -> None:
        bill = self._selected_bill()
        if bill is None or bill.status == BillStatus.VOID:
            return
        dialog = BillDetailDialog(self._runner, bill.id, parent=self)
        dialog.exec()
        self.refresh()
