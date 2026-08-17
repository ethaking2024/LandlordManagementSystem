from __future__ import annotations

import uuid
from typing import Any, cast

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.desktop.components.buttons import PrimaryButton, SecondaryButton
from app.desktop.components.dialogs import BaseDialog
from app.desktop.components.form import FormWidget
from app.desktop.services import OPERATION_FAILED, ServiceRunner
from app.domain.enums import SpaceType


class PropertyFormDialog(BaseDialog):
    """Add or edit a property via PropertyService.

    The owner is selected from a dropdown populated through OwnerService. When no
    suitable owner exists yet, the user can create one inline through the
    lightweight AddOwnerDialog. Business validation is delegated to the service.
    """

    def __init__(
        self,
        runner: ServiceRunner,
        owner_id: uuid.UUID | None = None,
        property_data: dict[str, Any] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        title = "Edit Property" if property_data else "Add Property"
        super().__init__(title, parent=parent)

        self._runner = runner
        self._owner_id = owner_id
        self._property_data = property_data or {}
        self._owners: dict[uuid.UUID, str] = {}
        self._result: Any = None

        form = FormWidget()
        self._owner_combo = QComboBox()
        self._owner_combo.setObjectName("ownerCombo")
        self._add_owner_button = SecondaryButton("+ Add Owner")
        self._add_owner_button.clicked.connect(self._on_add_owner)

        owner_row = QWidget()
        owner_layout = QHBoxLayout(owner_row)
        owner_layout.setContentsMargins(0, 0, 0, 0)
        owner_layout.setSpacing(8)
        owner_layout.addWidget(self._owner_combo, 1)
        owner_layout.addWidget(self._add_owner_button)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("e.g. Shrestha House")
        self._address_edit = QLineEdit()
        self._address_edit.setPlaceholderText("e.g. Thamel, Kathmandu")
        self._notes_edit = QTextEdit()
        self._notes_edit.setMaximumHeight(90)

        form.add_field("owner", "Owner", owner_row, required=True)
        form.add_field("name", "Name", self._name_edit, required=True)
        form.add_field("address", "Address", self._address_edit, required=True)
        form.add_field("notes", "Notes", self._notes_edit)

        self._form = form
        self._insert_form()

        self._cancel_button = SecondaryButton("Cancel")
        self._cancel_button.clicked.connect(self.reject)
        self.add_button(self._cancel_button)

        self._save_button = PrimaryButton("Save")
        self._save_button.setDefault(True)
        self._save_button.clicked.connect(self._on_save)
        self.add_button(self._save_button)

        self._load_owners()
        self._populate_from_data()

    def _insert_form(self) -> None:
        cast(QVBoxLayout, self.layout()).insertWidget(2, self._form)

    def _load_owners(self) -> None:
        result = self._runner.run(lambda services: services.owner().get_all_owners())
        if result is OPERATION_FAILED:
            return
        self._owners = {owner.id: owner.name for owner in result}
        self._owner_combo.clear()
        for owner_id, name in self._owners.items():
            self._owner_combo.addItem(name, owner_id)
        if self._owner_id:
            index = self._owner_combo.findData(self._owner_id)
            if index >= 0:
                self._owner_combo.setCurrentIndex(index)

    def _on_add_owner(self) -> None:
        dialog = AddOwnerDialog(self._runner, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        owner = dialog.created_owner()
        if owner is None:
            return
        self._owners[owner.id] = owner.name
        self._owner_combo.addItem(owner.name, owner.id)
        self._owner_combo.setCurrentIndex(self._owner_combo.count() - 1)

    def _populate_from_data(self) -> None:
        if not self._property_data:
            return
        self._name_edit.setText(self._property_data.get("name", ""))
        self._address_edit.setText(self._property_data.get("address", ""))
        self._notes_edit.setPlainText(self._property_data.get("notes") or "")

    def _on_save(self) -> None:
        self._form.clear_errors()
        name = self._name_edit.text().strip()
        address = self._address_edit.text().strip()

        valid = True
        if self._owner_combo.currentData() is None:
            self._form.set_error("owner", "An owner is required.")
            valid = False
        if not name:
            self._form.set_error("name", "Property name is required.")
            valid = False
        if not address:
            self._form.set_error("address", "Property address is required.")
            valid = False
        if not valid:
            return

        owner_id = self._owner_combo.currentData()
        notes = self._notes_edit.toPlainText().strip() or None
        if self._property_data:
            self._result = self._runner.run(
                lambda s: s.property().update_property(
                    self._property_data["id"], name=name, address=address, notes=notes
                ),
                parent=self,
            )
        else:
            self._result = self._runner.run(
                lambda s: s.property().create_property(
                    owner_id=owner_id, name=name, address=address, notes=notes
                ),
                parent=self,
            )
        if self._result is OPERATION_FAILED:
            return
        self.accept()

    def result_property(self) -> Any:
        return self._result


class RentalSpaceFormDialog(BaseDialog):
    """Add or edit a rental space within a property via RentalSpaceService."""

    _SPACE_TYPE_LABELS: dict[SpaceType, str] = {
        SpaceType.WHOLE_FLOOR: "Whole floor",
        SpaceType.FLAT: "Flat",
        SpaceType.ROOM: "Room",
        SpaceType.ROOM_GROUP: "Room group",
        SpaceType.OTHER: "Other",
    }

    def __init__(
        self,
        runner: ServiceRunner,
        property_id: uuid.UUID,
        space_data: dict[str, Any] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        title = "Edit Rental Space" if space_data else "Add Rental Space"
        super().__init__(title, parent=parent)

        self._runner = runner
        self._property_id = property_id
        self._space_data = space_data or {}
        self._result: Any = None

        form = FormWidget()
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("e.g. Ground Floor, Flat A, Room 1")
        self._type_combo = QComboBox()
        for space_type, label in self._SPACE_TYPE_LABELS.items():
            self._type_combo.addItem(label, space_type)
        self._floor_edit = QLineEdit()
        self._floor_edit.setPlaceholderText("e.g. Ground Floor (optional)")
        self._description_edit = QTextEdit()
        self._description_edit.setMaximumHeight(80)

        form.add_field("name", "Name", self._name_edit, required=True)
        form.add_field("space_type", "Type", self._type_combo)
        form.add_field("floor_label", "Floor / Label", self._floor_edit)
        form.add_field("description", "Description", self._description_edit)

        self._form = form
        self._insert_form()

        cancel = SecondaryButton("Cancel")
        cancel.clicked.connect(self.reject)
        self.add_button(cancel)

        self._save_button = PrimaryButton("Save")
        self._save_button.setDefault(True)
        self._save_button.clicked.connect(self._on_save)
        self.add_button(self._save_button)

        self._populate_from_data()

    def _insert_form(self) -> None:
        cast(QVBoxLayout, self.layout()).insertWidget(2, self._form)

    def _populate_from_data(self) -> None:
        if not self._space_data:
            return
        self._name_edit.setText(self._space_data.get("name", ""))
        space_type = self._space_data.get("space_type")
        if space_type:
            index = self._type_combo.findData(space_type)
            if index >= 0:
                self._type_combo.setCurrentIndex(index)
        self._floor_edit.setText(self._space_data.get("floor_label") or "")
        self._description_edit.setPlainText(self._space_data.get("description") or "")

    def _on_save(self) -> None:
        self._form.clear_errors()
        name = self._name_edit.text().strip()
        space_type = self._type_combo.currentData()

        valid = True
        if not name:
            self._form.set_error("name", "Rental space name is required.")
            valid = False
        if space_type is None:
            self._form.set_error("space_type", "A type is required.")
            valid = False
        if not valid:
            return

        floor_label = self._floor_edit.text().strip() or None
        description = self._description_edit.toPlainText().strip() or None
        space_type_enum = SpaceType(space_type)
        if self._space_data:
            self._result = self._runner.run(
                lambda s: s.rental_space().update_rental_space(
                    self._space_data["id"],
                    name=name,
                    space_type=space_type_enum,
                    floor_label=floor_label,
                    description=description,
                ),
                parent=self,
            )
        else:
            self._result = self._runner.run(
                lambda s: s.rental_space().create_rental_space(
                    property_id=self._property_id,
                    name=name,
                    space_type=space_type_enum,
                    floor_label=floor_label,
                    description=description,
                ),
                parent=self,
            )
        if self._result is OPERATION_FAILED:
            return
        self.accept()

    def result_space(self) -> Any:
        return self._result


class AddOwnerDialog(BaseDialog):
    """Lightweight dialog to create an owner when no suitable one exists."""

    def __init__(self, runner: ServiceRunner, parent: QWidget | None = None) -> None:
        super().__init__("Add Owner", parent=parent)
        self._runner = runner
        self._result: Any = None

        form = FormWidget()
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("Owner name (e.g. Ram Shrestha)")
        self._phone_edit = QLineEdit()
        self._phone_edit.setPlaceholderText("e.g. 9812345678 (optional)")
        self._email_edit = QLineEdit()
        self._email_edit.setPlaceholderText("e.g. owner@example.com (optional)")
        self._address_edit = QLineEdit()
        self._notes_edit = QTextEdit()
        self._notes_edit.setMaximumHeight(80)

        form.add_field("name", "Name", self._name_edit, required=True)
        form.add_field("phone", "Phone", self._phone_edit)
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

    def _on_save(self) -> None:
        self._form.clear_errors()
        name = self._name_edit.text().strip()
        if not name:
            self._form.set_error("name", "Owner name is required.")
            return
        self._result = self._runner.run(
            lambda s: s.owner().create_owner(
                name=name,
                phone=self._phone_edit.text().strip() or None,
                email=self._email_edit.text().strip() or None,
                address=self._address_edit.text().strip() or None,
                notes=self._notes_edit.toPlainText().strip() or None,
            ),
            parent=self,
        )
        if self._result is OPERATION_FAILED:
            return
        self.accept()

    def created_owner(self) -> Any:
        return self._result
