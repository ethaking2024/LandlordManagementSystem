from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.application.services import DepositService
from app.core.exceptions import NotFoundError, ValidationError
from app.domain.entities import Agreement, Deposit, DepositDeduction, DepositSettlement
from app.domain.enums import AgreementStatus, DepositStatus
from app.domain.value_objects import Money


def _agreement(status: AgreementStatus = AgreementStatus.ENDED) -> Agreement:
    return Agreement(
        tenant_id=uuid.uuid4(),
        rental_space_id=uuid.uuid4(),
        start_date=date(2026, 1, 1),
        end_date=date(2026, 6, 30),
        monthly_rent=Money(Decimal("15000")),
        status=status,
    )


def _held_deposit(agreement: Agreement, amount: str = "50000") -> Deposit:
    return Deposit(
        agreement_id=agreement.id,
        tenant_id=agreement.tenant_id,
        amount=Money(Decimal(amount)),
        received_date=date(2026, 1, 5),
        status=DepositStatus.HELD,
    )


class TestRecordDeposit:
    @pytest.fixture
    def service(self) -> DepositService:
        return DepositService(MagicMock(), MagicMock(), MagicMock())

    def test_record_deposit(self, service: DepositService) -> None:
        agreement = _agreement()
        service._agreement_repository.get.return_value = agreement
        service._deposit_repository.add.side_effect = lambda d: d

        result = service.record_deposit(
            agreement.id,
            Money(Decimal("50000")),
            date(2026, 1, 5),
            reference="DEP-001",
        )

        assert result.amount.amount == Decimal("50000.00")
        assert result.status == DepositStatus.HELD
        assert result.tenant_id == agreement.tenant_id
        assert result.agreement_id == agreement.id
        service._deposit_repository.add.assert_called_once()

    def test_record_deposit_agreement_not_found(self, service: DepositService) -> None:
        service._agreement_repository.get.return_value = None
        with pytest.raises(NotFoundError, match="Agreement"):
            service.record_deposit(uuid.uuid4(), Money(Decimal("50000")), date(2026, 1, 5))

    def test_record_deposit_zero_rejected(self, service: DepositService) -> None:
        agreement = _agreement()
        service._agreement_repository.get.return_value = agreement
        with pytest.raises(ValidationError, match="greater than zero"):
            service.record_deposit(agreement.id, Money(Decimal("0")), date(2026, 1, 5))


class TestDepositBalance:
    @pytest.fixture
    def service(self) -> DepositService:
        return DepositService(MagicMock(), MagicMock(), MagicMock())

    def test_balance_held_deposit(self, service: DepositService) -> None:
        agreement = _agreement()
        deposit = _held_deposit(agreement)
        service._deposit_repository.get.return_value = deposit

        balance = service.get_deposit_balance(deposit.id)

        assert balance.amount == Decimal("50000.00")

    def test_balance_settled_deposit_is_zero(self, service: DepositService) -> None:
        agreement = _agreement()
        deposit = _held_deposit(agreement)
        deposit.settle()
        service._deposit_repository.get.return_value = deposit

        balance = service.get_deposit_balance(deposit.id)

        assert balance.amount == Decimal("0.00")

    def test_balance_voided_deposit_is_zero(self, service: DepositService) -> None:
        agreement = _agreement()
        deposit = _held_deposit(agreement)
        deposit.void()
        service._deposit_repository.get.return_value = deposit

        balance = service.get_deposit_balance(deposit.id)

        assert balance.amount == Decimal("0.00")

    def test_agreement_balance_sums_held_deposits(self, service: DepositService) -> None:
        agreement = _agreement()
        d1 = _held_deposit(agreement, "50000")
        d2 = _held_deposit(agreement, "20000")
        service._deposit_repository.get_held_by_agreement.return_value = [d1, d2]

        balance = service.get_agreement_deposit_balance(agreement.id)

        assert balance.amount == Decimal("70000.00")

    def test_balance_deposit_not_found(self, service: DepositService) -> None:
        service._deposit_repository.get.return_value = None
        with pytest.raises(NotFoundError, match="Deposit"):
            service.get_deposit_balance(uuid.uuid4())


class TestVoidDeposit:
    @pytest.fixture
    def service(self) -> DepositService:
        return DepositService(MagicMock(), MagicMock(), MagicMock())

    def test_void_deposit(self, service: DepositService) -> None:
        agreement = _agreement()
        deposit = _held_deposit(agreement)
        service._deposit_repository.get.return_value = deposit
        service._deposit_repository.update.side_effect = lambda d: d

        result = service.void_deposit(deposit.id)

        assert result.status == DepositStatus.VOID
        service._deposit_repository.update.assert_called_once()

    def test_void_settled_deposit_rejected(self, service: DepositService) -> None:
        agreement = _agreement()
        deposit = _held_deposit(agreement)
        deposit.settle()
        service._deposit_repository.get.return_value = deposit

        with pytest.raises(ValidationError, match="Cannot void"):
            service.void_deposit(deposit.id)


class TestCreateSettlement:
    @pytest.fixture
    def service(self) -> DepositService:
        return DepositService(MagicMock(), MagicMock(), MagicMock())

    def test_create_settlement_full_refund_path(self, service: DepositService) -> None:
        agreement = _agreement()
        deposit = _held_deposit(agreement)
        service._deposit_repository.get.return_value = deposit
        service._deposit_settlement_repository.has_settlement_for_deposit.return_value = False
        service._agreement_repository.get.return_value = agreement
        service._deposit_settlement_repository.add.side_effect = lambda s: s

        settlement = service.create_settlement(deposit.id, date(2026, 6, 30), [("10000", "Damage")])

        assert settlement.total_deductions.amount == Decimal("10000.00")
        assert settlement.is_complete is False
        assert len(settlement.deductions) == 1
        service._deposit_settlement_repository.add.assert_called_once()

    def test_create_settlement_with_multiple_deductions(self, service: DepositService) -> None:
        agreement = _agreement()
        deposit = _held_deposit(agreement)
        service._deposit_repository.get.return_value = deposit
        service._deposit_settlement_repository.has_settlement_for_deposit.return_value = False
        service._agreement_repository.get.return_value = agreement
        service._deposit_settlement_repository.add.side_effect = lambda s: s

        settlement = service.create_settlement(
            deposit.id, date(2026, 6, 30), [("10000", "Damage"), ("5000", "Cleaning")]
        )

        assert settlement.total_deductions.amount == Decimal("15000.00")
        assert len(settlement.deductions) == 2

    def test_create_settlement_deposit_not_found(self, service: DepositService) -> None:
        service._deposit_repository.get.return_value = None
        with pytest.raises(NotFoundError, match="Deposit"):
            service.create_settlement(uuid.uuid4(), date(2026, 6, 30), [("10000", "Damage")])

    def test_create_settlement_voided_deposit_rejected(self, service: DepositService) -> None:
        agreement = _agreement()
        deposit = _held_deposit(agreement)
        deposit.void()
        service._deposit_repository.get.return_value = deposit

        with pytest.raises(ValidationError, match="only held deposits"):
            service.create_settlement(deposit.id, date(2026, 6, 30), [("10000", "Damage")])

    def test_create_settlement_double_settlement_rejected(self, service: DepositService) -> None:
        agreement = _agreement()
        deposit = _held_deposit(agreement)
        service._deposit_repository.get.return_value = deposit
        service._deposit_settlement_repository.has_settlement_for_deposit.return_value = True

        with pytest.raises(ValidationError, match="already been settled"):
            service.create_settlement(deposit.id, date(2026, 6, 30), [("10000", "Damage")])

    def test_create_settlement_active_agreement_rejected(self, service: DepositService) -> None:
        agreement = _agreement(AgreementStatus.ACTIVE)
        deposit = _held_deposit(agreement)
        service._deposit_repository.get.return_value = deposit
        service._deposit_settlement_repository.has_settlement_for_deposit.return_value = False
        service._agreement_repository.get.return_value = agreement

        with pytest.raises(ValidationError, match="agreement is active"):
            service.create_settlement(deposit.id, date(2026, 6, 30), [("10000", "Damage")])

    def test_create_settlement_deductions_exceed_deposit_rejected(self, service: DepositService) -> None:
        agreement = _agreement()
        deposit = _held_deposit(agreement, "50000")
        service._deposit_repository.get.return_value = deposit
        service._deposit_settlement_repository.has_settlement_for_deposit.return_value = False
        service._agreement_repository.get.return_value = agreement

        with pytest.raises(ValidationError, match="cannot exceed the deposit amount"):
            service.create_settlement(deposit.id, date(2026, 6, 30), [("60000", "Damage")])

    def test_create_settlement_zero_deduction_rejected(self, service: DepositService) -> None:
        agreement = _agreement()
        deposit = _held_deposit(agreement)
        service._deposit_repository.get.return_value = deposit
        service._deposit_settlement_repository.has_settlement_for_deposit.return_value = False
        service._agreement_repository.get.return_value = agreement

        with pytest.raises(ValidationError, match="greater than zero"):
            service.create_settlement(deposit.id, date(2026, 6, 30), [("0", "Damage")])

    def test_create_settlement_negative_deduction_rejected(self, service: DepositService) -> None:
        agreement = _agreement()
        deposit = _held_deposit(agreement)
        service._deposit_repository.get.return_value = deposit
        service._deposit_settlement_repository.has_settlement_for_deposit.return_value = False
        service._agreement_repository.get.return_value = agreement

        with pytest.raises(ValidationError, match="greater than zero"):
            service.create_settlement(deposit.id, date(2026, 6, 30), [("-1000", "Damage")])

    def test_create_settlement_missing_reason_rejected(self, service: DepositService) -> None:
        agreement = _agreement()
        deposit = _held_deposit(agreement)
        service._deposit_repository.get.return_value = deposit
        service._deposit_settlement_repository.has_settlement_for_deposit.return_value = False
        service._agreement_repository.get.return_value = agreement

        with pytest.raises(ValidationError, match="reason is required"):
            service.create_settlement(deposit.id, date(2026, 6, 30), [("10000", "  ")])

    def test_create_settlement_date_before_received_rejected(self, service: DepositService) -> None:
        agreement = _agreement()
        deposit = _held_deposit(agreement)
        service._deposit_repository.get.return_value = deposit
        service._deposit_settlement_repository.has_settlement_for_deposit.return_value = False
        service._agreement_repository.get.return_value = agreement

        with pytest.raises(ValidationError, match="before the deposit was received"):
            service.create_settlement(deposit.id, date(2025, 12, 31), [("10000", "Damage")])

    def test_failed_settlement_persists_nothing(self, service: DepositService) -> None:
        agreement = _agreement()
        deposit = _held_deposit(agreement, "50000")
        service._deposit_repository.get.return_value = deposit
        service._deposit_settlement_repository.has_settlement_for_deposit.return_value = False
        service._agreement_repository.get.return_value = agreement

        with pytest.raises(ValidationError, match="cannot exceed the deposit amount"):
            service.create_settlement(deposit.id, date(2026, 6, 30), [("60000", "Damage")])

        service._deposit_settlement_repository.add.assert_not_called()


class TestCompleteSettlement:
    @pytest.fixture
    def service(self) -> DepositService:
        return DepositService(MagicMock(), MagicMock(), MagicMock())

    def _setup(self, service: DepositService, agreement: Agreement, deposit: Deposit) -> None:
        service._deposit_repository.get.return_value = deposit
        service._agreement_repository.get.return_value = agreement

    def test_full_refund(self, service: DepositService) -> None:
        agreement = _agreement()
        deposit = _held_deposit(agreement)
        settlement = DepositSettlement(deposit_id=deposit.id, settlement_date=date(2026, 6, 30))
        self._setup(service, agreement, deposit)
        service._deposit_settlement_repository.get_by_deposit.return_value = settlement
        service._deposit_settlement_repository.update.side_effect = lambda s: s
        service._deposit_repository.update.side_effect = lambda d: d

        result = service.complete_settlement(deposit.id, Money(Decimal("50000")))

        assert result.is_complete is True
        assert result.refund_amount.amount == Decimal("50000.00")
        assert deposit.status == DepositStatus.SETTLED
        service._deposit_settlement_repository.update.assert_called_once()
        service._deposit_repository.update.assert_called_once()

    def test_deduction_plus_refund(self, service: DepositService) -> None:
        agreement = _agreement()
        deposit = _held_deposit(agreement)
        settlement = DepositSettlement(deposit_id=deposit.id, settlement_date=date(2026, 6, 30))
        settlement.add_deduction(DepositDeduction(amount=Money(Decimal("10000")), reason="Damage"))
        self._setup(service, agreement, deposit)
        service._deposit_settlement_repository.get_by_deposit.return_value = settlement
        service._deposit_settlement_repository.update.side_effect = lambda s: s
        service._deposit_repository.update.side_effect = lambda d: d

        result = service.complete_settlement(deposit.id, Money(Decimal("40000")))

        assert result.refund_amount.amount == Decimal("40000.00")
        assert result.total_deductions.amount == Decimal("10000.00")
        assert deposit.status == DepositStatus.SETTLED

    def test_refund_exceeds_deposit_rejected(self, service: DepositService) -> None:
        agreement = _agreement()
        deposit = _held_deposit(agreement)
        settlement = DepositSettlement(deposit_id=deposit.id, settlement_date=date(2026, 6, 30))
        self._setup(service, agreement, deposit)
        service._deposit_settlement_repository.get_by_deposit.return_value = settlement

        with pytest.raises(ValidationError, match="must equal the deposit amount"):
            service.complete_settlement(deposit.id, Money(Decimal("60000")))

    def test_refund_and_deductions_exceed_deposit_rejected(self, service: DepositService) -> None:
        agreement = _agreement()
        deposit = _held_deposit(agreement)
        settlement = DepositSettlement(deposit_id=deposit.id, settlement_date=date(2026, 6, 30))
        settlement.add_deduction(DepositDeduction(amount=Money(Decimal("10000")), reason="Damage"))
        self._setup(service, agreement, deposit)
        service._deposit_settlement_repository.get_by_deposit.return_value = settlement

        with pytest.raises(ValidationError, match="must equal the deposit amount"):
            service.complete_settlement(deposit.id, Money(Decimal("50000")))

    def test_refund_negative_rejected(self, service: DepositService) -> None:
        agreement = _agreement()
        deposit = _held_deposit(agreement)
        settlement = DepositSettlement(deposit_id=deposit.id, settlement_date=date(2026, 6, 30))
        self._setup(service, agreement, deposit)
        service._deposit_settlement_repository.get_by_deposit.return_value = settlement

        with pytest.raises(ValueError, match="cannot be negative"):
            service.complete_settlement(deposit.id, Money(Decimal("-5")))

    def test_double_completion_rejected(self, service: DepositService) -> None:
        agreement = _agreement()
        deposit = _held_deposit(agreement)
        settlement = DepositSettlement(deposit_id=deposit.id, settlement_date=date(2026, 6, 30))
        settlement.record_refund(Money(Decimal("50000")))
        self._setup(service, agreement, deposit)
        service._deposit_settlement_repository.get_by_deposit.return_value = settlement

        with pytest.raises(ValidationError, match="already been settled"):
            service.complete_settlement(deposit.id, Money(Decimal("50000")))

    def test_voided_deposit_cannot_complete(self, service: DepositService) -> None:
        agreement = _agreement()
        deposit = _held_deposit(agreement)
        deposit.void()
        self._setup(service, agreement, deposit)

        with pytest.raises(ValidationError, match="only held deposits"):
            service.complete_settlement(deposit.id, Money(Decimal("50000")))

    def test_active_agreement_cannot_complete(self, service: DepositService) -> None:
        agreement = _agreement(AgreementStatus.ACTIVE)
        deposit = _held_deposit(agreement)
        settlement = DepositSettlement(deposit_id=deposit.id, settlement_date=date(2026, 6, 30))
        self._setup(service, agreement, deposit)
        service._deposit_settlement_repository.get_by_deposit.return_value = settlement

        with pytest.raises(ValidationError, match="agreement is active"):
            service.complete_settlement(deposit.id, Money(Decimal("50000")))

    def test_no_settlement_rejected(self, service: DepositService) -> None:
        agreement = _agreement()
        deposit = _held_deposit(agreement)
        self._setup(service, agreement, deposit)
        service._deposit_settlement_repository.get_by_deposit.return_value = None

        with pytest.raises(ValidationError, match="no settlement"):
            service.complete_settlement(deposit.id, Money(Decimal("50000")))

    def test_failed_completion_persists_nothing(self, service: DepositService) -> None:
        agreement = _agreement()
        deposit = _held_deposit(agreement)
        settlement = DepositSettlement(deposit_id=deposit.id, settlement_date=date(2026, 6, 30))
        self._setup(service, agreement, deposit)
        service._deposit_settlement_repository.get_by_deposit.return_value = settlement

        with pytest.raises(ValidationError, match="must equal the deposit amount"):
            service.complete_settlement(deposit.id, Money(Decimal("60000")))

        service._deposit_settlement_repository.update.assert_not_called()
        service._deposit_repository.update.assert_not_called()


class TestGetAllDeposits:
    @pytest.fixture
    def service(self) -> DepositService:
        return DepositService(MagicMock(), MagicMock(), MagicMock())

    def test_get_all_deposits_delegates_to_repository(self, service: DepositService) -> None:
        agreement = _agreement()
        deposit = _held_deposit(agreement)
        service._deposit_repository.get_all.return_value = [deposit]

        result = service.get_all_deposits()

        service._deposit_repository.get_all.assert_called_once_with(limit=100, offset=0)
        assert result == [deposit]

    def test_get_all_deposits_empty(self, service: DepositService) -> None:
        service._deposit_repository.get_all.return_value = []

        result = service.get_all_deposits()

        assert result == []


class TestGetDepositsByDateRange:
    @pytest.fixture
    def service(self) -> DepositService:
        return DepositService(MagicMock(), MagicMock(), MagicMock())

    def test_delegates_to_repository(self, service: DepositService) -> None:
        agreement = _agreement()
        deposit = _held_deposit(agreement)
        service._deposit_repository.get_by_date_range.return_value = [deposit]

        result = service.get_deposits_by_date_range(date(2026, 1, 1), date(2026, 1, 31))

        service._deposit_repository.get_by_date_range.assert_called_once_with(
            date(2026, 1, 1), date(2026, 1, 31), limit=10000, offset=0
        )
        assert result == [deposit]

    def test_empty_range(self, service: DepositService) -> None:
        service._deposit_repository.get_by_date_range.return_value = []

        result = service.get_deposits_by_date_range(date(2026, 1, 1), date(2026, 1, 31))

        assert result == []


class TestDistinction:
    @pytest.fixture
    def service(self) -> DepositService:
        return DepositService(MagicMock(), MagicMock(), MagicMock())

    def test_deposit_not_a_payment(self, service: DepositService) -> None:
        agreement = _agreement()
        service._agreement_repository.get.return_value = agreement
        service._deposit_repository.add.side_effect = lambda d: d

        result = service.record_deposit(agreement.id, Money(Decimal("50000")), date(2026, 1, 5))

        # The deposit record is independent; no payment repository is involved.
        assert result.id is not None
        assert not hasattr(service, "_payment_repository")

    def test_deposit_balance_never_touches_payments(self, service: DepositService) -> None:
        agreement = _agreement()
        deposit = _held_deposit(agreement)
        service._deposit_repository.get.return_value = deposit

        balance = service.get_deposit_balance(deposit.id)

        assert balance.amount == Decimal("50000.00")

    def test_refund_does_not_create_tenant_credit(self, service: DepositService) -> None:
        agreement = _agreement()
        deposit = _held_deposit(agreement)
        settlement = DepositSettlement(deposit_id=deposit.id, settlement_date=date(2026, 6, 30))
        service._deposit_repository.get.return_value = deposit
        service._agreement_repository.get.return_value = agreement
        service._deposit_settlement_repository.get_by_deposit.return_value = settlement
        service._deposit_settlement_repository.update.side_effect = lambda s: s
        service._deposit_repository.update.side_effect = lambda d: d

        result = service.complete_settlement(deposit.id, Money(Decimal("50000")))

        assert result.refund_amount.amount == Decimal("50000.00")
        assert deposit.status == DepositStatus.SETTLED
        # No payment, no allocation, no bill mutation is involved.
        assert not hasattr(service, "_payment_repository")
        assert not hasattr(service, "_bill_repository")


class TestAgreementIntegration:
    @pytest.fixture
    def service(self) -> DepositService:
        return DepositService(MagicMock(), MagicMock(), MagicMock())

    def test_settlement_preserves_deposit_links_and_history(self, service: DepositService) -> None:
        agreement = _agreement()
        deposit = _held_deposit(agreement)
        settlement = DepositSettlement(deposit_id=deposit.id, settlement_date=date(2026, 6, 30))
        settlement.add_deduction(DepositDeduction(amount=Money(Decimal("10000")), reason="Damage"))
        service._deposit_repository.get.return_value = deposit
        service._agreement_repository.get.return_value = agreement
        service._deposit_settlement_repository.get_by_deposit.return_value = settlement
        service._deposit_settlement_repository.update.side_effect = lambda s: s
        service._deposit_repository.update.side_effect = lambda d: d

        service.complete_settlement(deposit.id, Money(Decimal("40000")))

        # The deposit and settlement keep their references to the agreement.
        assert deposit.agreement_id == agreement.id
        assert deposit.status == DepositStatus.SETTLED
        assert settlement.deposit_id == deposit.id
        assert settlement.is_complete is True
        # Historical deduction is preserved.
        assert settlement.total_deductions.amount == Decimal("10000.00")
