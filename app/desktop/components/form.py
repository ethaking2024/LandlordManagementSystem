from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)


class FormField:
    """A single labeled form field with validation message support.

    The validation label lives in a vertical column next to the input widget so
    that it can be shown/hidden without disturbing the row layout.
    """

    def __init__(
        self,
        name: str,
        label: str,
        widget: QWidget,
        *,
        required: bool = False,
        hint: str | None = None,
    ) -> None:
        self.name = name
        self.label = label
        self.widget = widget
        self.required = required

        self._error_label = QLabel()
        self._error_label.setObjectName("validationLabel")
        self._error_label.setWordWrap(True)
        self._error_label.hide()

        self._column = QWidget()
        column_layout = QVBoxLayout(self._column)
        column_layout.setContentsMargins(0, 0, 0, 0)
        column_layout.setSpacing(2)
        column_layout.addWidget(widget)
        column_layout.addWidget(self._error_label)

        if hint:
            hint_label = QLabel(hint)
            hint_label.setObjectName("formHint")
            column_layout.addWidget(hint_label)

    @property
    def input_container(self) -> QWidget:
        """Widget to be placed on the right side of a QFormLayout row."""
        return self._column

    def set_error(self, message: str | None) -> None:
        if message:
            self._error_label.setText(message)
            self._error_label.show()
        else:
            self._error_label.clear()
            self._error_label.hide()


class FormWidget(QWidget):
    """A form layout with labeled fields, hints and validation support."""

    def __init__(self, title: str | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._fields: dict[str, FormField] = {}

        self._title_label: QLabel | None = None
        if title:
            self._title_label = QLabel(title)
            self._title_label.setObjectName("formTitle")

        self._form = QFormLayout()
        self._form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self._form.setHorizontalSpacing(12)
        self._form.setVerticalSpacing(8)
        self._form.setContentsMargins(0, 0, 0, 0)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        if self._title_label:
            layout.addWidget(self._title_label)
        layout.addLayout(self._form)

    @property
    def fields(self) -> dict[str, FormField]:
        return self._fields

    def add_field(
        self,
        name: str,
        label: str,
        widget: QWidget,
        *,
        required: bool = False,
        hint: str | None = None,
    ) -> FormField:
        field = FormField(name, label, widget, required=required, hint=hint)
        self._fields[name] = field
        self._form.addRow(self._build_label(field), field.input_container)
        return field

    def _build_label(self, field: FormField) -> QWidget:
        label = QLabel(field.label)
        label.setObjectName("fieldLabel")
        if not field.required:
            return label
        container = QWidget()
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(2)
        row.addWidget(label)
        marker = QLabel("*")
        marker.setObjectName("requiredMarker")
        row.addWidget(marker)
        row.addStretch()
        return container

    def get_widget(self, name: str) -> QWidget:
        return self._fields[name].widget

    def set_error(self, name: str, message: str | None) -> None:
        self._fields[name].set_error(message)

    def clear_errors(self) -> None:
        for field in self._fields.values():
            field.set_error(None)
