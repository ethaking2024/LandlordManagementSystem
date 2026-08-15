from __future__ import annotations

import uuid
from datetime import date

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.domain.entities import Meter
from app.domain.enums import UtilityType
from app.infrastructure.repositories import MeterRepository, RentalSpaceRepository


class MeterService:
    def __init__(
        self,
        repository: MeterRepository,
        rental_space_repository: RentalSpaceRepository,
    ) -> None:
        self._repository = repository
        self._rental_space_repository = rental_space_repository

    def create_meter(
        self,
        rental_space_id: uuid.UUID,
        utility_type: UtilityType,
        identifier: str,
        installation_date: date,
        notes: str | None = None,
    ) -> Meter:
        if not self._rental_space_repository.get(rental_space_id):
            raise NotFoundError(f"Rental space with id {rental_space_id} not found")
        if not isinstance(utility_type, UtilityType):
            raise ValidationError(f"Invalid utility type: {utility_type}")
        if not identifier or not identifier.strip():
            raise ValidationError("Meter identifier is required")
        if self._repository.get_by_identifier(identifier.strip()):
            raise ConflictError(f"Meter with identifier '{identifier.strip()}' already exists")
        meter = Meter(
            rental_space_id=rental_space_id,
            utility_type=utility_type,
            identifier=identifier.strip(),
            installation_date=installation_date,
            notes=notes.strip() if notes else None,
        )
        return self._repository.add(meter)

    def get_meter(self, meter_id: uuid.UUID) -> Meter:
        meter = self._repository.get(meter_id)
        if not meter:
            raise NotFoundError(f"Meter with id {meter_id} not found")
        return meter

    def get_meters_by_rental_space(self, rental_space_id: uuid.UUID, limit: int = 100, offset: int = 0) -> list[Meter]:
        return self._repository.get_by_rental_space(rental_space_id, limit=limit, offset=offset)

    def get_meters_by_rental_space_and_utility(
        self, rental_space_id: uuid.UUID, utility_type: UtilityType, limit: int = 100, offset: int = 0
    ) -> list[Meter]:
        return self._repository.get_by_rental_space_and_utility(rental_space_id, utility_type, limit=limit, offset=offset)

    def get_active_meters(self, rental_space_id: uuid.UUID) -> list[Meter]:
        return self._repository.get_active_meters(rental_space_id)

    def deactivate_meter(self, meter_id: uuid.UUID) -> Meter:
        meter = self.get_meter(meter_id)
        if not meter.is_active:
            raise ValidationError(f"Meter {meter.identifier} is already inactive")
        meter.deactivate()
        return self._repository.update(meter)

    def activate_meter(self, meter_id: uuid.UUID) -> Meter:
        meter = self.get_meter(meter_id)
        if meter.is_active:
            raise ValidationError(f"Meter {meter.identifier} is already active")
        meter.activate()
        return self._repository.update(meter)

    def update_meter(
        self,
        meter_id: uuid.UUID,
        identifier: str | None = None,
        notes: str | None = None,
    ) -> Meter:
        meter = self.get_meter(meter_id)
        if identifier is not None:
            if not identifier.strip():
                raise ValidationError("Meter identifier cannot be empty")
            existing = self._repository.get_by_identifier(identifier.strip())
            if existing and existing.id != meter.id:
                raise ConflictError(f"Meter with identifier '{identifier.strip()}' already exists")
            meter.identifier = identifier.strip()
        if notes is not None:
            meter.notes = notes.strip() if notes else None
        return self._repository.update(meter)
