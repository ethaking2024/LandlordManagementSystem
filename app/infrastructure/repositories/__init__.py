from __future__ import annotations

from app.infrastructure.repositories.agreement_repository import AgreementRepository
from app.infrastructure.repositories.base import RepositoryBase
from app.infrastructure.repositories.owner_repository import OwnerRepository
from app.infrastructure.repositories.property_repository import PropertyRepository
from app.infrastructure.repositories.rental_space_repository import RentalSpaceRepository
from app.infrastructure.repositories.tenant_repository import TenantRepository

__all__ = [
    "RepositoryBase",
    "OwnerRepository",
    "PropertyRepository",
    "RentalSpaceRepository",
    "TenantRepository",
    "AgreementRepository",
]
