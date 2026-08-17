from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.domain.enums import ExpenseStatus
from app.infrastructure.persistence.models import ExpenseModel
from tests.integration.factories import make_expense, seed_core_chain


@pytest.mark.integration
def test_expense_roundtrip(repositories):
    core = seed_core_chain(repositories)
    expense = repositories.expense.add(make_expense(core["property"].id, "5000"))

    fetched = repositories.expense.get(expense.id)
    assert fetched.amount.amount == Decimal("5000.00")
    assert fetched.expense_date == date(2026, 2, 15)
    assert fetched.status == ExpenseStatus.RECORDED

    by_property = repositories.expense.get_recorded_by_property(core["property"].id)
    assert [e.id for e in by_property] == [expense.id]


@pytest.mark.integration
def test_non_positive_expense_amount_rejected_by_check(session, repositories):
    core = seed_core_chain(repositories)
    bad = ExpenseModel(
        property_id=core["property"].id,
        expense_date=date(2026, 2, 15),
        category="electrical",
        amount=Decimal("0"),
        status="recorded",
    )
    session.add(bad)
    with pytest.raises(IntegrityError):
        session.flush()


@pytest.mark.integration
def test_invalid_expense_category_rejected_by_check(session, repositories):
    core = seed_core_chain(repositories)
    bad = ExpenseModel(
        property_id=core["property"].id,
        expense_date=date(2026, 2, 15),
        category="travel",
        amount=Decimal("100"),
        status="recorded",
    )
    session.add(bad)
    with pytest.raises(IntegrityError):
        session.flush()


@pytest.mark.integration
def test_delete_property_blocked_when_expenses_exist(repositories):
    core = seed_core_chain(repositories)
    repositories.expense.add(make_expense(core["property"].id, "5000"))

    with pytest.raises(IntegrityError):
        repositories.property.delete(core["property"].id)
