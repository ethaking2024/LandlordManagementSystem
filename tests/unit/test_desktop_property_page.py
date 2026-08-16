from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtWidgets import QDialog

from app.core.exceptions import DatabaseError
from app.desktop.property_page import PropertiesPage
from app.domain.enums import SpaceType


class FakeRunner:
    def __init__(self) -> None:
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
        return operation(services)


def make_property(prop_id: uuid.UUID | None = None, name: str = "Shrestha House"):
    prop = MagicMock()
    prop.id = prop_id or uuid.uuid4()
    prop.name = name
    prop.address = "Thamel, Kathmandu"
    prop.notes = "Notes"
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


@pytest.fixture
def page(qapp) -> tuple[PropertiesPage, FakeRunner]:
    runner = FakeRunner()
    properties_page = PropertiesPage(runner)
    properties_page.show()
    return properties_page, runner


@pytest.mark.unit
def test_refresh_populates_property_table(page) -> None:
    properties_page, runner = page
    prop = make_property()
    space = make_space()
    space.property_id = prop.id
    runner.property.get_all_properties.return_value = [prop]
    runner.rental_space.get_rental_spaces_by_property.return_value = [space]

    properties_page.refresh()

    assert properties_page._property_model.rowCount() == 1
    assert (
        properties_page._property_model.data(properties_page._property_model.index(0, 0))
        == "Shrestha House"
    )
    assert properties_page._property_table.isVisible()


@pytest.mark.unit
def test_refresh_empty_shows_empty_state(page) -> None:
    properties_page, runner = page
    runner.property.get_all_properties.return_value = []

    properties_page.refresh()

    assert properties_page._property_model.rowCount() == 0
    assert properties_page._list_empty.isVisible()


@pytest.mark.unit
def test_open_property_shows_detail(page) -> None:
    properties_page, runner = page
    prop = make_property()
    space = make_space()
    space.property_id = prop.id
    runner.property.get_all_properties.return_value = [prop]
    runner.rental_space.get_rental_spaces_by_property.return_value = [space]
    runner.agreement.is_rental_space_occupied.return_value = True

    properties_page.refresh()
    properties_page._property_table.selectRow(0)
    properties_page._on_open_property()

    assert properties_page._stack.currentWidget() is properties_page._detail_page
    assert properties_page._space_model.rowCount() == 1
    assert properties_page._space_model.data(properties_page._space_model.index(0, 3)) == "Yes"


@pytest.mark.unit
def test_back_returns_to_list(page) -> None:
    properties_page, runner = page
    prop = make_property()
    runner.property.get_all_properties.return_value = [prop]
    runner.rental_space.get_rental_spaces_by_property.return_value = []

    properties_page.refresh()
    properties_page._current_property = prop
    properties_page.refresh_spaces()
    properties_page._on_back()

    assert properties_page._stack.currentWidget() is properties_page._list_page


@pytest.mark.unit
def test_delete_property_calls_service(page) -> None:
    properties_page, runner = page
    prop = make_property()
    runner.property.get_all_properties.return_value = [prop]
    runner.rental_space.get_rental_spaces_by_property.return_value = []
    runner.property.delete_property.return_value = True

    properties_page.refresh()
    properties_page._property_table.selectRow(0)

    import app.desktop.property_page as pp

    fake_confirm = MagicMock()
    fake_confirm.exec.return_value = QDialog.DialogCode.Accepted
    fake_confirm.confirmed = True
    with patch.object(pp, "ConfirmationDialog", return_value=fake_confirm):
        properties_page._on_delete_property()

    runner.property.delete_property.assert_called_once_with(prop.id)


@pytest.mark.unit
def test_add_space_calls_form(page) -> None:
    properties_page, runner = page
    prop = make_property()
    space = make_space()
    space.property_id = prop.id
    runner.property.get_all_properties.return_value = [prop]
    runner.rental_space.get_rental_spaces_by_property.return_value = [space]
    runner.agreement.is_rental_space_occupied.return_value = False

    properties_page.refresh()
    properties_page._current_property = prop

    import app.desktop.property_page as pp

    fake_dialog = MagicMock()
    fake_dialog.exec.return_value = QDialog.DialogCode.Accepted
    with patch.object(pp, "RentalSpaceFormDialog", return_value=fake_dialog):
        properties_page._on_add_space()

    assert properties_page._space_model.rowCount() == 1
    runner.rental_space.get_rental_spaces_by_property.assert_called()


@pytest.mark.unit
def test_constraint_error_message_used_for_delete(page) -> None:
    from app.desktop import error_handler

    class FakeIntegrityError(Exception):
        pass

    error = DatabaseError("Database operation failed: x")
    try:
        raise FakeIntegrityError("fk violation")
    except FakeIntegrityError as cause:
        error.__cause__ = cause
    assert (
        error_handler.user_message(error)
        == "This action could not be completed because related records exist."
    )


@pytest.mark.unit
def test_unknown_space_type_renders_label(page) -> None:
    properties_page, runner = page
    prop = make_property()
    space = make_space()
    space.property_id = prop.id
    space.space_type = SpaceType.OTHER
    runner.property.get_all_properties.return_value = [prop]
    runner.rental_space.get_rental_spaces_by_property.return_value = [space]
    runner.agreement.is_rental_space_occupied.return_value = False

    properties_page.refresh()
    properties_page._current_property = prop
    properties_page.refresh_spaces()

    assert properties_page._space_model.data(properties_page._space_model.index(0, 1)) == "Other"
