from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from app.application.services.meter_reading_service import MeterReadingService
from app.core.exceptions import NotFoundError, ValidationError
from app.domain.entities import Meter, MeterReplacement
from app.infrastructure.repositories import (
    MeterReadingRepository,
    MeterReplacementRepository,
    MeterRepository,
)


class MeterReplacementService:
    def __init__(
        self,
        repository: MeterReplacementRepository,
        meter_repository: MeterRepository,
        meter_reading_repository: MeterReadingRepository,
    ) -> None:
        self._repository = repository
        self._meter_repository = meter_repository
        self._reading_service = MeterReadingService(meter_reading_repository, meter_repository)

    def replace_meter(
        self,
        old_meter_id: uuid.UUID,
        new_identifier: str,
        replaced_on: date,
        final_reading_value: Decimal | str,
        initial_reading_value: Decimal | str,
        notes: str | None = None,
    ) -> MeterReplacement:
        """Controlled meter replacement.

        Flow: old meter final reading -> replacement record -> new meter -> initial reading.
        The final reading is recorded on the old meter (decreasing readings are allowed here
        because the meter may have been faulty). The new meter receives the initial reading.
        Historical readings remain associated with the old meter and are never deleted.
        """
        old_meter = self._meter_repository.get(old_meter_id)
        if not old_meter:
            raise NotFoundError(f"Meter with id {old_meter_id} not found")
        if not old_meter.is_active:
            raise ValidationError(f"Only active meters can be replaced (meter {old_meter.identifier} is inactive)")

        if not new_identifier or not new_identifier.strip():
            raise ValidationError("New meter identifier is required")
        if self._meter_repository.get_by_identifier(new_identifier.strip()):
            raise NotFoundError(f"Meter with identifier '{new_identifier.strip()}' already exists")

        # Final reading on the old meter. The dedicated controlled-replacement path
        # permits a decreasing value (the meter may have been faulty), while normal
        # reading validation still applies: duplicate dates and out-of-sequence dates
        # remain rejected.
        self._reading_service.record_final_reading(
            meter_id=old_meter_id,
            reading_date=replaced_on,
            value=final_reading_value,
            notes=notes,
        )

        # Deactivate the old meter; its history remains intact.
        old_meter.deactivate()
        self._meter_repository.update(old_meter)

        # New meter installed on the same rental space / utility context.
        new_meter = Meter(
            rental_space_id=old_meter.rental_space_id,
            utility_type=old_meter.utility_type,
            identifier=new_identifier.strip(),
            installation_date=replaced_on,
            is_active=True,
            notes=notes.strip() if notes else None,
        )
        new_meter = self._meter_repository.add(new_meter)

        # Initial reading on the new meter via the normal path (no prior readings,
        # so no decrease check applies).
        self._reading_service.record_reading(
            meter_id=new_meter.id,
            reading_date=replaced_on,
            value=initial_reading_value,
            notes=notes,
        )

        replacement = MeterReplacement(
            old_meter_id=old_meter_id,
            new_meter_id=new_meter.id,
            replaced_on=replaced_on,
            notes=notes.strip() if notes else None,
        )
        return self._repository.add(replacement)

    def get_replacement(self, replacement_id: uuid.UUID) -> MeterReplacement:
        replacement = self._repository.get(replacement_id)
        if not replacement:
            raise NotFoundError(f"Meter replacement with id {replacement_id} not found")
        return replacement

    def get_replacements_by_old_meter(self, old_meter_id: uuid.UUID) -> list[MeterReplacement]:
        return self._repository.get_by_old_meter(old_meter_id)

    def get_replacements_by_new_meter(self, new_meter_id: uuid.UUID) -> list[MeterReplacement]:
        return self._repository.get_by_new_meter(new_meter_id)
