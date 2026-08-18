from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from app.domain.enums import (
    BillStatus,
    ExpenseCategory,
    ExpenseStatus,
    PaymentMethod,
    SpaceType,
    UtilityType,
)
from app.domain.value_objects import Money
from app.reports.data import ReportFilters

CURRENT_YEAR = date.today().year
CURRENT_MONTH = date.today().month


def _month_period() -> tuple[date, date]:
    import calendar

    days_in_month = calendar.monthrange(CURRENT_YEAR, CURRENT_MONTH)[1]
    start = date(CURRENT_YEAR, CURRENT_MONTH, 1)
    end = date(CURRENT_YEAR, CURRENT_MONTH, days_in_month)
    return start, end


def _next_month_period() -> tuple[date, date]:
    import calendar

    year = CURRENT_YEAR + 1 if CURRENT_MONTH == 12 else CURRENT_YEAR
    month = 1 if CURRENT_MONTH == 12 else CURRENT_MONTH + 1
    days_in_month = calendar.monthrange(year, month)[1]
    return date(year, month, 1), date(year, month, days_in_month)


def _seed_core(services, name: str, phone: str = "9800000001"):
    owner = services.owner().create_owner(name=f"{name} Owner", phone=phone)
    prop = services.property().create_property(owner.id, f"{name} Building", "Kathmandu")
    space = services.rental_space().create_rental_space(prop.id, "Room 1", SpaceType.ROOM)
    tenant = services.tenant().create_tenant(f"{name} Tenant", "9800000002")
    agreement = services.agreement().create_agreement(tenant.id, space.id, date(2026, 1, 1), "25000")
    return {
        "owner_id": owner.id,
        "property_id": prop.id,
        "space_id": space.id,
        "tenant_id": tenant.id,
        "agreement_id": agreement.id,
    }


def _seed_billed_agreement(services, name: str):
    ids = _seed_core(services, name)
    services.utility_config().set_config(ids["space_id"], UtilityType.ELECTRICITY, "fixed", "1500")
    services.utility_config().set_config(ids["space_id"], UtilityType.WATER, "no_charge")
    period_start, period_end = _month_period()
    bill = services.billing().generate_bill(ids["agreement_id"], period_start, period_end, period_end)
    services.billing().confirm_bill(bill.id)
    ids["bill_id"] = bill.id
    return ids


@pytest.mark.integration
def test_workflow_e_credit_overpayment_applied_to_another_bill(run_with_services, repositories) -> None:
    def _run(services):
        ids = _seed_billed_agreement(services, "Credit")
        bill1 = ids["bill_id"]
        balance_before = services.payment().calculate_bill_balance(bill1)
        assert balance_before.outstanding.amount == Decimal("26500.00")

        payment = services.payment().record_payment(
            ids["tenant_id"], date.today(), Money(Decimal("30000")), PaymentMethod.CASH
        )
        services.payment().allocate_payment(payment.id, bill1, Money(Decimal("26500")))

        credit = services.payment().calculate_tenant_credit(ids["tenant_id"])
        assert credit.amount == Decimal("3500.00")

        period_start, period_end = _next_month_period()
        bill2 = services.billing().generate_bill(
            ids["agreement_id"], period_start, period_end, period_end
        )
        services.billing().confirm_bill(bill2.id)

        allocations = services.payment().apply_tenant_credit(
            ids["tenant_id"], bill2.id, Money(Decimal("3500"))
        )
        assert len(allocations) == 1

        balance2 = services.payment().calculate_bill_balance(bill2.id)
        assert balance2.outstanding.amount == Decimal("23000.00")
        return {"bill1": bill1, "bill2": bill2.id, "credit": credit}

    result = run_with_services(_run)

    bill1 = repositories.bill.get(result["bill1"])
    assert bill1.status == BillStatus.CONFIRMED
    bill2 = repositories.bill.get(result["bill2"])
    assert bill2.status == BillStatus.CONFIRMED
    assert result["credit"].amount == Decimal("3500.00")


@pytest.mark.integration
def test_workflow_g_expense_total_and_void(run_with_services, repositories) -> None:
    def _run(services):
        ids = _seed_core(services, "Expense")
        first = services.expense().record_expense(
            ids["property_id"],
            date(CURRENT_YEAR, CURRENT_MONTH, 5),
            ExpenseCategory.PLUMBING,
            Money(Decimal("7500")),
            description="Pipe replacement",
            rental_space_id=ids["space_id"],
        )
        second = services.expense().record_expense(
            ids["property_id"],
            date(CURRENT_YEAR, CURRENT_MONTH, 10),
            ExpenseCategory.CLEANING,
            Money(Decimal("2500")),
            rental_space_id=ids["space_id"],
        )
        total = services.expense().calculate_property_expense_total(ids["property_id"])
        assert total.amount == Decimal("10000.00")

        services.expense().void_expense(first.id)
        total_after_void = services.expense().calculate_property_expense_total(ids["property_id"])
        assert total_after_void.amount == Decimal("2500.00")
        return {"first": first.id, "second": second.id}

    result = run_with_services(_run)

    first = repositories.expense.get(result["first"])
    assert first.status == ExpenseStatus.VOID
    second = repositories.expense.get(result["second"])
    assert second.status == ExpenseStatus.RECORDED


@pytest.mark.integration
def test_workflow_h_dashboard_kpis_and_summary(run_with_services) -> None:
    def _run(services):
        occupied = _seed_billed_agreement(services, "Dashboard")
        vacant_prop = services.property().create_property(
            occupied["owner_id"], "Dashboard Vacant Building", "Kathmandu"
        )
        vacant_space = services.rental_space().create_rental_space(
            vacant_prop.id, "Vacant Room", SpaceType.ROOM
        )

        period_start, period_end = _month_period()
        bill = services.billing().get_bill(occupied["bill_id"])
        assert bill.billing_date == period_end

        payment = services.payment().record_payment(
            occupied["tenant_id"], date.today(), Money(Decimal("26500")), PaymentMethod.CASH
        )
        services.payment().allocate_payment(payment.id, occupied["bill_id"], Money(Decimal("26500")))

        properties = services.property().get_all_properties()
        active_agreements = services.agreement().get_active_agreements(limit=10000)
        occupied_now = services.agreement().is_rental_space_occupied(occupied["space_id"])
        vacant_now = services.agreement().is_rental_space_occupied(vacant_space.id)
        summary = services.payment().calculate_monthly_summary(CURRENT_YEAR, CURRENT_MONTH)
        outstanding = services.payment().get_outstanding_bills()
        recent = services.payment().get_all_payments(limit=10000)

        return {
            "properties": len(properties),
            "active_agreements": len(active_agreements),
            "occupied": occupied_now,
            "vacant": vacant_now,
            "summary_billed": summary.billed,
            "summary_paid": summary.paid,
            "summary_outstanding": summary.outstanding,
            "outstanding_count": len(outstanding),
            "recent_payments": len(recent),
        }

    result = run_with_services(_run)

    assert result["properties"] == 2
    assert result["active_agreements"] == 1
    assert result["occupied"] is True
    assert result["vacant"] is False
    assert result["summary_billed"].amount == Decimal("26500.00")
    assert result["summary_paid"].amount == Decimal("26500.00")
    assert result["summary_outstanding"].amount == Decimal("0.00")
    assert result["outstanding_count"] == 0
    assert result["recent_payments"] == 1


@pytest.mark.integration
def test_workflow_i_reports_filter_and_export(run_with_services, tmp_path: Path) -> None:
    def _run(services):
        ids = _seed_billed_agreement(services, "Report")
        other = _seed_billed_agreement(services, "ReportTwo")

        period_start, period_end = _month_period()
        filters = ReportFilters(
            property_id=ids["property_id"],
            from_date=period_start,
            to_date=period_end,
            bill_status=BillStatus.CONFIRMED,
        )
        rows = services.report().billing_report(filters)
        assert len(rows) == 1
        assert rows[0].property_name == "Report Building"
        assert rows[0].total.amount == Decimal("26500.00")
        assert rows[0].status == BillStatus.CONFIRMED

        all_rows = services.report().billing_report(ReportFilters())
        assert len(all_rows) == 2
        return {"rows": rows, "other_property": other["property_id"], "all_rows": all_rows}

    result = run_with_services(_run)

    from app.reports.csv import write_csv
    from app.reports.pdf import write_pdf

    headers = ["Date", "Tenant", "Property", "Space", "Total", "Status"]
    csv_rows = [
        (
            str(row.billing_date),
            row.tenant_name,
            row.property_name,
            row.rental_space_name,
            str(row.total),
            row.status.value,
        )
        for row in result["rows"]
    ]
    csv_path = write_csv(tmp_path / "report.csv", headers, csv_rows)
    assert csv_path.is_file()
    content = csv_path.read_text(encoding="utf-8")
    assert "Report Building" in content
    assert content.count("\n") >= 2

    pdf_path = write_pdf(
        tmp_path / "report.pdf",
        "Billing Report",
        "Period test",
        headers,
        csv_rows,
    )
    assert pdf_path.is_file()
    assert pdf_path.read_bytes().startswith(b"%PDF")

    other_filter = ReportFilters(property_id=result["other_property"], bill_status=BillStatus.CONFIRMED)
    filtered = result["all_rows"]
    assert any(row.property_name == "ReportTwo Building" for row in filtered)
    assert other_filter.property_id is not None
