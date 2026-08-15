from __future__ import annotations

from datetime import date

import pytest

from app.shared.dates import BSCalendar
from app.shared.dates.bs import BsDate


class TestBSCalendar:
    def test_ad_to_bs_known_anchor(self) -> None:
        assert BSCalendar.ad_to_bs(date(2000, 1, 1)) == BsDate(year=2056, month=9, day=17)

    def test_ad_to_bs_recent_date(self) -> None:
        assert BSCalendar.ad_to_bs(date(2026, 8, 10)) == BsDate(year=2083, month=4, day=25)

    def test_ad_to_bs_round_trip(self) -> None:
        for ad in [date(1944, 1, 1), date(2023, 4, 14), date(2026, 8, 15), date(2030, 12, 31)]:
            bs = BSCalendar.ad_to_bs(ad)
            assert BSCalendar.bs_to_ad(bs.year, bs.month, bs.day) == ad

    def test_bs_to_ad_epoch(self) -> None:
        assert BSCalendar.bs_to_ad(2000, 1, 1) == date(1943, 4, 14)

    def test_bs_to_ad_known_anchor(self) -> None:
        assert BSCalendar.bs_to_ad(2056, 9, 17) == date(2000, 1, 1)

    def test_format_bs(self) -> None:
        assert BSCalendar.format_bs(date(2026, 8, 10)) == "Shrawan 25, 2083"

    def test_format_bs_iso(self) -> None:
        assert BSCalendar.format_bs_iso(date(2026, 8, 10)) == "2083-04-25"

    def test_to_ad_str(self) -> None:
        assert BSCalendar.to_ad_str(date(2024, 1, 1)) == "2024-01-01"

    def test_is_valid_bs(self) -> None:
        assert BSCalendar.is_valid_bs(2083, 4, 25) is True

    def test_is_valid_bs_rejects_invalid_month(self) -> None:
        assert BSCalendar.is_valid_bs(2083, 13, 1) is False

    def test_is_valid_bs_rejects_invalid_day(self) -> None:
        assert BSCalendar.is_valid_bs(2083, 1, 33) is False

    def test_bs_to_ad_rejects_invalid_month(self) -> None:
        with pytest.raises(ValueError, match="Invalid BS date"):
            BSCalendar.bs_to_ad(2083, 13, 1)

    def test_bs_to_ad_rejects_invalid_day(self) -> None:
        with pytest.raises(ValueError, match="Invalid BS date"):
            BSCalendar.bs_to_ad(2083, 1, 33)

    def test_ad_to_bs_rejects_non_date(self) -> None:
        with pytest.raises(ValueError, match="ad_date must be a date"):
            BSCalendar.ad_to_bs("2026-08-10")


class TestBsDate:
    def test_month_name(self) -> None:
        assert BsDate(2083, 4, 25).month_name == "Shrawan"

    def test_to_display_string(self) -> None:
        assert BsDate(2083, 4, 25).to_display_string() == "Shrawan 25, 2083"

    def test_to_iso_string(self) -> None:
        assert BsDate(2083, 4, 25).to_iso_string() == "2083-04-25"

    def test_rejects_invalid_month(self) -> None:
        with pytest.raises(ValueError, match="BS month"):
            BsDate(2083, 13, 1)

    def test_rejects_invalid_day(self) -> None:
        with pytest.raises(ValueError, match="BS day"):
            BsDate(2083, 1, 33)

    def test_rejects_negative_year(self) -> None:
        with pytest.raises(ValueError, match="BS year"):
            BsDate(-1, 1, 1)
