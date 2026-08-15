from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import cast

from nepali_datetime import date as _NepaliDate

# BS month names in English, index 1-based: 1 = Baishakh ... 12 = Chaitra
BS_MONTH_NAMES: tuple[str, ...] = (
    "Baishakh",
    "Jestha",
    "Ashad",
    "Shrawan",
    "Bhadra",
    "Ashwin",
    "Kartik",
    "Mangsir",
    "Poush",
    "Magh",
    "Falgun",
    "Chaitra",
)


@dataclass(frozen=True, slots=True)
class BsDate:
    """An immutable Bikram Sambat calendar date."""

    year: int
    month: int
    day: int

    def __post_init__(self) -> None:
        if self.year < 0:
            raise ValueError("BS year cannot be negative")
        if not 1 <= self.month <= 12:
            raise ValueError("BS month must be between 1 and 12")
        if not 1 <= self.day <= 32:
            raise ValueError("BS day must be between 1 and 32")

    @property
    def month_name(self) -> str:
        return BS_MONTH_NAMES[self.month - 1]

    def to_display_string(self) -> str:
        return f"{self.month_name} {self.day}, {self.year}"

    def to_iso_string(self) -> str:
        return f"{self.year:04d}-{self.month:02d}-{self.day:02d}"

    def __str__(self) -> str:
        return self.to_iso_string()


class BSCalendar:
    """Isolated Bikram Sambat (BS) conversion and display foundation.

    This is the only module that depends directly on a calendar library.
    The rest of the application must use this service instead of importing
    a third-party calendar package.
    """

    @staticmethod
    def ad_to_bs(ad_date: date) -> BsDate:
        if not isinstance(ad_date, date):
            raise ValueError("ad_date must be a date")
        bs = _NepaliDate.from_datetime_date(ad_date)
        return BsDate(year=bs.year, month=bs.month, day=bs.day)

    @staticmethod
    def bs_to_ad(year: int, month: int, day: int) -> date:
        try:
            bs = _NepaliDate(year, month, day)
        except ValueError as exc:
            raise ValueError(f"Invalid BS date: {exc}") from exc
        return cast(date, bs.to_datetime_date())

    @staticmethod
    def format_bs(ad_date: date) -> str:
        """Return the display string (e.g. 'Bhadra 1, 2083') for an AD date."""
        return BSCalendar.ad_to_bs(ad_date).to_display_string()

    @staticmethod
    def format_bs_iso(ad_date: date) -> str:
        """Return the ISO string (e.g. '2083-04-25') for an AD date."""
        return BSCalendar.ad_to_bs(ad_date).to_iso_string()

    @staticmethod
    def is_valid_bs(year: int, month: int, day: int) -> bool:
        try:
            _NepaliDate(year, month, day)
            return True
        except ValueError:
            return False

    @staticmethod
    def to_ad_str(ad_date: date) -> str:
        """Return the AD ISO representation for display (canonical form)."""
        return ad_date.isoformat()
