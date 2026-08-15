from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.domain.entities import MeterReading
from app.domain.value_objects import MeterReadingValue
from app.infrastructure.repositories import MeterReadingRepository, MeterRepository


class MeterReadingService:
    def __init__(
        self,
        repository: MeterReadingRepository,
        meter_repository: MeterRepository,
    ) -> None:
        self._repository = repository
        self._meter_repository = meter_repository

    def record_reading(
        self,
        meter_id: uuid.UUID,
        reading_date: date,
        value: Decimal | str,
        notes: str | None = None,
        allow_decrease: bool = False,
    ) -> MeterReading:
        meter = self._meter_repository.get(meter_id)
        if not meter:
            raise NotFoundError(f"Meter with id {meter_id} not found")

        value_obj = MeterReadingValue(Decimal(str(value)))

        if self._repository.has_reading_on_date(meter_id, reading_date):
            raise ConflictError(f"A reading for meter {meter.identifier} on {reading_date} already exists")

        latest = self._repository.get_latest_reading(meter_id)
        if latest:
            if reading_date < latest.reading_date:
                raise ValidationError(
                    f"Reading date {reading_date} is before the latest reading {latest.reading_date} on meter {meter.identifier}"
                )
            if value_obj.value < latest.value.value and not allow_decrease:
                raise ValidationError(
                    f"Reading value {value_obj.value} is less than the previous reading {latest.value.value} "
                    f"on meter {meter.identifier}. Decreasing readings are only allowed during a controlled meter replacement."
                )

        reading = MeterReading(
            meter_id=meter_id,
            reading_date=reading_date,
            value=value_obj,
            notes=notes.strip() if notes else None,
        )
        return self._repository.add(reading)

    def get_reading(self, reading_id: uuid.UUID) -> MeterReading:
        reading = self._repository.get(reading_id)
        if not reading:
            raise NotFoundError(f"Meter reading with id {reading_id} not found")
        return reading

    def get_readings_by_meter(self, meter_id: uuid.UUID, limit: int = 100, offset: int = 0) -> list[MeterReading]:
        return self._repository.get_by_meter(meter_id, limit=limit, offset=offset)

    def get_latest_reading(self, meter_id: uuid.UUID) -> MeterReading | None:
        return self._repository.get_latest_reading(meter_id)

    def get_consumption_between(
        self,
        meter_id: uuid.UUID,
        start_date: date,
        end_date: date,
    ) -> Decimal:
        """Compute consumption (current - previous) between two reading dates.

        The 'previous' reading is the latest reading at or before start_date and the
        'current' reading is the latest reading at or before end_date. This is the
        foundation for metered utility billing in later releases.
        """
        if end_date < start_date:
            raise ValidationError("End date cannot be before start date")

        readings = self._repository.get_by_meter_between(meter_id, end_date=end_date)
        previous: MeterReading | None = None
        current: MeterReading | None = None
        for reading in readings:
            if reading.reading_date <= start_date:
                previous = reading
            current = reading

        if previous is None:
            raise ValidationError(f"No reading found at or before {start_date} for meter {meter_id}")
        if current is None:
            raise ValidationError(f"No reading found at or before {end_date} for meter {meter_id}")
        if previous.reading_date == current.reading_date and current.value.value < previous.value.value:
            raise ValidationError("Consumption cannot be negative")

        consumption = current.value.value - previous.value.value
        if consumption < 0:
            raise ValidationError("Consumption cannot be negative")
        return consumption

    def calculate_consumption(self, current: MeterReadingValue, previous: MeterReadingValue) -> MeterReadingValue:
        """Consumption = current - previous; never silently negative."""
        if current.value < previous.value:
            raise ValidationError("Consumption cannot be negative")
        return MeterReadingValue(current.value - previous.value)
