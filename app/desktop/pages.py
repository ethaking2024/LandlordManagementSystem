from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import QWidget

from app.desktop.agreement_page import AgreementsPage
from app.desktop.billing_page import BillingPage
from app.desktop.components.page import PlaceholderPage
from app.desktop.deposit_page import DepositsPage
from app.desktop.expense_page import ExpensesPage
from app.desktop.navigation import NavigationRegistry, NavItem
from app.desktop.payment_page import PaymentsPage
from app.desktop.property_page import PropertiesPage
from app.desktop.services import ServiceRunner
from app.desktop.tenant_page import TenantsPage

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

_REAL_PAGES: set[str] = {"properties", "tenants", "agreements", "billing", "payments", "deposits", "expenses"}


def build_navigation(runner: ServiceRunner | None = None) -> NavigationRegistry:
    """Build the ordered sidebar navigation registry.

    Pass a ServiceRunner to wire the properties, tenants and agreements pages to
    the application services. Without one, every entry is a placeholder page.
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
            factory = _make_real_page_factory(key, runner, label, description)
        else:
            factory = _make_placeholder_factory(label, description)

        items.append(
            NavItem(
                key=key,
                label=label,
                subtitle=description,
                page_factory=factory,
            )
        )
    return NavigationRegistry(items)


def _make_real_page_factory(
    key: str,
    runner: ServiceRunner,
    label: str,
    description: str,
) -> Callable[[], QWidget]:
    def factory() -> QWidget:
        if key == "properties":
            return PropertiesPage(runner=runner, title=label, subtitle=description)
        if key == "tenants":
            return TenantsPage(runner=runner, title=label, subtitle=description)
        if key == "agreements":
            return AgreementsPage(runner=runner, title=label, subtitle=description)
        if key == "billing":
            return BillingPage(runner=runner, title=label, subtitle=description)
        if key == "payments":
            return PaymentsPage(runner=runner, title=label, subtitle=description)
        if key == "deposits":
            return DepositsPage(runner=runner, title=label, subtitle=description)
        if key == "expenses":
            return ExpensesPage(runner=runner, title=label, subtitle=description)
        raise ValueError(f"Unhandled real page key: {key}")

    return factory


def _make_placeholder_factory(label: str, description: str) -> Callable[[], QWidget]:
    def factory() -> PlaceholderPage:
        return PlaceholderPage(title=label, subtitle=description)

    return factory
