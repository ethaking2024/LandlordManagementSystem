from __future__ import annotations

import uuid
from typing import Any, cast

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.desktop.components.buttons import PrimaryButton, SecondaryButton
from app.desktop.components.dialogs import BaseDialog
from app.desktop.components.form import FormWidget
from app.desktop.components.table import DataTableView, SimpleTableModel
from app.desktop.dates import format_date_display
from app.desktop.services import OPERATION_FAILED, ServiceRunner


class TenantDetailDialog(BaseDialog):
    """Read-only view of a tenant and their agreements."""

    def __init__(
        self,
        runner: ServiceRunner,
        tenant_id: uuid.UUID,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__("Tenant Details", parent=parent)
        self._runner = runner
        self._tenant_id = tenant_id

        self._details_label = QLabel("")
        self._details_label.setObjectName("dialogMessage")
        self._details_label.setWordWrap(True)
        self._details_label.setTextInteractionFlags(
            self._details_label.textInteractionFlags() | Qt.TextInteractionFlag.TextSelectableByMouse
        )

        self._agreement_model = SimpleTableModel(
            ["Rental Space", "Status", "Start Date", "Monthly Rent"],
            parent=self,
        )
        self._agreement_table = DataTableView()
        self._agreement_table.setModel(self._agreement_model)

        layout = cast(QVBoxLayout, self.layout())
        layout.insertWidget(2, self._details_label)
        layout.insertWidget(3, self._agreement_table)

        close = SecondaryButton("Close")
        close.clicked.connect(self.accept)
        self.add_button(close)

        self._load()

    def _load(self) -> None:
        def _load_data(services) -> tuple[Any, list[tuple[str, ...]]]:
            tenant = services.tenant().get_tenant(self._tenant_id)
            agreements = services.agreement().get_agreements_by_tenant(self._tenant_id)
            rows: list[tuple[str, ...]] = []
            for agreement in agreements:
                space = services.rental_space().get_rental_space(agreement.rental_space_id)
                rows.append(
                    (
                        space.name or "",
                        agreement.status.value.capitalize(),
                        format_date_display(agreement.start_date),
                        str(agreement.monthly_rent),
                    )
                )
            return tenant, rows

        result = self._runner.run(_load_data, parent=self)
        if result is OPERATION_FAILED:
            self._details_label.setText("Could not load tenant details.")
            return
        tenant, rows = result
        lines = [
            f"Name: {tenant.full_name}",
            f"Phone: {tenant.phone}",
        ]
        if tenant.alternate_phone:
            lines.append(f"Alternate Phone: {tenant.alternate_phone}")
        if tenant.email:
            lines.append(f"Email: {tenant.email}")
        if tenant.address:
            lines.append(f"Address: {tenant.address}")
        if tenant.notes:
            lines.append(f"Notes: {tenant.notes}")
        self._details_label.setText("\n".join(lines))
        self._agreement_model.set_rows(rows)
        self._agreement_table.resize_columns_to_contents()


class TenantFormDialog(BaseDialog):
    """Add or edit a tenant via TenantService."""

    def __init__(
        self,
        runner: ServiceRunner,
        tenant_data: dict[str, Any] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        title = "Edit Tenant" if tenant_data else "Add Tenant"
        super().__init__(title, parent=parent)

        self._runner = runner
        self._tenant_data = tenant_data or {}
        self._result: Any = None

        form = FormWidget()
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("e.g. Sita Shrestha")
        self._phone_edit = QLineEdit()
        self._phone_edit.setPlaceholderText("e.g. 9812345678")
        self._alternate_phone_edit = QLineEdit()
        self._alternate_phone_edit.setPlaceholderText("Optional alternate phone")
        self._email_edit = QLineEdit()
        self._email_edit.setPlaceholderText("e.g. sita@example.com (optional)")
        self._address_edit = QLineEdit()
        self._notes_edit = QTextEdit()
        self._notes_edit.setMaximumHeight(80)

        form.add_field("full_name", "Full Name", self._name_edit, required=True)
        form.add_field("phone", "Phone", self._phone_edit, required=True)
        form.add_field("alternate_phone", "Alternate Phone", self._alternate_phone_edit)
        form.add_field("email", "Email", self._email_edit)
        form.add_field("address", "Address", self._address_edit)
        form.add_field("notes", "Notes", self._notes_edit)

        self._form = form
        cast(QVBoxLayout, self.layout()).insertWidget(2, form)

        cancel = SecondaryButton("Cancel")
        cancel.clicked.connect(self.reject)
        self.add_button(cancel)

        self._save_button = PrimaryButton("Save")
        self._save_button.setDefault(True)
        self._save_button.clicked.connect(self._on_save)
        self.add_button(self._save_button)

        self._populate_from_data()

    def _populate_from_data(self) -> None:
        if not self._tenant_data:
            return
        self._name_edit.setText(self._tenant_data.get("full_name", ""))
        self._phone_edit.setText(self._tenant_data.get("phone", ""))
        self._alternate_phone_edit.setText(self._tenant_data.get("alternate_phone") or "")
        self._email_edit.setText(self._tenant_data.get("email") or "")
        self._address_edit.setText(self._tenant_data.get("address") or "")
        self._notes_edit.setPlainText(self._tenant_data.get("notes") or "")

    def _on_save(self) -> None:
        self._form.clear_errors()
        full_name = self._name_edit.text().strip()
        phone = self._phone_edit.text().strip()

        valid = True
        if not full_name:
            self._form.set_error("full_name", "Full name is required.")
            valid = False
        if not phone:
            self._form.set_error("phone", "Phone is required.")
            valid = False
        if not valid:
            return

        if self._tenant_data:
            self._result = self._runner.run(
                lambda s: s.tenant().update_tenant(
                    self._tenant_data["id"],
                    full_name=full_name,
                    phone=phone,
                    alternate_phone=self._alternate_phone_edit.text().strip() or None,
                    email=self._email_edit.text().strip() or None,
                    address=self._address_edit.text().strip() or None,
                    notes=self._notes_edit.toPlainText().strip() or None,
                ),
                parent=self,
            )
        else:
            self._result = self._runner.run(
                lambda s: s.tenant().create_tenant(
                    full_name=full_name,
                    phone=phone,
                    alternate_phone=self._alternate_phone_edit.text().strip() or None,
                    email=self._email_edit.text().strip() or None,
                    address=self._address_edit.text().strip() or None,
                    notes=self._notes_edit.toPlainText().strip() or None,
                ),
                parent=self,
            )
        if self._result is OPERATION_FAILED:
            return
        self.accept()

    def result_tenant(self) -> Any:
        return self._result
