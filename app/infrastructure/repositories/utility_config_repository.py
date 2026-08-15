from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities import UtilityConfig
from app.domain.enums import UtilityType
from app.domain.value_objects import Money
from app.infrastructure.persistence.models import UtilityConfigModel
from app.infrastructure.repositories.base import RepositoryBase


class UtilityConfigRepository(RepositoryBase[UtilityConfig]):
    def __init__(self, session: Session) -> None:
        super().__init__(session)

    def add(self, entity: UtilityConfig) -> UtilityConfig:
        model = self._to_model(entity)
        self.session.add(model)
        self.session.flush()
        return self._to_entity(model)

    def get(self, id: uuid.UUID) -> UtilityConfig | None:
        model = self.session.get(UtilityConfigModel, id)
        return self._to_entity(model) if model else None

    def get_all(self, limit: int = 100, offset: int = 0) -> list[UtilityConfig]:
        stmt = select(UtilityConfigModel).offset(offset).limit(limit)
        models = self.session.scalars(stmt).all()
        return [self._to_entity(m) for m in models]

    def get_by_rental_space(self, rental_space_id: uuid.UUID, limit: int = 100, offset: int = 0) -> list[UtilityConfig]:
        stmt = (
            select(UtilityConfigModel)
            .where(UtilityConfigModel.rental_space_id == rental_space_id)
            .offset(offset)
            .limit(limit)
        )
        models = self.session.scalars(stmt).all()
        return [self._to_entity(m) for m in models]

    def get_by_rental_space_and_utility(self, rental_space_id: uuid.UUID, utility_type: UtilityType) -> UtilityConfig | None:
        stmt = select(UtilityConfigModel).where(
            UtilityConfigModel.rental_space_id == rental_space_id,
            UtilityConfigModel.utility_type == utility_type.value,
        )
        model = self.session.scalar(stmt)
        return self._to_entity(model) if model else None

    def update(self, entity: UtilityConfig) -> UtilityConfig:
        model = self.session.get(UtilityConfigModel, entity.id)
        if not model:
            raise ValueError(f"UtilityConfig with id {entity.id} not found")
        self._update_model(model, entity)
        self.session.flush()
        return self._to_entity(model)

    def delete(self, id: uuid.UUID) -> bool:
        model = self.session.get(UtilityConfigModel, id)
        if not model:
            return False
        self.session.delete(model)
        self.session.flush()
        return True

    def _to_model(self, entity: UtilityConfig) -> UtilityConfigModel:
        return UtilityConfigModel(
            id=entity.id,
            rental_space_id=entity.rental_space_id,
            utility_type=entity.utility_type.value,
            config_type=entity.config_type,
            fixed_amount=entity.fixed_amount.amount if entity.fixed_amount else None,
        )

    def _update_model(self, model: UtilityConfigModel, entity: UtilityConfig) -> None:
        model.rental_space_id = entity.rental_space_id
        model.utility_type = entity.utility_type.value
        model.config_type = entity.config_type
        model.fixed_amount = entity.fixed_amount.amount if entity.fixed_amount else None

    def _to_entity(self, model: UtilityConfigModel) -> UtilityConfig:
        return UtilityConfig(
            id=model.id,
            rental_space_id=model.rental_space_id,
            utility_type=UtilityType(model.utility_type),
            config_type=model.config_type,
            fixed_amount=Money(model.fixed_amount) if model.fixed_amount is not None else None,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
