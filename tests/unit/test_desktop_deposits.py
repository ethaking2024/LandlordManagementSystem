from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtWidgets import QDialog

from app.core.exceptions import NotFoundError, ValidationError
from app.desktop.deposit_forms import (
    DepositDetailDialog,
    RecordDepositDialog,
    SettlementDialog,
    format_deposit_status,
    format_money,
)
from app.desktop.deposit_page import DepositsPage
from app.desktop.services import OPERATION_FAILED
from app.domain.enums import AgreementStatus, DepositStatus


class FakeRunner:
    def __init__(self) -> None:
        self.deposit = MagicMock()
        self.agreement = MagicMock()
        self.tenant = MagicMock()
        self.rental_space = MagicMock()

    def run(self, operation, parent=None):
        services = MagicMock()
        services.deposit = MagicMock(return_value=self.deposit)
        services.agreement = MagicMock(return_value=self.agreement)
        services.tenant = MagicMock(return_value=self.tenant)
        services.rental_space = MagicMock(return_value=self.rental_space)
        try:
            return operation(services)
        except Exception:
            return OPERATION_FAILED


class _Amount:
    def __init__(self, value: str) -> None:
        self.amount = Decimal(value)

    def __str__(self) -> str:
        return str(self.amount)


def make_tenant(tenant_id: uuid.UUID | None = None, name: str = "Sita Shrestha"):
    tenant = MagicMock()
    tenant.id = tenant_id or uuid.uuid4()
    tenant.full_name = name
    return tenant


def make_space(space_id: uuid.UUID | None = None, name: str = "Room 101"):
    space = MagicMock()
    space.id = space_id or uuid.uuid4()
    space.name = name
    return space


def make_agreement(
    agreement_id: uuid.UUID | None = None,
    tenant_id: uuid.UUID | None = None,
    status: AgreementStatus = AgreementStatus.ACTIVE,
    end_date: date | None = date(2026, 12, 31),
):
    agreement = MagicMock()
    agreement.id = agreement_id or uuid.uuid4()
    agreement.tenant_id = tenant_id or uuid.uuid4()
    agreement.rental_space_id = uuid.uuid4()
    agreement.start_date = date(2026, 1, 1)
    agreement.end_date = end_date
    agreement.status = status
    return agreement


def make_deposit(
    deposit_id: uuid.UUID | None = None,
    status: DepositStatus = DepositStatus.HELD,
    amount: str = "50000",
    agreement_id: uuid.UUID | None = None,
):
    deposit = MagicMock()
    deposit.id = deposit_id or uuid.uuid4()
    deposit.agreement_id = agreement_id or uuid.uuid4()
    deposit.tenant_id = uuid.uuid4()
    deposit.received_date = date(2026, 1, 15)
    deposit.amount = _Amount(amount)
    deposit.status = status
    deposit.reference = None
    deposit.notes = None
    return deposit


def make_settlement(deductions: list[tuple[str, str]] | None = None, refund: str = "40000", total_deductions: str = "10000"):
    settlement = MagicMock()
    settlement.settlement_date = date(2026, 12, 31)
    settlement.deductions = []
    for reason, amount in deductions or []:
        deduction = MagicMock()
        deduction.reason = reason
        deduction.amount = _Amount(amount)
        settlement.deductions.append(deduction)
    settlement.refund_amount = _Amount(refund)
    settlement.total_deductions = _Amount(total_deductions)
    settlement.notes = None
    return settlement


# ------------------------------------------------------------------
# Formatting helpers
# ------------------------------------------------------------------


@pytest.mark.unit
def test_format_deposit_status() -> None:
    assert format_deposit_status(DepositStatus.HELD) == "Held"
    assert format_deposit_status(DepositStatus.SETTLED) == "Settled"
    assert format_deposit_status(DepositStatus.VOID) == "Void"


@pytest.mark.unit
def test_format_money() -> None:
    assert format_money(_Amount("50000")) == "NPR 50000"
    assert format_money(None) == ""


# ------------------------------------------------------------------
# Record deposit dialog
# ------------------------------------------------------------------


@pytest.mark.unit
def test_record_deposit_dialog_saves(qapp) -> None:
    runner = FakeRunner()
    agreement = make_agreement()
    tenant = make_tenant()
    space = make_space()
    deposit = make_deposit(agreement_id=agreement.id)
    runner.agreement.get_all_agreements.return_value = [agreement]
    runner.tenant.get_tenant.return_value = tenant
    runner.rental_space.get_rental_space.return_value = space
    runner.deposit.record_deposit.return_value = deposit

    dialog = RecordDepositDialog(runner)
    dialog._agreement_combo.setCurrentIndex(0)
    dialog._amount_edit.setText("50000")
    dialog._received_date_input.set_date(date(2026, 1, 15))
    dialog._on_save()

    assert dialog.saved is True
    assert dialog.result_deposit() is deposit
    call = runner.deposit.record_deposit.call_args
    assert call.args[0] == agreement.id
    assert call.args[1].amount == Decimal("50000")
    assert call.args[2] == date(2026, 1, 15)


@pytest.mark.unit
def test_record_deposit_dialog_requires_amount(qapp) -> None:
    runner = FakeRunner()
    agreement = make_agreement()
    tenant = make_tenant()
    space = make_space()
    runner.agreement.get_all_agreements.return_value = [agreement]
    runner.tenant.get_tenant.return_value = tenant
    runner.rental_space.get_rental_space.return_value = space

    dialog = RecordDepositDialog(runner)
    dialog._agreement_combo.setCurrentIndex(0)
    dialog._received_date_input.set_date(date(2026, 1, 15))
    dialog._on_save()

    assert dialog.saved is False
    runner.deposit.record_deposit.assert_not_called()


@pytest.mark.unit
def test_record_deposit_dialog_invalid_amount(qapp) -> None:
    runner = FakeRunner()
    agreement = make_agreement()
    tenant = make_tenant()
    space = make_space()
    runner.agreement.get_all_agreements.return_value = [agreement]
    runner.tenant.get_tenant.return_value = tenant
    runner.rental_space.get_rental_space.return_value = space

    dialog = RecordDepositDialog(runner)
    dialog._agreement_combo.setCurrentIndex(0)
    dialog._amount_edit.setText("abc")
    dialog._received_date_input.set_date(date(2026, 1, 15))
    dialog._on_save()

    assert dialog.saved is False
    runner.deposit.record_deposit.assert_not_called()


@pytest.mark.unit
def test_record_deposit_dialog_service_error_keeps_open(qapp) -> None:
    runner = FakeRunner()
    agreement = make_agreement()
    tenant = make_tenant()
    space = make_space()
    runner.agreement.get_all_agreements.return_value = [agreement]
    runner.tenant.get_tenant.return_value = tenant
    runner.rental_space.get_rental_space.return_value = space
    runner.deposit.record_deposit.side_effect = ValidationError("agreement not active")

    dialog = RecordDepositDialog(runner)
    dialog._agreement_combo.setCurrentIndex(0)
    dialog._amount_edit.setText("50000")
    dialog._received_date_input.set_date(date(2026, 1, 15))
    dialog._on_save()

    assert dialog.saved is False


# ------------------------------------------------------------------
# Settlement dialog
# ------------------------------------------------------------------


@pytest.mark.unit
def test_settlement_dialog_settles_with_deductions(qapp) -> None:
    runner = FakeRunner()
    deposit = make_deposit(amount="50000")
    settlement = make_settlement([("Cleaning", "10000")], refund="40000")
    runner.deposit.get_deposit.return_value = deposit
    runner.deposit.create_settlement.return_value = settlement
    runner.deposit.complete_settlement.return_value = settlement

    dialog = SettlementDialog(runner, deposit.id)
    assert len(dialog._deduction_rows) == 1
    row = dialog._deduction_rows[0]
    row._reason_edit.setText("Cleaning")
    row._amount_edit.setText("10000")
    dialog._update_expected()
    dialog._settlement_date_input.set_date(date(2026, 12, 31))
    dialog._on_settle()

    assert dialog.settled is True
    create_call = runner.deposit.create_settlement.call_args
    assert create_call.args[0] == deposit.id
    assert create_call.args[1] == date(2026, 12, 31)
    assert create_call.args[2] == [(Decimal("10000"), "Cleaning")]
    complete_call = runner.deposit.complete_settlement.call_args
    assert complete_call.args[1].amount == Decimal("40000")


@pytest.mark.unit
def test_settlement_dialog_refund_matches_deposit_minus_deductions(qapp) -> None:
    runner = FakeRunner()
    deposit = make_deposit(amount="50000")
    settlement = make_settlement([("Damages", "15000")], refund="35000", total_deductions="15000")
    runner.deposit.get_deposit.return_value = deposit
    runner.deposit.create_settlement.return_value = settlement
    runner.deposit.complete_settlement.return_value = settlement

    dialog = SettlementDialog(runner, deposit.id)
    row = dialog._deduction_rows[0]
    row._reason_edit.setText("Damages")
    row._amount_edit.setText("15000")
    dialog._update_expected()
    dialog._settlement_date_input.set_date(date(2026, 12, 31))
    dialog._on_settle()

    complete_call = runner.deposit.complete_settlement.call_args
    assert complete_call.args[1].amount == Decimal("35000")


@pytest.mark.unit
def test_settlement_dialog_service_rejects_rule_violation(qapp) -> None:
    runner = FakeRunner()
    deposit = make_deposit(amount="50000")
    runner.deposit.get_deposit.return_value = deposit
    runner.deposit.create_settlement.side_effect = ValidationError(
        "refund plus deductions must equal the deposit"
    )

    dialog = SettlementDialog(runner, deposit.id)
    row = dialog._deduction_rows[0]
    row._reason_edit.setText("Cleaning")
    row._amount_edit.setText("10000")
    dialog._settlement_date_input.set_date(date(2026, 12, 31))
    dialog._on_settle()

    assert dialog.settled is False


@pytest.mark.unit
def test_settlement_dialog_requires_settlement_date(qapp) -> None:
    runner = FakeRunner()
    deposit = make_deposit()
    runner.deposit.get_deposit.return_value = deposit

    dialog = SettlementDialog(runner, deposit.id)
    dialog._on_settle()

    assert dialog.settled is False
    runner.deposit.create_settlement.assert_not_called()


@pytest.mark.unit
def test_settlement_dialog_expected_summary(qapp) -> None:
    runner = FakeRunner()
    deposit = make_deposit(amount="50000")
    runner.deposit.get_deposit.return_value = deposit

    dialog = SettlementDialog(runner, deposit.id)
    row = dialog._deduction_rows[0]
    row._reason_edit.setText("Cleaning")
    row._amount_edit.setText("10000")
    dialog._update_expected()

    text = dialog._expected_label.text()
    assert "Deposit: NPR 50000" in text
    assert "Total deductions: NPR 10000" in text
    assert "Expected refund: NPR 40000" in text


# ------------------------------------------------------------------
# Deposit detail dialog
# ------------------------------------------------------------------


@pytest.mark.unit
def test_deposit_detail_dialog_renders(qapp) -> None:
    runner = FakeRunner()
    deposit = make_deposit()
    agreement = make_agreement()
    tenant = make_tenant()
    space = make_space()
    settlement = make_settlement([("Cleaning", "10000")], refund="40000")
    runner.deposit.get_deposit.return_value = deposit
    runner.agreement.get_agreement.return_value = agreement
    runner.tenant.get_tenant.return_value = tenant
    runner.rental_space.get_rental_space.return_value = space
    runner.deposit.get_settlement_by_deposit.return_value = settlement

    dialog = DepositDetailDialog(runner, deposit.id)

    text = dialog._details_label.text()
    assert "Sita Shrestha" in text
    assert "Room 101" in text
    assert "Held" in text
    assert "Deduction — Cleaning: NPR 10000" in text
    assert "Refund: NPR 40000" in text
    assert dialog._settle_button.isEnabled() is True
    assert dialog._void_button.isEnabled() is True


@pytest.mark.unit
def test_deposit_detail_dialog_void_disabled_for_settled(qapp) -> None:
    runner = FakeRunner()
    deposit = make_deposit(status=DepositStatus.SETTLED)
    agreement = make_agreement()
    tenant = make_tenant()
    space = make_space()
    settlement = make_settlement()
    runner.deposit.get_deposit.return_value = deposit
    runner.agreement.get_agreement.return_value = agreement
    runner.tenant.get_tenant.return_value = tenant
    runner.rental_space.get_rental_space.return_value = space
    runner.deposit.get_settlement_by_deposit.return_value = settlement

    dialog = DepositDetailDialog(runner, deposit.id)

    assert dialog._settle_button.isEnabled() is False
    assert dialog._void_button.isEnabled() is False


@pytest.mark.unit
def test_deposit_detail_dialog_load_error(qapp) -> None:
    runner = FakeRunner()
    runner.deposit.get_deposit.side_effect = NotFoundError("deposit not found")

    dialog = DepositDetailDialog(runner, uuid.uuid4())

    assert "Could not load deposit details" in dialog._details_label.text()


@pytest.mark.unit
def test_deposit_detail_dialog_settle_opens_dialog(qapp) -> None:
    import app.desktop.deposit_forms as df

    runner = FakeRunner()
    deposit = make_deposit()
    agreement = make_agreement()
    tenant = make_tenant()
    space = make_space()
    runner.deposit.get_deposit.return_value = deposit
    runner.agreement.get_agreement.return_value = agreement
    runner.tenant.get_tenant.return_value = tenant
    runner.rental_space.get_rental_space.return_value = space
    runner.deposit.get_settlement_by_deposit.return_value = None

    dialog = DepositDetailDialog(runner, deposit.id)

    fake_settle = MagicMock()
    fake_settle.exec.return_value = QDialog.DialogCode.Accepted
    with patch.object(df, "SettlementDialog", return_value=fake_settle):
        dialog._on_settle()

    fake_settle.exec.assert_called_once()


# ------------------------------------------------------------------
# Deposits page
# ------------------------------------------------------------------


@pytest.fixture
def page(qapp) -> tuple[DepositsPage, FakeRunner]:
    runner = FakeRunner()
    deposits_page = DepositsPage(runner)
    deposits_page.show()
    return deposits_page, runner


@pytest.mark.unit
def test_deposits_page_refresh_populates_table(page) -> None:
    deposits_page, runner = page
    deposit = make_deposit()
    agreement = make_agreement()
    runner.deposit.get_all_deposits.return_value = [deposit]
    runner.tenant.get_tenant.return_value = make_tenant()
    runner.agreement.get_agreement.return_value = agreement
    runner.rental_space.get_rental_space.return_value = make_space()

    deposits_page.refresh()

    assert deposits_page._deposit_model.rowCount() == 1
    assert "Sita Shrestha" in deposits_page._deposit_model.data(deposits_page._deposit_model.index(0, 0))
    assert "Room 101" in deposits_page._deposit_model.data(deposits_page._deposit_model.index(0, 1))
    assert "NPR 50000" in deposits_page._deposit_model.data(deposits_page._deposit_model.index(0, 2))
    assert "Held" in deposits_page._deposit_model.data(deposits_page._deposit_model.index(0, 3))


@pytest.mark.unit
def test_deposits_page_empty_state(page) -> None:
    deposits_page, runner = page
    runner.deposit.get_all_deposits.return_value = []

    deposits_page.refresh()

    assert deposits_page._deposit_model.rowCount() == 0
    assert deposits_page._list_empty.isVisible()


@pytest.mark.unit
def test_deposits_page_view_deposit(page) -> None:
    import app.desktop.deposit_page as dp

    deposits_page, runner = page
    deposit = make_deposit()
    agreement = make_agreement()
    runner.deposit.get_all_deposits.return_value = [deposit]
    runner.tenant.get_tenant.return_value = make_tenant()
    runner.agreement.get_agreement.return_value = agreement
    runner.rental_space.get_rental_space.return_value = make_space()

    deposits_page.refresh()
    deposits_page._deposit_table.selectRow(0)

    fake_detail = MagicMock()
    fake_detail.exec.return_value = QDialog.DialogCode.Accepted
    with patch.object(dp, "DepositDetailDialog", return_value=fake_detail):
        deposits_page._on_view_deposit()

    fake_detail.exec.assert_called_once()


@pytest.mark.unit
def test_deposits_page_record_workflow(page) -> None:
    import app.desktop.deposit_page as dp

    deposits_page, runner = page
    runner.deposit.get_all_deposits.return_value = []

    deposits_page.refresh()

    fake_record = MagicMock()
    fake_record.exec.return_value = QDialog.DialogCode.Accepted
    with patch.object(dp, "RecordDepositDialog", return_value=fake_record):
        deposits_page._on_record()

    fake_record.exec.assert_called_once()


@pytest.mark.unit
def test_deposits_page_settle_workflow(page) -> None:
    import app.desktop.deposit_page as dp

    deposits_page, runner = page
    deposit = make_deposit()
    agreement = make_agreement()
    runner.deposit.get_all_deposits.return_value = [deposit]
    runner.tenant.get_tenant.return_value = make_tenant()
    runner.agreement.get_agreement.return_value = agreement
    runner.rental_space.get_rental_space.return_value = make_space()

    deposits_page.refresh()
    deposits_page._deposit_table.selectRow(0)

    fake_detail = MagicMock()
    fake_detail.exec.return_value = QDialog.DialogCode.Accepted
    with patch.object(dp, "DepositDetailDialog", return_value=fake_detail):
        deposits_page._on_settle_deposit()

    fake_detail.exec.assert_called_once()
    deposits_page.refresh()


@pytest.mark.unit
def test_deposits_page_service_error(page) -> None:
    deposits_page, runner = page
    runner.deposit.get_all_deposits.side_effect = ValidationError("db unavailable")

    deposits_page.refresh()

    assert deposits_page._deposit_model.rowCount() == 0


# ------------------------------------------------------------------
# Integration: agreement -> deposit -> settlement
# ------------------------------------------------------------------


@pytest.mark.unit
def test_agreement_to_deposit_to_settlement_workflow(qapp) -> None:
    """A deposit on an agreement is held, then settled with deductions on end."""
    runner = FakeRunner()
    agreement = make_agreement(status=AgreementStatus.ENDED)
    tenant = make_tenant()
    space = make_space()
    deposit = make_deposit(amount="50000", agreement_id=agreement.id)
    settlement = make_settlement([("Cleaning", "10000")], refund="40000")
    runner.agreement.get_all_agreements.return_value = [agreement]
    runner.tenant.get_tenant.return_value = tenant
    runner.rental_space.get_rental_space.return_value = space
    runner.deposit.record_deposit.return_value = deposit
    runner.deposit.get_deposit.return_value = deposit
    runner.deposit.create_settlement.return_value = settlement
    runner.deposit.complete_settlement.return_value = settlement

    record = RecordDepositDialog(runner)
    record._agreement_combo.setCurrentIndex(0)
    record._amount_edit.setText("50000")
    record._received_date_input.set_date(date(2026, 1, 15))
    record._on_save()
    assert record.saved is True

    settle = SettlementDialog(runner, deposit.id)
    row = settle._deduction_rows[0]
    row._reason_edit.setText("Cleaning")
    row._amount_edit.setText("10000")
    settle._settlement_date_input.set_date(date(2026, 12, 31))
    settle._on_settle()
    assert settle.settled is True


@pytest.mark.unit
def test_settlement_rejected_for_active_agreement_by_service(qapp) -> None:
    """The service rejects settlement while the agreement is still active."""
    runner = FakeRunner()
    deposit = make_deposit(amount="50000")
    runner.deposit.get_deposit.return_value = deposit
    runner.deposit.create_settlement.side_effect = ValidationError(
        "deposit can only be settled when the agreement is ended"
    )

    dialog = SettlementDialog(runner, deposit.id)
    row = dialog._deduction_rows[0]
    row._reason_edit.setText("Cleaning")
    row._amount_edit.setText("10000")
    dialog._settlement_date_input.set_date(date(2026, 12, 31))
    dialog._on_settle()

    assert dialog.settled is False


@pytest.mark.unit
def test_full_refund_settlement(qapp) -> None:
    runner = FakeRunner()
    deposit = make_deposit(amount="50000")
    settlement = make_settlement([], refund="50000", total_deductions="0")
    runner.deposit.get_deposit.return_value = deposit
    runner.deposit.create_settlement.return_value = settlement
    runner.deposit.complete_settlement.return_value = settlement

    dialog = SettlementDialog(runner, deposit.id)
    dialog._settlement_date_input.set_date(date(2026, 12, 31))
    dialog._on_settle()

    assert dialog.settled is True
    complete_call = runner.deposit.complete_settlement.call_args
    assert complete_call.args[1].amount == Decimal("50000")
