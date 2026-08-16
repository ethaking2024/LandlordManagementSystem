from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.application.services.report_service import ReportService
from app.domain.entities import (
    Agreement,
    Bill,
    BillLine,
    Deposit,
    DepositSettlement,
    Expense,
    Payment,
    Property,
    RentalSpace,
    Tenant,
)
from app.domain.enums import (
    AgreementStatus,
    BillCategory,
    BillStatus,
    DepositStatus,
    ExpenseCategory,
    ExpenseStatus,
    PaymentMethod,
    PaymentStatus,
)
from app.domain.value_objects import BillingPeriod, Money
from app.reports.data import ReportFilters


def _money(value: str) -> Money:
    return Money(Decimal(value))


def _tenant(name: str = "Ram Sharma") -> Tenant:
    from app.domain.value_objects import PhoneNumber

    return Tenant(full_name=name, phone=PhoneNumber("9841000000"))


def _property(name: str = "Sunrise Apartments") -> Property:
    return Property(owner_id=uuid.uuid4(), name=name, address="Kathmandu")


def _space(property_id: uuid.UUID, name: str = "A-101") -> RentalSpace:
    return RentalSpace(property_id=property_id, name=name)


def _agreement(
    tenant_id: uuid.UUID,
    space_id: uuid.UUID,
    start_date: date = date(2026, 1, 1),
    status: AgreementStatus = AgreementStatus.ACTIVE,
) -> Agreement:
    return Agreement(
        tenant_id=tenant_id,
        rental_space_id=space_id,
        start_date=start_date,
        monthly_rent=_money("20000"),
        status=status,
    )


def _bill(
    tenant_id: uuid.UUID,
    space_id: uuid.UUID,
    billing_date: date = date(2026, 8, 31),
    status: BillStatus = BillStatus.CONFIRMED,
    rent: str = "20000",
    utilities: str = "3000",
) -> Bill:
    lines = [BillLine(category=BillCategory.RENT, description="rent", amount=_money(rent))]
    if utilities != "0":
        lines.append(BillLine(category=BillCategory.ELECTRICITY, description="elec", amount=_money(utilities)))
    return Bill(
        agreement_id=uuid.uuid4(),
        tenant_id=tenant_id,
        rental_space_id=space_id,
        period=BillingPeriod(date(2026, 8, 1), date(2026, 8, 31)),
        billing_date=billing_date,
        status=status,
        lines=lines,
    )


def _payment(
    tenant_id: uuid.UUID,
    payment_date: date = date(2026, 8, 10),
    amount: str = "8000",
    method: PaymentMethod = PaymentMethod.CASH,
    status: PaymentStatus = PaymentStatus.RECORDED,
) -> Payment:
    return Payment(
        tenant_id=tenant_id,
        payment_date=payment_date,
        amount=_money(amount),
        payment_method=method,
        status=status,
    )


def _expense(
    property_id: uuid.UUID,
    space_id: uuid.UUID | None = None,
    expense_date: date = date(2026, 8, 15),
    category: ExpenseCategory = ExpenseCategory.PLUMBING,
    amount: str = "3500",
    status: ExpenseStatus = ExpenseStatus.RECORDED,
) -> Expense:
    return Expense(
        property_id=property_id,
        rental_space_id=space_id,
        expense_date=expense_date,
        category=category,
        amount=_money(amount),
        status=status,
    )


def _deposit(
    agreement_id: uuid.UUID,
    tenant_id: uuid.UUID,
    received_date: date = date(2026, 8, 5),
    amount: str = "50000",
    status: DepositStatus = DepositStatus.HELD,
) -> Deposit:
    return Deposit(
        agreement_id=agreement_id,
        tenant_id=tenant_id,
        amount=_money(amount),
        received_date=received_date,
        status=status,
    )


def _balance(allocated: str, total: str = "23000"):
    balance = MagicMock()
    balance.total = _money(total)
    balance.allocated = _money(allocated)
    balance.outstanding = _money(str(Decimal(total) - Decimal(allocated)))
    return balance


def make_report_service(
    *,
    bills: list[Bill] | None = None,
    payments: list[Payment] | None = None,
    expenses: list[Expense] | None = None,
    deposits: list[Deposit] | None = None,
    properties: list[Property] | None = None,
    spaces: list[RentalSpace] | None = None,
    tenants: list[Tenant] | None = None,
    agreements: list[Agreement] | None = None,
    balances: dict[uuid.UUID, object] | None = None,
    allocated: dict[uuid.UUID, Money] | None = None,
    unused: dict[uuid.UUID, Money] | None = None,
    occupied: dict[uuid.UUID, bool] | None = None,
    settlements: dict[uuid.UUID, DepositSettlement] | None = None,
) -> ReportService:
    billing = MagicMock()
    billing.get_bills_by_billing_date_range.return_value = bills or []
    billing.get_all_bills.return_value = bills or []

    payment = MagicMock()
    payment.get_payments_by_date_range.return_value = payments or []
    payment.get_all_payments.return_value = payments or []
    payment.calculate_bill_balance.side_effect = lambda bill_id: (balances or {}).get(bill_id, _balance("0"))
    payment.calculate_payment_allocated.side_effect = lambda pid: (allocated or {}).get(pid, _money("0"))
    payment.calculate_payment_unused.side_effect = lambda pid: (unused or {}).get(pid, _money("0"))

    expense = MagicMock()
    expense.get_expenses_by_date_range.return_value = expenses or []
    expense.get_all_expenses.return_value = expenses or []

    deposit = MagicMock()
    deposit.get_deposits_by_date_range.return_value = deposits or []
    deposit.get_all_deposits.return_value = deposits or []
    deposit.get_settlement_by_deposit.side_effect = lambda did: (settlements or {}).get(did)

    property_svc = MagicMock()
    property_svc.get_all_properties.return_value = properties or []

    rental = MagicMock()
    rental.get_all_rental_spaces.return_value = spaces or []

    tenant_svc = MagicMock()
    tenant_svc.get_all_tenants.return_value = tenants or []

    agreement_svc = MagicMock()
    agreement_svc.get_all_agreements.return_value = agreements or []
    agreement_svc.is_rental_space_occupied.side_effect = lambda sid: (occupied or {}).get(sid, False)

    return ReportService(
        billing_service=billing,
        payment_service=payment,
        expense_service=expense,
        deposit_service=deposit,
        property_service=property_svc,
        rental_space_service=rental,
        tenant_service=tenant_svc,
        agreement_service=agreement_svc,
    )


class TestBillingReport:
    @pytest.mark.unit
    def test_produces_rows_with_amounts_and_balance(self) -> None:
        tenant = _tenant()
        property_obj = _property()
        space = _space(property_obj.id)
        bill = _bill(tenant.id, space.id)
        service = make_report_service(
            bills=[bill],
            spaces=[space],
            properties=[property_obj],
            tenants=[tenant],
            balances={bill.id: _balance("10000")},
        )

        rows = service.billing_report(ReportFilters(from_date=date(2026, 8, 1), to_date=date(2026, 8, 31)))

        assert len(rows) == 1
        row = rows[0]
        assert row.tenant_name == "Ram Sharma"
        assert row.property_name == "Sunrise Apartments"
        assert row.rental_space_name == "A-101"
        assert row.rent == _money("20000")
        assert row.utilities == _money("3000")
        assert row.total == _money("23000")
        assert row.paid == _money("10000")
        assert row.outstanding == _money("13000")
        assert row.status == BillStatus.CONFIRMED

    @pytest.mark.unit
    def test_uses_date_range_query(self) -> None:
        service = make_report_service(bills=[])
        service.billing_report(ReportFilters(from_date=date(2026, 8, 1), to_date=date(2026, 8, 31)))
        service._billing_service.get_bills_by_billing_date_range.assert_called_once_with(
            date(2026, 8, 1), date(2026, 8, 31)
        )

    @pytest.mark.unit
    def test_filters_by_property(self) -> None:
        tenant = _tenant()
        prop_a = _property("A")
        prop_b = _property("B")
        space_a = _space(prop_a.id, "A-1")
        space_b = _space(prop_b.id, "B-1")
        bill_a = _bill(tenant.id, space_a.id)
        bill_b = _bill(tenant.id, space_b.id)
        service = make_report_service(
            bills=[bill_a, bill_b],
            spaces=[space_a, space_b],
            properties=[prop_a, prop_b],
            tenants=[tenant],
        )

        rows = service.billing_report(ReportFilters(property_id=prop_a.id))

        assert [row.rental_space_name for row in rows] == ["A-1"]

    @pytest.mark.unit
    def test_filters_by_tenant_status_and_space(self) -> None:
        tenant_a = _tenant("A")
        tenant_b = _tenant("B")
        prop = _property()
        space_a = _space(prop.id, "S1")
        space_b = _space(prop.id, "S2")
        bill_a = _bill(tenant_a.id, space_a.id)
        bill_b = _bill(tenant_b.id, space_b.id, status=BillStatus.DRAFT)
        service = make_report_service(
            bills=[bill_a, bill_b],
            spaces=[space_a, space_b],
            properties=[prop],
            tenants=[tenant_a, tenant_b],
        )

        rows = service.billing_report(
            ReportFilters(tenant_id=tenant_a.id, rental_space_id=space_a.id, bill_status=BillStatus.CONFIRMED)
        )

        assert len(rows) == 1
        assert rows[0].tenant_name == "A"

    @pytest.mark.unit
    def test_void_bills_remain_historical(self) -> None:
        tenant = _tenant()
        prop = _property()
        space = _space(prop.id)
        bill = _bill(tenant.id, space.id, status=BillStatus.VOID)
        service = make_report_service(
            bills=[bill], spaces=[space], properties=[prop], tenants=[tenant]
        )

        rows = service.billing_report(ReportFilters())

        assert len(rows) == 1
        assert rows[0].status == BillStatus.VOID

    @pytest.mark.unit
    def test_empty_result(self) -> None:
        service = make_report_service(bills=[])
        assert service.billing_report(ReportFilters()) == []


class TestPaymentReport:
    @pytest.mark.unit
    def test_produces_rows_with_allocated_and_remaining(self) -> None:
        tenant = _tenant()
        prop = _property()
        space = _space(prop.id)
        agreement = _agreement(tenant.id, space.id)
        payment = _payment(tenant.id)
        service = make_report_service(
            payments=[payment],
            tenants=[tenant],
            properties=[prop],
            spaces=[space],
            agreements=[agreement],
            allocated={payment.id: _money("6000")},
            unused={payment.id: _money("2000")},
        )

        rows = service.payment_report(ReportFilters(from_date=date(2026, 8, 1), to_date=date(2026, 8, 31)))

        assert len(rows) == 1
        row = rows[0]
        assert row.tenant_name == "Ram Sharma"
        assert row.property_name == "Sunrise Apartments"
        assert row.amount == _money("8000")
        assert row.payment_method == PaymentMethod.CASH
        assert row.allocated == _money("6000")
        assert row.remaining == _money("2000")
        assert row.status == PaymentStatus.RECORDED

    @pytest.mark.unit
    def test_property_resolved_from_active_agreement(self) -> None:
        tenant = _tenant()
        prop = _property("Highland")
        space = _space(prop.id)
        agreement = _agreement(tenant.id, space.id)
        payment = _payment(tenant.id)
        service = make_report_service(
            payments=[payment],
            tenants=[tenant],
            properties=[prop],
            spaces=[space],
            agreements=[agreement],
        )

        rows = service.payment_report(ReportFilters(property_id=prop.id))

        assert len(rows) == 1
        assert rows[0].property_name == "Highland"

    @pytest.mark.unit
    def test_filters_by_method_status_and_tenant(self) -> None:
        tenant_a = _tenant("A")
        tenant_b = _tenant("B")
        prop = _property()
        space = _space(prop.id)
        agreement_a = _agreement(tenant_a.id, space.id)
        payment_a = _payment(tenant_a.id, method=PaymentMethod.CASH)
        payment_b = _payment(tenant_b.id, method=PaymentMethod.BANK_TRANSFER, status=PaymentStatus.VOID)
        service = make_report_service(
            payments=[payment_a, payment_b],
            tenants=[tenant_a, tenant_b],
            properties=[prop],
            spaces=[space],
            agreements=[agreement_a],
        )

        rows = service.payment_report(
            ReportFilters(tenant_id=tenant_a.id, payment_method=PaymentMethod.CASH, payment_status=PaymentStatus.RECORDED)
        )

        assert len(rows) == 1
        assert rows[0].tenant_name == "A"


class TestExpenseReport:
    @pytest.mark.unit
    def test_produces_rows_with_property_and_space(self) -> None:
        prop = _property()
        space = _space(prop.id, "Basement")
        expense = _expense(prop.id, space.id)
        service = make_report_service(
            expenses=[expense], properties=[prop], spaces=[space]
        )

        rows = service.expense_report(ReportFilters(from_date=date(2026, 8, 1), to_date=date(2026, 8, 31)))

        assert len(rows) == 1
        row = rows[0]
        assert row.property_name == "Sunrise Apartments"
        assert row.rental_space_name == "Basement"
        assert row.category == ExpenseCategory.PLUMBING
        assert row.amount == _money("3500")
        assert row.status == ExpenseStatus.RECORDED

    @pytest.mark.unit
    def test_filters_by_property_category_status_and_space(self) -> None:
        prop_a = _property("A")
        prop_b = _property("B")
        space = _space(prop_a.id)
        expense_a = _expense(prop_a.id, space.id, category=ExpenseCategory.TAX)
        expense_b = _expense(prop_b.id, category=ExpenseCategory.PLUMBING)
        service = make_report_service(
            expenses=[expense_a, expense_b], properties=[prop_a, prop_b], spaces=[space]
        )

        rows = service.expense_report(
            ReportFilters(property_id=prop_a.id, expense_category=ExpenseCategory.TAX)
        )

        assert len(rows) == 1
        assert rows[0].category == ExpenseCategory.TAX


class TestDepositReport:
    @pytest.mark.unit
    def test_produces_rows_with_settlement(self) -> None:
        tenant = _tenant()
        prop = _property()
        space = _space(prop.id)
        agreement = _agreement(tenant.id, space.id, status=AgreementStatus.ENDED)
        deposit = _deposit(agreement.id, tenant.id)
        settlement = DepositSettlement(deposit_id=deposit.id, settlement_date=date(2026, 9, 1))
        from app.domain.entities import DepositDeduction

        settlement.add_deduction(DepositDeduction(amount=_money("10000"), reason="Damage"))
        settlement.record_refund(_money("40000"))
        service = make_report_service(
            deposits=[deposit],
            agreements=[agreement],
            tenants=[tenant],
            properties=[prop],
            spaces=[space],
            settlements={deposit.id: settlement},
        )

        rows = service.deposit_report(ReportFilters(from_date=date(2026, 8, 1), to_date=date(2026, 8, 31)))

        assert len(rows) == 1
        row = rows[0]
        assert row.tenant_name == "Ram Sharma"
        assert row.property_name == "Sunrise Apartments"
        assert row.amount == _money("50000")
        assert row.status == DepositStatus.HELD
        assert row.settlement_date == date(2026, 9, 1)
        assert row.deductions == _money("10000")
        assert row.refund == _money("40000")

    @pytest.mark.unit
    def test_unsettled_deposit_has_zero_deductions(self) -> None:
        tenant = _tenant()
        prop = _property()
        space = _space(prop.id)
        agreement = _agreement(tenant.id, space.id)
        deposit = _deposit(agreement.id, tenant.id)
        service = make_report_service(
            deposits=[deposit],
            agreements=[agreement],
            tenants=[tenant],
            properties=[prop],
            spaces=[space],
        )

        rows = service.deposit_report(ReportFilters())

        assert rows[0].deductions == _money("0")
        assert rows[0].refund is None

    @pytest.mark.unit
    def test_filters_by_status_tenant_and_property(self) -> None:
        tenant_a = _tenant("A")
        tenant_b = _tenant("B")
        prop = _property()
        space = _space(prop.id)
        agreement_a = _agreement(tenant_a.id, space.id)
        deposit_a = _deposit(agreement_a.id, tenant_a.id)
        deposit_b = _deposit(agreement_a.id, tenant_a.id, status=DepositStatus.VOID)
        service = make_report_service(
            deposits=[deposit_a, deposit_b],
            agreements=[agreement_a],
            tenants=[tenant_a, tenant_b],
            properties=[prop],
            spaces=[space],
        )

        rows = service.deposit_report(
            ReportFilters(tenant_id=tenant_a.id, deposit_status=DepositStatus.HELD)
        )

        assert len(rows) == 1
        assert rows[0].status == DepositStatus.HELD


class TestPropertySummary:
    @pytest.mark.unit
    def test_totals_only_confirmed_bills_and_recorded_expenses(self) -> None:
        tenant = _tenant()
        prop = _property()
        space = _space(prop.id)
        confirmed = _bill(tenant.id, space.id, rent="20000", utilities="3000")
        draft = _bill(tenant.id, space.id, status=BillStatus.DRAFT)
        void_expense = _expense(prop.id, amount="5000", status=ExpenseStatus.VOID)
        recorded_expense = _expense(prop.id, amount="3500")
        service = make_report_service(
            bills=[confirmed, draft],
            expenses=[void_expense, recorded_expense],
            properties=[prop],
            spaces=[space],
            tenants=[tenant],
            balances={confirmed.id: _balance("5000")},
        )

        rows = service.property_summary(ReportFilters())

        assert len(rows) == 1
        row = rows[0]
        assert row.rental_spaces == 1
        assert row.billed == _money("23000")
        assert row.payments_received == _money("5000")
        assert row.outstanding == _money("18000")
        assert row.expenses == _money("3500")

    @pytest.mark.unit
    def test_occupancy_and_vacancy(self) -> None:
        prop = _property()
        space_occupied = _space(prop.id, "S1")
        space_vacant = _space(prop.id, "S2")
        service = make_report_service(
            properties=[prop],
            spaces=[space_occupied, space_vacant],
            occupied={space_occupied.id: True, space_vacant.id: False},
        )

        rows = service.property_summary(ReportFilters())

        assert rows[0].rental_spaces == 2
        assert rows[0].occupied == 1
        assert rows[0].vacant == 1

    @pytest.mark.unit
    def test_property_filter_limits_rows(self) -> None:
        prop_a = _property("A")
        prop_b = _property("B")
        service = make_report_service(properties=[prop_a, prop_b], spaces=[])

        rows = service.property_summary(ReportFilters(property_id=prop_a.id))

        assert len(rows) == 1
        assert rows[0].property_name == "A"

    @pytest.mark.unit
    def test_default_range_is_current_month(self) -> None:
        today = date.today()
        month_start = today.replace(day=1)
        if month_start.month == 12:
            next_month = date(month_start.year + 1, 1, 1)
        else:
            next_month = date(month_start.year, month_start.month + 1, 1)
        month_end = next_month - timedelta(days=1)

        service = make_report_service(properties=[_property()], spaces=[])
        rows = service.property_summary(ReportFilters())

        assert rows[0].from_date == month_start
        assert rows[0].to_date == month_end

    @pytest.mark.unit
    def test_explicit_range_used(self) -> None:
        prop = _property()
        service = make_report_service(properties=[prop], spaces=[])
        rows = service.property_summary(ReportFilters(from_date=date(2026, 1, 1), to_date=date(2026, 1, 31)))
        assert rows[0].from_date == date(2026, 1, 1)
        assert rows[0].to_date == date(2026, 1, 31)
