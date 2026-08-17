from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.domain.entities import (
    Agreement,
    Bill,
    BillLine,
    Deposit,
    DepositDeduction,
    DepositSettlement,
    Expense,
    Meter,
    MeterReading,
    MeterReplacement,
    Owner,
    Payment,
    PaymentAllocation,
    Property,
    RentalSpace,
    Tenant,
    UtilityConfig,
    UtilityTariff,
)
from app.domain.enums import (
    BillCategory,
    ExpenseCategory,
    PaymentMethod,
    SpaceType,
    UtilityType,
)
from app.domain.value_objects import BillingPeriod, MeterReadingValue, Money, PhoneNumber


def make_owner(name="Alice Owner") -> Owner:
    return Owner(name=name, phone=PhoneNumber("9800000001"))


def make_property(owner_id, name="Main Building") -> Property:
    return Property(owner_id=owner_id, name=name, address="Kathmandu, Nepal")


def make_space(property_id, name="Room 1", space_type=SpaceType.ROOM) -> RentalSpace:
    return RentalSpace(property_id=property_id, name=name, space_type=space_type)


def make_tenant(name="Bob Tenant") -> Tenant:
    return Tenant(full_name=name, phone=PhoneNumber("9800000002"))


def make_agreement(tenant_id, space_id, monthly_rent="25000") -> Agreement:
    return Agreement(
        tenant_id=tenant_id,
        rental_space_id=space_id,
        start_date=date(2026, 1, 1),
        monthly_rent=Money(Decimal(monthly_rent)),
        security_deposit=Money(Decimal("50000")),
    )


def make_utility_config(space_id, utility_type=UtilityType.ELECTRICITY, config_type="fixed", fixed_amount="1500"):
    return UtilityConfig(
        rental_space_id=space_id,
        utility_type=utility_type,
        config_type=config_type,
        fixed_amount=Money(Decimal(fixed_amount)) if fixed_amount is not None else None,
    )


def make_meter(space_id, utility_type=UtilityType.ELECTRICITY, identifier="MTR-001"):
    return Meter(
        rental_space_id=space_id,
        utility_type=utility_type,
        identifier=identifier,
        installation_date=date(2026, 1, 1),
    )


def make_reading(meter_id, reading_date, value) -> MeterReading:
    return MeterReading(meter_id=meter_id, reading_date=reading_date, value=MeterReadingValue(Decimal(value)))


def make_tariff(utility_type=UtilityType.ELECTRICITY, effective_from=date(2026, 1, 1), rate="15"):
    return UtilityTariff(utility_type=utility_type, effective_from=effective_from, rate=Money(Decimal(rate)))


def make_meter_replacement(old_meter_id, new_meter_id, replaced_on=date(2026, 3, 1)) -> MeterReplacement:
    return MeterReplacement(old_meter_id=old_meter_id, new_meter_id=new_meter_id, replaced_on=replaced_on)


def make_bill(agreement_id, tenant_id, space_id, start=date(2026, 1, 1), end=date(2026, 1, 31), lines=None) -> Bill:
    bill = Bill(
        agreement_id=agreement_id,
        tenant_id=tenant_id,
        rental_space_id=space_id,
        period=BillingPeriod(start, end),
        billing_date=end,
    )
    for line in lines or []:
        bill.add_line(line)
    return bill


def make_rent_line(amount="25000") -> BillLine:
    return BillLine(
        category=BillCategory.RENT,
        description="Monthly rent",
        amount=Money(Decimal(amount)),
    )


def make_payment(tenant_id, amount="25000", payment_method=PaymentMethod.CASH) -> Payment:
    return Payment(
        tenant_id=tenant_id,
        payment_date=date(2026, 1, 31),
        amount=Money(Decimal(amount)),
        payment_method=payment_method,
    )


def make_allocation(payment_id, bill_id, amount) -> PaymentAllocation:
    return PaymentAllocation(
        payment_id=payment_id,
        bill_id=bill_id,
        allocated_amount=Money(Decimal(amount)),
    )


def make_deposit(agreement_id, tenant_id, amount="50000") -> Deposit:
    return Deposit(
        agreement_id=agreement_id,
        tenant_id=tenant_id,
        amount=Money(Decimal(amount)),
        received_date=date(2026, 1, 1),
    )


def make_deduction(amount, reason="Damage") -> DepositDeduction:
    return DepositDeduction(amount=Money(Decimal(amount)), reason=reason)


def make_settlement(deposit_id, settlement_date=date(2026, 12, 31), deductions=None) -> DepositSettlement:
    settlement = DepositSettlement(deposit_id=deposit_id, settlement_date=settlement_date)
    for d in deductions or []:
        settlement.add_deduction(d)
    return settlement


def make_expense(property_id, amount="5000", category=ExpenseCategory.ELECTRICAL) -> Expense:
    return Expense(
        property_id=property_id,
        expense_date=date(2026, 2, 15),
        category=category,
        amount=Money(Decimal(amount)),
    )


def seed_core_chain(repos) -> dict:
    """Persist owner -> property -> rental space -> tenant -> agreement."""
    owner = repos.owner.add(make_owner())
    prop = repos.property.add(make_property(owner.id))
    space = repos.rental_space.add(make_space(prop.id))
    tenant = repos.tenant.add(make_tenant())
    agreement = repos.agreement.add(make_agreement(tenant.id, space.id))
    return {
        "owner": owner,
        "property": prop,
        "space": space,
        "tenant": tenant,
        "agreement": agreement,
    }
