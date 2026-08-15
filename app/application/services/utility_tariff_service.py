from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.domain.entities import UtilityTariff
from app.domain.enums import UtilityType
from app.domain.value_objects import Money
from app.infrastructure.repositories import UtilityTariffRepository


class UtilityTariffService:
    def __init__(self, repository: UtilityTariffRepository) -> None:
        self._repository = repository

    def create_tariff(
        self,
        utility_type: UtilityType,
        effective_from: date,
        rate: Decimal | str,
        notes: str | None = None,
    ) -> UtilityTariff:
        if not isinstance(utility_type, UtilityType):
            raise ValidationError(f"Invalid utility type: {utility_type}")
        rate_obj = Money(Decimal(str(rate)))
        if rate_obj.amount < 0:
            raise ValidationError("Tariff rate cannot be negative")
        if self._repository.get_on_effective_date(utility_type, effective_from):
            raise ConflictError(
                f"A {utility_type.value} tariff effective on {effective_from} already exists"
            )
        tariff = UtilityTariff(
            utility_type=utility_type,
            effective_from=effective_from,
            rate=rate_obj,
            notes=notes.strip() if notes else None,
        )
        return self._repository.add(tariff)

    def get_tariff(self, tariff_id: uuid.UUID) -> UtilityTariff:
        tariff = self._repository.get(tariff_id)
        if not tariff:
            raise NotFoundError(f"Utility tariff with id {tariff_id} not found")
        return tariff

    def get_tariffs_by_utility_type(self, utility_type: UtilityType, limit: int = 100, offset: int = 0) -> list[UtilityTariff]:
        return self._repository.get_by_utility_type(utility_type, limit=limit, offset=offset)

    def get_applicable_tariff(self, utility_type: UtilityType, on_date: date) -> UtilityTariff | None:
        """Return the tariff with the latest effective_from at or before on_date."""
        return self._repository.get_applicable_tariff(utility_type, on_date)

    def update_tariff(
        self,
        tariff_id: uuid.UUID,
        rate: Decimal | str | None = None,
        notes: str | None = None,
    ) -> UtilityTariff:
        tariff = self.get_tariff(tariff_id)
        if rate is not None:
            rate_obj = Money(Decimal(str(rate)))
            if rate_obj.amount < 0:
                raise ValidationError("Tariff rate cannot be negative")
            tariff.rate = rate_obj
        if notes is not None:
            tariff.notes = notes.strip() if notes else None
        return self._repository.update(tariff)

    def delete_tariff(self, tariff_id: uuid.UUID) -> bool:
        return self._repository.delete(tariff_id)
