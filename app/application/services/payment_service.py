from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from app.core.exceptions import NotFoundError, ValidationError
from app.domain.entities import Bill, Payment, PaymentAllocation
from app.domain.enums import BillStatus, PaymentMethod, PaymentStatus
from app.domain.value_objects import BillBalance, Money, MonthlySummary
from app.infrastructure.repositories import (
    BillRepository,
    PaymentAllocationRepository,
    PaymentRepository,
    TenantRepository,
)


class PaymentService:
    """Records payments and applies them to bills via immutable allocations.

    The payment record is the primary source of truth for money received. Bill
    balances and tenant credit are always derived from payments plus their valid
    (non-voided) allocations; they are never stored as mutable balance fields.
    """

    def __init__(
        self,
        payment_repository: PaymentRepository,
        payment_allocation_repository: PaymentAllocationRepository,
        bill_repository: BillRepository,
        tenant_repository: TenantRepository,
    ) -> None:
        self._payment_repository = payment_repository
        self._payment_allocation_repository = payment_allocation_repository
        self._bill_repository = bill_repository
        self._tenant_repository = tenant_repository

    # ------------------------------------------------------------------
    # Payments
    # ------------------------------------------------------------------

    def record_payment(
        self,
        tenant_id: uuid.UUID,
        payment_date: date,
        amount: Money,
        payment_method: PaymentMethod,
        reference: str | None = None,
        notes: str | None = None,
    ) -> Payment:
        tenant = self._tenant_repository.get(tenant_id)
        if not tenant:
            raise NotFoundError(f"Tenant with id {tenant_id} not found")

        payment = Payment(
            tenant_id=tenant_id,
            payment_date=payment_date,
            amount=amount,
            payment_method=payment_method,
            reference=reference.strip() if reference else None,
            notes=notes.strip() if notes else None,
        )
        return self._payment_repository.add(payment)

    def get_payment(self, payment_id: uuid.UUID) -> Payment:
        payment = self._payment_repository.get(payment_id)
        if not payment:
            raise NotFoundError(f"Payment with id {payment_id} not found")
        return payment

    def get_payments_by_tenant(self, tenant_id: uuid.UUID, limit: int = 100, offset: int = 0) -> list[Payment]:
        return self._payment_repository.get_by_tenant(tenant_id, limit=limit, offset=offset)

    def get_all_payments(self, limit: int = 100, offset: int = 0) -> list[Payment]:
        return self._payment_repository.get_all(limit=limit, offset=offset)

    def get_payments_by_date_range(
        self, start_date: date, end_date: date, limit: int = 10000, offset: int = 0
    ) -> list[Payment]:
        return self._payment_repository.get_by_date_range(start_date, end_date, limit=limit, offset=offset)

    def get_allocations_by_payment(self, payment_id: uuid.UUID) -> list[PaymentAllocation]:
        return self._payment_allocation_repository.get_by_payment(payment_id)

    def void_payment(self, payment_id: uuid.UUID) -> Payment:
        payment = self.get_payment(payment_id)
        if payment.status == PaymentStatus.VOID:
            raise ValidationError("Payment is already void")
        payment.void()
        return self._payment_repository.update(payment)

    # ------------------------------------------------------------------
    # Allocation
    # ------------------------------------------------------------------

    def allocate_payment(self, payment_id: uuid.UUID, bill_id: uuid.UUID, allocated_amount: Money) -> PaymentAllocation:
        payment = self.get_payment(payment_id)
        bill = self._get_allocatable_bill(bill_id)
        self._validate_payment_allocation(payment, bill)

        if allocated_amount.amount <= 0:
            raise ValidationError("Allocated amount must be greater than zero")

        if self._payment_allocation_repository.has_allocation_for(payment_id, bill_id):
            raise ValidationError(
                f"A payment allocation already exists for payment {payment_id} and bill {bill_id}"
            )

        remaining_payment = self._remaining_payment_amount(payment)
        if allocated_amount.amount > remaining_payment.amount:
            raise ValidationError(
                f"Allocated amount {allocated_amount} exceeds the payment's remaining "
                f"amount {remaining_payment}"
            )

        outstanding = self.calculate_bill_balance(bill_id).outstanding
        if allocated_amount.amount > outstanding.amount:
            raise ValidationError(
                f"Allocated amount {allocated_amount} exceeds the bill's outstanding "
                f"amount {outstanding}"
            )

        allocation = PaymentAllocation(
            payment_id=payment_id,
            bill_id=bill_id,
            allocated_amount=allocated_amount,
        )
        return self._payment_allocation_repository.add(allocation)

    def apply_tenant_credit(self, tenant_id: uuid.UUID, bill_id: uuid.UUID, amount: Money) -> list[PaymentAllocation]:
        """Apply a tenant's available credit to a bill.

        Credit is money from recorded payments that has not yet been allocated to
        any bill. It is applied by creating allocations from the tenant's recorded
        payments (oldest first) up to the requested amount. The original payment
        references keep the credit trail fully traceable.
        """
        if amount.amount <= 0:
            raise ValidationError("Credit amount must be greater than zero")

        self._get_allocatable_bill(bill_id)
        outstanding = self.calculate_bill_balance(bill_id).outstanding
        if amount.amount > outstanding.amount:
            raise ValidationError(
                f"Credit amount {amount} exceeds the bill's outstanding amount {outstanding}"
            )

        payments = self._payment_repository.get_by_tenant(tenant_id, limit=1000)
        recorded = [p for p in payments if p.status == PaymentStatus.RECORDED]
        recorded.sort(key=lambda p: (p.payment_date, p.created_at))

        allocations: list[PaymentAllocation] = []
        remaining = amount
        for payment in recorded:
            if remaining.amount == 0:
                break
            if self._payment_allocation_repository.has_allocation_for(payment.id, bill_id):
                continue
            unused = self._remaining_payment_amount(payment)
            if unused.amount == 0:
                continue
            portion = remaining if remaining.amount < unused.amount else unused
            allocation = PaymentAllocation(
                payment_id=payment.id,
                bill_id=bill_id,
                allocated_amount=portion,
            )
            allocations.append(allocation)
            remaining = Money(remaining.amount - portion.amount)

        if remaining.amount > 0:
            raise ValidationError(
                f"Insufficient tenant credit for tenant {tenant_id}: requested {amount} "
                f"but only {Money(amount.amount - remaining.amount)} available"
            )

        for allocation in allocations:
            self._payment_allocation_repository.add(allocation)
        return allocations

    # ------------------------------------------------------------------
    # Balances
    # ------------------------------------------------------------------

    def calculate_bill_balance(self, bill_id: uuid.UUID) -> BillBalance:
        bill = self._bill_repository.get(bill_id)
        if not bill:
            raise NotFoundError(f"Bill with id {bill_id} not found")

        allocations = self._payment_allocation_repository.get_valid_by_bill(bill_id)
        allocated = Money(sum((a.allocated_amount.amount for a in allocations), Decimal("0")))
        return BillBalance(
            total=bill.total,
            allocated=allocated,
            outstanding=Money(bill.total.amount - allocated.amount),
        )

    def calculate_tenant_credit(self, tenant_id: uuid.UUID) -> Money:
        payments = self._payment_repository.get_by_tenant(tenant_id, limit=1000)
        total_credit = Decimal("0")
        for payment in payments:
            if payment.status != PaymentStatus.RECORDED:
                continue
            used = self._allocated_total_for_payment(payment.id)
            total_credit += payment.amount.amount - used
        return Money(total_credit)

    def calculate_payment_unused(self, payment_id: uuid.UUID) -> Money:
        payment = self.get_payment(payment_id)
        used = self._allocated_total_for_payment(payment.id)
        return Money(payment.amount.amount - used)

    def calculate_payment_allocated(self, payment_id: uuid.UUID) -> Money:
        """Return the total amount allocated from a payment to its bills."""
        return Money(self._allocated_total_for_payment(payment_id))

    def get_allocatable_bills(self, tenant_id: uuid.UUID, limit: int = 100, offset: int = 0) -> list[Bill]:
        """Return confirmed bills for a tenant that still have an outstanding amount."""
        bills = self._bill_repository.get_by_tenant(tenant_id, limit=limit, offset=offset)
        return [
            bill
            for bill in bills
            if bill.status == BillStatus.CONFIRMED and self.calculate_bill_balance(bill.id).outstanding.amount > 0
        ]

    def get_outstanding_bills(self, limit: int = 100, offset: int = 0) -> list[tuple[Bill, BillBalance]]:
        """Return confirmed bills with an outstanding amount, paired with their balance."""
        bills = self._bill_repository.get_by_status(BillStatus.CONFIRMED, limit=limit, offset=offset)
        rows: list[tuple[Bill, BillBalance]] = []
        for bill in bills:
            balance = self.calculate_bill_balance(bill.id)
            if balance.outstanding.amount > 0:
                rows.append((bill, balance))
        return rows

    def calculate_monthly_summary(self, year: int, month: int) -> MonthlySummary:
        """Return billed, paid and outstanding totals for a calendar month.

        Only confirmed bills with a billing date within the month are counted.
        Payment allocations remain the source of truth for paid and outstanding
        amounts; the dashboard never derives these itself.
        """
        month_start = date(year, month, 1)
        next_month = month + 1
        month_end_year = year + 1 if next_month == 13 else year
        month_end_month = 1 if next_month == 13 else next_month
        month_end = date(month_end_year, month_end_month, 1)
        bills = self._bill_repository.get_by_billing_date_range(month_start, month_end, limit=10000)
        confirmed = [bill for bill in bills if bill.status == BillStatus.CONFIRMED]

        billed = Money(sum((bill.total.amount for bill in confirmed), Decimal("0")))
        paid = Money(Decimal("0"))
        for bill in confirmed:
            balance = self.calculate_bill_balance(bill.id)
            paid = Money(paid.amount + balance.allocated.amount)
        outstanding = Money(billed.amount - paid.amount)
        return MonthlySummary(billed=billed, paid=paid, outstanding=outstanding)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_allocatable_bill(self, bill_id: uuid.UUID) -> Bill:
        bill = self._bill_repository.get(bill_id)
        if not bill:
            raise NotFoundError(f"Bill with id {bill_id} not found")
        if bill.status != BillStatus.CONFIRMED:
            raise ValidationError(
                f"Cannot allocate payments to a bill with status {bill.status.value}; bill must be confirmed"
            )
        return bill

    def _validate_payment_allocation(self, payment: Payment, bill: Bill) -> None:
        if payment.status != PaymentStatus.RECORDED:
            raise ValidationError("Cannot allocate a void payment")
        if payment.tenant_id != bill.tenant_id:
            raise ValidationError("Payment and bill must belong to the same tenant")

    def _remaining_payment_amount(self, payment: Payment) -> Money:
        used = self._allocated_total_for_payment(payment.id)
        return Money(payment.amount.amount - used)

    def _allocated_total_for_payment(self, payment_id: uuid.UUID) -> Decimal:
        allocations = self._payment_allocation_repository.get_by_payment(payment_id)
        return sum((a.allocated_amount.amount for a in allocations), Decimal("0"))
