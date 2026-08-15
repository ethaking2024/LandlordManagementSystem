from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.application.services import (
    MeterReadingService,
    MeterReplacementService,
    MeterService,
    UtilityConfigService,
    UtilityTariffService,
)
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.domain.entities import (
    Meter,
    MeterReading,
    MeterReadingValue,
    MeterReplacement,
    UtilityConfig,
    UtilityTariff,
)
from app.domain.enums import UtilityType
from app.domain.value_objects import Money


class TestUtilityConfigService:
    @pytest.fixture
    def mock_repo(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def mock_rental_space_repo(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def service(
        self, mock_repo: MagicMock, mock_rental_space_repo: MagicMock
    ) -> UtilityConfigService:
        return UtilityConfigService(mock_repo, mock_rental_space_repo)

    def test_set_electricity_fixed(
        self, service: UtilityConfigService, mock_rental_space_repo: MagicMock, mock_repo: MagicMock
    ) -> None:
        mock_rental_space_repo.get.return_value = object()
        mock_repo.get_by_rental_space_and_utility.return_value = None
        mock_config = UtilityConfig(
            rental_space_id=uuid.uuid4(),
            utility_type=UtilityType.ELECTRICITY,
            config_type="fixed",
            fixed_amount=Money(Decimal("500")),
        )
        mock_repo.add.return_value = mock_config

        result = service.set_config(uuid.uuid4(), UtilityType.ELECTRICITY, "fixed", "500")

        assert result.config_type == "fixed"
        assert result.fixed_amount is not None
        mock_repo.add.assert_called_once()

    def test_set_electricity_metered(self, service: UtilityConfigService, mock_rental_space_repo: MagicMock, mock_repo: MagicMock) -> None:
        mock_rental_space_repo.get.return_value = object()
        mock_repo.get_by_rental_space_and_utility.return_value = None
        mock_config = UtilityConfig(
            rental_space_id=uuid.uuid4(),
            utility_type=UtilityType.ELECTRICITY,
            config_type="metered",
        )
        mock_repo.add.return_value = mock_config
        result = service.set_config(uuid.uuid4(), UtilityType.ELECTRICITY, "metered")
        assert result.config_type == "metered"

    def test_set_water_no_charge(self, service: UtilityConfigService, mock_rental_space_repo: MagicMock, mock_repo: MagicMock) -> None:
        mock_rental_space_repo.get.return_value = object()
        mock_repo.get_by_rental_space_and_utility.return_value = None
        mock_config = UtilityConfig(
            rental_space_id=uuid.uuid4(),
            utility_type=UtilityType.WATER,
            config_type="no_charge",
        )
        mock_repo.add.return_value = mock_config
        result = service.set_config(uuid.uuid4(), UtilityType.WATER, "no_charge")
        assert result.config_type == "no_charge"

    def test_set_water_fixed(self, service: UtilityConfigService, mock_rental_space_repo: MagicMock, mock_repo: MagicMock) -> None:
        mock_rental_space_repo.get.return_value = object()
        mock_repo.get_by_rental_space_and_utility.return_value = None
        mock_config = UtilityConfig(
            rental_space_id=uuid.uuid4(),
            utility_type=UtilityType.WATER,
            config_type="fixed",
            fixed_amount=Money(Decimal("300")),
        )
        mock_repo.add.return_value = mock_config
        result = service.set_config(uuid.uuid4(), UtilityType.WATER, "fixed", "300")
        assert result.config_type == "fixed"
        assert result.fixed_amount is not None

    def test_set_water_metered(self, service: UtilityConfigService, mock_rental_space_repo: MagicMock, mock_repo: MagicMock) -> None:
        mock_rental_space_repo.get.return_value = object()
        mock_repo.get_by_rental_space_and_utility.return_value = None
        mock_config = UtilityConfig(
            rental_space_id=uuid.uuid4(),
            utility_type=UtilityType.WATER,
            config_type="metered",
        )
        mock_repo.add.return_value = mock_config
        result = service.set_config(uuid.uuid4(), UtilityType.WATER, "metered")
        assert result.config_type == "metered"

    def test_rejects_missing_rental_space(self, service: UtilityConfigService, mock_rental_space_repo: MagicMock) -> None:
        mock_rental_space_repo.get.return_value = None
        with pytest.raises(NotFoundError):
            service.set_config(uuid.uuid4(), UtilityType.ELECTRICITY, "fixed", "500")

    def test_rejects_invalid_electricity_config(self, service: UtilityConfigService, mock_rental_space_repo: MagicMock) -> None:
        mock_rental_space_repo.get.return_value = object()
        with pytest.raises(ValidationError, match="Invalid electricity config type"):
            service.set_config(uuid.uuid4(), UtilityType.ELECTRICITY, "no_charge")

    def test_rejects_fixed_without_amount(self, service: UtilityConfigService, mock_rental_space_repo: MagicMock) -> None:
        mock_rental_space_repo.get.return_value = object()
        with pytest.raises(ValidationError, match="requires a fixed amount"):
            service.set_config(uuid.uuid4(), UtilityType.WATER, "fixed")

    def test_rejects_negative_fixed_amount(self, service: UtilityConfigService, mock_rental_space_repo: MagicMock) -> None:
        mock_rental_space_repo.get.return_value = object()
        with pytest.raises(ValidationError, match="Fixed amount cannot be negative"):
            service.set_config(uuid.uuid4(), UtilityType.WATER, "fixed", "-100")

    def test_updates_existing_config(
        self, service: UtilityConfigService, mock_rental_space_repo: MagicMock, mock_repo: MagicMock
    ) -> None:
        mock_rental_space_repo.get.return_value = object()
        existing = UtilityConfig(
            rental_space_id=uuid.uuid4(),
            utility_type=UtilityType.ELECTRICITY,
            config_type="metered",
        )
        mock_repo.get_by_rental_space_and_utility.return_value = existing
        mock_repo.update.return_value = existing

        result = service.set_config(existing.rental_space_id, UtilityType.ELECTRICITY, "fixed", "500")

        assert result.config_type == "fixed"
        mock_repo.update.assert_called_once()

    def test_get_config_not_found(self, service: UtilityConfigService, mock_repo: MagicMock) -> None:
        mock_repo.get_by_rental_space_and_utility.return_value = None
        with pytest.raises(NotFoundError):
            service.get_config(uuid.uuid4(), UtilityType.ELECTRICITY)


class TestMeterService:
    @pytest.fixture
    def mock_repo(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def mock_rental_space_repo(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def service(self, mock_repo: MagicMock, mock_rental_space_repo: MagicMock) -> MeterService:
        return MeterService(mock_repo, mock_rental_space_repo)

    def test_create_meter(self, service: MeterService, mock_rental_space_repo: MagicMock, mock_repo: MagicMock) -> None:
        mock_rental_space_repo.get.return_value = object()
        mock_repo.get_by_identifier.return_value = None
        mock_meter = Meter(
            rental_space_id=uuid.uuid4(),
            utility_type=UtilityType.ELECTRICITY,
            identifier="MET-001",
            installation_date=date(2026, 1, 1),
        )
        mock_repo.add.return_value = mock_meter

        result = service.create_meter(uuid.uuid4(), UtilityType.ELECTRICITY, "MET-001", date(2026, 1, 1))

        assert result.identifier == "MET-001"
        mock_repo.add.assert_called_once()

    def test_create_meter_rejects_missing_space(self, service: MeterService, mock_rental_space_repo: MagicMock) -> None:
        mock_rental_space_repo.get.return_value = None
        with pytest.raises(NotFoundError):
            service.create_meter(uuid.uuid4(), UtilityType.ELECTRICITY, "MET-001", date(2026, 1, 1))

    def test_create_meter_rejects_empty_identifier(self, service: MeterService, mock_rental_space_repo: MagicMock) -> None:
        mock_rental_space_repo.get.return_value = object()
        with pytest.raises(ValidationError, match="Meter identifier is required"):
            service.create_meter(uuid.uuid4(), UtilityType.ELECTRICITY, "", date(2026, 1, 1))

    def test_create_meter_rejects_duplicate_identifier(self, service: MeterService, mock_rental_space_repo: MagicMock, mock_repo: MagicMock) -> None:
        mock_rental_space_repo.get.return_value = object()
        mock_repo.get_by_identifier.return_value = Meter(
            rental_space_id=uuid.uuid4(),
            utility_type=UtilityType.ELECTRICITY,
            identifier="MET-001",
            installation_date=date(2026, 1, 1),
        )
        with pytest.raises(ConflictError, match="already exists"):
            service.create_meter(uuid.uuid4(), UtilityType.ELECTRICITY, "MET-001", date(2026, 1, 1))

    def test_deactivate_meter(self, service: MeterService, mock_repo: MagicMock) -> None:
        meter = Meter(
            rental_space_id=uuid.uuid4(),
            utility_type=UtilityType.ELECTRICITY,
            identifier="MET-001",
            installation_date=date(2026, 1, 1),
            is_active=True,
        )
        mock_repo.get.return_value = meter
        mock_repo.update.return_value = meter

        result = service.deactivate_meter(meter.id)

        assert result.is_active is False
        mock_repo.update.assert_called_once()

    def test_deactivate_inactive_meter_rejected(self, service: MeterService, mock_repo: MagicMock) -> None:
        meter = Meter(
            rental_space_id=uuid.uuid4(),
            utility_type=UtilityType.ELECTRICITY,
            identifier="MET-001",
            installation_date=date(2026, 1, 1),
            is_active=False,
        )
        mock_repo.get.return_value = meter
        with pytest.raises(ValidationError, match="already inactive"):
            service.deactivate_meter(meter.id)

    def test_activate_meter(self, service: MeterService, mock_repo: MagicMock) -> None:
        meter = Meter(
            rental_space_id=uuid.uuid4(),
            utility_type=UtilityType.ELECTRICITY,
            identifier="MET-001",
            installation_date=date(2026, 1, 1),
            is_active=False,
        )
        mock_repo.get.return_value = meter
        mock_repo.update.return_value = meter

        result = service.activate_meter(meter.id)

        assert result.is_active is True


class TestMeterReadingService:
    @pytest.fixture
    def mock_reading_repo(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def mock_meter_repo(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def service(self, mock_reading_repo: MagicMock, mock_meter_repo: MagicMock) -> MeterReadingService:
        return MeterReadingService(mock_reading_repo, mock_meter_repo)

    def _meter(self) -> Meter:
        return Meter(
            rental_space_id=uuid.uuid4(),
            utility_type=UtilityType.ELECTRICITY,
            identifier="MET-001",
            installation_date=date(2026, 1, 1),
            is_active=True,
        )

    def test_record_reading_valid(
        self, service: MeterReadingService, mock_meter_repo: MagicMock, mock_reading_repo: MagicMock
    ) -> None:
        meter = self._meter()
        mock_meter_repo.get.return_value = meter
        mock_reading_repo.has_reading_on_date.return_value = False
        mock_reading_repo.get_latest_reading.return_value = None
        reading = MeterReading(
            meter_id=meter.id,
            reading_date=date(2026, 1, 5),
            value=MeterReadingValue(Decimal("100")),
        )
        mock_reading_repo.add.return_value = reading

        result = service.record_reading(meter.id, date(2026, 1, 5), "100")

        assert result.value.value == Decimal("100")
        mock_reading_repo.add.assert_called_once()

    def test_record_reading_rejects_missing_meter(self, service: MeterReadingService, mock_meter_repo: MagicMock) -> None:
        mock_meter_repo.get.return_value = None
        with pytest.raises(NotFoundError):
            service.record_reading(uuid.uuid4(), date(2026, 1, 5), "100")

    def test_record_reading_rejects_negative_value(
        self, service: MeterReadingService, mock_meter_repo: MagicMock
    ) -> None:
        mock_meter_repo.get.return_value = self._meter()
        with pytest.raises(ValueError, match="Reading value cannot be negative"):
            service.record_reading(uuid.uuid4(), date(2026, 1, 5), "-100")

    def test_record_reading_rejects_duplicate_date(
        self, service: MeterReadingService, mock_meter_repo: MagicMock, mock_reading_repo: MagicMock
    ) -> None:
        meter = self._meter()
        mock_meter_repo.get.return_value = meter
        mock_reading_repo.has_reading_on_date.return_value = True
        with pytest.raises(ConflictError, match="already exists"):
            service.record_reading(meter.id, date(2026, 1, 5), "100")

    def test_record_reading_rejects_decreasing_value(
        self, service: MeterReadingService, mock_meter_repo: MagicMock, mock_reading_repo: MagicMock
    ) -> None:
        meter = self._meter()
        mock_meter_repo.get.return_value = meter
        mock_reading_repo.has_reading_on_date.return_value = False
        previous = MeterReading(
            meter_id=meter.id,
            reading_date=date(2026, 1, 1),
            value=MeterReadingValue(Decimal("150")),
        )
        mock_reading_repo.get_latest_reading.return_value = previous
        with pytest.raises(ValidationError, match="Decreasing readings"):
            service.record_reading(meter.id, date(2026, 2, 1), "100")

    def test_record_reading_allows_decrease_in_controlled_replacement(
        self, service: MeterReadingService, mock_meter_repo: MagicMock, mock_reading_repo: MagicMock
    ) -> None:
        meter = self._meter()
        mock_meter_repo.get.return_value = meter
        mock_reading_repo.has_reading_on_date.return_value = False
        previous = MeterReading(
            meter_id=meter.id,
            reading_date=date(2026, 1, 1),
            value=MeterReadingValue(Decimal("150")),
        )
        mock_reading_repo.get_latest_reading.return_value = previous
        reading = MeterReading(
            meter_id=meter.id,
            reading_date=date(2026, 2, 1),
            value=MeterReadingValue(Decimal("100")),
        )
        mock_reading_repo.add.return_value = reading

        result = service.record_reading(meter.id, date(2026, 2, 1), "100", allow_decrease=True)

        assert result is not None

    def test_record_reading_rejects_out_of_sequence_date(
        self, service: MeterReadingService, mock_meter_repo: MagicMock, mock_reading_repo: MagicMock
    ) -> None:
        meter = self._meter()
        mock_meter_repo.get.return_value = meter
        mock_reading_repo.has_reading_on_date.return_value = False
        previous = MeterReading(
            meter_id=meter.id,
            reading_date=date(2026, 2, 1),
            value=MeterReadingValue(Decimal("100")),
        )
        mock_reading_repo.get_latest_reading.return_value = previous
        with pytest.raises(ValidationError, match="before the latest reading"):
            service.record_reading(meter.id, date(2026, 1, 1), "100")

    def test_get_consumption_between(
        self, service: MeterReadingService, mock_reading_repo: MagicMock
    ) -> None:
        meter_id = uuid.uuid4()
        reading1 = MeterReading(
            meter_id=meter_id,
            reading_date=date(2026, 1, 1),
            value=MeterReadingValue(Decimal("100")),
        )
        reading2 = MeterReading(
            meter_id=meter_id,
            reading_date=date(2026, 2, 1),
            value=MeterReadingValue(Decimal("150")),
        )
        mock_reading_repo.get_by_meter_between.return_value = [reading1, reading2]

        consumption = service.get_consumption_between(meter_id, date(2026, 1, 1), date(2026, 2, 1))

        assert consumption == Decimal("50")

    def test_get_consumption_between_negative_rejected(
        self, service: MeterReadingService, mock_reading_repo: MagicMock
    ) -> None:
        meter_id = uuid.uuid4()
        reading1 = MeterReading(
            meter_id=meter_id,
            reading_date=date(2026, 1, 1),
            value=MeterReadingValue(Decimal("150")),
        )
        reading2 = MeterReading(
            meter_id=meter_id,
            reading_date=date(2026, 2, 1),
            value=MeterReadingValue(Decimal("100")),
        )
        mock_reading_repo.get_by_meter_between.return_value = [reading1, reading2]
        with pytest.raises(ValidationError, match="Consumption cannot be negative"):
            service.get_consumption_between(meter_id, date(2026, 1, 1), date(2026, 2, 1))

    def test_calculate_consumption(self, service: MeterReadingService) -> None:
        result = service.calculate_consumption(
            MeterReadingValue(Decimal("150")), MeterReadingValue(Decimal("100"))
        )
        assert result.value == Decimal("50.000")

    def test_calculate_consumption_negative_rejected(self, service: MeterReadingService) -> None:
        with pytest.raises(ValidationError, match="Consumption cannot be negative"):
            service.calculate_consumption(
                MeterReadingValue(Decimal("100")), MeterReadingValue(Decimal("150"))
            )


class TestUtilityTariffService:
    @pytest.fixture
    def mock_repo(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def service(self, mock_repo: MagicMock) -> UtilityTariffService:
        return UtilityTariffService(mock_repo)

    def test_create_tariff(self, service: UtilityTariffService, mock_repo: MagicMock) -> None:
        mock_repo.get_on_effective_date.return_value = None
        tariff = UtilityTariff(
            utility_type=UtilityType.ELECTRICITY,
            effective_from=date(2026, 1, 1),
            rate=Money(Decimal("12")),
        )
        mock_repo.add.return_value = tariff

        result = service.create_tariff(UtilityType.ELECTRICITY, date(2026, 1, 1), "12")

        assert result.rate.amount == Decimal("12.00")
        mock_repo.add.assert_called_once()

    def test_create_tariff_rejects_duplicate_effective_date(self, service: UtilityTariffService, mock_repo: MagicMock) -> None:
        mock_repo.get_on_effective_date.return_value = UtilityTariff(
            utility_type=UtilityType.ELECTRICITY,
            effective_from=date(2026, 1, 1),
            rate=Money(Decimal("12")),
        )
        with pytest.raises(ConflictError, match="already exists"):
            service.create_tariff(UtilityType.ELECTRICITY, date(2026, 1, 1), "12")

    def test_create_tariff_rejects_negative_rate(self, service: UtilityTariffService, mock_repo: MagicMock) -> None:
        mock_repo.get_on_effective_date.return_value = None
        with pytest.raises(ValueError, match="Money amount cannot be negative"):
            service.create_tariff(UtilityType.ELECTRICITY, date(2026, 1, 1), "-5")

    def test_get_applicable_tariff(self, service: UtilityTariffService, mock_repo: MagicMock) -> None:
        tariff = UtilityTariff(
            utility_type=UtilityType.ELECTRICITY,
            effective_from=date(2026, 1, 1),
            rate=Money(Decimal("12")),
        )
        mock_repo.get_applicable_tariff.return_value = tariff

        result = service.get_applicable_tariff(UtilityType.ELECTRICITY, date(2026, 6, 1))

        assert result is not None
        mock_repo.get_applicable_tariff.assert_called_once_with(UtilityType.ELECTRICITY, date(2026, 6, 1))

    def test_get_applicable_tariff_none(self, service: UtilityTariffService, mock_repo: MagicMock) -> None:
        mock_repo.get_applicable_tariff.return_value = None
        result = service.get_applicable_tariff(UtilityType.ELECTRICITY, date(2025, 1, 1))
        assert result is None


class TestMeterReplacementService:
    @pytest.fixture
    def mock_replacement_repo(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def mock_meter_repo(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def mock_reading_repo(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def service(
        self,
        mock_replacement_repo: MagicMock,
        mock_meter_repo: MagicMock,
        mock_reading_repo: MagicMock,
    ) -> MeterReplacementService:
        return MeterReplacementService(mock_replacement_repo, mock_meter_repo, mock_reading_repo)

    def test_replace_meter(
        self,
        service: MeterReplacementService,
        mock_replacement_repo: MagicMock,
        mock_meter_repo: MagicMock,
        mock_reading_repo: MagicMock,
    ) -> None:
        old_meter = Meter(
            rental_space_id=uuid.uuid4(),
            utility_type=UtilityType.ELECTRICITY,
            identifier="OLD-001",
            installation_date=date(2020, 1, 1),
            is_active=True,
        )
        mock_meter_repo.get.return_value = old_meter
        mock_meter_repo.get_by_identifier.return_value = None
        mock_reading_repo.has_reading_on_date.return_value = False
        mock_reading_repo.get_latest_reading.return_value = None
        new_meter = Meter(
            rental_space_id=old_meter.rental_space_id,
            utility_type=UtilityType.ELECTRICITY,
            identifier="NEW-001",
            installation_date=date(2026, 3, 1),
            is_active=True,
        )
        mock_meter_repo.add.return_value = new_meter
        replacement = MeterReplacement(
            old_meter_id=old_meter.id,
            new_meter_id=new_meter.id,
            replaced_on=date(2026, 3, 1),
        )
        mock_replacement_repo.add.return_value = replacement

        result = service.replace_meter(
            old_meter_id=old_meter.id,
            new_identifier="NEW-001",
            replaced_on=date(2026, 3, 1),
            final_reading_value="1000",
            initial_reading_value="0",
        )

        assert result is not None
        assert result.new_meter_id == new_meter.id
        assert old_meter.is_active is False
        mock_meter_repo.add.assert_called_once()
        mock_replacement_repo.add.assert_called_once()

    def test_replace_meter_rejects_inactive_old(self, service: MeterReplacementService, mock_meter_repo: MagicMock) -> None:
        old_meter = Meter(
            rental_space_id=uuid.uuid4(),
            utility_type=UtilityType.ELECTRICITY,
            identifier="OLD-001",
            installation_date=date(2020, 1, 1),
            is_active=False,
        )
        mock_meter_repo.get.return_value = old_meter
        with pytest.raises(ValidationError, match="Only active meters can be replaced"):
            service.replace_meter(old_meter.id, "NEW-001", date(2026, 3, 1), "1000", "0")

    def test_replace_meter_rejects_missing_old(self, service: MeterReplacementService, mock_meter_repo: MagicMock) -> None:
        mock_meter_repo.get.return_value = None
        with pytest.raises(NotFoundError):
            service.replace_meter(uuid.uuid4(), "NEW-001", date(2026, 3, 1), "1000", "0")

    def test_replace_meter_rejects_duplicate_new_identifier(
        self, service: MeterReplacementService, mock_meter_repo: MagicMock
    ) -> None:
        old_meter = Meter(
            rental_space_id=uuid.uuid4(),
            utility_type=UtilityType.ELECTRICITY,
            identifier="OLD-001",
            installation_date=date(2020, 1, 1),
            is_active=True,
        )
        mock_meter_repo.get.return_value = old_meter
        mock_meter_repo.get_by_identifier.return_value = Meter(
            rental_space_id=uuid.uuid4(),
            utility_type=UtilityType.ELECTRICITY,
            identifier="NEW-001",
            installation_date=date(2026, 1, 1),
        )
        with pytest.raises(NotFoundError, match="already exists"):
            service.replace_meter(old_meter.id, "NEW-001", date(2026, 3, 1), "1000", "0")
