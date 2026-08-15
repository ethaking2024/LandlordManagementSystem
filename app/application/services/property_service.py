from __future__ import annotations

import uuid

from app.core.exceptions import NotFoundError, ValidationError
from app.domain.entities import Property
from app.infrastructure.repositories import OwnerRepository, PropertyRepository


class PropertyService:
    def __init__(self, repository: PropertyRepository, owner_repository: OwnerRepository) -> None:
        self._repository = repository
        self._owner_repository = owner_repository

    def create_property(
        self,
        owner_id: uuid.UUID,
        name: str,
        address: str,
        notes: str | None = None,
    ) -> Property:
        if not self._owner_repository.get(owner_id):
            raise NotFoundError(f"Owner with id {owner_id} not found")
        if not name or not name.strip():
            raise ValidationError("Property name is required")
        if not address or not address.strip():
            raise ValidationError("Property address is required")
        property_ = Property(
            owner_id=owner_id,
            name=name.strip(),
            address=address.strip(),
            notes=notes.strip() if notes else None,
        )
        return self._repository.add(property_)

    def get_property(self, property_id: uuid.UUID) -> Property:
        property_ = self._repository.get(property_id)
        if not property_:
            raise NotFoundError(f"Property with id {property_id} not found")
        return property_

    def get_properties_by_owner(self, owner_id: uuid.UUID, limit: int = 100, offset: int = 0) -> list[Property]:
        return self._repository.get_by_owner(owner_id, limit=limit, offset=offset)

    def get_all_properties(self, limit: int = 100, offset: int = 0) -> list[Property]:
        return self._repository.get_all(limit=limit, offset=offset)

    def update_property(
        self,
        property_id: uuid.UUID,
        name: str | None = None,
        address: str | None = None,
        notes: str | None = None,
    ) -> Property:
        property_ = self.get_property(property_id)
        if name is not None:
            if not name.strip():
                raise ValidationError("Property name cannot be empty")
            property_.name = name.strip()
        if address is not None:
            if not address.strip():
                raise ValidationError("Property address cannot be empty")
            property_.address = address.strip()
        if notes is not None:
            property_.notes = notes.strip() if notes else None
        return self._repository.update(property_)

    def delete_property(self, property_id: uuid.UUID) -> bool:
        return self._repository.delete(property_id)
