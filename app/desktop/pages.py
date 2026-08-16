from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import QWidget

from app.desktop.components.page import PlaceholderPage
from app.desktop.navigation import NavigationRegistry, NavItem
from app.desktop.property_page import PropertiesPage
from app.desktop.services import ServiceRunner

_DESCRIPTIONS: dict[str, str] = {
    "dashboard": "An overview of your properties, tenants and recent activity.",
    "properties": "Manage your owned properties and their rental spaces.",
    "tenants": "Manage the tenants living in your properties.",
    "agreements": "Manage tenancy agreements and their terms.",
    "billing": "Generate and review bills for rent and utilities.",
    "payments": "Record and track payments from tenants.",
    "deposits": "Manage security deposits and their settlement.",
    "expenses": "Track expenses across your properties.",
    "reports": "Generate reports on your portfolio performance.",
    "settings": "Configure application preferences.",
}

_REAL_PAGES: set[str] = {"properties"}


def build_navigation(runner: ServiceRunner | None = None) -> NavigationRegistry:
    """Build the ordered sidebar navigation registry.

    Pass a ServiceRunner to wire the properties page to the application
    services. Without one, every entry is rendered as a placeholder page.
    """
    items: list[NavItem] = []
    for key in (
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
    ):
        label = key.capitalize()
        description = _DESCRIPTIONS[key]

        factory: Callable[[], QWidget]
        if runner is not None and key in _REAL_PAGES:

            def make_real_page(
                page_label: str = label,
                page_description: str = description,
            ) -> PropertiesPage:
                return PropertiesPage(
                    runner=runner,
                    title=page_label,
                    subtitle=page_description,
                )

            factory = make_real_page
        else:

            def make_page(
                page_label: str = label,
                page_description: str = description,
            ) -> PlaceholderPage:
                return PlaceholderPage(title=page_label, subtitle=page_description)

            factory = make_page

        items.append(
            NavItem(
                key=key,
                label=label,
                subtitle=description,
                page_factory=factory,
            )
        )
    return NavigationRegistry(items)
