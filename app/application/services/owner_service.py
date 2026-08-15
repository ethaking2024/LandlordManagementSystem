from __future__ import annotations

import uuid

from app.core.exceptions import NotFoundError, ValidationError
from app.domain.entities import Owner
from app.domain.value_objects import PhoneNumber
from app.infrastructure.repositories import OwnerRepository


class OwnerService:
    def __init__(self, repository: OwnerRepository) -> None:
        self._repository = repository

    def create_owner(
        self,
        name: str,
        phone: str | None = None,
        email: str | None = None,
        address: str | None = None,
        notes: str | None = None,
    ) -> Owner:
        if not name or not name.strip():
            raise ValidationError("Owner name is required")
        phone_obj = PhoneNumber(phone) if phone else None
        owner = Owner(
            name=name.strip(),
            phone=phone_obj,
            email=email.strip() if email else None,
            address=address.strip() if address else None,
            notes=notes.strip() if notes else None,
        )
        return self._repository.add(owner)

    def get_owner(self, owner_id: uuid.UUID) -> Owner:
        owner = self._repository.get(owner_id)
        if not owner:
            raise NotFoundError(f"Owner with id {owner_id} not found")
        return owner

    def get_all_owners(self, limit: int = 100, offset: int = 0) -> list[Owner]:
        return self._repository.get_all(limit=limit, offset=offset)

    def update_owner(
        self,
        owner_id: uuid.UUID,
        name: str | None = None,
        phone: str | None = None,
        email: str | None = None,
        address: str | None = None,
        notes: str | None = None,
    ) -> Owner:
        owner = self.get_owner(owner_id)
        if name is not None:
            if not name.strip():
                raise ValidationError("Owner name cannot be empty")
            owner.name = name.strip()
        if phone is not None:
            owner.phone = PhoneNumber(phone) if phone else None
        if email is not None:
            owner.email = email.strip() if email else None
        if address is not None:
            owner.address = address.strip() if address else None
        if notes is not None:
            owner.notes = notes.strip() if notes else None
        return self._repository.update(owner)

    def delete_owner(self, owner_id: uuid.UUID) -> bool:
        return self._repository.delete(owner_id)
