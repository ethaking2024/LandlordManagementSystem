from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QDialog, QHBoxLayout, QWidget

from app.desktop.components.buttons import PrimaryButton, SecondaryButton
from app.desktop.components.page import Page
from app.desktop.components.table import DataTableView, SimpleTableModel
from app.desktop.components.widgets import EmptyState
from app.desktop.dates import format_date_display
from app.desktop.expense_forms import (
    ExpenseDetailDialog,
    ExpenseDialog,
    format_expense_category,
    format_expense_status,
    format_money,
)
from app.desktop.services import OPERATION_FAILED, ServiceRunner
from app.domain.enums import ExpenseStatus


class ExpensesPage(Page):
    """Expense list and lifecycle management page.

    Shows all landlord expenses and lets the user record a new expense, view
    expense details, or void a recorded expense. All operations go through
    ExpenseService via the ServiceRunner; the UI never calculates totals or
    applies validation rules.
    """

    def __init__(
        self,
        runner: ServiceRunner,
        title: str = "Expenses",
        subtitle: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(title, subtitle, parent)
        self._runner = runner
        self._expenses: list[Any] = []

        toolbar = QHBoxLayout()
        self._add_button = PrimaryButton("Add Expense")
        self._add_button.clicked.connect(self._on_add_expense)
        self._refresh_button = SecondaryButton("Refresh")
        self._refresh_button.clicked.connect(self.refresh)
        self._view_button = SecondaryButton("Details")
        self._view_button.clicked.connect(self._on_view_expense)
        self._void_button = SecondaryButton("Void")
        self._void_button.setObjectName("dangerButton")
        self._void_button.clicked.connect(self._on_void_expense)
        for button in (
            self._add_button,
            self._refresh_button,
            self._view_button,
            self._void_button,
        ):
            toolbar.addWidget(button)
        toolbar.addStretch()
        self.content_layout.addLayout(toolbar)

        self._expense_table = DataTableView()
        self._expense_model = SimpleTableModel(
            ["Date", "Property", "Space", "Category", "Amount", "Status"],
            parent=self._expense_table,
        )
        self._expense_table.setModel(self._expense_model)
        self._expense_table.doubleClicked.connect(self._on_view_expense)
        self.content_layout.addWidget(self._expense_table, stretch=1)

        self._list_empty = EmptyState(
            title="No expenses yet",
            message="Add an expense from your properties to start tracking costs.",
        )
        self.content_layout.addWidget(self._list_empty)

    def refresh(self) -> None:
        def _load(services) -> list[tuple[Any, str, str, str]]:
            expenses = services.expense().get_all_expenses()
            rows: list[tuple[Any, str, str, str]] = []
            for expense in expenses:
                property_obj = services.property().get_property(expense.property_id)
                space_name = ""
                if expense.rental_space_id is not None:
                    space = services.rental_space().get_rental_space(expense.rental_space_id)
                    space_name = space.name or ""
                rows.append((expense, property_obj.name or "", space_name, format_expense_category(expense.category)))
            return rows

        result = self._runner.run(_load)
        if result is OPERATION_FAILED:
            return
        self._expenses = [entry[0] for entry in result]
        self._render_rows(result)

    def _render_rows(self, rows: list[tuple[Any, str, str, str]]) -> None:
        table_rows: list[tuple[str, ...]] = [
            (
                format_date_display(expense.expense_date),
                property_name,
                space_name,
                category_label,
                format_money(expense.amount),
                format_expense_status(expense.status),
            )
            for expense, property_name, space_name, category_label in rows
        ]
        self._expense_model.set_rows(table_rows)
        self._expense_table.resize_columns_to_contents()
        has_rows = bool(table_rows)
        self._expense_table.setVisible(has_rows)
        self._list_empty.setVisible(not has_rows)
        self._view_button.setEnabled(has_rows)
        self._void_button.setEnabled(has_rows)

    def _selected_expense(self) -> Any | None:
        index = self._expense_table.currentIndex()
        row = index.row() if index.isValid() else -1
        if row < 0 or row >= len(self._expenses):
            return None
        return self._expenses[row]

    def _on_add_expense(self) -> None:
        dialog = ExpenseDialog(self._runner, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def _on_view_expense(self, *_args) -> None:
        expense = self._selected_expense()
        if expense is None:
            return
        dialog = ExpenseDetailDialog(self._runner, expense.id, parent=self)
        dialog.exec()

    def _on_void_expense(self) -> None:
        expense = self._selected_expense()
        if expense is None or expense.status != ExpenseStatus.RECORDED:
            return
        dialog = ExpenseDetailDialog(self._runner, expense.id, parent=self)
        dialog.exec()
        self.refresh()
