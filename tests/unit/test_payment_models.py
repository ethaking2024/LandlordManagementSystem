from __future__ import annotations

from app.infrastructure.persistence.base import Base
from app.infrastructure.persistence.models import PaymentAllocationModel, PaymentModel


class TestPaymentModels:
    def test_payments_table_present(self) -> None:
        table_names = {t.name for t in Base.metadata.sorted_tables}
        assert "payments" in table_names
        assert "payment_allocations" in table_names

    def test_payments_columns_and_constraints(self) -> None:
        table = Base.metadata.tables["payments"]
        columns = {c.name for c in table.columns}
        assert {"id", "tenant_id", "payment_date", "amount", "payment_method", "reference", "notes", "status"} <= columns

        constraints = {c.name for c in table.constraints}
        assert "ck_payments_amount_positive" in constraints
        assert "ck_payments_payment_method" in constraints
        assert "ck_payments_status" in constraints

        indexes = {i.name for i in table.indexes}
        assert {"ix_payments_tenant_id", "ix_payments_payment_date", "ix_payments_status"} <= indexes

    def test_payments_foreign_key_to_tenants(self) -> None:
        table = Base.metadata.tables["payments"]
        fk_targets = {fk.target_fullname for fk in table.foreign_keys}
        assert "tenants.id" in fk_targets

    def test_payment_allocations_columns_and_constraints(self) -> None:
        table = Base.metadata.tables["payment_allocations"]
        columns = {c.name for c in table.columns}
        assert {"id", "payment_id", "bill_id", "allocated_amount", "created_at"} <= columns

        constraints = {c.name for c in table.constraints}
        assert "uq_payment_allocations_payment_bill" in constraints
        assert "ck_payment_allocations_amount_positive" in constraints

        indexes = {i.name for i in table.indexes}
        assert {"ix_payment_allocations_payment_id", "ix_payment_allocations_bill_id"} <= indexes

    def test_payment_allocations_foreign_keys(self) -> None:
        table = Base.metadata.tables["payment_allocations"]
        fk_targets = {fk.target_fullname for fk in table.foreign_keys}
        assert "payments.id" in fk_targets
        assert "bills.id" in fk_targets

    def test_models_registered(self) -> None:
        assert PaymentModel.__tablename__ == "payments"
        assert PaymentAllocationModel.__tablename__ == "payment_allocations"
