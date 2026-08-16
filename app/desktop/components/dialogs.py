from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.desktop.components.buttons import DangerButton, PrimaryButton, SecondaryButton


class BaseDialog(QDialog):
    """Base modal dialog with a title, optional message and a button row."""

    def __init__(
        self,
        title: str,
        message: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(420)

        self._title_label = QLabel(title)
        self._title_label.setObjectName("dialogTitle")

        self._message_label: QLabel | None = None
        if message:
            self._message_label = QLabel(message)
            self._message_label.setObjectName("dialogMessage")
            self._message_label.setWordWrap(True)

        self._button_row = QHBoxLayout()
        self._button_row.addStretch()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(12)
        layout.addWidget(self._title_label)
        if self._message_label:
            layout.addWidget(self._message_label)
        layout.addStretch()
        layout.addLayout(self._button_row)

    def add_button(self, button: QPushButton, stretch: int = 0) -> None:
        self._button_row.addWidget(button, stretch)


class ConfirmationDialog(BaseDialog):
    """A modal confirmation dialog with configurable confirm/cancel buttons."""

    def __init__(
        self,
        title: str,
        message: str,
        parent: QWidget | None = None,
        *,
        confirm_text: str = "Confirm",
        cancel_text: str = "Cancel",
        danger: bool = False,
    ) -> None:
        super().__init__(title, message, parent)

        self._confirmed = False
        self._confirm_button: QPushButton

        cancel = SecondaryButton(cancel_text)
        cancel.clicked.connect(self.reject)

        if danger:
            self._confirm_button = DangerButton(confirm_text)
        else:
            self._confirm_button = PrimaryButton(confirm_text)
        self._confirm_button.setDefault(True)
        self._confirm_button.clicked.connect(self._accept)

        self.add_button(cancel)
        self.add_button(self._confirm_button)

    @property
    def confirmed(self) -> bool:
        return self._confirmed

    def _accept(self) -> None:
        self._confirmed = True
        self.accept()

    def confirm_button(self) -> QPushButton:
        return self._confirm_button
