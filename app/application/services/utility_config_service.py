from __future__ import annotations

import uuid
from decimal import Decimal

from app.core.exceptions import NotFoundError, ValidationError
from app.domain.entities import UtilityConfig
from app.domain.enums import ElectricityConfigType, UtilityType, WaterConfigType
from app.domain.value_objects import Money
from app.infrastructure.repositories import RentalSpaceRepository, UtilityConfigRepository


class UtilityConfigService:
    def __init__(
        self,
        repository: UtilityConfigRepository,
        rental_space_repository: RentalSpaceRepository,
    ) -> None:
        self._repository = repository
        self._rental_space_repository = rental_space_repository

    def _validate_config_type(self, utility_type: UtilityType, config_type: str) -> str:
        if utility_type == UtilityType.ELECTRICITY:
            try:
                return ElectricityConfigType(config_type).value
            except ValueError as exc:
                raise ValidationError(
                    f"Invalid electricity config type '{config_type}'. Must be one of: fixed, metered"
                ) from exc
        try:
            return WaterConfigType(config_type).value
        except ValueError as exc:
            raise ValidationError(
                f"Invalid water config type '{config_type}'. Must be one of: no_charge, fixed, metered"
            ) from exc

    def set_config(
        self,
        rental_space_id: uuid.UUID,
        utility_type: UtilityType,
        config_type: str,
        fixed_amount: Decimal | str | None = None,
    ) -> UtilityConfig:
        if not self._rental_space_repository.get(rental_space_id):
            raise NotFoundError(f"Rental space with id {rental_space_id} not found")
        if not isinstance(utility_type, UtilityType):
            raise ValidationError(f"Invalid utility type: {utility_type}")

        config_type = self._validate_config_type(utility_type, config_type)

        amount = Decimal(str(fixed_amount)) if fixed_amount is not None else None
        if amount is not None and amount < 0:
            raise ValidationError("Fixed amount cannot be negative")

        is_fixed = config_type in (ElectricityConfigType.FIXED.value, WaterConfigType.FIXED.value)
        if is_fixed and amount is None:
            raise ValidationError("Fixed utility config requires a fixed amount")
        if not is_fixed:
            amount = None

        existing = self._repository.get_by_rental_space_and_utility(rental_space_id, utility_type)
        if existing:
            existing.update_config(config_type, Money(amount) if amount is not None else None)
            return self._repository.update(existing)

        config = UtilityConfig(
            rental_space_id=rental_space_id,
            utility_type=utility_type,
            config_type=config_type,
            fixed_amount=Money(amount) if amount is not None else None,
        )
        return self._repository.add(config)

    def get_config(self, rental_space_id: uuid.UUID, utility_type: UtilityType) -> UtilityConfig:
        config = self._repository.get_by_rental_space_and_utility(rental_space_id, utility_type)
        if not config:
            raise NotFoundError(
                f"Utility config for {utility_type.value} on rental space {rental_space_id} not found"
            )
        return config

    def get_configs_by_rental_space(self, rental_space_id: uuid.UUID) -> list[UtilityConfig]:
        return self._repository.get_by_rental_space(rental_space_id)

    def update_config(
        self,
        config_id: uuid.UUID,
        config_type: str | None = None,
        fixed_amount: Decimal | str | None = None,
    ) -> UtilityConfig:
        config = self._repository.get(config_id)
        if not config:
            raise NotFoundError(f"Utility config with id {config_id} not found")
        new_type = self._validate_config_type(config.utility_type, config_type) if config_type else config.config_type
        amount = Decimal(str(fixed_amount)) if fixed_amount is not None else config.fixed_amount.amount if config.fixed_amount else None
        if amount is not None and amount < 0:
            raise ValidationError("Fixed amount cannot be negative")

        is_fixed = new_type in (ElectricityConfigType.FIXED.value, WaterConfigType.FIXED.value)
        if is_fixed and amount is None:
            raise ValidationError("Fixed utility config requires a fixed amount")
        if not is_fixed:
            amount = None

        if self._repository.get_by_rental_space_and_utility(config.rental_space_id, config.utility_type) is None:
            raise NotFoundError(f"Utility config with id {config_id} not found")

        config.update_config(new_type, Money(amount) if amount is not None else None)
        return self._repository.update(config)

    def delete_config(self, config_id: uuid.UUID) -> bool:
        return self._repository.delete(config_id)
