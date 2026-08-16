from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy.orm import Session

from app.application.services import (
    AgreementService,
    BillingService,
    DepositService,
    ExpenseService,
    MeterReadingService,
    MeterReplacementService,
    MeterService,
    OwnerService,
    PaymentService,
    PropertyService,
    RentalSpaceService,
    TenantService,
    UtilityConfigService,
    UtilityTariffService,
)
from app.core.exceptions import LMSError
from app.desktop.error_handler import handle_exception
from app.infrastructure.database import Database
from app.infrastructure.repositories import (
    AgreementRepository,
    BillRepository,
    DepositRepository,
    DepositSettlementRepository,
    ExpenseRepository,
    MeterReadingRepository,
    MeterReplacementRepository,
    MeterRepository,
    OwnerRepository,
    PaymentAllocationRepository,
    PaymentRepository,
    PropertyRepository,
    RentalSpaceRepository,
    TenantRepository,
    UtilityConfigRepository,
    UtilityTariffRepository,
)


class Repositories:
    """All repositories bound to a single session."""

    def __init__(self, session: Session) -> None:
        self.owner = OwnerRepository(session)
        self.property = PropertyRepository(session)
        self.rental_space = RentalSpaceRepository(session)
        self.tenant = TenantRepository(session)
        self.agreement = AgreementRepository(session)
        self.utility_config = UtilityConfigRepository(session)
        self.meter = MeterRepository(session)
        self.meter_reading = MeterReadingRepository(session)
        self.utility_tariff = UtilityTariffRepository(session)
        self.meter_replacement = MeterReplacementRepository(session)
        self.bill = BillRepository(session)
        self.payment = PaymentRepository(session)
        self.payment_allocation = PaymentAllocationRepository(session)
        self.deposit = DepositRepository(session)
        self.deposit_settlement = DepositSettlementRepository(session)
        self.expense = ExpenseRepository(session)


class Services:
    """Application services bound to a session-scoped set of repositories.

    Every service operation runs within the short-lived session provided by
    :meth:`Services.scope`, so no global persistent session is ever introduced.
    """

    def __init__(self, repositories: Repositories) -> None:
        self._repos = repositories

    @property
    def repositories(self) -> Repositories:
        return self._repos

    def owner(self) -> OwnerService:
        return OwnerService(self._repos.owner)

    def property(self) -> PropertyService:
        return PropertyService(self._repos.property, self._repos.owner)

    def rental_space(self) -> RentalSpaceService:
        return RentalSpaceService(self._repos.rental_space, self._repos.property)

    def tenant(self) -> TenantService:
        return TenantService(self._repos.tenant)

    def agreement(self) -> AgreementService:
        return AgreementService(self._repos.agreement, self._repos.tenant, self._repos.rental_space)

    def utility_config(self) -> UtilityConfigService:
        return UtilityConfigService(self._repos.utility_config, self._repos.rental_space)

    def meter(self) -> MeterService:
        return MeterService(self._repos.meter, self._repos.rental_space)

    def meter_reading(self) -> MeterReadingService:
        return MeterReadingService(self._repos.meter_reading, self._repos.meter)

    def utility_tariff(self) -> UtilityTariffService:
        return UtilityTariffService(self._repos.utility_tariff)

    def meter_replacement(self) -> MeterReplacementService:
        return MeterReplacementService(
            self._repos.meter_replacement,
            self._repos.meter,
            self._repos.meter_reading,
        )

    def billing(self) -> BillingService:
        return BillingService(
            self._repos.bill,
            self._repos.agreement,
            self._repos.utility_config,
            self._repos.meter,
            self._repos.meter_reading,
            self._repos.utility_tariff,
        )

    def payment(self) -> PaymentService:
        return PaymentService(
            self._repos.payment,
            self._repos.payment_allocation,
            self._repos.bill,
            self._repos.tenant,
        )

    def deposit(self) -> DepositService:
        return DepositService(
            self._repos.deposit,
            self._repos.deposit_settlement,
            self._repos.agreement,
        )

    def expense(self) -> ExpenseService:
        return ExpenseService(
            self._repos.expense,
            self._repos.property,
            self._repos.rental_space,
        )


class DatabaseSession:
    """Provides a session-scoped Services instance using Database.session().

    A new session is opened on each call; the existing Database commit/rollback
    semantics are preserved and sessions are always closed.
    """

    def __init__(self, database: Database) -> None:
        self._database = database

    @property
    def database(self) -> Database:
        return self._database

    @contextmanager
    def services(self) -> Generator[Services]:
        with self._database.session() as session:
            yield Services(Repositories(session))


def create_database_session(database: Database | None = None) -> DatabaseSession:
    """Create a DatabaseSession, lazily resolving the shared database if needed."""
    if database is not None:
        return DatabaseSession(database)
    from app.infrastructure.database import get_database

    return DatabaseSession(get_database())


class OperationFailed:
    """Sentinel returned by ServiceRunner when an operation raises an exception."""


OPERATION_FAILED = OperationFailed()


class ServiceRunner:
    """Executes service operations within a short-lived session.

    The runner opens a session via the shared Database session model, runs the
    given callable with a session-scoped Services object, and translates any
    exception into a user-friendly dialog using the desktop error handler.
    On failure it returns OPERATION_FAILED so callers can react.
    """

    def __init__(self, database_session: DatabaseSession | None = None) -> None:
        self._database_session = database_session or create_database_session()

    @property
    def database_session(self) -> DatabaseSession:
        return self._database_session

    def run(self, operation, parent=None):
        """Run ``operation(services)`` inside one short-lived session.

        Returns the operation result, or OPERATION_FAILED when an exception was
        raised (the error dialog has already been presented to the user).
        """
        try:
            with self._database_session.services() as services:
                return operation(services)
        except LMSError as exc:
            handle_exception(exc, parent)
        except Exception as exc:  # noqa: BLE001 - translate all UI-facing errors
            handle_exception(exc, parent)
        return OPERATION_FAILED
