from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    UUID,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain.enums import (
    AgreementStatus,
    BillStatus,
    DepositStatus,
    ExpenseStatus,
    PaymentStatus,
)
from app.infrastructure.persistence.base import Base


class OwnerModel(Base):
    __tablename__ = "owners"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    properties: Mapped[list[PropertyModel]] = relationship("PropertyModel", back_populates="owner", lazy="selectin")

    def __repr__(self) -> str:
        return f"<OwnerModel(id={self.id}, name={self.name!r})>"


class PropertyModel(Base):
    __tablename__ = "properties"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("owners.id", ondelete="RESTRICT"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    owner: Mapped[OwnerModel] = relationship("OwnerModel", back_populates="properties", lazy="selectin")
    rental_spaces: Mapped[list[RentalSpaceModel]] = relationship("RentalSpaceModel", back_populates="property", lazy="selectin")
    expenses: Mapped[list[ExpenseModel]] = relationship("ExpenseModel", back_populates="property", lazy="selectin")

    __table_args__ = (
        Index("ix_properties_owner_id", "owner_id"),
    )

    def __repr__(self) -> str:
        return f"<PropertyModel(id={self.id}, name={self.name!r})>"


class RentalSpaceModel(Base):
    __tablename__ = "rental_spaces"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    property_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("properties.id", ondelete="RESTRICT"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    space_type: Mapped[str] = mapped_column(String(30), nullable=False)
    floor_label: Mapped[str | None] = mapped_column(String(50), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    property: Mapped[PropertyModel] = relationship("PropertyModel", back_populates="rental_spaces", lazy="selectin")
    agreements: Mapped[list[AgreementModel]] = relationship("AgreementModel", back_populates="rental_space", lazy="selectin")
    utility_configs: Mapped[list[UtilityConfigModel]] = relationship("UtilityConfigModel", back_populates="rental_space", lazy="selectin")
    meters: Mapped[list[MeterModel]] = relationship("MeterModel", back_populates="rental_space", lazy="selectin")
    expenses: Mapped[list[ExpenseModel]] = relationship("ExpenseModel", back_populates="rental_space", lazy="selectin")

    __table_args__ = (
        Index("ix_rental_spaces_property_id", "property_id"),
        Index("ix_rental_spaces_is_active", "is_active"),
        CheckConstraint("space_type IN ('whole_floor', 'flat', 'room', 'room_group', 'other')", name="ck_rental_spaces_space_type"),
    )

    def __repr__(self) -> str:
        return f"<RentalSpaceModel(id={self.id}, name={self.name!r}, type={self.space_type!r})>"


class TenantModel(Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(50), nullable=False)
    alternate_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    agreements: Mapped[list[AgreementModel]] = relationship("AgreementModel", back_populates="tenant", lazy="selectin")
    payments: Mapped[list[PaymentModel]] = relationship("PaymentModel", back_populates="tenant", lazy="selectin")

    __table_args__ = (
        Index("ix_tenants_full_name", "full_name"),
    )

    def __repr__(self) -> str:
        return f"<TenantModel(id={self.id}, full_name={self.full_name!r})>"


class AgreementModel(Base):
    __tablename__ = "agreements"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False)
    rental_space_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("rental_spaces.id", ondelete="RESTRICT"), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    monthly_rent: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0"))
    security_deposit: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=AgreementStatus.ACTIVE.value)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    tenant: Mapped[TenantModel] = relationship("TenantModel", back_populates="agreements", lazy="selectin")
    rental_space: Mapped[RentalSpaceModel] = relationship("RentalSpaceModel", back_populates="agreements", lazy="selectin")
    bills: Mapped[list[BillModel]] = relationship("BillModel", back_populates="agreement", lazy="selectin")
    deposits: Mapped[list[DepositModel]] = relationship("DepositModel", back_populates="agreement", lazy="selectin")

    __table_args__ = (
        Index("ix_agreements_tenant_id", "tenant_id"),
        Index("ix_agreements_rental_space_id", "rental_space_id"),
        Index("ix_agreements_status", "status"),
        CheckConstraint("monthly_rent >= 0", name="ck_agreements_monthly_rent_non_negative"),
        CheckConstraint("security_deposit IS NULL OR security_deposit >= 0", name="ck_agreements_security_deposit_non_negative"),
        CheckConstraint("end_date IS NULL OR end_date >= start_date", name="ck_agreements_end_date_after_start"),
        CheckConstraint("status IN ('active', 'ended', 'cancelled')", name="ck_agreements_status"),
    )

    def __repr__(self) -> str:
        return f"<AgreementModel(id={self.id}, tenant_id={self.tenant_id}, rental_space_id={self.rental_space_id}, status={self.status!r})>"


class UtilityConfigModel(Base):
    __tablename__ = "utility_configs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rental_space_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rental_spaces.id", ondelete="RESTRICT"), nullable=False
    )
    utility_type: Mapped[str] = mapped_column(String(30), nullable=False)
    config_type: Mapped[str] = mapped_column(String(30), nullable=False)
    fixed_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    rental_space: Mapped[RentalSpaceModel] = relationship("RentalSpaceModel", back_populates="utility_configs", lazy="selectin")

    __table_args__ = (
        UniqueConstraint("rental_space_id", "utility_type", name="uq_utility_configs_rental_space_utility"),
        CheckConstraint("utility_type IN ('electricity', 'water')", name="ck_utility_configs_utility_type"),
        CheckConstraint("config_type IN ('no_charge', 'fixed', 'metered')", name="ck_utility_configs_config_type"),
        CheckConstraint("fixed_amount IS NULL OR fixed_amount >= 0", name="ck_utility_configs_fixed_amount_non_negative"),
    )

    def __repr__(self) -> str:
        return (
            f"<UtilityConfigModel(id={self.id}, rental_space_id={self.rental_space_id}, "
            f"utility_type={self.utility_type!r}, config_type={self.config_type!r})>"
        )


class MeterModel(Base):
    __tablename__ = "meters"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rental_space_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rental_spaces.id", ondelete="RESTRICT"), nullable=False
    )
    utility_type: Mapped[str] = mapped_column(String(30), nullable=False)
    identifier: Mapped[str] = mapped_column(String(100), nullable=False)
    installation_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    rental_space: Mapped[RentalSpaceModel] = relationship("RentalSpaceModel", back_populates="meters", lazy="selectin")
    readings: Mapped[list[MeterReadingModel]] = relationship("MeterReadingModel", back_populates="meter", lazy="selectin")
    replacements_old: Mapped[list[MeterReplacementModel]] = relationship(
        "MeterReplacementModel", back_populates="old_meter", foreign_keys="MeterReplacementModel.old_meter_id", lazy="selectin"
    )
    replacements_new: Mapped[list[MeterReplacementModel]] = relationship(
        "MeterReplacementModel", back_populates="new_meter", foreign_keys="MeterReplacementModel.new_meter_id", lazy="selectin"
    )

    __table_args__ = (
        Index("ix_meters_rental_space_id", "rental_space_id"),
        Index("ix_meters_utility_type", "utility_type"),
        Index("ix_meters_is_active", "is_active"),
        UniqueConstraint("rental_space_id", "utility_type", "identifier", name="uq_meters_rental_space_utility_identifier"),
        CheckConstraint("utility_type IN ('electricity', 'water')", name="ck_meters_utility_type"),
    )

    def __repr__(self) -> str:
        return f"<MeterModel(id={self.id}, identifier={self.identifier!r}, utility_type={self.utility_type!r})>"


class MeterReadingModel(Base):
    __tablename__ = "meter_readings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meter_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("meters.id", ondelete="RESTRICT"), nullable=False)
    reading_date: Mapped[date] = mapped_column(Date, nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    meter: Mapped[MeterModel] = relationship("MeterModel", back_populates="readings", lazy="selectin")

    __table_args__ = (
        Index("ix_meter_readings_meter_id", "meter_id"),
        Index("ix_meter_readings_reading_date", "reading_date"),
        UniqueConstraint("meter_id", "reading_date", name="uq_meter_readings_meter_date"),
        CheckConstraint("value >= 0", name="ck_meter_readings_value_non_negative"),
    )

    def __repr__(self) -> str:
        return f"<MeterReadingModel(id={self.id}, meter_id={self.meter_id}, reading_date={self.reading_date}, value={self.value})>"


class UtilityTariffModel(Base):
    __tablename__ = "utility_tariffs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    utility_type: Mapped[str] = mapped_column(String(30), nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    rate: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_utility_tariffs_utility_type", "utility_type"),
        Index("ix_utility_tariffs_effective_from", "effective_from"),
        UniqueConstraint("utility_type", "effective_from", name="uq_utility_tariffs_utility_effective_from"),
        CheckConstraint("utility_type IN ('electricity', 'water')", name="ck_utility_tariffs_utility_type"),
        CheckConstraint("rate >= 0", name="ck_utility_tariffs_rate_non_negative"),
    )

    def __repr__(self) -> str:
        return f"<UtilityTariffModel(id={self.id}, utility_type={self.utility_type!r}, effective_from={self.effective_from}, rate={self.rate})>"


class MeterReplacementModel(Base):
    __tablename__ = "meter_replacements"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    old_meter_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("meters.id", ondelete="RESTRICT"), nullable=False)
    new_meter_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("meters.id", ondelete="RESTRICT"), nullable=False)
    replaced_on: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    old_meter: Mapped[MeterModel] = relationship(
        "MeterModel", back_populates="replacements_old", foreign_keys=[old_meter_id], lazy="selectin"
    )
    new_meter: Mapped[MeterModel] = relationship(
        "MeterModel", back_populates="replacements_new", foreign_keys=[new_meter_id], lazy="selectin"
    )

    __table_args__ = (
        Index("ix_meter_replacements_old_meter_id", "old_meter_id"),
        Index("ix_meter_replacements_new_meter_id", "new_meter_id"),
    )

    def __repr__(self) -> str:
        return f"<MeterReplacementModel(id={self.id}, old_meter_id={self.old_meter_id}, new_meter_id={self.new_meter_id})>"


class BillModel(Base):
    __tablename__ = "bills"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agreement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agreements.id", ondelete="RESTRICT"), nullable=False
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False
    )
    rental_space_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rental_spaces.id", ondelete="RESTRICT"), nullable=False
    )
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    billing_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=BillStatus.DRAFT.value)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0"))
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    agreement: Mapped[AgreementModel] = relationship("AgreementModel", back_populates="bills", lazy="selectin")
    lines: Mapped[list[BillLineModel]] = relationship(
        "BillLineModel", back_populates="bill", lazy="selectin", cascade="all, delete-orphan"
    )
    allocations: Mapped[list[PaymentAllocationModel]] = relationship(
        "PaymentAllocationModel", back_populates="bill", lazy="selectin"
    )

    __table_args__ = (
        Index("ix_bills_agreement_id", "agreement_id"),
        Index("ix_bills_tenant_id", "tenant_id"),
        Index("ix_bills_rental_space_id", "rental_space_id"),
        Index("ix_bills_status", "status"),
        Index("ix_bills_period_start", "period_start"),
        UniqueConstraint("agreement_id", "period_start", "period_end", name="uq_bills_agreement_period"),
        CheckConstraint("period_end >= period_start", name="ck_bills_period_end_after_start"),
        CheckConstraint("total_amount >= 0", name="ck_bills_total_non_negative"),
        CheckConstraint("status IN ('draft', 'confirmed', 'void')", name="ck_bills_status"),
    )

    def __repr__(self) -> str:
        return f"<BillModel(id={self.id}, agreement_id={self.agreement_id}, status={self.status!r})>"


class BillLineModel(Base):
    __tablename__ = "bill_lines"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bills.id", ondelete="CASCADE"), nullable=False
    )
    category: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 3), nullable=True)
    unit_rate: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    config_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    meter_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("meters.id", ondelete="RESTRICT"), nullable=True
    )
    meter_identifier: Mapped[str | None] = mapped_column(String(100), nullable=True)
    previous_reading: Mapped[Decimal | None] = mapped_column(Numeric(18, 3), nullable=True)
    current_reading: Mapped[Decimal | None] = mapped_column(Numeric(18, 3), nullable=True)
    consumption: Mapped[Decimal | None] = mapped_column(Numeric(18, 3), nullable=True)
    tariff_rate: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    tariff_effective_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    bill: Mapped[BillModel] = relationship("BillModel", back_populates="lines", lazy="selectin")

    __table_args__ = (
        Index("ix_bill_lines_bill_id", "bill_id"),
        Index("ix_bill_lines_category", "category"),
        Index("ix_bill_lines_meter_id", "meter_id"),
        CheckConstraint("amount >= 0", name="ck_bill_lines_amount_non_negative"),
        CheckConstraint("category IN ('rent', 'electricity', 'water')", name="ck_bill_lines_category"),
    )

    def __repr__(self) -> str:
        return f"<BillLineModel(id={self.id}, bill_id={self.bill_id}, category={self.category!r}, amount={self.amount})>"


class PaymentModel(Base):
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False
    )
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    payment_method: Mapped[str] = mapped_column(String(30), nullable=False)
    reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=PaymentStatus.RECORDED.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    tenant: Mapped[TenantModel] = relationship("TenantModel", back_populates="payments", lazy="selectin")
    allocations: Mapped[list[PaymentAllocationModel]] = relationship(
        "PaymentAllocationModel", back_populates="payment", lazy="selectin"
    )

    __table_args__ = (
        Index("ix_payments_tenant_id", "tenant_id"),
        Index("ix_payments_payment_date", "payment_date"),
        Index("ix_payments_status", "status"),
        CheckConstraint("amount > 0", name="ck_payments_amount_positive"),
        CheckConstraint("payment_method IN ('cash', 'bank_transfer', 'online', 'other')", name="ck_payments_payment_method"),
        CheckConstraint("status IN ('recorded', 'void')", name="ck_payments_status"),
    )

    def __repr__(self) -> str:
        return f"<PaymentModel(id={self.id}, tenant_id={self.tenant_id}, amount={self.amount}, status={self.status!r})>"


class PaymentAllocationModel(Base):
    __tablename__ = "payment_allocations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("payments.id", ondelete="RESTRICT"), nullable=False
    )
    bill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bills.id", ondelete="RESTRICT"), nullable=False
    )
    allocated_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    payment: Mapped[PaymentModel] = relationship("PaymentModel", back_populates="allocations", lazy="selectin")
    bill: Mapped[BillModel] = relationship("BillModel", back_populates="allocations", lazy="selectin")

    __table_args__ = (
        Index("ix_payment_allocations_payment_id", "payment_id"),
        Index("ix_payment_allocations_bill_id", "bill_id"),
        UniqueConstraint("payment_id", "bill_id", name="uq_payment_allocations_payment_bill"),
        CheckConstraint("allocated_amount > 0", name="ck_payment_allocations_amount_positive"),
    )

    def __repr__(self) -> str:
        return (
            f"<PaymentAllocationModel(id={self.id}, payment_id={self.payment_id}, "
            f"bill_id={self.bill_id}, allocated_amount={self.allocated_amount})>"
        )


class DepositModel(Base):
    __tablename__ = "deposits"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agreement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agreements.id", ondelete="RESTRICT"), nullable=False
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    received_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=DepositStatus.HELD.value)
    reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    agreement: Mapped[AgreementModel] = relationship("AgreementModel", back_populates="deposits", lazy="selectin")
    settlement: Mapped[DepositSettlementModel | None] = relationship(
        "DepositSettlementModel", back_populates="deposit", uselist=False, lazy="selectin"
    )

    __table_args__ = (
        Index("ix_deposits_agreement_id", "agreement_id"),
        Index("ix_deposits_tenant_id", "tenant_id"),
        Index("ix_deposits_status", "status"),
        Index("ix_deposits_received_date", "received_date"),
        CheckConstraint("amount > 0", name="ck_deposits_amount_positive"),
        CheckConstraint("status IN ('held', 'settled', 'void')", name="ck_deposits_status"),
    )

    def __repr__(self) -> str:
        return f"<DepositModel(id={self.id}, agreement_id={self.agreement_id}, amount={self.amount}, status={self.status!r})>"


class DepositSettlementModel(Base):
    __tablename__ = "deposit_settlements"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deposit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("deposits.id", ondelete="RESTRICT"), nullable=False
    )
    settlement_date: Mapped[date] = mapped_column(Date, nullable=False)
    refund_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    deposit: Mapped[DepositModel] = relationship("DepositModel", back_populates="settlement", lazy="selectin")
    deductions: Mapped[list[DepositDeductionModel]] = relationship(
        "DepositDeductionModel", back_populates="settlement", lazy="selectin"
    )

    __table_args__ = (
        Index("ix_deposit_settlements_deposit_id", "deposit_id"),
        UniqueConstraint("deposit_id", name="uq_deposit_settlements_deposit"),
        CheckConstraint(
            "refund_amount IS NULL OR refund_amount >= 0", name="ck_deposit_settlements_refund_non_negative"
        ),
    )

    def __repr__(self) -> str:
        return f"<DepositSettlementModel(id={self.id}, deposit_id={self.deposit_id}, complete={self.refund_amount is not None})>"


class DepositDeductionModel(Base):
    __tablename__ = "deposit_deductions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    settlement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("deposit_settlements.id", ondelete="CASCADE"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    settlement: Mapped[DepositSettlementModel] = relationship(
        "DepositSettlementModel", back_populates="deductions", lazy="selectin"
    )

    __table_args__ = (
        Index("ix_deposit_deductions_settlement_id", "settlement_id"),
        CheckConstraint("amount > 0", name="ck_deposit_deductions_amount_positive"),
    )

    def __repr__(self) -> str:
        return f"<DepositDeductionModel(id={self.id}, settlement_id={self.settlement_id}, amount={self.amount})>"


class ExpenseModel(Base):
    __tablename__ = "expenses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    property_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("properties.id", ondelete="RESTRICT"), nullable=False
    )
    rental_space_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rental_spaces.id", ondelete="RESTRICT"), nullable=True
    )
    expense_date: Mapped[date] = mapped_column(Date, nullable=False)
    category: Mapped[str] = mapped_column(String(30), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=ExpenseStatus.RECORDED.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    property: Mapped[PropertyModel] = relationship("PropertyModel", back_populates="expenses", lazy="selectin")
    rental_space: Mapped[RentalSpaceModel | None] = relationship("RentalSpaceModel", back_populates="expenses", lazy="selectin")

    __table_args__ = (
        Index("ix_expenses_property_id", "property_id"),
        Index("ix_expenses_rental_space_id", "rental_space_id"),
        Index("ix_expenses_expense_date", "expense_date"),
        Index("ix_expenses_category", "category"),
        Index("ix_expenses_status", "status"),
        CheckConstraint("amount > 0", name="ck_expenses_amount_positive"),
        CheckConstraint(
            "category IN ('electrical', 'plumbing', 'cleaning', 'tax', 'common_area', 'other')",
            name="ck_expenses_category",
        ),
        CheckConstraint("status IN ('recorded', 'void')", name="ck_expenses_status"),
    )

    def __repr__(self) -> str:
        return (
            f"<ExpenseModel(id={self.id}, property_id={self.property_id}, "
            f"category={self.category!r}, amount={self.amount}, status={self.status!r})>"
        )
