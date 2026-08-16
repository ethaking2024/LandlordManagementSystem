from __future__ import annotations

import pytest

from app.desktop.main_window import MainWindow
from app.desktop.pages import build_navigation
from app.desktop.property_page import PropertiesPage
from app.desktop.services import ServiceRunner


@pytest.fixture
def main_window(qapp) -> MainWindow:
    return MainWindow()


@pytest.mark.unit
def test_main_window_creation(qapp) -> None:
    window = MainWindow()
    assert window.windowTitle() == "Landlord Management System"
    assert window.current_key == "dashboard"


@pytest.mark.unit
def test_main_window_has_status_bar(main_window: MainWindow) -> None:
    assert main_window.statusBar() is not None
    assert main_window.statusBar().currentMessage() == "Dashboard"


@pytest.mark.unit
def test_navigation_registry_entries(qapp) -> None:
    nav = build_navigation()
    keys = nav.keys()
    assert keys == [
        "dashboard",
        "properties",
        "tenants",
        "agreements",
        "billing",
        "payments",
        "deposits",
        "expenses",
        "reports",
        "settings",
    ]
    assert len(nav) == 10


@pytest.mark.unit
def test_page_switching(main_window: MainWindow) -> None:
    main_window.navigate("properties")
    assert main_window.current_key == "properties"
    assert main_window._stack.currentWidget() is main_window._pages["properties"]


@pytest.mark.unit
def test_navigate_all_pages(main_window: MainWindow) -> None:
    nav = main_window.navigation
    for key in nav.keys():
        main_window.navigate(key)
        assert main_window.current_key == key
        assert main_window._stack.currentWidget() is not None


@pytest.mark.unit
def test_navigate_unknown_key_raises(main_window: MainWindow) -> None:
    with pytest.raises(ValueError, match="Unknown navigation key"):
        main_window.navigate("does_not_exist")


@pytest.mark.unit
def test_pages_cached_on_navigation(main_window: MainWindow) -> None:
    main_window.navigate("properties")
    first = main_window._pages["properties"]
    main_window.navigate("tenants")
    main_window.navigate("properties")
    assert main_window._pages["properties"] is first


@pytest.mark.unit
def test_page_title_updates(main_window: MainWindow) -> None:
    main_window.navigate("billing")
    assert main_window._page_title_label.text() == "Billing"
    assert main_window._page_subtitle_label.text() != ""


@pytest.mark.unit
def test_placeholder_pages_have_coming_soon(main_window: MainWindow) -> None:
    main_window.navigate("payments")
    page = main_window._pages["payments"]
    assert page.title == "Payments"


@pytest.mark.unit
def test_navigation_with_runner_creates_real_properties_page(qapp) -> None:
    from unittest.mock import MagicMock

    database_session = MagicMock()
    runner = ServiceRunner(database_session)
    nav = build_navigation(runner)
    properties_page = nav.get("properties").page_factory()
    assert isinstance(properties_page, PropertiesPage)

    payments_page = nav.get("payments").page_factory()
    assert not isinstance(payments_page, PropertiesPage)


@pytest.mark.unit
def test_main_window_uses_runner(qapp) -> None:
    window = MainWindow()
    assert window.runner is not None
    window.navigate("properties")
    assert isinstance(window._pages["properties"], PropertiesPage)
