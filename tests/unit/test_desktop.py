from __future__ import annotations

import pytest


@pytest.mark.unit
def test_desktop_module_imports() -> None:
    from app.desktop import main_window
    assert main_window is not None


@pytest.mark.unit
def test_main_module_imports() -> None:
    import app.main
    assert app.main is not None
