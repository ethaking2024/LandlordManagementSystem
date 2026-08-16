from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.application.services import BillingService
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.domain.entities import (
    Agreement,
    Bill,
    BillLine,
    Meter,
    MeterReading,
    MeterReadingValue,
    UtilityConfig,
    UtilityTariff,
)
from app.domain.enums import AgreementStatus, BillCategory, BillStatus, UtilityType
from app.domain.value_objects import BillingPeriod, Money


def _agreement(rent: str = "20000") -> Agreement:
    return Agreement(
        tenant_id=uuid.uuid4(),
        rental_space_id=uuid.uuid4(),
        start_date=date(2026, 1, 1),
        monthly_rent=Money(Decimal(rent)),
        status=AgreementStatus.ACTIVE,
    )


def _config(utility: UtilityType, config_type: str, fixed_amount: str | None = None) -> UtilityConfig:
    return UtilityConfig(
        rental_space_id=uuid.uuid4(),
        utility_type=utility,
        config_type=config_type,
        fixed_amount=Money(Decimal(fixed_amount)) if fixed_amount else None,
    )


def _meter(utility: UtilityType = UtilityType.ELECTRICITY, identifier: str = "EL-001") -> Meter:
    return Meter(
        rental_space_id=uuid.uuid4(),
        utility_type=utility,
        identifier=identifier,
        installation_date=date(2025, 1, 1),
        is_active=True,
    )


def _reading(meter_id: uuid.UUID, reading_date: date, value: str) -> MeterReading:
    return MeterReading(
        meter_id=meter_id,
        reading_date=reading_date,
        value=MeterReadingValue(Decimal(value)),
    )


def _tariff(utility: UtilityType = UtilityType.ELECTRICITY, rate: str = "12", effective: date = date(2026, 1, 1)) -> UtilityTariff:
    return UtilityTariff(
        utility_type=utility,
        effective_from=effective,
        rate=Money(Decimal(rate)),
    )


class TestGenerateBasicBill:
    @pytest.fixture
    def mock_bill_repo(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def mock_agreement_repo(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def mock_config_repo(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def mock_meter_repo(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def mock_reading_repo(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def mock_tariff_repo(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def service(
        self,
        mock_bill_repo: MagicMock,
        mock_agreement_repo: MagicMock,
        mock_config_repo: MagicMock,
        mock_meter_repo: MagicMock,
        mock_reading_repo: MagicMock,
        mock_tariff_repo: MagicMock,
    ) -> BillingService:
        return BillingService(
            mock_bill_repo,
            mock_agreement_repo,
            mock_config_repo,
            mock_meter_repo,
            mock_reading_repo,
            mock_tariff_repo,
        )

    def test_basic_bill_rent_electricity_water_total(
        self,
        service: BillingService,
        mock_bill_repo: MagicMock,
        mock_agreement_repo: MagicMock,
        mock_config_repo: MagicMock,
    ) -> None:
        agreement = _agreement()
        mock_agreement_repo.get.return_value = agreement
        mock_bill_repo.has_bill_for_period.return_value = False
        mock_bill_repo.add.side_effect = lambda bill: bill
        # electricity fixed 1000, water fixed 500
        mock_config_repo.get_by_rental_space_and_utility.side_effect = [
            _config(UtilityType.ELECTRICITY, "fixed", "1000"),
            _config(UtilityType.WATER, "fixed", "500"),
        ]

        result = service.generate_bill(
            agreement.id,
            date(2026, 1, 1),
            date(2026, 1, 31),
            date(2026, 1, 31),
        )

        rent_line = result.lines[0]
        elec_line = result.lines[1]
        water_line = result.lines[2]

        assert rent_line.amount.amount == Decimal("20000.00")
        assert elec_line.amount.amount == Decimal("1000.00")
        assert water_line.amount.amount == Decimal("500.00")
        assert result.total.amount == Decimal("21500.00")
        mock_bill_repo.add.assert_called_once()

    def test_rent_full_month(self, service: BillingService, mock_agreement_repo: MagicMock, mock_config_repo: MagicMock, mock_bill_repo: MagicMock) -> None:
        agreement = _agreement("20000")
        mock_agreement_repo.get.return_value = agreement
        mock_bill_repo.has_bill_for_period.return_value = False
        mock_bill_repo.add.side_effect = lambda bill: bill
        mock_config_repo.get_by_rental_space_and_utility.side_effect = [
            _config(UtilityType.ELECTRICITY, "fixed", "1000"),
            _config(UtilityType.WATER, "no_charge"),
        ]

        result = service.generate_bill(agreement.id, date(2026, 1, 1), date(2026, 1, 31), date(2026, 1, 31))

        assert result.lines[0].amount.amount == Decimal("20000.00")
        assert result.lines[0].quantity is None

    def test_rent_prorated_partial_month(self, service: BillingService, mock_agreement_repo: MagicMock, mock_config_repo: MagicMock, mock_bill_repo: MagicMock) -> None:
        agreement = _agreement("31000")
        mock_agreement_repo.get.return_value = agreement
        mock_bill_repo.has_bill_for_period.return_value = False
        mock_bill_repo.add.side_effect = lambda bill: bill
        mock_config_repo.get_by_rental_space_and_utility.side_effect = [
            _config(UtilityType.ELECTRICITY, "fixed", "1000"),
            _config(UtilityType.WATER, "no_charge"),
        ]

        # 10 days in a 31-day month: 31000 * 10/31 = 10000.00
        result = service.generate_bill(agreement.id, date(2026, 1, 10), date(2026, 1, 19), date(2026, 1, 19))

        assert result.lines[0].amount.amount == Decimal("10000.00")
        assert result.lines[0].quantity == Decimal("10")

    def test_agreement_not_found(self, service: BillingService, mock_agreement_repo: MagicMock) -> None:
        mock_agreement_repo.get.return_value = None
        with pytest.raises(NotFoundError, match="Agreement"):
            service.generate_bill(uuid.uuid4(), date(2026, 1, 1), date(2026, 1, 31), date(2026, 1, 31))

    def test_period_before_agreement_rejected(self, service: BillingService, mock_agreement_repo: MagicMock) -> None:
        agreement = _agreement()
        agreement.start_date = date(2026, 2, 1)
        mock_agreement_repo.get.return_value = agreement
        with pytest.raises(ValidationError, match="before agreement start"):
            service.generate_bill(agreement.id, date(2026, 1, 1), date(2026, 1, 31), date(2026, 1, 31))

    def test_duplicate_bill_rejected(self, service: BillingService, mock_agreement_repo: MagicMock, mock_bill_repo: MagicMock) -> None:
        agreement = _agreement()
        mock_agreement_repo.get.return_value = agreement
        mock_bill_repo.has_bill_for_period.return_value = True
        with pytest.raises(ConflictError, match="already exists"):
            service.generate_bill(agreement.id, date(2026, 1, 1), date(2026, 1, 31), date(2026, 1, 31))

    def test_missing_electricity_config_rejected(
        self, service: BillingService, mock_agreement_repo: MagicMock, mock_config_repo: MagicMock, mock_bill_repo: MagicMock
    ) -> None:
        agreement = _agreement()
        mock_agreement_repo.get.return_value = agreement
        mock_bill_repo.has_bill_for_period.return_value = False
        mock_config_repo.get_by_rental_space_and_utility.side_effect = [None]
        with pytest.raises(ValidationError, match="No electricity config"):
            service.generate_bill(agreement.id, date(2026, 1, 1), date(2026, 1, 31), date(2026, 1, 31))

    def test_missing_water_config_rejected(
        self, service: BillingService, mock_agreement_repo: MagicMock, mock_config_repo: MagicMock, mock_bill_repo: MagicMock
    ) -> None:
        agreement = _agreement()
        mock_agreement_repo.get.return_value = agreement
        mock_bill_repo.has_bill_for_period.return_value = False
        mock_config_repo.get_by_rental_space_and_utility.side_effect = [
            _config(UtilityType.ELECTRICITY, "fixed", "1000"),
            None,
        ]
        with pytest.raises(ValidationError, match="No water config"):
            service.generate_bill(agreement.id, date(2026, 1, 1), date(2026, 1, 31), date(2026, 1, 31))


class TestMeteredElectricity:
    @pytest.fixture
    def service(self) -> BillingService:
        bill_repo = MagicMock()
        agreement_repo = MagicMock()
        config_repo = MagicMock()
        meter_repo = MagicMock()
        reading_repo = MagicMock()
        tariff_repo = MagicMock()
        return BillingService(bill_repo, agreement_repo, config_repo, meter_repo, reading_repo, tariff_repo)

    def _setup_metered(self, service: BillingService, agreement: Agreement, meter: Meter, readings: list[MeterReading], tariff: UtilityTariff) -> None:
        service._agreement_repository.get.return_value = agreement
        service._bill_repository.has_bill_for_period.return_value = False
        service._bill_repository.add.side_effect = lambda bill: bill
        service._utility_config_repository.get_by_rental_space_and_utility.side_effect = [
            _config(UtilityType.ELECTRICITY, "metered"),
            _config(UtilityType.WATER, "no_charge"),
        ]
        service._meter_repository.get_by_rental_space_and_utility.return_value = [meter]
        service._meter_reading_repository.get_latest_reading_at_or_before.side_effect = readings
        service._utility_tariff_repository.get_applicable_tariff.return_value = tariff

    def test_metered_electricity_consumption_and_tariff(self, service: BillingService) -> None:
        agreement = _agreement()
        meter = _meter(UtilityType.ELECTRICITY, "EL-001")
        readings = [
            _reading(meter.id, date(2025, 12, 31), "1000"),
            _reading(meter.id, date(2026, 1, 31), "1100"),
        ]
        self._setup_metered(service, agreement, meter, readings, _tariff(UtilityType.ELECTRICITY, "12", date(2026, 1, 1)))

        result = service.generate_bill(agreement.id, date(2026, 1, 1), date(2026, 1, 31), date(2026, 1, 31))

        elec_line = result.lines[1]
        assert elec_line.quantity == Decimal("100")
        assert elec_line.amount.amount == Decimal("1200.00")
        assert elec_line.consumption == Decimal("100")
        assert elec_line.previous_reading == Decimal("1000")
        assert elec_line.current_reading == Decimal("1100")
        assert elec_line.meter_identifier == "EL-001"
        assert elec_line.tariff_rate is not None
        assert elec_line.tariff_effective_from == date(2026, 1, 1)
        assert result.total.amount == Decimal("21200.00")

    def test_metered_missing_previous_reading_rejected(self, service: BillingService) -> None:
        agreement = _agreement()
        meter = _meter()
        self._setup_metered(
            service, agreement, meter,
            [None, _reading(meter.id, date(2026, 1, 31), "1100")],
            _tariff(),
        )
        with pytest.raises(ValidationError, match="No previous reading"):
            service.generate_bill(agreement.id, date(2026, 1, 1), date(2026, 1, 31), date(2026, 1, 31))

    def test_metered_missing_current_reading_rejected(self, service: BillingService) -> None:
        agreement = _agreement()
        meter = _meter()
        self._setup_metered(
            service, agreement, meter,
            [_reading(meter.id, date(2025, 12, 31), "1000"), None],
            _tariff(),
        )
        with pytest.raises(ValidationError, match="No current reading"):
            service.generate_bill(agreement.id, date(2026, 1, 1), date(2026, 1, 31), date(2026, 1, 31))

    def test_metered_no_reading_in_period_rejected(self, service: BillingService) -> None:
        agreement = _agreement()
        meter = _meter()
        self._setup_metered(
            service, agreement, meter,
            [
                _reading(meter.id, date(2025, 12, 31), "1000"),
                _reading(meter.id, date(2025, 12, 31), "1000"),
            ],
            _tariff(),
        )
        with pytest.raises(ValidationError, match="No reading found within the billing period"):
            service.generate_bill(agreement.id, date(2026, 1, 1), date(2026, 1, 31), date(2026, 1, 31))

    def test_metered_decreasing_reading_rejected(self, service: BillingService) -> None:
        agreement = _agreement()
        meter = _meter()
        self._setup_metered(
            service, agreement, meter,
            [
                _reading(meter.id, date(2025, 12, 31), "1100"),
                _reading(meter.id, date(2026, 1, 31), "1000"),
            ],
            _tariff(),
        )
        with pytest.raises(ValidationError, match="less than previous"):
            service.generate_bill(agreement.id, date(2026, 1, 1), date(2026, 1, 31), date(2026, 1, 31))

    def test_metered_missing_tariff_rejected(self, service: BillingService) -> None:
        agreement = _agreement()
        meter = _meter()
        self._setup_metered(
            service, agreement, meter,
            [
                _reading(meter.id, date(2025, 12, 31), "1000"),
                _reading(meter.id, date(2026, 1, 31), "1100"),
            ],
            None,
        )
        with pytest.raises(ValidationError, match="No electricity tariff"):
            service.generate_bill(agreement.id, date(2026, 1, 1), date(2026, 1, 31), date(2026, 1, 31))

    def test_metered_no_active_meter_rejected(self, service: BillingService) -> None:
        agreement = _agreement()
        mock_meter_repo = MagicMock()
        service._meter_repository = mock_meter_repo
        mock_meter_repo.get_by_rental_space_and_utility.return_value = []
        service._agreement_repository.get.return_value = agreement
        service._bill_repository.has_bill_for_period.return_value = False
        service._utility_config_repository.get_by_rental_space_and_utility.side_effect = [
            _config(UtilityType.ELECTRICITY, "metered"),
            _config(UtilityType.WATER, "no_charge"),
        ]
        with pytest.raises(ValidationError, match="No active electricity meter"):
            service.generate_bill(agreement.id, date(2026, 1, 1), date(2026, 1, 31), date(2026, 1, 31))


class TestMeteredWater:
    @pytest.fixture
    def service(self) -> BillingService:
        bill_repo = MagicMock()
        agreement_repo = MagicMock()
        config_repo = MagicMock()
        meter_repo = MagicMock()
        reading_repo = MagicMock()
        tariff_repo = MagicMock()
        return BillingService(bill_repo, agreement_repo, config_repo, meter_repo, reading_repo, tariff_repo)

    def test_metered_water_consumption_and_tariff(self, service: BillingService) -> None:
        agreement = _agreement()
        meter = _meter(UtilityType.WATER, "WT-001")
        service._agreement_repository.get.return_value = agreement
        service._bill_repository.has_bill_for_period.return_value = False
        service._bill_repository.add.side_effect = lambda bill: bill
        service._utility_config_repository.get_by_rental_space_and_utility.side_effect = [
            _config(UtilityType.ELECTRICITY, "fixed", "1000"),
            _config(UtilityType.WATER, "metered"),
        ]
        service._meter_repository.get_by_rental_space_and_utility.return_value = [meter]
        service._meter_reading_repository.get_latest_reading_at_or_before.side_effect = [
            _reading(meter.id, date(2025, 12, 31), "100"),
            _reading(meter.id, date(2026, 1, 31), "200"),
        ]
        service._utility_tariff_repository.get_applicable_tariff.return_value = _tariff(UtilityType.WATER, "50", date(2026, 1, 1))

        result = service.generate_bill(agreement.id, date(2026, 1, 1), date(2026, 1, 31), date(2026, 1, 31))

        water_line = result.lines[2]
        assert water_line.quantity == Decimal("100")
        assert water_line.amount.amount == Decimal("5000.00")
        assert water_line.meter_identifier == "WT-001"


class TestHistoricalSnapshot:
    @pytest.fixture
    def service(self) -> BillingService:
        bill_repo = MagicMock()
        agreement_repo = MagicMock()
        config_repo = MagicMock()
        meter_repo = MagicMock()
        reading_repo = MagicMock()
        tariff_repo = MagicMock()
        return BillingService(bill_repo, agreement_repo, config_repo, meter_repo, reading_repo, tariff_repo)

    def test_snapshot_does_not_change_after_rent_tariff_config_change(self, service: BillingService) -> None:
        agreement = _agreement("20000")
        # Bill generated with rent=20000, elec fixed=1000, water fixed=500
        service._agreement_repository.get.return_value = agreement
        service._bill_repository.has_bill_for_period.return_value = False
        service._bill_repository.add.side_effect = lambda bill: bill
        service._utility_config_repository.get_by_rental_space_and_utility.side_effect = [
            _config(UtilityType.ELECTRICITY, "fixed", "1000"),
            _config(UtilityType.WATER, "fixed", "500"),
        ]

        bill = service.generate_bill(
            agreement.id,
            date(2026, 1, 1),
            date(2026, 1, 31),
            date(2026, 1, 31),
        )

        # The bill lines carry their own amounts regardless of any later changes to
        # the agreement rent, electricity tariff, or water configuration.
        rent_line = next(line for line in bill.lines if line.category == BillCategory.RENT)
        elec_line = next(line for line in bill.lines if line.category == BillCategory.ELECTRICITY)
        water_line = next(line for line in bill.lines if line.category == BillCategory.WATER)

        assert rent_line.amount.amount == Decimal("20000.00")
        assert elec_line.amount.amount == Decimal("1000.00")
        assert water_line.amount.amount == Decimal("500.00")
        assert bill.total.amount == Decimal("21500.00")

        # Even after the agreement rent is raised, the stored bill is unchanged.
        agreement.monthly_rent = Money(Decimal("22000"))
        assert rent_line.amount.amount == Decimal("20000.00")

    def test_metered_snapshot_preserves_meter_history(self, service: BillingService) -> None:
        agreement = _agreement()
        meter = _meter(UtilityType.ELECTRICITY, "EL-001")
        service._agreement_repository.get.return_value = agreement
        service._bill_repository.has_bill_for_period.return_value = False
        service._bill_repository.add.side_effect = lambda bill: bill
        service._utility_config_repository.get_by_rental_space_and_utility.side_effect = [
            _config(UtilityType.ELECTRICITY, "metered"),
            _config(UtilityType.WATER, "no_charge"),
        ]
        service._meter_repository.get_by_rental_space_and_utility.return_value = [meter]
        service._meter_reading_repository.get_latest_reading_at_or_before.side_effect = [
            _reading(meter.id, date(2025, 12, 31), "1000"),
            _reading(meter.id, date(2026, 1, 31), "1100"),
        ]
        service._utility_tariff_repository.get_applicable_tariff.return_value = _tariff(UtilityType.ELECTRICITY, "12", date(2026, 1, 1))

        bill = service.generate_bill(agreement.id, date(2026, 1, 1), date(2026, 1, 31), date(2026, 1, 31))

        elec_line = next(line for line in bill.lines if line.category == BillCategory.ELECTRICITY)
        # The meter readings and tariff used at generation time remain explainable.
        assert elec_line.previous_reading == Decimal("1000")
        assert elec_line.current_reading == Decimal("1100")
        assert elec_line.consumption == Decimal("100")
        assert elec_line.tariff_rate.amount == Decimal("12.00")
        assert elec_line.amount.amount == Decimal("1200.00")


class TestLifecycle:
    @pytest.fixture
    def mock_bill_repo(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def service(self, mock_bill_repo: MagicMock) -> BillingService:
        return BillingService(
            mock_bill_repo,
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
            MagicMock(),
        )

    def _draft_bill(self) -> Bill:
        return Bill(
            agreement_id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            rental_space_id=uuid.uuid4(),
            period=BillingPeriod(date(2026, 1, 1), date(2026, 1, 31)),
            billing_date=date(2026, 1, 31),
            lines=[
                BillLine(category=BillCategory.RENT, description="rent", amount=Money(Decimal("20000"))),
            ],
        )

    def test_confirm_draft(self, service: BillingService, mock_bill_repo: MagicMock) -> None:
        bill = self._draft_bill()
        mock_bill_repo.get.return_value = bill
        mock_bill_repo.update.return_value = bill

        result = service.confirm_bill(bill.id)

        assert result.status == BillStatus.CONFIRMED
        mock_bill_repo.update.assert_called_once()

    def test_confirm_confirmed_rejected(self, service: BillingService, mock_bill_repo: MagicMock) -> None:
        bill = self._draft_bill()
        bill.status = BillStatus.CONFIRMED
        mock_bill_repo.get.return_value = bill
        with pytest.raises(ValidationError, match="Cannot confirm"):
            service.confirm_bill(bill.id)

    def test_confirm_empty_lines_rejected(self, service: BillingService, mock_bill_repo: MagicMock) -> None:
        bill = Bill(
            agreement_id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            rental_space_id=uuid.uuid4(),
            period=BillingPeriod(date(2026, 1, 1), date(2026, 1, 31)),
            billing_date=date(2026, 1, 31),
        )
        mock_bill_repo.get.return_value = bill
        with pytest.raises(ValidationError, match="without line items"):
            service.confirm_bill(bill.id)

    def test_void_bill(self, service: BillingService, mock_bill_repo: MagicMock) -> None:
        bill = self._draft_bill()
        mock_bill_repo.get.return_value = bill
        mock_bill_repo.update.return_value = bill

        result = service.void_bill(bill.id)

        assert result.status == BillStatus.VOID

    def test_void_confirmed_bill_allowed(self, service: BillingService, mock_bill_repo: MagicMock) -> None:
        bill = self._draft_bill()
        bill.status = BillStatus.CONFIRMED
        mock_bill_repo.get.return_value = bill
        mock_bill_repo.update.return_value = bill

        result = service.void_bill(bill.id)

        assert result.status == BillStatus.VOID

    def test_delete_confirmed_rejected(self, service: BillingService, mock_bill_repo: MagicMock) -> None:
        bill = self._draft_bill()
        bill.status = BillStatus.CONFIRMED
        mock_bill_repo.get.return_value = bill
        with pytest.raises(ValidationError, match="Cannot delete"):
            service.delete_bill(bill.id)

    def test_delete_draft_allowed(self, service: BillingService, mock_bill_repo: MagicMock) -> None:
        bill = self._draft_bill()
        mock_bill_repo.get.return_value = bill
        mock_bill_repo.delete.return_value = True

        result = service.delete_bill(bill.id)

        assert result is True
        mock_bill_repo.delete.assert_called_once_with(bill.id)


class TestTransactionAndMoney:
    @pytest.fixture
    def mock_bill_repo(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def mock_agreement_repo(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def mock_config_repo(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def mock_meter_repo(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def mock_reading_repo(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def mock_tariff_repo(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def service(
        self,
        mock_bill_repo: MagicMock,
        mock_agreement_repo: MagicMock,
        mock_config_repo: MagicMock,
        mock_meter_repo: MagicMock,
        mock_reading_repo: MagicMock,
        mock_tariff_repo: MagicMock,
    ) -> BillingService:
        return BillingService(
            mock_bill_repo,
            mock_agreement_repo,
            mock_config_repo,
            mock_meter_repo,
            mock_reading_repo,
            mock_tariff_repo,
        )

    def test_failed_billing_persists_nothing(
        self,
        service: BillingService,
        mock_bill_repo: MagicMock,
        mock_agreement_repo: MagicMock,
        mock_config_repo: MagicMock,
        mock_meter_repo: MagicMock,
        mock_reading_repo: MagicMock,
    ) -> None:
        agreement = _agreement()
        mock_agreement_repo.get.return_value = agreement
        mock_bill_repo.has_bill_for_period.return_value = False
        mock_config_repo.get_by_rental_space_and_utility.side_effect = [
            _config(UtilityType.ELECTRICITY, "metered"),
            _config(UtilityType.WATER, "no_charge"),
        ]
        mock_meter_repo.get_by_rental_space_and_utility.return_value = [_meter()]
        # A failure occurs while resolving the current reading.
        mock_reading_repo.get_latest_reading_at_or_before.side_effect = [
            _reading(uuid.uuid4(), date(2025, 12, 31), "1000"),
            None,
        ]

        with pytest.raises(ValidationError, match="No current reading"):
            service.generate_bill(agreement.id, date(2026, 1, 1), date(2026, 1, 31), date(2026, 1, 31))

        # No bill and no lines were committed: the operation is atomic.
        mock_bill_repo.add.assert_not_called()

    def test_decimal_money_no_float(self, service: BillingService, mock_agreement_repo: MagicMock, mock_bill_repo: MagicMock, mock_config_repo: MagicMock) -> None:
        agreement = _agreement("20000")
        mock_agreement_repo.get.return_value = agreement
        mock_bill_repo.has_bill_for_period.return_value = False
        mock_bill_repo.add.side_effect = lambda bill: bill
        mock_config_repo.get_by_rental_space_and_utility.side_effect = [
            _config(UtilityType.ELECTRICITY, "fixed", "1000"),
            _config(UtilityType.WATER, "no_charge"),
        ]

        result = service.generate_bill(agreement.id, date(2026, 1, 1), date(2026, 1, 31), date(2026, 1, 31))

        assert isinstance(result.lines[0].amount.amount, Decimal)
        assert isinstance(result.lines[1].amount.amount, Decimal)
        assert isinstance(result.total.amount, Decimal)
        assert result.total.amount == Decimal("21000.00")

    def test_rounding_on_prorated_rent(self, service: BillingService, mock_agreement_repo: MagicMock, mock_bill_repo: MagicMock, mock_config_repo: MagicMock) -> None:
        agreement = _agreement("20000")
        mock_agreement_repo.get.return_value = agreement
        mock_bill_repo.has_bill_for_period.return_value = False
        mock_bill_repo.add.side_effect = lambda bill: bill
        mock_config_repo.get_by_rental_space_and_utility.side_effect = [
            _config(UtilityType.ELECTRICITY, "fixed", "1000"),
            _config(UtilityType.WATER, "no_charge"),
        ]

        # 20,000 * 17/31 = 10967.7419... -> 10967.74
        result = service.generate_bill(agreement.id, date(2026, 1, 15), date(2026, 1, 31), date(2026, 1, 31))

        assert result.lines[0].amount.amount == Decimal("10967.74")
        assert result.lines[0].amount.amount == result.lines[0].amount.amount.quantize(Decimal("0.01"))


class TestGetAllBills:
    @pytest.fixture
    def mock_bill_repo(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def mock_agreement_repo(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def mock_config_repo(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def mock_meter_repo(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def mock_reading_repo(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def mock_tariff_repo(self) -> MagicMock:
        return MagicMock()

    @pytest.fixture
    def service(
        self,
        mock_bill_repo: MagicMock,
        mock_agreement_repo: MagicMock,
        mock_config_repo: MagicMock,
        mock_meter_repo: MagicMock,
        mock_reading_repo: MagicMock,
        mock_tariff_repo: MagicMock,
    ) -> BillingService:
        return BillingService(
            mock_bill_repo,
            mock_agreement_repo,
            mock_config_repo,
            mock_meter_repo,
            mock_reading_repo,
            mock_tariff_repo,
        )

    def test_get_all_bills_delegates_to_repository(
        self,
        service: BillingService,
        mock_bill_repo: MagicMock,
    ) -> None:
        bill = Bill(
            agreement_id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            rental_space_id=uuid.uuid4(),
            period=BillingPeriod(date(2026, 1, 1), date(2026, 1, 31)),
            billing_date=date(2026, 1, 31),
            status=BillStatus.DRAFT,
        )
        mock_bill_repo.get_all.return_value = [bill]

        result = service.get_all_bills()

        mock_bill_repo.get_all.assert_called_once_with(limit=100, offset=0)
        assert result == [bill]

    def test_get_all_bills_empty(self, service: BillingService, mock_bill_repo: MagicMock) -> None:
        mock_bill_repo.get_all.return_value = []

        result = service.get_all_bills()

        assert result == []

    def test_get_bills_by_billing_date_range_delegates_to_repository(
        self,
        service: BillingService,
        mock_bill_repo: MagicMock,
    ) -> None:
        bill = Bill(
            agreement_id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            rental_space_id=uuid.uuid4(),
            period=BillingPeriod(date(2026, 1, 1), date(2026, 1, 31)),
            billing_date=date(2026, 1, 31),
            status=BillStatus.DRAFT,
        )
        mock_bill_repo.get_by_billing_date_range.return_value = [bill]

        result = service.get_bills_by_billing_date_range(date(2026, 1, 1), date(2026, 1, 31))

        mock_bill_repo.get_by_billing_date_range.assert_called_once_with(
            date(2026, 1, 1), date(2026, 1, 31), limit=10000, offset=0
        )
        assert result == [bill]

    def test_get_bills_by_billing_date_range_empty(
        self, service: BillingService, mock_bill_repo: MagicMock
    ) -> None:
        mock_bill_repo.get_by_billing_date_range.return_value = []

        result = service.get_bills_by_billing_date_range(date(2026, 1, 1), date(2026, 1, 31))

        assert result == []
