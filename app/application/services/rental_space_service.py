from __future__ import annotations

import uuid

from app.core.exceptions import NotFoundError, ValidationError
from app.domain.entities import RentalSpace
from app.domain.enums import SpaceType
from app.infrastructure.repositories import PropertyRepository, RentalSpaceRepository


class RentalSpaceService:
    def __init__(
        self,
        repository: RentalSpaceRepository,
        property_repository: PropertyRepository,
    ) -> None:
        self._repository = repository
        self._property_repository = property_repository

    def create_rental_space(
        self,
        property_id: uuid.UUID,
        name: str,
        space_type: SpaceType,
        floor_label: str | None = None,
        description: str | None = None,
    ) -> RentalSpace:
        if not self._property_repository.get(property_id):
            raise NotFoundError(f"Property with id {property_id} not found")
        if not name or not name.strip():
            raise ValidationError("Rental space name is required")
        if not isinstance(space_type, SpaceType):
            raise ValidationError(f"Invalid space type: {space_type}")
        rental_space = RentalSpace(
            property_id=property_id,
            name=name.strip(),
            space_type=space_type,
            floor_label=floor_label.strip() if floor_label else None,
            description=description.strip() if description else None,
        )
        return self._repository.add(rental_space)

    def get_rental_space(self, rental_space_id: uuid.UUID) -> RentalSpace:
        rental_space = self._repository.get(rental_space_id)
        if not rental_space:
            raise NotFoundError(f"Rental space with id {rental_space_id} not found")
        return rental_space

    def get_rental_spaces_by_property(
        self,
        property_id: uuid.UUID,
        active_only: bool = True,
        limit: int = 100,
        offset: int = 0,
    ) -> list[RentalSpace]:
        if not self._property_repository.get(property_id):
            raise NotFoundError(f"Property with id {property_id} not found")
        return self._repository.get_by_property(property_id, active_only=active_only, limit=limit, offset=offset)

    def get_active_rental_spaces(self, property_id: uuid.UUID) -> list[RentalSpace]:
        return self._repository.get_active_spaces(property_id)

    def get_all_rental_spaces(self, limit: int = 100, offset: int = 0) -> list[RentalSpace]:
        return self._repository.get_all(limit=limit, offset=offset)

    def update_rental_space(
        self,
        rental_space_id: uuid.UUID,
        name: str | None = None,
        space_type: SpaceType | None = None,
        floor_label: str | None = None,
        description: str | None = None,
        is_active: bool | None = None,
    ) -> RentalSpace:
        rental_space = self.get_rental_space(rental_space_id)
        if name is not None:
            if not name.strip():
                raise ValidationError("Rental space name cannot be empty")
            rental_space.name = name.strip()
        if space_type is not None:
            if not isinstance(space_type, SpaceType):
                raise ValidationError(f"Invalid space type: {space_type}")
            rental_space.space_type = space_type
        if floor_label is not None:
            rental_space.floor_label = floor_label.strip() if floor_label else None
        if description is not None:
            rental_space.description = description.strip() if description else None
        if is_active is not None:
            rental_space.is_active = is_active
        return self._repository.update(rental_space)

    def delete_rental_space(self, rental_space_id: uuid.UUID) -> bool:
        return self._repository.delete(rental_space_id)
