from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities import UtilityTariff
from app.domain.enums import UtilityType
from app.domain.value_objects import Money
from app.infrastructure.persistence.models import UtilityTariffModel
from app.infrastructure.repositories.base import RepositoryBase


class UtilityTariffRepository(RepositoryBase[UtilityTariff]):
    def __init__(self, session: Session) -> None:
        super().__init__(session)

    def add(self, entity: UtilityTariff) -> UtilityTariff:
        model = self._to_model(entity)
        self.session.add(model)
        self.session.flush()
        return self._to_entity(model)

    def get(self, id: uuid.UUID) -> UtilityTariff | None:
        model = self.session.get(UtilityTariffModel, id)
        return self._to_entity(model) if model else None

    def get_all(self, limit: int = 100, offset: int = 0) -> list[UtilityTariff]:
        stmt = select(UtilityTariffModel).order_by(UtilityTariffModel.effective_from).offset(offset).limit(limit)
        models = self.session.scalars(stmt).all()
        return [self._to_entity(m) for m in models]

    def get_by_utility_type(self, utility_type: UtilityType, limit: int = 100, offset: int = 0) -> list[UtilityTariff]:
        stmt = (
            select(UtilityTariffModel)
            .where(UtilityTariffModel.utility_type == utility_type.value)
            .order_by(UtilityTariffModel.effective_from)
            .offset(offset)
            .limit(limit)
        )
        models = self.session.scalars(stmt).all()
        return [self._to_entity(m) for m in models]

    def get_applicable_tariff(self, utility_type: UtilityType, on_date: date) -> UtilityTariff | None:
        """Return the tariff with the greatest effective_from that is not after on_date."""
        stmt = (
            select(UtilityTariffModel)
            .where(
                UtilityTariffModel.utility_type == utility_type.value,
                UtilityTariffModel.effective_from <= on_date,
            )
            .order_by(UtilityTariffModel.effective_from.desc())
            .limit(1)
        )
        model = self.session.scalar(stmt)
        return self._to_entity(model) if model else None

    def get_on_effective_date(self, utility_type: UtilityType, effective_from: date) -> UtilityTariff | None:
        stmt = select(UtilityTariffModel).where(
            UtilityTariffModel.utility_type == utility_type.value,
            UtilityTariffModel.effective_from == effective_from,
        )
        model = self.session.scalar(stmt)
        return self._to_entity(model) if model else None

    def update(self, entity: UtilityTariff) -> UtilityTariff:
        model = self.session.get(UtilityTariffModel, entity.id)
        if not model:
            raise ValueError(f"UtilityTariff with id {entity.id} not found")
        self._update_model(model, entity)
        self.session.flush()
        return self._to_entity(model)

    def delete(self, id: uuid.UUID) -> bool:
        model = self.session.get(UtilityTariffModel, id)
        if not model:
            return False
        self.session.delete(model)
        self.session.flush()
        return True

    def _to_model(self, entity: UtilityTariff) -> UtilityTariffModel:
        return UtilityTariffModel(
            id=entity.id,
            utility_type=entity.utility_type.value,
            effective_from=entity.effective_from,
            rate=entity.rate.amount,
            notes=entity.notes,
        )

    def _update_model(self, model: UtilityTariffModel, entity: UtilityTariff) -> None:
        model.utility_type = entity.utility_type.value
        model.effective_from = entity.effective_from
        model.rate = entity.rate.amount
        model.notes = entity.notes

    def _to_entity(self, model: UtilityTariffModel) -> UtilityTariff:
        return UtilityTariff(
            id=model.id,
            utility_type=UtilityType(model.utility_type),
            effective_from=model.effective_from,
            rate=Money(model.rate),
            notes=model.notes,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
