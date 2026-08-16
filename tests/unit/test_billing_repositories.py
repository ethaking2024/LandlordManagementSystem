from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from app.domain import Bill, BillCategory, BillingPeriod, BillLine, BillStatus
from app.domain.value_objects import Money
from app.infrastructure.persistence.models import BillModel
from app.infrastructure.repositories import BillRepository


def _bill(status: BillStatus = BillStatus.DRAFT) -> Bill:
    period = BillingPeriod(date(2026, 1, 1), date(2026, 1, 31))
    bill = Bill(
        agreement_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        rental_space_id=uuid.uuid4(),
        period=period,
        billing_date=date(2026, 1, 31),
        status=status,
        lines=[
            BillLine(category=BillCategory.RENT, description="rent", amount=Money(Decimal("20000"))),
        ],
    )
    return bill


class TestBillRepository:
    @pytest.fixture
    def mock_session(self) -> MagicMock:
        return MagicMock(spec=Session)

    @pytest.fixture
    def repository(self, mock_session: MagicMock) -> BillRepository:
        return BillRepository(mock_session)

    def test_add(self, repository: BillRepository, mock_session: MagicMock) -> None:
        bill = _bill()
        mock_model = MagicMock(spec=BillModel)
        with patch.object(repository, "_to_model", return_value=mock_model), patch.object(
            repository, "_to_entity", return_value=bill
        ):
            result = repository.add(bill)
            assert result is bill
            mock_session.add.assert_called_once()
            mock_session.flush.assert_called_once()

    def test_get(self, repository: BillRepository, mock_session: MagicMock) -> None:
        mock_session.get.return_value = None
        result = repository.get(uuid.uuid4())
        assert result is None
        mock_session.get.assert_called_once()

    def test_get_by_agreement(self, repository: BillRepository, mock_session: MagicMock) -> None:
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_session.scalars.return_value = mock_scalars

        result = repository.get_by_agreement(uuid.uuid4())

        assert result == []
        mock_session.scalars.assert_called_once()

    def test_get_by_tenant(self, repository: BillRepository, mock_session: MagicMock) -> None:
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_session.scalars.return_value = mock_scalars

        result = repository.get_by_tenant(uuid.uuid4())

        assert result == []
        mock_session.scalars.assert_called_once()

    def test_get_by_agreement_and_period(self, repository: BillRepository, mock_session: MagicMock) -> None:
        mock_session.scalar.return_value = None
        result = repository.get_by_agreement_and_period(uuid.uuid4(), date(2026, 1, 1), date(2026, 1, 31))
        assert result is None
        mock_session.scalar.assert_called_once()

    def test_has_bill_for_period_false(self, repository: BillRepository, mock_session: MagicMock) -> None:
        mock_session.scalar.return_value = None
        result = repository.has_bill_for_period(uuid.uuid4(), date(2026, 1, 1), date(2026, 1, 31))
        assert result is False

    def test_has_bill_for_period_true(self, repository: BillRepository, mock_session: MagicMock) -> None:
        mock_session.scalar.return_value = uuid.uuid4()
        result = repository.has_bill_for_period(uuid.uuid4(), date(2026, 1, 1), date(2026, 1, 31))
        assert result is True

    def test_get_by_status(self, repository: BillRepository, mock_session: MagicMock) -> None:
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_session.scalars.return_value = mock_scalars

        result = repository.get_by_status(BillStatus.DRAFT)

        assert result == []
        mock_session.scalars.assert_called_once()

    def test_get_by_billing_date_range(self, repository: BillRepository, mock_session: MagicMock) -> None:
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_session.scalars.return_value = mock_scalars

        result = repository.get_by_billing_date_range(date(2026, 1, 1), date(2026, 1, 31))

        assert result == []
        mock_session.scalars.assert_called_once()

    def test_update(self, repository: BillRepository, mock_session: MagicMock) -> None:
        bill = _bill(BillStatus.CONFIRMED)
        mock_model = MagicMock(spec=BillModel)
        mock_session.get.return_value = mock_model
        with patch.object(repository, "_to_entity", return_value=bill):
            result = repository.update(bill)
            assert result is bill
            mock_session.flush.assert_called_once()

    def test_delete(self, repository: BillRepository, mock_session: MagicMock) -> None:
        mock_session.get.return_value = None
        result = repository.delete(uuid.uuid4())
        assert result is False

    def test_delete_existing(self, repository: BillRepository, mock_session: MagicMock) -> None:
        mock_model = MagicMock(spec=BillModel)
        mock_session.get.return_value = mock_model

        result = repository.delete(uuid.uuid4())

        assert result is True
        mock_session.delete.assert_called_once_with(mock_model)
        mock_session.flush.assert_called_once()

    def test_line_to_model_snapshot_fields(self, repository: BillRepository) -> None:
        line = BillLine(
            category=BillCategory.ELECTRICITY,
            description="Metered electricity",
            quantity=Decimal("100"),
            unit_rate=Money(Decimal("12")),
            amount=Money(Decimal("1200")),
            config_type="metered",
            meter_id=uuid.uuid4(),
            meter_identifier="EL-001",
            previous_reading=Decimal("1000"),
            current_reading=Decimal("1100"),
            consumption=Decimal("100"),
            tariff_rate=Money(Decimal("12")),
            tariff_effective_from=date(2026, 1, 1),
        )
        model = repository._line_to_model(line, uuid.uuid4())
        assert model.category == "electricity"
        assert model.quantity == Decimal("100")
        assert model.consumption == Decimal("100")
        assert model.meter_identifier == "EL-001"
        assert model.tariff_rate == Decimal("12")
