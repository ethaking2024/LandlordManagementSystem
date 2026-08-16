from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtWidgets import QDialog

from app.core.exceptions import NotFoundError, ValidationError
from app.desktop.expense_forms import (
    ExpenseDetailDialog,
    ExpenseDialog,
    format_expense_category,
    format_expense_status,
    format_money,
)
from app.desktop.expense_page import ExpensesPage
from app.desktop.services import OPERATION_FAILED
from app.domain.enums import ExpenseCategory, ExpenseStatus


class FakeRunner:
    def __init__(self) -> None:
        self.expense = MagicMock()
        self.property = MagicMock()
        self.rental_space = MagicMock()

    def run(self, operation, parent=None):
        services = MagicMock()
        services.expense = MagicMock(return_value=self.expense)
        services.property = MagicMock(return_value=self.property)
        services.rental_space = MagicMock(return_value=self.rental_space)
        try:
            return operation(services)
        except Exception:
            return OPERATION_FAILED


class _Amount:
    def __init__(self, value: str) -> None:
        self.amount = Decimal(value)

    def __str__(self) -> str:
        return str(self.amount)


def make_property(property_id: uuid.UUID | None = None, name: str = "Main Building"):
    prop = MagicMock()
    prop.id = property_id or uuid.uuid4()
    prop.name = name
    return prop


def make_space(
    space_id: uuid.UUID | None = None,
    property_id: uuid.UUID | None = None,
    name: str = "Room 101",
):
    space = MagicMock()
    space.id = space_id or uuid.uuid4()
    space.property_id = property_id or uuid.uuid4()
    space.name = name
    return space


def make_expense(
    expense_id: uuid.UUID | None = None,
    property_id: uuid.UUID | None = None,
    rental_space_id: uuid.UUID | None = None,
    status: ExpenseStatus = ExpenseStatus.RECORDED,
    amount: str = "3500",
    category: ExpenseCategory = ExpenseCategory.PLUMBING,
    expense_date: date = date(2026, 3, 10),
    description: str | None = None,
    reference: str | None = None,
):
    expense = MagicMock()
    expense.id = expense_id or uuid.uuid4()
    expense.property_id = property_id or uuid.uuid4()
    expense.rental_space_id = rental_space_id
    expense.expense_date = expense_date
    expense.category = category
    expense.amount = _Amount(amount)
    expense.description = description
    expense.reference = reference
    expense.status = status
    return expense


# ------------------------------------------------------------------
# Formatting helpers
# ------------------------------------------------------------------


@pytest.mark.unit
def test_format_expense_status() -> None:
    assert format_expense_status(ExpenseStatus.RECORDED) == "Recorded"
    assert format_expense_status(ExpenseStatus.VOID) == "Void"


@pytest.mark.unit
def test_format_expense_category() -> None:
    assert format_expense_category(ExpenseCategory.ELECTRICAL) == "Electrical"
    assert format_expense_category(ExpenseCategory.COMMON_AREA) == "Common area"
    assert format_expense_category(ExpenseCategory.OTHER) == "Other"


@pytest.mark.unit
def test_format_money() -> None:
    assert format_money(_Amount("3500")) == "NPR 3500"
    assert format_money(None) == ""


# ------------------------------------------------------------------
# Add Expense dialog
# ------------------------------------------------------------------


@pytest.mark.unit
def test_expense_dialog_saves_valid_expense(qapp) -> None:
    runner = FakeRunner()
    prop = make_property()
    expense = make_expense(property_id=prop.id)
    runner.property.get_all_properties.return_value = [prop]
    runner.expense.record_expense.return_value = expense

    dialog = ExpenseDialog(runner)
    dialog._property_combo.setCurrentIndex(0)
    dialog._expense_date_input.set_date(date(2026, 3, 10))
    dialog._category_combo.setCurrentIndex(0)
    dialog._amount_edit.setText("3500")
    dialog._on_save()

    assert dialog.saved is True
    assert dialog.result_expense() is expense
    call = runner.expense.record_expense.call_args
    assert call.args[0] == prop.id
    assert call.args[1] == date(2026, 3, 10)
    assert call.args[2] == ExpenseCategory.ELECTRICAL
    assert call.args[3].amount == Decimal("3500")
    assert call.kwargs["rental_space_id"] is None


@pytest.mark.unit
def test_expense_dialog_requires_property(qapp) -> None:
    runner = FakeRunner()
    runner.property.get_all_properties.return_value = []

    dialog = ExpenseDialog(runner)
    dialog._expense_date_input.set_date(date(2026, 3, 10))
    dialog._amount_edit.setText("3500")
    dialog._on_save()

    assert dialog.saved is False
    runner.expense.record_expense.assert_not_called()


@pytest.mark.unit
def test_expense_dialog_requires_amount(qapp) -> None:
    runner = FakeRunner()
    prop = make_property()
    runner.property.get_all_properties.return_value = [prop]

    dialog = ExpenseDialog(runner)
    dialog._property_combo.setCurrentIndex(0)
    dialog._expense_date_input.set_date(date(2026, 3, 10))
    dialog._on_save()

    assert dialog.saved is False
    runner.expense.record_expense.assert_not_called()


@pytest.mark.unit
def test_expense_dialog_invalid_amount(qapp) -> None:
    runner = FakeRunner()
    prop = make_property()
    runner.property.get_all_properties.return_value = [prop]

    dialog = ExpenseDialog(runner)
    dialog._property_combo.setCurrentIndex(0)
    dialog._expense_date_input.set_date(date(2026, 3, 10))
    dialog._amount_edit.setText("abc")
    dialog._on_save()

    assert dialog.saved is False
    runner.expense.record_expense.assert_not_called()


@pytest.mark.unit
def test_expense_dialog_requires_date(qapp) -> None:
    runner = FakeRunner()
    prop = make_property()
    runner.property.get_all_properties.return_value = [prop]

    dialog = ExpenseDialog(runner)
    dialog._property_combo.setCurrentIndex(0)
    dialog._amount_edit.setText("3500")
    dialog._on_save()

    assert dialog.saved is False
    runner.expense.record_expense.assert_not_called()


@pytest.mark.unit
def test_expense_dialog_requires_category(qapp) -> None:
    runner = FakeRunner()
    prop = make_property()
    runner.property.get_all_properties.return_value = [prop]

    dialog = ExpenseDialog(runner)
    dialog._property_combo.setCurrentIndex(0)
    dialog._expense_date_input.set_date(date(2026, 3, 10))
    dialog._category_combo.setCurrentIndex(-1)
    dialog._amount_edit.setText("3500")
    dialog._on_save()

    assert dialog.saved is False
    runner.expense.record_expense.assert_not_called()


@pytest.mark.unit
def test_expense_dialog_property_selection_loads_spaces(qapp) -> None:
    runner = FakeRunner()
    prop = make_property()
    space = make_space(property_id=prop.id, name="Room 5")
    runner.property.get_all_properties.return_value = [prop]
    runner.rental_space.get_rental_spaces_by_property.return_value = [space]

    dialog = ExpenseDialog(runner)
    dialog._property_combo.setCurrentIndex(0)

    assert dialog._space_combo.count() == 1
    assert dialog._space_combo.itemText(0) == "Room 5"


@pytest.mark.unit
def test_expense_dialog_optional_rental_space(qapp) -> None:
    runner = FakeRunner()
    prop = make_property()
    space = make_space(property_id=prop.id, name="Room 5")
    expense = make_expense(property_id=prop.id, rental_space_id=space.id)
    runner.property.get_all_properties.return_value = [prop]
    runner.rental_space.get_rental_spaces_by_property.return_value = [space]
    runner.expense.record_expense.return_value = expense

    dialog = ExpenseDialog(runner)
    dialog._property_combo.setCurrentIndex(0)
    dialog._space_combo.setCurrentIndex(0)
    dialog._expense_date_input.set_date(date(2026, 3, 10))
    dialog._amount_edit.setText("3500")
    dialog._on_save()

    assert dialog.saved is True
    call = runner.expense.record_expense.call_args
    assert call.kwargs["rental_space_id"] == space.id


@pytest.mark.unit
def test_expense_dialog_invalid_property_space_combo_service_error(qapp) -> None:
    runner = FakeRunner()
    prop = make_property()
    space = make_space(property_id=uuid.uuid4(), name="Wrong property")
    runner.property.get_all_properties.return_value = [prop]
    runner.rental_space.get_rental_spaces_by_property.return_value = [space]
    runner.expense.record_expense.side_effect = ValidationError(
        "Rental space does not belong to property"
    )

    dialog = ExpenseDialog(runner)
    dialog._property_combo.setCurrentIndex(0)
    dialog._expense_date_input.set_date(date(2026, 3, 10))
    dialog._amount_edit.setText("3500")
    dialog._on_save()

    assert dialog.saved is False


@pytest.mark.unit
def test_expense_dialog_service_error_keeps_open(qapp) -> None:
    runner = FakeRunner()
    prop = make_property()
    runner.property.get_all_properties.return_value = [prop]
    runner.expense.record_expense.side_effect = ValidationError("expense amount must be greater than zero")

    dialog = ExpenseDialog(runner)
    dialog._property_combo.setCurrentIndex(0)
    dialog._expense_date_input.set_date(date(2026, 3, 10))
    dialog._amount_edit.setText("0")
    dialog._on_save()

    assert dialog.saved is False


@pytest.mark.unit
def test_expense_dialog_preselects_property_and_space(qapp) -> None:
    runner = FakeRunner()
    prop = make_property()
    space = make_space(property_id=prop.id, name="Room 7")
    runner.property.get_all_properties.return_value = [prop]
    runner.rental_space.get_rental_spaces_by_property.return_value = [space]

    dialog = ExpenseDialog(runner, property_id=prop.id, rental_space_id=space.id)

    assert dialog._property_combo.currentData() == prop.id
    assert dialog._space_combo.currentData() == space.id


# ------------------------------------------------------------------
# Expense detail dialog
# ------------------------------------------------------------------


@pytest.mark.unit
def test_expense_detail_dialog_renders(qapp) -> None:
    runner = FakeRunner()
    prop = make_property(name="Main Building")
    space = make_space(property_id=prop.id, name="Room 101")
    expense = make_expense(
        property_id=prop.id,
        rental_space_id=space.id,
        description="Fixed leak",
        reference="REC-1",
    )
    runner.expense.get_expense.return_value = expense
    runner.property.get_property.return_value = prop
    runner.rental_space.get_rental_space.return_value = space
    runner.expense.calculate_property_expense_total.return_value = _Amount("13500")
    runner.expense.calculate_rental_space_expense_total.return_value = _Amount("3500")

    dialog = ExpenseDetailDialog(runner, expense.id)

    text = dialog._details_label.text()
    assert "Main Building" in text
    assert "Room 101" in text
    assert "2026-03-10" in text
    assert "Plumbing" in text
    assert "NPR 3500" in text
    assert "Fixed leak" in text
    assert "REC-1" in text
    assert "Recorded" in text
    assert "Property recorded expense total: NPR 13500" in text
    assert "Rental-space recorded expense total: NPR 3500" in text
    assert dialog._void_button.isEnabled() is True


@pytest.mark.unit
def test_expense_detail_dialog_void_disabled_for_void(qapp) -> None:
    runner = FakeRunner()
    prop = make_property()
    expense = make_expense(property_id=prop.id, status=ExpenseStatus.VOID)
    runner.expense.get_expense.return_value = expense
    runner.property.get_property.return_value = prop
    runner.expense.calculate_property_expense_total.return_value = _Amount("0")

    dialog = ExpenseDetailDialog(runner, expense.id)

    assert dialog._void_button.isEnabled() is False


@pytest.mark.unit
def test_expense_detail_dialog_property_total_only(qapp) -> None:
    runner = FakeRunner()
    prop = make_property()
    expense = make_expense(property_id=prop.id, rental_space_id=None)
    runner.expense.get_expense.return_value = expense
    runner.property.get_property.return_value = prop
    runner.expense.calculate_property_expense_total.return_value = _Amount("3500")

    dialog = ExpenseDetailDialog(runner, expense.id)

    text = dialog._details_label.text()
    assert "Property recorded expense total: NPR 3500" in text
    assert "Rental-space recorded expense total" not in text


@pytest.mark.unit
def test_expense_detail_dialog_load_error(qapp) -> None:
    runner = FakeRunner()
    runner.expense.get_expense.side_effect = NotFoundError("expense not found")

    dialog = ExpenseDetailDialog(runner, uuid.uuid4())

    assert "Could not load expense details" in dialog._details_label.text()


@pytest.mark.unit
def test_expense_detail_dialog_void_updates(qapp) -> None:
    import app.desktop.expense_forms as ef

    runner = FakeRunner()
    prop = make_property()
    expense = make_expense(property_id=prop.id)
    voided = make_expense(property_id=prop.id, status=ExpenseStatus.VOID)
    runner.expense.get_expense.side_effect = [expense, voided]
    runner.property.get_property.return_value = prop
    runner.expense.calculate_property_expense_total.return_value = _Amount("0")

    dialog = ExpenseDetailDialog(runner, expense.id)

    confirm = MagicMock()
    confirm.exec.return_value = QDialog.DialogCode.Accepted
    confirm.confirmed = True
    runner.expense.void_expense.return_value = voided
    with patch.object(ef, "ConfirmationDialog", return_value=confirm):
        dialog._on_void()

    runner.expense.void_expense.assert_called_once_with(expense.id)


@pytest.mark.unit
def test_expense_detail_dialog_void_cancelled(qapp) -> None:
    import app.desktop.expense_forms as ef

    runner = FakeRunner()
    prop = make_property()
    expense = make_expense(property_id=prop.id)
    runner.expense.get_expense.return_value = expense
    runner.property.get_property.return_value = prop
    runner.expense.calculate_property_expense_total.return_value = _Amount("3500")

    dialog = ExpenseDetailDialog(runner, expense.id)

    confirm = MagicMock()
    confirm.exec.return_value = QDialog.DialogCode.Rejected
    confirm.confirmed = False
    with patch.object(ef, "ConfirmationDialog", return_value=confirm):
        dialog._on_void()

    runner.expense.void_expense.assert_not_called()


# ------------------------------------------------------------------
# Expenses page
# ------------------------------------------------------------------


@pytest.fixture
def page(qapp) -> tuple[ExpensesPage, FakeRunner]:
    runner = FakeRunner()
    expenses_page = ExpensesPage(runner)
    expenses_page.show()
    return expenses_page, runner


@pytest.mark.unit
def test_expenses_page_refresh_populates_table(page) -> None:
    expenses_page, runner = page
    prop = make_property(name="Main Building")
    space = make_space(property_id=prop.id, name="Room 101")
    expense = make_expense(property_id=prop.id, rental_space_id=space.id)
    runner.expense.get_all_expenses.return_value = [expense]
    runner.property.get_property.return_value = prop
    runner.rental_space.get_rental_space.return_value = space

    expenses_page.refresh()

    assert expenses_page._expense_model.rowCount() == 1
    assert "Main Building" in expenses_page._expense_model.data(expenses_page._expense_model.index(0, 1))
    assert "Room 101" in expenses_page._expense_model.data(expenses_page._expense_model.index(0, 2))
    assert "Plumbing" in expenses_page._expense_model.data(expenses_page._expense_model.index(0, 3))
    assert "NPR 3500" in expenses_page._expense_model.data(expenses_page._expense_model.index(0, 4))
    assert "Recorded" in expenses_page._expense_model.data(expenses_page._expense_model.index(0, 5))


@pytest.mark.unit
def test_expenses_page_empty_state(page) -> None:
    expenses_page, runner = page
    runner.expense.get_all_expenses.return_value = []

    expenses_page.refresh()

    assert expenses_page._expense_model.rowCount() == 0
    assert expenses_page._list_empty.isVisible()


@pytest.mark.unit
def test_expenses_page_add_workflow(page) -> None:
    import app.desktop.expense_page as ep

    expenses_page, runner = page
    runner.expense.get_all_expenses.return_value = []
    expenses_page.refresh()

    fake_dialog = MagicMock()
    fake_dialog.exec.return_value = QDialog.DialogCode.Accepted
    with patch.object(ep, "ExpenseDialog", return_value=fake_dialog):
        expenses_page._on_add_expense()

    fake_dialog.exec.assert_called_once()


@pytest.mark.unit
def test_expenses_page_view_workflow(page) -> None:
    import app.desktop.expense_page as ep

    expenses_page, runner = page
    prop = make_property()
    expense = make_expense(property_id=prop.id)
    runner.expense.get_all_expenses.return_value = [expense]
    runner.property.get_property.return_value = prop
    expenses_page.refresh()
    expenses_page._expense_table.selectRow(0)

    fake_detail = MagicMock()
    fake_detail.exec.return_value = QDialog.DialogCode.Accepted
    with patch.object(ep, "ExpenseDetailDialog", return_value=fake_detail):
        expenses_page._on_view_expense()

    fake_detail.exec.assert_called_once()


@pytest.mark.unit
def test_expenses_page_void_workflow(page) -> None:
    import app.desktop.expense_page as ep

    expenses_page, runner = page
    prop = make_property()
    expense = make_expense(property_id=prop.id)
    runner.expense.get_all_expenses.return_value = [expense]
    runner.property.get_property.return_value = prop
    expenses_page.refresh()
    expenses_page._expense_table.selectRow(0)

    fake_detail = MagicMock()
    fake_detail.exec.return_value = QDialog.DialogCode.Accepted
    with patch.object(ep, "ExpenseDetailDialog", return_value=fake_detail):
        expenses_page._on_void_expense()

    fake_detail.exec.assert_called_once()
    expenses_page.refresh()


@pytest.mark.unit
def test_expenses_page_service_error(page) -> None:
    expenses_page, runner = page
    runner.expense.get_all_expenses.side_effect = ValidationError("db unavailable")

    expenses_page.refresh()

    assert expenses_page._expense_model.rowCount() == 0


# ------------------------------------------------------------------
# Integration: record -> detail -> void stays historical
# ------------------------------------------------------------------


@pytest.mark.unit
def test_record_then_detail_then_void_keeps_history(qapp) -> None:
    """A recorded expense can be voided; the record remains in history."""
    runner = FakeRunner()
    prop = make_property()
    expense = make_expense(property_id=prop.id)
    voided = make_expense(property_id=prop.id, status=ExpenseStatus.VOID)
    runner.property.get_all_properties.return_value = [prop]
    runner.expense.record_expense.return_value = expense
    runner.expense.get_expense.side_effect = [expense, voided]
    runner.property.get_property.return_value = prop
    runner.expense.calculate_property_expense_total.return_value = _Amount("0")

    record = ExpenseDialog(runner)
    record._property_combo.setCurrentIndex(0)
    record._expense_date_input.set_date(date(2026, 3, 10))
    record._amount_edit.setText("3500")
    record._on_save()
    assert record.saved is True

    detail = ExpenseDetailDialog(runner, expense.id)
    assert detail._void_button.isEnabled() is True

    import app.desktop.expense_forms as ef

    confirm = MagicMock()
    confirm.exec.return_value = QDialog.DialogCode.Accepted
    confirm.confirmed = True
    runner.expense.void_expense.return_value = voided
    with patch.object(ef, "ConfirmationDialog", return_value=confirm):
        detail._on_void()

    runner.expense.void_expense.assert_called_once_with(expense.id)
    assert detail._void_button.isEnabled() is False


@pytest.mark.unit
def test_expense_ad_bs_display(qapp) -> None:
    runner = FakeRunner()
    prop = make_property()
    expense = make_expense(property_id=prop.id, expense_date=date(2026, 3, 10))
    runner.expense.get_expense.return_value = expense
    runner.property.get_property.return_value = prop
    runner.expense.calculate_property_expense_total.return_value = _Amount("3500")

    dialog = ExpenseDetailDialog(runner, expense.id)

    text = dialog._details_label.text()
    assert "2026-03-10" in text
    # BS conversion is included by format_date_display
    assert "2082" in text
