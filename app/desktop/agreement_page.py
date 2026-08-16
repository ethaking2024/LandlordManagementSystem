from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.desktop.agreement_forms import (
    EndAgreementDialog,
    confirm_cancel_agreement,
    format_agreement_status,
)
from app.desktop.components.buttons import PrimaryButton, SecondaryButton
from app.desktop.components.page import Page
from app.desktop.components.table import DataTableView, SimpleTableModel
from app.desktop.components.widgets import EmptyState
from app.desktop.dates import format_date_display
from app.desktop.services import OPERATION_FAILED, ServiceRunner
from app.domain.enums import AgreementStatus


class AgreementsPage(Page):
    """Agreement list and lifecycle management page.

    Lists all agreements and lets the user view details, end an active
    agreement, or cancel an active agreement. All operations go through
    AgreementService via the ServiceRunner.
    """

    def __init__(
        self,
        runner: ServiceRunner,
        title: str = "Agreements",
        subtitle: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(title, subtitle, parent)
        self._runner = runner
        self._agreements: list[Any] = []
        self._current_agreement: Any = None

        self._stack = QStackedWidget()
        self.content_layout.addWidget(self._stack, stretch=1)

        self._build_list_view()
        self._build_detail_view()
        self._stack.setCurrentWidget(self._list_page)

    # ------------------------------------------------------------------
    # List view
    # ------------------------------------------------------------------

    def _build_list_view(self) -> None:
        self._list_page = QWidget()
        layout = QVBoxLayout(self._list_page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        toolbar = QHBoxLayout()
        self._refresh_button = PrimaryButton("Refresh")
        self._refresh_button.clicked.connect(self.refresh)
        self._view_button = SecondaryButton("Details")
        self._view_button.clicked.connect(self._on_view_agreement)
        self._end_button = SecondaryButton("End Agreement")
        self._end_button.clicked.connect(self._on_end_agreement)
        self._cancel_button = SecondaryButton("Cancel Agreement")
        self._cancel_button.setObjectName("dangerButton")
        self._cancel_button.clicked.connect(self._on_cancel_agreement)
        for button in (
            self._refresh_button,
            self._view_button,
            self._end_button,
            self._cancel_button,
        ):
            toolbar.addWidget(button)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        self._agreement_table = DataTableView()
        self._agreement_model = SimpleTableModel(
            ["Tenant", "Rental Space", "Status", "Start Date", "Monthly Rent"],
            parent=self._agreement_table,
        )
        self._agreement_table.setModel(self._agreement_model)
        self._agreement_table.doubleClicked.connect(self._on_view_agreement)
        layout.addWidget(self._agreement_table, stretch=1)

        self._list_empty = EmptyState(
            title="No agreements yet",
            message="Add a tenant and agreement from a vacant rental space to get started.",
        )
        layout.addWidget(self._list_empty)

        self._stack.addWidget(self._list_page)

    # ------------------------------------------------------------------
    # Detail view
    # ------------------------------------------------------------------

    def _build_detail_view(self) -> None:
        self._detail_page = QWidget()
        layout = QVBoxLayout(self._detail_page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        header = QHBoxLayout()
        self._back_button = SecondaryButton("Back to Agreements")
        self._back_button.clicked.connect(self._on_back)
        header.addWidget(self._back_button)
        header.addStretch()
        layout.addLayout(header)

        self._agreement_summary = QLabel("")
        self._agreement_summary.setObjectName("agreementSummary")
        self._agreement_summary.setWordWrap(True)
        layout.addWidget(self._agreement_summary)

        actions = QHBoxLayout()
        self._detail_end_button = SecondaryButton("End Agreement")
        self._detail_end_button.clicked.connect(self._on_end_agreement)
        self._detail_cancel_button = SecondaryButton("Cancel Agreement")
        self._detail_cancel_button.setObjectName("dangerButton")
        self._detail_cancel_button.clicked.connect(self._on_cancel_agreement)
        actions.addWidget(self._detail_end_button)
        actions.addWidget(self._detail_cancel_button)
        actions.addStretch()
        layout.addLayout(actions)

        self._stack.addWidget(self._detail_page)

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def refresh(self) -> None:
        def _load(services) -> list[tuple[Any, str, str]]:
            agreements = services.agreement().get_all_agreements()
            rows: list[tuple[Any, str, str]] = []
            for agreement in agreements:
                tenant = services.tenant().get_tenant(agreement.tenant_id)
                space = services.rental_space().get_rental_space(agreement.rental_space_id)
                rows.append(
                    (
                        agreement,
                        tenant.full_name or "",
                        f"{space.name or ''}",
                    )
                )
            return rows

        result = self._runner.run(_load)
        if result is OPERATION_FAILED:
            return
        self._agreements = [entry[0] for entry in result]
        self._render_rows(result)

    def _render_rows(self, rows: list[tuple[Any, str, str]]) -> None:
        table_rows: list[tuple[str, ...]] = [
            (
                tenant_name,
                space_label,
                format_agreement_status(agreement.status),
                format_date_display(agreement.start_date),
                str(agreement.monthly_rent),
            )
            for agreement, tenant_name, space_label in rows
        ]
        self._agreement_model.set_rows(table_rows)
        self._agreement_table.resize_columns_to_contents()
        has_rows = bool(table_rows)
        self._agreement_table.setVisible(has_rows)
        self._list_empty.setVisible(not has_rows)
        self._view_button.setEnabled(has_rows)
        self._end_button.setEnabled(has_rows)
        self._cancel_button.setEnabled(has_rows)

    def refresh_detail(self) -> None:
        if self._current_agreement is None:
            return

        def _load(services) -> tuple[Any, str, str]:
            agreement = services.agreement().get_agreement(self._current_agreement.id)
            tenant = services.tenant().get_tenant(agreement.tenant_id)
            space = services.rental_space().get_rental_space(agreement.rental_space_id)
            return agreement, tenant.full_name or "", space.name or ""

        result = self._runner.run(_load)
        if result is OPERATION_FAILED:
            return
        agreement, tenant_name, space_label = result
        self._current_agreement = agreement
        self._render_detail(agreement, tenant_name, space_label)

    def _render_detail(
        self,
        agreement: Any,
        tenant_name: str,
        space_label: str,
    ) -> None:
        lines = [
            f"Tenant: {tenant_name}",
            f"Rental Space: {space_label}",
            f"Status: {format_agreement_status(agreement.status)}",
            f"Start Date: {format_date_display(agreement.start_date)}",
        ]
        if agreement.end_date:
            lines.append(f"End Date: {format_date_display(agreement.end_date)}")
        lines.append(f"Monthly Rent: NPR {agreement.monthly_rent}")
        if agreement.security_deposit is not None:
            lines.append(f"Security Deposit: NPR {agreement.security_deposit}")
        if agreement.notes:
            lines.append(f"Notes: {agreement.notes}")
        self._agreement_summary.setText("\n".join(lines))

        is_active = agreement.status == AgreementStatus.ACTIVE
        self._detail_end_button.setEnabled(is_active)
        self._detail_cancel_button.setEnabled(is_active)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _selected_agreement(self) -> Any | None:
        index = self._agreement_table.currentIndex()
        row = index.row() if index.isValid() else -1
        if row < 0 or row >= len(self._agreements):
            return None
        return self._agreements[row]

    def _on_view_agreement(self, *_args) -> None:
        agreement = self._selected_agreement()
        if agreement is None:
            return
        self._current_agreement = agreement
        self.refresh_detail()
        self._stack.setCurrentWidget(self._detail_page)

    def _on_end_agreement(self) -> None:
        agreement = self._selected_agreement()
        if agreement is None or agreement.status != AgreementStatus.ACTIVE:
            return
        dialog = EndAgreementDialog(
            self._runner,
            agreement_data={
                "id": agreement.id,
                "start_date": agreement.start_date,
            },
            parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._after_mutation()

    def _on_cancel_agreement(self) -> None:
        agreement = self._selected_agreement()
        if agreement is None or agreement.status != AgreementStatus.ACTIVE:
            return
        label = self._current_agreement_label(agreement)
        result = confirm_cancel_agreement(self._runner, agreement.id, label, parent=self)
        if result is OPERATION_FAILED:
            return
        if result is not None:
            self._after_mutation()

    def _current_agreement_label(self, agreement: Any) -> str:
        if self._stack.currentWidget() is self._detail_page:
            return f"space of tenant {getattr(agreement, 'tenant_id', '')}"
        return str(getattr(agreement, "rental_space_id", ""))

    def _after_mutation(self) -> None:
        if self._stack.currentWidget() is self._detail_page:
            self.refresh_detail()
        else:
            self.refresh()

    def _on_back(self) -> None:
        self._current_agreement = None
        self.refresh()
        self._stack.setCurrentWidget(self._list_page)
