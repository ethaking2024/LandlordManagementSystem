from __future__ import annotations

from datetime import date
from typing import Any

from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.desktop.billing_forms import BillDetailDialog, format_bill_status
from app.desktop.components.buttons import SecondaryButton
from app.desktop.components.page import Page
from app.desktop.components.table import DataTableView, SimpleTableModel
from app.desktop.components.widgets import EmptyState
from app.desktop.dates import format_date_display
from app.desktop.payment_forms import PaymentDetailDialog, format_money, format_payment_method
from app.desktop.services import OPERATION_FAILED, ServiceRunner
from app.desktop.theme import AppColors
from app.domain.enums import PaymentStatus


class StatCard(QFrame):
    """A labelled KPI card showing a single dashboard value."""

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("statCard")
        self.setMinimumWidth(120)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(4)
        self._title_label = QLabel(title, self)
        self._title_label.setObjectName("statCardTitle")
        self._value_label = QLabel("—", self)
        self._value_label.setObjectName("statCardValue")
        layout.addWidget(self._title_label)
        layout.addWidget(self._value_label)
        self.setStyleSheet(
            f"""
            QFrame#statCard {{
                background-color: {AppColors.SURFACE};
                border: 1px solid {AppColors.BORDER};
                border-radius: 6px;
            }}
            QLabel#statCardTitle {{
                color: {AppColors.TEXT_SECONDARY};
                font-size: 12px;
                font-weight: 600;
            }}
            QLabel#statCardValue {{
                color: {AppColors.TEXT};
                font-size: 20px;
                font-weight: 700;
            }}
            """
        )

    def set_value(self, value: str) -> None:
        self._value_label.setText(value)


class _SectionLabel(QLabel):
    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setObjectName("sectionTitle")
        self.setStyleSheet(
            f"color: {AppColors.TEXT_SECONDARY}; font-size: 13px; font-weight: 700;"
        )


class DashboardPage(Page):
    """Read-only overview of the landlord's portfolio.

    Shows KPI cards, a current-month billing summary, outstanding bills, recent
    payments and vacant rental spaces. Every value is loaded from the application
    services inside a single ServiceRunner operation; the UI never calculates
    balances, applies occupancy rules or talks to repositories directly.
    """

    def __init__(
        self,
        runner: ServiceRunner,
        title: str = "Dashboard",
        subtitle: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(title, subtitle, parent)
        self._runner = runner
        self._outstanding: list[tuple[Any, str, str, Any]] = []
        self._payments: list[tuple[Any, str]] = []
        self._vacant: list[tuple[Any, str]] = []

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        body = QWidget()
        self._body_layout = QVBoxLayout(body)
        self._body_layout.setContentsMargins(0, 0, 0, 0)
        self._body_layout.setSpacing(12)
        scroll.setWidget(body)
        self.content_layout.addWidget(scroll, stretch=1)

        toolbar = QHBoxLayout()
        self._refresh_button = SecondaryButton("Refresh")
        self._refresh_button.clicked.connect(self.refresh)
        toolbar.addWidget(self._refresh_button)
        toolbar.addStretch()
        self._body_layout.addLayout(toolbar)

        self._build_kpi_cards()
        self._build_month_summary()
        self._build_outstanding_bills()
        self._build_recent_payments()
        self._build_vacant_spaces()

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def _build_kpi_cards(self) -> None:
        row = QHBoxLayout()
        self._cards = {
            "properties": StatCard("Properties"),
            "spaces": StatCard("Rental Spaces"),
            "occupied": StatCard("Occupied"),
            "vacant": StatCard("Vacant"),
            "active_tenants": StatCard("Active Tenants"),
            "active_agreements": StatCard("Active Agreements"),
        }
        for card in self._cards.values():
            row.addWidget(card, stretch=1)
        self._body_layout.addLayout(row)

    def _build_month_summary(self) -> None:
        self._body_layout.addWidget(_SectionLabel("Current Month"))
        row = QHBoxLayout()
        self._month_cards = {
            "billed": StatCard("Billed"),
            "paid": StatCard("Paid"),
            "outstanding": StatCard("Outstanding"),
        }
        for card in self._month_cards.values():
            row.addWidget(card, stretch=1)
        self._body_layout.addLayout(row)

    def _build_outstanding_bills(self) -> None:
        self._body_layout.addWidget(_SectionLabel("Outstanding Bills"))
        self._outstanding_table = DataTableView()
        self._outstanding_model = SimpleTableModel(
            ["Tenant", "Space", "Period", "Total", "Status", "Outstanding"],
            parent=self._outstanding_table,
        )
        self._outstanding_table.setModel(self._outstanding_model)
        self._outstanding_table.doubleClicked.connect(self._on_open_bill)
        self._body_layout.addWidget(self._outstanding_table, stretch=1)
        self._outstanding_empty = EmptyState(
            title="Nothing outstanding",
            message="All confirmed bills are paid in full.",
        )
        self._body_layout.addWidget(self._outstanding_empty)

    def _build_recent_payments(self) -> None:
        self._body_layout.addWidget(_SectionLabel("Recent Payments"))
        self._payment_table = DataTableView()
        self._payment_model = SimpleTableModel(
            ["Date", "Tenant", "Amount", "Payment Method"],
            parent=self._payment_table,
        )
        self._payment_table.setModel(self._payment_model)
        self._payment_table.doubleClicked.connect(self._on_open_payment)
        self._body_layout.addWidget(self._payment_table, stretch=1)
        self._payment_empty = EmptyState(
            title="No payments yet",
            message="Record a payment from a tenant to see it here.",
        )
        self._body_layout.addWidget(self._payment_empty)

    def _build_vacant_spaces(self) -> None:
        self._body_layout.addWidget(_SectionLabel("Vacant Spaces"))
        self._vacant_table = DataTableView()
        self._vacant_model = SimpleTableModel(
            ["Property", "Space"],
            parent=self._vacant_table,
        )
        self._vacant_table.setModel(self._vacant_model)
        self._body_layout.addWidget(self._vacant_table, stretch=1)
        self._vacant_empty = EmptyState(
            title="No vacant spaces",
            message="Every rental space is currently occupied.",
        )
        self._body_layout.addWidget(self._vacant_empty)

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def refresh(self) -> None:
        today = date.today()

        def _load(services) -> dict[str, Any]:
            properties = services.property().get_all_properties()
            spaces = services.rental_space().get_all_rental_spaces(limit=10000)

            occupied = 0
            vacant_rows: list[tuple[Any, str]] = []
            for space in spaces:
                if services.agreement().is_rental_space_occupied(space.id):
                    occupied += 1
                else:
                    prop = services.property().get_property(space.property_id)
                    vacant_rows.append((space, prop.name or ""))

            active_agreements = services.agreement().get_active_agreements(limit=10000)
            active_tenants = len({agreement.tenant_id for agreement in active_agreements})

            summary = services.payment().calculate_monthly_summary(today.year, today.month)

            outstanding_rows: list[tuple[Any, str, str, Any]] = []
            for bill, balance in services.payment().get_outstanding_bills():
                tenant = services.tenant().get_tenant(bill.tenant_id)
                space = services.rental_space().get_rental_space(bill.rental_space_id)
                outstanding_rows.append((bill, tenant.full_name or "", space.name or "", balance))

            payments = [
                payment
                for payment in services.payment().get_all_payments(limit=10000)
                if payment.status == PaymentStatus.RECORDED
            ]
            payments.sort(key=lambda payment: payment.payment_date, reverse=True)
            recent = payments[:10]
            payment_rows: list[tuple[Any, str]] = []
            for payment in recent:
                tenant = services.tenant().get_tenant(payment.tenant_id)
                payment_rows.append((payment, tenant.full_name or ""))

            return {
                "properties": len(properties),
                "spaces": len(spaces),
                "occupied": occupied,
                "vacant": len(spaces) - occupied,
                "active_tenants": active_tenants,
                "active_agreements": len(active_agreements),
                "summary": summary,
                "outstanding_rows": outstanding_rows,
                "payment_rows": payment_rows,
                "vacant_rows": vacant_rows,
            }

        result = self._runner.run(_load)
        if result is OPERATION_FAILED:
            return
        self._render(result)

    def _render(self, data: dict[str, Any]) -> None:
        self._cards["properties"].set_value(str(data["properties"]))
        self._cards["spaces"].set_value(str(data["spaces"]))
        self._cards["occupied"].set_value(str(data["occupied"]))
        self._cards["vacant"].set_value(str(data["vacant"]))
        self._cards["active_tenants"].set_value(str(data["active_tenants"]))
        self._cards["active_agreements"].set_value(str(data["active_agreements"]))

        summary = data["summary"]
        self._month_cards["billed"].set_value(format_money(summary.billed))
        self._month_cards["paid"].set_value(format_money(summary.paid))
        self._month_cards["outstanding"].set_value(format_money(summary.outstanding))

        self._outstanding = data["outstanding_rows"]
        outstanding_rows: list[tuple[str, ...]] = [
            (
                tenant_name,
                space_name,
                f"{format_date_display(bill.period.start)} — {format_date_display(bill.period.end)}",
                format_money(bill.total),
                format_bill_status(bill.status),
                format_money(balance.outstanding),
            )
            for bill, tenant_name, space_name, balance in self._outstanding
        ]
        self._outstanding_model.set_rows(outstanding_rows)
        self._outstanding_table.resize_columns_to_contents()
        has_outstanding = bool(outstanding_rows)
        self._outstanding_table.setVisible(has_outstanding)
        self._outstanding_empty.setVisible(not has_outstanding)

        self._payments = data["payment_rows"]
        payment_rows: list[tuple[str, ...]] = [
            (
                format_date_display(payment.payment_date),
                tenant_name,
                format_money(payment.amount),
                format_payment_method(payment.payment_method),
            )
            for payment, tenant_name in self._payments
        ]
        self._payment_model.set_rows(payment_rows)
        self._payment_table.resize_columns_to_contents()
        has_payments = bool(payment_rows)
        self._payment_table.setVisible(has_payments)
        self._payment_empty.setVisible(not has_payments)

        self._vacant = data["vacant_rows"]
        vacant_rows: list[tuple[str, ...]] = [
            (property_name, space.name or "")
            for space, property_name in self._vacant
        ]
        self._vacant_model.set_rows(vacant_rows)
        self._vacant_table.resize_columns_to_contents()
        has_vacant = bool(vacant_rows)
        self._vacant_table.setVisible(has_vacant)
        self._vacant_empty.setVisible(not has_vacant)

    # ------------------------------------------------------------------
    # Selection and navigation
    # ------------------------------------------------------------------

    def _selected_outstanding(self) -> tuple[Any, str, str, Any] | None:
        index = self._outstanding_table.currentIndex()
        row = index.row() if index.isValid() else -1
        if row < 0 or row >= len(self._outstanding):
            return None
        return self._outstanding[row]

    def _selected_payment(self) -> tuple[Any, str] | None:
        index = self._payment_table.currentIndex()
        row = index.row() if index.isValid() else -1
        if row < 0 or row >= len(self._payments):
            return None
        return self._payments[row]

    def _on_open_bill(self, *_args) -> None:
        selected = self._selected_outstanding()
        if selected is None:
            return
        bill, _tenant_name, _space_name, _balance = selected
        dialog = BillDetailDialog(self._runner, bill.id, parent=self)
        dialog.exec()

    def _on_open_payment(self, *_args) -> None:
        selected = self._selected_payment()
        if selected is None:
            return
        payment, _tenant_name = selected
        dialog = PaymentDetailDialog(self._runner, payment.id, parent=self)
        dialog.exec()
