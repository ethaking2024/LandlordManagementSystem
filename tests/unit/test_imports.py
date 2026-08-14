from __future__ import annotations

import pytest


@pytest.mark.unit
def test_app_package_imports() -> None:
    import app
    import app.api
    import app.application
    import app.core
    import app.desktop
    import app.domain
    import app.infrastructure
    import app.reports
    import app.shared

    assert app is not None


@pytest.mark.unit
def test_core_modules_import() -> None:
    from app.core import config, exceptions, logging

    assert config is not None
    assert logging is not None
    assert exceptions is not None


@pytest.mark.unit
def test_infrastructure_modules_import() -> None:
    from app.infrastructure import database
    from app.infrastructure.persistence import base

    assert database is not None
    assert base is not None


@pytest.mark.unit
def test_desktop_modules_import() -> None:
    from app.desktop import main_window

    assert main_window is not None
