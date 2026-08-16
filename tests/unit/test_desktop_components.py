from __future__ import annotations

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLineEdit

from app.desktop.components.buttons import DangerButton, PrimaryButton, SecondaryButton
from app.desktop.components.dialogs import ConfirmationDialog
from app.desktop.components.form import FormWidget
from app.desktop.components.page import Page, PlaceholderPage
from app.desktop.components.table import DataTableView, SimpleTableModel
from app.desktop.components.widgets import EmptyState


@pytest.mark.unit
def test_page_creation(qapp) -> None:
    page = Page("Properties", subtitle="Manage properties")
    assert page.title == "Properties"
    assert page.content_layout is not None


@pytest.mark.unit
def test_placeholder_page(qapp) -> None:
    page = PlaceholderPage("Reports", subtitle="reports", message="Coming soon text")
    assert page.title == "Reports"


@pytest.mark.unit
def test_form_widget_add_field(qapp) -> None:
    form = FormWidget(title="New Owner")
    form.add_field("name", "Name", QLineEdit(), required=True)
    form.add_field("phone", "Phone", QLineEdit())
    assert set(form.fields.keys()) == {"name", "phone"}
    assert form.fields["name"].required is True


@pytest.mark.unit
def test_form_widget_validation_message(qapp) -> None:
    form = FormWidget()
    form.add_field("name", "Name", QLineEdit())
    form.show()

    form.set_error("name", "Name is required")
    assert form.fields["name"]._error_label.isVisible()

    form.set_error("name", None)
    assert not form.fields["name"]._error_label.isVisible()

    form.set_error("name", "Again")
    form.clear_errors()
    assert not form.fields["name"]._error_label.isVisible()


@pytest.mark.unit
def test_data_table_view(qapp) -> None:
    table = DataTableView()
    assert table.alternatingRowColors()
    assert not table.isSortingEnabled()


@pytest.mark.unit
def test_simple_table_model_headers_and_rows(qapp) -> None:
    model = SimpleTableModel(["Name", "Address"], [("House A", "Thamel")])
    assert model.rowCount() == 1
    assert model.columnCount() == 2
    assert model.data(model.index(0, 0)) == "House A"
    assert model.data(model.index(0, 1)) == "Thamel"
    assert model.headerData(0, Qt.Orientation.Horizontal) == "Name"
    assert model.data(model.index(5, 5)) is None


@pytest.mark.unit
def test_simple_table_model_set_rows_resets(qapp) -> None:
    model = SimpleTableModel(["Name"])
    assert model.rowCount() == 0
    model.set_rows([("A",), ("B",)])
    assert model.rowCount() == 2
    assert model.data(model.index(1, 0)) == "B"
    model.clear()
    assert model.rowCount() == 0


@pytest.mark.unit
def test_confirmation_dialog_accept_sets_confirmed(qapp) -> None:
    dialog = ConfirmationDialog("Delete?", "Are you sure?")
    dialog._accept()
    assert dialog.confirmed is True
    assert dialog.result() == 1  # Accepted


@pytest.mark.unit
def test_confirmation_dialog_reject_not_confirmed(qapp) -> None:
    dialog = ConfirmationDialog("Delete?", "Are you sure?")
    dialog.reject()
    assert dialog.confirmed is False


@pytest.mark.unit
def test_confirmation_dialog_danger_flag(qapp) -> None:
    dialog = ConfirmationDialog("Delete", "Sure?", danger=True)
    assert dialog.confirm_button().objectName() == "dangerButton"


@pytest.mark.unit
def test_buttons_object_names(qapp) -> None:
    assert PrimaryButton().objectName() == "primaryButton"
    assert SecondaryButton().objectName() == "secondaryButton"
    assert DangerButton().objectName() == "dangerButton"


@pytest.mark.unit
def test_empty_state(qapp) -> None:
    empty = EmptyState("No data", "There is nothing to show")
    assert empty.title == "No data"
    assert empty.message == "There is nothing to show"
