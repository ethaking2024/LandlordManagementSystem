from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import TypeVar

from sqlalchemy.orm import Session

T = TypeVar("T")


class RepositoryBase[T](ABC):
    def __init__(self, session: Session) -> None:
        self._session = session

    @property
    def session(self) -> Session:
        return self._session

    @abstractmethod
    def add(self, entity: T) -> T:
        raise NotImplementedError

    @abstractmethod
    def get(self, id: uuid.UUID) -> T | None:
        raise NotImplementedError

    @abstractmethod
    def get_all(self, limit: int = 100, offset: int = 0) -> list[T]:
        raise NotImplementedError

    @abstractmethod
    def update(self, entity: T) -> T:
        raise NotImplementedError

    @abstractmethod
    def delete(self, id: uuid.UUID) -> bool:
        raise NotImplementedError
