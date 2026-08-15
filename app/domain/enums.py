from __future__ import annotations

from enum import StrEnum


class SpaceType(StrEnum):
    WHOLE_FLOOR = "whole_floor"
    FLAT = "flat"
    ROOM = "room"
    ROOM_GROUP = "room_group"
    OTHER = "other"


class AgreementStatus(StrEnum):
    ACTIVE = "active"
    ENDED = "ended"
    CANCELLED = "cancelled"


class UtilityType(StrEnum):
    ELECTRICITY = "electricity"
    WATER = "water"


class ElectricityConfigType(StrEnum):
    FIXED = "fixed"
    METERED = "metered"


class WaterConfigType(StrEnum):
    NO_CHARGE = "no_charge"
    FIXED = "fixed"
    METERED = "metered"


class BillStatus(StrEnum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    VOID = "void"


class BillCategory(StrEnum):
    RENT = "rent"
    ELECTRICITY = "electricity"
    WATER = "water"


class PaymentStatus(StrEnum):
    RECORDED = "recorded"
    VOID = "void"


class PaymentMethod(StrEnum):
    CASH = "cash"
    BANK_TRANSFER = "bank_transfer"
    ONLINE = "online"
    OTHER = "other"
