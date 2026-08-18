from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QSizePolicy,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from app.desktop.navigation import NavigationRegistry
from app.desktop.pages import build_navigation
from app.desktop.services import DatabaseSession, ServiceRunner


class MainWindow(QMainWindow):
    """The main application window with sidebar navigation and a page stack."""

    def __init__(
        self,
        navigation: NavigationRegistry | None = None,
        database_session: DatabaseSession | None = None,
    ) -> None:
        super().__init__()
        self._runner = ServiceRunner(database_session)
        self._navigation = navigation if navigation is not None else build_navigation(self._runner)
        self._database_session = database_session
        self._pages: dict[str, QWidget] = {}
        self._current_key: str | None = None

        self.setWindowTitle("Landlord Management System")
        self.resize(1100, 720)
        self.setMinimumSize(760, 520)

        self._build_ui()
        self._build_sidebar()
        self._build_status_bar()
        self.navigate(self._navigation.keys()[0])

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)

        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._sidebar = QFrame()
        self._sidebar.setObjectName("sidebar")
        self._sidebar.setFixedWidth(220)
        self._sidebar.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        root.addWidget(self._sidebar)

        self._content = QWidget()
        content_layout = QVBoxLayout(self._content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        self._page_header = QFrame()
        self._page_header.setObjectName("pageHeader")
        header_layout = QVBoxLayout(self._page_header)
        header_layout.setContentsMargins(24, 14, 24, 12)
        header_layout.setSpacing(2)
        self._page_title_label = QLabel("")
        self._page_title_label.setObjectName("pageTitle")
        self._page_subtitle_label = QLabel("")
        self._page_subtitle_label.setObjectName("pageSubtitle")
        header_layout.addWidget(self._page_title_label)
        header_layout.addWidget(self._page_subtitle_label)
        content_layout.addWidget(self._page_header)

        self._stack = QStackedWidget()
        self._stack.setObjectName("contentStack")
        content_layout.addWidget(self._stack, stretch=1)

        root.addWidget(self._content, stretch=1)

    def _build_sidebar(self) -> None:
        layout = QVBoxLayout(self._sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        title = QLabel("Landlord")
        title.setObjectName("sidebarTitle")
        layout.addWidget(title)

        subtitle = QLabel("Management System")
        subtitle.setObjectName("sidebarSubtitle")
        layout.addWidget(subtitle)

        self._sidebar_list = QListWidget()
        self._sidebar_list.setObjectName("sidebarList")
        self._sidebar_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        for item in self._navigation.items:
            list_item = QListWidgetItem(item.label)
            list_item.setData(Qt.ItemDataRole.UserRole, item.key)
            self._sidebar_list.addItem(list_item)
        self._sidebar_list.currentItemChanged.connect(self._on_sidebar_item_changed)
        layout.addWidget(self._sidebar_list, stretch=1)

        version = QLabel("Release 0.8")
        version.setObjectName("sidebarVersion")
        layout.addWidget(version)

    def _build_status_bar(self) -> None:
        status_bar = QStatusBar()
        status_bar.setSizeGripEnabled(False)
        self.setStatusBar(status_bar)

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    @property
    def navigation(self) -> NavigationRegistry:
        return self._navigation

    @property
    def current_key(self) -> str | None:
        return self._current_key

    @property
    def database_session(self) -> DatabaseSession | None:
        return self._database_session

    @property
    def runner(self) -> ServiceRunner:
        return self._runner

    def navigate(self, key: str) -> None:
        """Switch to the page registered under ``key``."""
        if not self._navigation.contains(key):
            raise ValueError(f"Unknown navigation key: {key}")

        page = self._pages.get(key)
        if page is None:
            page = self._navigation.get(key).page_factory()
            self._pages[key] = page
            self._stack.addWidget(page)

        self._stack.setCurrentWidget(page)
        self._current_key = key

        item = self._navigation.get(key)
        self._page_title_label.setText(item.label)
        subtitle = item.subtitle or ""
        self._page_subtitle_label.setText(subtitle)
        self._page_subtitle_label.setVisible(bool(subtitle))

        self._sync_sidebar_selection(key)
        self.statusBar().showMessage(item.label)

    def _sync_sidebar_selection(self, key: str) -> None:
        if not self._navigation.contains(key):
            return
        row = self._navigation.index_of(key)
        current = self._sidebar_list.currentRow()
        if current != row:
            self._sidebar_list.blockSignals(True)
            self._sidebar_list.setCurrentRow(row)
            self._sidebar_list.blockSignals(False)

    def _on_sidebar_item_changed(self, current: QListWidgetItem | None, _previous: QListWidgetItem | None) -> None:
        if current is None:
            return
        key = current.data(Qt.ItemDataRole.UserRole)
        if key != self._current_key:
            self.navigate(key)
