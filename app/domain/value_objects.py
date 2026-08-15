from __future__ import annotations

from dataclasses import dataclass
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
