from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.domain.entities import Agreement, Owner, Property, RentalSpace, Tenant
from app.domain.enums import AgreementStatus, SpaceType
from app.domain.value_objects import Money, PhoneNumber
from app.infrastructure.persistence.models import (
    AgreementModel,
    OwnerModel,
    PropertyModel,
    RentalSpaceModel,
)


def make_owner(name="Alice Owner"):
    return Owner(name=name, phone=PhoneNumber("9800000001"))


def make_property(owner_id, name="Main Building"):
    return Property(owner_id=owner_id, name=name, address="Kathmandu, Nepal")


def make_space(property_id, name="Room 1"):
    return RentalSpace(property_id=property_id, name=name, space_type=SpaceType.ROOM)


def make_tenant(name="Bob Tenant"):
    return Tenant(full_name=name, phone=PhoneNumber("9800000002"))


def make_agreement(tenant_id, space_id):
    return Agreement(
        tenant_id=tenant_id,
        rental_space_id=space_id,
        start_date=date(2026, 1, 1),
        monthly_rent=Money(Decimal("25000")),
        security_deposit=Money(Decimal("50000")),
    )


@pytest.mark.integration
def test_owner_repository_roundtrip(repositories):
    repo = repositories.owner
    created = repo.add(make_owner())
    assert created.id is not None

    fetched = repo.get(created.id)
    assert fetched is not None
    assert fetched.name == "Alice Owner"
    assert fetched.phone.number == "9800000001"
    assert fetched.created_at is not None

    fetched.name = "Alice Renamed"
    repo.update(fetched)
    assert repo.get(created.id).name == "Alice Renamed"

    assert repo.delete(created.id) is True
    assert repo.get(created.id) is None


@pytest.mark.integration
def test_property_rental_space_tenant_agreement_roundtrip(repositories):
    owner = repositories.owner.add(make_owner())
    prop = repositories.property.add(make_property(owner.id))
    space = repositories.rental_space.add(make_space(prop.id))
    tenant = repositories.tenant.add(make_tenant())
    agreement = repositories.agreement.add(make_agreement(tenant.id, space.id))

    assert repositories.property.get(prop.id).name == "Main Building"
    assert repositories.rental_space.get(space.id).space_type == SpaceType.ROOM
    fetched_tenant = repositories.tenant.get(tenant.id)
    assert fetched_tenant.full_name == "Bob Tenant"
    assert fetched_tenant.phone.number == "9800000002"

    fetched_agreement = repositories.agreement.get(agreement.id)
    assert fetched_agreement.status == AgreementStatus.ACTIVE
    assert fetched_agreement.monthly_rent.amount == Decimal("25000.00")
    assert fetched_agreement.security_deposit.amount == Decimal("50000.00")
    assert fetched_agreement.start_date == date(2026, 1, 1)


@pytest.mark.integration
def test_property_get_by_owner(repositories):
    owner = repositories.owner.add(make_owner())
    other = repositories.owner.add(make_owner(name="Other Owner"))
    repositories.property.add(make_property(owner.id, name="Building A"))
    repositories.property.add(make_property(owner.id, name="Building B"))
    repositories.property.add(make_property(other.id, name="Other Building"))

    props = repositories.property.get_by_owner(owner.id)
    assert {p.name for p in props} == {"Building A", "Building B"}


@pytest.mark.integration
def test_tenant_search_by_name(repositories):
    repositories.tenant.add(make_tenant(name="Ramesh Shrestha"))
    repositories.tenant.add(make_tenant(name="Sita Sharma"))

    assert [t.full_name for t in repositories.tenant.search_by_name("ram")] == ["Ramesh Shrestha"]


@pytest.mark.integration
def test_agreement_has_overlapping_active_agreement(repositories):
    owner = repositories.owner.add(make_owner())
    prop = repositories.property.add(make_property(owner.id))
    space = repositories.rental_space.add(make_space(prop.id))
    tenant = repositories.tenant.add(make_tenant())
    repositories.agreement.add(make_agreement(tenant.id, space.id))

    overlapping = date(2026, 1, 15)
    assert repositories.agreement.has_overlapping_active_agreement(space.id, overlapping) is True


@pytest.mark.integration
def test_delete_owner_blocked_by_restrict_fk(repositories):
    owner = repositories.owner.add(make_owner())
    repositories.property.add(make_property(owner.id))

    with pytest.raises(IntegrityError):
        repositories.owner.delete(owner.id)


@pytest.mark.integration
def test_delete_property_blocked_by_restrict_fk(repositories):
    owner = repositories.owner.add(make_owner())
    prop = repositories.property.add(make_property(owner.id))
    repositories.rental_space.add(make_space(prop.id))

    with pytest.raises(IntegrityError):
        repositories.property.delete(prop.id)


@pytest.mark.integration
def test_invalid_agreement_status_rejected_by_check(session):
    owner_model = OwnerModel(name="X", phone="9800000001")
    session.add(owner_model)
    session.flush()
    prop_model = PropertyModel(owner_id=owner_model.id, name="P", address="A")
    session.add(prop_model)
    session.flush()
    space_model = RentalSpaceModel(property_id=prop_model.id, name="S", space_type="room")
    session.add(space_model)
    session.flush()

    bad = AgreementModel(
        tenant_id=owner_model.id,
        rental_space_id=space_model.id,
        start_date=date(2026, 1, 1),
        monthly_rent=Decimal("1000"),
        status="bogus",
    )
    session.add(bad)
    with pytest.raises(IntegrityError):
        session.flush()


@pytest.mark.integration
def test_invalid_space_type_rejected_by_check(session):
    owner_model = OwnerModel(name="X", phone="9800000001")
    session.add(owner_model)
    session.flush()
    prop_model = PropertyModel(owner_id=owner_model.id, name="P", address="A")
    session.add(prop_model)
    session.flush()

    bad = RentalSpaceModel(property_id=prop_model.id, name="S", space_type="penthouse")
    session.add(bad)
    with pytest.raises(IntegrityError):
        session.flush()
