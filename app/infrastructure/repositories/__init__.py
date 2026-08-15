from __future__ import annotations

from app.infrastructure.repositories.agreement_repository import AgreementRepository
from app.infrastructure.repositories.base import RepositoryBase
from app.infrastructure.repositories.bill_repository import BillRepository
from app.infrastructure.repositories.meter_reading_repository import MeterReadingRepository
from app.infrastructure.repositories.meter_replacement_repository import MeterReplacementRepository
from app.infrastructure.repositories.meter_repository import MeterRepository
from app.infrastructure.repositories.owner_repository import OwnerRepository
from app.infrastructure.repositories.property_repository import PropertyRepository
from app.infrastructure.repositories.rental_space_repository import RentalSpaceRepository
from app.infrastructure.repositories.tenant_repository import TenantRepository
from app.infrastructure.repositories.utility_config_repository import UtilityConfigRepository
from app.infrastructure.repositories.utility_tariff_repository import UtilityTariffRepository

__all__ = [
    "RepositoryBase",
    "OwnerRepository",
    "PropertyRepository",
    "RentalSpaceRepository",
    "TenantRepository",
    "AgreementRepository",
    "UtilityConfigRepository",
    "MeterRepository",
    "MeterReadingRepository",
    "UtilityTariffRepository",
    "MeterReplacementRepository",
    "BillRepository",
]
