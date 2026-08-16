from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.domain.entities import Agreement
from app.domain.enums import AgreementStatus
from app.domain.value_objects import Money
from app.infrastructure.persistence.models import AgreementModel
from app.infrastructure.repositories.base import RepositoryBase


class AgreementRepository(RepositoryBase[Agreement]):
    def __init__(self, session: Session) -> None:
        super().__init__(session)

    def add(self, entity: Agreement) -> Agreement:
        model = self._to_model(entity)
        self.session.add(model)
        self.session.flush()
        return self._to_entity(model)

    def get(self, id: uuid.UUID) -> Agreement | None:
        model = self.session.get(AgreementModel, id)
        return self._to_entity(model) if model else None

    def get_all(self, limit: int = 100, offset: int = 0) -> list[Agreement]:
        stmt = select(AgreementModel).offset(offset).limit(limit)
        models = self.session.scalars(stmt).all()
        return [self._to_entity(m) for m in models]

    def get_by_tenant(self, tenant_id: uuid.UUID, limit: int = 100, offset: int = 0) -> list[Agreement]:
        stmt = select(AgreementModel).where(AgreementModel.tenant_id == tenant_id).offset(offset).limit(limit)
        models = self.session.scalars(stmt).all()
        return [self._to_entity(m) for m in models]

    def get_by_rental_space(self, rental_space_id: uuid.UUID, limit: int = 100, offset: int = 0) -> list[Agreement]:
        stmt = select(AgreementModel).where(AgreementModel.rental_space_id == rental_space_id).offset(offset).limit(limit)
        models = self.session.scalars(stmt).all()
        return [self._to_entity(m) for m in models]

    def get_active_by_rental_space(self, rental_space_id: uuid.UUID) -> list[Agreement]:
        stmt = select(AgreementModel).where(
            AgreementModel.rental_space_id == rental_space_id,
            AgreementModel.status == AgreementStatus.ACTIVE.value,
        )
        models = self.session.scalars(stmt).all()
        return [self._to_entity(m) for m in models]

    def get_active(self, limit: int = 100, offset: int = 0) -> list[Agreement]:
        stmt = (
            select(AgreementModel)
            .where(AgreementModel.status == AgreementStatus.ACTIVE.value)
            .offset(offset)
            .limit(limit)
        )
        models = self.session.scalars(stmt).all()
        return [self._to_entity(m) for m in models]

    def has_overlapping_active_agreement(
        self,
        rental_space_id: uuid.UUID,
        start_date: date,
        end_date: date | None = None,
        exclude_id: uuid.UUID | None = None,
    ) -> bool:
        stmt = select(AgreementModel).where(
            AgreementModel.rental_space_id == rental_space_id,
            AgreementModel.status == AgreementStatus.ACTIVE.value,
        )
        if exclude_id:
            stmt = stmt.where(AgreementModel.id != exclude_id)
        if end_date:
            stmt = stmt.where(
                and_(
                    AgreementModel.start_date <= end_date,
                    (AgreementModel.end_date.is_(None) | (AgreementModel.end_date >= start_date)),
                )
            )
        else:
            stmt = stmt.where(
                and_(
                    AgreementModel.start_date <= start_date,
                    (AgreementModel.end_date.is_(None) | (AgreementModel.end_date >= start_date)),
                )
            )
        return self.session.scalar(stmt) is not None

    def update(self, entity: Agreement) -> Agreement:
        model = self.session.get(AgreementModel, entity.id)
        if not model:
            raise ValueError(f"Agreement with id {entity.id} not found")
        self._update_model(model, entity)
        self.session.flush()
        return self._to_entity(model)

    def delete(self, id: uuid.UUID) -> bool:
        model = self.session.get(AgreementModel, id)
        if not model:
            return False
        self.session.delete(model)
        self.session.flush()
        return True

    def _to_model(self, entity: Agreement) -> AgreementModel:
        return AgreementModel(
            id=entity.id,
            tenant_id=entity.tenant_id,
            rental_space_id=entity.rental_space_id,
            start_date=entity.start_date,
            end_date=entity.end_date,
            monthly_rent=entity.monthly_rent.amount,
            security_deposit=entity.security_deposit.amount if entity.security_deposit else None,
            status=entity.status.value,
            notes=entity.notes,
        )

    def _update_model(self, model: AgreementModel, entity: Agreement) -> None:
        model.tenant_id = entity.tenant_id
        model.rental_space_id = entity.rental_space_id
        model.start_date = entity.start_date
        model.end_date = entity.end_date
        model.monthly_rent = entity.monthly_rent.amount
        model.security_deposit = entity.security_deposit.amount if entity.security_deposit else None
        model.status = entity.status.value
        model.notes = entity.notes

    def _to_entity(self, model: AgreementModel) -> Agreement:
        return Agreement(
            id=model.id,
            tenant_id=model.tenant_id,
            rental_space_id=model.rental_space_id,
            start_date=model.start_date,
            end_date=model.end_date,
            monthly_rent=Money(model.monthly_rent),
            security_deposit=Money(model.security_deposit) if model.security_deposit is not None else None,
            status=AgreementStatus(model.status),
            notes=model.notes,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
