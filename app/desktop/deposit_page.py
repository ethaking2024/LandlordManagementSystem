from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QDialog, QHBoxLayout, QWidget

from app.desktop.components.buttons import PrimaryButton, SecondaryButton
from app.desktop.components.page import Page
from app.desktop.components.table import DataTableView, SimpleTableModel
from app.desktop.components.widgets import EmptyState
from app.desktop.dates import format_date_display
from app.desktop.deposit_forms import (
    DepositDetailDialog,
    RecordDepositDialog,
    format_deposit_status,
    format_money,
)
from app.desktop.services import OPERATION_FAILED, ServiceRunner
from app.domain.enums import DepositStatus


class DepositsPage(Page):
    """Deposit list and settlement page.

    Shows all security deposits and lets the user record a deposit, view deposit
    details, settle a held deposit, or void it. All operations go through
    DepositService via the ServiceRunner; the UI never applies settlement rules.
    """

    def __init__(
        self,
        runner: ServiceRunner,
        title: str = "Deposits",
        subtitle: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(title, subtitle, parent)
        self._runner = runner
        self._deposits: list[Any] = []

        toolbar = QHBoxLayout()
        self._record_button = PrimaryButton("Record Deposit")
        self._record_button.clicked.connect(self._on_record)
        self._refresh_button = SecondaryButton("Refresh")
        self._refresh_button.clicked.connect(self.refresh)
        self._view_button = SecondaryButton("Details")
        self._view_button.clicked.connect(self._on_view_deposit)
        self._settle_button = SecondaryButton("Settle")
        self._settle_button.clicked.connect(self._on_settle_deposit)
        self._void_button = SecondaryButton("Void")
        self._void_button.setObjectName("dangerButton")
        self._void_button.clicked.connect(self._on_void_deposit)
        for button in (
            self._record_button,
            self._refresh_button,
            self._view_button,
            self._settle_button,
            self._void_button,
        ):
            toolbar.addWidget(button)
        toolbar.addStretch()
        self.content_layout.addLayout(toolbar)

        self._deposit_table = DataTableView()
        self._deposit_model = SimpleTableModel(
            ["Tenant", "Space", "Amount", "Status", "Agreement"],
            parent=self._deposit_table,
        )
        self._deposit_table.setModel(self._deposit_model)
        self._deposit_table.doubleClicked.connect(self._on_view_deposit)
        self.content_layout.addWidget(self._deposit_table, stretch=1)

        self._list_empty = EmptyState(
            title="No deposits yet",
            message="Record a security deposit for an agreement to start tracking.",
        )
        self.content_layout.addWidget(self._list_empty)

    def refresh(self) -> None:
        def _load(services) -> list[tuple[Any, str, str, str]]:
            deposits = services.deposit().get_all_deposits()
            rows: list[tuple[Any, str, str, str]] = []
            for deposit in deposits:
                tenant = services.tenant().get_tenant(deposit.tenant_id)
                agreement = services.agreement().get_agreement(deposit.agreement_id)
                space = services.rental_space().get_rental_space(agreement.rental_space_id)
                agreement_label = (
                    f"{format_date_display(agreement.start_date)} — "
                    f"{format_date_display(agreement.end_date) if agreement.end_date else 'ongoing'}"
                )
                rows.append((deposit, tenant.full_name or "", space.name or "", agreement_label))
            return rows

        result = self._runner.run(_load)
        if result is OPERATION_FAILED:
            return
        self._deposits = [entry[0] for entry in result]
        self._render_rows(result)

    def _render_rows(self, rows: list[tuple[Any, str, str, str]]) -> None:
        table_rows: list[tuple[str, ...]] = [
            (
                tenant_name,
                space_name,
                format_money(deposit.amount),
                format_deposit_status(deposit.status),
                agreement_label,
            )
            for deposit, tenant_name, space_name, agreement_label in rows
        ]
        self._deposit_model.set_rows(table_rows)
        self._deposit_table.resize_columns_to_contents()
        has_rows = bool(table_rows)
        self._deposit_table.setVisible(has_rows)
        self._list_empty.setVisible(not has_rows)
        self._view_button.setEnabled(has_rows)
        self._settle_button.setEnabled(has_rows)
        self._void_button.setEnabled(has_rows)

    def _selected_deposit(self) -> Any | None:
        index = self._deposit_table.currentIndex()
        row = index.row() if index.isValid() else -1
        if row < 0 or row >= len(self._deposits):
            return None
        return self._deposits[row]

    def _on_record(self) -> None:
        dialog = RecordDepositDialog(self._runner, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def _on_view_deposit(self, *_args) -> None:
        deposit = self._selected_deposit()
        if deposit is None:
            return
        dialog = DepositDetailDialog(self._runner, deposit.id, parent=self)
        dialog.exec()

    def _on_settle_deposit(self) -> None:
        deposit = self._selected_deposit()
        if deposit is None or deposit.status != DepositStatus.HELD:
            return
        dialog = DepositDetailDialog(self._runner, deposit.id, parent=self)
        dialog.exec()
        self.refresh()

    def _on_void_deposit(self) -> None:
        deposit = self._selected_deposit()
        if deposit is None or deposit.status != DepositStatus.HELD:
            return
        dialog = DepositDetailDialog(self._runner, deposit.id, parent=self)
        dialog.exec()
        self.refresh()
