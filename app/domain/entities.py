from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal

from app.domain.enums import (
    AgreementStatus,
    BillCategory,
    BillStatus,
    ElectricityConfigType,
    PaymentMethod,
    PaymentStatus,
    SpaceType,
    UtilityType,
    WaterConfigType,
)
from app.domain.value_objects import BillingPeriod, MeterReadingValue, Money, PhoneNumber
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


@dataclass(slots=True)
class BillLine:
    """A single line item on a bill that preserves the financial values used.

    The `amount` is authoritative. The quantity/rate and snapshot fields capture
    the historical calculation basis so a confirmed bill remains explainable even
    after agreements, tariffs, utility configs, or meter readings change.
    """

    category: BillCategory
    description: str
    amount: Money
    bill_id: uuid.UUID | None = None
    quantity: Decimal | None = None
    unit_rate: Money | None = None
    config_type: str | None = None
    meter_id: uuid.UUID | None = None
    meter_identifier: str | None = None
    previous_reading: Decimal | None = None
    current_reading: Decimal | None = None
    consumption: Decimal | None = None
    tariff_rate: Money | None = None
    tariff_effective_from: date | None = None
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)

    def __post_init__(self) -> None:
        if not isinstance(self.category, BillCategory):
            raise ValueError(f"Invalid bill category: {self.category}")
        if not self.description or not self.description.strip():
            raise ValueError("Bill line description is required")
        if not isinstance(self.amount, Money):
            raise ValueError("Bill line amount must be a Money object")
        if self.quantity is not None and self.quantity < 0:
            raise ValueError("Bill line quantity cannot be negative")
        if self.consumption is not None and self.consumption < 0:
            raise ValueError("Bill line consumption cannot be negative")
        if self.unit_rate is not None and not isinstance(self.unit_rate, Money):
            raise ValueError("Bill line unit rate must be a Money object")
        if self.tariff_rate is not None and not isinstance(self.tariff_rate, Money):
            raise ValueError("Bill line tariff rate must be a Money object")
        self.description = self.description.strip()


@dataclass(slots=True)
class Bill:
    """A billing period bill with line items.

    The total is always derived from the sum of line amounts; it is never stored
    as an independently editable value. A confirmed bill is a frozen historical
    financial record.
    """

    agreement_id: uuid.UUID
    tenant_id: uuid.UUID
    rental_space_id: uuid.UUID
    period: BillingPeriod
    billing_date: date
    lines: list[BillLine] = field(default_factory=list)
    status: BillStatus = BillStatus.DRAFT
    notes: str | None = None
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)

    def __post_init__(self) -> None:
        if not isinstance(self.period, BillingPeriod):
            raise ValueError("Bill period must be a BillingPeriod object")
        if self.billing_date < self.period.start:
            raise ValueError("Billing date cannot be before the billing period start")
        if not isinstance(self.status, BillStatus):
            raise ValueError(f"Invalid bill status: {self.status}")
        if self.notes:
            self.notes = self.notes.strip()

    @property
    def total(self) -> Money:
        total = Money(Decimal("0"))
        for line in self.lines:
            total = total + line.amount
        return total

    def add_line(self, line: BillLine) -> None:
        if self.status != BillStatus.DRAFT:
            raise ValueError("Lines can only be added to a draft bill")
        line.bill_id = self.id
        self.lines.append(line)
        self.updated_at = utcnow()

    def confirm(self) -> None:
        if self.status != BillStatus.DRAFT:
            raise ValueError(f"Cannot confirm a bill with status {self.status.value}")
        if not self.lines:
            raise ValueError("Cannot confirm a bill without line items")
        self.status = BillStatus.CONFIRMED
        self.updated_at = utcnow()

    def void(self) -> None:
        if self.status == BillStatus.VOID:
            raise ValueError("Bill is already void")
        self.status = BillStatus.VOID
        self.updated_at = utcnow()


@dataclass(slots=True)
class Payment:
    """Money actually received from a tenant.

    The payment record is the primary source of truth for money received; the
    status governs whether the payment (and its allocations) still count toward
    bill balances. A payment is never physically deleted.
    """

    tenant_id: uuid.UUID
    payment_date: date
    amount: Money
    payment_method: PaymentMethod
    reference: str | None = None
    notes: str | None = None
    status: PaymentStatus = PaymentStatus.RECORDED
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)

    def __post_init__(self) -> None:
        if not isinstance(self.amount, Money):
            raise ValueError("Payment amount must be a Money object")
        if self.amount.amount <= 0:
            raise ValueError("Payment amount must be greater than zero")
        if not isinstance(self.payment_method, PaymentMethod):
            raise ValueError(f"Invalid payment method: {self.payment_method}")
        if not isinstance(self.status, PaymentStatus):
            raise ValueError(f"Invalid payment status: {self.status}")
        if self.reference:
            self.reference = self.reference.strip()
        if self.notes:
            self.notes = self.notes.strip()

    def void(self) -> None:
        if self.status == PaymentStatus.VOID:
            raise ValueError("Payment is already void")
        self.status = PaymentStatus.VOID
        self.updated_at = utcnow()


@dataclass(slots=True)
class PaymentAllocation:
    """A portion of a payment applied to a particular bill.

    Allocations are immutable records. A valid allocation is one whose payment is
    still RECORDED; once the payment is voided the allocation no longer counts
    toward bill balances but the record itself is preserved.
    """

    payment_id: uuid.UUID
    bill_id: uuid.UUID
    allocated_amount: Money
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime = field(default_factory=utcnow)

    def __post_init__(self) -> None:
        if not isinstance(self.allocated_amount, Money):
            raise ValueError("Allocated amount must be a Money object")
        if self.allocated_amount.amount <= 0:
            raise ValueError("Allocated amount must be greater than zero")
