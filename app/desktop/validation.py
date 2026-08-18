from __future__ import annotations

from decimal import Decimal


def is_decimal(text: str) -> bool:
    """Return True when ``text`` parses as a decimal (money-style) value."""
    try:
        Decimal(text)
        return True
    except Exception:
        return False
