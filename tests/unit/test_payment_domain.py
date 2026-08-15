from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

import pytest

from app.domain import BillBalance, Payment, PaymentAllocation, PaymentMethod, PaymentStatus
from app.domain.value_objects import Money


class TestPayment:
    def test_valid_payment(self) -> None:
        payment = Payment(
            tenant_id=uuid.uuid4(),
            payment_date=date(2026, 1, 10),
            amount=Money(Decimal("8000")),
            payment_method=PaymentMethod.CASH,
        )
        assert payment.status == PaymentStatus.RECORDED
        assert payment.amount.amount == Decimal("8000.00")

    def test_amount_quantized_to_two_decimals(self) -> None:
        payment = Payment(
            tenant_id=uuid.uuid4(),
            payment_date=date(2026, 1, 10),
            amount=Money(Decimal("8000.006")),
            payment_method=PaymentMethod.BANK_TRANSFER,
        )
        assert payment.amount.amount == Decimal("8000.01")

    def test_rejects_non_money_amount(self) -> None:
        with pytest.raises(ValueError, match="must be a Money object"):
            Payment(
                tenant_id=uuid.uuid4(),
                payment_date=date(2026, 1, 10),
                amount=Decimal("8000"),
                payment_method=PaymentMethod.CASH,
            )

    def test_rejects_zero_amount(self) -> None:
        with pytest.raises(ValueError, match="greater than zero"):
            Payment(
                tenant_id=uuid.uuid4(),
                payment_date=date(2026, 1, 10),
                amount=Money(Decimal("0")),
                payment_method=PaymentMethod.CASH,
            )

    def test_rejects_negative_amount(self) -> None:
        with pytest.raises(ValueError, match="cannot be negative"):
            Payment(
                tenant_id=uuid.uuid4(),
                payment_date=date(2026, 1, 10),
                amount=Money(Decimal("-5")),
                payment_method=PaymentMethod.CASH,
            )

    def test_rejects_invalid_payment_method(self) -> None:
        with pytest.raises(ValueError, match="Invalid payment method"):
            Payment(
                tenant_id=uuid.uuid4(),
                payment_date=date(2026, 1, 10),
                amount=Money(Decimal("8000")),
                payment_method="cash",
            )

    def test_rejects_invalid_status(self) -> None:
        with pytest.raises(ValueError, match="Invalid payment status"):
            Payment(
                tenant_id=uuid.uuid4(),
                payment_date=date(2026, 1, 10),
                amount=Money(Decimal("8000")),
                payment_method=PaymentMethod.CASH,
                status="recorded",
            )

    def test_strips_reference_and_notes(self) -> None:
        payment = Payment(
            tenant_id=uuid.uuid4(),
            payment_date=date(2026, 1, 10),
            amount=Money(Decimal("8000")),
            payment_method=PaymentMethod.ONLINE,
            reference="  REF-001  ",
            notes="  Thank you  ",
        )
        assert payment.reference == "REF-001"
        assert payment.notes == "Thank you"

    def test_void_sets_status(self) -> None:
        payment = Payment(
            tenant_id=uuid.uuid4(),
            payment_date=date(2026, 1, 10),
            amount=Money(Decimal("8000")),
            payment_method=PaymentMethod.CASH,
        )
        payment.void()
        assert payment.status == PaymentStatus.VOID

    def test_void_twice_rejected(self) -> None:
        payment = Payment(
            tenant_id=uuid.uuid4(),
            payment_date=date(2026, 1, 10),
            amount=Money(Decimal("8000")),
            payment_method=PaymentMethod.CASH,
        )
        payment.void()
        with pytest.raises(ValueError, match="already void"):
            payment.void()


class TestPaymentAllocation:
    def test_valid_allocation(self) -> None:
        allocation = PaymentAllocation(
            payment_id=uuid.uuid4(),
            bill_id=uuid.uuid4(),
            allocated_amount=Money(Decimal("5000")),
        )
        assert allocation.allocated_amount.amount == Decimal("5000.00")

    def test_rejects_non_money_amount(self) -> None:
        with pytest.raises(ValueError, match="must be a Money object"):
            PaymentAllocation(
                payment_id=uuid.uuid4(),
                bill_id=uuid.uuid4(),
                allocated_amount=Decimal("5000"),
            )

    def test_rejects_zero_amount(self) -> None:
        with pytest.raises(ValueError, match="greater than zero"):
            PaymentAllocation(
                payment_id=uuid.uuid4(),
                bill_id=uuid.uuid4(),
                allocated_amount=Money(Decimal("0")),
            )

    def test_rejects_negative_amount(self) -> None:
        with pytest.raises(ValueError, match="cannot be negative"):
            PaymentAllocation(
                payment_id=uuid.uuid4(),
                bill_id=uuid.uuid4(),
                allocated_amount=Money(Decimal("-5")),
            )


class TestBillBalance:
    def test_valid_balance(self) -> None:
        balance = BillBalance(
            total=Money(Decimal("20000")),
            allocated=Money(Decimal("8000")),
            outstanding=Money(Decimal("12000")),
        )
        assert balance.outstanding.amount == Decimal("12000.00")

    def test_fully_paid(self) -> None:
        balance = BillBalance(
            total=Money(Decimal("20000")),
            allocated=Money(Decimal("20000")),
            outstanding=Money(Decimal("0")),
        )
        assert balance.outstanding.amount == Decimal("0.00")

    def test_rejects_allocated_exceeding_total(self) -> None:
        with pytest.raises(ValueError, match="cannot exceed bill total"):
            BillBalance(
                total=Money(Decimal("20000")),
                allocated=Money(Decimal("25000")),
                outstanding=Money(Decimal("0")),
            )
