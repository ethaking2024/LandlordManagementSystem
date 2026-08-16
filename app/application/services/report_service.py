from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal

from app.application.services.agreement_service import AgreementService
from app.application.services.billing_service import BillingService
from app.application.services.deposit_service import DepositService
from app.application.services.expense_service import ExpenseService
from app.application.services.payment_service import PaymentService
from app.application.services.property_service import PropertyService
from app.application.services.rental_space_service import RentalSpaceService
from app.application.services.tenant_service import TenantService
from app.domain.entities import Agreement, Bill, Property, RentalSpace, Tenant
from app.domain.enums import BillCategory, BillStatus, ExpenseStatus
from app.domain.value_objects import Money
from app.reports.data import (
    BillReportRow,
    DepositReportRow,
    ExpenseReportRow,
    PaymentReportRow,
    PropertySummaryRow,
    ReportFilters,
)


class ReportService:
    """Derives read-only, presentation-independent report data.

    The service composes existing application services as authoritative sources
    of truth (bill balances, payment allocations, occupancy, expense totals) and
    produces plain DTO rows. It never writes data and never applies business
    rules outside the existing services. The desktop layer, PDF renderer and CSV
    renderer all consume the same DTOs.
    """

    def __init__(
        self,
        *,
        billing_service: BillingService,
        payment_service: PaymentService,
        expense_service: ExpenseService,
        deposit_service: DepositService,
        property_service: PropertyService,
        rental_space_service: RentalSpaceService,
        tenant_service: TenantService,
        agreement_service: AgreementService,
    ) -> None:
        self._billing_service = billing_service
        self._payment_service = payment_service
        self._expense_service = expense_service
        self._deposit_service = deposit_service
        self._property_service = property_service
        self._rental_space_service = rental_space_service
        self._tenant_service = tenant_service
        self._agreement_service = agreement_service

        self._spaces_by_id: dict[uuid.UUID, RentalSpace] | None = None
        self._properties_by_id: dict[uuid.UUID, Property] | None = None
        self._tenants_by_id: dict[uuid.UUID, Tenant] | None = None
        self._tenant_property: dict[uuid.UUID, uuid.UUID | None] | None = None

    # ------------------------------------------------------------------
    # Reports
    # ------------------------------------------------------------------

    def billing_report(self, filters: ReportFilters) -> list[BillReportRow]:
        bills = self._fetch_bills(filters)
        spaces = self._spaces()
        properties = self._properties()
        tenants = self._tenants()
        property_spaces = self._property_space_ids(filters.property_id)

        rows: list[BillReportRow] = []
        for bill in bills:
            if filters.tenant_id and bill.tenant_id != filters.tenant_id:
                continue
            if filters.rental_space_id and bill.rental_space_id != filters.rental_space_id:
                continue
            if filters.bill_status and bill.status != filters.bill_status:
                continue
            if property_spaces is not None and bill.rental_space_id not in property_spaces:
                continue

            space = spaces.get(bill.rental_space_id)
            property_obj = properties.get(space.property_id) if space else None
            tenant = tenants.get(bill.tenant_id)
            balance = self._payment_service.calculate_bill_balance(bill.id)
            rent = self._sum(line.amount for line in bill.lines if line.category == BillCategory.RENT)
            utilities = self._sum(
                line.amount for line in bill.lines if line.category in (BillCategory.ELECTRICITY, BillCategory.WATER)
            )
            rows.append(
                BillReportRow(
                    billing_date=bill.billing_date,
                    tenant_name=tenant.full_name if tenant else "",
                    property_name=property_obj.name if property_obj else "",
                    rental_space_name=space.name if space else "",
                    rent=rent,
                    utilities=utilities,
                    total=bill.total,
                    paid=balance.allocated,
                    outstanding=balance.outstanding,
                    status=bill.status,
                )
            )
        return rows

    def payment_report(self, filters: ReportFilters) -> list[PaymentReportRow]:
        payments = self._fetch_payments(filters)
        tenants = self._tenants()
        properties = self._properties()
        tenant_property = self._tenant_property_map()

        rows: list[PaymentReportRow] = []
        for payment in payments:
            if filters.tenant_id and payment.tenant_id != filters.tenant_id:
                continue
            if filters.payment_method and payment.payment_method != filters.payment_method:
                continue
            if filters.payment_status and payment.status != filters.payment_status:
                continue
            property_id = tenant_property.get(payment.tenant_id)
            if filters.property_id and property_id != filters.property_id:
                continue

            tenant = tenants.get(payment.tenant_id)
            property_obj = properties.get(property_id) if property_id else None
            rows.append(
                PaymentReportRow(
                    payment_date=payment.payment_date,
                    tenant_name=tenant.full_name if tenant else "",
                    property_name=property_obj.name if property_obj else "",
                    amount=payment.amount,
                    payment_method=payment.payment_method,
                    reference=payment.reference,
                    allocated=self._payment_service.calculate_payment_allocated(payment.id),
                    remaining=self._payment_service.calculate_payment_unused(payment.id),
                    status=payment.status,
                )
            )
        return rows

    def expense_report(self, filters: ReportFilters) -> list[ExpenseReportRow]:
        expenses = self._fetch_expenses(filters)
        spaces = self._spaces()
        properties = self._properties()

        rows: list[ExpenseReportRow] = []
        for expense in expenses:
            if filters.property_id and expense.property_id != filters.property_id:
                continue
            if filters.rental_space_id and expense.rental_space_id != filters.rental_space_id:
                continue
            if filters.expense_category and expense.category != filters.expense_category:
                continue
            if filters.expense_status and expense.status != filters.expense_status:
                continue

            property_obj = properties.get(expense.property_id)
            space_name = ""
            if expense.rental_space_id:
                space = spaces.get(expense.rental_space_id)
                space_name = space.name if space else ""
            rows.append(
                ExpenseReportRow(
                    expense_date=expense.expense_date,
                    property_name=property_obj.name if property_obj else "",
                    rental_space_name=space_name,
                    category=expense.category,
                    amount=expense.amount,
                    description=expense.description,
                    status=expense.status,
                )
            )
        return rows

    def deposit_report(self, filters: ReportFilters) -> list[DepositReportRow]:
        deposits = self._fetch_deposits(filters)
        agreements = {a.id: a for a in self._agreement_service.get_all_agreements(limit=10000)}
        spaces = self._spaces()
        properties = self._properties()
        tenants = self._tenants()

        rows: list[DepositReportRow] = []
        for deposit in deposits:
            if filters.tenant_id and deposit.tenant_id != filters.tenant_id:
                continue
            if filters.deposit_status and deposit.status != filters.deposit_status:
                continue
            agreement = agreements.get(deposit.agreement_id)
            space = spaces.get(agreement.rental_space_id) if agreement else None
            property_id = space.property_id if space else None
            if filters.property_id and property_id != filters.property_id:
                continue

            settlement = self._deposit_service.get_settlement_by_deposit(deposit.id)
            tenant = tenants.get(deposit.tenant_id)
            property_obj = properties.get(property_id) if property_id else None
            rows.append(
                DepositReportRow(
                    tenant_name=tenant.full_name if tenant else "",
                    property_name=property_obj.name if property_obj else "",
                    rental_space_name=space.name if space else "",
                    amount=deposit.amount,
                    status=deposit.status,
                    settlement_date=settlement.settlement_date if settlement else None,
                    deductions=settlement.total_deductions if settlement else Money(Decimal("0")),
                    refund=settlement.refund_amount if settlement else None,
                )
            )
        return rows

    def property_summary(self, filters: ReportFilters) -> list[PropertySummaryRow]:
        from_date, to_date = self._resolve_range(filters)
        range_filters = replace(filters, from_date=from_date, to_date=to_date)

        spaces = self._spaces()
        properties = self._properties()
        if filters.property_id:
            property_ids = [filters.property_id]
        else:
            property_ids = [prop.id for prop in properties.values()]

        confirmed_by_space: dict[uuid.UUID, list[Bill]] = {}
        for bill in self._fetch_bills(range_filters):
            if bill.status != BillStatus.CONFIRMED:
                continue
            confirmed_by_space.setdefault(bill.rental_space_id, []).append(bill)

        recorded_expenses = [e for e in self._fetch_expenses(range_filters) if e.status == ExpenseStatus.RECORDED]

        rows: list[PropertySummaryRow] = []
        for property_id in property_ids:
            property_obj = properties.get(property_id)
            if not property_obj:
                continue
            space_ids = {space.id for space in spaces.values() if space.property_id == property_id}
            occupied = sum(
                1 for space_id in space_ids if self._agreement_service.is_rental_space_occupied(space_id)
            )
            property_bills = [bill for space_id in space_ids for bill in confirmed_by_space.get(space_id, [])]
            billed = self._sum(bill.total for bill in property_bills)
            paid = self._sum(
                self._payment_service.calculate_bill_balance(bill.id).allocated for bill in property_bills
            )
            outstanding = Money(billed.amount - paid.amount)
            property_expenses = [expense for expense in recorded_expenses if expense.property_id == property_id]
            expense_total = self._sum(expense.amount for expense in property_expenses)
            rows.append(
                PropertySummaryRow(
                    property_name=property_obj.name,
                    from_date=from_date,
                    to_date=to_date,
                    rental_spaces=len(space_ids),
                    occupied=occupied,
                    vacant=len(space_ids) - occupied,
                    billed=billed,
                    payments_received=paid,
                    outstanding=outstanding,
                    expenses=expense_total,
                )
            )
        return rows

    # ------------------------------------------------------------------
    # Fetching
    # ------------------------------------------------------------------

    def _fetch_bills(self, filters: ReportFilters) -> list[Bill]:
        if filters.from_date and filters.to_date:
            return self._billing_service.get_bills_by_billing_date_range(filters.from_date, filters.to_date)
        return self._billing_service.get_all_bills(limit=10000)

    def _fetch_payments(self, filters: ReportFilters) -> list:
        if filters.from_date and filters.to_date:
            return self._payment_service.get_payments_by_date_range(filters.from_date, filters.to_date)
        return self._payment_service.get_all_payments(limit=10000)

    def _fetch_expenses(self, filters: ReportFilters) -> list:
        if filters.from_date and filters.to_date:
            return self._expense_service.get_expenses_by_date_range(filters.from_date, filters.to_date)
        return self._expense_service.get_all_expenses(limit=10000)

    def _fetch_deposits(self, filters: ReportFilters) -> list:
        if filters.from_date and filters.to_date:
            return self._deposit_service.get_deposits_by_date_range(filters.from_date, filters.to_date)
        return self._deposit_service.get_all_deposits(limit=10000)

    # ------------------------------------------------------------------
    # Lookup maps
    # ------------------------------------------------------------------

    def _spaces(self) -> dict[uuid.UUID, RentalSpace]:
        if self._spaces_by_id is None:
            self._spaces_by_id = {s.id: s for s in self._rental_space_service.get_all_rental_spaces(limit=10000)}
        return self._spaces_by_id

    def _properties(self) -> dict[uuid.UUID, Property]:
        if self._properties_by_id is None:
            self._properties_by_id = {
                p.id: p for p in self._property_service.get_all_properties(limit=10000)
            }
        return self._properties_by_id

    def _tenants(self) -> dict[uuid.UUID, Tenant]:
        if self._tenants_by_id is None:
            self._tenants_by_id = {t.id: t for t in self._tenant_service.get_all_tenants(limit=10000)}
        return self._tenants_by_id

    def _tenant_property_map(self) -> dict[uuid.UUID, uuid.UUID | None]:
        """Map each tenant to the property of their most relevant agreement.

        A tenant's active agreement (most recently started) wins; when the tenant
        has no active agreement the most recently started agreement is used.
        """
        if self._tenant_property is None:
            agreements = self._agreement_service.get_all_agreements(limit=10000)
            spaces = self._spaces()
            by_tenant: dict[uuid.UUID, list[Agreement]] = {}
            for agreement in agreements:
                by_tenant.setdefault(agreement.tenant_id, []).append(agreement)

            mapping: dict[uuid.UUID, uuid.UUID | None] = {}
            for tenant_id, tenant_agreements in by_tenant.items():
                active = [agreement for agreement in tenant_agreements if agreement.is_active]
                pool = active if active else tenant_agreements
                chosen = max(pool, key=lambda agreement: agreement.start_date)
                space = spaces.get(chosen.rental_space_id)
                mapping[tenant_id] = space.property_id if space else None
            self._tenant_property = mapping
        return self._tenant_property

    def _property_space_ids(self, property_id: uuid.UUID | None) -> set[uuid.UUID] | None:
        if property_id is None:
            return None
        return {space.id for space in self._spaces().values() if space.property_id == property_id}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_range(filters: ReportFilters) -> tuple[date, date]:
        """Resolve the summary period, defaulting to the current calendar month."""
        today = date.today()
        month_start = today.replace(day=1)
        if month_start.month == 12:
            next_month = date(month_start.year + 1, 1, 1)
        else:
            next_month = date(month_start.year, month_start.month + 1, 1)
        month_end = next_month - timedelta(days=1)
        return (filters.from_date or month_start), (filters.to_date or month_end)

    @staticmethod
    def _sum(monies) -> Money:
        return Money(sum((money.amount for money in monies), Decimal("0")))
