from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

import pytest

from app.domain import Bill, BillCategory, BillingPeriod, BillLine, BillStatus
from app.domain.value_objects import Money


class TestBillingPeriod:
    def test_valid_period(self) -> None:
        period = BillingPeriod(date(2026, 1, 1), date(2026, 1, 31))
        assert period.days == 31

    def test_single_day_period(self) -> None:
        period = BillingPeriod(date(2026, 1, 15), date(2026, 1, 15))
        assert period.days == 1

    def test_rejects_end_before_start(self) -> None:
        with pytest.raises(ValueError, match="cannot be before start"):
            BillingPeriod(date(2026, 2, 1), date(2026, 1, 31))

    def test_contains(self) -> None:
        period = BillingPeriod(date(2026, 1, 1), date(2026, 1, 31))
        assert period.contains(date(2026, 1, 15))
        assert not period.contains(date(2026, 2, 1))


class TestBillLine:
    def test_valid_line(self) -> None:
        line = BillLine(
            category=BillCategory.RENT,
            description="Monthly rent for 2026-01",
            amount=Money(Decimal("20000")),
        )
        assert line.amount.amount == Decimal("20000.00")

    def test_rejects_invalid_category(self) -> None:
        with pytest.raises(ValueError, match="Invalid bill category"):
            BillLine(category="rent", description="x", amount=Money(Decimal("1")))

    def test_rejects_empty_description(self) -> None:
        with pytest.raises(ValueError, match="description is required"):
            BillLine(category=BillCategory.RENT, description="", amount=Money(Decimal("1")))

    def test_rejects_non_money_amount(self) -> None:
        with pytest.raises(ValueError, match="amount must be a Money object"):
            BillLine(category=BillCategory.RENT, description="x", amount=Decimal("1"))

    def test_rejects_negative_quantity(self) -> None:
        with pytest.raises(ValueError, match="quantity cannot be negative"):
            BillLine(
                category=BillCategory.ELECTRICITY,
                description="x",
                amount=Money(Decimal("1")),
                quantity=Decimal("-5"),
            )

    def test_rejects_negative_consumption(self) -> None:
        with pytest.raises(ValueError, match="consumption cannot be negative"):
            BillLine(
                category=BillCategory.ELECTRICITY,
                description="x",
                amount=Money(Decimal("1")),
                consumption=Decimal("-5"),
            )

    def test_accepts_meter_snapshot_fields(self) -> None:
        line = BillLine(
            category=BillCategory.ELECTRICITY,
            description="Metered electricity",
            quantity=Decimal("100"),
            unit_rate=Money(Decimal("12")),
            amount=Money(Decimal("1200")),
            meter_id=uuid.uuid4(),
            meter_identifier="EL-001",
            previous_reading=Decimal("1000"),
            current_reading=Decimal("1100"),
            consumption=Decimal("100"),
            tariff_rate=Money(Decimal("12")),
            tariff_effective_from=date(2026, 1, 1),
        )
        assert line.meter_identifier == "EL-001"
        assert line.consumption == Decimal("100")
        assert line.tariff_rate is not None


class TestBill:
    @pytest.fixture
    def period(self) -> BillingPeriod:
        return BillingPeriod(date(2026, 1, 1), date(2026, 1, 31))

    @pytest.fixture
    def bill(self, period: BillingPeriod) -> Bill:
        return Bill(
            agreement_id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            rental_space_id=uuid.uuid4(),
            period=period,
            billing_date=date(2026, 1, 31),
        )

    def test_default_status_is_draft(self, bill: Bill) -> None:
        assert bill.status == BillStatus.DRAFT

    def test_rejects_billing_date_before_period(self, period: BillingPeriod) -> None:
        with pytest.raises(ValueError, match="cannot be before"):
            Bill(
                agreement_id=uuid.uuid4(),
                tenant_id=uuid.uuid4(),
                rental_space_id=uuid.uuid4(),
                period=period,
                billing_date=date(2025, 12, 31),
            )

    def test_total_derived_from_lines(self, bill: Bill) -> None:
        bill.add_line(BillLine(category=BillCategory.RENT, description="rent", amount=Money(Decimal("20000"))))
        bill.add_line(BillLine(category=BillCategory.ELECTRICITY, description="elec", amount=Money(Decimal("1200"))))
        bill.add_line(BillLine(category=BillCategory.WATER, description="water", amount=Money(Decimal("500"))))
        assert bill.total.amount == Decimal("21700.00")

    def test_total_zero_when_no_lines(self, bill: Bill) -> None:
        assert bill.total.amount == Decimal("0.00")

    def test_add_line_after_confirm_rejected(self, bill: Bill) -> None:
        bill.add_line(BillLine(category=BillCategory.RENT, description="rent", amount=Money(Decimal("20000"))))
        bill.confirm()
        with pytest.raises(ValueError, match="draft bill"):
            bill.add_line(BillLine(category=BillCategory.RENT, description="rent", amount=Money(Decimal("1"))))

    def test_confirm_sets_status(self, bill: Bill) -> None:
        bill.add_line(BillLine(category=BillCategory.RENT, description="rent", amount=Money(Decimal("20000"))))
        bill.confirm()
        assert bill.status == BillStatus.CONFIRMED

    def test_confirm_requires_lines(self, bill: Bill) -> None:
        with pytest.raises(ValueError, match="without line items"):
            bill.confirm()

    def test_confirm_twice_rejected(self, bill: Bill) -> None:
        bill.add_line(BillLine(category=BillCategory.RENT, description="rent", amount=Money(Decimal("1"))))
        bill.confirm()
        with pytest.raises(ValueError, match="Cannot confirm"):
            bill.confirm()

    def test_void_sets_status(self, bill: Bill) -> None:
        bill.void()
        assert bill.status == BillStatus.VOID

    def test_void_twice_rejected(self, bill: Bill) -> None:
        bill.void()
        with pytest.raises(ValueError, match="already void"):
            bill.void()
