from __future__ import annotations

import calendar
import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtWidgets import QDialog

from app.desktop.property_page import PropertiesPage
from app.desktop.services import OPERATION_FAILED
from app.desktop.settings_page import SettingsPage
from app.domain.enums import (
    AgreementStatus,
    BillStatus,
    DepositStatus,
    ExpenseStatus,
    PaymentMethod,
    SpaceType,
    UtilityType,
)


def _current_month() -> tuple[date, date]:
    today = date.today()
    month_start = today.replace(day=1)
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    return month_start, month_start.replace(day=days_in_month)


MONTH_START, MONTH_END = _current_month()


def _seed_core_chain(runner):
    """Persist owner -> property -> space -> tenant -> agreement via the real
    ServiceRunner wiring used by the desktop UI."""
    result = runner.run(
        lambda services: _build_core_chain(services)
    )
    assert result is not OPERATION_FAILED
    return result


def _build_core_chain(services) -> dict:
    owner = services.owner().create_owner(name="E2E Owner", phone="9800000001")
    prop = services.property().create_property(owner.id, "E2E Building", "Kathmandu, Nepal")
    space = services.rental_space().create_rental_space(prop.id, "Room 1", SpaceType.ROOM)
    tenant = services.tenant().create_tenant("E2E Tenant", "9800000002")
    agreement = services.agreement().create_agreement(
        tenant.id,
        space.id,
        MONTH_START,
        "25000",
        security_deposit="50000",
    )
    return {
        "owner": owner,
        "property": prop,
        "space": space,
        "tenant": tenant,
        "agreement": agreement,
    }


def _seed_utility_configs(runner, space_id: uuid.UUID) -> None:
    result = runner.run(
        lambda services: _set_utility_configs(services, space_id)
    )
    assert result is not OPERATION_FAILED


def _set_utility_configs(services, space_id: uuid.UUID) -> bool:
    services.utility_config().set_config(space_id, UtilityType.ELECTRICITY, "fixed", "1500")
    services.utility_config().set_config(space_id, UtilityType.WATER, "no_charge")
    return True


def _seed_confirmed_bill(runner) -> tuple[dict, object]:
    chain = _seed_core_chain(runner)
    _seed_utility_configs(runner, chain["space"].id)
    bill = runner.run(
        lambda services: services.billing().generate_bill(
            chain["agreement"].id, MONTH_START, MONTH_END, date.today()
        )
    )
    assert bill is not OPERATION_FAILED
    confirm = runner.run(lambda services: services.billing().confirm_bill(bill.id))
    assert confirm is not OPERATION_FAILED
    return chain, bill


@pytest.mark.integration
def test_main_window_boots_with_real_database_and_navigates_all_pages(app_window) -> None:
    window = app_window
    assert window.windowTitle() == "Landlord Management System"
    assert window.current_key == "dashboard"
    assert window.database_session is not None

    for key in window.navigation.keys():
        window.navigate(key)
        assert window.current_key == key
        assert window._stack.currentWidget() is not None

    from app.desktop.dashboard_page import DashboardPage

    assert isinstance(window._pages["dashboard"], DashboardPage)
    assert isinstance(window._pages["properties"], PropertiesPage)
    assert isinstance(window._pages["settings"], SettingsPage)


@pytest.mark.integration
def test_properties_page_refresh_renders_real_database(app_window, repositories, qapp) -> None:
    app_window.navigate("properties")
    page = app_window._pages["properties"]
    assert isinstance(page, PropertiesPage)
    page.refresh()
    assert page._property_model.rowCount() == 0
    assert page._property_table.isHidden()
    assert not page._list_empty.isHidden()

    result = app_window.runner.run(
        lambda services: services.owner().create_owner(name="Owner X", phone="9800000001")
    )
    assert result is not OPERATION_FAILED
    prop = app_window.runner.run(
        lambda services: services.property().create_property(
            result.id, "Building X", "Kathmandu"
        )
    )
    assert prop is not OPERATION_FAILED
    assert repositories.property.get(prop.id) is not None

    page.refresh()
    assert page._property_model.rowCount() == 1
    assert page._property_model.data(page._property_model.index(0, 0)) == "Building X"
    assert not page._property_table.isHidden()
    assert page._list_empty.isHidden()


@pytest.mark.integration
def test_create_core_chain_through_real_dialogs(runner, repositories, qapp) -> None:
    from app.desktop.agreement_forms import AgreementFormDialog
    from app.desktop.forms import AddOwnerDialog, PropertyFormDialog, RentalSpaceFormDialog
    from app.desktop.tenant_forms import TenantFormDialog

    owner_dialog = AddOwnerDialog(runner)
    owner_dialog._name_edit.setText("E2E Owner")
    owner_dialog._phone_edit.setText("9800000001")
    owner_dialog._on_save()
    owner = owner_dialog.created_owner()
    assert owner is not OPERATION_FAILED

    property_dialog = PropertyFormDialog(runner)
    assert property_dialog._owner_combo.count() == 1
    property_dialog._owner_combo.setCurrentIndex(0)
    property_dialog._name_edit.setText("E2E Building")
    property_dialog._address_edit.setText("Kathmandu, Nepal")
    property_dialog._on_save()
    prop = property_dialog.result_property()
    assert prop is not OPERATION_FAILED

    space_dialog = RentalSpaceFormDialog(runner, property_id=prop.id)
    space_dialog._name_edit.setText("Room 1")
    space_dialog._type_combo.setCurrentIndex(space_dialog._type_combo.findData(SpaceType.ROOM))
    space_dialog._on_save()
    space = space_dialog.result_space()
    assert space is not OPERATION_FAILED

    tenant_dialog = TenantFormDialog(runner)
    tenant_dialog._name_edit.setText("E2E Tenant")
    tenant_dialog._phone_edit.setText("9800000002")
    tenant_dialog._on_save()
    tenant = tenant_dialog.result_tenant()
    assert tenant is not OPERATION_FAILED

    agreement_dialog = AgreementFormDialog(runner, rental_space_id=space.id)
    assert agreement_dialog._tenant_combo.count() == 1
    agreement_dialog._tenant_combo.setCurrentIndex(0)
    agreement_dialog._start_input.set_date(MONTH_START)
    agreement_dialog._rent_edit.setText("25000")
    agreement_dialog._on_save()
    agreement = agreement_dialog.result_agreement()
    assert agreement is not OPERATION_FAILED

    assert repositories.owner.get(owner.id).name == "E2E Owner"
    assert repositories.property.get(prop.id).address == "Kathmandu, Nepal"
    assert repositories.rental_space.get(space.id).is_active is True
    assert repositories.tenant.get(tenant.id).full_name == "E2E Tenant"
    stored = repositories.agreement.get(agreement.id)
    assert stored.status == AgreementStatus.ACTIVE
    assert stored.monthly_rent.amount == Decimal("25000.00")


@pytest.mark.integration
def test_bill_payment_allocation_workflow_through_real_dialogs(runner, repositories, qapp) -> None:
    from app.desktop.billing_forms import BillDetailDialog, GenerateBillDialog
    from app.desktop.payment_forms import AllocatePaymentDialog, RecordPaymentDialog
    from app.desktop.utility_forms import UtilityConfigDialog

    chain = _seed_core_chain(runner)
    space = chain["space"]

    electricity = UtilityConfigDialog(runner, space.id, UtilityType.ELECTRICITY)
    electricity._type_combo.setCurrentIndex(
        electricity._type_combo.findData("fixed")
    )
    electricity._amount_edit.setText("1500")
    electricity._on_save()
    assert electricity.result_config() is not OPERATION_FAILED

    water = UtilityConfigDialog(runner, space.id, UtilityType.WATER)
    water._type_combo.setCurrentIndex(water._type_combo.findData("no_charge"))
    water._on_save()
    assert water.result_config() is not OPERATION_FAILED

    bill_dialog = GenerateBillDialog(runner)
    assert bill_dialog._agreement_combo.count() == 1
    bill_dialog._agreement_combo.setCurrentIndex(0)
    bill_dialog._period_start_input.set_date(MONTH_START)
    bill_dialog._period_end_input.set_date(MONTH_END)
    bill_dialog._on_generate()
    bill = bill_dialog.result_bill()
    assert bill is not OPERATION_FAILED
    assert bill_dialog.generated is True
    assert bill.total.amount == Decimal("26500.00")

    import app.desktop.billing_forms as billing_forms

    confirm = MagicMock()
    confirm.exec.return_value = QDialog.DialogCode.Accepted
    confirm.confirmed = True
    with patch.object(billing_forms, "ConfirmationDialog", return_value=confirm):
        detail = BillDetailDialog(runner, bill.id)
        detail._on_confirm()
    stored_bill = repositories.bill.get(bill.id)
    assert stored_bill.status == BillStatus.CONFIRMED

    payment_dialog = RecordPaymentDialog(runner)
    assert payment_dialog._tenant_combo.count() == 1
    payment_dialog._tenant_combo.setCurrentIndex(0)
    payment_dialog._payment_date_input.set_date(MONTH_END)
    payment_dialog._amount_edit.setText("26500")
    payment_dialog._method_combo.setCurrentIndex(
        payment_dialog._method_combo.findData(PaymentMethod.CASH)
    )
    payment_dialog._on_save()
    payment = payment_dialog.result_payment()
    assert payment is not OPERATION_FAILED
    assert payment_dialog.saved is True

    allocation_dialog = AllocatePaymentDialog(runner, payment.id)
    assert allocation_dialog._bill_combo.count() == 1
    allocation_dialog._bill_combo.setCurrentIndex(0)
    allocation_dialog._amount_edit.setText("26500")
    allocation_dialog._on_allocate()
    assert allocation_dialog.result_allocation() is not OPERATION_FAILED
    assert allocation_dialog.allocated is True

    balance = runner.run(
        lambda services: services.payment().calculate_bill_balance(bill.id)
    )
    assert balance is not OPERATION_FAILED
    assert balance.outstanding.amount == Decimal("0.00")
    assert balance.allocated.amount == Decimal("26500.00")


@pytest.mark.integration
def test_deposit_and_expense_recorded_through_real_dialogs(runner, repositories, qapp) -> None:
    from app.desktop.deposit_forms import RecordDepositDialog
    from app.desktop.expense_forms import ExpenseDialog

    chain = _seed_core_chain(runner)
    agreement = chain["agreement"]

    deposit_dialog = RecordDepositDialog(runner)
    assert deposit_dialog._agreement_combo.count() == 1
    deposit_dialog._agreement_combo.setCurrentIndex(0)
    deposit_dialog._amount_edit.setText("50000")
    deposit_dialog._received_date_input.set_date(MONTH_START)
    deposit_dialog._on_save()
    deposit = deposit_dialog.result_deposit()
    assert deposit is not OPERATION_FAILED
    assert deposit_dialog.saved is True

    expense_dialog = ExpenseDialog(runner)
    expense_dialog._expense_date_input.set_date(date.today())
    expense_dialog._amount_edit.setText("7500")
    expense_dialog._on_save()
    expense = expense_dialog.result_expense()
    assert expense is not OPERATION_FAILED
    assert expense_dialog.saved is True

    stored_deposit = repositories.deposit.get(deposit.id)
    assert stored_deposit.status == DepositStatus.HELD
    assert stored_deposit.amount.amount == Decimal("50000.00")
    assert stored_deposit.agreement_id == agreement.id

    stored_expense = repositories.expense.get(expense.id)
    assert stored_expense.status == ExpenseStatus.RECORDED
    assert stored_expense.amount.amount == Decimal("7500.00")
    assert stored_expense.property_id == chain["property"].id


@pytest.mark.integration
def test_dashboard_and_reports_refresh_real_data(runner, qapp) -> None:
    from app.desktop.dashboard_page import DashboardPage
    from app.desktop.reports_page import ReportsPage

    _seed_confirmed_bill(runner)

    dashboard = DashboardPage(runner)
    dashboard.refresh()
    assert dashboard._cards["properties"]._value_label.text() == "1"
    assert dashboard._cards["spaces"]._value_label.text() == "1"
    assert dashboard._cards["occupied"]._value_label.text() == "1"
    assert dashboard._cards["vacant"]._value_label.text() == "0"
    assert dashboard._outstanding_model.rowCount() == 1

    reports = ReportsPage(runner)
    reports.refresh()
    assert reports._table_model.rowCount() == 1
    assert reports._table_model.columnCount() > 0


@pytest.mark.integration
def test_error_boundary_returns_operation_failed_without_crash(runner, repositories, qapp) -> None:
    from app.desktop.billing_forms import GenerateBillDialog

    chain = _seed_core_chain(runner)
    _seed_utility_configs(runner, chain["space"].id)

    with patch("app.desktop.error_handler._show_message") as show_message:
        bill_dialog = GenerateBillDialog(runner)
        bill_dialog._agreement_combo.setCurrentIndex(0)
        bill_dialog._period_start_input.set_date(MONTH_START)
        bill_dialog._period_end_input.set_date(MONTH_END)
        bill_dialog._on_generate()
        bill = bill_dialog.result_bill()
        assert bill is not OPERATION_FAILED
        assert bill_dialog.generated is True

        duplicate = GenerateBillDialog(runner)
        duplicate._agreement_combo.setCurrentIndex(0)
        duplicate._period_start_input.set_date(MONTH_START)
        duplicate._period_end_input.set_date(MONTH_END)
        duplicate._on_generate()
        assert duplicate.result_bill() is OPERATION_FAILED
        assert duplicate.generated is False
        assert show_message.call_count == 1

    assert repositories.bill.get(bill.id) is not None


@pytest.mark.integration
def test_fresh_main_window_populates_data_pages_without_manual_refresh(app_window, runner, qapp) -> None:
    """V1.0.1 regression: after a restart, navigating to a page must load
    persisted data automatically (no manual Refresh/Search)."""
    from typing import cast

    from app.desktop.agreement_page import AgreementsPage
    from app.desktop.dashboard_page import DashboardPage
    from app.desktop.main_window import MainWindow
    from app.desktop.tenant_page import TenantsPage

    _seed_core_chain(runner)

    window = MainWindow(database_session=app_window.database_session)

    window.navigate("properties")
    page = cast(PropertiesPage, window._pages["properties"])
    assert page._property_model.rowCount() == 1
    assert not page._property_table.isHidden()
    assert page._list_empty.isHidden()

    window.navigate("tenants")
    tenant_page = cast(TenantsPage, window._pages["tenants"])
    assert tenant_page._tenant_model.rowCount() == 1
    assert not tenant_page._tenant_table.isHidden()

    window.navigate("agreements")
    agreement_page = cast(AgreementsPage, window._pages["agreements"])
    assert agreement_page._agreement_model.rowCount() == 1

    window.navigate("dashboard")
    dashboard = cast(DashboardPage, window._pages["dashboard"])
    assert dashboard._cards["properties"]._value_label.text() == "1"
    assert dashboard._cards["spaces"]._value_label.text() == "1"


@pytest.mark.integration
def test_navigation_refreshes_cached_page_when_navigated_again(app_window, runner, qapp) -> None:
    """V1.0.1 regression: re-entering an already-created page shows changes
    made elsewhere."""
    from typing import cast

    from app.desktop.main_window import MainWindow

    window = MainWindow(database_session=app_window.database_session)

    window.navigate("properties")
    page = cast(PropertiesPage, window._pages["properties"])
    assert page._property_model.rowCount() == 0

    owner = runner.run(lambda s: s.owner().create_owner(name="Owner Y", phone="9800000003"))
    assert owner is not OPERATION_FAILED
    prop = runner.run(
        lambda s: s.property().create_property(owner.id, "Building Y", "Kathmandu")
    )
    assert prop is not OPERATION_FAILED

    window.navigate("dashboard")
    window.navigate("properties")
    assert page._property_model.rowCount() == 1
    assert page._property_model.data(page._property_model.index(0, 0)) == "Building Y"


@pytest.mark.integration
def test_agreement_dialog_tenant_selector_shows_persisted_tenants_after_restart(
    app_window, runner, qapp
) -> None:
    """V1.0.1 regression: a freshly opened agreement dialog lists tenants that
    were persisted in a previous session."""
    from app.desktop.agreement_forms import AgreementFormDialog

    chain = _seed_core_chain(runner)

    dialog = AgreementFormDialog(
        app_window.runner,
        rental_space_id=chain["space"].id,
        rental_space_label=chain["space"].name or "",
    )
    assert dialog._tenant_combo.count() >= 1
    assert any(
        dialog._tenant_combo.itemData(i) == chain["tenant"].id
        for i in range(dialog._tenant_combo.count())
    )


@pytest.mark.integration
def test_navigation_supports_pages_without_refresh(app_window, qapp) -> None:
    """V1.0.1 regression: navigating to pages without a callable refresh()
    (Settings, placeholder pages) must not fail."""
    from app.desktop.components.page import PlaceholderPage
    from app.desktop.main_window import MainWindow
    from app.desktop.pages import build_navigation

    window = app_window
    window.navigate("settings")
    assert window.current_key == "settings"
    assert window._pages["settings"] is not None

    placeholder_nav = build_navigation()
    placeholder_window = MainWindow(
        navigation=placeholder_nav, database_session=app_window.database_session
    )
    placeholder_window.navigate("properties")
    assert isinstance(placeholder_window._pages["properties"], PlaceholderPage)
    assert placeholder_window.current_key == "properties"
