from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

import pytest

from app.domain import (
    Deposit,
    DepositDeduction,
    DepositSettlement,
    DepositStatus,
)
from app.domain.value_objects import Money


class TestDeposit:
    def test_valid_deposit(self) -> None:
        deposit = Deposit(
            agreement_id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            amount=Money(Decimal("50000")),
            received_date=date(2026, 1, 5),
        )
        assert deposit.status == DepositStatus.HELD
        assert deposit.is_held is True
        assert deposit.amount.amount == Decimal("50000.00")

    def test_amount_quantized_to_two_decimals(self) -> None:
        deposit = Deposit(
            agreement_id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            amount=Money(Decimal("50000.006")),
            received_date=date(2026, 1, 5),
        )
        assert deposit.amount.amount == Decimal("50000.01")

    def test_rejects_non_money_amount(self) -> None:
        with pytest.raises(ValueError, match="must be a Money object"):
            Deposit(
                agreement_id=uuid.uuid4(),
                tenant_id=uuid.uuid4(),
                amount=Decimal("50000"),
                received_date=date(2026, 1, 5),
            )

    def test_rejects_zero_amount(self) -> None:
        with pytest.raises(ValueError, match="greater than zero"):
            Deposit(
                agreement_id=uuid.uuid4(),
                tenant_id=uuid.uuid4(),
                amount=Money(Decimal("0")),
                received_date=date(2026, 1, 5),
            )

    def test_rejects_negative_amount(self) -> None:
        with pytest.raises(ValueError, match="cannot be negative"):
            Deposit(
                agreement_id=uuid.uuid4(),
                tenant_id=uuid.uuid4(),
                amount=Money(Decimal("-5")),
                received_date=date(2026, 1, 5),
            )

    def test_rejects_invalid_status(self) -> None:
        with pytest.raises(ValueError, match="Invalid deposit status"):
            Deposit(
                agreement_id=uuid.uuid4(),
                tenant_id=uuid.uuid4(),
                amount=Money(Decimal("50000")),
                received_date=date(2026, 1, 5),
                status="held",
            )

    def test_strips_reference_and_notes(self) -> None:
        deposit = Deposit(
            agreement_id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            amount=Money(Decimal("50000")),
            received_date=date(2026, 1, 5),
            reference="  DEP-001  ",
            notes="  Received by bank  ",
        )
        assert deposit.reference == "DEP-001"
        assert deposit.notes == "Received by bank"

    def test_settle_sets_status(self) -> None:
        deposit = Deposit(
            agreement_id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            amount=Money(Decimal("50000")),
            received_date=date(2026, 1, 5),
        )
        deposit.settle()
        assert deposit.status == DepositStatus.SETTLED
        assert deposit.is_held is False

    def test_settle_twice_rejected(self) -> None:
        deposit = Deposit(
            agreement_id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            amount=Money(Decimal("50000")),
            received_date=date(2026, 1, 5),
        )
        deposit.settle()
        with pytest.raises(ValueError, match="Cannot settle"):
            deposit.settle()

    def test_void_sets_status(self) -> None:
        deposit = Deposit(
            agreement_id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            amount=Money(Decimal("50000")),
            received_date=date(2026, 1, 5),
        )
        deposit.void()
        assert deposit.status == DepositStatus.VOID

    def test_settle_voided_deposit_rejected(self) -> None:
        deposit = Deposit(
            agreement_id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            amount=Money(Decimal("50000")),
            received_date=date(2026, 1, 5),
        )
        deposit.void()
        with pytest.raises(ValueError, match="Cannot settle"):
            deposit.settle()


class TestDepositDeduction:
    def test_valid_deduction(self) -> None:
        deduction = DepositDeduction(
            settlement_id=uuid.uuid4(),
            amount=Money(Decimal("10000")),
            reason="Damage to room",
        )
        assert deduction.amount.amount == Decimal("10000.00")
        assert deduction.reason == "Damage to room"

    def test_rejects_zero_amount(self) -> None:
        with pytest.raises(ValueError, match="greater than zero"):
            DepositDeduction(
                settlement_id=uuid.uuid4(),
                amount=Money(Decimal("0")),
                reason="Damage",
            )

    def test_rejects_missing_reason(self) -> None:
        with pytest.raises(ValueError, match="reason is required"):
            DepositDeduction(
                settlement_id=uuid.uuid4(),
                amount=Money(Decimal("10000")),
                reason="   ",
            )

    def test_strips_reason(self) -> None:
        deduction = DepositDeduction(
            settlement_id=uuid.uuid4(),
            amount=Money(Decimal("10000")),
            reason="  Damage  ",
        )
        assert deduction.reason == "Damage"


class TestDepositSettlement:
    def test_valid_settlement_incomplete_by_default(self) -> None:
        settlement = DepositSettlement(
            deposit_id=uuid.uuid4(),
            settlement_date=date(2026, 6, 30),
        )
        assert settlement.is_complete is False
        assert settlement.total_deductions.amount == Decimal("0.00")
        assert settlement.refund_amount is None

    def test_total_deductions_sums_lines(self) -> None:
        settlement = DepositSettlement(deposit_id=uuid.uuid4(), settlement_date=date(2026, 6, 30))
        settlement.add_deduction(DepositDeduction(amount=Money(Decimal("10000")), reason="Damage"))
        settlement.add_deduction(DepositDeduction(amount=Money(Decimal("5000")), reason="Cleaning"))
        assert settlement.total_deductions.amount == Decimal("15000.00")
        assert settlement.deductions[0].settlement_id == settlement.id

    def test_record_refund_completes(self) -> None:
        settlement = DepositSettlement(deposit_id=uuid.uuid4(), settlement_date=date(2026, 6, 30))
        settlement.add_deduction(DepositDeduction(amount=Money(Decimal("10000")), reason="Damage"))
        settlement.record_refund(Money(Decimal("40000")))
        assert settlement.is_complete is True
        assert settlement.refund_amount.amount == Decimal("40000.00")

    def test_record_refund_twice_rejected(self) -> None:
        settlement = DepositSettlement(deposit_id=uuid.uuid4(), settlement_date=date(2026, 6, 30))
        settlement.record_refund(Money(Decimal("50000")))
        with pytest.raises(ValueError, match="already has a recorded refund"):
            settlement.record_refund(Money(Decimal("10000")))

    def test_record_negative_refund_rejected(self) -> None:
        settlement = DepositSettlement(deposit_id=uuid.uuid4(), settlement_date=date(2026, 6, 30))
        with pytest.raises(ValueError, match="cannot be negative"):
            settlement.record_refund(Money(Decimal("-5")))

    def test_add_deduction_after_completion_rejected(self) -> None:
        settlement = DepositSettlement(deposit_id=uuid.uuid4(), settlement_date=date(2026, 6, 30))
        settlement.record_refund(Money(Decimal("50000")))
        with pytest.raises(ValueError, match="completed settlement"):
            settlement.add_deduction(DepositDeduction(amount=Money(Decimal("10000")), reason="Damage"))
