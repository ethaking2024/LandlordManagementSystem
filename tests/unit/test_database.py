from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import DatabaseError
from app.infrastructure.database import Database, close_database, init_database


@pytest.mark.unit
def test_database_creation() -> None:
    with patch("app.infrastructure.database.create_engine") as mock_create_engine:
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        db = Database("postgresql+psycopg://user:pass@localhost/db")

        assert db.engine is mock_engine
        assert db.session_factory is not None
        mock_create_engine.assert_called_once()


@pytest.mark.unit
def test_database_session_context_manager() -> None:
    with patch("app.infrastructure.database.create_engine") as mock_create_engine:
        mock_engine = MagicMock()
        mock_session = MagicMock(spec=Session)
        mock_session_factory = MagicMock(return_value=mock_session)
        mock_create_engine.return_value = mock_engine

        db = Database("postgresql+psycopg://user:pass@localhost/db")
        db._session_factory = mock_session_factory

        with db.session() as session:
            assert session is mock_session

        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()


@pytest.mark.unit
def test_database_session_rollback_on_error() -> None:
    with patch("app.infrastructure.database.create_engine") as mock_create_engine:
        mock_engine = MagicMock()
        mock_session = MagicMock(spec=Session)
        mock_session_factory = MagicMock(return_value=mock_session)
        mock_create_engine.return_value = mock_engine

        db = Database("postgresql+psycopg://user:pass@localhost/db")
        db._session_factory = mock_session_factory

        with pytest.raises(DatabaseError):
            with db.session():
                raise ValueError("Test error")

        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()


@pytest.mark.unit
def test_init_database() -> None:
    with patch("app.infrastructure.database.Database") as mock_db_class:
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db

        db = init_database(testing=True)

        assert db is mock_db
        mock_db_class.assert_called_once()


@pytest.mark.unit
def test_close_database() -> None:
    with patch("app.infrastructure.database.Database") as mock_db_class:
        mock_db = MagicMock()
        mock_db_class.return_value = mock_db

        init_database(testing=True)
        close_database()

        mock_db.engine.dispose.assert_called_once()
