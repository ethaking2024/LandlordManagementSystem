from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class EmptyState(QWidget):
    """A centered placeholder shown when a page or table has no content."""

    def __init__(
        self,
        title: str,
        message: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._title = title
        self._message = message

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 48, 24, 48)
        layout.setSpacing(8)

        self._title_label = QLabel(title, self)
        self._title_label.setObjectName("emptyTitle")
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._message_label = QLabel(message, self)
        self._message_label.setObjectName("emptyMessage")
        self._message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._message_label.setWordWrap(True)

        layout.addStretch()
        layout.addWidget(self._title_label)
        layout.addWidget(self._message_label)
        layout.addStretch()

    @property
    def title(self) -> str:
        return self._title

    @property
    def message(self) -> str:
        return self._message
