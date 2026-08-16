from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import QDialog

from app.desktop.services import OPERATION_FAILED
from app.desktop.tenant_forms import TenantFormDialog
from app.desktop.tenant_page import TenantsPage


class FakeRunner:
    """ServiceRunner stand-in dispatching to fake services.

    Mirrors ServiceRunner: exceptions are translated and OPERATION_FAILED is
    returned so the UI keeps dialogs open.
    """

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
    tenant.alternate_phone = None
    tenant.email = "sita@example.com"
    tenant.address = "Thamel, Kathmandu"
    tenant.notes = None
    return tenant


def make_space(space_id: uuid.UUID | None = None, name: str = "Flat A"):
    space = MagicMock()
    space.id = space_id or uuid.uuid4()
    space.name = name
    return space


def make_agreement(
    agreement_id: uuid.UUID | None = None,
    tenant_id: uuid.UUID | None = None,
    space_id: uuid.UUID | None = None,
    status: str = "active",
):
    agreement = MagicMock()
    agreement.id = agreement_id or uuid.uuid4()
    agreement.tenant_id = tenant_id or uuid.uuid4()
    agreement.rental_space_id = space_id or uuid.uuid4()
    agreement.status = MagicMock()
    agreement.status.value = status
    agreement.start_date = MagicMock()
    agreement.start_date.isoformat.return_value = "2026-08-10"
    agreement.monthly_rent = "15000"
    return agreement


# ------------------------------------------------------------------
# Tenant form
# ------------------------------------------------------------------


@pytest.mark.unit
def test_tenant_form_creates_tenant(qapp) -> None:
    runner = FakeRunner()
    created = make_tenant()
    runner.tenant.create_tenant.return_value = created

    dialog = TenantFormDialog(runner)
    dialog._name_edit.setText("Ram Shrestha")
    dialog._phone_edit.setText("9812345678")
    dialog._on_save()

    assert dialog.result() == QDialog.DialogCode.Accepted
    assert dialog.result_tenant() is created
    runner.tenant.create_tenant.assert_called_once()


@pytest.mark.unit
def test_tenant_form_validation_blocks_empty(qapp) -> None:
    runner = FakeRunner()
    dialog = TenantFormDialog(runner)
    dialog._on_save()

    assert dialog.result() != QDialog.DialogCode.Accepted
    runner.tenant.create_tenant.assert_not_called()


@pytest.mark.unit
def test_tenant_form_edit_calls_update(qapp) -> None:
    runner = FakeRunner()
    tenant = make_tenant()
    runner.tenant.update_tenant.return_value = tenant

    dialog = TenantFormDialog(
        runner,
        tenant_data={
            "id": tenant.id,
            "full_name": tenant.full_name,
            "phone": "9812345678",
            "alternate_phone": None,
            "email": tenant.email,
            "address": tenant.address,
            "notes": None,
        },
    )
    dialog._name_edit.setText("Renamed Tenant")
    dialog._on_save()

    assert dialog.result() == QDialog.DialogCode.Accepted
    runner.tenant.update_tenant.assert_called_once()


@pytest.mark.unit
def test_tenant_form_service_error_keeps_open(qapp) -> None:
    from app.core.exceptions import ValidationError

    runner = FakeRunner()
    runner.tenant.create_tenant.side_effect = ValidationError("phone invalid")

    dialog = TenantFormDialog(runner)
    dialog._name_edit.setText("Ram Shrestha")
    dialog._phone_edit.setText("9812345678")
    dialog._on_save()

    assert dialog.result() != QDialog.DialogCode.Accepted


# ------------------------------------------------------------------
# Tenant page
# ------------------------------------------------------------------


@pytest.fixture
def page(qapp) -> tuple[TenantsPage, FakeRunner]:
    runner = FakeRunner()
    tenant_page = TenantsPage(runner)
    tenant_page.show()
    return tenant_page, runner


@pytest.mark.unit
def test_tenant_page_refresh_populates_table(page) -> None:
    tenant_page, runner = page
    runner.tenant.get_all_tenants.return_value = [make_tenant()]

    tenant_page.refresh()

    assert tenant_page._tenant_model.rowCount() == 1
    assert (
        tenant_page._tenant_model.data(tenant_page._tenant_model.index(0, 0))
        == "Sita Shrestha"
    )
    assert tenant_page._tenant_table.isVisible()


@pytest.mark.unit
def test_tenant_page_refresh_empty_shows_empty_state(page) -> None:
    tenant_page, runner = page
    runner.tenant.get_all_tenants.return_value = []

    tenant_page.refresh()

    assert tenant_page._tenant_model.rowCount() == 0
    assert tenant_page._list_empty.isVisible()


@pytest.mark.unit
def test_tenant_page_search_by_name(page) -> None:
    tenant_page, runner = page
    runner.tenant.search_tenants_by_name.return_value = [make_tenant(name="Ram")]
    runner.tenant.get_tenant_by_phone.return_value = None

    tenant_page._search_edit.setText("Ram")
    tenant_page.refresh()

    runner.tenant.search_tenants_by_name.assert_called_with("Ram")
    assert tenant_page._tenant_model.rowCount() == 1


@pytest.mark.unit
def test_tenant_page_search_by_phone(page) -> None:
    tenant_page, runner = page
    runner.tenant.search_tenants_by_name.return_value = []
    phone_match = make_tenant(name="Phone Owner")
    runner.tenant.get_tenant_by_phone.return_value = phone_match

    tenant_page._search_edit.setText("9812345678")
    tenant_page.refresh()

    runner.tenant.get_tenant_by_phone.assert_called_with("9812345678")
    assert tenant_page._tenant_model.rowCount() == 1


@pytest.mark.unit
def test_tenant_page_open_shows_detail_with_agreements(page) -> None:
    tenant_page, runner = page
    tenant = make_tenant()
    space = make_space()
    agreement = make_agreement(tenant_id=tenant.id, space_id=space.id)
    runner.tenant.get_all_tenants.return_value = [tenant]
    runner.tenant.get_tenant.return_value = tenant
    runner.agreement.get_agreements_by_tenant.return_value = [agreement]
    runner.rental_space.get_rental_space.return_value = space

    tenant_page.refresh()
    tenant_page._tenant_table.selectRow(0)
    tenant_page._on_open_tenant()

    assert tenant_page._stack.currentWidget() is tenant_page._detail_page
    assert tenant_page._agreement_model.rowCount() == 1


@pytest.mark.unit
def test_tenant_page_add_opens_form(page) -> None:
    from unittest.mock import patch

    import app.desktop.tenant_page as tp

    tenant_page, runner = page
    runner.tenant.get_all_tenants.return_value = []

    fake_dialog = MagicMock()
    fake_dialog.exec.return_value = QDialog.DialogCode.Accepted
    with patch.object(tp, "TenantFormDialog", return_value=fake_dialog):
        tenant_page._on_add_tenant()

    runner.tenant.get_all_tenants.assert_called()


@pytest.mark.unit
def test_tenant_page_delete_calls_service(page) -> None:
    from unittest.mock import patch

    import app.desktop.tenant_page as tp

    tenant_page, runner = page
    tenant = make_tenant()
    runner.tenant.get_all_tenants.return_value = [tenant]
    runner.tenant.delete_tenant.return_value = True

    tenant_page.refresh()
    tenant_page._tenant_table.selectRow(0)

    fake_confirm = MagicMock()
    fake_confirm.exec.return_value = QDialog.DialogCode.Accepted
    fake_confirm.confirmed = True
    with patch.object(tp, "ConfirmationDialog", return_value=fake_confirm):
        tenant_page._on_delete_tenant()

    runner.tenant.delete_tenant.assert_called_once_with(tenant.id)


@pytest.mark.unit
def test_tenant_page_service_error_keeps_list(page) -> None:
    tenant_page, runner = page
    from app.core.exceptions import NotFoundError

    runner.tenant.get_all_tenants.side_effect = NotFoundError("db down")
    tenant_page.refresh()
    assert tenant_page._tenant_model.rowCount() == 0
