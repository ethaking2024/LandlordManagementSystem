from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from app.core.exceptions import NotFoundError, ValidationError
from app.domain.entities import Deposit, DepositDeduction, DepositSettlement
from app.domain.enums import AgreementStatus, DepositStatus
from app.domain.value_objects import Money
from app.infrastructure.repositories import (
    AgreementRepository,
    DepositRepository,
    DepositSettlementRepository,
)


class DepositService:
    """Records security deposits and settles them when agreements end.

    Deposits are held money that is separate from bill payments and tenant
    credit. Recording, settling or refunding a deposit never creates a payment,
    never touches a bill, and never creates tenant credit. Settlement is always
    validated in full before anything is persisted.
    """

    def __init__(
        self,
        deposit_repository: DepositRepository,
        deposit_settlement_repository: DepositSettlementRepository,
        agreement_repository: AgreementRepository,
    ) -> None:
        self._deposit_repository = deposit_repository
        self._deposit_settlement_repository = deposit_settlement_repository
        self._agreement_repository = agreement_repository

    # ------------------------------------------------------------------
    # Deposits
    # ------------------------------------------------------------------

    def record_deposit(
        self,
        agreement_id: uuid.UUID,
        amount: Money,
        received_date: date,
        reference: str | None = None,
        notes: str | None = None,
    ) -> Deposit:
        agreement = self._agreement_repository.get(agreement_id)
        if not agreement:
            raise NotFoundError(f"Agreement with id {agreement_id} not found")
        if not isinstance(amount, Money):
            raise ValidationError("Deposit amount must be a Money object")
        if amount.amount <= 0:
            raise ValidationError("Deposit amount must be greater than zero")

        deposit = Deposit(
            agreement_id=agreement.id,
            tenant_id=agreement.tenant_id,
            amount=amount,
            received_date=received_date,
            reference=reference.strip() if reference else None,
            notes=notes.strip() if notes else None,
        )
        return self._deposit_repository.add(deposit)

    def get_deposit(self, deposit_id: uuid.UUID) -> Deposit:
        deposit = self._deposit_repository.get(deposit_id)
        if not deposit:
            raise NotFoundError(f"Deposit with id {deposit_id} not found")
        return deposit

    def get_deposits_by_agreement(self, agreement_id: uuid.UUID, limit: int = 100, offset: int = 0) -> list[Deposit]:
        return self._deposit_repository.get_by_agreement(agreement_id, limit=limit, offset=offset)

    def get_all_deposits(self, limit: int = 100, offset: int = 0) -> list[Deposit]:
        return self._deposit_repository.get_all(limit=limit, offset=offset)

    def get_deposit_balance(self, deposit_id: uuid.UUID) -> Money:
        deposit = self.get_deposit(deposit_id)
        if deposit.status != DepositStatus.HELD:
            return Money(Decimal("0"))
        return deposit.amount

    def get_agreement_deposit_balance(self, agreement_id: uuid.UUID) -> Money:
        deposits = self._deposit_repository.get_held_by_agreement(agreement_id)
        total = sum((d.amount.amount for d in deposits), Decimal("0"))
        return Money(total)

    def void_deposit(self, deposit_id: uuid.UUID) -> Deposit:
        deposit = self.get_deposit(deposit_id)
        if deposit.status != DepositStatus.HELD:
            raise ValidationError(f"Cannot void a deposit with status {deposit.status.value}")
        deposit.void()
        return self._deposit_repository.update(deposit)

    # ------------------------------------------------------------------
    # Settlement
    # ------------------------------------------------------------------

    def create_settlement(
        self,
        deposit_id: uuid.UUID,
        settlement_date: date,
        deductions: list[tuple[Decimal | str, str]],
        notes: str | None = None,
    ) -> DepositSettlement:
        deposit = self.get_deposit(deposit_id)
        if deposit.status != DepositStatus.HELD:
            raise ValidationError(
                f"Cannot settle a deposit with status {deposit.status.value}; only held deposits can be settled"
            )
        if self._deposit_settlement_repository.has_settlement_for_deposit(deposit_id):
            raise ValidationError(f"Deposit {deposit_id} has already been settled")

        agreement = self._agreement_repository.get(deposit.agreement_id)
        if not agreement:
            raise NotFoundError(f"Agreement with id {deposit.agreement_id} not found")
        if agreement.status == AgreementStatus.ACTIVE:
            raise ValidationError("Cannot settle a deposit while the agreement is active")

        if settlement_date < deposit.received_date:
            raise ValidationError("Settlement date cannot be before the deposit was received")

        deduction_entities: list[DepositDeduction] = []
        total_deductions = Decimal("0")
        for amount, reason in deductions:
            deduction_amount = Decimal(str(amount))
            if deduction_amount <= 0:
                raise ValidationError("Deduction amount must be greater than zero")
            if not reason or not reason.strip():
                raise ValidationError("Deduction reason is required")
            total_deductions += deduction_amount
            deduction_entities.append(DepositDeduction(amount=Money(deduction_amount), reason=reason.strip()))

        if total_deductions > deposit.amount.amount:
            raise ValidationError(
                f"Total deductions {Money(total_deductions)} cannot exceed the deposit amount {deposit.amount}"
            )

        settlement = DepositSettlement(
            deposit_id=deposit.id,
            settlement_date=settlement_date,
            notes=notes.strip() if notes else None,
        )
        for deduction in deduction_entities:
            settlement.add_deduction(deduction)
        return self._deposit_settlement_repository.add(settlement)

    def complete_settlement(self, deposit_id: uuid.UUID, refund_amount: Money) -> DepositSettlement:
        deposit = self.get_deposit(deposit_id)
        if deposit.status != DepositStatus.HELD:
            raise ValidationError(
                f"Cannot settle a deposit with status {deposit.status.value}; only held deposits can be settled"
            )

        settlement = self._deposit_settlement_repository.get_by_deposit(deposit_id)
        if not settlement:
            raise ValidationError(f"Deposit {deposit_id} has no settlement to complete")
        if settlement.is_complete:
            raise ValidationError(f"Deposit {deposit_id} has already been settled")

        agreement = self._agreement_repository.get(deposit.agreement_id)
        if not agreement:
            raise NotFoundError(f"Agreement with id {deposit.agreement_id} not found")
        if agreement.status == AgreementStatus.ACTIVE:
            raise ValidationError("Cannot settle a deposit while the agreement is active")

        if not isinstance(refund_amount, Money):
            raise ValidationError("Refund amount must be a Money object")
        if refund_amount.amount < 0:
            raise ValidationError("Refund amount cannot be negative")

        total_deductions = settlement.total_deductions.amount
        expected_refund = deposit.amount.amount - total_deductions
        if refund_amount.amount != expected_refund:
            raise ValidationError(
                f"Refund amount {refund_amount} plus deductions {settlement.total_deductions} "
                f"must equal the deposit amount {deposit.amount} (expected refund {Money(expected_refund)})"
            )

        settlement.record_refund(refund_amount)
        deposit.settle()
        self._deposit_settlement_repository.update(settlement)
        self._deposit_repository.update(deposit)
        return settlement

    def get_settlement_by_deposit(self, deposit_id: uuid.UUID) -> DepositSettlement | None:
        return self._deposit_settlement_repository.get_by_deposit(deposit_id)
