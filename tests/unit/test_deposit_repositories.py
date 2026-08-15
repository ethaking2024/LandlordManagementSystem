from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from app.domain import Deposit, DepositDeduction, DepositSettlement, DepositStatus
from app.domain.value_objects import Money
from app.infrastructure.persistence.models import (
    DepositModel,
    DepositSettlementModel,
)
from app.infrastructure.repositories import DepositRepository, DepositSettlementRepository


def _deposit(status: DepositStatus = DepositStatus.HELD) -> Deposit:
    return Deposit(
        agreement_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        amount=Money(Decimal("50000")),
        received_date=date(2026, 1, 5),
        status=status,
    )


def _settlement() -> DepositSettlement:
    settlement = DepositSettlement(deposit_id=uuid.uuid4(), settlement_date=date(2026, 6, 30))
    settlement.add_deduction(DepositDeduction(amount=Money(Decimal("10000")), reason="Damage"))
    return settlement


class TestDepositRepository:
    @pytest.fixture
    def mock_session(self) -> MagicMock:
        return MagicMock(spec=Session)

    @pytest.fixture
    def repository(self, mock_session: MagicMock) -> DepositRepository:
        return DepositRepository(mock_session)

    def test_add(self, repository: DepositRepository, mock_session: MagicMock) -> None:
        deposit = _deposit()
        mock_model = MagicMock(spec=DepositModel)
        with patch.object(repository, "_to_model", return_value=mock_model), patch.object(
            repository, "_to_entity", return_value=deposit
        ):
            result = repository.add(deposit)
            assert result is deposit
            mock_session.add.assert_called_once()
            mock_session.flush.assert_called_once()

    def test_get(self, repository: DepositRepository, mock_session: MagicMock) -> None:
        mock_session.get.return_value = None
        result = repository.get(uuid.uuid4())
        assert result is None
        mock_session.get.assert_called_once()

    def test_get_by_agreement(self, repository: DepositRepository, mock_session: MagicMock) -> None:
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_session.scalars.return_value = mock_scalars

        result = repository.get_by_agreement(uuid.uuid4())

        assert result == []
        mock_session.scalars.assert_called_once()

    def test_get_by_tenant(self, repository: DepositRepository, mock_session: MagicMock) -> None:
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_session.scalars.return_value = mock_scalars

        result = repository.get_by_tenant(uuid.uuid4())

        assert result == []
        mock_session.scalars.assert_called_once()

    def test_get_by_status(self, repository: DepositRepository, mock_session: MagicMock) -> None:
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_session.scalars.return_value = mock_scalars

        result = repository.get_by_status(DepositStatus.SETTLED)

        assert result == []
        mock_session.scalars.assert_called_once()

    def test_get_held_by_agreement(self, repository: DepositRepository, mock_session: MagicMock) -> None:
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_session.scalars.return_value = mock_scalars

        result = repository.get_held_by_agreement(uuid.uuid4())

        assert result == []
        mock_session.scalars.assert_called_once()

    def test_update(self, repository: DepositRepository, mock_session: MagicMock) -> None:
        deposit = _deposit(DepositStatus.SETTLED)
        mock_model = MagicMock(spec=DepositModel)
        mock_session.get.return_value = mock_model
        with patch.object(repository, "_to_entity", return_value=deposit):
            result = repository.update(deposit)
            assert result is deposit
            mock_session.flush.assert_called_once()

    def test_delete(self, repository: DepositRepository, mock_session: MagicMock) -> None:
        mock_session.get.return_value = None
        result = repository.delete(uuid.uuid4())
        assert result is False

    def test_delete_existing(self, repository: DepositRepository, mock_session: MagicMock) -> None:
        mock_model = MagicMock(spec=DepositModel)
        mock_session.get.return_value = mock_model

        result = repository.delete(uuid.uuid4())

        assert result is True
        mock_session.delete.assert_called_once_with(mock_model)
        mock_session.flush.assert_called_once()

    def test_to_model_round_trip(self, repository: DepositRepository) -> None:
        deposit = _deposit(DepositStatus.HELD)
        model = repository._to_model(deposit)
        assert model.amount == Decimal("50000.00")
        assert model.status == "held"
        assert model.agreement_id == deposit.agreement_id
        assert model.tenant_id == deposit.tenant_id


class TestDepositSettlementRepository:
    @pytest.fixture
    def mock_session(self) -> MagicMock:
        return MagicMock(spec=Session)

    @pytest.fixture
    def repository(self, mock_session: MagicMock) -> DepositSettlementRepository:
        return DepositSettlementRepository(mock_session)

    def test_add(self, repository: DepositSettlementRepository, mock_session: MagicMock) -> None:
        settlement = _settlement()
        mock_model = MagicMock(spec=DepositSettlementModel)
        with patch.object(repository, "_to_model", return_value=mock_model), patch.object(
            repository, "_to_entity", return_value=settlement
        ):
            result = repository.add(settlement)
            assert result is settlement
            mock_session.add.assert_called_once()
            mock_session.flush.assert_called_once()

    def test_get(self, repository: DepositSettlementRepository, mock_session: MagicMock) -> None:
        mock_session.get.return_value = None
        result = repository.get(uuid.uuid4())
        assert result is None
        mock_session.get.assert_called_once()

    def test_get_by_deposit(self, repository: DepositSettlementRepository, mock_session: MagicMock) -> None:
        mock_session.scalar.return_value = None
        result = repository.get_by_deposit(uuid.uuid4())
        assert result is None
        mock_session.scalar.assert_called_once()

    def test_has_settlement_for_deposit_false(self, repository: DepositSettlementRepository, mock_session: MagicMock) -> None:
        mock_session.scalar.return_value = None
        result = repository.has_settlement_for_deposit(uuid.uuid4())
        assert result is False

    def test_has_settlement_for_deposit_true(self, repository: DepositSettlementRepository, mock_session: MagicMock) -> None:
        mock_session.scalar.return_value = uuid.uuid4()
        result = repository.has_settlement_for_deposit(uuid.uuid4())
        assert result is True

    def test_update(self, repository: DepositSettlementRepository, mock_session: MagicMock) -> None:
        settlement = _settlement()
        settlement.record_refund(Money(Decimal("40000")))
        mock_model = MagicMock(spec=DepositSettlementModel)
        mock_session.get.return_value = mock_model
        with patch.object(repository, "_to_entity", return_value=settlement):
            result = repository.update(settlement)
            assert result is settlement
            mock_session.flush.assert_called_once()

    def test_delete(self, repository: DepositSettlementRepository, mock_session: MagicMock) -> None:
        mock_session.get.return_value = None
        result = repository.delete(uuid.uuid4())
        assert result is False

    def test_delete_existing(self, repository: DepositSettlementRepository, mock_session: MagicMock) -> None:
        mock_model = MagicMock(spec=DepositSettlementModel)
        mock_session.get.return_value = mock_model

        result = repository.delete(uuid.uuid4())

        assert result is True
        mock_session.delete.assert_called_once_with(mock_model)
        mock_session.flush.assert_called_once()

    def test_to_model_with_deductions(self, repository: DepositSettlementRepository) -> None:
        settlement = _settlement()
        model = repository._to_model(settlement)
        assert model.deposit_id == settlement.deposit_id
        assert model.refund_amount is None
        assert len(model.deductions) == 1
        assert model.deductions[0].amount == Decimal("10000.00")
        assert model.deductions[0].reason == "Damage"

    def test_to_model_round_trip(self, repository: DepositSettlementRepository) -> None:
        settlement = _settlement()
        model = repository._to_model(settlement)
        entity = repository._to_entity(model)
        assert entity.total_deductions.amount == Decimal("10000.00")
        assert entity.is_complete is False
