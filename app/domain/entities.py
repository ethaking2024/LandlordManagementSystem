from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime

from app.domain.enums import (
    AgreementStatus,
    ElectricityConfigType,
    SpaceType,
    UtilityType,
    WaterConfigType,
)
from app.domain.value_objects import MeterReadingValue, Money, PhoneNumber
from app.shared.dates.bs import BSCalendar


def utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(slots=True)
class Owner:
    name: str
    phone: PhoneNumber | None = None
    email: str | None = None
    address: str | None = None
    notes: str | None = None
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("Owner name is required")
        self.name = self.name.strip()


@dataclass(slots=True)
class Property:
    owner_id: uuid.UUID
    name: str
    address: str
    notes: str | None = None
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("Property name is required")
        if not self.address or not self.address.strip():
            raise ValueError("Property address is required")
        self.name = self.name.strip()
        self.address = self.address.strip()


@dataclass(slots=True)
class RentalSpace:
    property_id: uuid.UUID
    name: str
    space_type: SpaceType = SpaceType.OTHER
    floor_label: str | None = None
    description: str | None = None
    is_active: bool = True
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("Rental space name is required")
        if not isinstance(self.space_type, SpaceType):
            raise ValueError(f"Invalid space type: {self.space_type}")
        self.name = self.name.strip()
        if self.floor_label:
            self.floor_label = self.floor_label.strip()


@dataclass(slots=True)
class Tenant:
    full_name: str
    phone: PhoneNumber
    alternate_phone: PhoneNumber | None = None
    email: str | None = None
    address: str | None = None
    notes: str | None = None
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)

    def __post_init__(self) -> None:
        if not self.full_name or not self.full_name.strip():
            raise ValueError("Tenant full name is required")
        if not self.phone or not self.phone.number:
            raise ValueError("Tenant phone is required")
        self.full_name = self.full_name.strip()


@dataclass(slots=True)
class Agreement:
    tenant_id: uuid.UUID
    rental_space_id: uuid.UUID
    start_date: date
    monthly_rent: Money
    end_date: date | None = None
    security_deposit: Money | None = None
    status: AgreementStatus = AgreementStatus.ACTIVE
    notes: str | None = None
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)

    def __post_init__(self) -> None:
        if not isinstance(self.monthly_rent, Money):
            raise ValueError("Monthly rent must be a Money object")
        if self.monthly_rent.amount < 0:
            raise ValueError("Monthly rent cannot be negative")
        if self.security_deposit is not None and self.security_deposit.amount < 0:
            raise ValueError("Security deposit cannot be negative")
        if self.end_date is not None and self.end_date < self.start_date:
            raise ValueError("End date cannot be before start date")
        if not isinstance(self.status, AgreementStatus):
            raise ValueError(f"Invalid agreement status: {self.status}")

    @property
    def is_active(self) -> bool:
        return self.status == AgreementStatus.ACTIVE

    def end_agreement(self, end_date: date) -> None:
        if end_date < self.start_date:
            raise ValueError("End date cannot be before start date")
        self.end_date = end_date
        self.status = AgreementStatus.ENDED
        self.updated_at = utcnow()

    def cancel_agreement(self) -> None:
        self.status = AgreementStatus.CANCELLED
        self.updated_at = utcnow()


@dataclass(slots=True)
class UtilityConfig:
    rental_space_id: uuid.UUID
    utility_type: UtilityType
    config_type: str
    fixed_amount: Money | None = None
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)

    def __post_init__(self) -> None:
        if not isinstance(self.utility_type, UtilityType):
            raise ValueError(f"Invalid utility type: {self.utility_type}")
        if self.utility_type == UtilityType.ELECTRICITY:
            valid = {c.value for c in ElectricityConfigType}
        else:
            valid = {c.value for c in WaterConfigType}
        if self.config_type not in valid:
            raise ValueError(f"Invalid config type '{self.config_type}' for {self.utility_type.value}")
        if self.fixed_amount is not None:
            if not isinstance(self.fixed_amount, Money):
                raise ValueError("Fixed amount must be a Money object")
            if self.fixed_amount.amount < 0:
                raise ValueError("Fixed amount cannot be negative")
        if self.config_type == ElectricityConfigType.FIXED.value and self.fixed_amount is None:
            raise ValueError("Fixed utility config requires a fixed amount")

    def update_config(self, config_type: str, fixed_amount: Money | None = None) -> None:
        if self.utility_type == UtilityType.ELECTRICITY:
            valid = {c.value for c in ElectricityConfigType}
        else:
            valid = {c.value for c in WaterConfigType}
        if config_type not in valid:
            raise ValueError(f"Invalid config type '{config_type}' for {self.utility_type.value}")
        if config_type == ElectricityConfigType.FIXED.value and fixed_amount is None:
            raise ValueError("Fixed utility config requires a fixed amount")
        if fixed_amount is not None and fixed_amount.amount < 0:
            raise ValueError("Fixed amount cannot be negative")
        self.config_type = config_type
        self.fixed_amount = fixed_amount
        self.updated_at = utcnow()


@dataclass(slots=True)
class Meter:
    rental_space_id: uuid.UUID
    utility_type: UtilityType
    identifier: str
    installation_date: date
    is_active: bool = True
    notes: str | None = None
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)

    def __post_init__(self) -> None:
        if not isinstance(self.utility_type, UtilityType):
            raise ValueError(f"Invalid utility type: {self.utility_type}")
        if not self.identifier or not self.identifier.strip():
            raise ValueError("Meter identifier is required")
        self.identifier = self.identifier.strip()
        if self.notes:
            self.notes = self.notes.strip()

    def deactivate(self) -> None:
        self.is_active = False
        self.updated_at = utcnow()

    def activate(self) -> None:
        self.is_active = True
        self.updated_at = utcnow()


@dataclass(slots=True)
class MeterReading:
    meter_id: uuid.UUID
    reading_date: date
    value: MeterReadingValue
    notes: str | None = None
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)

    def __post_init__(self) -> None:
        if not isinstance(self.value, MeterReadingValue):
            raise ValueError("Reading value must be a MeterReadingValue object")
        if self.notes:
            self.notes = self.notes.strip()

    @property
    def bs_display(self) -> str:
        return BSCalendar.format_bs(self.reading_date)

    def consumption_since(self, previous: MeterReading) -> MeterReadingValue:
        consumption = self.value.value - previous.value.value
        if consumption < 0:
            raise ValueError("Consumption cannot be negative")
        return MeterReadingValue(consumption)


@dataclass(slots=True)
class UtilityTariff:
    utility_type: UtilityType
    effective_from: date
    rate: Money
    notes: str | None = None
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)

    def __post_init__(self) -> None:
        if not isinstance(self.utility_type, UtilityType):
            raise ValueError(f"Invalid utility type: {self.utility_type}")
        if not isinstance(self.rate, Money):
            raise ValueError("Tariff rate must be a Money object")
        if self.rate.amount < 0:
            raise ValueError("Tariff rate cannot be negative")
        if self.notes:
            self.notes = self.notes.strip()


@dataclass(slots=True)
class MeterReplacement:
    old_meter_id: uuid.UUID
    new_meter_id: uuid.UUID
    replaced_on: date
    notes: str | None = None
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=utcnow)

    def __post_init__(self) -> None:
        if self.old_meter_id == self.new_meter_id:
            raise ValueError("Old and new meter cannot be the same")
        if self.notes:
            self.notes = self.notes.strip()
