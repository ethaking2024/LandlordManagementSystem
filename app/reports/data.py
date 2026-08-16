from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date

from app.domain.enums import (
    BillStatus,
    DepositStatus,
    ExpenseCategory,
    ExpenseStatus,
    PaymentMethod,
    PaymentStatus,
)
from app.domain.value_objects import Money


@dataclass(frozen=True, slots=True)
class ReportFilters:
    """Read-only criteria shared by every report.

    A ``None`` filter means "no constraint". From/to dates are inclusive and are
    applied to the natural date of each report (billing date, payment date,
    expense date, deposit received date). When both dates are omitted the report
    covers all records.
    """

    from_date: date | None = None
    to_date: date | None = None
    property_id: uuid.UUID | None = None
    tenant_id: uuid.UUID | None = None
    rental_space_id: uuid.UUID | None = None
    bill_status: BillStatus | None = None
    payment_method: PaymentMethod | None = None
    payment_status: PaymentStatus | None = None
    expense_category: ExpenseCategory | None = None
    expense_status: ExpenseStatus | None = None
    deposit_status: DepositStatus | None = None


@dataclass(frozen=True, slots=True)
class BillReportRow:
    billing_date: date
    tenant_name: str
    property_name: str
    rental_space_name: str
    rent: Money
    utilities: Money
    total: Money
    paid: Money
    outstanding: Money
    status: BillStatus


@dataclass(frozen=True, slots=True)
class PaymentReportRow:
    payment_date: date
    tenant_name: str
    property_name: str
    amount: Money
    payment_method: PaymentMethod
    reference: str | None
    allocated: Money
    remaining: Money
    status: PaymentStatus


@dataclass(frozen=True, slots=True)
class ExpenseReportRow:
    expense_date: date
    property_name: str
    rental_space_name: str
    category: ExpenseCategory
    amount: Money
    description: str | None
    status: ExpenseStatus


@dataclass(frozen=True, slots=True)
class DepositReportRow:
    tenant_name: str
    property_name: str
    rental_space_name: str
    amount: Money
    status: DepositStatus
    settlement_date: date | None
    deductions: Money
    refund: Money | None


@dataclass(frozen=True, slots=True)
class PropertySummaryRow:
    property_name: str
    from_date: date
    to_date: date
    rental_spaces: int
    occupied: int
    vacant: int
    billed: Money
    payments_received: Money
    outstanding: Money
    expenses: Money
