from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.domain.enums import BillStatus
from app.infrastructure.persistence.models import BillLineModel, BillModel
from tests.integration.factories import make_bill, make_rent_line, seed_core_chain


@pytest.mark.integration
def test_bill_with_lines_roundtrip(repositories):
    core = seed_core_chain(repositories)
    bill = make_bill(core["agreement"].id, core["tenant"].id, core["space"].id)
    bill.add_line(make_rent_line("25000"))
    saved = repositories.bill.add(bill)

    fetched = repositories.bill.get(saved.id)
    assert fetched.status == BillStatus.DRAFT
    assert len(fetched.lines) == 1
    assert fetched.lines[0].category.value == "rent"
    assert fetched.lines[0].amount.amount == Decimal("25000.00")
    assert fetched.total.amount == Decimal("25000.00")


@pytest.mark.integration
def test_bill_get_by_status_and_period(repositories):
    core = seed_core_chain(repositories)
    bill = make_bill(core["agreement"].id, core["tenant"].id, core["space"].id)
    bill.add_line(make_rent_line("25000"))
    bill.confirm()
    saved = repositories.bill.add(bill)

    confirmed = repositories.bill.get_by_status(BillStatus.CONFIRMED)
    assert [b.id for b in confirmed] == [saved.id]

    assert repositories.bill.has_bill_for_period(
        core["agreement"].id, date(2026, 1, 1), date(2026, 1, 31)
    )
    by_period = repositories.bill.get_by_agreement_and_period(
        core["agreement"].id, date(2026, 1, 1), date(2026, 1, 31)
    )
    assert by_period is not None
    assert by_period.id == saved.id


@pytest.mark.integration
def test_duplicate_bill_period_rejected(session, repositories):
    core = seed_core_chain(repositories)
    bill = make_bill(core["agreement"].id, core["tenant"].id, core["space"].id)
    bill.add_line(make_rent_line("25000"))
    repositories.bill.add(bill)

    duplicate = BillModel(
        agreement_id=core["agreement"].id,
        tenant_id=core["tenant"].id,
        rental_space_id=core["space"].id,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 1, 31),
        billing_date=date(2026, 1, 31),
        status="draft",
        total_amount=Decimal("25000"),
    )
    session.add(duplicate)
    with pytest.raises(IntegrityError):
        session.flush()


@pytest.mark.integration
def test_invalid_bill_status_rejected_by_check(session, repositories):
    core = seed_core_chain(repositories)
    bad = BillModel(
        agreement_id=core["agreement"].id,
        tenant_id=core["tenant"].id,
        rental_space_id=core["space"].id,
        period_start=date(2026, 1, 1),
        period_end=date(2026, 1, 31),
        billing_date=date(2026, 1, 31),
        status="bogus",
        total_amount=Decimal("0"),
    )
    session.add(bad)
    with pytest.raises(IntegrityError):
        session.flush()


@pytest.mark.integration
def test_bill_delete_cascades_to_bill_lines(session, repositories):
    core = seed_core_chain(repositories)
    bill = make_bill(core["agreement"].id, core["tenant"].id, core["space"].id)
    bill.add_line(make_rent_line("25000"))
    bill.add_line(make_rent_line("500"))
    saved = repositories.bill.add(bill)

    count = session.scalar(select(func.count()).select_from(BillLineModel).where(BillLineModel.bill_id == saved.id))
    assert count == 2

    assert repositories.bill.delete(saved.id) is True
    session.expire_all()
    remaining = session.scalar(
        select(func.count()).select_from(BillLineModel).where(BillLineModel.bill_id == saved.id)
    )
    assert remaining == 0


@pytest.mark.integration
def test_delete_agreement_blocked_by_restrict_fk(repositories):
    core = seed_core_chain(repositories)
    bill = make_bill(core["agreement"].id, core["tenant"].id, core["space"].id)
    bill.add_line(make_rent_line("25000"))
    repositories.bill.add(bill)

    with pytest.raises(IntegrityError):
        repositories.agreement.delete(core["agreement"].id)
