from __future__ import annotations

import csv
import io
from datetime import date
from decimal import Decimal

import pytest

from app.core.exceptions import ReportError
from app.domain.enums import BillStatus, PaymentMethod
from app.domain.value_objects import Money
from app.reports import csv as report_csv
from app.reports import pdf as report_pdf
from app.reports.data import BillReportRow
from app.reports.formats import (
    BILLING_HEADERS,
    PAYMENT_HEADERS,
    bill_status_label,
    billing_csv_rows,
    billing_display_rows,
    format_date,
    format_money,
    money_csv,
    payment_method_label,
)


def _bill_row() -> BillReportRow:
    return BillReportRow(
        billing_date=date(2026, 8, 1),
        tenant_name="Ram Sharma",
        property_name="Sunrise Apartments",
        rental_space_name="A-101",
        rent=Money(Decimal("20000")),
        utilities=Money(Decimal("3000")),
        total=Money(Decimal("23000")),
        paid=Money(Decimal("10000")),
        outstanding=Money(Decimal("13000")),
        status=BillStatus.CONFIRMED,
    )


@pytest.mark.unit
def test_money_csv_is_decimal_only() -> None:
    assert money_csv(Money(Decimal("80000.00"))) == "80000.00"


@pytest.mark.unit
def test_format_money_has_currency_prefix() -> None:
    assert format_money(Money(Decimal("80000.00"))) == "NPR 80000.00"


@pytest.mark.unit
def test_format_date_includes_bs() -> None:
    text = format_date(date(2026, 8, 16))
    assert text.startswith("2026-08-16 (")
    assert text.endswith(")")


@pytest.mark.unit
def test_payment_method_label() -> None:
    assert payment_method_label(PaymentMethod.BANK_TRANSFER) == "Bank transfer"


@pytest.mark.unit
def test_bill_status_label() -> None:
    assert bill_status_label(BillStatus.CONFIRMED) == "Confirmed"


@pytest.mark.unit
def test_billing_csv_rows_use_plain_values() -> None:
    rows = billing_csv_rows([_bill_row()])
    assert rows[0][0] == "2026-08-01"
    assert rows[0][4] == "20000.00"
    assert rows[0][5] == "3000.00"
    assert rows[0][9] == "Confirmed"


@pytest.mark.unit
def test_billing_display_rows_use_formatted_values() -> None:
    rows = billing_display_rows([_bill_row()])
    assert rows[0][4] == "NPR 20000.00"
    assert rows[0][5] == "NPR 3000.00"


class TestCsvRenderer:
    @pytest.mark.unit
    def test_render_csv_contains_headers_and_data(self) -> None:
        headers = list(BILLING_HEADERS)
        rows = billing_csv_rows([_bill_row()])
        text = report_csv.render_csv(headers, rows)
        lines = text.strip().splitlines()
        assert lines[0] == ",".join(headers)
        assert "2026-08-01" in lines[1]
        assert "Ram Sharma" in lines[1]
        assert "23000.00" in lines[1]

    @pytest.mark.unit
    def test_render_csv_escapes_commas_and_quotes(self) -> None:
        text = report_csv.render_csv(["A", "B"], [("hello, world", 'say "hi"')])
        parsed = list(csv.reader(io.StringIO(text)))
        assert parsed[1] == ["hello, world", 'say "hi"']

    @pytest.mark.unit
    def test_write_csv_creates_file(self, tmp_path) -> None:
        target = tmp_path / "report.csv"
        report_csv.write_csv(target, ["A", "B"], [("1", "2")])
        assert target.exists()
        with target.open(encoding="utf-8") as handle:
            content = handle.read()
        assert "A,B\n1,2\n" == content

    @pytest.mark.unit
    def test_write_csv_raises_on_bad_directory(self, tmp_path) -> None:
        target = tmp_path / "missing" / "report.csv"
        with pytest.raises(ReportError):
            report_csv.write_csv(target, ["A"], [])


class TestPdfRenderer:
    @pytest.mark.unit
    def test_build_story_contains_title_and_table(self) -> None:
        from reportlab.platypus import Table

        story = report_pdf.build_story(
            "Rent & Billing",
            "Period: 2026-08-01 to 2026-08-31",
            list(PAYMENT_HEADERS),
            [("2026-08-01", "Ram Sharma", "Sunrise Apartments", "A-101", "80000.00")],
        )
        texts = [paragraph.getPlainText() for paragraph in story if hasattr(paragraph, "getPlainText")]
        assert "LANDLORD MANAGEMENT SYSTEM" in texts
        assert "Rent & Billing" in texts
        assert any("Period:" in text for text in texts)

        tables = [flowable for flowable in story if isinstance(flowable, Table)]
        assert len(tables) == 1
        data = tables[0]._cellvalues
        assert len(data) == 2  # header row + one data row

    @pytest.mark.unit
    def test_write_pdf_creates_valid_pdf(self, tmp_path) -> None:
        target = tmp_path / "report.pdf"
        report_pdf.write_pdf(
            target,
            "Payments",
            None,
            list(PAYMENT_HEADERS),
            [("2026-08-01", "Ram Sharma", "Sunrise Apartments", "80000.00")],
        )
        assert target.exists()
        assert target.stat().st_size > 0
        with target.open("rb") as handle:
            assert handle.read(5) == b"%PDF-"

    @pytest.mark.unit
    def test_write_pdf_raises_on_bad_directory(self, tmp_path) -> None:
        target = tmp_path / "missing" / "report.pdf"
        with pytest.raises(ReportError):
            report_pdf.write_pdf(target, "Payments", None, ["A"], [("1",)])
