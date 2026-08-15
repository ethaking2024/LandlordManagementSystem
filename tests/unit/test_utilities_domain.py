from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.domain import (
    Meter,
    MeterReading,
    MeterReadingValue,
    MeterReplacement,
    UtilityConfig,
    UtilityTariff,
    UtilityType,
)
from app.domain.entities import ElectricityConfigType, WaterConfigType
from app.domain.value_objects import Money


class TestUtilityConfig:
    def test_electricity_fixed_valid(self) -> None:
        config = UtilityConfig(
            rental_space_id="rs1",
            utility_type=UtilityType.ELECTRICITY,
            config_type=ElectricityConfigType.FIXED.value,
            fixed_amount=Money(Decimal("500")),
        )
        assert config.config_type == "fixed"
        assert config.fixed_amount is not None

    def test_electricity_metered_valid(self) -> None:
        config = UtilityConfig(
            rental_space_id="rs1",
            utility_type=UtilityType.ELECTRICITY,
            config_type=ElectricityConfigType.METERED.value,
        )
        assert config.config_type == "metered"
        assert config.fixed_amount is None

    def test_water_no_charge_valid(self) -> None:
        config = UtilityConfig(
            rental_space_id="rs1",
            utility_type=UtilityType.WATER,
            config_type=WaterConfigType.NO_CHARGE.value,
        )
        assert config.config_type == "no_charge"

    def test_water_fixed_valid(self) -> None:
        config = UtilityConfig(
            rental_space_id="rs1",
            utility_type=UtilityType.WATER,
            config_type=WaterConfigType.FIXED.value,
            fixed_amount=Money(Decimal("300")),
        )
        assert config.config_type == "fixed"

    def test_water_metered_valid(self) -> None:
        config = UtilityConfig(
            rental_space_id="rs1",
            utility_type=UtilityType.WATER,
            config_type=WaterConfigType.METERED.value,
        )
        assert config.config_type == "metered"

    def test_rejects_invalid_electricity_config_type(self) -> None:
        with pytest.raises(ValueError, match="Invalid config type"):
            UtilityConfig(
                rental_space_id="rs1",
                utility_type=UtilityType.ELECTRICITY,
                config_type=WaterConfigType.NO_CHARGE.value,
            )

    def test_rejects_invalid_water_config_type(self) -> None:
        with pytest.raises(ValueError, match="Invalid config type"):
            UtilityConfig(
                rental_space_id="rs1",
                utility_type=UtilityType.WATER,
                config_type="unmetered",
            )

    def test_fixed_requires_amount(self) -> None:
        with pytest.raises(ValueError, match="requires a fixed amount"):
            UtilityConfig(
                rental_space_id="rs1",
                utility_type=UtilityType.ELECTRICITY,
                config_type=ElectricityConfigType.FIXED.value,
            )

    def test_rejects_negative_fixed_amount(self) -> None:
        with pytest.raises(ValueError, match="Money amount cannot be negative"):
            UtilityConfig(
                rental_space_id="rs1",
                utility_type=UtilityType.WATER,
                config_type=WaterConfigType.FIXED.value,
                fixed_amount=Money(Decimal("-100")),
            )

    def test_update_config_changes_type(self) -> None:
        config = UtilityConfig(
            rental_space_id="rs1",
            utility_type=UtilityType.ELECTRICITY,
            config_type=ElectricityConfigType.METERED.value,
        )
        config.update_config(ElectricityConfigType.FIXED.value, Money(Decimal("400")))
        assert config.config_type == "fixed"
        assert config.fixed_amount is not None


class TestMeter:
    def test_create_meter_valid(self) -> None:
        meter = Meter(
            rental_space_id="rs1",
            utility_type=UtilityType.ELECTRICITY,
            identifier="MET-001",
            installation_date=date(2026, 1, 1),
        )
        assert meter.is_active is True
        assert meter.identifier == "MET-001"

    def test_identifier_required(self) -> None:
        with pytest.raises(ValueError, match="Meter identifier is required"):
            Meter(
                rental_space_id="rs1",
                utility_type=UtilityType.ELECTRICITY,
                identifier="   ",
                installation_date=date(2026, 1, 1),
            )

    def test_deactivate_and_activate(self) -> None:
        meter = Meter(
            rental_space_id="rs1",
            utility_type=UtilityType.ELECTRICITY,
            identifier="MET-001",
            installation_date=date(2026, 1, 1),
        )
        meter.deactivate()
        assert meter.is_active is False
        meter.activate()
        assert meter.is_active is True


class TestMeterReading:
    def test_create_reading_valid(self) -> None:
        reading = MeterReading(
            meter_id="m1",
            reading_date=date(2026, 1, 1),
            value=MeterReadingValue(Decimal("100")),
        )
        assert reading.value.value == Decimal("100")

    def test_value_quantized(self) -> None:
        reading = MeterReading(
            meter_id="m1",
            reading_date=date(2026, 1, 1),
            value=MeterReadingValue(Decimal("100.12345")),
        )
        assert reading.value.value == Decimal("100.123")

    def test_bs_display(self) -> None:
        reading = MeterReading(
            meter_id="m1",
            reading_date=date(2026, 8, 10),
            value=MeterReadingValue(Decimal("100")),
        )
        assert reading.bs_display == "Shrawan 25, 2083"

    def test_consumption_since(self) -> None:
        previous = MeterReading(
            meter_id="m1",
            reading_date=date(2026, 1, 1),
            value=MeterReadingValue(Decimal("100")),
        )
        current = MeterReading(
            meter_id="m1",
            reading_date=date(2026, 2, 1),
            value=MeterReadingValue(Decimal("150")),
        )
        consumption = current.consumption_since(previous)
        assert consumption.value == Decimal("50.000")

    def test_consumption_since_rejects_decrease(self) -> None:
        previous = MeterReading(
            meter_id="m1",
            reading_date=date(2026, 1, 1),
            value=MeterReadingValue(Decimal("150")),
        )
        current = MeterReading(
            meter_id="m1",
            reading_date=date(2026, 2, 1),
            value=MeterReadingValue(Decimal("100")),
        )
        with pytest.raises(ValueError, match="Consumption cannot be negative"):
            current.consumption_since(previous)


class TestMeterReadingValue:
    def test_rejects_negative(self) -> None:
        with pytest.raises(ValueError, match="Reading value cannot be negative"):
            MeterReadingValue(Decimal("-1"))

    def test_equality(self) -> None:
        assert MeterReadingValue(Decimal("10")) == MeterReadingValue(Decimal("10"))


class TestUtilityTariff:
    def test_create_tariff_valid(self) -> None:
        tariff = UtilityTariff(
            utility_type=UtilityType.ELECTRICITY,
            effective_from=date(2026, 1, 1),
            rate=Money(Decimal("12")),
        )
        assert tariff.rate.amount == Decimal("12.00")

    def test_rejects_negative_rate(self) -> None:
        with pytest.raises(ValueError, match="Money amount cannot be negative"):
            UtilityTariff(
                utility_type=UtilityType.ELECTRICITY,
                effective_from=date(2026, 1, 1),
                rate=Money(Decimal("-5")),
            )

    def test_water_tariff_valid(self) -> None:
        tariff = UtilityTariff(
            utility_type=UtilityType.WATER,
            effective_from=date(2026, 1, 1),
            rate=Money(Decimal("30")),
        )
        assert tariff.utility_type == UtilityType.WATER


class TestMeterReplacement:
    def test_create_replacement_valid(self) -> None:
        replacement = MeterReplacement(
            old_meter_id="old1",
            new_meter_id="new1",
            replaced_on=date(2026, 1, 1),
        )
        assert replacement.old_meter_id == "old1"
        assert replacement.new_meter_id == "new1"

    def test_rejects_same_meter(self) -> None:
        with pytest.raises(ValueError, match="cannot be the same"):
            MeterReplacement(
                old_meter_id="m1",
                new_meter_id="m1",
                replaced_on=date(2026, 1, 1),
            )
