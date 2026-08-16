from __future__ import annotations

import uuid
from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtWidgets import QDialog

from app.core.exceptions import ConflictError
from app.desktop.agreement_forms import (
    AgreementDetailDialog,
    AgreementFormDialog,
    EndAgreementDialog,
    confirm_cancel_agreement,
    format_agreement_status,
)
from app.desktop.agreement_page import AgreementsPage
from app.desktop.services import OPERATION_FAILED
from app.domain.enums import AgreementStatus


class FakeRunner:
    def __init__(self) -> None:
        self.tenant = MagicMock()
        self.agreement = MagicMock()
        self.rental_space = MagicMock()

    def run(self, operation, parent=None):
        services = MagicMock()
        services.tenant = MagicMock(return_value=self.tenant)
        services.agreement = MagicMock(return_value=self.agreement)
        services.rental_space = MagicMock(return_value=self.rental_space)
        try:
            return operation(services)
        except Exception:
            return OPERATION_FAILED


def make_tenant(tenant_id: uuid.UUID | None = None, name: str = "Sita Shrestha"):
    tenant = MagicMock()
    tenant.id = tenant_id or uuid.uuid4()
    tenant.full_name = name
    tenant.phone = "9812345678"
    return tenant


def make_space(space_id: uuid.UUID | None = None, name: str = "Flat A"):
    space = MagicMock()
    space.id = space_id or uuid.uuid4()
    space.name = name
    return space


def make_agreement(
    agreement_id: uuid.UUID | None = None,
    status: AgreementStatus = AgreementStatus.ACTIVE,
):
    agreement = MagicMock()
    agreement.id = agreement_id or uuid.uuid4()
    agreement.tenant_id = uuid.uuid4()
    agreement.rental_space_id = uuid.uuid4()
    agreement.status = status
    agreement.start_date = date(2026, 8, 10)
    agreement.end_date = None
    agreement.monthly_rent = "15000"
    agreement.security_deposit = None
    agreement.notes = None
    return agreement


# ------------------------------------------------------------------
# Agreement form
# ------------------------------------------------------------------


@pytest.mark.unit
def test_agreement_form_creates_agreement(qapp) -> None:
    runner = FakeRunner()
    tenant = make_tenant()
    space = make_space()
    runner.tenant.get_all_tenants.return_value = [tenant]
    created = make_agreement()
    runner.agreement.create_agreement.return_value = created

    dialog = AgreementFormDialog(runner, rental_space_id=space.id, rental_space_label=space.name)
    dialog._tenant_combo.setCurrentIndex(0)
    dialog._start_input.set_date(date(2026, 8, 10))
    dialog._rent_edit.setText("15000")
    dialog._on_save()

    assert dialog.result() == QDialog.DialogCode.Accepted
    assert dialog.result_agreement() is created
    runner.agreement.create_agreement.assert_called_once()


@pytest.mark.unit
def test_agreement_form_validation_blocks_missing_rent(qapp) -> None:
    runner = FakeRunner()
    tenant = make_tenant()
    runner.tenant.get_all_tenants.return_value = [tenant]

    dialog = AgreementFormDialog(runner, rental_space_id=uuid.uuid4())
    dialog._tenant_combo.setCurrentIndex(0)
    dialog._start_input.set_date(date(2026, 8, 10))
    dialog._on_save()

    assert dialog.result() != QDialog.DialogCode.Accepted
    runner.agreement.create_agreement.assert_not_called()


@pytest.mark.unit
def test_agreement_form_service_conflict_keeps_open(qapp) -> None:
    runner = FakeRunner()
    tenant = make_tenant()
    runner.tenant.get_all_tenants.return_value = [tenant]
    runner.agreement.create_agreement.side_effect = ConflictError("overlapping agreement")

    dialog = AgreementFormDialog(runner, rental_space_id=uuid.uuid4())
    dialog._tenant_combo.setCurrentIndex(0)
    dialog._start_input.set_date(date(2026, 8, 10))
    dialog._rent_edit.setText("15000")
    dialog._on_save()

    assert dialog.result() != QDialog.DialogCode.Accepted


@pytest.mark.unit
def test_agreement_form_add_tenant_inline(qapp) -> None:
    import app.desktop.agreement_forms as af

    runner = FakeRunner()
    existing = make_tenant()
    runner.tenant.get_all_tenants.return_value = [existing]
    new_tenant = make_tenant(name="New Tenant")
    runner.tenant.create_tenant.return_value = new_tenant

    dialog = AgreementFormDialog(runner, rental_space_id=uuid.uuid4())

    fake_tenant_dialog = MagicMock()
    fake_tenant_dialog.exec.return_value = QDialog.DialogCode.Accepted
    fake_tenant_dialog.result_tenant.return_value = new_tenant
    with patch.object(af, "TenantFormDialog", return_value=fake_tenant_dialog):
        dialog._on_add_tenant()

    assert dialog._tenant_combo.count() == 2
    assert dialog._tenant_combo.currentData() == new_tenant.id


# ------------------------------------------------------------------
# End / cancel helpers
# ------------------------------------------------------------------


@pytest.mark.unit
def test_end_agreement_dialog_calls_service(qapp) -> None:
    runner = FakeRunner()
    agreement = make_agreement()
    runner.agreement.end_agreement.return_value = agreement

    dialog = EndAgreementDialog(runner, agreement_data={"id": agreement.id, "start_date": date(2026, 8, 10)})
    dialog._end_input.set_date(date(2027, 8, 10))
    dialog._on_end()

    assert dialog.result() == QDialog.DialogCode.Accepted
    runner.agreement.end_agreement.assert_called_once()


@pytest.mark.unit
def test_end_agreement_dialog_requires_date(qapp) -> None:
    runner = FakeRunner()
    agreement = make_agreement()

    dialog = EndAgreementDialog(runner, agreement_data={"id": agreement.id, "start_date": date(2026, 8, 10)})
    dialog._on_end()

    assert dialog.result() != QDialog.DialogCode.Accepted
    runner.agreement.end_agreement.assert_not_called()


@pytest.mark.unit
def test_confirm_cancel_agreement(qapp) -> None:
    import app.desktop.agreement_forms as af

    runner = FakeRunner()
    agreement = make_agreement()
    runner.agreement.cancel_agreement.return_value = agreement

    fake_confirm = MagicMock()
    fake_confirm.exec.return_value = QDialog.DialogCode.Accepted
    fake_confirm.confirmed = True
    with patch.object(af, "ConfirmationDialog", return_value=fake_confirm):
        result = confirm_cancel_agreement(runner, agreement.id, "Flat A")

    assert result is agreement
    runner.agreement.cancel_agreement.assert_called_once_with(agreement.id)


@pytest.mark.unit
def test_format_agreement_status() -> None:
    assert format_agreement_status(AgreementStatus.ACTIVE) == "Active"
    assert format_agreement_status(AgreementStatus.ENDED) == "Ended"
    assert format_agreement_status(AgreementStatus.CANCELLED) == "Cancelled"


# ------------------------------------------------------------------
# Agreement detail dialog
# ------------------------------------------------------------------


@pytest.mark.unit
def test_agreement_detail_dialog_renders_and_disables_inactive(qapp) -> None:
    runner = FakeRunner()
    tenant = make_tenant()
    space = make_space()
    agreement = make_agreement(status=AgreementStatus.ENDED)
    runner.agreement.get_agreement.return_value = agreement
    runner.tenant.get_tenant.return_value = tenant
    runner.rental_space.get_rental_space.return_value = space

    dialog = AgreementDetailDialog(runner, agreement.id)

    assert "Ended" in dialog._details_label.text()
    assert dialog._end_button.isEnabled() is False
    assert dialog._cancel_button.isEnabled() is False


# ------------------------------------------------------------------
# Agreements page
# ------------------------------------------------------------------


@pytest.fixture
def page(qapp) -> tuple[AgreementsPage, FakeRunner]:
    runner = FakeRunner()
    agreements_page = AgreementsPage(runner)
    agreements_page.show()
    return agreements_page, runner


@pytest.mark.unit
def test_agreement_page_refresh_populates_table(page) -> None:
    agreements_page, runner = page
    tenant = make_tenant()
    space = make_space()
    agreement = make_agreement()
    runner.agreement.get_all_agreements.return_value = [agreement]
    runner.tenant.get_tenant.return_value = tenant
    runner.rental_space.get_rental_space.return_value = space

    agreements_page.refresh()

    assert agreements_page._agreement_model.rowCount() == 1
    assert (
        agreements_page._agreement_model.data(agreements_page._agreement_model.index(0, 0))
        == "Sita Shrestha"
    )
    assert agreements_page._agreement_table.isVisible()


@pytest.mark.unit
def test_agreement_page_empty_state(page) -> None:
    agreements_page, runner = page
    runner.agreement.get_all_agreements.return_value = []

    agreements_page.refresh()

    assert agreements_page._agreement_model.rowCount() == 0
    assert agreements_page._list_empty.isVisible()


@pytest.mark.unit
def test_agreement_page_view_shows_detail(page) -> None:
    agreements_page, runner = page
    tenant = make_tenant()
    space = make_space()
    agreement = make_agreement()
    runner.agreement.get_all_agreements.return_value = [agreement]
    runner.agreement.get_agreement.return_value = agreement
    runner.tenant.get_tenant.return_value = tenant
    runner.rental_space.get_rental_space.return_value = space

    agreements_page.refresh()
    agreements_page._agreement_table.selectRow(0)
    agreements_page._on_view_agreement()

    assert agreements_page._stack.currentWidget() is agreements_page._detail_page
    assert "Active" in agreements_page._agreement_summary.text()


@pytest.mark.unit
def test_agreement_page_end_workflow(page) -> None:
    import app.desktop.agreement_page as ap

    agreements_page, runner = page
    tenant = make_tenant()
    space = make_space()
    agreement = make_agreement()
    ended = make_agreement(agreement_id=agreement.id, status=AgreementStatus.ENDED)
    runner.agreement.get_all_agreements.return_value = [agreement]
    runner.agreement.get_agreement.return_value = ended
    runner.agreement.end_agreement.return_value = ended
    runner.tenant.get_tenant.return_value = tenant
    runner.rental_space.get_rental_space.return_value = space

    agreements_page.refresh()
    agreements_page._agreement_table.selectRow(0)

    class FakeEndDialog:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def exec(self) -> int:
            runner.agreement.end_agreement(agreement.id, date(2027, 8, 10))
            return QDialog.DialogCode.Accepted

    with patch.object(ap, "EndAgreementDialog", FakeEndDialog):
        agreements_page._on_end_agreement()

    runner.agreement.end_agreement.assert_called_once_with(agreement.id, date(2027, 8, 10))


@pytest.mark.unit
def test_agreement_page_cancel_workflow(page) -> None:
    import app.desktop.agreement_page as ap

    agreements_page, runner = page
    tenant = make_tenant()
    space = make_space()
    agreement = make_agreement()
    runner.agreement.get_all_agreements.return_value = [agreement]
    runner.tenant.get_tenant.return_value = tenant
    runner.rental_space.get_rental_space.return_value = space

    agreements_page.refresh()
    agreements_page._agreement_table.selectRow(0)

    fake_confirm = MagicMock()
    fake_confirm.exec.return_value = QDialog.DialogCode.Accepted
    fake_confirm.confirmed = True
    with patch.object(ap, "confirm_cancel_agreement", return_value=agreement):
        agreements_page._on_cancel_agreement()

    assert agreements_page._agreement_model.rowCount() == 1
