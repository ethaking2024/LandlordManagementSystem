from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from app.domain import Expense, ExpenseCategory, ExpenseStatus
from app.domain.value_objects import Money
from app.infrastructure.persistence.models import ExpenseModel
from app.infrastructure.repositories import ExpenseRepository


def _expense(status: ExpenseStatus = ExpenseStatus.RECORDED) -> Expense:
    return Expense(
        property_id=uuid.uuid4(),
        rental_space_id=uuid.uuid4(),
        expense_date=date(2026, 3, 10),
        category=ExpenseCategory.PLUMBING,
        amount=Money(Decimal("3500")),
        status=status,
    )


class TestExpenseRepository:
    @pytest.fixture
    def mock_session(self) -> MagicMock:
        return MagicMock(spec=Session)

    @pytest.fixture
    def repository(self, mock_session: MagicMock) -> ExpenseRepository:
        return ExpenseRepository(mock_session)

    def test_add(self, repository: ExpenseRepository, mock_session: MagicMock) -> None:
        expense = _expense()
        mock_model = MagicMock(spec=ExpenseModel)
        with patch.object(repository, "_to_model", return_value=mock_model), patch.object(
            repository, "_to_entity", return_value=expense
        ):
            result = repository.add(expense)
            assert result is expense
            mock_session.add.assert_called_once()
            mock_session.flush.assert_called_once()

    def test_get(self, repository: ExpenseRepository, mock_session: MagicMock) -> None:
        mock_session.get.return_value = None
        result = repository.get(uuid.uuid4())
        assert result is None
        mock_session.get.assert_called_once()

    def test_get_by_property(self, repository: ExpenseRepository, mock_session: MagicMock) -> None:
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_session.scalars.return_value = mock_scalars

        result = repository.get_by_property(uuid.uuid4())

        assert result == []
        mock_session.scalars.assert_called_once()

    def test_get_by_rental_space(self, repository: ExpenseRepository, mock_session: MagicMock) -> None:
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_session.scalars.return_value = mock_scalars

        result = repository.get_by_rental_space(uuid.uuid4())

        assert result == []
        mock_session.scalars.assert_called_once()

    def test_get_by_category(self, repository: ExpenseRepository, mock_session: MagicMock) -> None:
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_session.scalars.return_value = mock_scalars

        result = repository.get_by_category(ExpenseCategory.TAX)

        assert result == []
        mock_session.scalars.assert_called_once()

    def test_get_by_status(self, repository: ExpenseRepository, mock_session: MagicMock) -> None:
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_session.scalars.return_value = mock_scalars

        result = repository.get_by_status(ExpenseStatus.VOID)

        assert result == []
        mock_session.scalars.assert_called_once()

    def test_get_recorded_by_property(self, repository: ExpenseRepository, mock_session: MagicMock) -> None:
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_session.scalars.return_value = mock_scalars

        result = repository.get_recorded_by_property(uuid.uuid4())

        assert result == []
        mock_session.scalars.assert_called_once()

    def test_get_recorded_by_rental_space(self, repository: ExpenseRepository, mock_session: MagicMock) -> None:
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_session.scalars.return_value = mock_scalars

        result = repository.get_recorded_by_rental_space(uuid.uuid4())

        assert result == []
        mock_session.scalars.assert_called_once()

    def test_update(self, repository: ExpenseRepository, mock_session: MagicMock) -> None:
        expense = _expense(ExpenseStatus.VOID)
        mock_model = MagicMock(spec=ExpenseModel)
        mock_session.get.return_value = mock_model
        with patch.object(repository, "_to_entity", return_value=expense):
            result = repository.update(expense)
            assert result is expense
            mock_session.flush.assert_called_once()

    def test_delete(self, repository: ExpenseRepository, mock_session: MagicMock) -> None:
        mock_session.get.return_value = None
        result = repository.delete(uuid.uuid4())
        assert result is False

    def test_delete_existing(self, repository: ExpenseRepository, mock_session: MagicMock) -> None:
        mock_model = MagicMock(spec=ExpenseModel)
        mock_session.get.return_value = mock_model

        result = repository.delete(uuid.uuid4())

        assert result is True
        mock_session.delete.assert_called_once_with(mock_model)
        mock_session.flush.assert_called_once()

    def test_to_model_round_trip(self, repository: ExpenseRepository) -> None:
        expense = _expense(ExpenseStatus.RECORDED)
        model = repository._to_model(expense)
        assert model.amount == Decimal("3500.00")
        assert model.category == "plumbing"
        assert model.status == "recorded"
        assert model.property_id == expense.property_id
        assert model.rental_space_id == expense.rental_space_id

    def test_to_entity_round_trip(self, repository: ExpenseRepository) -> None:
        expense = _expense(ExpenseStatus.RECORDED)
        model = repository._to_model(expense)
        entity = repository._to_entity(model)
        assert entity.amount.amount == Decimal("3500.00")
        assert entity.category == ExpenseCategory.PLUMBING
        assert entity.status == ExpenseStatus.RECORDED
