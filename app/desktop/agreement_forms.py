from __future__ import annotations

import uuid
from datetime import date
from typing import Any, cast

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.desktop.components.buttons import PrimaryButton, SecondaryButton
from app.desktop.components.dialogs import BaseDialog, ConfirmationDialog
from app.desktop.components.form import FormWidget
from app.desktop.dates import DateInput, format_date_display
from app.desktop.services import OPERATION_FAILED, ServiceRunner
from app.desktop.tenant_forms import TenantFormDialog
from app.desktop.validation import is_decimal
from app.domain.enums import AgreementStatus


class AgreementFormDialog(BaseDialog):
    """Create or edit an agreement via AgreementService.

    The tenant is selected from a dropdown populated through TenantService; when
    no suitable tenant exists yet, the user can create one inline through the
    lightweight TenantFormDialog. Business rules (overlaps, occupancy, dates)
    are delegated entirely to the service.
    """

    def __init__(
        self,
        runner: ServiceRunner,
        rental_space_id: uuid.UUID | None = None,
        rental_space_label: str | None = None,
        agreement_data: dict[str, Any] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        title = "Edit Agreement" if agreement_data else "Add Agreement"
        super().__init__(title, parent=parent)

        self._runner = runner
        self._rental_space_id = rental_space_id
        self._rental_space_label = rental_space_label or "Selected rental space"
        self._agreement_data = agreement_data or {}
        self._tenants: dict[uuid.UUID, str] = {}
        self._result: Any = None

        form = FormWidget()
        self._tenant_combo = QComboBox()
        self._tenant_combo.setObjectName("tenantCombo")
        self._add_tenant_button = SecondaryButton("+ Add Tenant")
        self._add_tenant_button.clicked.connect(self._on_add_tenant)

        tenant_row = QWidget()
        tenant_layout = QHBoxLayout(tenant_row)
        tenant_layout.setContentsMargins(0, 0, 0, 0)
        tenant_layout.setSpacing(8)
        tenant_layout.addWidget(self._tenant_combo, 1)
        tenant_layout.addWidget(self._add_tenant_button)

        self._space_edit = QLineEdit(self._rental_space_label)
        self._space_edit.setReadOnly(True)

        self._start_input = DateInput()
        self._end_input = DateInput()

        self._rent_edit = QLineEdit()
        self._rent_edit.setPlaceholderText("e.g. 15000 (per month)")
        self._deposit_edit = QLineEdit()
        self._deposit_edit.setPlaceholderText("e.g. 30000 (optional)")
        self._notes_edit = QTextEdit()
        self._notes_edit.setMaximumHeight(80)

        form.add_field("tenant", "Tenant", tenant_row, required=True)
        form.add_field("rental_space", "Rental Space", self._space_edit, required=True)
        form.add_field("start_date", "Start Date", self._start_input)
        form.add_field("end_date", "End Date", self._end_input)
        form.add_field("monthly_rent", "Monthly Rent (NPR)", self._rent_edit, required=True)
        form.add_field("security_deposit", "Security Deposit (NPR)", self._deposit_edit)
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

        self._load_tenants()
        self._populate_from_data()

    def _load_tenants(self) -> None:
        result = self._runner.run(lambda s: s.tenant().get_all_tenants())
        if result is OPERATION_FAILED:
            return
        self._tenants = {tenant.id: tenant.full_name for tenant in result}
        self._tenant_combo.clear()
        for tenant_id, name in self._tenants.items():
            self._tenant_combo.addItem(name, tenant_id)

    def _on_add_tenant(self) -> None:
        dialog = TenantFormDialog(self._runner, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        tenant = dialog.result_tenant()
        if tenant is None:
            return
        self._tenants[tenant.id] = tenant.full_name
        self._tenant_combo.addItem(tenant.full_name, tenant.id)
        self._tenant_combo.setCurrentIndex(self._tenant_combo.count() - 1)

    def _populate_from_data(self) -> None:
        if not self._agreement_data:
            return
        tenant_id = self._agreement_data.get("tenant_id")
        if tenant_id:
            index = self._tenant_combo.findData(tenant_id)
            if index >= 0:
                self._tenant_combo.setCurrentIndex(index)
        start_date = self._agreement_data.get("start_date")
        if isinstance(start_date, date):
            self._start_input.set_date(start_date)
        end_date = self._agreement_data.get("end_date")
        if isinstance(end_date, date):
            self._end_input.set_date(end_date)
        rent = self._agreement_data.get("monthly_rent")
        if rent is not None:
            self._rent_edit.setText(str(rent))
        deposit = self._agreement_data.get("security_deposit")
        if deposit is not None:
            self._deposit_edit.setText(str(deposit))
        self._notes_edit.setPlainText(self._agreement_data.get("notes") or "")

    def _on_save(self) -> None:
        self._form.clear_errors()
        tenant_id = self._tenant_combo.currentData()
        start_date = self._start_input.value()
        rent_text = self._rent_edit.text().strip()

        valid = True
        if tenant_id is None:
            self._form.set_error("tenant", "A tenant is required.")
            valid = False
        if not rent_text:
            self._form.set_error("monthly_rent", "Monthly rent is required.")
            valid = False
        elif not is_decimal(rent_text):
            self._form.set_error("monthly_rent", "Enter a valid amount.")
            valid = False
        if not self._start_input.is_valid():
            self._form.set_error("start_date", "Enter a valid start date.")
            valid = False
        elif start_date is None:
            self._form.set_error("start_date", "Start date is required.")
            valid = False
        if not self._end_input.is_valid():
            self._form.set_error("end_date", "Enter a valid end date.")
            valid = False
        if not valid:
            return

        deposit_text = self._deposit_edit.text().strip() or None
        if deposit_text and not is_decimal(deposit_text):
            self._form.set_error("security_deposit", "Enter a valid amount.")
            return
        end_date = self._end_input.value()
        notes = self._notes_edit.toPlainText().strip() or None

        if self._agreement_data:
            self._result = self._runner.run(
                lambda s: s.agreement().update_agreement(
                    self._agreement_data["id"],
                    monthly_rent=rent_text,
                    security_deposit=deposit_text,
                    notes=notes,
                ),
                parent=self,
            )
        else:
            self._result = self._runner.run(
                lambda s: s.agreement().create_agreement(
                    tenant_id=tenant_id,
                    rental_space_id=self._rental_space_id,
                    start_date=start_date,
                    monthly_rent=rent_text,
                    end_date=end_date,
                    security_deposit=deposit_text,
                    notes=notes,
                ),
                parent=self,
            )
        if self._result is OPERATION_FAILED:
            return
        self.accept()

    def result_agreement(self) -> Any:
        return self._result


class EndAgreementDialog(BaseDialog):
    """Collect the end date for the agreement-end workflow."""

    def __init__(
        self,
        runner: ServiceRunner,
        agreement_data: dict[str, Any],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__("End Agreement", parent=parent)
        self._runner = runner
        self._agreement_data = agreement_data
        self._result: Any = None

        form = FormWidget()
        self._end_input = DateInput()
        start_date = self._agreement_data.get("start_date")
        if isinstance(start_date, date):
            hint = f"Start date: {format_date_display(start_date)}"
        else:
            hint = None
        form.add_field("end_date", "End Date", self._end_input, required=True, hint=hint)

        self._form = form
        cast(QVBoxLayout, self.layout()).insertWidget(2, form)

        cancel = SecondaryButton("Cancel")
        cancel.clicked.connect(self.reject)
        self.add_button(cancel)

        self._end_button = PrimaryButton("End Agreement")
        self._end_button.setDefault(True)
        self._end_button.clicked.connect(self._on_end)
        self.add_button(self._end_button)

    def _on_end(self) -> None:
        self._form.clear_errors()
        if not self._end_input.is_valid():
            self._form.set_error("end_date", "Enter a valid end date.")
            return
        end_date = self._end_input.value()
        if end_date is None:
            self._form.set_error("end_date", "End date is required.")
            return
        self._result = self._runner.run(
            lambda s: s.agreement().end_agreement(self._agreement_data["id"], end_date),
            parent=self,
        )
        if self._result is OPERATION_FAILED:
            return
        self.accept()

    def result_agreement(self) -> Any:
        return self._result


def confirm_cancel_agreement(
    runner: ServiceRunner,
    agreement_id: uuid.UUID,
    label: str,
    parent: QWidget | None = None,
) -> Any:
    """Confirm and cancel an agreement, returning the result or OPERATION_FAILED."""
    confirm = ConfirmationDialog(
        "Cancel Agreement",
        f"Cancel the agreement for '{label}'? This cannot be undone.",
        parent=parent,
        confirm_text="Cancel Agreement",
        danger=True,
    )
    if confirm.exec() != QDialog.DialogCode.Accepted or not confirm.confirmed:
        return None
    return runner.run(lambda s: s.agreement().cancel_agreement(agreement_id), parent=parent)


def format_agreement_status(status: AgreementStatus) -> str:
    return status.value.capitalize()


class AgreementDetailDialog(BaseDialog):
    """Read-only view of an agreement with end/cancel actions."""

    def __init__(
        self,
        runner: ServiceRunner,
        agreement_id: uuid.UUID,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__("Agreement Details", parent=parent)
        self._runner = runner
        self._agreement_id = agreement_id
        self._agreement: Any = None

        self._details_label = QLabel("")
        self._details_label.setObjectName("dialogMessage")
        self._details_label.setWordWrap(True)
        self._details_label.setTextInteractionFlags(
            self._details_label.textInteractionFlags() | Qt.TextInteractionFlag.TextSelectableByMouse
        )

        layout = cast(QVBoxLayout, self.layout())
        layout.insertWidget(2, self._details_label)

        self._end_button = SecondaryButton("End Agreement")
        self._end_button.clicked.connect(self._on_end)
        self._cancel_button = SecondaryButton("Cancel Agreement")
        self._cancel_button.setObjectName("dangerButton")
        self._cancel_button.clicked.connect(self._on_cancel)
        self.add_button(self._cancel_button)
        self.add_button(self._end_button)

        close = SecondaryButton("Close")
        close.clicked.connect(self.accept)
        self.add_button(close)

        self._load()

    def _load(self) -> None:
        def _load_data(services) -> tuple[Any, str, str]:
            agreement = services.agreement().get_agreement(self._agreement_id)
            tenant = services.tenant().get_tenant(agreement.tenant_id)
            space = services.rental_space().get_rental_space(agreement.rental_space_id)
            return agreement, tenant.full_name or "", space.name or ""

        result = self._runner.run(_load_data, parent=self)
        if result is OPERATION_FAILED:
            self._details_label.setText("Could not load agreement details.")
            return
        agreement, tenant_name, space_label = result
        self._agreement = agreement
        self._render(agreement, tenant_name, space_label)

    def _render(self, agreement: Any, tenant_name: str, space_label: str) -> None:
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
        self._details_label.setText("\n".join(lines))

        is_active = agreement.status == AgreementStatus.ACTIVE
        self._end_button.setEnabled(is_active)
        self._cancel_button.setEnabled(is_active)

    def _on_end(self) -> None:
        if self._agreement is None or self._agreement.status != AgreementStatus.ACTIVE:
            return
        dialog = EndAgreementDialog(
            self._runner,
            agreement_data={
                "id": self._agreement.id,
                "start_date": self._agreement.start_date,
            },
            parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._load()

    def _on_cancel(self) -> None:
        if self._agreement is None or self._agreement.status != AgreementStatus.ACTIVE:
            return
        result = confirm_cancel_agreement(
            self._runner,
            self._agreement.id,
            str(self._agreement.rental_space_id),
            parent=self,
        )
        if result is OPERATION_FAILED:
            return
        if result is not None:
            self._load()
