from __future__ import annotations

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication


class AppColors:
    """Central color palette for the desktop application."""

    PRIMARY = "#2f6bff"
    PRIMARY_HOVER = "#2458e6"
    PRIMARY_PRESSED = "#1e4cc9"
    BACKGROUND = "#f5f6f8"
    SURFACE = "#ffffff"
    BORDER = "#d8dbe2"
    TEXT = "#1f2430"
    TEXT_SECONDARY = "#5c6370"
    TEXT_DISABLED = "#9aa0ab"
    SIDEBAR_BACKGROUND = "#1f2430"
    SIDEBAR_TEXT = "#c9ced6"
    SIDEBAR_TEXT_ACTIVE = "#ffffff"
    SIDEBAR_HOVER = "#2b3240"
    SIDEBAR_ACTIVE = "#2f6bff"
    DANGER = "#d64545"
    DANGER_HOVER = "#c43a3a"
    WARNING = "#b8860b"
    SUCCESS = "#2e8b57"


def _base_stylesheet() -> str:
    return f"""
    * {{
        font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
        font-size: 13px;
    }}
    QMainWindow, QWidget {{
        background-color: {AppColors.BACKGROUND};
        color: {AppColors.TEXT};
    }}
    QLabel {{
        background: transparent;
    }}
    QToolTip {{
        background-color: {AppColors.SIDEBAR_BACKGROUND};
        color: {AppColors.SIDEBAR_TEXT};
        border: 1px solid {AppColors.BORDER};
        padding: 4px 8px;
    }}
    """


def _sidebar_stylesheet() -> str:
    return f"""
    QFrame#sidebar {{
        background-color: {AppColors.SIDEBAR_BACKGROUND};
        border: none;
    }}
    QLabel#sidebarTitle {{
        color: {AppColors.SIDEBAR_TEXT_ACTIVE};
        font-size: 16px;
        font-weight: 600;
        padding: 16px 16px 8px 16px;
    }}
    QLabel#sidebarSubtitle {{
        color: {AppColors.SIDEBAR_TEXT};
        font-size: 11px;
        padding: 0 16px 12px 16px;
    }}
    QListWidget#sidebarList {{
        background-color: transparent;
        border: none;
        outline: none;
        padding: 4px;
    }}
    QListWidget#sidebarList::item {{
        color: {AppColors.SIDEBAR_TEXT};
        padding: 10px 12px;
        margin: 2px 4px;
        border-radius: 6px;
    }}
    QListWidget#sidebarList::item:hover {{
        background-color: {AppColors.SIDEBAR_HOVER};
        color: {AppColors.SIDEBAR_TEXT_ACTIVE};
    }}
    QListWidget#sidebarList::item:selected {{
        background-color: {AppColors.SIDEBAR_ACTIVE};
        color: {AppColors.SIDEBAR_TEXT_ACTIVE};
    }}
    QLabel#sidebarVersion {{
        color: {AppColors.SIDEBAR_TEXT};
        font-size: 11px;
        padding: 8px 16px;
    }}
    """


def _content_stylesheet() -> str:
    return f"""
    QFrame#pageHeader {{
        background-color: {AppColors.SURFACE};
        border-bottom: 1px solid {AppColors.BORDER};
    }}
    QLabel#pageTitle {{
        font-size: 20px;
        font-weight: 600;
        color: {AppColors.TEXT};
        padding: 4px 0 0 0;
    }}
    QLabel#pageSubtitle {{
        font-size: 12px;
        color: {AppColors.TEXT_SECONDARY};
        padding: 0 0 4px 0;
    }}
    QStackedWidget#contentStack {{
        background-color: {AppColors.BACKGROUND};
    }}
    QStatusBar {{
        background-color: {AppColors.SURFACE};
        color: {AppColors.TEXT_SECONDARY};
        border-top: 1px solid {AppColors.BORDER};
    }}
    QFrame#pageContainer {{
        background-color: {AppColors.BACKGROUND};
    }}
    QLabel#emptyTitle {{
        font-size: 16px;
        font-weight: 600;
        color: {AppColors.TEXT};
    }}
    QLabel#emptyMessage {{
        font-size: 13px;
        color: {AppColors.TEXT_SECONDARY};
    }}
    """


def _form_stylesheet() -> str:
    return f"""
    QLabel#fieldLabel {{
        color: {AppColors.TEXT};
        font-weight: 600;
    }}
    QLabel#requiredMarker {{
        color: {AppColors.DANGER};
        font-weight: 600;
    }}
    QLabel#validationLabel {{
        color: {AppColors.DANGER};
        font-size: 12px;
    }}
    QLabel#formTitle {{
        font-size: 15px;
        font-weight: 600;
        color: {AppColors.TEXT};
    }}
    QLabel#formHint {{
        font-size: 12px;
        color: {AppColors.TEXT_SECONDARY};
    }}
    """


def _input_stylesheet() -> str:
    return f"""
    QLineEdit, QComboBox, QDateEdit, QTextEdit, QSpinBox, QDoubleSpinBox {{
        background-color: {AppColors.SURFACE};
        color: {AppColors.TEXT};
        border: 1px solid {AppColors.BORDER};
        border-radius: 4px;
        padding: 5px 8px;
        selection-background-color: {AppColors.PRIMARY};
        selection-color: #ffffff;
    }}
    QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QTextEdit:focus,
    QSpinBox:focus, QDoubleSpinBox:focus {{
        border: 1px solid {AppColors.PRIMARY};
    }}
    QLineEdit:disabled, QComboBox:disabled, QDateEdit:disabled, QTextEdit:disabled,
    QSpinBox:disabled, QDoubleSpinBox:disabled {{
        color: {AppColors.TEXT_DISABLED};
        background-color: {AppColors.BACKGROUND};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 24px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {AppColors.SURFACE};
        color: {AppColors.TEXT};
        border: 1px solid {AppColors.BORDER};
        selection-background-color: {AppColors.PRIMARY};
        selection-color: #ffffff;
    }}
    """


def _button_stylesheet() -> str:
    return f"""
    QPushButton#primaryButton {{
        background-color: {AppColors.PRIMARY};
        color: #ffffff;
        border: none;
        border-radius: 4px;
        padding: 6px 16px;
        font-weight: 600;
    }}
    QPushButton#primaryButton:hover {{
        background-color: {AppColors.PRIMARY_HOVER};
    }}
    QPushButton#primaryButton:pressed {{
        background-color: {AppColors.PRIMARY_PRESSED};
    }}
    QPushButton#primaryButton:disabled {{
        background-color: {AppColors.BORDER};
        color: {AppColors.TEXT_DISABLED};
    }}
    QPushButton#secondaryButton {{
        background-color: {AppColors.SURFACE};
        color: {AppColors.TEXT};
        border: 1px solid {AppColors.BORDER};
        border-radius: 4px;
        padding: 5px 15px;
    }}
    QPushButton#secondaryButton:hover {{
        background-color: {AppColors.BACKGROUND};
        border-color: {AppColors.TEXT_SECONDARY};
    }}
    QPushButton#secondaryButton:pressed {{
        background-color: {AppColors.BORDER};
    }}
    QPushButton#dangerButton {{
        background-color: {AppColors.SURFACE};
        color: {AppColors.DANGER};
        border: 1px solid {AppColors.DANGER};
        border-radius: 4px;
        padding: 5px 15px;
    }}
    QPushButton#dangerButton:hover {{
        background-color: {AppColors.DANGER};
        color: #ffffff;
    }}
    QPushButton#iconButton {{
        background-color: transparent;
        color: {AppColors.TEXT_SECONDARY};
        border: none;
        border-radius: 4px;
        padding: 4px 8px;
    }}
    QPushButton#iconButton:hover {{
        background-color: {AppColors.BACKGROUND};
        color: {AppColors.TEXT};
    }}
    """


def _table_stylesheet() -> str:
    return f"""
    QTableView {{
        background-color: {AppColors.SURFACE};
        alternate-background-color: {AppColors.BACKGROUND};
        color: {AppColors.TEXT};
        border: 1px solid {AppColors.BORDER};
        border-radius: 4px;
        gridline-color: {AppColors.BORDER};
        selection-background-color: {AppColors.PRIMARY};
        selection-color: #ffffff;
    }}
    QTableView::item {{
        padding: 4px 6px;
    }}
    QTableView::item:selected {{
        background-color: {AppColors.PRIMARY};
        color: #ffffff;
    }}
    QHeaderView::section {{
        background-color: {AppColors.SURFACE};
        color: {AppColors.TEXT_SECONDARY};
        font-weight: 600;
        border: none;
        border-bottom: 1px solid {AppColors.BORDER};
        border-right: 1px solid {AppColors.BORDER};
        padding: 6px 8px;
    }}
    """


def _dialog_stylesheet() -> str:
    return f"""
    QDialog {{
        background-color: {AppColors.SURFACE};
    }}
    QLabel#dialogTitle {{
        font-size: 16px;
        font-weight: 600;
        color: {AppColors.TEXT};
    }}
    QLabel#dialogMessage {{
        font-size: 13px;
        color: {AppColors.TEXT_SECONDARY};
    }}
    """


def build_stylesheet() -> str:
    """Build the complete application stylesheet."""
    return "".join(
        [
            _base_stylesheet(),
            _sidebar_stylesheet(),
            _content_stylesheet(),
            _form_stylesheet(),
            _input_stylesheet(),
            _button_stylesheet(),
            _table_stylesheet(),
            _dialog_stylesheet(),
        ]
    )


def build_palette() -> QPalette:
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(AppColors.BACKGROUND))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(AppColors.TEXT))
    palette.setColor(QPalette.ColorRole.Base, QColor(AppColors.SURFACE))
    palette.setColor(QPalette.ColorRole.Text, QColor(AppColors.TEXT))
    palette.setColor(QPalette.ColorRole.Button, QColor(AppColors.SURFACE))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(AppColors.TEXT))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(AppColors.PRIMARY))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(AppColors.TEXT_DISABLED))
    return palette


def apply_theme(app: QApplication) -> None:
    """Apply the centralized application theme to a QApplication."""
    app.setStyle("Fusion")
    app.setPalette(build_palette())
    app.setStyleSheet(build_stylesheet())
