from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

import pytest

from app.domain.enums import UtilityType
from tests.integration.factories import (
    make_bill,
    make_meter,
    make_reading,
    make_rent_line,
    seed_core_chain,
)


@pytest.mark.integration
def test_uuid_primary_keys_and_foreign_keys_roundtrip(repositories):
    core = seed_core_chain(repositories)

    assert isinstance(core["owner"].id, uuid.UUID)
    assert isinstance(core["property"].id, uuid.UUID)
    assert isinstance(core["space"].id, uuid.UUID)
    assert isinstance(core["tenant"].id, uuid.UUID)
    assert isinstance(core["agreement"].id, uuid.UUID)

    # FK relationships resolve through the real database
    agreement = repositories.agreement.get(core["agreement"].id)
    assert agreement.tenant_id == core["tenant"].id
    assert agreement.rental_space_id == core["space"].id

    prop = repositories.property.get(core["property"].id)
    assert prop.owner_id == core["owner"].id


@pytest.mark.integration
def test_decimal_money_roundtrip_with_exact_precision(repositories):
    core = seed_core_chain(repositories)
    bill = make_bill(core["agreement"].id, core["tenant"].id, core["space"].id)
    bill.add_line(make_rent_line("12345678.90"))
    saved = repositories.bill.add(bill)

    fetched = repositories.bill.get(saved.id)
    # PostgreSQL NUMERIC returns Decimal, never float
    assert isinstance(fetched.lines[0].amount.amount, Decimal)
    assert fetched.lines[0].amount.amount == Decimal("12345678.90")
    assert fetched.total.amount == Decimal("12345678.90")


@pytest.mark.integration
def test_money_is_quantized_to_two_decimals(repositories):
    core = seed_core_chain(repositories)
    bill = make_bill(core["agreement"].id, core["tenant"].id, core["space"].id)
    bill.add_line(make_rent_line("25000.555"))
    saved = repositories.bill.add(bill)

    fetched = repositories.bill.get(saved.id)
    assert fetched.lines[0].amount.amount == Decimal("25000.56")


@pytest.mark.integration
def test_meter_reading_three_decimal_roundtrip(repositories):
    core = seed_core_chain(repositories)
    meter = repositories.meter.add(make_meter(core["space"].id, UtilityType.ELECTRICITY))
    reading = repositories.meter_reading.add(make_reading(meter.id, date(2026, 1, 31), "1234.567"))

    fetched = repositories.meter_reading.get(reading.id)
    assert isinstance(fetched.value.value, Decimal)
    assert fetched.value.value == Decimal("1234.567")


@pytest.mark.integration
def test_ad_date_roundtrip_no_information_loss(repositories):
    core = seed_core_chain(repositories)
    agreement = repositories.agreement.get(core["agreement"].id)

    assert isinstance(agreement.start_date, date)
    assert agreement.start_date == date(2026, 1, 1)

    bill = make_bill(core["agreement"].id, core["tenant"].id, core["space"].id, date(2026, 2, 1), date(2026, 2, 28))
    bill.add_line(make_rent_line("25000"))
    saved = repositories.bill.add(bill)
    fetched = repositories.bill.get(saved.id)
    assert fetched.period.start == date(2026, 2, 1)
    assert fetched.period.end == date(2026, 2, 28)
    assert fetched.billing_date == date(2026, 2, 28)
