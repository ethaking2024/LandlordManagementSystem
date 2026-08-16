from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtWidgets import QMessageBox

from app.core.exceptions import ValidationError
from app.desktop.pages import build_navigation
from app.desktop.reports_page import ReportsPage
from app.desktop.services import OPERATION_FAILED, ServiceRunner
from app.domain.enums import (
    BillStatus,
    DepositStatus,
    ExpenseCategory,
    ExpenseStatus,
    PaymentMethod,
    PaymentStatus,
)
from app.domain.value_objects import Money
from app.reports.data import (
    BillReportRow,
    DepositReportRow,
    ExpenseReportRow,
    PaymentReportRow,
    PropertySummaryRow,
)
from app.reports.formats import (
    BILLING_HEADERS,
    DEPOSIT_HEADERS,
    EXPENSE_HEADERS,
    PAYMENT_HEADERS,
    SUMMARY_HEADERS,
)


def _money(value: str) -> Money:
    return Money(Decimal(value))


class FakeRunner:
    def __init__(self) -> None:
        self.property = MagicMock()
        self.tenant = MagicMock()
        self.rental_space = MagicMock()
        self.report = MagicMock()

    def run(self, operation, parent=None):
        services = MagicMock()
        services.property = MagicMock(return_value=self.property)
        services.tenant = MagicMock(return_value=self.tenant)
        services.rental_space = MagicMock(return_value=self.rental_space)
        services.report = MagicMock(return_value=self.report)
        try:
            return operation(services)
        except Exception:
            return OPERATION_FAILED


def make_property(property_id: uuid.UUID | None = None, name: str = "Sunrise Apartments"):
    prop = MagicMock()
    prop.id = property_id or uuid.uuid4()
    prop.name = name
    return prop


def make_tenant(tenant_id: uuid.UUID | None = None, name: str = "Ram Sharma"):
    tenant = MagicMock()
    tenant.id = tenant_id or uuid.uuid4()
    tenant.full_name = name
    return tenant


def make_space(space_id: uuid.UUID | None = None, property_id: uuid.UUID | None = None, name: str = "A-101"):
    space = MagicMock()
    space.id = space_id or uuid.uuid4()
    space.property_id = property_id or uuid.uuid4()
    space.name = name
    return space


def make_bill_row(tenant: str = "Ram Sharma", property_name: str = "Sunrise Apartments") -> BillReportRow:
    return BillReportRow(
        billing_date=date(2026, 8, 31),
        tenant_name=tenant,
        property_name=property_name,
        rental_space_name="A-101",
        rent=_money("20000"),
        utilities=_money("3000"),
        total=_money("23000"),
        paid=_money("10000"),
        outstanding=_money("13000"),
        status=BillStatus.CONFIRMED,
    )


def make_payment_row(tenant: str = "Ram Sharma") -> PaymentReportRow:
    return PaymentReportRow(
        payment_date=date(2026, 8, 10),
        tenant_name=tenant,
        property_name="Sunrise Apartments",
        amount=_money("8000"),
        payment_method=PaymentMethod.CASH,
        reference="REF-1",
        allocated=_money("6000"),
        remaining=_money("2000"),
        status=PaymentStatus.RECORDED,
    )


def make_expense_row() -> ExpenseReportRow:
    return ExpenseReportRow(
        expense_date=date(2026, 8, 15),
        property_name="Sunrise Apartments",
        rental_space_name="",
        category=ExpenseCategory.PLUMBING,
        amount=_money("3500"),
        description="Pipe repair",
        status=ExpenseStatus.RECORDED,
    )


def make_deposit_row() -> DepositReportRow:
    return DepositReportRow(
        tenant_name="Ram Sharma",
        property_name="Sunrise Apartments",
        rental_space_name="A-101",
        amount=_money("50000"),
        status=DepositStatus.HELD,
        settlement_date=None,
        deductions=_money("0"),
        refund=None,
    )


def make_summary_row() -> PropertySummaryRow:
    return PropertySummaryRow(
        property_name="Sunrise Apartments",
        from_date=date(2026, 8, 1),
        to_date=date(2026, 8, 31),
        rental_spaces=2,
        occupied=1,
        vacant=1,
        billed=_money("23000"),
        payments_received=_money("5000"),
        outstanding=_money("18000"),
        expenses=_money("3500"),
    )


@pytest.fixture
def page(qapp) -> tuple[ReportsPage, FakeRunner]:
    runner = FakeRunner()
    reports_page = ReportsPage(runner)
    reports_page.show()
    return reports_page, runner


@pytest.mark.unit
def test_reports_page_construction(page) -> None:
    reports_page, runner = page
    assert reports_page._report_combo.count() == 5
    assert reports_page._report_type == "billing"
    assert reports_page._status_combo.isEnabled()
    assert not reports_page._method_combo.isVisible()
    assert not reports_page._category_combo.isVisible()
    assert reports_page._table_model.columnCount() == len(BILLING_HEADERS)


@pytest.mark.unit
def test_reports_page_refresh_loads_filters_and_generates(page) -> None:
    reports_page, runner = page
    prop = make_property()
    tenant = make_tenant()
    space = make_space(property_id=prop.id)
    runner.property.get_all_properties.return_value = [prop]
    runner.tenant.get_all_tenants.return_value = [tenant]
    runner.rental_space.get_all_rental_spaces.return_value = [space]
    runner.report.billing_report.return_value = [make_bill_row()]

    reports_page.refresh()

    assert reports_page._property_combo.count() == 2  # All + one property
    assert reports_page._tenant_combo.count() == 2
    assert reports_page._space_combo.count() == 2
    assert reports_page._table_model.rowCount() == 1
    assert reports_page._table.isVisible()
    assert not reports_page._list_empty.isVisible()
    assert reports_page._export_pdf_button.isEnabled()
    assert reports_page._export_csv_button.isEnabled()
    assert "1 records" in reports_page._summary_label.text()


@pytest.mark.unit
def test_reports_page_refresh_empty_result_shows_empty_state(page) -> None:
    reports_page, runner = page
    runner.property.get_all_properties.return_value = []
    runner.tenant.get_all_tenants.return_value = []
    runner.rental_space.get_all_rental_spaces.return_value = []
    runner.report.billing_report.return_value = []

    reports_page.refresh()

    assert reports_page._table_model.rowCount() == 0
    assert reports_page._list_empty.isVisible()
    assert not reports_page._export_pdf_button.isEnabled()
    assert not reports_page._export_csv_button.isEnabled()


@pytest.mark.unit
def test_reports_page_service_error_keeps_table_clear(page) -> None:
    reports_page, runner = page
    runner.property.get_all_properties.return_value = []
    runner.tenant.get_all_tenants.return_value = []
    runner.rental_space.get_all_rental_spaces.return_value = []
    runner.report.billing_report.side_effect = ValidationError("db unavailable")

    reports_page.refresh()

    assert reports_page._table_model.rowCount() == 0


@pytest.mark.unit
def test_reports_page_switch_report_type_updates_filters(page) -> None:
    reports_page, runner = page
    runner.property.get_all_properties.return_value = []
    runner.tenant.get_all_tenants.return_value = []
    runner.rental_space.get_all_rental_spaces.return_value = []
    runner.report.payment_report.return_value = [make_payment_row()]
    for i in range(reports_page._report_combo.count()):
        if reports_page._report_combo.itemData(i) == "payment":
            reports_page._report_combo.setCurrentIndex(i)
            break

    assert reports_page._report_type == "payment"
    assert reports_page._method_combo.isVisible()
    assert not reports_page._category_combo.isVisible()
    status_items = [
        reports_page._status_combo.itemData(i) for i in range(reports_page._status_combo.count())
    ]
    assert PaymentStatus.RECORDED in status_items

    reports_page._on_generate()
    assert reports_page._table_model.columnCount() == len(PAYMENT_HEADERS)


@pytest.mark.unit
def test_reports_page_summary_report_disables_status(page) -> None:
    reports_page, runner = page
    runner.property.get_all_properties.return_value = []
    runner.tenant.get_all_tenants.return_value = []
    runner.rental_space.get_all_rental_spaces.return_value = []
    runner.report.property_summary.return_value = [make_summary_row()]
    for i in range(reports_page._report_combo.count()):
        if reports_page._report_combo.itemData(i) == "summary":
            reports_page._report_combo.setCurrentIndex(i)
            break

    assert reports_page._report_type == "summary"
    assert not reports_page._status_combo.isEnabled()

    reports_page._on_generate()
    assert reports_page._table_model.columnCount() == len(SUMMARY_HEADERS)


@pytest.mark.unit
def test_reports_page_property_filter_updates_spaces(page) -> None:
    reports_page, runner = page
    prop_a = make_property(name="A")
    prop_b = make_property(name="B")
    space_a = make_space(property_id=prop_a.id, name="A-1")
    space_b = make_space(property_id=prop_b.id, name="B-1")
    runner.property.get_all_properties.return_value = [prop_a, prop_b]
    runner.tenant.get_all_tenants.return_value = []
    runner.rental_space.get_all_rental_spaces.return_value = [space_a, space_b]
    runner.report.billing_report.return_value = []

    reports_page.refresh()

    index = next(
        (i for i in range(reports_page._property_combo.count()) if reports_page._property_combo.itemData(i) == prop_a.id),
        -1,
    )
    assert index >= 0
    reports_page._property_combo.setCurrentIndex(index)

    space_names = [reports_page._space_combo.itemText(i) for i in range(reports_page._space_combo.count())]
    assert "A-1" in space_names
    assert "B-1" not in space_names


@pytest.mark.unit
def test_reports_page_generate_each_report(page) -> None:
    reports_page, runner = page
    runner.property.get_all_properties.return_value = []
    runner.tenant.get_all_tenants.return_value = []
    runner.rental_space.get_all_rental_spaces.return_value = []

    cases = {
        "billing": (runner.report.billing_report, [make_bill_row()], BILLING_HEADERS),
        "payment": (runner.report.payment_report, [make_payment_row()], PAYMENT_HEADERS),
        "expense": (runner.report.expense_report, [make_expense_row()], EXPENSE_HEADERS),
        "deposit": (runner.report.deposit_report, [make_deposit_row()], DEPOSIT_HEADERS),
        "summary": (runner.report.property_summary, [make_summary_row()], SUMMARY_HEADERS),
    }
    for report_type, (mock, rows, headers) in cases.items():
        mock.return_value = rows
        for i in range(reports_page._report_combo.count()):
            if reports_page._report_combo.itemData(i) == report_type:
                reports_page._report_combo.setCurrentIndex(i)
                break
        reports_page._on_generate()
        assert reports_page._table_model.rowCount() == 1, report_type
        assert reports_page._table_model.columnCount() == len(headers), report_type


@pytest.mark.unit
def test_reports_page_generate_invalid_dates_warns(page) -> None:
    reports_page, runner = page
    reports_page._from_input._date_edit.setText("not-a-date")
    with patch.object(QMessageBox, "warning") as mock_warning:
        reports_page._on_generate()
    mock_warning.assert_called_once()
    assert reports_page._table_model.rowCount() == 0


@pytest.mark.unit
def test_reports_page_export_pdf(page, tmp_path) -> None:
    reports_page, runner = page
    runner.property.get_all_properties.return_value = []
    runner.tenant.get_all_tenants.return_value = []
    runner.rental_space.get_all_rental_spaces.return_value = []
    runner.report.billing_report.return_value = [make_bill_row()]
    reports_page.refresh()

    target = tmp_path / "export.pdf"
    with patch("app.desktop.reports_page.QFileDialog.getSaveFileName", return_value=(str(target), "")):
        reports_page._on_export_pdf()

    assert target.exists()
    with target.open("rb") as handle:
        assert handle.read(5) == b"%PDF-"


@pytest.mark.unit
def test_reports_page_export_csv(page, tmp_path) -> None:
    reports_page, runner = page
    runner.property.get_all_properties.return_value = []
    runner.tenant.get_all_tenants.return_value = []
    runner.rental_space.get_all_rental_spaces.return_value = []
    runner.report.billing_report.return_value = [make_bill_row()]
    reports_page.refresh()

    target = tmp_path / "export.csv"
    with patch("app.desktop.reports_page.QFileDialog.getSaveFileName", return_value=(str(target), "")):
        reports_page._on_export_csv()

    assert target.exists()
    content = target.read_text(encoding="utf-8")
    assert "Date,Tenant,Property" in content
    assert "Ram Sharma" in content


@pytest.mark.unit
def test_reports_page_export_cancelled_no_crash(page) -> None:
    reports_page, runner = page
    runner.property.get_all_properties.return_value = []
    runner.tenant.get_all_tenants.return_value = []
    runner.rental_space.get_all_rental_spaces.return_value = []
    runner.report.billing_report.return_value = [make_bill_row()]
    reports_page.refresh()

    with patch("app.desktop.reports_page.QFileDialog.getSaveFileName", return_value=("", "")):
        reports_page._on_export_pdf()
        reports_page._on_export_csv()

    assert reports_page._table_model.rowCount() == 1


@pytest.mark.unit
def test_navigation_creates_real_reports_page(qapp) -> None:
    runner = ServiceRunner(MagicMock())
    nav = build_navigation(runner)
    reports_page = nav.get("reports").page_factory()
    assert isinstance(reports_page, ReportsPage)


@pytest.mark.unit
def test_reports_page_has_no_repository_access() -> None:
    """The reports page must stay presentation-only and never touch infrastructure."""
    import inspect

    import app.desktop.reports_page as module

    source = inspect.getsource(module)
    assert "from app.infrastructure" not in source
    assert "sqlalchemy" not in source
    assert "Session" not in source
    assert "session" not in source


@pytest.mark.unit
def test_report_service_has_no_repository_access() -> None:
    """ReportService composes services and must never touch repositories directly."""
    import inspect

    from app.application.services.report_service import ReportService

    source = inspect.getsource(ReportService)
    assert "Repository" not in source
    assert "sqlalchemy" not in source
    assert "session" not in source
