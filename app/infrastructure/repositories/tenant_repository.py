from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities import Tenant
from app.domain.value_objects import PhoneNumber
from app.infrastructure.persistence.models import TenantModel
from app.infrastructure.repositories.base import RepositoryBase


class TenantRepository(RepositoryBase[Tenant]):
    def __init__(self, session: Session) -> None:
        super().__init__(session)

    def add(self, entity: Tenant) -> Tenant:
        model = self._to_model(entity)
        self.session.add(model)
        self.session.flush()
        return self._to_entity(model)

    def get(self, id: uuid.UUID) -> Tenant | None:
        model = self.session.get(TenantModel, id)
        return self._to_entity(model) if model else None

    def get_all(self, limit: int = 100, offset: int = 0) -> list[Tenant]:
        stmt = select(TenantModel).offset(offset).limit(limit)
        models = self.session.scalars(stmt).all()
        return [self._to_entity(m) for m in models]

    def get_by_phone(self, phone: str) -> Tenant | None:
        stmt = select(TenantModel).where(TenantModel.phone == phone)
        model = self.session.scalar(stmt)
        return self._to_entity(model) if model else None

    def search_by_name(self, name: str, limit: int = 100, offset: int = 0) -> list[Tenant]:
        stmt = select(TenantModel).where(TenantModel.full_name.ilike(f"%{name}%")).offset(offset).limit(limit)
        models = self.session.scalars(stmt).all()
        return [self._to_entity(m) for m in models]

    def update(self, entity: Tenant) -> Tenant:
        model = self.session.get(TenantModel, entity.id)
        if not model:
            raise ValueError(f"Tenant with id {entity.id} not found")
        self._update_model(model, entity)
        self.session.flush()
        return self._to_entity(model)

    def delete(self, id: uuid.UUID) -> bool:
        model = self.session.get(TenantModel, id)
        if not model:
            return False
        self.session.delete(model)
        self.session.flush()
        return True

    def _to_model(self, entity: Tenant) -> TenantModel:
        return TenantModel(
            id=entity.id,
            full_name=entity.full_name,
            phone=entity.phone.number,
            alternate_phone=entity.alternate_phone.number if entity.alternate_phone else None,
            email=entity.email,
            address=entity.address,
            notes=entity.notes,
        )

    def _update_model(self, model: TenantModel, entity: Tenant) -> None:
        model.full_name = entity.full_name
        model.phone = entity.phone.number
        model.alternate_phone = entity.alternate_phone.number if entity.alternate_phone else None
        model.email = entity.email
        model.address = entity.address
        model.notes = entity.notes

    def _to_entity(self, model: TenantModel) -> Tenant:
        return Tenant(
            id=model.id,
            full_name=model.full_name,
            phone=PhoneNumber(model.phone),
            alternate_phone=PhoneNumber(model.alternate_phone) if model.alternate_phone else None,
            email=model.email,
            address=model.address,
            notes=model.notes,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
