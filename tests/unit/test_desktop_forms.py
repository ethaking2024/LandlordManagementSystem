from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import QDialog

from app.desktop.forms import AddOwnerDialog, PropertyFormDialog, RentalSpaceFormDialog
from app.desktop.services import OPERATION_FAILED
from app.domain.enums import SpaceType


class FakeRunner:
    """ServiceRunner stand-in that dispatches to configured fake services.

    Mirrors ServiceRunner behaviour: LMSError is translated (error dialog shown)
    and OPERATION_FAILED returned so the UI keeps the dialog open.
    """

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple, dict]] = []
        self.results: dict[str, Any] = {}
        self.owner = MagicMock()
        self.property = MagicMock()
        self.rental_space = MagicMock()
        self.agreement = MagicMock()

    def run(self, operation, parent=None):
        services = MagicMock()
        services.owner = MagicMock(return_value=self.owner)
        services.property = MagicMock(return_value=self.property)
        services.rental_space = MagicMock(return_value=self.rental_space)
        services.agreement = MagicMock(return_value=self.agreement)
        try:
            return operation(services)
        except Exception:
            return OPERATION_FAILED


def make_owner(owner_id: uuid.UUID | None = None, name: str = "Ram Shrestha"):
    owner = MagicMock()
    owner.id = owner_id or uuid.uuid4()
    owner.name = name
    return owner


def make_property(prop_id: uuid.UUID | None = None, name: str = "Shrestha House"):
    prop = MagicMock()
    prop.id = prop_id or uuid.uuid4()
    prop.name = name
    prop.address = "Thamel, Kathmandu"
    prop.notes = "Notes here"
    prop.owner_id = uuid.uuid4()
    return prop


def make_space(space_id: uuid.UUID | None = None, name: str = "Flat A"):
    space = MagicMock()
    space.id = space_id or uuid.uuid4()
    space.name = name
    space.space_type = SpaceType.FLAT
    space.floor_label = "Ground Floor"
    space.description = ""
    space.property_id = uuid.uuid4()
    return space


@pytest.mark.unit
def test_property_form_dialog_creates_property(qapp) -> None:
    runner = FakeRunner()
    runner.owner.get_all_owners.return_value = [make_owner()]
    created = make_property(name="New House")
    runner.property.create_property.return_value = created

    dialog = PropertyFormDialog(runner)
    dialog._owner_combo.setCurrentIndex(0)
    dialog._name_edit.setText("New House")
    dialog._address_edit.setText("Baneshwor")
    dialog._on_save()

    assert dialog.result() == QDialog.DialogCode.Accepted
    assert dialog.result_property() is created
    runner.property.create_property.assert_called_once()


@pytest.mark.unit
def test_property_form_dialog_validation_blocks_empty(qapp) -> None:
    runner = FakeRunner()
    runner.owner.get_all_owners.return_value = [make_owner()]

    dialog = PropertyFormDialog(runner)
    dialog._on_save()

    assert dialog.result() != QDialog.DialogCode.Accepted
    runner.property.create_property.assert_not_called()


@pytest.mark.unit
def test_property_form_dialog_edit_calls_update(qapp) -> None:
    runner = FakeRunner()
    runner.owner.get_all_owners.return_value = [make_owner()]
    prop = make_property()
    updated = make_property(prop_id=prop.id, name="Renamed")
    runner.property.update_property.return_value = updated

    dialog = PropertyFormDialog(
        runner,
        owner_id=prop.owner_id,
        property_data={"id": prop.id, "name": prop.name, "address": prop.address, "notes": None},
    )
    dialog._name_edit.setText("Renamed")
    dialog._on_save()

    assert dialog.result() == QDialog.DialogCode.Accepted
    runner.property.update_property.assert_called_once()


@pytest.mark.unit
def test_property_form_dialog_service_error_keeps_open(qapp) -> None:
    from app.core.exceptions import ValidationError

    runner = FakeRunner()
    runner.owner.get_all_owners.return_value = [make_owner()]
    runner.property.create_property.side_effect = ValidationError("name too long")

    dialog = PropertyFormDialog(runner)
    dialog._owner_combo.setCurrentIndex(0)
    dialog._name_edit.setText("X")
    dialog._address_edit.setText("Y")
    dialog._on_save()

    assert dialog.result() != QDialog.DialogCode.Accepted


@pytest.mark.unit
def test_add_owner_dialog_creates_owner(qapp) -> None:
    runner = FakeRunner()
    owner = make_owner()
    runner.owner.create_owner.return_value = owner

    dialog = AddOwnerDialog(runner)
    dialog._name_edit.setText("Sita Shrestha")
    dialog._on_save()

    assert dialog.result() == QDialog.DialogCode.Accepted
    assert dialog.created_owner() is owner
    runner.owner.create_owner.assert_called_once()


@pytest.mark.unit
def test_add_owner_dialog_requires_name(qapp) -> None:
    runner = FakeRunner()
    dialog = AddOwnerDialog(runner)
    dialog._on_save()
    assert dialog.result() != QDialog.DialogCode.Accepted
    runner.owner.create_owner.assert_not_called()


@pytest.mark.unit
def test_rental_space_form_dialog_creates_space(qapp) -> None:
    runner = FakeRunner()
    space = make_space()
    runner.rental_space.create_rental_space.return_value = space
    prop_id = uuid.uuid4()

    dialog = RentalSpaceFormDialog(runner, property_id=prop_id)
    dialog._name_edit.setText("Room 1")
    dialog._on_save()

    assert dialog.result() == QDialog.DialogCode.Accepted
    assert dialog.result_space() is space
    runner.rental_space.create_rental_space.assert_called_once()


@pytest.mark.unit
def test_rental_space_form_dialog_edit_updates(qapp) -> None:
    runner = FakeRunner()
    space = make_space()
    runner.rental_space.update_rental_space.return_value = space

    dialog = RentalSpaceFormDialog(
        runner,
        property_id=space.property_id,
        space_data={
            "id": space.id,
            "name": "Old",
            "space_type": SpaceType.ROOM,
            "floor_label": "1",
            "description": "desc",
        },
    )
    dialog._name_edit.setText("New")
    dialog._on_save()

    assert dialog.result() == QDialog.DialogCode.Accepted
    runner.rental_space.update_rental_space.assert_called_once()
