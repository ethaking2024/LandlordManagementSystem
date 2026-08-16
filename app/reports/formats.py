from __future__ import annotations

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
from app.reports.data import (
    BillReportRow,
    DepositReportRow,
    ExpenseReportRow,
    PaymentReportRow,
    PropertySummaryRow,
)
from app.shared.dates.bs import BSCalendar

BILLING_HEADERS: tuple[str, ...] = (
    "Date",
    "Tenant",
    "Property",
    "Rental Space",
    "Rent",
    "Utilities",
    "Total",
    "Paid",
    "Outstanding",
    "Status",
)

PAYMENT_HEADERS: tuple[str, ...] = (
    "Date",
    "Tenant",
    "Property",
    "Amount",
    "Payment Method",
    "Reference",
    "Allocated",
    "Remaining",
    "Status",
)

EXPENSE_HEADERS: tuple[str, ...] = (
    "Date",
    "Property",
    "Rental Space",
    "Category",
    "Amount",
    "Description",
    "Status",
)

DEPOSIT_HEADERS: tuple[str, ...] = (
    "Tenant",
    "Property",
    "Rental Space",
    "Deposit Amount",
    "Status",
    "Settlement Date",
    "Deductions",
    "Refund",
)

SUMMARY_HEADERS: tuple[str, ...] = (
    "Property",
    "Period",
    "Rental Spaces",
    "Occupied",
    "Vacant",
    "Billed",
    "Payments Received",
    "Outstanding",
    "Expenses",
)


# ---------------------------------------------------------------------------
# Value formatting
# ---------------------------------------------------------------------------


def format_money(money: Money) -> str:
    """Display formatting for money (e.g. 'NPR 80000.00')."""
    return f"NPR {money}"


def money_csv(money: Money) -> str:
    """Machine-friendly decimal representation for money in exports."""
    return str(money.amount)


def format_date(ad_date: date) -> str:
    """Display formatting for a date as 'AD (BS)' (e.g. '2026-08-16 (Bhadra 1, 2083)')."""
    return f"{ad_date.isoformat()} ({BSCalendar.format_bs(ad_date)})"


def date_csv(ad_date: date) -> str:
    """Machine-friendly ISO representation for dates in exports."""
    return ad_date.isoformat()


def bill_status_label(status: BillStatus) -> str:
    return status.value.capitalize()


def payment_method_label(method: PaymentMethod) -> str:
    return method.value.replace("_", " ").capitalize()


def payment_status_label(status: PaymentStatus) -> str:
    return status.value.capitalize()


def expense_category_label(category: ExpenseCategory) -> str:
    labels = {
        ExpenseCategory.ELECTRICAL: "Electrical",
        ExpenseCategory.PLUMBING: "Plumbing",
        ExpenseCategory.CLEANING: "Cleaning",
        ExpenseCategory.TAX: "Tax",
        ExpenseCategory.COMMON_AREA: "Common Area",
        ExpenseCategory.OTHER: "Other",
    }
    return labels.get(category, category.value.capitalize())


def expense_status_label(status: ExpenseStatus) -> str:
    return status.value.capitalize()


def deposit_status_label(status: DepositStatus) -> str:
    return status.value.capitalize()


# ---------------------------------------------------------------------------
# Row conversion
# ---------------------------------------------------------------------------


def billing_display_rows(rows: list[BillReportRow]) -> list[tuple[str, ...]]:
    return [
        (
            format_date(row.billing_date),
            row.tenant_name,
            row.property_name,
            row.rental_space_name,
            format_money(row.rent),
            format_money(row.utilities),
            format_money(row.total),
            format_money(row.paid),
            format_money(row.outstanding),
            bill_status_label(row.status),
        )
        for row in rows
    ]


def billing_csv_rows(rows: list[BillReportRow]) -> list[tuple[str, ...]]:
    return [
        (
            date_csv(row.billing_date),
            row.tenant_name,
            row.property_name,
            row.rental_space_name,
            money_csv(row.rent),
            money_csv(row.utilities),
            money_csv(row.total),
            money_csv(row.paid),
            money_csv(row.outstanding),
            bill_status_label(row.status),
        )
        for row in rows
    ]


def payment_display_rows(rows: list[PaymentReportRow]) -> list[tuple[str, ...]]:
    return [
        (
            format_date(row.payment_date),
            row.tenant_name,
            row.property_name,
            format_money(row.amount),
            payment_method_label(row.payment_method),
            row.reference or "",
            format_money(row.allocated),
            format_money(row.remaining),
            payment_status_label(row.status),
        )
        for row in rows
    ]


def payment_csv_rows(rows: list[PaymentReportRow]) -> list[tuple[str, ...]]:
    return [
        (
            date_csv(row.payment_date),
            row.tenant_name,
            row.property_name,
            money_csv(row.amount),
            payment_method_label(row.payment_method),
            row.reference or "",
            money_csv(row.allocated),
            money_csv(row.remaining),
            payment_status_label(row.status),
        )
        for row in rows
    ]


def expense_display_rows(rows: list[ExpenseReportRow]) -> list[tuple[str, ...]]:
    return [
        (
            format_date(row.expense_date),
            row.property_name,
            row.rental_space_name,
            expense_category_label(row.category),
            format_money(row.amount),
            row.description or "",
            expense_status_label(row.status),
        )
        for row in rows
    ]


def expense_csv_rows(rows: list[ExpenseReportRow]) -> list[tuple[str, ...]]:
    return [
        (
            date_csv(row.expense_date),
            row.property_name,
            row.rental_space_name,
            expense_category_label(row.category),
            money_csv(row.amount),
            row.description or "",
            expense_status_label(row.status),
        )
        for row in rows
    ]


def deposit_display_rows(rows: list[DepositReportRow]) -> list[tuple[str, ...]]:
    return [
        (
            row.tenant_name,
            row.property_name,
            row.rental_space_name,
            format_money(row.amount),
            deposit_status_label(row.status),
            format_date(row.settlement_date) if row.settlement_date else "",
            format_money(row.deductions),
            format_money(row.refund) if row.refund is not None else "",
        )
        for row in rows
    ]


def deposit_csv_rows(rows: list[DepositReportRow]) -> list[tuple[str, ...]]:
    return [
        (
            row.tenant_name,
            row.property_name,
            row.rental_space_name,
            money_csv(row.amount),
            deposit_status_label(row.status),
            date_csv(row.settlement_date) if row.settlement_date else "",
            money_csv(row.deductions),
            money_csv(row.refund) if row.refund is not None else "",
        )
        for row in rows
    ]


def summary_display_rows(rows: list[PropertySummaryRow]) -> list[tuple[str, ...]]:
    return [
        (
            row.property_name,
            f"{format_date(row.from_date)} to {format_date(row.to_date)}",
            str(row.rental_spaces),
            str(row.occupied),
            str(row.vacant),
            format_money(row.billed),
            format_money(row.payments_received),
            format_money(row.outstanding),
            format_money(row.expenses),
        )
        for row in rows
    ]


def summary_csv_rows(rows: list[PropertySummaryRow]) -> list[tuple[str, ...]]:
    return [
        (
            row.property_name,
            f"{date_csv(row.from_date)} to {date_csv(row.to_date)}",
            str(row.rental_spaces),
            str(row.occupied),
            str(row.vacant),
            money_csv(row.billed),
            money_csv(row.payments_received),
            money_csv(row.outstanding),
            money_csv(row.expenses),
        )
        for row in rows
    ]
