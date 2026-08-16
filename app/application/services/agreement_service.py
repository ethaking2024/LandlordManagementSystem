from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.domain.entities import Agreement
from app.domain.enums import AgreementStatus
from app.domain.value_objects import Money
from app.infrastructure.repositories import (
    AgreementRepository,
    RentalSpaceRepository,
    TenantRepository,
)


class AgreementService:
    def __init__(
        self,
        repository: AgreementRepository,
        tenant_repository: TenantRepository,
        rental_space_repository: RentalSpaceRepository,
    ) -> None:
        self._repository = repository
        self._tenant_repository = tenant_repository
        self._rental_space_repository = rental_space_repository

    def create_agreement(
        self,
        tenant_id: uuid.UUID,
        rental_space_id: uuid.UUID,
        start_date: date,
        monthly_rent: Decimal | str,
        end_date: date | None = None,
        security_deposit: Decimal | str | None = None,
        notes: str | None = None,
    ) -> Agreement:
        if not self._tenant_repository.get(tenant_id):
            raise NotFoundError(f"Tenant with id {tenant_id} not found")
        rental_space = self._rental_space_repository.get(rental_space_id)
        if not rental_space:
            raise NotFoundError(f"Rental space with id {rental_space_id} not found")
        if not rental_space.is_active:
            raise ValidationError("Cannot create agreement for inactive rental space")

        rent_amount = Decimal(str(monthly_rent))
        if rent_amount < 0:
            raise ValidationError("Monthly rent cannot be negative")
        deposit_amount = Decimal(str(security_deposit)) if security_deposit is not None else None
        if deposit_amount is not None and deposit_amount < 0:
            raise ValidationError("Security deposit cannot be negative")
        if end_date and end_date < start_date:
            raise ValidationError("End date cannot be before start date")

        if self._repository.has_overlapping_active_agreement(rental_space_id, start_date, end_date):
            raise ConflictError(
                f"Rental space {rental_space_id} already has an active agreement overlapping with the given dates"
            )

        rent = Money(rent_amount)
        deposit = Money(deposit_amount) if deposit_amount is not None else None

        agreement = Agreement(
            tenant_id=tenant_id,
            rental_space_id=rental_space_id,
            start_date=start_date,
            end_date=end_date,
            monthly_rent=rent,
            security_deposit=deposit,
            status=AgreementStatus.ACTIVE,
            notes=notes.strip() if notes else None,
        )
        return self._repository.add(agreement)

    def get_agreement(self, agreement_id: uuid.UUID) -> Agreement:
        agreement = self._repository.get(agreement_id)
        if not agreement:
            raise NotFoundError(f"Agreement with id {agreement_id} not found")
        return agreement

    def get_all_agreements(self, limit: int = 100, offset: int = 0) -> list[Agreement]:
        return self._repository.get_all(limit=limit, offset=offset)

    def get_agreements_by_tenant(self, tenant_id: uuid.UUID, limit: int = 100, offset: int = 0) -> list[Agreement]:
        return self._repository.get_by_tenant(tenant_id, limit=limit, offset=offset)

    def get_agreements_by_rental_space(self, rental_space_id: uuid.UUID, limit: int = 100, offset: int = 0) -> list[Agreement]:
        return self._repository.get_by_rental_space(rental_space_id, limit=limit, offset=offset)

    def get_active_agreements_by_rental_space(self, rental_space_id: uuid.UUID) -> list[Agreement]:
        return self._repository.get_active_by_rental_space(rental_space_id)

    def get_active_agreements(self, limit: int = 100, offset: int = 0) -> list[Agreement]:
        return self._repository.get_active(limit=limit, offset=offset)

    def end_agreement(self, agreement_id: uuid.UUID, end_date: date) -> Agreement:
        agreement = self.get_agreement(agreement_id)
        if agreement.status != AgreementStatus.ACTIVE:
            raise ValidationError(f"Cannot end agreement with status {agreement.status.value}")
        if end_date < agreement.start_date:
            raise ValidationError("End date cannot be before start date")
        agreement.end_agreement(end_date)
        return self._repository.update(agreement)

    def cancel_agreement(self, agreement_id: uuid.UUID) -> Agreement:
        agreement = self.get_agreement(agreement_id)
        if agreement.status != AgreementStatus.ACTIVE:
            raise ValidationError(f"Cannot cancel agreement with status {agreement.status.value}")
        agreement.cancel_agreement()
        return self._repository.update(agreement)

    def update_agreement(
        self,
        agreement_id: uuid.UUID,
        monthly_rent: Decimal | str | None = None,
        security_deposit: Decimal | str | None = None,
        notes: str | None = None,
    ) -> Agreement:
        agreement = self.get_agreement(agreement_id)
        if monthly_rent is not None:
            rent_amount = Decimal(str(monthly_rent))
            if rent_amount < 0:
                raise ValidationError("Monthly rent cannot be negative")
            agreement.monthly_rent = Money(rent_amount)
        if security_deposit is not None:
            deposit_amount = Decimal(str(security_deposit))
            if deposit_amount < 0:
                raise ValidationError("Security deposit cannot be negative")
            agreement.security_deposit = Money(deposit_amount)
        if notes is not None:
            agreement.notes = notes.strip() if notes else None
        return self._repository.update(agreement)

    def is_rental_space_occupied(self, rental_space_id: uuid.UUID, check_date: date | None = None) -> bool:
        check_date = check_date or date.today()
        active_agreements = self._repository.get_active_by_rental_space(rental_space_id)
        for agreement in active_agreements:
            if agreement.start_date <= check_date:
                if agreement.end_date is None or agreement.end_date >= check_date:
                    return True
        return False
