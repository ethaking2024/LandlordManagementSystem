from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

import pytest

from app.domain.entities import Agreement, Owner, Property, RentalSpace, Tenant
from app.domain.enums import AgreementStatus, SpaceType
from app.domain.value_objects import Money, PhoneNumber


class TestOwner:
    def test_create_owner_valid(self) -> None:
        owner = Owner(name="John Doe", phone=PhoneNumber("+977-9812345678"))
        assert owner.name == "John Doe"
        assert owner.phone is not None
        assert owner.phone.number == "+9779812345678"
        assert isinstance(owner.id, uuid.UUID)
        assert isinstance(owner.created_at, datetime)

    def test_create_owner_name_required(self) -> None:
        with pytest.raises(ValueError, match="Owner name is required"):
            Owner(name="")

    def test_create_owner_name_whitespace_only(self) -> None:
        with pytest.raises(ValueError, match="Owner name is required"):
            Owner(name="   ")

    def test_create_owner_trims_name(self) -> None:
        owner = Owner(name="  John Doe  ")
        assert owner.name == "John Doe"


class TestProperty:
    def test_create_property_valid(self) -> None:
        owner_id = uuid.uuid4()
        prop = Property(owner_id=owner_id, name="My House", address="Kathmandu, Nepal")
        assert prop.owner_id == owner_id
        assert prop.name == "My House"
        assert prop.address == "Kathmandu, Nepal"
        assert isinstance(prop.id, uuid.UUID)

    def test_create_property_name_required(self) -> None:
        with pytest.raises(ValueError, match="Property name is required"):
            Property(owner_id=uuid.uuid4(), name="", address="Address")

    def test_create_property_address_required(self) -> None:
        with pytest.raises(ValueError, match="Property address is required"):
            Property(owner_id=uuid.uuid4(), name="Name", address="")


class TestRentalSpace:
    def test_create_rental_space_valid(self) -> None:
        property_id = uuid.uuid4()
        space = RentalSpace(property_id=property_id, name="First Floor Flat", space_type=SpaceType.FLAT)
        assert space.property_id == property_id
        assert space.name == "First Floor Flat"
        assert space.space_type == SpaceType.FLAT
        assert space.is_active is True

    def test_create_rental_space_all_types(self) -> None:
        property_id = uuid.uuid4()
        for space_type in SpaceType:
            space = RentalSpace(property_id=property_id, name=f"Space {space_type}", space_type=space_type)
            assert space.space_type == space_type

    def test_create_rental_space_name_required(self) -> None:
        with pytest.raises(ValueError, match="Rental space name is required"):
            RentalSpace(property_id=uuid.uuid4(), name="", space_type=SpaceType.ROOM)

    def test_create_rental_space_invalid_type(self) -> None:
        with pytest.raises(ValueError, match="Invalid space type"):
            RentalSpace(property_id=uuid.uuid4(), name="Test", space_type="invalid")


class TestTenant:
    def test_create_tenant_valid(self) -> None:
        tenant = Tenant(full_name="Jane Smith", phone=PhoneNumber("9812345678"))
        assert tenant.full_name == "Jane Smith"
        assert tenant.phone.number == "9812345678"

    def test_create_tenant_name_required(self) -> None:
        with pytest.raises(ValueError, match="Tenant full name is required"):
            Tenant(full_name="", phone=PhoneNumber("9812345678"))

    def test_create_tenant_phone_required(self) -> None:
        with pytest.raises(ValueError, match="Phone number cannot be empty"):
            Tenant(full_name="Jane Smith", phone=PhoneNumber(""))

    def test_create_tenant_with_alternate_phone(self) -> None:
        tenant = Tenant(
            full_name="Jane Smith",
            phone=PhoneNumber("9812345678"),
            alternate_phone=PhoneNumber("9823456789"),
        )
        assert tenant.alternate_phone is not None
        assert tenant.alternate_phone.number == "9823456789"


class TestAgreement:
    def test_create_agreement_valid(self) -> None:
        tenant_id = uuid.uuid4()
        rental_space_id = uuid.uuid4()
        agreement = Agreement(
            tenant_id=tenant_id,
            rental_space_id=rental_space_id,
            start_date=date(2024, 1, 1),
            monthly_rent=Money(Decimal("15000.00")),
        )
        assert agreement.tenant_id == tenant_id
        assert agreement.rental_space_id == rental_space_id
        assert agreement.start_date == date(2024, 1, 1)
        assert agreement.monthly_rent.amount == Decimal("15000.00")
        assert agreement.status == AgreementStatus.ACTIVE
        assert agreement.is_active is True

    def test_create_agreement_with_end_date(self) -> None:
        agreement = Agreement(
            tenant_id=uuid.uuid4(),
            rental_space_id=uuid.uuid4(),
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            monthly_rent=Money(Decimal("15000.00")),
        )
        assert agreement.end_date == date(2024, 12, 31)

    def test_create_agreement_with_deposit(self) -> None:
        agreement = Agreement(
            tenant_id=uuid.uuid4(),
            rental_space_id=uuid.uuid4(),
            start_date=date(2024, 1, 1),
            monthly_rent=Money(Decimal("15000.00")),
            security_deposit=Money(Decimal("30000.00")),
        )
        assert agreement.security_deposit is not None
        assert agreement.security_deposit.amount == Decimal("30000.00")

    def test_create_agreement_rejects_negative_rent(self) -> None:
        with pytest.raises(ValueError, match="Money amount cannot be negative"):
            Agreement(
                tenant_id=uuid.uuid4(),
                rental_space_id=uuid.uuid4(),
                start_date=date(2024, 1, 1),
                monthly_rent=Money(Decimal("-1000.00")),
            )

    def test_create_agreement_rejects_negative_deposit(self) -> None:
        with pytest.raises(ValueError, match="Money amount cannot be negative"):
            Agreement(
                tenant_id=uuid.uuid4(),
                rental_space_id=uuid.uuid4(),
                start_date=date(2024, 1, 1),
                monthly_rent=Money(Decimal("15000.00")),
                security_deposit=Money(Decimal("-5000.00")),
            )

    def test_create_agreement_rejects_end_before_start(self) -> None:
        with pytest.raises(ValueError, match="End date cannot be before start date"):
            Agreement(
                tenant_id=uuid.uuid4(),
                rental_space_id=uuid.uuid4(),
                start_date=date(2024, 12, 31),
                end_date=date(2024, 1, 1),
                monthly_rent=Money(Decimal("15000.00")),
            )

    def test_end_agreement(self) -> None:
        agreement = Agreement(
            tenant_id=uuid.uuid4(),
            rental_space_id=uuid.uuid4(),
            start_date=date(2024, 1, 1),
            monthly_rent=Money(Decimal("15000.00")),
        )
        agreement.end_agreement(date(2024, 6, 30))
        assert agreement.end_date == date(2024, 6, 30)
        assert agreement.status == AgreementStatus.ENDED
        assert agreement.is_active is False

    def test_end_agreement_rejects_invalid_date(self) -> None:
        agreement = Agreement(
            tenant_id=uuid.uuid4(),
            rental_space_id=uuid.uuid4(),
            start_date=date(2024, 1, 1),
            monthly_rent=Money(Decimal("15000.00")),
        )
        with pytest.raises(ValueError, match="End date cannot be before start date"):
            agreement.end_agreement(date(2023, 12, 31))

    def test_cancel_agreement(self) -> None:
        agreement = Agreement(
            tenant_id=uuid.uuid4(),
            rental_space_id=uuid.uuid4(),
            start_date=date(2024, 1, 1),
            monthly_rent=Money(Decimal("15000.00")),
        )
        agreement.cancel_agreement()
        assert agreement.status == AgreementStatus.CANCELLED
        assert agreement.is_active is False


class TestMoney:
    def test_money_creation(self) -> None:
        money = Money(Decimal("15000.50"))
        assert money.amount == Decimal("15000.50")

    def test_money_quantizes_to_two_decimals(self) -> None:
        money = Money(Decimal("15000.555"))
        assert money.amount == Decimal("15000.56")

    def test_money_rejects_negative(self) -> None:
        with pytest.raises(ValueError, match="Money amount cannot be negative"):
            Money(Decimal("-100.00"))

    def test_money_addition(self) -> None:
        money1 = Money(Decimal("10000.00"))
        money2 = Money(Decimal("5000.00"))
        result = money1 + money2
        assert result.amount == Decimal("15000.00")

    def test_money_subtraction(self) -> None:
        money1 = Money(Decimal("15000.00"))
        money2 = Money(Decimal("5000.00"))
        result = money1 - money2
        assert result.amount == Decimal("10000.00")

    def test_money_multiplication(self) -> None:
        money = Money(Decimal("10000.00"))
        result = money * 2
        assert result.amount == Decimal("20000.00")


class TestPhoneNumber:
    def test_phone_number_creation(self) -> None:
        phone = PhoneNumber("+977-9812345678")
        assert phone.number == "+9779812345678"

    def test_phone_number_strips_non_digits(self) -> None:
        phone = PhoneNumber(" 981-234-5678 ")
        assert phone.number == "9812345678"

    def test_phone_number_rejects_empty(self) -> None:
        with pytest.raises(ValueError, match="Phone number cannot be empty"):
            PhoneNumber("")

    def test_phone_number_rejects_only_non_digits(self) -> None:
        with pytest.raises(ValueError, match="Phone number cannot be empty"):
            PhoneNumber("abc-def")
