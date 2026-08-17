from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.domain.enums import (
    AgreementStatus,
    BillCategory,
    DepositStatus,
    ExpenseCategory,
    PaymentMethod,
    SpaceType,
    UtilityType,
)
from app.domain.value_objects import Money


@pytest.mark.integration
def test_workflow_a_core_chain(run_with_services, repositories):
    def _build(services):
        owner = services.owner().create_owner(name="Workflow Owner", phone="9800000001")
        prop = services.property().create_property(owner.id, "Workflow Building", "Kathmandu")
        space = services.rental_space().create_rental_space(prop.id, "Room 1", SpaceType.ROOM)
        tenant = services.tenant().create_tenant("Workflow Tenant", "9800000002")
        agreement = services.agreement().create_agreement(
            tenant.id, space.id, date(2026, 1, 1), "25000"
        )
        return {
            "owner_id": owner.id,
            "property_id": prop.id,
            "space_id": space.id,
            "tenant_id": tenant.id,
            "agreement_id": agreement.id,
        }

    ids = run_with_services(_build)

    # Verify every entity is persisted and readable through the real repositories
    assert repositories.owner.get(ids["owner_id"]).name == "Workflow Owner"
    assert repositories.property.get(ids["property_id"]).address == "Kathmandu"
    assert repositories.rental_space.get(ids["space_id"]).is_active is True
    assert repositories.tenant.get(ids["tenant_id"]).full_name == "Workflow Tenant"
    agreement = repositories.agreement.get(ids["agreement_id"])
    assert agreement.status == AgreementStatus.ACTIVE
    assert agreement.monthly_rent.amount == Decimal("25000.00")


@pytest.mark.integration
def test_workflow_b_bill_payment_allocation_and_balance(run_with_services, repositories):
    def _run(services):
        owner = services.owner().create_owner(name="Billing Owner", phone="9800000001")
        prop = services.property().create_property(owner.id, "Billing Building", "Kathmandu")
        space = services.rental_space().create_rental_space(prop.id, "Room 1", SpaceType.ROOM)
        tenant = services.tenant().create_tenant("Billing Tenant", "9800000002")
        agreement = services.agreement().create_agreement(
            tenant.id, space.id, date(2026, 1, 1), "25000"
        )
        services.utility_config().set_config(space.id, UtilityType.ELECTRICITY, "fixed", "1500")
        services.utility_config().set_config(space.id, UtilityType.WATER, "no_charge")

        bill = services.billing().generate_bill(
            agreement.id, date(2026, 1, 1), date(2026, 1, 31), date(2026, 1, 31)
        )
        bill_id = bill.id
        before = services.payment().calculate_bill_balance(bill_id)
        assert before.outstanding.amount == Decimal("26500.00")

        services.billing().confirm_bill(bill_id)
        payment = services.payment().record_payment(
            tenant.id, date(2026, 1, 31), Money(Decimal("26500")), PaymentMethod.CASH
        )
        services.payment().allocate_payment(payment.id, bill_id, Money(Decimal("26500")))
        after = services.payment().calculate_bill_balance(bill_id)
        return {"bill_id": bill_id, "before": before, "after": after}

    result = run_with_services(_run)

    assert result["before"].outstanding.amount == Decimal("26500.00")
    assert result["after"].outstanding.amount == Decimal("0.00")
    assert result["after"].allocated.amount == Decimal("26500.00")

    bill = repositories.bill.get(result["bill_id"])
    assert bill.status.value == "confirmed"
    assert len(bill.lines) == 3


@pytest.mark.integration
def test_workflow_c_meter_reading_tariff_billing(run_with_services, repositories):
    def _run(services):
        owner = services.owner().create_owner(name="Utility Owner", phone="9800000001")
        prop = services.property().create_property(owner.id, "Utility Building", "Kathmandu")
        space = services.rental_space().create_rental_space(prop.id, "Room 1", SpaceType.ROOM)
        tenant = services.tenant().create_tenant("Utility Tenant", "9800000002")
        agreement = services.agreement().create_agreement(
            tenant.id, space.id, date(2026, 1, 1), "25000"
        )
        services.utility_config().set_config(space.id, UtilityType.ELECTRICITY, "metered")
        services.utility_config().set_config(space.id, UtilityType.WATER, "no_charge")

        meter = services.meter().create_meter(
            space.id, UtilityType.ELECTRICITY, "MTR-UTIL", date(2026, 1, 1)
        )
        services.meter_reading().record_reading(meter.id, date(2026, 1, 1), "1000")
        services.meter_reading().record_reading(meter.id, date(2026, 1, 31), "1100")
        services.utility_tariff().create_tariff(UtilityType.ELECTRICITY, date(2026, 1, 1), "15")

        bill = services.billing().generate_bill(
            agreement.id, date(2026, 1, 1), date(2026, 1, 31), date(2026, 1, 31)
        )
        return {"bill_id": bill.id}

    result = run_with_services(_run)

    bill = repositories.bill.get(result["bill_id"])
    electricity_line = next(line for line in bill.lines if line.category == BillCategory.ELECTRICITY)
    assert electricity_line.consumption == Decimal("100")
    assert electricity_line.tariff_rate.amount == Decimal("15.00")
    assert electricity_line.amount.amount == Decimal("1500.00")
    assert electricity_line.meter_identifier == "MTR-UTIL"


@pytest.mark.integration
def test_workflow_d_deposit_settlement(run_with_services, repositories):
    def _run(services):
        owner = services.owner().create_owner(name="Deposit Owner", phone="9800000001")
        prop = services.property().create_property(owner.id, "Deposit Building", "Kathmandu")
        space = services.rental_space().create_rental_space(prop.id, "Room 1", SpaceType.ROOM)
        tenant = services.tenant().create_tenant("Deposit Tenant", "9800000002")
        agreement = services.agreement().create_agreement(
            tenant.id, space.id, date(2026, 1, 1), "25000"
        )
        deposit = services.deposit().record_deposit(
            agreement.id, Money(Decimal("50000")), date(2026, 1, 1)
        )
        services.agreement().end_agreement(agreement.id, date(2026, 12, 31))
        services.deposit().create_settlement(
            deposit.id, date(2026, 12, 31), [("5000", "Damage repair")]
        )
        services.deposit().complete_settlement(deposit.id, Money(Decimal("45000")))
        return {"deposit_id": deposit.id, "agreement_id": agreement.id}

    result = run_with_services(_run)

    deposit = repositories.deposit.get(result["deposit_id"])
    assert deposit.status == DepositStatus.SETTLED

    settlement = repositories.deposit_settlement.get_by_deposit(result["deposit_id"])
    assert settlement is not None
    assert settlement.refund_amount.amount == Decimal("45000.00")
    assert settlement.total_deductions.amount == Decimal("5000.00")

    agreement = repositories.agreement.get(result["agreement_id"])
    assert agreement.status == AgreementStatus.ENDED


@pytest.mark.integration
def test_workflow_e_expense(run_with_services, repositories):
    def _run(services):
        owner = services.owner().create_owner(name="Expense Owner", phone="9800000001")
        prop = services.property().create_property(owner.id, "Expense Building", "Kathmandu")
        space = services.rental_space().create_rental_space(prop.id, "Room 1", SpaceType.ROOM)
        expense = services.expense().record_expense(
            prop.id,
            date(2026, 2, 15),
            ExpenseCategory.PLUMBING,
            Money(Decimal("7500")),
            description="Pipe replacement",
            rental_space_id=space.id,
        )
        total = services.expense().calculate_property_expense_total(prop.id)
        return {"expense_id": expense.id, "total": total}

    result = run_with_services(_run)

    expense = repositories.expense.get(result["expense_id"])
    assert expense.category == ExpenseCategory.PLUMBING
    assert expense.amount.amount == Decimal("7500.00")
    assert expense.rental_space_id is not None
    assert result["total"].amount == Decimal("7500.00")
