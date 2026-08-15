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

from app.domain.enums import AgreementStatus
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
