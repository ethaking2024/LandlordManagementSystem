from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.infrastructure.persistence.models import PaymentAllocationModel, PaymentModel
from tests.integration.factories import (
    make_allocation,
    make_bill,
    make_payment,
    make_rent_line,
    seed_core_chain,
)


@pytest.mark.integration
def test_payment_roundtrip(repositories):
    core = seed_core_chain(repositories)
    payment = repositories.payment.add(make_payment(core["tenant"].id, "25000"))

    fetched = repositories.payment.get(payment.id)
    assert fetched.amount.amount == Decimal("25000.00")
    assert fetched.payment_date == date(2026, 1, 31)
    assert fetched.payment_method.value == "cash"


@pytest.mark.integration
def test_payment_allocation_roundtrip_and_unique(session, repositories):
    core = seed_core_chain(repositories)
    bill = make_bill(core["agreement"].id, core["tenant"].id, core["space"].id)
    bill.add_line(make_rent_line("25000"))
    repositories.bill.add(bill)
    payment = repositories.payment.add(make_payment(core["tenant"].id, "25000"))
    allocation = repositories.payment_allocation.add(make_allocation(payment.id, bill.id, "25000"))

    fetched = repositories.payment_allocation.get(allocation.id)
    assert fetched.allocated_amount.amount == Decimal("25000.00")
    assert repositories.payment_allocation.has_allocation_for(payment.id, bill.id)

    duplicate = PaymentAllocationModel(
        payment_id=payment.id,
        bill_id=bill.id,
        allocated_amount=Decimal("100"),
    )
    session.add(duplicate)
    with pytest.raises(IntegrityError):
        session.flush()


@pytest.mark.integration
def test_non_positive_payment_amount_rejected_by_check(session, repositories):
    core = seed_core_chain(repositories)
    bad = PaymentModel(
        tenant_id=core["tenant"].id,
        payment_date=date(2026, 1, 31),
        amount=Decimal("0"),
        payment_method="cash",
        status="recorded",
    )
    session.add(bad)
    with pytest.raises(IntegrityError):
        session.flush()


@pytest.mark.integration
def test_invalid_payment_status_rejected_by_check(session, repositories):
    core = seed_core_chain(repositories)
    bad = PaymentModel(
        tenant_id=core["tenant"].id,
        payment_date=date(2026, 1, 31),
        amount=Decimal("100"),
        payment_method="cash",
        status="bogus",
    )
    session.add(bad)
    with pytest.raises(IntegrityError):
        session.flush()


@pytest.mark.integration
def test_delete_payment_blocked_when_allocations_exist(repositories):
    core = seed_core_chain(repositories)
    bill = make_bill(core["agreement"].id, core["tenant"].id, core["space"].id)
    bill.add_line(make_rent_line("25000"))
    repositories.bill.add(bill)
    payment = repositories.payment.add(make_payment(core["tenant"].id, "25000"))
    repositories.payment_allocation.add(make_allocation(payment.id, bill.id, "25000"))

    with pytest.raises(IntegrityError):
        repositories.payment.delete(payment.id)
