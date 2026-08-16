from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.application.services import (
    AgreementService,
    OwnerService,
    PropertyService,
    RentalSpaceService,
    TenantService,
)
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.domain.entities import Agreement, Owner, Property, RentalSpace, Tenant
from app.domain.enums import AgreementStatus, SpaceType
from app.domain.value_objects import Money, PhoneNumber


class TestOwnerService:
    @pytest.fixture
    def mock_repo(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def service(self, mock_repo: MagicMock) -> OwnerService:
        return OwnerService(mock_repo)

    def test_create_owner_valid(self, service: OwnerService, mock_repo: MagicMock) -> None:
        mock_owner = Owner(name="Test Owner", phone=PhoneNumber("9812345678"))
        mock_repo.add.return_value = mock_owner

        result = service.create_owner("Test Owner", "9812345678")

        assert result == mock_owner
        mock_repo.add.assert_called_once()

    def test_create_owner_rejects_empty_name(self, service: OwnerService) -> None:
        with pytest.raises(ValidationError, match="Owner name is required"):
            service.create_owner("")

    def test_get_owner(self, service: OwnerService, mock_repo: MagicMock) -> None:
        owner_id = uuid.uuid4()
        mock_owner = Owner(name="Test Owner")
        mock_repo.get.return_value = mock_owner

        result = service.get_owner(owner_id)

        assert result == mock_owner
        mock_repo.get.assert_called_once_with(owner_id)

    def test_get_owner_not_found(self, service: OwnerService, mock_repo: MagicMock) -> None:
        mock_repo.get.return_value = None
        with pytest.raises(NotFoundError):
            service.get_owner(uuid.uuid4())

    def test_update_owner(self, service: OwnerService, mock_repo: MagicMock) -> None:
        owner_id = uuid.uuid4()
        mock_owner = Owner(name="Updated")
        mock_repo.get.return_value = mock_owner
        mock_repo.update.return_value = mock_owner

        result = service.update_owner(owner_id, name="Updated")

        assert result == mock_owner
        mock_repo.get.assert_called_once_with(owner_id)
        mock_repo.update.assert_called_once()


class TestPropertyService:
    @pytest.fixture
    def mock_property_repo(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def mock_owner_repo(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def service(self, mock_property_repo: MagicMock, mock_owner_repo: MagicMock) -> PropertyService:
        return PropertyService(mock_property_repo, mock_owner_repo)

    def test_create_property_valid(self, service: PropertyService, mock_property_repo: MagicMock, mock_owner_repo: MagicMock) -> None:
        owner_id = uuid.uuid4()
        mock_owner = Owner(name="Owner")
        mock_property = Property(owner_id=owner_id, name="My House", address="Kathmandu")
        mock_owner_repo.get.return_value = mock_owner
        mock_property_repo.add.return_value = mock_property

        result = service.create_property(owner_id, "My House", "Kathmandu")

        assert result == mock_property
        mock_owner_repo.get.assert_called_once_with(owner_id)
        mock_property_repo.add.assert_called_once()

    def test_create_property_rejects_missing_owner(self, service: PropertyService, mock_owner_repo: MagicMock) -> None:
        mock_owner_repo.get.return_value = None
        with pytest.raises(NotFoundError):
            service.create_property(uuid.uuid4(), "House", "Address")

    def test_create_property_rejects_empty_name(self, service: PropertyService, mock_owner_repo: MagicMock) -> None:
        mock_owner_repo.get.return_value = Owner(name="Owner")
        with pytest.raises(ValidationError, match="Property name is required"):
            service.create_property(uuid.uuid4(), "", "Address")

    def test_create_property_rejects_empty_address(self, service: PropertyService, mock_owner_repo: MagicMock) -> None:
        mock_owner_repo.get.return_value = Owner(name="Owner")
        with pytest.raises(ValidationError, match="Property address is required"):
            service.create_property(uuid.uuid4(), "House", "")


class TestRentalSpaceService:
    @pytest.fixture
    def mock_space_repo(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def mock_property_repo(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def service(self, mock_space_repo: MagicMock, mock_property_repo: MagicMock) -> RentalSpaceService:
        return RentalSpaceService(mock_space_repo, mock_property_repo)

    def test_create_rental_space_valid(self, service: RentalSpaceService, mock_space_repo: MagicMock, mock_property_repo: MagicMock) -> None:
        property_id = uuid.uuid4()
        mock_property = Property(owner_id=uuid.uuid4(), name="House", address="Kathmandu")
        mock_space = RentalSpace(property_id=property_id, name="First Floor", space_type=SpaceType.FLAT)
        mock_property_repo.get.return_value = mock_property
        mock_space_repo.add.return_value = mock_space

        result = service.create_rental_space(property_id, "First Floor", SpaceType.FLAT)

        assert result == mock_space
        mock_property_repo.get.assert_called_once_with(property_id)
        mock_space_repo.add.assert_called_once()

    def test_create_rental_space_rejects_missing_property(self, service: RentalSpaceService, mock_property_repo: MagicMock) -> None:
        mock_property_repo.get.return_value = None
        with pytest.raises(NotFoundError):
            service.create_rental_space(uuid.uuid4(), "Space", SpaceType.ROOM)

    def test_create_rental_space_rejects_empty_name(self, service: RentalSpaceService, mock_property_repo: MagicMock) -> None:
        mock_property_repo.get.return_value = Property(owner_id=uuid.uuid4(), name="House", address="Address")
        with pytest.raises(ValidationError, match="Rental space name is required"):
            service.create_rental_space(uuid.uuid4(), "", SpaceType.ROOM)

    def test_get_all_rental_spaces_delegates_to_repository(
        self, service: RentalSpaceService, mock_space_repo: MagicMock
    ) -> None:
        mock_space = RentalSpace(property_id=uuid.uuid4(), name="First Floor", space_type=SpaceType.FLAT)
        mock_space_repo.get_all.return_value = [mock_space]

        result = service.get_all_rental_spaces()

        assert result == [mock_space]
        mock_space_repo.get_all.assert_called_once_with(limit=100, offset=0)


class TestTenantService:
    @pytest.fixture
    def mock_repo(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def service(self, mock_repo: MagicMock) -> TenantService:
        return TenantService(mock_repo)

    def test_create_tenant_valid(self, service: TenantService, mock_repo: MagicMock) -> None:
        mock_tenant = Tenant(full_name="Jane Smith", phone=PhoneNumber("9812345678"))
        mock_repo.add.return_value = mock_tenant

        result = service.create_tenant("Jane Smith", "9812345678")

        assert result == mock_tenant
        mock_repo.add.assert_called_once()

    def test_create_tenant_rejects_empty_name(self, service: TenantService) -> None:
        with pytest.raises(ValidationError, match="Tenant full name is required"):
            service.create_tenant("", "9812345678")

    def test_create_tenant_rejects_empty_phone(self, service: TenantService) -> None:
        with pytest.raises(ValidationError, match="Tenant phone is required"):
            service.create_tenant("Jane Smith", "")

    def test_get_tenant(self, service: TenantService, mock_repo: MagicMock) -> None:
        tenant_id = uuid.uuid4()
        mock_tenant = Tenant(full_name="Jane Smith", phone=PhoneNumber("9812345678"))
        mock_repo.get.return_value = mock_tenant

        result = service.get_tenant(tenant_id)

        assert result == mock_tenant
        mock_repo.get.assert_called_once_with(tenant_id)

    def test_get_tenant_by_phone(self, service: TenantService, mock_repo: MagicMock) -> None:
        mock_tenant = Tenant(full_name="Jane Smith", phone=PhoneNumber("9812345678"))
        mock_repo.get_by_phone.return_value = mock_tenant

        result = service.get_tenant_by_phone("9812345678")

        assert result == mock_tenant
        mock_repo.get_by_phone.assert_called_once_with("9812345678")


class TestAgreementService:
    @pytest.fixture
    def mock_agreement_repo(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def mock_tenant_repo(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def mock_space_repo(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def service(
        self,
        mock_agreement_repo: MagicMock,
        mock_tenant_repo: MagicMock,
        mock_space_repo: MagicMock,
    ) -> AgreementService:
        return AgreementService(mock_agreement_repo, mock_tenant_repo, mock_space_repo)

    def test_create_agreement_valid(
        self,
        service: AgreementService,
        mock_agreement_repo: MagicMock,
        mock_tenant_repo: MagicMock,
        mock_space_repo: MagicMock,
    ) -> None:
        tenant_id = uuid.uuid4()
        rental_space_id = uuid.uuid4()
        mock_tenant = Tenant(full_name="Tenant", phone=PhoneNumber("9812345678"))
        mock_space = RentalSpace(property_id=uuid.uuid4(), name="Space", space_type=SpaceType.ROOM, is_active=True)
        mock_agreement = Agreement(
            tenant_id=tenant_id,
            rental_space_id=rental_space_id,
            start_date=date(2024, 1, 1),
            monthly_rent=Money(Decimal("15000.00")),
        )
        mock_tenant_repo.get.return_value = mock_tenant
        mock_space_repo.get.return_value = mock_space
        mock_agreement_repo.has_overlapping_active_agreement.return_value = False
        mock_agreement_repo.add.return_value = mock_agreement

        result = service.create_agreement(
            tenant_id=tenant_id,
            rental_space_id=rental_space_id,
            start_date=date(2024, 1, 1),
            monthly_rent=Decimal("15000.00"),
        )

        assert result == mock_agreement
        mock_tenant_repo.get.assert_called_once_with(tenant_id)
        mock_space_repo.get.assert_called_once_with(rental_space_id)
        mock_agreement_repo.has_overlapping_active_agreement.assert_called_once()
        mock_agreement_repo.add.assert_called_once()

    def test_create_agreement_rejects_missing_tenant(self, service: AgreementService, mock_tenant_repo: MagicMock) -> None:
        mock_tenant_repo.get.return_value = None
        with pytest.raises(NotFoundError):
            service.create_agreement(uuid.uuid4(), uuid.uuid4(), date(2024, 1, 1), Decimal("15000.00"))

    def test_create_agreement_rejects_missing_space(self, service: AgreementService, mock_tenant_repo: MagicMock, mock_space_repo: MagicMock) -> None:
        mock_tenant_repo.get.return_value = Tenant(full_name="Tenant", phone=PhoneNumber("9812345678"))
        mock_space_repo.get.return_value = None
        with pytest.raises(NotFoundError):
            service.create_agreement(uuid.uuid4(), uuid.uuid4(), date(2024, 1, 1), Decimal("15000.00"))

    def test_create_agreement_rejects_inactive_space(self, service: AgreementService, mock_tenant_repo: MagicMock, mock_space_repo: MagicMock) -> None:
        mock_tenant_repo.get.return_value = Tenant(full_name="Tenant", phone=PhoneNumber("9812345678"))
        mock_space = RentalSpace(property_id=uuid.uuid4(), name="Space", space_type=SpaceType.ROOM, is_active=False)
        mock_space_repo.get.return_value = mock_space
        with pytest.raises(ValidationError, match="Cannot create agreement for inactive rental space"):
            service.create_agreement(uuid.uuid4(), uuid.uuid4(), date(2024, 1, 1), Decimal("15000.00"))

    def test_create_agreement_rejects_negative_rent(self, service: AgreementService, mock_tenant_repo: MagicMock, mock_space_repo: MagicMock) -> None:
        mock_tenant_repo.get.return_value = Tenant(full_name="Tenant", phone=PhoneNumber("9812345678"))
        mock_space_repo.get.return_value = RentalSpace(property_id=uuid.uuid4(), name="Space", space_type=SpaceType.ROOM, is_active=True)
        with pytest.raises(ValidationError, match="Monthly rent cannot be negative"):
            service.create_agreement(uuid.uuid4(), uuid.uuid4(), date(2024, 1, 1), Decimal("-1000.00"))

    def test_create_agreement_rejects_negative_deposit(self, service: AgreementService, mock_tenant_repo: MagicMock, mock_space_repo: MagicMock) -> None:
        mock_tenant_repo.get.return_value = Tenant(full_name="Tenant", phone=PhoneNumber("9812345678"))
        mock_space_repo.get.return_value = RentalSpace(property_id=uuid.uuid4(), name="Space", space_type=SpaceType.ROOM, is_active=True)
        with pytest.raises(ValidationError, match="Security deposit cannot be negative"):
            service.create_agreement(uuid.uuid4(), uuid.uuid4(), date(2024, 1, 1), Decimal("15000.00"), security_deposit=Decimal("-5000.00"))

    def test_create_agreement_rejects_end_before_start(self, service: AgreementService, mock_tenant_repo: MagicMock, mock_space_repo: MagicMock) -> None:
        mock_tenant_repo.get.return_value = Tenant(full_name="Tenant", phone=PhoneNumber("9812345678"))
        mock_space_repo.get.return_value = RentalSpace(property_id=uuid.uuid4(), name="Space", space_type=SpaceType.ROOM, is_active=True)
        with pytest.raises(ValidationError, match="End date cannot be before start date"):
            service.create_agreement(uuid.uuid4(), uuid.uuid4(), date(2024, 12, 31), Decimal("15000.00"), end_date=date(2024, 1, 1))

    def test_create_agreement_rejects_overlapping_active(
        self,
        service: AgreementService,
        mock_tenant_repo: MagicMock,
        mock_space_repo: MagicMock,
        mock_agreement_repo: MagicMock,
    ) -> None:
        mock_tenant_repo.get.return_value = Tenant(full_name="Tenant", phone=PhoneNumber("9812345678"))
        mock_space_repo.get.return_value = RentalSpace(property_id=uuid.uuid4(), name="Space", space_type=SpaceType.ROOM, is_active=True)
        mock_agreement_repo.has_overlapping_active_agreement.return_value = True
        with pytest.raises(ConflictError, match="already has an active agreement overlapping"):
            service.create_agreement(uuid.uuid4(), uuid.uuid4(), date(2024, 1, 1), Decimal("15000.00"))

    def test_end_agreement_valid(
        self,
        service: AgreementService,
        mock_agreement_repo: MagicMock,
    ) -> None:
        agreement_id = uuid.uuid4()
        mock_agreement = Agreement(
            tenant_id=uuid.uuid4(),
            rental_space_id=uuid.uuid4(),
            start_date=date(2024, 1, 1),
            monthly_rent=Money(Decimal("15000.00")),
            status=AgreementStatus.ACTIVE,
        )
        mock_agreement_repo.get.return_value = mock_agreement
        mock_agreement_repo.update.return_value = mock_agreement

        result = service.end_agreement(agreement_id, date(2024, 6, 30))

        assert result == mock_agreement
        assert mock_agreement.end_date == date(2024, 6, 30)
        assert mock_agreement.status == AgreementStatus.ENDED
        mock_agreement_repo.update.assert_called_once()

    def test_end_agreement_rejects_non_active(self, service: AgreementService, mock_agreement_repo: MagicMock) -> None:
        agreement_id = uuid.uuid4()
        mock_agreement = Agreement(
            tenant_id=uuid.uuid4(),
            rental_space_id=uuid.uuid4(),
            start_date=date(2024, 1, 1),
            monthly_rent=Money(Decimal("15000.00")),
            status=AgreementStatus.ENDED,
        )
        mock_agreement_repo.get.return_value = mock_agreement
        with pytest.raises(ValidationError, match="Cannot end agreement with status"):
            service.end_agreement(agreement_id, date(2024, 6, 30))

    def test_cancel_agreement_valid(
        self,
        service: AgreementService,
        mock_agreement_repo: MagicMock,
    ) -> None:
        agreement_id = uuid.uuid4()
        mock_agreement = Agreement(
            tenant_id=uuid.uuid4(),
            rental_space_id=uuid.uuid4(),
            start_date=date(2024, 1, 1),
            monthly_rent=Money(Decimal("15000.00")),
            status=AgreementStatus.ACTIVE,
        )
        mock_agreement_repo.get.return_value = mock_agreement
        mock_agreement_repo.update.return_value = mock_agreement

        result = service.cancel_agreement(agreement_id)

        assert result == mock_agreement
        assert mock_agreement.status == AgreementStatus.CANCELLED
        mock_agreement_repo.update.assert_called_once()

    def test_is_rental_space_occupied(
        self,
        service: AgreementService,
        mock_agreement_repo: MagicMock,
    ) -> None:
        rental_space_id = uuid.uuid4()
        mock_agreement = Agreement(
            tenant_id=uuid.uuid4(),
            rental_space_id=rental_space_id,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            monthly_rent=Money(Decimal("15000.00")),
            status=AgreementStatus.ACTIVE,
        )
        mock_agreement_repo.get_active_by_rental_space.return_value = [mock_agreement]

        result = service.is_rental_space_occupied(rental_space_id, date(2024, 6, 15))

        assert result is True
        mock_agreement_repo.get_active_by_rental_space.assert_called_once_with(rental_space_id)

    def test_get_active_agreements_delegates_to_repository(
        self,
        service: AgreementService,
        mock_agreement_repo: MagicMock,
    ) -> None:
        mock_agreement = Agreement(
            tenant_id=uuid.uuid4(),
            rental_space_id=uuid.uuid4(),
            start_date=date(2024, 1, 1),
            monthly_rent=Money(Decimal("15000.00")),
            status=AgreementStatus.ACTIVE,
        )
        mock_agreement_repo.get_active.return_value = [mock_agreement]

        result = service.get_active_agreements()

        assert result == [mock_agreement]
        mock_agreement_repo.get_active.assert_called_once_with(limit=100, offset=0)
