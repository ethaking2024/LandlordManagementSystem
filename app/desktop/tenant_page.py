from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.desktop.components.buttons import PrimaryButton, SecondaryButton
from app.desktop.components.dialogs import ConfirmationDialog
from app.desktop.components.page import Page
from app.desktop.components.table import DataTableView, SimpleTableModel
from app.desktop.components.widgets import EmptyState
from app.desktop.services import OPERATION_FAILED, ServiceRunner
from app.desktop.tenant_forms import TenantFormDialog


class TenantsPage(Page):
    """Tenant list and management page.

    Shows a searchable list of tenants and lets the user add, edit, delete and
    view tenant details. All operations go through TenantService via the
    ServiceRunner; business validation stays in the service layer.
    """

    def __init__(
        self,
        runner: ServiceRunner,
        title: str = "Tenants",
        subtitle: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(title, subtitle, parent)
        self._runner = runner
        self._tenants: list[Any] = []
        self._current_tenant: Any = None
        self._search_term = ""

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

        search_row = QHBoxLayout()
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("Search by name or phone")
        self._search_edit.setObjectName("tenantSearch")
        self._search_edit.returnPressed.connect(self.refresh)
        search_button = SecondaryButton("Search")
        search_button.clicked.connect(self.refresh)
        search_row.addWidget(self._search_edit, 1)
        search_row.addWidget(search_button)
        layout.addLayout(search_row)

        toolbar = QHBoxLayout()
        self._add_button = PrimaryButton("Add Tenant")
        self._add_button.clicked.connect(self._on_add_tenant)
        self._edit_button = SecondaryButton("Edit")
        self._edit_button.clicked.connect(self._on_edit_tenant)
        self._open_button = SecondaryButton("Details")
        self._open_button.clicked.connect(self._on_open_tenant)
        self._delete_button = SecondaryButton("Delete")
        self._delete_button.setObjectName("dangerButton")
        self._delete_button.clicked.connect(self._on_delete_tenant)
        for button in (
            self._add_button,
            self._edit_button,
            self._open_button,
            self._delete_button,
        ):
            toolbar.addWidget(button)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        self._tenant_table = DataTableView()
        self._tenant_model = SimpleTableModel(
            ["Full Name", "Phone", "Email", "Address"],
            parent=self._tenant_table,
        )
        self._tenant_table.setModel(self._tenant_model)
        self._tenant_table.doubleClicked.connect(self._on_open_tenant)
        layout.addWidget(self._tenant_table, stretch=1)

        self._list_empty = EmptyState(
            title="No tenants found",
            message="Add your first tenant to start creating agreements.",
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
        self._back_button = SecondaryButton("Back to Tenants")
        self._back_button.clicked.connect(self._on_back)
        header.addWidget(self._back_button)
        header.addStretch()
        layout.addLayout(header)

        self._tenant_summary = QLabel("")
        self._tenant_summary.setObjectName("tenantSummary")
        self._tenant_summary.setWordWrap(True)
        layout.addWidget(self._tenant_summary)

        self._agreement_table = DataTableView()
        self._agreement_model = SimpleTableModel(
            ["Rental Space", "Status", "Start Date", "Monthly Rent"],
            parent=self._agreement_table,
        )
        self._agreement_table.setModel(self._agreement_model)
        layout.addWidget(self._agreement_table, stretch=1)

        self._agreement_empty = EmptyState(
            title="No agreements",
            message="This tenant does not have any agreements yet.",
        )
        layout.addWidget(self._agreement_empty)

        self._stack.addWidget(self._detail_page)

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def refresh(self) -> None:
        """Reload tenants based on the current search term."""
        self._search_term = self._search_edit.text().strip()
        if self._search_term:
            result = self._runner.run(
                lambda s: self._search(s, self._search_term),
            )
        else:
            result = self._runner.run(lambda s: s.tenant().get_all_tenants())
        if result is OPERATION_FAILED:
            return
        self._tenants = result
        self._render_tenants()

    def _search(self, services, term: str) -> list[Any]:
        by_name = list(services.tenant().search_tenants_by_name(term))
        by_phone = services.tenant().get_tenant_by_phone(term)
        if by_phone is None or any(t.id == by_phone.id for t in by_name):
            return by_name
        return [by_phone, *by_name]

    def refresh_agreements(self) -> None:
        if self._current_tenant is None:
            return

        def _load(services) -> tuple[Any, list[tuple[str, ...]]]:
            tenant = services.tenant().get_tenant(self._current_tenant.id)
            agreements = services.agreement().get_agreements_by_tenant(self._current_tenant.id)
            rows: list[tuple[str, ...]] = []
            for agreement in agreements:
                space = services.rental_space().get_rental_space(agreement.rental_space_id)
                rows.append(
                    (
                        space.name or "",
                        agreement.status.value.capitalize(),
                        agreement.start_date.isoformat(),
                        str(agreement.monthly_rent),
                    )
                )
            return tenant, rows

        result = self._runner.run(_load)
        if result is OPERATION_FAILED:
            return
        tenant, rows = result
        self._current_tenant = tenant
        self._render_agreements(rows)

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _render_tenants(self) -> None:
        rows: list[tuple[str, ...]] = []
        for tenant in self._tenants:
            rows.append(
                (
                    tenant.full_name or "",
                    str(tenant.phone or ""),
                    tenant.email or "",
                    tenant.address or "",
                )
            )
        self._tenant_model.set_rows(rows)
        self._tenant_table.resize_columns_to_contents()
        has_rows = bool(rows)
        self._tenant_table.setVisible(has_rows)
        self._list_empty.setVisible(not has_rows)
        self._edit_button.setEnabled(has_rows)
        self._open_button.setEnabled(has_rows)
        self._delete_button.setEnabled(has_rows)

    def _render_agreements(self, rows: list[tuple[str, ...]]) -> None:
        if self._current_tenant is None:
            return
        self._tenant_summary.setText(
            f"{self._current_tenant.full_name or ''} — {self._current_tenant.phone or ''}"
        )
        self._agreement_model.set_rows(rows)
        self._agreement_table.resize_columns_to_contents()
        has_rows = bool(rows)
        self._agreement_table.setVisible(has_rows)
        self._agreement_empty.setVisible(not has_rows)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _selected_tenant(self) -> Any | None:
        index = self._tenant_table.currentIndex()
        row = index.row() if index.isValid() else -1
        if row < 0 or row >= len(self._tenants):
            return None
        return self._tenants[row]

    def _on_add_tenant(self) -> None:
        dialog = TenantFormDialog(self._runner, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def _on_edit_tenant(self) -> None:
        tenant = self._selected_tenant()
        if tenant is None:
            return
        dialog = TenantFormDialog(
            self._runner,
            tenant_data={
                "id": tenant.id,
                "full_name": tenant.full_name,
                "phone": str(tenant.phone),
                "alternate_phone": str(tenant.alternate_phone) if tenant.alternate_phone else None,
                "email": tenant.email,
                "address": tenant.address,
                "notes": tenant.notes,
            },
            parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def _on_delete_tenant(self) -> None:
        tenant = self._selected_tenant()
        if tenant is None:
            return
        confirm = ConfirmationDialog(
            "Delete Tenant",
            f"Delete tenant '{tenant.full_name or ''}'? This cannot be undone.",
            parent=self,
            confirm_text="Delete",
            danger=True,
        )
        if confirm.exec() != QDialog.DialogCode.Accepted or not confirm.confirmed:
            return
        result = self._runner.run(
            lambda s: s.tenant().delete_tenant(tenant.id),
            parent=self,
        )
        if result is OPERATION_FAILED:
            return
        self.refresh()

    def _on_open_tenant(self, *_args) -> None:
        tenant = self._selected_tenant()
        if tenant is None:
            return
        self._current_tenant = tenant
        self.refresh_agreements()
        self._stack.setCurrentWidget(self._detail_page)

    def _on_back(self) -> None:
        self._current_tenant = None
        self.refresh()
        self._stack.setCurrentWidget(self._list_page)
