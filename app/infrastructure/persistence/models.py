from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    UUID,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
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
