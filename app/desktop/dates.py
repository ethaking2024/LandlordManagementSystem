from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QLineEdit, QWidget

from app.shared.dates import BSCalendar


def format_date_display(ad_date: date) -> str:
    """Return a compact AD + BS display string for an AD date."""
    ad = ad_date.isoformat()
    bs = BSCalendar.format_bs(ad_date)
    return f"{ad} ({bs})"


def format_bs_display(ad_date: date) -> str:
    """Return only the BS display string for an AD date."""
    return BSCalendar.format_bs(ad_date)


def parse_ad_date(text: str) -> date | None:
    """Parse an AD date string (YYYY-MM-DD) into a date, or None if invalid."""
    text = text.strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


class DateInput(QWidget):
    """A date field that supports entry in both AD and BS calendars.

    The user picks a calendar (AD or BS) and types a date. The widget converts
    between calendars using BSCalendar; the canonical value returned by
    :meth:`value` is always an AD :class:`datetime.date`.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._calendar_combo = QComboBox()
        self._calendar_combo.addItem("AD", "ad")
        self._calendar_combo.addItem("BS", "bs")
        self._calendar_combo.setObjectName("calendarCombo")

        self._date_edit = QLineEdit()
        self._date_edit.setPlaceholderText("YYYY-MM-DD")
        self._date_edit.setObjectName("dateEdit")
        self._date_edit.textChanged.connect(self._on_text_changed)

        self._converted_label = QLabel("")
        self._converted_label.setObjectName("dateHint")
        self._converted_label.setAlignment(Qt.AlignmentFlag.AlignLeft)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(self._calendar_combo)
        layout.addWidget(self._date_edit)
        layout.addWidget(self._converted_label)
        layout.addStretch()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_date(self, ad_date: date) -> None:
        """Set the field to an AD date, showing the BS conversion."""
        self._calendar_combo.setCurrentIndex(0)
        self._date_edit.setText(ad_date.isoformat())
        self._update_converted()

    def value(self) -> date | None:
        """Return the canonical AD date, or None when empty/invalid."""
        text = self._date_edit.text().strip()
        if not text:
            return None
        try:
            if self._calendar_combo.currentData() == "bs":
                return BSCalendar.bs_to_ad(*self._split_bs(text))
            return parse_ad_date(text)
        except ValueError:
            return None

    def is_valid(self) -> bool:
        """Return True when the field is empty or holds a valid date."""
        text = self._date_edit.text().strip()
        if not text:
            return True
        return self.value() is not None

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _split_bs(self, text: str) -> tuple[int, int, int]:
        parts = text.strip().split("-")
        if len(parts) != 3:
            raise ValueError("Invalid BS date")
        return int(parts[0]), int(parts[1]), int(parts[2])

    def _on_text_changed(self, _text: str) -> None:
        self._update_converted()

    def _update_converted(self) -> None:
        try:
            ad = self.value()
        except ValueError:
            self._converted_label.setText("")
            return
        if ad is None:
            self._converted_label.setText("")
            return
        if self._calendar_combo.currentData() == "bs":
            self._converted_label.setText(f"AD: {ad.isoformat()}")
        else:
            self._converted_label.setText(f"BS: {format_bs_display(ad)}")
