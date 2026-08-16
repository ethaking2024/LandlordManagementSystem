from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtWidgets import QDialog

from app.core.exceptions import ValidationError
from app.desktop.billing_forms import BillDetailDialog, format_money
from app.desktop.dashboard_page import DashboardPage
from app.desktop.payment_forms import PaymentDetailDialog, format_payment_method
from app.desktop.services import OPERATION_FAILED
from app.domain.enums import BillStatus, PaymentMethod, PaymentStatus


class FakeRunner:
    def __init__(self) -> None:
        self.property = MagicMock()
        self.rental_space = MagicMock()
        self.agreement = MagicMock()
        self.tenant = MagicMock()
        self.payment = MagicMock()
        self.billing = MagicMock()

    def run(self, operation, parent=None):
        services = MagicMock()
        services.property = MagicMock(return_value=self.property)
        services.rental_space = MagicMock(return_value=self.rental_space)
        services.agreement = MagicMock(return_value=self.agreement)
        services.tenant = MagicMock(return_value=self.tenant)
        services.payment = MagicMock(return_value=self.payment)
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


class _Summary:
    def __init__(self, billed: str = "0", paid: str = "0", outstanding: str = "0") -> None:
        self.billed = _Amount(billed)
        self.paid = _Amount(paid)
        self.outstanding = _Amount(outstanding)


class _Balance:
    def __init__(self, total: str = "20000", outstanding: str = "20000") -> None:
        self.total = _Amount(total)
        self.outstanding = _Amount(outstanding)


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


def make_tenant(tenant_id: uuid.UUID | None = None, name: str = "Sita Shrestha"):
    tenant = MagicMock()
    tenant.id = tenant_id or uuid.uuid4()
    tenant.full_name = name
    return tenant


def make_agreement(tenant_id: uuid.UUID):
    agreement = MagicMock()
    agreement.id = uuid.uuid4()
    agreement.tenant_id = tenant_id
    agreement.status = "ACTIVE"
    return agreement


def make_bill(
    bill_id: uuid.UUID | None = None,
    tenant_id: uuid.UUID | None = None,
    space_id: uuid.UUID | None = None,
    status: BillStatus = BillStatus.CONFIRMED,
):
    bill = MagicMock()
    bill.id = bill_id or uuid.uuid4()
    bill.tenant_id = tenant_id or uuid.uuid4()
    bill.rental_space_id = space_id or uuid.uuid4()
    bill.period = MagicMock()
    bill.period.start = date(2026, 8, 1)
    bill.period.end = date(2026, 8, 31)
    bill.status = status
    bill.total = _Amount("20000")
    return bill


def make_payment(
    payment_id: uuid.UUID | None = None,
    tenant_id: uuid.UUID | None = None,
    status: PaymentStatus = PaymentStatus.RECORDED,
    amount: str = "8000",
    method: PaymentMethod = PaymentMethod.CASH,
    payment_date: date = date(2026, 8, 10),
):
    payment = MagicMock()
    payment.id = payment_id or uuid.uuid4()
    payment.tenant_id = tenant_id or uuid.uuid4()
    payment.payment_date = payment_date
    payment.amount = _Amount(amount)
    payment.payment_method = method
    payment.status = status
    return payment


def configure_full_dataset(runner: FakeRunner) -> dict[str, object]:
    """Configure a complete, consistent dashboard dataset and return shared objects."""
    prop = make_property()
    occupied_space = make_space(property_id=prop.id, name="Room 101")
    vacant_space = make_space(property_id=prop.id, name="Room 202")
    tenant = make_tenant()
    active_agreement = make_agreement(tenant.id)
    bill = make_bill(tenant_id=tenant.id, space_id=occupied_space.id)
    payment = make_payment(tenant_id=tenant.id)

    runner.property.get_all_properties.return_value = [prop]
    runner.rental_space.get_all_rental_spaces.return_value = [occupied_space, vacant_space]
    runner.property.get_property.side_effect = lambda _property_id: prop
    runner.agreement.is_rental_space_occupied.side_effect = lambda space_id: space_id == occupied_space.id
    runner.agreement.get_active_agreements.return_value = [active_agreement]
    runner.payment.calculate_monthly_summary.return_value = _Summary(
        billed="60000", paid="40000", outstanding="20000"
    )
    runner.payment.get_outstanding_bills.return_value = [(bill, _Balance(outstanding="12000"))]
    runner.tenant.get_tenant.side_effect = lambda _tenant_id: tenant
    runner.rental_space.get_rental_space.side_effect = lambda _space_id: occupied_space
    runner.payment.get_all_payments.return_value = [payment]

    return {
        "prop": prop,
        "occupied_space": occupied_space,
        "vacant_space": vacant_space,
        "tenant": tenant,
        "active_agreement": active_agreement,
        "bill": bill,
        "payment": payment,
    }


@pytest.fixture
def page(qapp) -> tuple[DashboardPage, FakeRunner]:
    runner = FakeRunner()
    dashboard = DashboardPage(runner)
    dashboard.show()
    return dashboard, runner


# ------------------------------------------------------------------
# Construction
# ------------------------------------------------------------------


@pytest.mark.unit
def test_dashboard_page_construction(page) -> None:
    dashboard, runner = page
    assert dashboard.title == "Dashboard"
    assert set(dashboard._cards.keys()) == {
        "properties",
        "spaces",
        "occupied",
        "vacant",
        "active_tenants",
        "active_agreements",
    }
    assert set(dashboard._month_cards.keys()) == {"billed", "paid", "outstanding"}
    assert dashboard._refresh_button is not None


@pytest.mark.unit
def test_dashboard_refresh_button_connected(page) -> None:
    dashboard, runner = page
    assert dashboard._refresh_button.clicked is not None


# ------------------------------------------------------------------
# KPI loading and counts
# ------------------------------------------------------------------


@pytest.mark.unit
def test_dashboard_kpi_counts(page) -> None:
    dashboard, runner = page
    configure_full_dataset(runner)

    dashboard.refresh()

    assert dashboard._cards["properties"]._value_label.text() == "1"
    assert dashboard._cards["spaces"]._value_label.text() == "2"
    assert dashboard._cards["occupied"]._value_label.text() == "1"
    assert dashboard._cards["vacant"]._value_label.text() == "1"
    assert dashboard._cards["active_tenants"]._value_label.text() == "1"
    assert dashboard._cards["active_agreements"]._value_label.text() == "1"


@pytest.mark.unit
def test_dashboard_active_tenants_is_distinct(page) -> None:
    dashboard, runner = page
    configure_full_dataset(runner)
    tenant_id = uuid.uuid4()
    runner.agreement.get_active_agreements.return_value = [
        make_agreement(tenant_id),
        make_agreement(tenant_id),
        make_agreement(uuid.uuid4()),
    ]

    dashboard.refresh()

    assert dashboard._cards["active_tenants"]._value_label.text() == "2"
    assert dashboard._cards["active_agreements"]._value_label.text() == "3"


# ------------------------------------------------------------------
# Current month summary
# ------------------------------------------------------------------


@pytest.mark.unit
def test_dashboard_month_summary(page) -> None:
    dashboard, runner = page
    configure_full_dataset(runner)

    dashboard.refresh()

    assert dashboard._month_cards["billed"]._value_label.text() == "NPR 60000"
    assert dashboard._month_cards["paid"]._value_label.text() == "NPR 40000"
    assert dashboard._month_cards["outstanding"]._value_label.text() == "NPR 20000"


@pytest.mark.unit
def test_dashboard_month_summary_uses_current_month(page) -> None:
    dashboard, runner = page
    configure_full_dataset(runner)

    dashboard.refresh()

    call = runner.payment.calculate_monthly_summary.call_args
    today = date.today()
    assert call.args[0] == today.year
    assert call.args[1] == today.month


# ------------------------------------------------------------------
# Outstanding bills
# ------------------------------------------------------------------


@pytest.mark.unit
def test_dashboard_outstanding_bills_table(page) -> None:
    dashboard, runner = page
    configure_full_dataset(runner)

    dashboard.refresh()

    assert dashboard._outstanding_model.rowCount() == 1
    assert dashboard._outstanding_model.data(dashboard._outstanding_model.index(0, 0)) == "Sita Shrestha"
    assert "Room 101" in dashboard._outstanding_model.data(dashboard._outstanding_model.index(0, 1))
    assert "NPR 20000" in dashboard._outstanding_model.data(dashboard._outstanding_model.index(0, 3))
    assert "NPR 12000" in dashboard._outstanding_model.data(dashboard._outstanding_model.index(0, 5))
    assert dashboard._outstanding_table.isVisible()
    assert not dashboard._outstanding_empty.isVisible()


@pytest.mark.unit
def test_dashboard_outstanding_empty_state(page) -> None:
    dashboard, runner = page
    configure_full_dataset(runner)
    runner.payment.get_outstanding_bills.return_value = []

    dashboard.refresh()

    assert dashboard._outstanding_model.rowCount() == 0
    assert not dashboard._outstanding_table.isVisible()
    assert dashboard._outstanding_empty.isVisible()


# ------------------------------------------------------------------
# Recent payments
# ------------------------------------------------------------------


@pytest.mark.unit
def test_dashboard_recent_payments_table(page) -> None:
    dashboard, runner = page
    configure_full_dataset(runner)

    dashboard.refresh()

    assert dashboard._payment_model.rowCount() == 1
    assert "Sita Shrestha" in dashboard._payment_model.data(dashboard._payment_model.index(0, 1))
    assert "NPR 8000" in dashboard._payment_model.data(dashboard._payment_model.index(0, 2))
    assert "Cash" in dashboard._payment_model.data(dashboard._payment_model.index(0, 3))
    assert dashboard._payment_table.isVisible()
    assert not dashboard._payment_empty.isVisible()


@pytest.mark.unit
def test_dashboard_recent_payments_excludes_void(page) -> None:
    dashboard, runner = page
    configure_full_dataset(runner)
    runner.payment.get_all_payments.return_value = [
        make_payment(status=PaymentStatus.VOID),
        make_payment(payment_date=date(2026, 8, 11)),
    ]

    dashboard.refresh()

    assert dashboard._payment_model.rowCount() == 1


@pytest.mark.unit
def test_dashboard_recent_payments_sorted_desc_and_limited(page) -> None:
    dashboard, runner = page
    configure_full_dataset(runner)
    payments = [
        make_payment(payment_date=date(2026, 8, 1)),
        make_payment(payment_date=date(2026, 8, 3)),
        make_payment(payment_date=date(2026, 8, 2)),
        make_payment(payment_date=date(2026, 8, 5)),
        make_payment(payment_date=date(2026, 8, 4)),
        make_payment(payment_date=date(2026, 8, 6)),
        make_payment(payment_date=date(2026, 8, 7)),
        make_payment(payment_date=date(2026, 8, 8)),
        make_payment(payment_date=date(2026, 8, 9)),
        make_payment(payment_date=date(2026, 8, 10)),
        make_payment(payment_date=date(2026, 8, 11)),
        make_payment(payment_date=date(2026, 8, 12)),
    ]
    runner.payment.get_all_payments.return_value = payments

    dashboard.refresh()

    assert dashboard._payment_model.rowCount() == 10


@pytest.mark.unit
def test_dashboard_recent_payments_empty_state(page) -> None:
    dashboard, runner = page
    configure_full_dataset(runner)
    runner.payment.get_all_payments.return_value = []

    dashboard.refresh()

    assert dashboard._payment_model.rowCount() == 0
    assert not dashboard._payment_table.isVisible()
    assert dashboard._payment_empty.isVisible()


# ------------------------------------------------------------------
# Vacant spaces
# ------------------------------------------------------------------


@pytest.mark.unit
def test_dashboard_vacant_spaces_table(page) -> None:
    dashboard, runner = page
    configure_full_dataset(runner)

    dashboard.refresh()

    assert dashboard._vacant_model.rowCount() == 1
    assert dashboard._vacant_model.data(dashboard._vacant_model.index(0, 0)) == "Main Building"
    assert dashboard._vacant_model.data(dashboard._vacant_model.index(0, 1)) == "Room 202"
    assert dashboard._vacant_table.isVisible()
    assert not dashboard._vacant_empty.isVisible()


@pytest.mark.unit
def test_dashboard_vacant_empty_state(page) -> None:
    dashboard, runner = page
    configure_full_dataset(runner)
    runner.agreement.is_rental_space_occupied.side_effect = lambda _space_id: True

    dashboard.refresh()

    assert dashboard._vacant_model.rowCount() == 0
    assert not dashboard._vacant_table.isVisible()
    assert dashboard._vacant_empty.isVisible()


# ------------------------------------------------------------------
# Refresh and service failure
# ------------------------------------------------------------------


@pytest.mark.unit
def test_dashboard_refresh_reloads(page) -> None:
    dashboard, runner = page
    configure_full_dataset(runner)
    dashboard.refresh()
    assert dashboard._cards["properties"]._value_label.text() == "1"

    runner.property.get_all_properties.return_value = [
        make_property(),
        make_property(),
    ]
    dashboard.refresh()

    assert dashboard._cards["properties"]._value_label.text() == "2"


@pytest.mark.unit
def test_dashboard_service_error_keeps_previous_state(page) -> None:
    dashboard, runner = page
    configure_full_dataset(runner)
    dashboard.refresh()
    assert dashboard._cards["properties"]._value_label.text() == "1"

    runner.property.get_all_properties.side_effect = ValidationError("db unavailable")
    dashboard.refresh()

    assert dashboard._cards["properties"]._value_label.text() == "1"


# ------------------------------------------------------------------
# Navigation from dashboard items
# ------------------------------------------------------------------


@pytest.mark.unit
def test_dashboard_open_bill_from_outstanding(page) -> None:
    import app.desktop.dashboard_page as dp

    dashboard, runner = page
    data = configure_full_dataset(runner)
    bill = data["bill"]
    runner.payment.calculate_monthly_summary.return_value = _Summary()
    dashboard.refresh()
    dashboard._outstanding_table.selectRow(0)

    fake_dialog = MagicMock()
    fake_dialog.exec.return_value = QDialog.DialogCode.Accepted
    with patch.object(dp, "BillDetailDialog", return_value=fake_dialog) as patched:
        dashboard._on_open_bill()

    patched.assert_called_once()
    assert patched.call_args.args[1] == bill.id
    fake_dialog.exec.assert_called_once()


@pytest.mark.unit
def test_dashboard_open_payment_from_recent(page) -> None:
    import app.desktop.dashboard_page as dp

    dashboard, runner = page
    data = configure_full_dataset(runner)
    payment = data["payment"]
    dashboard.refresh()
    dashboard._payment_table.selectRow(0)

    fake_dialog = MagicMock()
    fake_dialog.exec.return_value = QDialog.DialogCode.Accepted
    with patch.object(dp, "PaymentDetailDialog", return_value=fake_dialog) as patched:
        dashboard._on_open_payment()

    patched.assert_called_once()
    assert patched.call_args.args[1] == payment.id
    fake_dialog.exec.assert_called_once()


# ------------------------------------------------------------------
# Formatting helpers
# ------------------------------------------------------------------


@pytest.mark.unit
def test_dashboard_format_money() -> None:
    assert format_money(_Amount("3500")) == "NPR 3500"
    assert format_money(None) == ""


@pytest.mark.unit
def test_dashboard_format_payment_method() -> None:
    assert format_payment_method(PaymentMethod.CASH) == "Cash"
    assert format_payment_method(PaymentMethod.BANK_TRANSFER) == "Bank transfer"


@pytest.mark.unit
def test_dashboard_imported_dialogs_available() -> None:
    assert BillDetailDialog is not None
    assert PaymentDetailDialog is not None
