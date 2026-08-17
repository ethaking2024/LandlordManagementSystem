from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.domain.enums import UtilityType
from app.infrastructure.persistence.models import (
    MeterModel,
    MeterReadingModel,
    UtilityConfigModel,
    UtilityTariffModel,
)
from tests.integration.factories import (
    make_meter,
    make_meter_replacement,
    make_reading,
    make_tariff,
    make_utility_config,
    seed_core_chain,
)


@pytest.mark.integration
def test_utility_config_roundtrip_and_unique(repositories):
    core = seed_core_chain(repositories)
    cfg = repositories.utility_config.add(
        make_utility_config(core["space"].id, UtilityType.ELECTRICITY, "fixed", "1500")
    )

    fetched = repositories.utility_config.get(cfg.id)
    assert fetched.config_type == "fixed"
    assert fetched.fixed_amount.amount == Decimal("1500.00")

    found = repositories.utility_config.get_by_rental_space_and_utility(
        core["space"].id, UtilityType.ELECTRICITY
    )
    assert found is not None
    assert found.id == cfg.id


@pytest.mark.integration
def test_duplicate_utility_config_rejected(session, repositories):
    core = seed_core_chain(repositories)
    repositories.utility_config.add(
        make_utility_config(core["space"].id, UtilityType.ELECTRICITY, "fixed", "1500")
    )
    duplicate = UtilityConfigModel(
        rental_space_id=core["space"].id,
        utility_type="electricity",
        config_type="metered",
    )
    session.add(duplicate)
    with pytest.raises(IntegrityError):
        session.flush()


@pytest.mark.integration
def test_meter_roundtrip_and_unique(session, repositories):
    core = seed_core_chain(repositories)
    meter = repositories.meter.add(make_meter(core["space"].id, UtilityType.ELECTRICITY, "MTR-001"))

    fetched = repositories.meter.get(meter.id)
    assert fetched.identifier == "MTR-001"
    assert fetched.utility_type == UtilityType.ELECTRICITY
    assert fetched.installation_date == date(2026, 1, 1)

    duplicate = MeterModel(
        rental_space_id=core["space"].id,
        utility_type="electricity",
        identifier="MTR-001",
        installation_date=date(2026, 1, 1),
    )
    session.add(duplicate)
    with pytest.raises(IntegrityError):
        session.flush()


@pytest.mark.integration
def test_meter_reading_roundtrip_and_unique(session, repositories):
    core = seed_core_chain(repositories)
    meter = repositories.meter.add(make_meter(core["space"].id, UtilityType.ELECTRICITY, "MTR-001"))
    reading = repositories.meter_reading.add(make_reading(meter.id, date(2026, 1, 31), "1234.567"))

    fetched = repositories.meter_reading.get(reading.id)
    assert fetched.value.value == Decimal("1234.567")
    assert fetched.reading_date == date(2026, 1, 31)
    assert fetched.bs_display  # derived/display BS is available

    duplicate = MeterReadingModel(
        meter_id=meter.id,
        reading_date=date(2026, 1, 31),
        value=Decimal("100"),
    )
    session.add(duplicate)
    with pytest.raises(IntegrityError):
        session.flush()


@pytest.mark.integration
def test_tariff_roundtrip_and_unique(session, repositories):
    core = seed_core_chain(repositories)
    del core
    tariff = repositories.utility_tariff.add(make_tariff(UtilityType.ELECTRICITY, date(2026, 1, 1), "15"))

    fetched = repositories.utility_tariff.get(tariff.id)
    assert fetched.rate.amount == Decimal("15.00")

    applicable = repositories.utility_tariff.get_applicable_tariff(UtilityType.ELECTRICITY, date(2026, 2, 15))
    assert applicable is not None
    assert applicable.id == tariff.id

    duplicate = UtilityTariffModel(
        utility_type="electricity",
        effective_from=date(2026, 1, 1),
        rate=Decimal("20"),
    )
    session.add(duplicate)
    with pytest.raises(IntegrityError):
        session.flush()


@pytest.mark.integration
def test_meter_replacement_roundtrip(repositories):
    core = seed_core_chain(repositories)
    old_meter = repositories.meter.add(make_meter(core["space"].id, UtilityType.ELECTRICITY, "OLD-001"))
    new_meter = repositories.meter.add(make_meter(core["space"].id, UtilityType.ELECTRICITY, "NEW-001"))
    replacement = repositories.meter_replacement.add(
        make_meter_replacement(old_meter.id, new_meter.id, date(2026, 3, 1))
    )

    fetched = repositories.meter_replacement.get(replacement.id)
    assert fetched.old_meter_id == old_meter.id
    assert fetched.new_meter_id == new_meter.id

    by_old = repositories.meter_replacement.get_by_old_meter(old_meter.id)
    assert [r.id for r in by_old] == [replacement.id]


@pytest.mark.integration
def test_negative_reading_value_rejected_by_check(session, repositories):
    core = seed_core_chain(repositories)
    meter = repositories.meter.add(make_meter(core["space"].id, UtilityType.ELECTRICITY, "MTR-001"))

    bad = MeterReadingModel(
        meter_id=meter.id,
        reading_date=date(2026, 1, 31),
        value=Decimal("-1"),
    )
    session.add(bad)
    with pytest.raises(IntegrityError):
        session.flush()
