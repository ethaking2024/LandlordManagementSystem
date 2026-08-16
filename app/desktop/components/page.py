from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from app.desktop.components.widgets import EmptyState


class Page(QWidget):
    """Base page with a title header and a scrollable content area."""

    def __init__(self, title: str, subtitle: str | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._title = title
        self._subtitle = subtitle

        self._title_label = QLabel(title, self)
        self._title_label.setObjectName("pageTitle")
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignLeft)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 16, 24, 16)
        root.setSpacing(12)

        header = QHBoxLayout()
        header.addWidget(self._title_label)
        header.addStretch()
        root.addLayout(header)

        self._subtitle_label: QLabel | None = None
        if subtitle:
            self._subtitle_label = QLabel(subtitle, self)
            self._subtitle_label.setObjectName("pageSubtitle")
            root.addWidget(self._subtitle_label)

        self._content = QWidget(self)
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(12)
        root.addWidget(self._content, stretch=1)

    @property
    def title(self) -> str:
        return self._title

    @property
    def content_layout(self) -> QVBoxLayout:
        return self._content_layout

    def add_content(self, widget: QWidget) -> None:
        self._content_layout.addWidget(widget)

    def add_content_widget(self, widget: QWidget, stretch: int = 0) -> None:
        self._content_layout.addWidget(widget, stretch)


class PlaceholderPage(Page):
    """A page showing a simple coming-soon message for an unimplemented feature."""

    def __init__(
        self,
        title: str,
        subtitle: str | None = None,
        message: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(title, subtitle, parent)
        empty = EmptyState(
            title="Coming soon",
            message=message or f"{title} will be available in a future release.",
        )
        self._content_layout.addWidget(empty, stretch=1)
