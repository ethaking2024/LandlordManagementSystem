from __future__ import annotations

from typing import Any

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QPersistentModelIndex, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QTableView,
    QWidget,
)


class SimpleTableModel(QAbstractTableModel):
    """A minimal read-only table model backed by a list of row tuples."""

    def __init__(
        self,
        headers: list[str],
        rows: list[tuple[str, ...]] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._headers = list(headers)
        self._rows: list[tuple[str, ...]] = list(rows or [])

    def rowCount(self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent: QModelIndex | QPersistentModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._headers)

    def data(
        self,
        index: QModelIndex | QPersistentModelIndex,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if not index.isValid() or role != Qt.ItemDataRole.DisplayRole:
            return None
        return self._rows[index.row()][index.column()]

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return self._headers[section]
        return section + 1

    def set_rows(self, rows: list[tuple[str, ...]]) -> None:
        self.beginResetModel()
        self._rows = list(rows)
        self.endResetModel()

    def clear(self) -> None:
        self.set_rows([])


class DataTableView(QTableView):
    """A read-only table view with consistent selection and header defaults."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setAlternatingRowColors(True)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setShowGrid(True)
        self.setSortingEnabled(False)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setStretchLastSection(True)
        self.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

    def resize_columns_to_contents(self) -> None:
        self.resizeColumnsToContents()
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
