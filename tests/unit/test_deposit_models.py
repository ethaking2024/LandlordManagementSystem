from __future__ import annotations

from app.infrastructure.persistence.base import Base
from app.infrastructure.persistence.models import (
    DepositDeductionModel,
    DepositModel,
    DepositSettlementModel,
)


class TestDepositModels:
    def test_tables_present(self) -> None:
        table_names = {t.name for t in Base.metadata.sorted_tables}
        assert "deposits" in table_names
        assert "deposit_settlements" in table_names
        assert "deposit_deductions" in table_names

    def test_deposits_columns_and_constraints(self) -> None:
        table = Base.metadata.tables["deposits"]
        columns = {c.name for c in table.columns}
        assert {
            "id",
            "agreement_id",
            "tenant_id",
            "amount",
            "received_date",
            "status",
            "reference",
            "notes",
            "created_at",
            "updated_at",
        } <= columns

        constraints = {c.name for c in table.constraints}
        assert "ck_deposits_amount_positive" in constraints
        assert "ck_deposits_status" in constraints

        indexes = {i.name for i in table.indexes}
        assert {
            "ix_deposits_agreement_id",
            "ix_deposits_tenant_id",
            "ix_deposits_status",
            "ix_deposits_received_date",
        } <= indexes

    def test_deposits_foreign_keys(self) -> None:
        table = Base.metadata.tables["deposits"]
        fk_targets = {fk.target_fullname for fk in table.foreign_keys}
        assert "agreements.id" in fk_targets
        assert "tenants.id" in fk_targets

    def test_deposit_settlements_columns_and_constraints(self) -> None:
        table = Base.metadata.tables["deposit_settlements"]
        columns = {c.name for c in table.columns}
        assert {"id", "deposit_id", "settlement_date", "refund_amount", "notes", "created_at", "updated_at"} <= columns

        constraints = {c.name for c in table.constraints}
        assert "uq_deposit_settlements_deposit" in constraints
        assert "ck_deposit_settlements_refund_non_negative" in constraints

        indexes = {i.name for i in table.indexes}
        assert "ix_deposit_settlements_deposit_id" in indexes

    def test_deposit_settlements_foreign_key(self) -> None:
        table = Base.metadata.tables["deposit_settlements"]
        fk_targets = {fk.target_fullname for fk in table.foreign_keys}
        assert "deposits.id" in fk_targets

    def test_deposit_deductions_columns_and_constraints(self) -> None:
        table = Base.metadata.tables["deposit_deductions"]
        columns = {c.name for c in table.columns}
        assert {"id", "settlement_id", "amount", "reason", "created_at"} <= columns

        constraints = {c.name for c in table.constraints}
        assert "ck_deposit_deductions_amount_positive" in constraints

        indexes = {i.name for i in table.indexes}
        assert "ix_deposit_deductions_settlement_id" in indexes

    def test_deposit_deductions_foreign_key(self) -> None:
        table = Base.metadata.tables["deposit_deductions"]
        fk_targets = {fk.target_fullname for fk in table.foreign_keys}
        assert "deposit_settlements.id" in fk_targets

    def test_models_registered(self) -> None:
        assert DepositModel.__tablename__ == "deposits"
        assert DepositSettlementModel.__tablename__ == "deposit_settlements"
        assert DepositDeductionModel.__tablename__ == "deposit_deductions"
