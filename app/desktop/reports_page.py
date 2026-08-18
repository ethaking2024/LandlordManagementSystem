from __future__ import annotations

from collections.abc import Callable
from datetime import date, timedelta
from enum import Enum

from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QWidget,
)

from app.core.exceptions import ReportError
from app.desktop.components.buttons import PrimaryButton, SecondaryButton
from app.desktop.components.page import Page
from app.desktop.components.table import DataTableView, SimpleTableModel
from app.desktop.components.widgets import EmptyState
from app.desktop.dates import DateInput
from app.desktop.services import OPERATION_FAILED, ServiceRunner
from app.domain.enums import (
    BillStatus,
    DepositStatus,
    ExpenseCategory,
    ExpenseStatus,
    PaymentMethod,
    PaymentStatus,
)
from app.reports import csv as report_csv
from app.reports import pdf as report_pdf
from app.reports.data import ReportFilters
from app.reports.formats import (
    BILLING_HEADERS,
    DEPOSIT_HEADERS,
    EXPENSE_HEADERS,
    PAYMENT_HEADERS,
    SUMMARY_HEADERS,
    bill_status_label,
    billing_csv_rows,
    billing_display_rows,
    deposit_csv_rows,
    deposit_display_rows,
    deposit_status_label,
    expense_category_label,
    expense_csv_rows,
    expense_display_rows,
    expense_status_label,
    format_date,
    payment_csv_rows,
    payment_display_rows,
    payment_method_label,
    payment_status_label,
    summary_csv_rows,
    summary_display_rows,
)

_REPORT_TITLES: dict[str, str] = {
    "billing": "Rent & Billing",
    "payment": "Payments",
    "expense": "Expenses",
    "deposit": "Deposits",
    "summary": "Property Income & Expense Summary",
}

def _coerce_enum[EnumT: Enum](value, enum_type: type[EnumT]) -> EnumT | None:
    """Convert a combo data value back to its domain enum, or None for 'All'.

    PySide6 coerces stored StrEnum members to plain ``str`` via
    ``QComboBox.currentData()``, so filter values are converted back to the
    domain enums the report services expect.
    """
    if value is None:
        return None
    return enum_type(value)

_HEADERS: dict[str, list[str]] = {
    "billing": list(BILLING_HEADERS),
    "payment": list(PAYMENT_HEADERS),
    "expense": list(EXPENSE_HEADERS),
    "deposit": list(DEPOSIT_HEADERS),
    "summary": list(SUMMARY_HEADERS),
}

_DISPLAY_CONVERTERS: dict[str, Callable[..., list[tuple[str, ...]]]] = {
    "billing": billing_display_rows,
    "payment": payment_display_rows,
    "expense": expense_display_rows,
    "deposit": deposit_display_rows,
    "summary": summary_display_rows,
}

_CSV_CONVERTERS: dict[str, Callable[..., list[tuple[str, ...]]]] = {
    "billing": billing_csv_rows,
    "payment": payment_csv_rows,
    "expense": expense_csv_rows,
    "deposit": deposit_csv_rows,
    "summary": summary_csv_rows,
}


class ReportsPage(Page):
    """Read-only report generation and export page.

    Lets the user pick a report and filters, generate it through ReportService,
    and export the result as PDF or CSV. All financial values are derived by the
    application layer; the UI only formats and renders them.
    """

    def __init__(
        self,
        runner: ServiceRunner,
        title: str = "Reports",
        subtitle: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(title, subtitle, parent)
        self._runner = runner
        self._report_type = "billing"
        self._rows: list = []
        self._properties: list = []
        self._tenants: list = []
        self._spaces: list = []

        self._build_toolbar()
        self._build_filters()
        self._build_results()
        self._report_combo.currentIndexChanged.connect(self._on_report_type_changed)
        self._populate_status_combo()

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def _build_toolbar(self) -> None:
        toolbar = QHBoxLayout()
        self._report_combo = QComboBox()
        self._report_combo.setObjectName("reportCombo")
        for key, label in _REPORT_TITLES.items():
            self._report_combo.addItem(label, key)

        self._generate_button = PrimaryButton("Generate Report")
        self._generate_button.clicked.connect(self._on_generate)
        self._export_pdf_button = SecondaryButton("Export PDF")
        self._export_pdf_button.clicked.connect(self._on_export_pdf)
        self._export_csv_button = SecondaryButton("Export CSV")
        self._export_csv_button.clicked.connect(self._on_export_csv)
        self._refresh_button = SecondaryButton("Refresh")
        self._refresh_button.clicked.connect(self.refresh)

        toolbar.addWidget(QLabel("Report:"))
        toolbar.addWidget(self._report_combo)
        toolbar.addWidget(self._generate_button)
        toolbar.addWidget(self._export_pdf_button)
        toolbar.addWidget(self._export_csv_button)
        toolbar.addWidget(self._refresh_button)
        toolbar.addStretch()
        self.content_layout.addLayout(toolbar)

    def _build_filters(self) -> None:
        filters_widget = QWidget()
        grid = QGridLayout(filters_widget)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(8)

        today = date.today()
        month_start = today.replace(day=1)
        next_month = (
            date(month_start.year + 1, 1, 1)
            if month_start.month == 12
            else date(month_start.year, month_start.month + 1, 1)
        )
        month_end = next_month - timedelta(days=1)

        self._from_input = DateInput()
        self._from_input.set_date(month_start)
        self._to_input = DateInput()
        self._to_input.set_date(month_end)

        self._property_combo = QComboBox()
        self._property_combo.setObjectName("propertyCombo")
        self._property_combo.currentIndexChanged.connect(self._on_property_changed)
        self._tenant_combo = QComboBox()
        self._tenant_combo.setObjectName("tenantCombo")
        self._space_combo = QComboBox()
        self._space_combo.setObjectName("spaceCombo")
        self._status_combo = QComboBox()
        self._status_combo.setObjectName("statusCombo")

        self._method_label = QLabel("Payment Method")
        self._method_combo = QComboBox()
        self._method_combo.setObjectName("methodCombo")
        self._method_combo.addItem("All", None)
        for method in PaymentMethod:
            self._method_combo.addItem(payment_method_label(method), method)

        self._category_label = QLabel("Expense Category")
        self._category_combo = QComboBox()
        self._category_combo.setObjectName("categoryCombo")
        self._category_combo.addItem("All", None)
        for category in ExpenseCategory:
            self._category_combo.addItem(expense_category_label(category), category)

        grid.addWidget(QLabel("From"), 0, 0)
        grid.addWidget(self._from_input, 0, 1)
        grid.addWidget(QLabel("To"), 0, 2)
        grid.addWidget(self._to_input, 0, 3)
        grid.addWidget(QLabel("Property"), 1, 0)
        grid.addWidget(self._property_combo, 1, 1)
        grid.addWidget(QLabel("Tenant"), 1, 2)
        grid.addWidget(self._tenant_combo, 1, 3)
        grid.addWidget(QLabel("Rental Space"), 2, 0)
        grid.addWidget(self._space_combo, 2, 1)
        grid.addWidget(QLabel("Status"), 2, 2)
        grid.addWidget(self._status_combo, 2, 3)
        grid.addWidget(self._method_label, 3, 0)
        grid.addWidget(self._method_combo, 3, 1)
        grid.addWidget(self._category_label, 3, 2)
        grid.addWidget(self._category_combo, 3, 3)

        self._method_label.setVisible(False)
        self._method_combo.setVisible(False)
        self._category_label.setVisible(False)
        self._category_combo.setVisible(False)

        self.content_layout.addWidget(filters_widget)

        self._summary_label = QLabel("")
        self._summary_label.setObjectName("summaryLabel")
        self.content_layout.addWidget(self._summary_label)

    def _build_results(self) -> None:
        self._table = DataTableView()
        self._table_model = SimpleTableModel(list(_HEADERS["billing"]), parent=self._table)
        self._table.setModel(self._table_model)
        self.content_layout.addWidget(self._table, stretch=1)

        self._list_empty = EmptyState(
            title="No report generated yet",
            message="Choose a report and click Generate Report to see results.",
        )
        self.content_layout.addWidget(self._list_empty)

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def refresh(self) -> None:
        def _load(services) -> tuple[list, list, list]:
            properties = services.property().get_all_properties()
            tenants = services.tenant().get_all_tenants()
            spaces = services.rental_space().get_all_rental_spaces()
            return properties, tenants, spaces

        result = self._runner.run(_load)
        if result is OPERATION_FAILED:
            return
        self._properties, self._tenants, self._spaces = result
        self._repopulate_filter_combos()
        self._on_generate()

    def _repopulate_filter_combos(self) -> None:
        self._property_combo.clear()
        self._property_combo.addItem("All Properties", None)
        for prop in self._properties:
            self._property_combo.addItem(prop.name or "", prop.id)

        self._tenant_combo.clear()
        self._tenant_combo.addItem("All Tenants", None)
        for tenant in self._tenants:
            self._tenant_combo.addItem(tenant.full_name or "", tenant.id)

        self._populate_space_combo()

    def _populate_space_combo(self) -> None:
        property_id = self._property_combo.currentData()
        self._space_combo.clear()
        self._space_combo.addItem("All Spaces", None)
        for space in self._spaces:
            if property_id is None or space.property_id == property_id:
                self._space_combo.addItem(space.name or "", space.id)

    def _on_property_changed(self, *_args) -> None:
        self._populate_space_combo()

    def _on_report_type_changed(self, *_args) -> None:
        self._report_type = self._report_combo.currentData() or "billing"
        self._populate_status_combo()
        is_payment = self._report_type == "payment"
        is_expense = self._report_type == "expense"
        self._method_label.setVisible(is_payment)
        self._method_combo.setVisible(is_payment)
        self._category_label.setVisible(is_expense)
        self._category_combo.setVisible(is_expense)

    def _populate_status_combo(self) -> None:
        self._status_combo.clear()
        self._status_combo.addItem("All", None)
        if self._report_type == "billing":
            for bill_status in BillStatus:
                self._status_combo.addItem(bill_status_label(bill_status), bill_status)
            self._status_combo.setEnabled(True)
        elif self._report_type == "payment":
            for payment_status in PaymentStatus:
                self._status_combo.addItem(payment_status_label(payment_status), payment_status)
            self._status_combo.setEnabled(True)
        elif self._report_type == "expense":
            for expense_status in ExpenseStatus:
                self._status_combo.addItem(expense_status_label(expense_status), expense_status)
            self._status_combo.setEnabled(True)
        elif self._report_type == "deposit":
            for deposit_status in DepositStatus:
                self._status_combo.addItem(deposit_status_label(deposit_status), deposit_status)
            self._status_combo.setEnabled(True)
        else:
            self._status_combo.setEnabled(False)

    def _filters(self) -> ReportFilters:
        status_value = self._status_combo.currentData()
        return ReportFilters(
            from_date=self._from_input.value(),
            to_date=self._to_input.value(),
            property_id=self._property_combo.currentData(),
            tenant_id=self._tenant_combo.currentData(),
            rental_space_id=self._space_combo.currentData(),
            bill_status=_coerce_enum(status_value, BillStatus) if self._report_type == "billing" else None,
            payment_method=(
                _coerce_enum(self._method_combo.currentData(), PaymentMethod)
                if self._report_type == "payment"
                else None
            ),
            payment_status=(
                _coerce_enum(status_value, PaymentStatus) if self._report_type == "payment" else None
            ),
            expense_category=(
                _coerce_enum(self._category_combo.currentData(), ExpenseCategory)
                if self._report_type == "expense"
                else None
            ),
            expense_status=(
                _coerce_enum(status_value, ExpenseStatus) if self._report_type == "expense" else None
            ),
            deposit_status=(
                _coerce_enum(status_value, DepositStatus) if self._report_type == "deposit" else None
            ),
        )

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------

    def _on_generate(self) -> None:
        if not self._from_input.is_valid() or not self._to_input.is_valid():
            QMessageBox.warning(self, "Invalid Date Range", "Enter valid From and To dates.")
            return
        filters = self._filters()
        report_type = self._report_type

        def _load(services):
            report = services.report()
            if report_type == "billing":
                return report.billing_report(filters)
            if report_type == "payment":
                return report.payment_report(filters)
            if report_type == "expense":
                return report.expense_report(filters)
            if report_type == "deposit":
                return report.deposit_report(filters)
            if report_type == "summary":
                return report.property_summary(filters)
            return []

        result = self._runner.run(_load)
        if result is OPERATION_FAILED:
            return
        self._rows = list(result)
        self._render()

    def _render(self) -> None:
        display_rows = self._display_rows()
        self._table_model.set_headers(_HEADERS[self._report_type])
        self._table_model.set_rows(display_rows)
        self._table.resize_columns_to_contents()
        has_rows = bool(display_rows)
        self._table.setVisible(has_rows)
        self._list_empty.setVisible(not has_rows)
        self._export_pdf_button.setEnabled(has_rows)
        self._export_csv_button.setEnabled(has_rows)
        self._summary_label.setText(f"{len(display_rows)} records{self._period_text()}")

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def _on_export_pdf(self) -> None:
        if not self._rows:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Report as PDF", self._default_export_name(".pdf"), "PDF Files (*.pdf)"
        )
        if not path:
            return
        try:
            report_pdf.write_pdf(
                path,
                _REPORT_TITLES[self._report_type],
                self._export_subtitle(),
                _HEADERS[self._report_type],
                self._display_rows(),
            )
        except ReportError as exc:
            QMessageBox.critical(self, "Export Failed", str(exc))

    def _on_export_csv(self) -> None:
        if not self._rows:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Report as CSV", self._default_export_name(".csv"), "CSV Files (*.csv)"
        )
        if not path:
            return
        try:
            report_csv.write_csv(
                path,
                _HEADERS[self._report_type],
                self._csv_rows(),
            )
        except ReportError as exc:
            QMessageBox.critical(self, "Export Failed", str(exc))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _display_rows(self) -> list[tuple[str, ...]]:
        return list(_DISPLAY_CONVERTERS[self._report_type](self._rows))

    def _csv_rows(self) -> list[tuple[str, ...]]:
        return list(_CSV_CONVERTERS[self._report_type](self._rows))

    def _period_text(self) -> str:
        from_date = self._from_input.value()
        to_date = self._to_input.value()
        if from_date and to_date:
            return f" for {format_date(from_date)} to {format_date(to_date)}"
        return ""

    def _export_subtitle(self) -> str:
        from_date = self._from_input.value()
        to_date = self._to_input.value()
        if from_date and to_date:
            return f"Period: {format_date(from_date)} to {format_date(to_date)}"
        return "Period: All records"

    def _default_export_name(self, suffix: str) -> str:
        return f"report_{self._report_type}_{date.today().isoformat()}{suffix}"
