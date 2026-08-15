from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.application.services import PaymentService
from app.core.exceptions import NotFoundError, ValidationError
from app.domain.entities import Bill, BillLine, Payment, PaymentAllocation, Tenant
from app.domain.enums import BillCategory, BillStatus, PaymentMethod, PaymentStatus
from app.domain.value_objects import BillingPeriod, Money


def _tenant() -> Tenant:
    from app.domain.value_objects import PhoneNumber

    return Tenant(full_name="Ram Sharma", phone=PhoneNumber("9841000000"))


def _confirmed_bill(tenant_id: uuid.UUID, total: str = "20000") -> Bill:
    bill = Bill(
        agreement_id=uuid.uuid4(),
        tenant_id=tenant_id,
        rental_space_id=uuid.uuid4(),
        period=BillingPeriod(date(2026, 1, 1), date(2026, 1, 31)),
        billing_date=date(2026, 1, 31),
        status=BillStatus.CONFIRMED,
        lines=[BillLine(category=BillCategory.RENT, description="rent", amount=Money(Decimal(total)))],
    )
    return bill


def _recorded_payment(tenant_id: uuid.UUID, amount: str = "8000", payment_date: date = date(2026, 1, 10)) -> Payment:
    return Payment(
        tenant_id=tenant_id,
        payment_date=payment_date,
        amount=Money(Decimal(amount)),
        payment_method=PaymentMethod.CASH,
        status=PaymentStatus.RECORDED,
    )


def _void_payment(tenant_id: uuid.UUID, amount: str = "8000") -> Payment:
    payment = _recorded_payment(tenant_id, amount)
    payment.void()
    return payment


class TestRecordPayment:
    @pytest.fixture
    def service(self) -> PaymentService:
        return PaymentService(MagicMock(), MagicMock(), MagicMock(), MagicMock())

    def test_record_payment(self, service: PaymentService) -> None:
        tenant = _tenant()
        service._tenant_repository.get.return_value = tenant
        service._payment_repository.add.side_effect = lambda p: p

        result = service.record_payment(
            tenant.id,
            date(2026, 1, 10),
            Money(Decimal("8000")),
            PaymentMethod.CASH,
            reference="REF-1",
        )

        assert result.amount.amount == Decimal("8000.00")
        assert result.status == PaymentStatus.RECORDED
        assert result.payment_method == PaymentMethod.CASH
        service._payment_repository.add.assert_called_once()

    def test_record_payment_tenant_not_found(self, service: PaymentService) -> None:
        service._tenant_repository.get.return_value = None
        with pytest.raises(NotFoundError, match="Tenant"):
            service.record_payment(
                uuid.uuid4(),
                date(2026, 1, 10),
                Money(Decimal("8000")),
                PaymentMethod.CASH,
            )

    def test_record_payment_zero_rejected(self, service: PaymentService) -> None:
        tenant = _tenant()
        service._tenant_repository.get.return_value = tenant
        with pytest.raises(ValueError, match="greater than zero"):
            service.record_payment(tenant.id, date(2026, 1, 10), Money(Decimal("0")), PaymentMethod.CASH)


class TestFullPayment:
    @pytest.fixture
    def service(self) -> PaymentService:
        return PaymentService(MagicMock(), MagicMock(), MagicMock(), MagicMock())

    def _setup(self, service: PaymentService, tenant: Tenant, bill: Bill, payment: Payment) -> None:
        store: list[PaymentAllocation] = []
        service._bill_repository.get.return_value = bill
        service._payment_repository.get.return_value = payment
        service._payment_allocation_repository.has_allocation_for.return_value = False
        service._payment_allocation_repository.get_valid_by_bill.side_effect = lambda _bill_id: store
        service._payment_allocation_repository.get_by_payment.return_value = []
        service._payment_allocation_repository.add.side_effect = lambda a: (store.append(a) or a)

    def test_exact_payment_bill_fully_paid(self, service: PaymentService) -> None:
        tenant = _tenant()
        bill = _confirmed_bill(tenant.id, "20000")
        payment = _recorded_payment(tenant.id, "20000")
        self._setup(service, tenant, bill, payment)

        allocation = service.allocate_payment(payment.id, bill.id, Money(Decimal("20000")))

        assert allocation.allocated_amount.amount == Decimal("20000.00")
        balance = service.calculate_bill_balance(bill.id)
        assert balance.total.amount == Decimal("20000.00")
        assert balance.allocated.amount == Decimal("20000.00")
        assert balance.outstanding.amount == Decimal("0.00")

    def test_payment_must_match_bill_tenant(self, service: PaymentService) -> None:
        tenant = _tenant()
        other_tenant = uuid.uuid4()
        bill = _confirmed_bill(other_tenant, "20000")
        payment = _recorded_payment(tenant.id, "20000")
        self._setup(service, tenant, bill, payment)

        with pytest.raises(ValidationError, match="same tenant"):
            service.allocate_payment(payment.id, bill.id, Money(Decimal("20000")))


class TestPartialPayment:
    @pytest.fixture
    def service(self) -> PaymentService:
        return PaymentService(MagicMock(), MagicMock(), MagicMock(), MagicMock())

    def test_partial_payment_outstanding_correct(self, service: PaymentService) -> None:
        tenant = _tenant()
        bill = _confirmed_bill(tenant.id, "20000")
        payment = _recorded_payment(tenant.id, "8000")
        store: list[PaymentAllocation] = []
        service._bill_repository.get.return_value = bill
        service._payment_repository.get.return_value = payment
        service._payment_allocation_repository.has_allocation_for.return_value = False
        service._payment_allocation_repository.get_valid_by_bill.side_effect = lambda _bill_id: store
        service._payment_allocation_repository.get_by_payment.return_value = []
        service._payment_allocation_repository.add.side_effect = lambda a: (store.append(a) or a)

        service.allocate_payment(payment.id, bill.id, Money(Decimal("8000")))

        balance = service.calculate_bill_balance(bill.id)
        assert balance.allocated.amount == Decimal("8000.00")
        assert balance.outstanding.amount == Decimal("12000.00")

    def test_allocate_more_than_bill_outstanding_rejected(self, service: PaymentService) -> None:
        tenant = _tenant()
        bill = _confirmed_bill(tenant.id, "20000")
        payment = _recorded_payment(tenant.id, "25000")
        service._bill_repository.get.return_value = bill
        service._payment_repository.get.return_value = payment
        service._payment_allocation_repository.has_allocation_for.return_value = False
        service._payment_allocation_repository.get_valid_by_bill.return_value = []
        service._payment_allocation_repository.get_by_payment.return_value = []

        with pytest.raises(ValidationError, match="exceeds the bill's outstanding"):
            service.allocate_payment(payment.id, bill.id, Money(Decimal("25000")))


class TestMultiplePayments:
    @pytest.fixture
    def service(self) -> PaymentService:
        return PaymentService(MagicMock(), MagicMock(), MagicMock(), MagicMock())

    def test_cumulative_allocation_across_payments(self, service: PaymentService) -> None:
        tenant = _tenant()
        bill = _confirmed_bill(tenant.id, "20000")
        p1 = _recorded_payment(tenant.id, "5000")
        p2 = _recorded_payment(tenant.id, "7000")
        p3 = _recorded_payment(tenant.id, "8000")
        store: list[PaymentAllocation] = []
        service._bill_repository.get.return_value = bill
        service._payment_allocation_repository.has_allocation_for.return_value = False
        service._payment_allocation_repository.get_valid_by_bill.side_effect = lambda _bill_id: store
        service._payment_allocation_repository.get_by_payment.side_effect = lambda _pid: [
            a for a in store if a.payment_id == _pid
        ]
        service._payment_allocation_repository.add.side_effect = lambda a: (store.append(a) or a)
        service._payment_repository.get.side_effect = [p1, p2, p3]

        service.allocate_payment(p1.id, bill.id, Money(Decimal("5000")))
        service.allocate_payment(p2.id, bill.id, Money(Decimal("7000")))
        service.allocate_payment(p3.id, bill.id, Money(Decimal("8000")))

        balance = service.calculate_bill_balance(bill.id)
        assert balance.allocated.amount == Decimal("20000.00")
        assert balance.outstanding.amount == Decimal("0.00")


class TestOverpayment:
    @pytest.fixture
    def service(self) -> PaymentService:
        return PaymentService(MagicMock(), MagicMock(), MagicMock(), MagicMock())

    def test_overpayment_excess_becomes_tenant_credit(self, service: PaymentService) -> None:
        tenant = _tenant()
        bill = _confirmed_bill(tenant.id, "20000")
        payment = _recorded_payment(tenant.id, "25000")
        store: list[PaymentAllocation] = []
        service._bill_repository.get.return_value = bill
        service._payment_repository.get.return_value = payment
        service._payment_repository.get_by_tenant.return_value = [payment]
        service._payment_allocation_repository.has_allocation_for.return_value = False
        service._payment_allocation_repository.get_valid_by_bill.side_effect = lambda _bill_id: store
        service._payment_allocation_repository.get_by_payment.side_effect = lambda _pid: [
            a for a in store if a.payment_id == _pid
        ]
        service._payment_allocation_repository.add.side_effect = lambda a: (store.append(a) or a)

        allocation = service.allocate_payment(payment.id, bill.id, Money(Decimal("20000")))

        assert allocation.allocated_amount.amount == Decimal("20000.00")
        balance = service.calculate_bill_balance(bill.id)
        assert balance.allocated.amount == Decimal("20000.00")
        assert balance.outstanding.amount == Decimal("0.00")

        # The extra 5,000 remains as unused payment amount -> tenant credit.
        credit = service.calculate_tenant_credit(tenant.id)
        assert credit.amount == Decimal("5000.00")

        # The payment record still reflects the full received amount.
        unused = service.calculate_payment_unused(payment.id)
        assert unused.amount == Decimal("5000.00")

    def test_credit_applied_to_future_bill(self, service: PaymentService) -> None:
        tenant = _tenant()
        bill1 = _confirmed_bill(tenant.id, "20000")
        bill2 = _confirmed_bill(tenant.id, "15000")
        payment = _recorded_payment(tenant.id, "25000")
        store: list[PaymentAllocation] = []
        service._bill_repository.get.side_effect = lambda _bid: bill1 if _bid == bill1.id else bill2
        service._payment_repository.get.return_value = payment
        service._payment_repository.get_by_tenant.return_value = [payment]
        service._payment_allocation_repository.has_allocation_for.return_value = False
        service._payment_allocation_repository.get_valid_by_bill.side_effect = lambda _bill_id: [
            a for a in store if a.bill_id == _bill_id
        ]
        service._payment_allocation_repository.get_by_payment.side_effect = lambda _pid: [
            a for a in store if a.payment_id == _pid
        ]
        service._payment_allocation_repository.add.side_effect = lambda a: (store.append(a) or a)

        service.allocate_payment(payment.id, bill1.id, Money(Decimal("20000")))
        allocations = service.apply_tenant_credit(tenant.id, bill2.id, Money(Decimal("5000")))

        assert len(allocations) == 1
        assert allocations[0].allocated_amount.amount == Decimal("5000.00")
        balance2 = service.calculate_bill_balance(bill2.id)
        assert balance2.allocated.amount == Decimal("5000.00")
        assert balance2.outstanding.amount == Decimal("10000.00")

        # Credit is fully consumed.
        credit = service.calculate_tenant_credit(tenant.id)
        assert credit.amount == Decimal("0.00")


class TestCredit:
    @pytest.fixture
    def service(self) -> PaymentService:
        return PaymentService(MagicMock(), MagicMock(), MagicMock(), MagicMock())

    def test_partial_credit_application_remaining_correct(self, service: PaymentService) -> None:
        tenant = _tenant()
        bill = _confirmed_bill(tenant.id, "15000")
        payment = _recorded_payment(tenant.id, "25000")
        store: list[PaymentAllocation] = []
        service._bill_repository.get.return_value = bill
        service._payment_repository.get_by_tenant.return_value = [payment]
        service._payment_allocation_repository.has_allocation_for.return_value = False
        service._payment_allocation_repository.get_valid_by_bill.side_effect = lambda _bill_id: store
        service._payment_allocation_repository.get_by_payment.side_effect = lambda _pid: [
            a for a in store if a.payment_id == _pid
        ]
        service._payment_allocation_repository.add.side_effect = lambda a: (store.append(a) or a)

        allocations = service.apply_tenant_credit(tenant.id, bill.id, Money(Decimal("5000")))

        assert len(allocations) == 1
        assert allocations[0].allocated_amount.amount == Decimal("5000.00")
        balance = service.calculate_bill_balance(bill.id)
        assert balance.outstanding.amount == Decimal("10000.00")
        # Remaining credit = 25,000 - 5,000 = 20,000
        credit = service.calculate_tenant_credit(tenant.id)
        assert credit.amount == Decimal("20000.00")

    def test_credit_insufficient_rejected(self, service: PaymentService) -> None:
        tenant = _tenant()
        bill = _confirmed_bill(tenant.id, "15000")
        payment = _recorded_payment(tenant.id, "3000")
        service._bill_repository.get.return_value = bill
        service._payment_repository.get_by_tenant.return_value = [payment]
        service._payment_allocation_repository.has_allocation_for.return_value = False
        service._payment_allocation_repository.get_valid_by_bill.return_value = []
        service._payment_allocation_repository.get_by_payment.return_value = []

        with pytest.raises(ValidationError, match="Insufficient tenant credit"):
            service.apply_tenant_credit(tenant.id, bill.id, Money(Decimal("5000")))

    def test_credit_history_traceable(self, service: PaymentService) -> None:
        tenant = _tenant()
        bill = _confirmed_bill(tenant.id, "15000")
        payment = _recorded_payment(tenant.id, "25000")
        store: list[PaymentAllocation] = []
        service._bill_repository.get.return_value = bill
        service._payment_repository.get_by_tenant.return_value = [payment]
        service._payment_allocation_repository.has_allocation_for.return_value = False
        service._payment_allocation_repository.get_valid_by_bill.side_effect = lambda _bill_id: store
        service._payment_allocation_repository.get_by_payment.side_effect = lambda _pid: [
            a for a in store if a.payment_id == _pid
        ]
        service._payment_allocation_repository.add.side_effect = lambda a: (store.append(a) or a)

        allocations = service.apply_tenant_credit(tenant.id, bill.id, Money(Decimal("5000")))

        # Every credit application links back to the original payment record.
        assert allocations[0].payment_id == payment.id
        assert allocations[0].bill_id == bill.id


class TestVoid:
    @pytest.fixture
    def service(self) -> PaymentService:
        return PaymentService(MagicMock(), MagicMock(), MagicMock(), MagicMock())

    def test_void_payment(self, service: PaymentService) -> None:
        payment = _recorded_payment(uuid.uuid4(), "8000")
        service._payment_repository.get.return_value = payment
        service._payment_repository.update.side_effect = lambda p: p

        result = service.void_payment(payment.id)

        assert result.status == PaymentStatus.VOID
        service._payment_repository.update.assert_called_once()

    def test_void_twice_rejected(self, service: PaymentService) -> None:
        payment = _void_payment(uuid.uuid4(), "8000")
        service._payment_repository.get.return_value = payment
        with pytest.raises(ValidationError, match="already void"):
            service.void_payment(payment.id)

    def test_void_payment_no_longer_affects_balance(self, service: PaymentService) -> None:
        tenant = _tenant()
        bill = _confirmed_bill(tenant.id, "20000")
        payment = _recorded_payment(tenant.id, "8000")
        service._payment_repository.get.return_value = payment
        service._bill_repository.get.return_value = bill
        service._payment_allocation_repository.has_allocation_for.return_value = False
        service._payment_allocation_repository.get_by_payment.return_value = []
        service._payment_allocation_repository.get_valid_by_bill.return_value = []
        service._payment_allocation_repository.add.side_effect = lambda a: a

        service.allocate_payment(payment.id, bill.id, Money(Decimal("8000")))
        payment.void()

        # After the payment is voided its allocation no longer counts.
        service._payment_allocation_repository.get_valid_by_bill.return_value = []
        balance = service.calculate_bill_balance(bill.id)
        assert balance.allocated.amount == Decimal("0.00")
        assert balance.outstanding.amount == Decimal("20000.00")

    def test_void_payment_historical_record_remains(self, service: PaymentService) -> None:
        payment = _recorded_payment(uuid.uuid4(), "8000")
        service._payment_repository.get.return_value = payment
        service._payment_repository.update.side_effect = lambda p: p

        result = service.void_payment(payment.id)

        # The payment is not deleted; it is only transitioned to VOID.
        assert result.id is not None
        assert result.status == PaymentStatus.VOID


class TestAllocation:
    @pytest.fixture
    def service(self) -> PaymentService:
        return PaymentService(MagicMock(), MagicMock(), MagicMock(), MagicMock())

    def test_duplicate_allocation_rejected(self, service: PaymentService) -> None:
        tenant = _tenant()
        bill = _confirmed_bill(tenant.id, "20000")
        payment = _recorded_payment(tenant.id, "8000")
        service._bill_repository.get.return_value = bill
        service._payment_repository.get.return_value = payment
        service._payment_allocation_repository.has_allocation_for.return_value = True

        with pytest.raises(ValidationError, match="already exists"):
            service.allocate_payment(payment.id, bill.id, Money(Decimal("8000")))

    def test_allocate_to_unconfirmed_bill_rejected(self, service: PaymentService) -> None:
        tenant = _tenant()
        bill = _confirmed_bill(tenant.id, "20000")
        bill.status = BillStatus.DRAFT
        payment = _recorded_payment(tenant.id, "8000")
        service._bill_repository.get.return_value = bill
        service._payment_repository.get.return_value = payment

        with pytest.raises(ValidationError, match="must be confirmed"):
            service.allocate_payment(payment.id, bill.id, Money(Decimal("8000")))

    def test_allocate_void_payment_rejected(self, service: PaymentService) -> None:
        tenant = _tenant()
        bill = _confirmed_bill(tenant.id, "20000")
        payment = _void_payment(tenant.id, "8000")
        service._bill_repository.get.return_value = bill
        service._payment_repository.get.return_value = payment

        with pytest.raises(ValidationError, match="void payment"):
            service.allocate_payment(payment.id, bill.id, Money(Decimal("8000")))

    def test_allocate_bill_not_found(self, service: PaymentService) -> None:
        tenant = _tenant()
        payment = _recorded_payment(tenant.id, "8000")
        service._bill_repository.get.return_value = None
        service._payment_repository.get.return_value = payment

        with pytest.raises(NotFoundError, match="Bill"):
            service.allocate_payment(payment.id, uuid.uuid4(), Money(Decimal("8000")))

    def test_allocate_exceeds_payment_rejected(self, service: PaymentService) -> None:
        tenant = _tenant()
        bill = _confirmed_bill(tenant.id, "20000")
        payment = _recorded_payment(tenant.id, "5000")
        service._bill_repository.get.return_value = bill
        service._payment_repository.get.return_value = payment
        service._payment_allocation_repository.has_allocation_for.return_value = False
        service._payment_allocation_repository.get_valid_by_bill.return_value = []
        service._payment_allocation_repository.get_by_payment.return_value = []

        with pytest.raises(ValidationError, match="exceeds the payment's remaining"):
            service.allocate_payment(payment.id, bill.id, Money(Decimal("8000")))


class TestMoney:
    @pytest.fixture
    def service(self) -> PaymentService:
        return PaymentService(MagicMock(), MagicMock(), MagicMock(), MagicMock())

    def test_decimal_arithmetic_two_decimals(self, service: PaymentService) -> None:
        tenant = _tenant()
        bill = _confirmed_bill(tenant.id, "20000")
        payment = _recorded_payment(tenant.id, "8000.006")
        assert payment.amount.amount == Decimal("8000.01")

        store: list[PaymentAllocation] = []
        service._bill_repository.get.return_value = bill
        service._payment_repository.get.return_value = payment
        service._payment_allocation_repository.has_allocation_for.return_value = False
        service._payment_allocation_repository.get_valid_by_bill.side_effect = lambda _bill_id: store
        service._payment_allocation_repository.get_by_payment.side_effect = lambda _pid: [
            a for a in store if a.payment_id == _pid
        ]
        service._payment_allocation_repository.add.side_effect = lambda a: (store.append(a) or a)

        service.allocate_payment(payment.id, bill.id, payment.amount)

        balance = service.calculate_bill_balance(bill.id)
        assert isinstance(balance.total.amount, Decimal)
        assert isinstance(balance.allocated.amount, Decimal)
        assert isinstance(balance.outstanding.amount, Decimal)
        assert balance.allocated.amount == Decimal("8000.01")
        assert balance.outstanding.amount == Decimal("11999.99")


class TestTransactionSafety:
    @pytest.fixture
    def service(self) -> PaymentService:
        return PaymentService(MagicMock(), MagicMock(), MagicMock(), MagicMock())

    def test_failed_allocation_persists_nothing(self, service: PaymentService) -> None:
        tenant = _tenant()
        bill = _confirmed_bill(tenant.id, "20000")
        payment = _recorded_payment(tenant.id, "5000")
        service._bill_repository.get.return_value = bill
        service._payment_repository.get.return_value = payment
        service._payment_allocation_repository.has_allocation_for.return_value = False
        service._payment_allocation_repository.get_valid_by_bill.return_value = []
        service._payment_allocation_repository.get_by_payment.return_value = []

        with pytest.raises(ValidationError, match="exceeds the payment's remaining"):
            service.allocate_payment(payment.id, bill.id, Money(Decimal("8000")))

        # Validation happens before any allocation is committed.
        service._payment_allocation_repository.add.assert_not_called()

    def test_failed_credit_application_persists_nothing(self, service: PaymentService) -> None:
        tenant = _tenant()
        bill = _confirmed_bill(tenant.id, "15000")
        p1 = _recorded_payment(tenant.id, "3000")
        p2 = _recorded_payment(tenant.id, "1000")
        service._bill_repository.get.return_value = bill
        service._payment_repository.get_by_tenant.return_value = [p1, p2]
        service._payment_allocation_repository.has_allocation_for.return_value = False
        service._payment_allocation_repository.get_valid_by_bill.return_value = []
        service._payment_allocation_repository.get_by_payment.side_effect = [[], []]

        with pytest.raises(ValidationError, match="Insufficient tenant credit"):
            service.apply_tenant_credit(tenant.id, bill.id, Money(Decimal("5000")))

        # Insufficient credit is detected before any allocation is committed.
        service._payment_allocation_repository.add.assert_not_called()
