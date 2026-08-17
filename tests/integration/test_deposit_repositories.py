from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.domain.enums import DepositStatus
from app.infrastructure.persistence.models import (
    DepositDeductionModel,
    DepositModel,
    DepositSettlementModel,
)
from tests.integration.factories import (
    make_deduction,
    make_deposit,
    make_settlement,
    seed_core_chain,
)


@pytest.mark.integration
def test_deposit_roundtrip(repositories):
    core = seed_core_chain(repositories)
    deposit = repositories.deposit.add(make_deposit(core["agreement"].id, core["tenant"].id, "50000"))

    fetched = repositories.deposit.get(deposit.id)
    assert fetched.amount.amount == Decimal("50000.00")
    assert fetched.status == DepositStatus.HELD

    held = repositories.deposit.get_held_by_agreement(core["agreement"].id)
    assert [d.id for d in held] == [deposit.id]


@pytest.mark.integration
def test_settlement_with_deductions_roundtrip(session, repositories):
    core = seed_core_chain(repositories)
    deposit = repositories.deposit.add(make_deposit(core["agreement"].id, core["tenant"].id, "50000"))
    settlement = make_settlement(deposit.id, date(2026, 12, 31), [make_deduction("5000")])
    saved = repositories.deposit_settlement.add(settlement)

    fetched = repositories.deposit_settlement.get(saved.id)
    assert fetched.settlement_date == date(2026, 12, 31)
    assert fetched.total_deductions.amount == Decimal("5000.00")
    assert fetched.refund_amount is None

    assert repositories.deposit_settlement.has_settlement_for_deposit(deposit.id) is True

    deduction_count = session.scalar(
        select(func.count()).select_from(DepositDeductionModel).where(
            DepositDeductionModel.settlement_id == saved.id
        )
    )
    assert deduction_count == 1


@pytest.mark.integration
def test_one_settlement_per_deposit_unique(session, repositories):
    core = seed_core_chain(repositories)
    deposit = repositories.deposit.add(make_deposit(core["agreement"].id, core["tenant"].id, "50000"))
    repositories.deposit_settlement.add(make_settlement(deposit.id, date(2026, 12, 31)))

    duplicate = DepositSettlementModel(deposit_id=deposit.id, settlement_date=date(2026, 12, 31))
    session.add(duplicate)
    with pytest.raises(IntegrityError):
        session.flush()


@pytest.mark.integration
def test_negative_refund_rejected_by_check(session, repositories):
    core = seed_core_chain(repositories)
    deposit = repositories.deposit.add(make_deposit(core["agreement"].id, core["tenant"].id, "50000"))

    bad = DepositSettlementModel(
        deposit_id=deposit.id,
        settlement_date=date(2026, 12, 31),
        refund_amount=Decimal("-1"),
    )
    session.add(bad)
    with pytest.raises(IntegrityError):
        session.flush()


@pytest.mark.integration
def test_non_positive_deposit_amount_rejected_by_check(session, repositories):
    core = seed_core_chain(repositories)
    bad = DepositModel(
        agreement_id=core["agreement"].id,
        tenant_id=core["tenant"].id,
        amount=Decimal("0"),
        received_date=date(2026, 1, 1),
        status="held",
    )
    session.add(bad)
    with pytest.raises(IntegrityError):
        session.flush()


@pytest.mark.integration
def test_delete_settlement_cascades_to_deductions_at_db_level(database, repositories, session):
    core = seed_core_chain(repositories)
    deposit = repositories.deposit.add(make_deposit(core["agreement"].id, core["tenant"].id, "50000"))
    settlement = make_settlement(deposit.id, date(2026, 12, 31), [make_deduction("5000")])
    saved = repositories.deposit_settlement.add(settlement)
    session.commit()

    # The migration defines deposit_deductions.settlement_id ON DELETE CASCADE.
    # Deleting the settlement at the database level must remove its deductions.
    from sqlalchemy import text

    with database.engine.begin() as conn:
        conn.execute(text("DELETE FROM deposit_settlements WHERE id = :id"), {"id": saved.id})

    remaining = session.scalar(
        select(func.count()).select_from(DepositDeductionModel).where(
            DepositDeductionModel.settlement_id == saved.id
        )
    )
    assert remaining == 0
