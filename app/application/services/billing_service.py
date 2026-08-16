from __future__ import annotations

import calendar
import uuid
from datetime import date
from decimal import Decimal

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.domain.entities import Agreement, Bill, BillLine, Meter
from app.domain.enums import (
    BillCategory,
    BillStatus,
    ElectricityConfigType,
    UtilityType,
    WaterConfigType,
)
from app.domain.value_objects import BillingPeriod, Money
from app.infrastructure.repositories import (
    AgreementRepository,
    BillRepository,
    MeterReadingRepository,
    MeterRepository,
    UtilityConfigRepository,
    UtilityTariffRepository,
)


class BillingService:
    """Orchestrates bill generation for rent, electricity and water.

    Generated bills snapshot every value used during calculation so that later
    changes to agreements, tariffs, utility configs or meter readings never mutate
    an existing bill. Confirmed bills are frozen historical financial records.
    """

    def __init__(
        self,
        bill_repository: BillRepository,
        agreement_repository: AgreementRepository,
        utility_config_repository: UtilityConfigRepository,
        meter_repository: MeterRepository,
        meter_reading_repository: MeterReadingRepository,
        utility_tariff_repository: UtilityTariffRepository,
    ) -> None:
        self._bill_repository = bill_repository
        self._agreement_repository = agreement_repository
        self._utility_config_repository = utility_config_repository
        self._meter_repository = meter_repository
        self._meter_reading_repository = meter_reading_repository
        self._utility_tariff_repository = utility_tariff_repository

    # ------------------------------------------------------------------
    # Bill generation
    # ------------------------------------------------------------------

    def generate_bill(
        self,
        agreement_id: uuid.UUID,
        period_start: date,
        period_end: date,
        billing_date: date,
        notes: str | None = None,
    ) -> Bill:
        """Generate a DRAFT bill for an agreement and billing period.

        Raises if any required information is missing or invalid so a partial bill
        is never persisted: the calculation happens entirely before the bill is
        committed to the repository.
        """
        agreement = self._agreement_repository.get(agreement_id)
        if not agreement:
            raise NotFoundError(f"Agreement with id {agreement_id} not found")

        period = BillingPeriod(period_start, period_end)
        self._validate_period_within_agreement(agreement, period)

        if self._bill_repository.has_bill_for_period(agreement_id, period_start, period_end):
            raise ConflictError(
                f"A bill for agreement {agreement_id} already exists for period {period_start} to {period_end}. "
                "Use the existing DRAFT bill or void it before regenerating."
            )

        lines = [
            self._build_rent_line(agreement, period),
            self._build_electricity_line(agreement.rental_space_id, period, billing_date),
            self._build_water_line(agreement.rental_space_id, period, billing_date),
        ]

        bill = Bill(
            agreement_id=agreement.id,
            tenant_id=agreement.tenant_id,
            rental_space_id=agreement.rental_space_id,
            period=period,
            billing_date=billing_date,
            status=BillStatus.DRAFT,
            notes=notes.strip() if notes else None,
        )
        for line in lines:
            bill.add_line(line)
        return self._bill_repository.add(bill)

    def get_bill(self, bill_id: uuid.UUID) -> Bill:
        bill = self._bill_repository.get(bill_id)
        if not bill:
            raise NotFoundError(f"Bill with id {bill_id} not found")
        return bill

    def get_all_bills(self, limit: int = 100, offset: int = 0) -> list[Bill]:
        return self._bill_repository.get_all(limit=limit, offset=offset)

    def get_bills_by_agreement(self, agreement_id: uuid.UUID, limit: int = 100, offset: int = 0) -> list[Bill]:
        return self._bill_repository.get_by_agreement(agreement_id, limit=limit, offset=offset)

    def get_bills_by_status(self, status: BillStatus, limit: int = 100, offset: int = 0) -> list[Bill]:
        return self._bill_repository.get_by_status(status, limit=limit, offset=offset)

    def get_bills_by_billing_date_range(
        self, start_date: date, end_date: date, limit: int = 10000, offset: int = 0
    ) -> list[Bill]:
        return self._bill_repository.get_by_billing_date_range(
            start_date, end_date, limit=limit, offset=offset
        )

    def confirm_bill(self, bill_id: uuid.UUID) -> Bill:
        bill = self.get_bill(bill_id)
        if bill.status != BillStatus.DRAFT:
            raise ValidationError(f"Cannot confirm a bill with status {bill.status.value}")
        if not bill.lines:
            raise ValidationError("Cannot confirm a bill without line items")
        bill.confirm()
        return self._bill_repository.update(bill)

    def void_bill(self, bill_id: uuid.UUID) -> Bill:
        bill = self.get_bill(bill_id)
        if bill.status == BillStatus.VOID:
            raise ValidationError("Bill is already void")
        bill.void()
        return self._bill_repository.update(bill)

    def delete_bill(self, bill_id: uuid.UUID) -> bool:
        bill = self.get_bill(bill_id)
        if bill.status != BillStatus.DRAFT:
            raise ValidationError(
                f"Cannot delete a bill with status {bill.status.value}; historical records must be preserved"
            )
        return self._bill_repository.delete(bill_id)

    # ------------------------------------------------------------------
    # Line construction
    # ------------------------------------------------------------------

    def _build_rent_line(self, agreement: Agreement, period: BillingPeriod) -> BillLine:
        """Rent line with deterministic date-based proration for partial periods.

        Proration policy: a billing period that exactly covers one calendar month
        charges the full monthly rent; any other period is prorated as
        monthly_rent * (days in period / days in the calendar month of period start).
        """
        days_in_month = calendar.monthrange(period.start.year, period.start.month)[1]
        is_full_month = period.start.day == 1 and period.end == period.start.replace(day=days_in_month)

        if is_full_month:
            amount = agreement.monthly_rent
            description = f"Monthly rent for {period.start.strftime('%Y-%m')}"
            quantity: Decimal | None = None
        else:
            amount = Money(
                (agreement.monthly_rent.amount * Decimal(period.days)) / Decimal(days_in_month)
            )
            description = (
                f"Prorated rent for {period.start} to {period.end} "
                f"({period.days} of {days_in_month} days)"
            )
            quantity = Decimal(period.days)

        return BillLine(
            category=BillCategory.RENT,
            description=description,
            quantity=quantity,
            unit_rate=agreement.monthly_rent,
            amount=amount,
        )

    def _build_electricity_line(
        self, rental_space_id: uuid.UUID, period: BillingPeriod, billing_date: date
    ) -> BillLine:
        config = self._utility_config_repository.get_by_rental_space_and_utility(
            rental_space_id, UtilityType.ELECTRICITY
        )
        if not config:
            raise ValidationError(f"No electricity config found for rental space {rental_space_id}")

        if config.config_type == ElectricityConfigType.FIXED.value:
            if config.fixed_amount is None:
                raise ValidationError("Fixed electricity config is missing its fixed amount")
            return BillLine(
                category=BillCategory.ELECTRICITY,
                description="Fixed electricity charge",
                config_type=config.config_type,
                amount=config.fixed_amount,
            )

        return self._build_metered_line(
            rental_space_id=rental_space_id,
            utility_type=UtilityType.ELECTRICITY,
            period=period,
            billing_date=billing_date,
            config_type=config.config_type,
        )

    def _build_water_line(
        self, rental_space_id: uuid.UUID, period: BillingPeriod, billing_date: date
    ) -> BillLine:
        config = self._utility_config_repository.get_by_rental_space_and_utility(
            rental_space_id, UtilityType.WATER
        )
        if not config:
            raise ValidationError(f"No water config found for rental space {rental_space_id}")

        if config.config_type == WaterConfigType.NO_CHARGE.value:
            return BillLine(
                category=BillCategory.WATER,
                description="No water charge",
                config_type=config.config_type,
                amount=Money(Decimal("0")),
            )

        if config.config_type == WaterConfigType.FIXED.value:
            if config.fixed_amount is None:
                raise ValidationError("Fixed water config is missing its fixed amount")
            return BillLine(
                category=BillCategory.WATER,
                description="Fixed water charge",
                config_type=config.config_type,
                amount=config.fixed_amount,
            )

        return self._build_metered_line(
            rental_space_id=rental_space_id,
            utility_type=UtilityType.WATER,
            period=period,
            billing_date=billing_date,
            config_type=config.config_type,
        )

    def _build_metered_line(
        self,
        rental_space_id: uuid.UUID,
        utility_type: UtilityType,
        period: BillingPeriod,
        billing_date: date,
        config_type: str,
    ) -> BillLine:
        meter = self._find_meter(rental_space_id, utility_type)
        previous = self._meter_reading_repository.get_latest_reading_at_or_before(meter.id, period.start)
        current = self._meter_reading_repository.get_latest_reading_at_or_before(meter.id, period.end)

        if not previous:
            raise ValidationError(
                f"No previous reading found for meter {meter.identifier} at or before {period.start}"
            )
        if not current:
            raise ValidationError(
                f"No current reading found for meter {meter.identifier} at or before {period.end}"
            )
        if current.reading_date < period.start:
            raise ValidationError(
                f"No reading found within the billing period for meter {meter.identifier}"
            )
        if current.value.value < previous.value.value:
            raise ValidationError(
                f"Invalid reading on meter {meter.identifier}: current {current.value.value} "
                f"is less than previous {previous.value.value}"
            )

        consumption = current.value.value - previous.value.value
        tariff = self._utility_tariff_repository.get_applicable_tariff(utility_type, billing_date)
        if not tariff:
            raise ValidationError(f"No {utility_type.value} tariff applicable on {billing_date}")

        amount = Money(consumption * tariff.rate.amount)
        description = f"Metered {utility_type.value} ({meter.identifier})"

        return BillLine(
            category=BillCategory.ELECTRICITY if utility_type == UtilityType.ELECTRICITY else BillCategory.WATER,
            description=description,
            quantity=consumption,
            unit_rate=tariff.rate,
            amount=amount,
            config_type=config_type,
            meter_id=meter.id,
            meter_identifier=meter.identifier,
            previous_reading=previous.value.value,
            current_reading=current.value.value,
            consumption=consumption,
            tariff_rate=tariff.rate,
            tariff_effective_from=tariff.effective_from,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _find_meter(self, rental_space_id: uuid.UUID, utility_type: UtilityType) -> Meter:
        meters = self._meter_repository.get_by_rental_space_and_utility(rental_space_id, utility_type)
        active = [m for m in meters if m.is_active]
        if not active:
            raise ValidationError(f"No active {utility_type.value} meter found for rental space {rental_space_id}")
        return max(active, key=lambda m: m.installation_date)

    @staticmethod
    def _validate_period_within_agreement(agreement: Agreement, period: BillingPeriod) -> None:
        if period.start < agreement.start_date:
            raise ValidationError(
                f"Billing period start {period.start} is before agreement start {agreement.start_date}"
            )
        if agreement.end_date is not None and period.end > agreement.end_date:
            raise ValidationError(
                f"Billing period end {period.end} is after agreement end {agreement.end_date}"
            )
