from __future__ import annotations

import uuid
from typing import Any

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.desktop.components.buttons import PrimaryButton, SecondaryButton
from app.desktop.components.dialogs import ConfirmationDialog
from app.desktop.components.page import Page
from app.desktop.components.table import DataTableView, SimpleTableModel
from app.desktop.components.widgets import EmptyState
from app.desktop.forms import PropertyFormDialog, RentalSpaceFormDialog
from app.desktop.services import OPERATION_FAILED, ServiceRunner
from app.domain.enums import SpaceType

_SPACE_TYPE_LABELS: dict[SpaceType, str] = {
    SpaceType.WHOLE_FLOOR: "Whole floor",
    SpaceType.FLAT: "Flat",
    SpaceType.ROOM: "Room",
    SpaceType.ROOM_GROUP: "Room group",
    SpaceType.OTHER: "Other",
}


class PropertiesPage(Page):
    """Property and rental-space management page.

    Shows a list of properties and lets the user add, edit, open (detail view)
    and delete them. Inside a property, rental spaces can be listed, added,
    edited and deleted. All operations go through the application services via
    the ServiceRunner; occupancy is derived from AgreementService.
    """

    def __init__(
        self,
        runner: ServiceRunner,
        title: str = "Properties",
        subtitle: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(title, subtitle, parent)
        self._runner = runner
        self._properties: list[Any] = []
        self._space_counts: dict[uuid.UUID, int] = {}
        self._current_property: Any = None
        self._spaces: list[Any] = []
        self._occupied: dict[uuid.UUID, bool] = {}

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
        self._add_button = PrimaryButton("Add Property")
        self._add_button.clicked.connect(self._on_add_property)
        self._edit_button = SecondaryButton("Edit")
        self._edit_button.clicked.connect(self._on_edit_property)
        self._open_button = SecondaryButton("Open")
        self._open_button.clicked.connect(self._on_open_property)
        self._delete_button = SecondaryButton("Delete")
        self._delete_button.setObjectName("dangerButton")
        self._delete_button.clicked.connect(self._on_delete_property)
        for button in (
            self._add_button,
            self._edit_button,
            self._open_button,
            self._delete_button,
        ):
            toolbar.addWidget(button)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        self._property_table = DataTableView()
        self._property_model = SimpleTableModel(
            ["Name", "Address", "Notes", "Rental Spaces"],
            parent=self._property_table,
        )
        self._property_table.setModel(self._property_model)
        self._property_table.doubleClicked.connect(self._on_open_property)
        layout.addWidget(self._property_table, stretch=1)

        self._list_empty = EmptyState(
            title="No properties yet",
            message="Add your first property to start managing rental spaces.",
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
        self._back_button = SecondaryButton("Back to Properties")
        self._back_button.clicked.connect(self._on_back)
        header.addWidget(self._back_button)
        header.addStretch()
        layout.addLayout(header)

        self._property_summary = QLabel("")
        self._property_summary.setObjectName("propertySummary")
        self._property_summary.setWordWrap(True)
        layout.addWidget(self._property_summary)

        toolbar = QHBoxLayout()
        self._add_space_button = PrimaryButton("Add Rental Space")
        self._add_space_button.clicked.connect(self._on_add_space)
        self._edit_space_button = SecondaryButton("Edit")
        self._edit_space_button.clicked.connect(self._on_edit_space)
        self._delete_space_button = SecondaryButton("Delete")
        self._delete_space_button.setObjectName("dangerButton")
        self._delete_space_button.clicked.connect(self._on_delete_space)
        for button in (
            self._add_space_button,
            self._edit_space_button,
            self._delete_space_button,
        ):
            toolbar.addWidget(button)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        self._space_table = DataTableView()
        self._space_model = SimpleTableModel(
            ["Name", "Type", "Floor / Label", "Occupied"],
            parent=self._space_table,
        )
        self._space_table.setModel(self._space_model)
        layout.addWidget(self._space_table, stretch=1)

        self._space_empty = EmptyState(
            title="No rental spaces yet",
            message="Add a rental space to this property to start renting it out.",
        )
        layout.addWidget(self._space_empty)

        self._stack.addWidget(self._detail_page)

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def refresh(self) -> None:
        """Reload properties and per-property rental-space counts in one session."""

        def _load(services) -> tuple[list[Any], dict[uuid.UUID, int]]:
            properties = services.property().get_all_properties()
            counts: dict[uuid.UUID, int] = {}
            for prop in properties:
                spaces = services.rental_space().get_rental_spaces_by_property(
                    prop.id, active_only=False
                )
                counts[prop.id] = len(spaces)
            return properties, counts

        result = self._runner.run(_load)
        if result is OPERATION_FAILED:
            return
        self._properties, self._space_counts = result
        self._render_properties()

    def refresh_spaces(self) -> None:
        if self._current_property is None:
            return

        def _load(services) -> tuple[list[Any], dict[uuid.UUID, bool]]:
            spaces = services.rental_space().get_rental_spaces_by_property(
                self._current_property.id, active_only=False
            )
            occupied: dict[uuid.UUID, bool] = {}
            for space in spaces:
                occupied[space.id] = services.agreement().is_rental_space_occupied(space.id)
            return spaces, occupied

        result = self._runner.run(_load)
        if result is OPERATION_FAILED:
            return
        self._spaces, self._occupied = result
        self._render_spaces()

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _render_properties(self) -> None:
        rows: list[tuple[str, ...]] = []
        for prop in self._properties:
            space_count = self._space_counts.get(prop.id, 0)
            rows.append(
                (
                    prop.name or "",
                    prop.address or "",
                    prop.notes or "",
                    str(space_count),
                )
            )
        self._property_model.set_rows(rows)
        self._property_table.resize_columns_to_contents()
        has_rows = bool(rows)
        self._property_table.setVisible(has_rows)
        self._list_empty.setVisible(not has_rows)
        self._edit_button.setEnabled(has_rows)
        self._open_button.setEnabled(has_rows)
        self._delete_button.setEnabled(has_rows)

    def _render_spaces(self) -> None:
        if self._current_property is None:
            return
        self._property_summary.setText(
            f"{self._current_property.name or ''} — {self._current_property.address or ''}"
        )
        rows: list[tuple[str, ...]] = []
        for space in self._spaces:
            occupied = self._occupied.get(space.id, False)
            rows.append(
                (
                    space.name or "",
                    _SPACE_TYPE_LABELS.get(space.space_type, str(space.space_type)),
                    space.floor_label or "",
                    "Yes" if occupied else "No",
                )
            )
        self._space_model.set_rows(rows)
        self._space_table.resize_columns_to_contents()
        has_rows = bool(rows)
        self._space_table.setVisible(has_rows)
        self._space_empty.setVisible(not has_rows)
        self._edit_space_button.setEnabled(has_rows)
        self._delete_space_button.setEnabled(has_rows)

    # ------------------------------------------------------------------
    # Property actions
    # ------------------------------------------------------------------

    def _selected_property(self) -> Any | None:
        index = self._property_table.currentIndex()
        row = index.row() if index.isValid() else -1
        if row < 0 or row >= len(self._properties):
            return None
        return self._properties[row]

    def _on_add_property(self) -> None:
        dialog = PropertyFormDialog(self._runner, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def _on_edit_property(self) -> None:
        prop = self._selected_property()
        if prop is None:
            return
        dialog = PropertyFormDialog(
            self._runner,
            owner_id=prop.owner_id,
            property_data={
                "id": prop.id,
                "name": prop.name,
                "address": prop.address,
                "notes": prop.notes,
            },
            parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def _on_delete_property(self) -> None:
        prop = self._selected_property()
        if prop is None:
            return
        confirm = ConfirmationDialog(
            "Delete Property",
            f"Delete property '{prop.name or ''}'? This cannot be undone.",
            parent=self,
            confirm_text="Delete",
            danger=True,
        )
        if confirm.exec() != QDialog.DialogCode.Accepted or not confirm.confirmed:
            return
        result = self._runner.run(
            lambda s: s.property().delete_property(prop.id),
            parent=self,
        )
        if result is OPERATION_FAILED:
            return
        self.refresh()

    def _on_open_property(self, *_args) -> None:
        prop = self._selected_property()
        if prop is None:
            return
        self._current_property = prop
        self.refresh_spaces()
        self._stack.setCurrentWidget(self._detail_page)

    def _on_back(self) -> None:
        self._current_property = None
        self.refresh()
        self._stack.setCurrentWidget(self._list_page)

    # ------------------------------------------------------------------
    # Rental-space actions
    # ------------------------------------------------------------------

    def _selected_space(self) -> Any | None:
        index = self._space_table.currentIndex()
        row = index.row() if index.isValid() else -1
        if row < 0 or row >= len(self._spaces):
            return None
        return self._spaces[row]

    def _on_add_space(self) -> None:
        if self._current_property is None:
            return
        dialog = RentalSpaceFormDialog(
            self._runner,
            property_id=self._current_property.id,
            parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_spaces()

    def _on_edit_space(self) -> None:
        space = self._selected_space()
        if space is None:
            return
        dialog = RentalSpaceFormDialog(
            self._runner,
            property_id=space.property_id,
            space_data={
                "id": space.id,
                "name": space.name,
                "space_type": space.space_type,
                "floor_label": space.floor_label,
                "description": space.description,
            },
            parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_spaces()

    def _on_delete_space(self) -> None:
        space = self._selected_space()
        if space is None:
            return
        confirm = ConfirmationDialog(
            "Delete Rental Space",
            f"Delete rental space '{space.name or ''}'? This cannot be undone.",
            parent=self,
            confirm_text="Delete",
            danger=True,
        )
        if confirm.exec() != QDialog.DialogCode.Accepted or not confirm.confirmed:
            return
        result = self._runner.run(
            lambda s: s.rental_space().delete_rental_space(space.id),
            parent=self,
        )
        if result is OPERATION_FAILED:
            return
        self.refresh_spaces()
