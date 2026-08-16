from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.exceptions import DatabaseError, LMSError
from app.core.logging import get_logger

logger = get_logger(__name__)


class Database:
    def __init__(self, database_url: str, echo: bool = False) -> None:
        self._engine = create_engine(
            database_url,
            echo=echo,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
        )
        self._session_factory = sessionmaker(
            bind=self._engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )
        logger.info("Database engine created", extra={"extra_fields": {"url": database_url.split("@")[-1]}})

    @property
    def engine(self) -> Engine:
        return self._engine

    @property
    def session_factory(self) -> sessionmaker[Session]:
        return self._session_factory

    @contextmanager
    def session(self) -> Generator[Session]:
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except LMSError as e:
            session.rollback()
            logger.warning(
                "Database session rolled back (application error)",
                extra={"extra_fields": {"code": e.code, "message": e.message}},
            )
            raise
        except Exception as e:
            session.rollback()
            logger.exception("Database session error", extra={"extra_fields": {"error": str(e)}})
            raise DatabaseError(f"Database operation failed: {e}") from e
        finally:
            session.close()

    def create_all(self) -> None:
        from app.infrastructure.persistence.base import Base
        Base.metadata.create_all(self._engine)
        logger.info("Database tables created")

    def drop_all(self) -> None:
        from app.infrastructure.persistence.base import Base
        Base.metadata.drop_all(self._engine)
        logger.info("Database tables dropped")


_database: Database | None = None


def get_database() -> Database:
    global _database
    if _database is None:
        settings = get_settings()
        _database = Database(
            database_url=settings.get_database_url(),
            echo=settings.is_development,
        )
    return _database


def init_database(testing: bool = False) -> Database:
    global _database
    settings = get_settings()
    _database = Database(
        database_url=settings.get_database_url(testing=testing),
        echo=settings.is_development and not testing,
    )
    return _database


def close_database() -> None:
    global _database
    if _database is not None:
        _database.engine.dispose()
        _database = None
        logger.info("Database connection closed")
