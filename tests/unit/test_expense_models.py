from __future__ import annotations

from app.infrastructure.persistence.base import Base
from app.infrastructure.persistence.models import ExpenseModel


class TestExpenseModels:
    def test_expenses_table_present(self) -> None:
        table_names = {t.name for t in Base.metadata.sorted_tables}
        assert "expenses" in table_names

    def test_expenses_columns_and_constraints(self) -> None:
        table = Base.metadata.tables["expenses"]
        columns = {c.name for c in table.columns}
        assert {
            "id",
            "property_id",
            "rental_space_id",
            "expense_date",
            "category",
            "amount",
            "description",
            "reference",
            "status",
            "created_at",
            "updated_at",
        } <= columns

        constraints = {c.name for c in table.constraints}
        assert "ck_expenses_amount_positive" in constraints
        assert "ck_expenses_category" in constraints
        assert "ck_expenses_status" in constraints

        indexes = {i.name for i in table.indexes}
        assert {
            "ix_expenses_property_id",
            "ix_expenses_rental_space_id",
            "ix_expenses_expense_date",
            "ix_expenses_category",
            "ix_expenses_status",
        } <= indexes

    def test_expenses_foreign_keys(self) -> None:
        table = Base.metadata.tables["expenses"]
        fk_targets = {fk.target_fullname for fk in table.foreign_keys}
        assert "properties.id" in fk_targets
        assert "rental_spaces.id" in fk_targets

    def test_expenses_rental_space_optional(self) -> None:
        table = Base.metadata.tables["expenses"]
        rental_space_column = table.columns["rental_space_id"]
        assert rental_space_column.nullable is True

    def test_models_registered(self) -> None:
        assert ExpenseModel.__tablename__ == "expenses"
