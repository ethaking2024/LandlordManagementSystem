from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from app.domain.entities import Meter, UtilityConfig, UtilityTariff
from app.domain.enums import UtilityType
from app.domain.value_objects import Money
from app.infrastructure.persistence.models import (
    MeterModel,
    UtilityConfigModel,
    UtilityTariffModel,
)
from app.infrastructure.repositories import (
    MeterReadingRepository,
    MeterReplacementRepository,
    MeterRepository,
    UtilityConfigRepository,
    UtilityTariffRepository,
)


class TestUtilityConfigRepository:
    @pytest.fixture
    def mock_session(self) -> MagicMock:
        return MagicMock(spec=Session)

    @pytest.fixture
    def repository(self, mock_session: MagicMock) -> UtilityConfigRepository:
        return UtilityConfigRepository(mock_session)

    def test_add(self, repository: UtilityConfigRepository, mock_session: MagicMock) -> None:
        config = UtilityConfig(
            rental_space_id=uuid.uuid4(),
            utility_type=UtilityType.ELECTRICITY,
            config_type="metered",
        )
        mock_model = MagicMock(spec=UtilityConfigModel)
        mock_model.id = config.id
        mock_model.rental_space_id = config.rental_space_id
        mock_model.utility_type = "electricity"
        mock_model.config_type = "metered"
        mock_model.fixed_amount = None
        mock_model.created_at = None
        mock_model.updated_at = None
        with patch.object(repository, "_to_model", return_value=mock_model):
            _ = repository.add(config)
            mock_session.add.assert_called_once()
            mock_session.flush.assert_called_once()

    def test_get_by_rental_space(self, repository: UtilityConfigRepository, mock_session: MagicMock) -> None:
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_session.scalars.return_value = mock_scalars

        result = repository.get_by_rental_space(uuid.uuid4())

        assert result == []
        mock_session.scalars.assert_called_once()

    def test_get_by_rental_space_and_utility(self, repository: UtilityConfigRepository, mock_session: MagicMock) -> None:
        mock_session.scalar.return_value = None
        result = repository.get_by_rental_space_and_utility(uuid.uuid4(), UtilityType.ELECTRICITY)
        assert result is None
        mock_session.scalar.assert_called_once()


class TestMeterRepository:
    @pytest.fixture
    def mock_session(self) -> MagicMock:
        return MagicMock(spec=Session)

    @pytest.fixture
    def repository(self, mock_session: MagicMock) -> MeterRepository:
        return MeterRepository(mock_session)

    def test_get_by_rental_space(self, repository: MeterRepository, mock_session: MagicMock) -> None:
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_session.scalars.return_value = mock_scalars

        result = repository.get_by_rental_space(uuid.uuid4())

        assert result == []
        mock_session.scalars.assert_called_once()

    def test_get_active_meters(self, repository: MeterRepository, mock_session: MagicMock) -> None:
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_session.scalars.return_value = mock_scalars

        result = repository.get_active_meters(uuid.uuid4())

        assert result == []
        mock_session.scalars.assert_called_once()

    def test_get_by_identifier(self, repository: MeterRepository, mock_session: MagicMock) -> None:
        mock_session.scalar.return_value = None
        result = repository.get_by_identifier("MET-001")
        assert result is None
        mock_session.scalar.assert_called_once()

    def test_add(self, repository: MeterRepository, mock_session: MagicMock) -> None:
        meter = Meter(
            rental_space_id=uuid.uuid4(),
            utility_type=UtilityType.ELECTRICITY,
            identifier="MET-001",
            installation_date=date(2026, 1, 1),
        )
        mock_model = MagicMock(spec=MeterModel)
        mock_model.id = meter.id
        mock_model.rental_space_id = meter.rental_space_id
        mock_model.utility_type = "electricity"
        mock_model.identifier = "MET-001"
        mock_model.installation_date = date(2026, 1, 1)
        mock_model.is_active = True
        mock_model.notes = None
        mock_model.created_at = None
        mock_model.updated_at = None
        with patch.object(repository, "_to_model", return_value=mock_model):
            _ = repository.add(meter)
            mock_session.add.assert_called_once()
            mock_session.flush.assert_called_once()


class TestMeterReadingRepository:
    @pytest.fixture
    def mock_session(self) -> MagicMock:
        return MagicMock(spec=Session)

    @pytest.fixture
    def repository(self, mock_session: MagicMock) -> MeterReadingRepository:
        return MeterReadingRepository(mock_session)

    def test_get_by_meter(self, repository: MeterReadingRepository, mock_session: MagicMock) -> None:
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_session.scalars.return_value = mock_scalars

        result = repository.get_by_meter(uuid.uuid4())

        assert result == []
        mock_session.scalars.assert_called_once()

    def test_get_latest_reading(self, repository: MeterReadingRepository, mock_session: MagicMock) -> None:
        mock_session.scalar.return_value = None
        result = repository.get_latest_reading(uuid.uuid4())
        assert result is None
        mock_session.scalar.assert_called_once()

    def test_has_reading_on_date(self, repository: MeterReadingRepository, mock_session: MagicMock) -> None:
        mock_session.scalar.return_value = None
        result = repository.has_reading_on_date(uuid.uuid4(), date(2026, 1, 1))
        assert result is False
        mock_session.scalar.assert_called_once()

    def test_get_by_meter_between(self, repository: MeterReadingRepository, mock_session: MagicMock) -> None:
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_session.scalars.return_value = mock_scalars

        result = repository.get_by_meter_between(uuid.uuid4(), date(2026, 1, 1), date(2026, 12, 31))

        assert result == []
        mock_session.scalars.assert_called_once()


class TestUtilityTariffRepository:
    @pytest.fixture
    def mock_session(self) -> MagicMock:
        return MagicMock(spec=Session)

    @pytest.fixture
    def repository(self, mock_session: MagicMock) -> UtilityTariffRepository:
        return UtilityTariffRepository(mock_session)

    def test_add(self, repository: UtilityTariffRepository, mock_session: MagicMock) -> None:
        tariff = UtilityTariff(
            utility_type=UtilityType.ELECTRICITY,
            effective_from=date(2026, 1, 1),
            rate=Money(Decimal("12")),
        )
        mock_model = MagicMock(spec=UtilityTariffModel)
        mock_model.id = tariff.id
        mock_model.utility_type = "electricity"
        mock_model.effective_from = date(2026, 1, 1)
        mock_model.rate = Decimal("12")
        mock_model.notes = None
        mock_model.created_at = None
        mock_model.updated_at = None
        with patch.object(repository, "_to_model", return_value=mock_model):
            _ = repository.add(tariff)
            mock_session.add.assert_called_once()
            mock_session.flush.assert_called_once()

    def test_get_by_utility_type(self, repository: UtilityTariffRepository, mock_session: MagicMock) -> None:
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_session.scalars.return_value = mock_scalars

        result = repository.get_by_utility_type(UtilityType.ELECTRICITY)

        assert result == []
        mock_session.scalars.assert_called_once()

    def test_get_applicable_tariff(self, repository: UtilityTariffRepository, mock_session: MagicMock) -> None:
        mock_session.scalar.return_value = None
        result = repository.get_applicable_tariff(UtilityType.ELECTRICITY, date(2026, 6, 1))
        assert result is None
        mock_session.scalar.assert_called_once()

    def test_get_on_effective_date(self, repository: UtilityTariffRepository, mock_session: MagicMock) -> None:
        mock_session.scalar.return_value = None
        result = repository.get_on_effective_date(UtilityType.ELECTRICITY, date(2026, 1, 1))
        assert result is None
        mock_session.scalar.assert_called_once()


class TestMeterReplacementRepository:
    @pytest.fixture
    def mock_session(self) -> MagicMock:
        return MagicMock(spec=Session)

    @pytest.fixture
    def repository(self, mock_session: MagicMock) -> MeterReplacementRepository:
        return MeterReplacementRepository(mock_session)

    def test_get_by_old_meter(self, repository: MeterReplacementRepository, mock_session: MagicMock) -> None:
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_session.scalars.return_value = mock_scalars

        result = repository.get_by_old_meter(uuid.uuid4())

        assert result == []
        mock_session.scalars.assert_called_once()

    def test_get_by_new_meter(self, repository: MeterReplacementRepository, mock_session: MagicMock) -> None:
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_session.scalars.return_value = mock_scalars

        result = repository.get_by_new_meter(uuid.uuid4())

        assert result == []
        mock_session.scalars.assert_called_once()
