from __future__ import annotations

import pytest

from app.core.version import RELEASE_LABEL, VERSION, VERSION_INFO


@pytest.mark.unit
def test_version_is_dotted_numeric() -> None:
    parts = VERSION.split(".")
    assert len(parts) == 3
    assert all(part.isdigit() for part in parts)


@pytest.mark.unit
def test_version_info_matches_version() -> None:
    expected = tuple(int(part) for part in VERSION.split(".")) + (0,)
    assert VERSION_INFO == expected


@pytest.mark.unit
def test_release_label_is_non_empty() -> None:
    assert isinstance(RELEASE_LABEL, str)
    assert RELEASE_LABEL
