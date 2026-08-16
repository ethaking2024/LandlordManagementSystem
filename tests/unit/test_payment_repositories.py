from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from app.domain import Payment, PaymentAllocation, PaymentMethod, PaymentStatus
from app.domain.value_objects import Money
from app.infrastructure.persistence.models import PaymentAllocationModel, PaymentModel
from app.infrastructure.repositories import PaymentAllocationRepository, PaymentRepository


def _payment(status: PaymentStatus = PaymentStatus.RECORDED) -> Payment:
    return Payment(
        tenant_id=uuid.uuid4(),
        payment_date=date(2026, 1, 10),
        amount=Money(Decimal("8000")),
        payment_method=PaymentMethod.CASH,
        status=status,
    )


def _allocation() -> PaymentAllocation:
    return PaymentAllocation(
        payment_id=uuid.uuid4(),
        bill_id=uuid.uuid4(),
        allocated_amount=Money(Decimal("5000")),
    )


class TestPaymentRepository:
    @pytest.fixture
    def mock_session(self) -> MagicMock:
        return MagicMock(spec=Session)

    @pytest.fixture
    def repository(self, mock_session: MagicMock) -> PaymentRepository:
        return PaymentRepository(mock_session)

    def test_add(self, repository: PaymentRepository, mock_session: MagicMock) -> None:
        payment = _payment()
        mock_model = MagicMock(spec=PaymentModel)
        with patch.object(repository, "_to_model", return_value=mock_model), patch.object(
            repository, "_to_entity", return_value=payment
        ):
            result = repository.add(payment)
            assert result is payment
            mock_session.add.assert_called_once()
            mock_session.flush.assert_called_once()

    def test_get(self, repository: PaymentRepository, mock_session: MagicMock) -> None:
        mock_session.get.return_value = None
        result = repository.get(uuid.uuid4())
        assert result is None
        mock_session.get.assert_called_once()

    def test_get_by_tenant(self, repository: PaymentRepository, mock_session: MagicMock) -> None:
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_session.scalars.return_value = mock_scalars

        result = repository.get_by_tenant(uuid.uuid4())

        assert result == []
        mock_session.scalars.assert_called_once()

    def test_get_by_status(self, repository: PaymentRepository, mock_session: MagicMock) -> None:
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_session.scalars.return_value = mock_scalars

        result = repository.get_by_status(PaymentStatus.VOID)

        assert result == []
        mock_session.scalars.assert_called_once()

    def test_get_by_date_range(self, repository: PaymentRepository, mock_session: MagicMock) -> None:
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_session.scalars.return_value = mock_scalars

        result = repository.get_by_date_range(date(2026, 1, 1), date(2026, 1, 31))

        assert result == []
        mock_session.scalars.assert_called_once()

    def test_update(self, repository: PaymentRepository, mock_session: MagicMock) -> None:
        payment = _payment(PaymentStatus.VOID)
        mock_model = MagicMock(spec=PaymentModel)
        mock_session.get.return_value = mock_model
        with patch.object(repository, "_to_entity", return_value=payment):
            result = repository.update(payment)
            assert result is payment
            mock_session.flush.assert_called_once()

    def test_delete(self, repository: PaymentRepository, mock_session: MagicMock) -> None:
        mock_session.get.return_value = None
        result = repository.delete(uuid.uuid4())
        assert result is False

    def test_delete_existing(self, repository: PaymentRepository, mock_session: MagicMock) -> None:
        mock_model = MagicMock(spec=PaymentModel)
        mock_session.get.return_value = mock_model

        result = repository.delete(uuid.uuid4())

        assert result is True
        mock_session.delete.assert_called_once_with(mock_model)
        mock_session.flush.assert_called_once()

    def test_to_model_round_trip(self, repository: PaymentRepository) -> None:
        payment = _payment(PaymentStatus.RECORDED)
        model = repository._to_model(payment)
        assert model.amount == Decimal("8000.00")
        assert model.payment_method == "cash"
        assert model.status == "recorded"


class TestPaymentAllocationRepository:
    @pytest.fixture
    def mock_session(self) -> MagicMock:
        return MagicMock(spec=Session)

    @pytest.fixture
    def repository(self, mock_session: MagicMock) -> PaymentAllocationRepository:
        return PaymentAllocationRepository(mock_session)

    def test_add(self, repository: PaymentAllocationRepository, mock_session: MagicMock) -> None:
        allocation = _allocation()
        mock_model = MagicMock(spec=PaymentAllocationModel)
        with patch.object(repository, "_to_model", return_value=mock_model), patch.object(
            repository, "_to_entity", return_value=allocation
        ):
            result = repository.add(allocation)
            assert result is allocation
            mock_session.add.assert_called_once()
            mock_session.flush.assert_called_once()

    def test_get_by_payment(self, repository: PaymentAllocationRepository, mock_session: MagicMock) -> None:
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_session.scalars.return_value = mock_scalars

        result = repository.get_by_payment(uuid.uuid4())

        assert result == []
        mock_session.scalars.assert_called_once()

    def test_get_by_bill(self, repository: PaymentAllocationRepository, mock_session: MagicMock) -> None:
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_session.scalars.return_value = mock_scalars

        result = repository.get_by_bill(uuid.uuid4())

        assert result == []
        mock_session.scalars.assert_called_once()

    def test_get_valid_by_bill(self, repository: PaymentAllocationRepository, mock_session: MagicMock) -> None:
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_session.scalars.return_value = mock_scalars

        result = repository.get_valid_by_bill(uuid.uuid4())

        assert result == []
        mock_session.scalars.assert_called_once()

    def test_has_allocation_for_false(self, repository: PaymentAllocationRepository, mock_session: MagicMock) -> None:
        mock_session.scalar.return_value = None
        result = repository.has_allocation_for(uuid.uuid4(), uuid.uuid4())
        assert result is False

    def test_has_allocation_for_true(self, repository: PaymentAllocationRepository, mock_session: MagicMock) -> None:
        mock_session.scalar.return_value = uuid.uuid4()
        result = repository.has_allocation_for(uuid.uuid4(), uuid.uuid4())
        assert result is True

    def test_to_model_round_trip(self, repository: PaymentAllocationRepository) -> None:
        allocation = _allocation()
        model = repository._to_model(allocation)
        assert model.allocated_amount == Decimal("5000.00")
        assert model.payment_id == allocation.payment_id
        assert model.bill_id == allocation.bill_id
