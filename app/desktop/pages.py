from __future__ import annotations

from app.desktop.components.page import PlaceholderPage
from app.desktop.navigation import NavigationRegistry, NavItem

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


def build_navigation() -> NavigationRegistry:
    """Build the ordered sidebar navigation registry with placeholder pages."""
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

        def make_page(
            page_label: str = label,
            page_description: str = description,
        ) -> PlaceholderPage:
            return PlaceholderPage(title=page_label, subtitle=page_description)

        items.append(
            NavItem(
                key=key,
                label=label,
                subtitle=description,
                page_factory=make_page,
            )
        )
    return NavigationRegistry(items)
