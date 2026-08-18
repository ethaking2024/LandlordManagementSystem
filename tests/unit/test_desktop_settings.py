from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtWidgets import QDialog

from app.application.services import BackupResult, RestoreResult, VerificationResult
from app.core.exceptions import ValidationError
from app.desktop.services import OPERATION_FAILED
from app.desktop.settings_page import SettingsPage


class FakeRunner:
    def __init__(self, backup_dir: Path) -> None:
        self.backup = MagicMock()
        self.backup.backup_dir = backup_dir

    def run(self, operation, parent=None):
        services = MagicMock()
        services.backup = MagicMock(return_value=self.backup)
        try:
            return operation(services)
        except Exception:
            return OPERATION_FAILED


@pytest.fixture
def page(qapp, tmp_path) -> tuple[SettingsPage, FakeRunner]:
    runner = FakeRunner(tmp_path / "backups")
    settings = SettingsPage(runner)
    settings.show()
    return settings, runner


def _backup_result(path: Path) -> BackupResult:
    return BackupResult(path=path, size_bytes=2048, created_at=datetime(2026, 8, 18, 12, 0, 0))


# ------------------------------------------------------------------
# Construction
# ------------------------------------------------------------------


@pytest.mark.unit
def test_settings_page_construction(page) -> None:
    settings, runner = page
    assert settings.title == "Settings"
    assert settings._create_button is not None
    assert settings._choose_button is not None
    assert settings._verify_button is not None
    assert settings._restore_button is not None


@pytest.mark.unit
def test_settings_page_shows_backup_location(page) -> None:
    settings, runner = page
    assert str(settings._backup_location) in settings._location_label.text()
    assert "Backup location" in settings._location_label.text()


# ------------------------------------------------------------------
# Create backup
# ------------------------------------------------------------------


@pytest.mark.unit
def test_create_backup_success(page) -> None:
    settings, runner = page
    result = _backup_result(Path("backups/lms_backup_1.dump"))
    runner.backup.create_backup.return_value = result

    with patch("app.desktop.settings_page.QMessageBox.information") as info:
        settings._on_create_backup()

    runner.backup.create_backup.assert_called_once_with(settings._backup_location)
    info.assert_called_once()
    assert "Backup created" in settings._status_label.text()
    assert "lms_backup_1.dump" in settings._status_label.text()


@pytest.mark.unit
def test_create_backup_failure_shows_no_success(page) -> None:
    settings, runner = page
    runner.backup.create_backup.side_effect = ValidationError("no pg tools")

    with patch("app.desktop.settings_page.QMessageBox.information") as info:
        settings._on_create_backup()

    info.assert_not_called()


# ------------------------------------------------------------------
# Choose location
# ------------------------------------------------------------------


@pytest.mark.unit
def test_choose_location_updates_label(page) -> None:
    settings, runner = page
    chosen = "C:\\docs\\lms-backups"

    with patch("app.desktop.settings_page.QFileDialog.getExistingDirectory", return_value=chosen):
        settings._on_choose_location()

    assert settings._backup_location == Path(chosen)
    assert chosen in settings._location_label.text()


@pytest.mark.unit
def test_choose_location_cancelled_keeps_current(page) -> None:
    settings, runner = page
    original = settings._backup_location

    with patch("app.desktop.settings_page.QFileDialog.getExistingDirectory", return_value=""):
        settings._on_choose_location()

    assert settings._backup_location == original


# ------------------------------------------------------------------
# Verify backup
# ------------------------------------------------------------------


@pytest.mark.unit
def test_verify_backup_valid(page) -> None:
    settings, runner = page
    path = Path("backups/lms_backup_1.dump")
    runner.backup.verify_backup.return_value = VerificationResult(path=path, valid=True)

    with (
        patch("app.desktop.settings_page.QFileDialog.getOpenFileName", return_value=(str(path), "")),
        patch("app.desktop.settings_page.QMessageBox.information") as info,
    ):
        settings._on_verify_backup()

    runner.backup.verify_backup.assert_called_once_with(path)
    info.assert_called_once()
    assert "verified" in settings._status_label.text().lower()


@pytest.mark.unit
def test_verify_backup_invalid_warns(page) -> None:
    settings, runner = page
    path = Path("backups/bad.dump")
    runner.backup.verify_backup.return_value = VerificationResult(path=path, valid=False)

    with (
        patch("app.desktop.settings_page.QFileDialog.getOpenFileName", return_value=(str(path), "")),
        patch("app.desktop.settings_page.QMessageBox.warning") as warning,
    ):
        settings._on_verify_backup()

    warning.assert_called_once()
    assert "not a valid backup" in settings._status_label.text()


@pytest.mark.unit
def test_verify_backup_cancelled_no_call(page) -> None:
    settings, runner = page

    with patch("app.desktop.settings_page.QFileDialog.getOpenFileName", return_value=("", "")):
        settings._on_verify_backup()

    runner.backup.verify_backup.assert_not_called()


# ------------------------------------------------------------------
# Restore backup
# ------------------------------------------------------------------


def _fake_dialog(accepted: bool) -> MagicMock:
    dialog = MagicMock()
    dialog.exec.return_value = (
        QDialog.DialogCode.Accepted if accepted else QDialog.DialogCode.Rejected
    )
    dialog.confirmed = accepted
    return dialog


@pytest.mark.unit
def test_restore_backup_confirmed(page) -> None:
    settings, runner = page
    path = Path("backups/lms_backup_1.dump")
    runner.backup.restore_backup.return_value = RestoreResult(
        source=path, database="lms_dev", restored_at=datetime(2026, 8, 18, 12, 30, 0)
    )

    with (
        patch("app.desktop.settings_page.QFileDialog.getOpenFileName", return_value=(str(path), "")),
        patch("app.desktop.settings_page.ConfirmationDialog", return_value=_fake_dialog(True)),
        patch("app.desktop.settings_page.QMessageBox.information") as info,
    ):
        settings._on_restore_backup()

    runner.backup.restore_backup.assert_called_once_with(path)
    info.assert_called_once()
    assert "Restored from" in settings._status_label.text()


@pytest.mark.unit
def test_restore_backup_cancelled_file_dialog(page) -> None:
    settings, runner = page

    with patch("app.desktop.settings_page.QFileDialog.getOpenFileName", return_value=("", "")):
        settings._on_restore_backup()

    runner.backup.restore_backup.assert_not_called()


@pytest.mark.unit
def test_restore_backup_cancelled_confirmation(page) -> None:
    settings, runner = page
    path = Path("backups/lms_backup_1.dump")

    with (
        patch("app.desktop.settings_page.QFileDialog.getOpenFileName", return_value=(str(path), "")),
        patch("app.desktop.settings_page.ConfirmationDialog", return_value=_fake_dialog(False)),
    ):
        settings._on_restore_backup()

    runner.backup.restore_backup.assert_not_called()


# ------------------------------------------------------------------
# Navigation wiring
# ------------------------------------------------------------------


@pytest.mark.unit
def test_navigation_creates_real_settings_page(qapp, tmp_path) -> None:
    from app.desktop.pages import build_navigation

    runner = FakeRunner(tmp_path / "backups")
    nav = build_navigation(runner)
    settings_page = nav.get("settings").page_factory()
    assert isinstance(settings_page, SettingsPage)


@pytest.mark.unit
def test_settings_page_has_no_repository_access() -> None:
    """The settings page must stay presentation-only and never touch infrastructure."""
    import inspect

    import app.desktop.settings_page as module

    source = inspect.getsource(module)
    assert "from app.infrastructure" not in source
    assert "sqlalchemy" not in source
    assert "Session" not in source
    assert "session" not in source


@pytest.mark.unit
def test_settings_runner_without_configured_backup_reports_unavailable(qapp) -> None:
    runner = MagicMock()
    runner.run.return_value = OPERATION_FAILED

    settings = SettingsPage(runner)

    assert "unavailable" in settings._location_label.text().lower()
