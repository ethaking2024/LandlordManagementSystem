from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import ValidationError
from app.infrastructure.persistence.models import OwnerModel, PropertyModel
from tests.integration.factories import make_owner


@pytest.mark.integration
def test_commit_persists_data(database, repositories, session):
    owner = repositories.owner.add(make_owner("Committed Owner"))
    session.commit()
    with database.engine.connect() as conn:
        count = conn.execute(
            text("SELECT count(*) FROM owners WHERE name = :name"), {"name": "Committed Owner"}
        ).scalar()
    assert count == 1
    assert owner.id is not None


@pytest.mark.integration
def test_rollback_leaves_no_data(database, session):
    session.add(OwnerModel(name="Rolled Back Owner", phone="9800000001"))
    session.flush()
    session.rollback()

    with database.engine.connect() as conn:
        count = conn.execute(
            text("SELECT count(*) FROM owners WHERE name = :name"), {"name": "Rolled Back Owner"}
        ).scalar()
    assert count == 0


@pytest.mark.integration
def test_database_session_rolls_back_on_application_error(database):
    def _boom() -> None:
        with database.session() as session:
            session.add(OwnerModel(name="Error Owner", phone="9800000001"))
            session.flush()
            raise ValidationError("boom")

    with pytest.raises(ValidationError):
        _boom()

    with database.engine.connect() as conn:
        count = conn.execute(
            text("SELECT count(*) FROM owners WHERE name = :name"), {"name": "Error Owner"}
        ).scalar()
    assert count == 0


@pytest.mark.integration
def test_failed_multi_row_transaction_leaves_no_partial_data(database, session):
    """BEGIN -> insert valid owner -> insert invalid FK row -> ROLLBACK: neither survives."""
    session.add(OwnerModel(name="Second Owner", phone="9800000009"))
    session.flush()

    bad = PropertyModel(owner_id=uuid.uuid4(), name="Ghost Property", address="Nowhere")
    session.add(bad)
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()

    with database.engine.connect() as conn:
        count = conn.execute(
            text("SELECT count(*) FROM owners WHERE name = :name"), {"name": "Second Owner"}
        ).scalar()
    assert count == 0
