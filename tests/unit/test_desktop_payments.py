from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtWidgets import QDialog

from app.core.exceptions import NotFoundError, ValidationError
from app.desktop.payment_forms import (
    AllocatePaymentDialog,
    ApplyCreditDialog,
    PaymentDetailDialog,
    RecordPaymentDialog,
    format_money,
    format_payment_method,
    format_payment_status,
)
from app.desktop.payment_page import PaymentsPage
from app.desktop.services import OPERATION_FAILED
from app.domain.enums import BillStatus, PaymentMethod, PaymentStatus


class FakeRunner:
    def __init__(self) -> None:
        self.payment = MagicMock()
        self.tenant = MagicMock()
        self.billing = MagicMock()

    def run(self, operation, parent=None):
        services = MagicMock()
        services.payment = MagicMock(return_value=self.payment)
        services.tenant = MagicMock(return_value=self.tenant)
        services.billing = MagicMock(return_value=self.billing)
        try:
            return operation(services)
        except Exception:
            return OPERATION_FAILED


class _Amount:
    def __init__(self, value: str) -> None:
        self.amount = Decimal(value)

    def __str__(self) -> str:
        return str(self.amount)


def make_tenant(tenant_id: uuid.UUID | None = None, name: str = "Sita Shrestha"):
    tenant = MagicMock()
    tenant.id = tenant_id or uuid.uuid4()
    tenant.full_name = name
    return tenant


def make_bill(
    bill_id: uuid.UUID | None = None,
    status: BillStatus = BillStatus.CONFIRMED,
    total: str = "20000",
):
    bill = MagicMock()
    bill.id = bill_id or uuid.uuid4()
    bill.tenant_id = uuid.uuid4()
    bill.period = MagicMock()
    bill.period.start = date(2026, 8, 1)
    bill.period.end = date(2026, 8, 31)
    bill.status = status
    bill.total = _Amount(total)
    return bill


def make_payment(
    payment_id: uuid.UUID | None = None,
    status: PaymentStatus = PaymentStatus.RECORDED,
    amount: str = "25000",
    method: PaymentMethod = PaymentMethod.CASH,
):
    payment = MagicMock()
    payment.id = payment_id or uuid.uuid4()
    payment.tenant_id = uuid.uuid4()
    payment.payment_date = date(2026, 8, 10)
    payment.amount = _Amount(amount)
    payment.payment_method = method
    payment.status = status
    payment.reference = None
    payment.notes = None
    return payment


def make_allocation(bill, amount: str = "8000"):
    allocation = MagicMock()
    allocation.bill_id = bill.id
    allocation.allocated_amount = _Amount(amount)
    return allocation


# ------------------------------------------------------------------
# Formatting helpers
# ------------------------------------------------------------------


@pytest.mark.unit
def test_format_payment_status() -> None:
    assert format_payment_status(PaymentStatus.RECORDED) == "Recorded"
    assert format_payment_status(PaymentStatus.VOID) == "Void"


@pytest.mark.unit
def test_format_payment_method() -> None:
    assert format_payment_method(PaymentMethod.CASH) == "Cash"
    assert format_payment_method(PaymentMethod.BANK_TRANSFER) == "Bank transfer"
    assert format_payment_method(PaymentMethod.ONLINE) == "Online"


@pytest.mark.unit
def test_format_money() -> None:
    assert format_money(_Amount("1000")) == "NPR 1000"
    assert format_money(None) == ""


# ------------------------------------------------------------------
# Record payment dialog
# ------------------------------------------------------------------


@pytest.mark.unit
def test_record_payment_dialog_saves(qapp) -> None:
    runner = FakeRunner()
    tenant = make_tenant()
    payment = make_payment()
    runner.tenant.get_all_tenants.return_value = [tenant]
    runner.payment.record_payment.return_value = payment

    dialog = RecordPaymentDialog(runner)
    dialog._tenant_combo.setCurrentIndex(0)
    dialog._payment_date_input.set_date(date(2026, 8, 10))
    dialog._amount_edit.setText("25000")
    dialog._on_save()

    assert dialog.saved is True
    assert dialog.result_payment() is payment
    call = runner.payment.record_payment.call_args
    assert call.args[0] == tenant.id
    assert call.args[1] == date(2026, 8, 10)
    assert call.args[2].amount == Decimal("25000")
    assert call.args[3] == PaymentMethod.CASH


@pytest.mark.unit
def test_record_payment_dialog_requires_amount(qapp) -> None:
    runner = FakeRunner()
    tenant = make_tenant()
    runner.tenant.get_all_tenants.return_value = [tenant]

    dialog = RecordPaymentDialog(runner)
    dialog._tenant_combo.setCurrentIndex(0)
    dialog._payment_date_input.set_date(date(2026, 8, 10))
    dialog._on_save()

    assert dialog.saved is False
    runner.payment.record_payment.assert_not_called()


@pytest.mark.unit
def test_record_payment_dialog_invalid_amount(qapp) -> None:
    runner = FakeRunner()
    tenant = make_tenant()
    runner.tenant.get_all_tenants.return_value = [tenant]

    dialog = RecordPaymentDialog(runner)
    dialog._tenant_combo.setCurrentIndex(0)
    dialog._payment_date_input.set_date(date(2026, 8, 10))
    dialog._amount_edit.setText("abc")
    dialog._on_save()

    assert dialog.saved is False
    runner.payment.record_payment.assert_not_called()


@pytest.mark.unit
def test_record_payment_dialog_service_error_keeps_open(qapp) -> None:
    runner = FakeRunner()
    tenant = make_tenant()
    runner.tenant.get_all_tenants.return_value = [tenant]
    runner.payment.record_payment.side_effect = ValidationError("payment failed")

    dialog = RecordPaymentDialog(runner)
    dialog._tenant_combo.setCurrentIndex(0)
    dialog._payment_date_input.set_date(date(2026, 8, 10))
    dialog._amount_edit.setText("25000")
    dialog._on_save()

    assert dialog.saved is False


# ------------------------------------------------------------------
# Allocation dialog
# ------------------------------------------------------------------


@pytest.mark.unit
def test_allocate_payment_dialog_allocates(qapp) -> None:
    runner = FakeRunner()
    payment = make_payment()
    bill = make_bill()
    allocation = make_allocation(bill, "8000")
    runner.payment.get_payment.return_value = payment
    runner.payment.get_allocatable_bills.return_value = [bill]
    runner.payment.allocate_payment.return_value = allocation

    dialog = AllocatePaymentDialog(runner, payment.id)
    dialog._bill_combo.setCurrentIndex(0)
    dialog._amount_edit.setText("8000")
    dialog._on_allocate()

    assert dialog.allocated is True
    call = runner.payment.allocate_payment.call_args
    assert call.args[0] == payment.id
    assert call.args[1] == bill.id
    assert call.args[2].amount == Decimal("8000")


@pytest.mark.unit
def test_allocate_payment_dialog_requires_amount(qapp) -> None:
    runner = FakeRunner()
    payment = make_payment()
    bill = make_bill()
    runner.payment.get_payment.return_value = payment
    runner.payment.get_allocatable_bills.return_value = [bill]

    dialog = AllocatePaymentDialog(runner, payment.id)
    dialog._bill_combo.setCurrentIndex(0)
    dialog._on_allocate()

    assert dialog.allocated is False
    runner.payment.allocate_payment.assert_not_called()


@pytest.mark.unit
def test_allocate_payment_dialog_duplicate_rejected(qapp) -> None:
    runner = FakeRunner()
    payment = make_payment()
    bill = make_bill()
    runner.payment.get_payment.return_value = payment
    runner.payment.get_allocatable_bills.return_value = [bill]
    runner.payment.allocate_payment.side_effect = ValidationError("already exists")

    dialog = AllocatePaymentDialog(runner, payment.id)
    dialog._bill_combo.setCurrentIndex(0)
    dialog._amount_edit.setText("8000")
    dialog._on_allocate()

    assert dialog.allocated is False


@pytest.mark.unit
def test_allocate_payment_dialog_over_allocation_rejected(qapp) -> None:
    runner = FakeRunner()
    payment = make_payment()
    bill = make_bill()
    runner.payment.get_payment.return_value = payment
    runner.payment.get_allocatable_bills.return_value = [bill]
    runner.payment.allocate_payment.side_effect = ValidationError("exceeds the bill's outstanding")

    dialog = AllocatePaymentDialog(runner, payment.id)
    dialog._bill_combo.setCurrentIndex(0)
    dialog._amount_edit.setText("99999")
    dialog._on_allocate()

    assert dialog.allocated is False


# ------------------------------------------------------------------
# Credit dialog
# ------------------------------------------------------------------


@pytest.mark.unit
def test_apply_credit_dialog_shows_credit(qapp) -> None:
    runner = FakeRunner()
    tenant = make_tenant(name="Ram Sharma")
    bill = make_bill(total="15000")
    runner.tenant.get_all_tenants.return_value = [tenant]
    runner.payment.calculate_tenant_credit.return_value = _Amount("5000")
    runner.payment.get_allocatable_bills.return_value = [bill]

    dialog = ApplyCreditDialog(runner)

    assert "Available Credit: NPR 5000" in dialog._credit_label.text()
    assert dialog._bill_combo.count() == 1


@pytest.mark.unit
def test_apply_credit_dialog_applies(qapp) -> None:
    runner = FakeRunner()
    tenant = make_tenant()
    bill = make_bill()
    allocation = make_allocation(bill, "5000")
    runner.tenant.get_all_tenants.return_value = [tenant]
    runner.payment.calculate_tenant_credit.return_value = _Amount("5000")
    runner.payment.get_allocatable_bills.return_value = [bill]
    runner.payment.apply_tenant_credit.return_value = [allocation]

    dialog = ApplyCreditDialog(runner)
    dialog._amount_edit.setText("5000")
    dialog._on_apply()

    assert dialog.applied is True
    call = runner.payment.apply_tenant_credit.call_args
    assert call.args[0] == tenant.id
    assert call.args[1] == bill.id
    assert call.args[2].amount == Decimal("5000")


@pytest.mark.unit
def test_apply_credit_dialog_service_error_keeps_open(qapp) -> None:
    runner = FakeRunner()
    tenant = make_tenant()
    bill = make_bill()
    runner.tenant.get_all_tenants.return_value = [tenant]
    runner.payment.calculate_tenant_credit.return_value = _Amount("5000")
    runner.payment.get_allocatable_bills.return_value = [bill]
    runner.payment.apply_tenant_credit.side_effect = ValidationError("Insufficient tenant credit")

    dialog = ApplyCreditDialog(runner)
    dialog._amount_edit.setText("5000")
    dialog._on_apply()

    assert dialog.applied is False


# ------------------------------------------------------------------
# Payment detail dialog
# ------------------------------------------------------------------


@pytest.mark.unit
def test_payment_detail_dialog_renders(qapp) -> None:
    runner = FakeRunner()
    payment = make_payment()
    bill = make_bill()
    allocation = make_allocation(bill, "20000")
    runner.payment.get_payment.return_value = payment
    runner.tenant.get_tenant.return_value = make_tenant()
    runner.payment.get_allocations_by_payment.return_value = [allocation]
    runner.payment.calculate_payment_allocated.return_value = _Amount("20000")
    runner.payment.calculate_payment_unused.return_value = _Amount("5000")
    runner.billing.get_bill.return_value = bill

    dialog = PaymentDetailDialog(runner, payment.id)

    text = dialog._details_label.text()
    assert "Sita Shrestha" in text
    assert "Allocated: NPR 20000" in text
    assert "Remaining / Unallocated: NPR 5000" in text
    assert "Recorded" in text
    assert dialog._allocations_model.rowCount() == 1
    assert dialog._void_button.isEnabled() is True


@pytest.mark.unit
def test_payment_detail_dialog_void_disabled_for_void(qapp) -> None:
    runner = FakeRunner()
    payment = make_payment(status=PaymentStatus.VOID)
    runner.payment.get_payment.return_value = payment
    runner.tenant.get_tenant.return_value = make_tenant()
    runner.payment.get_allocations_by_payment.return_value = []
    runner.payment.calculate_payment_allocated.return_value = _Amount("0")
    runner.payment.calculate_payment_unused.return_value = _Amount("0")

    dialog = PaymentDetailDialog(runner, payment.id)

    assert dialog._void_button.isEnabled() is False


@pytest.mark.unit
def test_payment_detail_dialog_load_error(qapp) -> None:
    runner = FakeRunner()
    runner.payment.get_payment.side_effect = NotFoundError("payment not found")

    dialog = PaymentDetailDialog(runner, uuid.uuid4())

    assert "Could not load payment details" in dialog._details_label.text()


# ------------------------------------------------------------------
# Payments page
# ------------------------------------------------------------------


@pytest.fixture
def page(qapp) -> tuple[PaymentsPage, FakeRunner]:
    runner = FakeRunner()
    payments_page = PaymentsPage(runner)
    payments_page.show()
    return payments_page, runner


@pytest.mark.unit
def test_payments_page_refresh_populates_table(page) -> None:
    payments_page, runner = page
    payment = make_payment()
    runner.payment.get_all_payments.return_value = [payment]
    runner.tenant.get_tenant.return_value = make_tenant()
    runner.payment.calculate_payment_allocated.return_value = _Amount("20000")
    runner.payment.calculate_payment_unused.return_value = _Amount("5000")

    payments_page.refresh()

    assert payments_page._payment_model.rowCount() == 1
    assert "Sita Shrestha" in payments_page._payment_model.data(payments_page._payment_model.index(0, 1))
    assert "NPR 25000" in payments_page._payment_model.data(payments_page._payment_model.index(0, 2))
    assert "Cash" in payments_page._payment_model.data(payments_page._payment_model.index(0, 3))
    assert "Recorded" in payments_page._payment_model.data(payments_page._payment_model.index(0, 4))
    assert "NPR 20000" in payments_page._payment_model.data(payments_page._payment_model.index(0, 5))
    assert "NPR 5000" in payments_page._payment_model.data(payments_page._payment_model.index(0, 6))


@pytest.mark.unit
def test_payments_page_empty_state(page) -> None:
    payments_page, runner = page
    runner.payment.get_all_payments.return_value = []

    payments_page.refresh()

    assert payments_page._payment_model.rowCount() == 0
    assert payments_page._list_empty.isVisible()


@pytest.mark.unit
def test_payments_page_view_payment(page) -> None:
    import app.desktop.payment_page as pp

    payments_page, runner = page
    payment = make_payment()
    runner.payment.get_all_payments.return_value = [payment]
    runner.tenant.get_tenant.return_value = make_tenant()
    runner.payment.calculate_payment_allocated.return_value = _Amount("0")
    runner.payment.calculate_payment_unused.return_value = _Amount("25000")

    payments_page.refresh()
    payments_page._payment_table.selectRow(0)

    fake_detail = MagicMock()
    fake_detail.exec.return_value = QDialog.DialogCode.Accepted
    with patch.object(pp, "PaymentDetailDialog", return_value=fake_detail):
        payments_page._on_view_payment()

    fake_detail.exec.assert_called_once()


@pytest.mark.unit
def test_payments_page_record_workflow(page) -> None:
    import app.desktop.payment_page as pp

    payments_page, runner = page
    runner.payment.get_all_payments.return_value = []

    payments_page.refresh()

    fake_record = MagicMock()
    fake_record.exec.return_value = QDialog.DialogCode.Accepted
    with patch.object(pp, "RecordPaymentDialog", return_value=fake_record):
        payments_page._on_record()

    fake_record.exec.assert_called_once()


@pytest.mark.unit
def test_payments_page_allocate_workflow(page) -> None:
    import app.desktop.payment_page as pp

    payments_page, runner = page
    payment = make_payment()
    runner.payment.get_all_payments.return_value = [payment]
    runner.tenant.get_tenant.return_value = make_tenant()
    runner.payment.calculate_payment_allocated.return_value = _Amount("0")
    runner.payment.calculate_payment_unused.return_value = _Amount("25000")

    payments_page.refresh()
    payments_page._payment_table.selectRow(0)

    fake_allocate = MagicMock()
    fake_allocate.exec.return_value = QDialog.DialogCode.Accepted
    with patch.object(pp, "AllocatePaymentDialog", return_value=fake_allocate):
        payments_page._on_allocate()

    fake_allocate.exec.assert_called_once()


@pytest.mark.unit
def test_payments_page_void_workflow(page) -> None:
    import app.desktop.payment_page as pp

    payments_page, runner = page
    payment = make_payment()
    runner.payment.get_all_payments.return_value = [payment]
    runner.tenant.get_tenant.return_value = make_tenant()
    runner.payment.calculate_payment_allocated.return_value = _Amount("0")
    runner.payment.calculate_payment_unused.return_value = _Amount("25000")

    payments_page.refresh()
    payments_page._payment_table.selectRow(0)

    fake_detail = MagicMock()
    fake_detail.exec.return_value = QDialog.DialogCode.Accepted
    with patch.object(pp, "PaymentDetailDialog", return_value=fake_detail):
        payments_page._on_void_payment()

    fake_detail.exec.assert_called_once()
    payments_page.refresh()  # no crash after mutation


@pytest.mark.unit
def test_payments_page_service_error(page) -> None:
    payments_page, runner = page
    runner.payment.get_all_payments.side_effect = ValidationError("db unavailable")

    payments_page.refresh()

    assert payments_page._payment_model.rowCount() == 0


# ------------------------------------------------------------------
# Integration: bill -> payment -> allocation
# ------------------------------------------------------------------


@pytest.mark.unit
def test_bill_to_payment_to_allocation_workflow(qapp) -> None:
    """A confirmed bill can receive a partial allocation from a recorded payment."""
    runner = FakeRunner()
    tenant = make_tenant()
    bill = make_bill(total="20000")
    payment = make_payment(amount="8000")
    runner.tenant.get_all_tenants.return_value = [tenant]
    runner.payment.get_payment.return_value = payment
    runner.payment.get_allocatable_bills.return_value = [bill]

    record = RecordPaymentDialog(runner)
    record._tenant_combo.setCurrentIndex(0)
    record._payment_date_input.set_date(date(2026, 8, 10))
    record._amount_edit.setText("8000")
    record._on_save()
    assert record.saved is True

    allocate = AllocatePaymentDialog(runner, payment.id)
    allocate._bill_combo.setCurrentIndex(0)
    allocate._amount_edit.setText("8000")
    allocate._on_allocate()
    assert allocate.allocated is True


@pytest.mark.unit
def test_overpayment_leaves_remaining_credit(qapp) -> None:
    """An overpayment shows allocated vs remaining/credit via the service."""
    runner = FakeRunner()
    tenant = make_tenant(name="Ram Sharma")
    bill = make_bill(total="20000")
    payment = make_payment(amount="25000")
    runner.tenant.get_all_tenants.return_value = [tenant]
    runner.tenant.get_tenant.return_value = tenant
    runner.payment.get_payment.return_value = payment
    runner.payment.get_allocatable_bills.return_value = [bill]
    runner.payment.get_allocations_by_payment.return_value = []
    runner.payment.calculate_payment_allocated.return_value = _Amount("20000")
    runner.payment.calculate_payment_unused.return_value = _Amount("5000")

    detail = PaymentDetailDialog(runner, payment.id)

    text = detail._details_label.text()
    assert "Allocated: NPR 20000" in text
    assert "Remaining / Unallocated: NPR 5000" in text
    assert "Ram Sharma" in text
