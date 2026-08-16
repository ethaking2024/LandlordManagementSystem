from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from PySide6.QtWidgets import QWidget


@dataclass(frozen=True)
class NavItem:
    """A single sidebar navigation entry."""

    key: str
    label: str
    page_factory: Callable[[], QWidget]
    subtitle: str | None = None


class NavigationRegistry:
    """Ordered registry of sidebar navigation entries."""

    def __init__(self, items: list[NavItem]) -> None:
        self._items = list(items)
        self._by_key = {item.key: item for item in self._items}

    @property
    def items(self) -> list[NavItem]:
        return list(self._items)

    def keys(self) -> list[str]:
        return [item.key for item in self._items]

    def labels(self) -> list[str]:
        return [item.label for item in self._items]

    def get(self, key: str) -> NavItem:
        return self._by_key[key]

    def contains(self, key: str) -> bool:
        return key in self._by_key

    def index_of(self, key: str) -> int:
        return self.keys().index(key)

    def __len__(self) -> int:
        return len(self._items)
