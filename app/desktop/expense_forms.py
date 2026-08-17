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
from app.desktop.dates import DateInput, format_date_display
from app.desktop.services import OPERATION_FAILED, ServiceRunner
from app.domain.enums import ExpenseCategory, ExpenseStatus
from app.domain.value_objects import Money

_CATEGORY_LABELS: dict[ExpenseCategory, str] = {
    ExpenseCategory.ELECTRICAL: "Electrical",
    ExpenseCategory.PLUMBING: "Plumbing",
    ExpenseCategory.CLEANING: "Cleaning",
    ExpenseCategory.TAX: "Tax",
    ExpenseCategory.COMMON_AREA: "Common area",
    ExpenseCategory.OTHER: "Other",
}


def format_expense_status(status: ExpenseStatus) -> str:
    return status.value.capitalize()


def format_expense_category(category: ExpenseCategory) -> str:
    return _CATEGORY_LABELS.get(category, str(category))


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


class ExpenseDialog(BaseDialog):
    """Record a landlord expense via ExpenseService.

    Property is required; rental space is optional. ExpenseService is the sole
    authority over the space-belonging-to-property rule and all validation; the
    UI never duplicates those rules.
    """

    def __init__(
        self,
        runner: ServiceRunner,
        property_id: uuid.UUID | None = None,
        property_label: str | None = None,
        rental_space_id: uuid.UUID | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__("Add Expense", parent=parent)
        self._runner = runner
        self._properties: list[Any] = []
        self._spaces: list[Any] = []
        self._result: Any = None
        self._saved = False

        self._form_widget = FormWidget()
        self._property_combo = QComboBox()
        self._property_combo.setObjectName("propertyCombo")
        self._property_combo.currentIndexChanged.connect(self._on_property_changed)
        self._space_combo = QComboBox()
        self._space_combo.setObjectName("spaceCombo")
        self._expense_date_input = DateInput()
        self._category_combo = QComboBox()
        self._category_combo.setObjectName("categoryCombo")
        for category in ExpenseCategory:
            self._category_combo.addItem(format_expense_category(category), category)
        self._amount_edit = QLineEdit()
        self._amount_edit.setPlaceholderText("e.g. 3500")
        self._description_edit = QTextEdit()
        self._description_edit.setMaximumHeight(80)
        self._reference_edit = QLineEdit()
        self._reference_edit.setPlaceholderText("e.g. receipt number")

        self._form_widget.add_field("property", "Property", self._property_combo, required=True)
        self._form_widget.add_field("rental_space", "Rental Space (optional)", self._space_combo)
        self._form_widget.add_field("expense_date", "Expense Date", self._expense_date_input, required=True)
        self._form_widget.add_field("category", "Category", self._category_combo, required=True)
        self._form_widget.add_field("amount", "Amount (NPR)", self._amount_edit, required=True)
        self._form_widget.add_field("description", "Description", self._description_edit)
        self._form_widget.add_field("reference", "Reference", self._reference_edit)

        cast(QVBoxLayout, self.layout()).insertWidget(2, self._form_widget)

        cancel = SecondaryButton("Cancel")
        cancel.clicked.connect(self.reject)
        self.add_button(cancel)

        self._save_button = PrimaryButton("Record Expense")
        self._save_button.setDefault(True)
        self._save_button.clicked.connect(self._on_save)
        self.add_button(self._save_button)

        self._load_properties(property_id, property_label, rental_space_id)

    def _load_properties(
        self,
        preselected_property_id: uuid.UUID | None,
        property_label: str | None,
        preselected_space_id: uuid.UUID | None = None,
    ) -> None:
        def _load(services) -> tuple[list[Any], list[tuple[Any, str]]]:
            properties = services.property().get_all_properties()
            space_rows: list[tuple[Any, str]] = []
            if preselected_property_id is not None:
                spaces = services.rental_space().get_rental_spaces_by_property(
                    preselected_property_id, active_only=False
                )
                space_rows = [(space, space.name or "") for space in spaces]
            return properties, space_rows

        result = self._runner.run(_load, parent=self)
        if result is OPERATION_FAILED:
            return
        properties, space_rows = result
        self._properties = properties
        self._property_combo.clear()
        for prop in self._properties:
            self._property_combo.addItem(prop.name or "", prop.id)
        if preselected_property_id is not None:
            index = next(
                (i for i, prop in enumerate(self._properties) if prop.id == preselected_property_id),
                -1,
            )
            if index >= 0:
                self._property_combo.setCurrentIndex(index)
                self._spaces = [entry[0] for entry in space_rows]
                self._space_combo.clear()
                for space, name in space_rows:
                    self._space_combo.addItem(name, space.id)
                if preselected_space_id is not None:
                    space_index = next(
                        (i for i, space in enumerate(self._spaces) if space.id == preselected_space_id),
                        -1,
                    )
                    if space_index >= 0:
                        self._space_combo.setCurrentIndex(space_index)
                return
        if self._properties:
            self._property_combo.setCurrentIndex(0)
        self._on_property_changed()

    def _on_property_changed(self, *_args) -> None:
        property_id = self._property_combo.currentData()
        self._space_combo.clear()
        if property_id is None:
            self._spaces = []
            return

        def _load(services: Any) -> list[Any]:
            return list(services.rental_space().get_rental_spaces_by_property(property_id, active_only=False))

        result = self._runner.run(_load, parent=self)
        if result is OPERATION_FAILED:
            return
        self._spaces = result
        for space in self._spaces:
            self._space_combo.addItem(space.name or "", space.id)

    def _on_save(self) -> None:
        self._form_widget.clear_errors()
        property_id = self._property_combo.currentData()
        space_id = self._space_combo.currentData()
        expense_date = self._expense_date_input.value()
        category = self._category_combo.currentData()
        amount_text = self._amount_edit.text().strip()

        valid = True
        if property_id is None:
            self._form_widget.set_error("property", "A property is required.")
            valid = False
        if not self._expense_date_input.is_valid():
            self._form_widget.set_error("expense_date", "Enter a valid expense date.")
            valid = False
        elif expense_date is None:
            self._form_widget.set_error("expense_date", "An expense date is required.")
            valid = False
        if category is None:
            self._form_widget.set_error("category", "A category is required.")
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
        category_enum = ExpenseCategory(category)
        description = self._description_edit.toPlainText().strip() or None
        reference = self._reference_edit.text().strip() or None
        self._result = self._runner.run(
            lambda s: s.expense().record_expense(
                property_id,
                expense_date,
                category_enum,
                amount,
                description=description,
                rental_space_id=space_id,
                reference=reference,
            ),
            parent=self,
        )
        if self._result is OPERATION_FAILED:
            return
        self._saved = True
        self.accept()

    def result_expense(self) -> Any:
        return self._result

    @property
    def saved(self) -> bool:
        return self._saved


class ExpenseDetailDialog(BaseDialog):
    """Expense details with void where allowed."""

    def __init__(
        self,
        runner: ServiceRunner,
        expense_id: uuid.UUID,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__("Expense Details", parent=parent)
        self._runner = runner
        self._expense_id = expense_id
        self._expense: Any = None

        self._details_label = QLabel("")
        self._details_label.setObjectName("dialogMessage")
        self._details_label.setWordWrap(True)
        self._details_label.setTextInteractionFlags(
            self._details_label.textInteractionFlags() | Qt.TextInteractionFlag.TextSelectableByMouse
        )

        layout = cast(QVBoxLayout, self.layout())
        layout.insertWidget(2, self._details_label)

        self._void_button = SecondaryButton("Void Expense")
        self._void_button.setObjectName("dangerButton")
        self._void_button.clicked.connect(self._on_void)
        self.add_button(self._void_button)

        close = SecondaryButton("Close")
        close.clicked.connect(self.accept)
        self.add_button(close)

        self._load()

    def _load(self) -> None:
        def _load_data(services) -> tuple[Any, str, Any, str | None, Any, str | None]:
            expense = services.expense().get_expense(self._expense_id)
            property_obj = services.property().get_property(expense.property_id)
            space_name: str | None = None
            if expense.rental_space_id is not None:
                space = services.rental_space().get_rental_space(expense.rental_space_id)
                space_name = space.name or ""
            property_total = services.expense().calculate_property_expense_total(expense.property_id)
            space_total = None
            if expense.rental_space_id is not None:
                space_total = services.expense().calculate_rental_space_expense_total(
                    expense.rental_space_id
                )
            return (
                expense,
                property_obj.name or "",
                property_obj,
                space_name,
                property_total,
                space_total,
            )

        result = self._runner.run(_load_data, parent=self)
        if result is OPERATION_FAILED:
            self._details_label.setText("Could not load expense details.")
            return
        expense, property_name, property_obj, space_name, property_total, space_total = result
        self._expense = expense
        self._render(expense, property_name, space_name, property_total, space_total)

    def _render(
        self,
        expense: Any,
        property_name: str,
        space_name: str | None,
        property_total: Any,
        space_total: Any | None,
    ) -> None:
        lines = [
            f"Property: {property_name}",
        ]
        if space_name:
            lines.append(f"Rental Space: {space_name}")
        lines.append(f"Expense Date: {format_date_display(expense.expense_date)}")
        lines.append(f"Category: {format_expense_category(expense.category)}")
        lines.append(f"Amount: {format_money(expense.amount)}")
        if expense.description:
            lines.append(f"Description: {expense.description}")
        if expense.reference:
            lines.append(f"Reference: {expense.reference}")
        lines.append(f"Status: {format_expense_status(expense.status)}")
        lines.append("")
        lines.append(f"Property recorded expense total: {format_money(property_total)}")
        if space_name and space_total is not None:
            lines.append(
                f"Rental-space recorded expense total: {format_money(space_total)}"
            )
        self._details_label.setText("\n".join(lines))

        self._void_button.setEnabled(expense.status == ExpenseStatus.RECORDED)

    def _on_void(self) -> None:
        if self._expense is None or self._expense.status != ExpenseStatus.RECORDED:
            return
        confirm = ConfirmationDialog(
            "Void Expense",
            "Void this expense? The expense is marked void and kept in history. "
            "It no longer counts toward expense totals.",
            parent=self,
            confirm_text="Void",
            danger=True,
        )
        if confirm.exec() != QDialog.DialogCode.Accepted or not confirm.confirmed:
            return
        result = self._runner.run(lambda s: s.expense().void_expense(self._expense_id), parent=self)
        if result is OPERATION_FAILED:
            return
        self._load()
