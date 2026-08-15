from __future__ import annotations

import uuid

from app.core.exceptions import NotFoundError, ValidationError
from app.domain.entities import Tenant
from app.domain.value_objects import PhoneNumber
from app.infrastructure.repositories import TenantRepository


class TenantService:
    def __init__(self, repository: TenantRepository) -> None:
        self._repository = repository

    def create_tenant(
        self,
        full_name: str,
        phone: str,
        alternate_phone: str | None = None,
        email: str | None = None,
        address: str | None = None,
        notes: str | None = None,
    ) -> Tenant:
        if not full_name or not full_name.strip():
            raise ValidationError("Tenant full name is required")
        if not phone or not phone.strip():
            raise ValidationError("Tenant phone is required")
        tenant = Tenant(
            full_name=full_name.strip(),
            phone=PhoneNumber(phone),
            alternate_phone=PhoneNumber(alternate_phone) if alternate_phone else None,
            email=email.strip() if email else None,
            address=address.strip() if address else None,
            notes=notes.strip() if notes else None,
        )
        return self._repository.add(tenant)

    def get_tenant(self, tenant_id: uuid.UUID) -> Tenant:
        tenant = self._repository.get(tenant_id)
        if not tenant:
            raise NotFoundError(f"Tenant with id {tenant_id} not found")
        return tenant

    def get_all_tenants(self, limit: int = 100, offset: int = 0) -> list[Tenant]:
        return self._repository.get_all(limit=limit, offset=offset)

    def get_tenant_by_phone(self, phone: str) -> Tenant | None:
        return self._repository.get_by_phone(phone)

    def search_tenants_by_name(self, name: str, limit: int = 100, offset: int = 0) -> list[Tenant]:
        return self._repository.search_by_name(name, limit=limit, offset=offset)

    def update_tenant(
        self,
        tenant_id: uuid.UUID,
        full_name: str | None = None,
        phone: str | None = None,
        alternate_phone: str | None = None,
        email: str | None = None,
        address: str | None = None,
        notes: str | None = None,
    ) -> Tenant:
        tenant = self.get_tenant(tenant_id)
        if full_name is not None:
            if not full_name.strip():
                raise ValidationError("Tenant full name cannot be empty")
            tenant.full_name = full_name.strip()
        if phone is not None:
            if not phone.strip():
                raise ValidationError("Tenant phone cannot be empty")
            tenant.phone = PhoneNumber(phone)
        if alternate_phone is not None:
            tenant.alternate_phone = PhoneNumber(alternate_phone) if alternate_phone else None
        if email is not None:
            tenant.email = email.strip() if email else None
        if address is not None:
            tenant.address = address.strip() if address else None
        if notes is not None:
            tenant.notes = notes.strip() if notes else None
        return self._repository.update(tenant)

    def delete_tenant(self, tenant_id: uuid.UUID) -> bool:
        return self._repository.delete(tenant_id)
