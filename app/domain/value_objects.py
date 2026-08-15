from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class Money:
    amount: Decimal

    def __post_init__(self) -> None:
        if self.amount < 0:
            raise ValueError("Money amount cannot be negative")
        object.__setattr__(self, "amount", self.amount.quantize(Decimal("0.01")))

    def __add__(self, other: Money) -> Money:
        if not isinstance(other, Money):
            return NotImplemented
        return Money(self.amount + other.amount)

    def __sub__(self, other: Money) -> Money:
        if not isinstance(other, Money):
            return NotImplemented
        return Money(self.amount - other.amount)

    def __mul__(self, multiplier: int | Decimal) -> Money:
        return Money(self.amount * Decimal(str(multiplier)))

    def __str__(self) -> str:
        return str(self.amount)

    def __repr__(self) -> str:
        return f"Money({self.amount})"


@dataclass(frozen=True, slots=True)
class PhoneNumber:
    number: str

    def __post_init__(self) -> None:
        cleaned = "".join(c for c in self.number if c.isdigit() or c == "+")
        if not cleaned:
            raise ValueError("Phone number cannot be empty")
        object.__setattr__(self, "number", cleaned)

    def __str__(self) -> str:
        return self.number


@dataclass(frozen=True, slots=True)
class MeterReadingValue:
    """A non-negative meter reading value (e.g. kWh or units)."""

    value: Decimal

    def __post_init__(self) -> None:
        if self.value < 0:
            raise ValueError("Reading value cannot be negative")
        object.__setattr__(self, "value", self.value.quantize(Decimal("0.001")))

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True, slots=True)
class BillingPeriod:
    """An immutable billing period defined by canonical AD start and end dates."""

    start: date
    end: date

    def __post_init__(self) -> None:
        if self.end < self.start:
            raise ValueError("Billing period end cannot be before start")

    @property
    def days(self) -> int:
        return (self.end - self.start).days + 1

    def contains(self, day: date) -> bool:
        return self.start <= day <= self.end


@dataclass(frozen=True, slots=True)
class BillBalance:
    """A read-only snapshot of a bill's payment state derived from allocations.

    `total` is the bill total. `allocated` is the sum of amounts from valid
    (non-void) payment allocations. `outstanding` is the difference.
    """

    total: Money
    allocated: Money
    outstanding: Money

    def __post_init__(self) -> None:
        if self.allocated.amount > self.total.amount:
            raise ValueError("Allocated amount cannot exceed bill total")
