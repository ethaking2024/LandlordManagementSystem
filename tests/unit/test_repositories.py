from __future__ import annotations

import uuid
from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from app.domain.entities import Owner
from app.domain.value_objects import PhoneNumber
from app.infrastructure.persistence.models import (
    OwnerModel,
)
from app.infrastructure.repositories import (
    AgreementRepository,
    OwnerRepository,
    PropertyRepository,
    RentalSpaceRepository,
    TenantRepository,
)


class TestOwnerRepository:
    @pytest.fixture
    def mock_session(self) -> MagicMock:
        return MagicMock(spec=Session)

    @pytest.fixture
    def repository(self, mock_session: MagicMock) -> OwnerRepository:
        return OwnerRepository(mock_session)

    def test_add_owner(self, repository: OwnerRepository, mock_session: MagicMock) -> None:
        owner = Owner(name="Test Owner", phone=PhoneNumber("9812345678"))
        mock_session.get.return_value = None

        with patch.object(repository, "_to_model", return_value=MagicMock(spec=OwnerModel)) as mock_to_model:
            mock_model = MagicMock(spec=OwnerModel)
            mock_model.id = owner.id
            mock_model.phone = "9812345678"
            mock_to_model.return_value = mock_model

            _ = repository.add(owner)

            mock_session.add.assert_called_once()
            mock_session.flush.assert_called_once()

    def test_get_owner(self, repository: OwnerRepository, mock_session: MagicMock) -> None:
        owner_id = uuid.uuid4()
        mock_model = MagicMock(spec=OwnerModel)
        mock_model.id = owner_id
        mock_model.name = "Test Owner"
        mock_model.phone = "9812345678"
        mock_model.email = None
        mock_model.address = None
        mock_model.notes = None
        mock_model.created_at = None
        mock_model.updated_at = None

        mock_session.get.return_value = mock_model

        result = repository.get(owner_id)

        assert result is not None
        assert result.id == owner_id
        assert result.name == "Test Owner"
        mock_session.get.assert_called_once_with(OwnerModel, owner_id)

    def test_get_owner_not_found(self, repository: OwnerRepository, mock_session: MagicMock) -> None:
        mock_session.get.return_value = None
        result = repository.get(uuid.uuid4())
        assert result is None

    def test_get_all_owners(self, repository: OwnerRepository, mock_session: MagicMock) -> None:
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_session.scalars.return_value = mock_scalars

        result = repository.get_all()

        assert result == []
        mock_session.scalars.assert_called_once()

    def test_update_owner(self, repository: OwnerRepository, mock_session: MagicMock) -> None:
        owner = Owner(name="Updated Owner")
        mock_model = MagicMock(spec=OwnerModel)
        mock_session.get.return_value = mock_model

        _ = repository.update(owner)

        mock_session.get.assert_called_once_with(OwnerModel, owner.id)
        mock_session.flush.assert_called_once()

    def test_update_owner_not_found(self, repository: OwnerRepository, mock_session: MagicMock) -> None:
        mock_session.get.return_value = None
        owner = Owner(name="Test")
        with pytest.raises(ValueError, match="not found"):
            repository.update(owner)

    def test_delete_owner(self, repository: OwnerRepository, mock_session: MagicMock) -> None:
        mock_model = MagicMock(spec=OwnerModel)
        mock_session.get.return_value = mock_model

        result = repository.delete(uuid.uuid4())

        assert result is True
        mock_session.delete.assert_called_once()
        mock_session.flush.assert_called_once()

    def test_delete_owner_not_found(self, repository: OwnerRepository, mock_session: MagicMock) -> None:
        mock_session.get.return_value = None
        result = repository.delete(uuid.uuid4())
        assert result is False


class TestPropertyRepository:
    @pytest.fixture
    def mock_session(self) -> MagicMock:
        return MagicMock(spec=Session)

    @pytest.fixture
    def repository(self, mock_session: MagicMock) -> PropertyRepository:
        return PropertyRepository(mock_session)

    def test_get_by_owner(self, repository: PropertyRepository, mock_session: MagicMock) -> None:
        owner_id = uuid.uuid4()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_session.scalars.return_value = mock_scalars

        result = repository.get_by_owner(owner_id)

        assert result == []
        mock_session.scalars.assert_called_once()


class TestRentalSpaceRepository:
    @pytest.fixture
    def mock_session(self) -> MagicMock:
        return MagicMock(spec=Session)

    @pytest.fixture
    def repository(self, mock_session: MagicMock) -> RentalSpaceRepository:
        return RentalSpaceRepository(mock_session)

    def test_get_by_property(self, repository: RentalSpaceRepository, mock_session: MagicMock) -> None:
        property_id = uuid.uuid4()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_session.scalars.return_value = mock_scalars

        result = repository.get_by_property(property_id)

        assert result == []
        mock_session.scalars.assert_called_once()

    def test_get_active_spaces(self, repository: RentalSpaceRepository, mock_session: MagicMock) -> None:
        property_id = uuid.uuid4()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_session.scalars.return_value = mock_scalars

        result = repository.get_active_spaces(property_id)

        assert result == []
        mock_session.scalars.assert_called_once()


class TestTenantRepository:
    @pytest.fixture
    def mock_session(self) -> MagicMock:
        return MagicMock(spec=Session)

    @pytest.fixture
    def repository(self, mock_session: MagicMock) -> TenantRepository:
        return TenantRepository(mock_session)

    def test_get_by_phone(self, repository: TenantRepository, mock_session: MagicMock) -> None:
        mock_session.scalar.return_value = None

        result = repository.get_by_phone("9812345678")

        assert result is None
        mock_session.scalar.assert_called_once()

    def test_search_by_name(self, repository: TenantRepository, mock_session: MagicMock) -> None:
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_session.scalars.return_value = mock_scalars

        result = repository.search_by_name("John")

        assert result == []
        mock_session.scalars.assert_called_once()


class TestAgreementRepository:
    @pytest.fixture
    def mock_session(self) -> MagicMock:
        return MagicMock(spec=Session)

    @pytest.fixture
    def repository(self, mock_session: MagicMock) -> AgreementRepository:
        return AgreementRepository(mock_session)

    def test_get_by_tenant(self, repository: AgreementRepository, mock_session: MagicMock) -> None:
        tenant_id = uuid.uuid4()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_session.scalars.return_value = mock_scalars

        result = repository.get_by_tenant(tenant_id)

        assert result == []
        mock_session.scalars.assert_called_once()

    def test_get_by_rental_space(self, repository: AgreementRepository, mock_session: MagicMock) -> None:
        rental_space_id = uuid.uuid4()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_session.scalars.return_value = mock_scalars

        result = repository.get_by_rental_space(rental_space_id)

        assert result == []
        mock_session.scalars.assert_called_once()

    def test_get_active_by_rental_space(self, repository: AgreementRepository, mock_session: MagicMock) -> None:
        rental_space_id = uuid.uuid4()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_session.scalars.return_value = mock_scalars

        result = repository.get_active_by_rental_space(rental_space_id)

        assert result == []
        mock_session.scalars.assert_called_once()

    def test_get_active(self, repository: AgreementRepository, mock_session: MagicMock) -> None:
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_session.scalars.return_value = mock_scalars

        result = repository.get_active()

        assert result == []
        mock_session.scalars.assert_called_once()

    def test_has_overlapping_active_agreement(self, repository: AgreementRepository, mock_session: MagicMock) -> None:
        rental_space_id = uuid.uuid4()
        mock_session.scalar.return_value = None

        result = repository.has_overlapping_active_agreement(
            rental_space_id, date(2024, 1, 1), date(2024, 12, 31)
        )

        assert result is False
        mock_session.scalar.assert_called_once()
