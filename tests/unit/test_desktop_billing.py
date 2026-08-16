from __future__ import annotations

import uuid
from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtWidgets import QDialog

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.desktop.billing_forms import (
    BillDetailDialog,
    GenerateBillDialog,
    format_bill_status,
    format_money,
)
from app.desktop.billing_page import BillingPage
from app.desktop.services import OPERATION_FAILED
from app.domain.enums import BillCategory, BillStatus


class FakeRunner:
    def __init__(self) -> None:
        self.billing = MagicMock()
        self.tenant = MagicMock()
        self.rental_space = MagicMock()
        self.agreement = MagicMock()

    def run(self, operation, parent=None):
        services = MagicMock()
        services.billing = MagicMock(return_value=self.billing)
        services.tenant = MagicMock(return_value=self.tenant)
        services.rental_space = MagicMock(return_value=self.rental_space)
        services.agreement = MagicMock(return_value=self.agreement)
        try:
            return operation(services)
        except Exception:
            return OPERATION_FAILED


def make_tenant(tenant_id: uuid.UUID | None = None, name: str = "Sita Shrestha"):
    tenant = MagicMock()
    tenant.id = tenant_id or uuid.uuid4()
    tenant.full_name = name
    return tenant


def make_space(space_id: uuid.UUID | None = None, name: str = "Flat A"):
    space = MagicMock()
    space.id = space_id or uuid.uuid4()
    space.name = name
    return space


def make_agreement(agreement_id: uuid.UUID | None = None):
    agreement = MagicMock()
    agreement.id = agreement_id or uuid.uuid4()
    agreement.tenant_id = uuid.uuid4()
    agreement.rental_space_id = uuid.uuid4()
    return agreement


class _Amount:
    def __init__(self, value: str) -> None:
        self.amount = value

    def __str__(self) -> str:
        return str(self.amount)


def make_line(category: BillCategory, amount: str):
    line = MagicMock()
    line.category = category
    line.description = ""
    line.amount = _Amount(amount)
    return line


def make_bill(
    bill_id: uuid.UUID | None = None,
    status: BillStatus = BillStatus.DRAFT,
    lines: list | None = None,
):
    bill = MagicMock()
    bill.id = bill_id or uuid.uuid4()
    bill.agreement_id = uuid.uuid4()
    bill.tenant_id = uuid.uuid4()
    bill.rental_space_id = uuid.uuid4()
    bill.period = MagicMock()
    bill.period.start = date(2026, 8, 1)
    bill.period.end = date(2026, 8, 31)
    bill.billing_date = date(2026, 8, 31)
    bill.status = status
    bill.notes = None
    bill.lines = lines or [
        make_line(BillCategory.RENT, "15000"),
        make_line(BillCategory.ELECTRICITY, "1000"),
        make_line(BillCategory.WATER, "500"),
    ]
    bill.total = _Amount("16500")
    return bill


# ------------------------------------------------------------------
# Formatting helpers
# ------------------------------------------------------------------


@pytest.mark.unit
def test_format_bill_status() -> None:
    assert format_bill_status(BillStatus.DRAFT) == "Draft"
    assert format_bill_status(BillStatus.CONFIRMED) == "Confirmed"
    assert format_bill_status(BillStatus.VOID) == "Void"


@pytest.mark.unit
def test_format_money() -> None:
    assert format_money(_Amount("1000")) == "NPR 1000"
    assert format_money(None) == ""


# ------------------------------------------------------------------
# Generate bill dialog
# ------------------------------------------------------------------


@pytest.mark.unit
def test_generate_bill_dialog_creates_bill(qapp) -> None:
    runner = FakeRunner()
    agreement = make_agreement()
    tenant = make_tenant()
    space = make_space()
    bill = make_bill()
    runner.agreement.get_all_agreements.return_value = [agreement]
    runner.tenant.get_tenant.return_value = tenant
    runner.rental_space.get_rental_space.return_value = space
    runner.billing.generate_bill.return_value = bill

    dialog = GenerateBillDialog(runner)
    dialog._agreement_combo.setCurrentIndex(0)
    dialog._period_start_input.set_date(date(2026, 8, 1))
    dialog._period_end_input.set_date(date(2026, 8, 31))
    dialog._on_generate()

    assert dialog.generated is True
    assert dialog.result_bill() is bill
    runner.billing.generate_bill.assert_called_once()
    call = runner.billing.generate_bill.call_args
    assert call.args[0] == agreement.id
    assert call.args[1] == date(2026, 8, 1)
    assert call.args[2] == date(2026, 8, 31)


@pytest.mark.unit
def test_generate_bill_dialog_requires_period(qapp) -> None:
    runner = FakeRunner()
    agreement = make_agreement()
    tenant = make_tenant()
    space = make_space()
    runner.agreement.get_all_agreements.return_value = [agreement]
    runner.tenant.get_tenant.return_value = tenant
    runner.rental_space.get_rental_space.return_value = space

    dialog = GenerateBillDialog(runner)
    dialog._agreement_combo.setCurrentIndex(0)
    dialog._on_generate()

    assert dialog.generated is False
    runner.billing.generate_bill.assert_not_called()


@pytest.mark.unit
def test_generate_bill_dialog_service_error_keeps_open(qapp) -> None:
    runner = FakeRunner()
    agreement = make_agreement()
    tenant = make_tenant()
    space = make_space()
    runner.agreement.get_all_agreements.return_value = [agreement]
    runner.tenant.get_tenant.return_value = tenant
    runner.rental_space.get_rental_space.return_value = space
    runner.billing.generate_bill.side_effect = ConflictError("bill already exists")

    dialog = GenerateBillDialog(runner)
    dialog._agreement_combo.setCurrentIndex(0)
    dialog._period_start_input.set_date(date(2026, 8, 1))
    dialog._period_end_input.set_date(date(2026, 8, 31))
    dialog._on_generate()

    assert dialog.generated is False


@pytest.mark.unit
def test_generate_bill_dialog_preview_shows_lines(qapp) -> None:
    runner = FakeRunner()
    agreement = make_agreement()
    tenant = make_tenant()
    space = make_space()
    bill = make_bill()
    runner.agreement.get_all_agreements.return_value = [agreement]
    runner.tenant.get_tenant.return_value = tenant
    runner.rental_space.get_rental_space.return_value = space
    runner.billing.generate_bill.return_value = bill

    dialog = GenerateBillDialog(runner)
    dialog._agreement_combo.setCurrentIndex(0)
    dialog._period_start_input.set_date(date(2026, 8, 1))
    dialog._period_end_input.set_date(date(2026, 8, 31))
    dialog._on_generate()

    text = dialog._preview_label.text()
    assert "TOTAL: NPR 16500" in text
    assert "Rent: NPR 15000" in text
    assert "Electricity: NPR 1000" in text
    assert "Water: NPR 500" in text


# ------------------------------------------------------------------
# Bill detail dialog
# ------------------------------------------------------------------


@pytest.mark.unit
def test_bill_detail_dialog_renders_lines(qapp) -> None:
    runner = FakeRunner()
    bill = make_bill()
    tenant = make_tenant()
    space = make_space()
    runner.billing.get_bill.return_value = bill
    runner.tenant.get_tenant.return_value = tenant
    runner.rental_space.get_rental_space.return_value = space

    dialog = BillDetailDialog(runner, bill.id)

    text = dialog._details_label.text()
    assert "TOTAL: NPR 16500" in text
    assert "Sita Shrestha" in text
    assert "Flat A" in text
    assert "Draft" in text


@pytest.mark.unit
def test_bill_detail_dialog_confirm_enabled_only_for_draft(qapp) -> None:
    runner = FakeRunner()
    draft = make_bill(status=BillStatus.DRAFT)
    confirmed = make_bill(status=BillStatus.CONFIRMED)
    tenant = make_tenant()
    space = make_space()

    runner.billing.get_bill.return_value = draft
    runner.tenant.get_tenant.return_value = tenant
    runner.rental_space.get_rental_space.return_value = space
    dialog = BillDetailDialog(runner, draft.id)
    assert dialog._confirm_button.isEnabled() is True

    runner.billing.get_bill.return_value = confirmed
    dialog2 = BillDetailDialog(runner, confirmed.id)
    assert dialog2._confirm_button.isEnabled() is False


@pytest.mark.unit
def test_bill_detail_dialog_void_disabled_for_void(qapp) -> None:
    runner = FakeRunner()
    void_bill = make_bill(status=BillStatus.VOID)
    tenant = make_tenant()
    space = make_space()
    runner.billing.get_bill.return_value = void_bill
    runner.tenant.get_tenant.return_value = tenant
    runner.rental_space.get_rental_space.return_value = space

    dialog = BillDetailDialog(runner, void_bill.id)

    assert dialog._void_button.isEnabled() is False


@pytest.mark.unit
def test_bill_detail_dialog_confirm_workflow(qapp) -> None:
    runner = FakeRunner()
    draft = make_bill(status=BillStatus.DRAFT)
    confirmed = make_bill(bill_id=draft.id, status=BillStatus.CONFIRMED)
    tenant = make_tenant()
    space = make_space()
    runner.billing.get_bill.side_effect = [draft, confirmed]
    runner.billing.confirm_bill.return_value = confirmed
    runner.tenant.get_tenant.return_value = tenant
    runner.rental_space.get_rental_space.return_value = space

    dialog = BillDetailDialog(runner, draft.id)
    fake_confirm = MagicMock()
    fake_confirm.exec.return_value = QDialog.DialogCode.Accepted
    fake_confirm.confirmed = True
    with patch("app.desktop.billing_forms.ConfirmationDialog", return_value=fake_confirm):
        dialog._on_confirm()

    runner.billing.confirm_bill.assert_called_once_with(draft.id)
    assert "Confirmed" in dialog._details_label.text()


@pytest.mark.unit
def test_bill_detail_dialog_void_workflow(qapp) -> None:
    runner = FakeRunner()
    draft = make_bill(status=BillStatus.DRAFT)
    void_bill = make_bill(bill_id=draft.id, status=BillStatus.VOID)
    tenant = make_tenant()
    space = make_space()
    runner.billing.get_bill.side_effect = [draft, void_bill]
    runner.billing.void_bill.return_value = void_bill
    runner.tenant.get_tenant.return_value = tenant
    runner.rental_space.get_rental_space.return_value = space

    dialog = BillDetailDialog(runner, draft.id)
    fake_confirm = MagicMock()
    fake_confirm.exec.return_value = QDialog.DialogCode.Accepted
    fake_confirm.confirmed = True
    with patch("app.desktop.billing_forms.ConfirmationDialog", return_value=fake_confirm):
        dialog._on_void()

    runner.billing.void_bill.assert_called_once_with(draft.id)
    assert "Void" in dialog._details_label.text()


@pytest.mark.unit
def test_bill_detail_dialog_load_error(qapp) -> None:
    runner = FakeRunner()
    runner.billing.get_bill.side_effect = NotFoundError("bill not found")

    dialog = BillDetailDialog(runner, uuid.uuid4())

    assert "Could not load bill details" in dialog._details_label.text()


# ------------------------------------------------------------------
# Billing page
# ------------------------------------------------------------------


@pytest.fixture
def page(qapp) -> tuple[BillingPage, FakeRunner]:
    runner = FakeRunner()
    billing_page = BillingPage(runner)
    billing_page.show()
    return billing_page, runner


@pytest.mark.unit
def test_billing_page_refresh_populates_table(page) -> None:
    billing_page, runner = page
    bill = make_bill()
    runner.billing.get_all_bills.return_value = [bill]
    runner.tenant.get_tenant.return_value = make_tenant()
    runner.rental_space.get_rental_space.return_value = make_space()

    billing_page.refresh()

    assert billing_page._bill_model.rowCount() == 1
    assert "Sita Shrestha" in billing_page._bill_model.data(billing_page._bill_model.index(0, 1))
    assert "Flat A" in billing_page._bill_model.data(billing_page._bill_model.index(0, 2))
    assert "16500" in billing_page._bill_model.data(billing_page._bill_model.index(0, 3))
    assert "Draft" in billing_page._bill_model.data(billing_page._bill_model.index(0, 4))


@pytest.mark.unit
def test_billing_page_empty_state(page) -> None:
    billing_page, runner = page
    runner.billing.get_all_bills.return_value = []

    billing_page.refresh()

    assert billing_page._bill_model.rowCount() == 0
    assert billing_page._list_empty.isVisible()


@pytest.mark.unit
def test_billing_page_view_bill(page) -> None:
    import app.desktop.billing_page as bp

    billing_page, runner = page
    bill = make_bill()
    runner.billing.get_all_bills.return_value = [bill]
    runner.billing.get_bill.return_value = bill
    runner.tenant.get_tenant.return_value = make_tenant()
    runner.rental_space.get_rental_space.return_value = make_space()

    billing_page.refresh()
    billing_page._bill_table.selectRow(0)

    fake_detail = MagicMock()
    fake_detail.exec.return_value = QDialog.DialogCode.Accepted
    with patch.object(bp, "BillDetailDialog", return_value=fake_detail):
        billing_page._on_view_bill()

    fake_detail.exec.assert_called_once()


@pytest.mark.unit
def test_billing_page_generate_workflow(page) -> None:
    import app.desktop.billing_page as bp

    billing_page, runner = page
    bill = make_bill()
    runner.billing.get_all_bills.return_value = [bill]
    runner.tenant.get_tenant.return_value = make_tenant()
    runner.rental_space.get_rental_space.return_value = make_space()

    billing_page.refresh()

    fake_generate = MagicMock()
    fake_generate.exec.return_value = QDialog.DialogCode.Accepted
    fake_generate.result_bill.return_value = bill
    fake_detail = MagicMock()
    fake_detail.exec.return_value = QDialog.DialogCode.Accepted
    with patch.object(bp, "GenerateBillDialog", return_value=fake_generate), patch.object(
        bp, "BillDetailDialog", return_value=fake_detail
    ):
        billing_page._on_generate()

    fake_generate.exec.assert_called_once()
    fake_detail.exec.assert_called_once()


@pytest.mark.unit
def test_billing_page_service_error(page) -> None:
    billing_page, runner = page
    runner.billing.get_all_bills.side_effect = ValidationError("db unavailable")

    billing_page.refresh()

    assert billing_page._bill_model.rowCount() == 0


@pytest.mark.unit
def test_billing_page_confirm_flow(page) -> None:
    import app.desktop.billing_page as bp

    billing_page, runner = page
    bill = make_bill(status=BillStatus.DRAFT)
    runner.billing.get_all_bills.return_value = [bill]
    runner.billing.get_bill.return_value = bill
    runner.tenant.get_tenant.return_value = make_tenant()
    runner.rental_space.get_rental_space.return_value = make_space()

    billing_page.refresh()
    billing_page._bill_table.selectRow(0)

    fake_detail = MagicMock()
    fake_detail.exec.return_value = QDialog.DialogCode.Accepted
    with patch.object(bp, "BillDetailDialog", return_value=fake_detail):
        billing_page._on_confirm_bill()

    fake_detail.exec.assert_called_once()
    billing_page.refresh()  # no crash after mutation


# ------------------------------------------------------------------
# Integration: agreement -> billing
# ------------------------------------------------------------------


@pytest.mark.unit
def test_generate_bill_dialog_loads_agreements(qapp) -> None:
    """The agreement combo lists active agreements with tenant + space labels."""
    runner = FakeRunner()
    agreement = make_agreement()
    tenant = make_tenant(name="Ram Tamang")
    space = make_space(name="Room 2")
    runner.agreement.get_all_agreements.return_value = [agreement]
    runner.tenant.get_tenant.return_value = tenant
    runner.rental_space.get_rental_space.return_value = space

    dialog = GenerateBillDialog(runner)

    assert dialog._agreement_combo.count() == 1
    assert dialog._agreement_combo.currentText() == "Ram Tamang — Room 2"


@pytest.mark.unit
def test_generated_bill_displayed_in_page_and_detail(qapp) -> None:
    """A generated bill appears in the list and its detail view."""
    runner = FakeRunner()
    agreement = make_agreement()
    tenant = make_tenant()
    space = make_space()
    bill = make_bill()
    runner.agreement.get_all_agreements.return_value = [agreement]
    runner.billing.get_all_bills.return_value = [bill]
    runner.billing.get_bill.return_value = bill
    runner.tenant.get_tenant.return_value = tenant
    runner.rental_space.get_rental_space.return_value = space
    runner.billing.generate_bill.return_value = bill

    page = BillingPage(runner)
    page.show()
    page.refresh()
    assert page._bill_model.rowCount() == 1

    detail = BillDetailDialog(runner, bill.id)
    text = detail._details_label.text()
    assert "TOTAL: NPR 16500" in text
    assert "Sita Shrestha" in text
    assert "Flat A" in text
