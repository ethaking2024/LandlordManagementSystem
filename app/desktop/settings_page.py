from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QWidget,
)

from app.desktop.components.buttons import PrimaryButton, SecondaryButton
from app.desktop.components.dialogs import ConfirmationDialog
from app.desktop.components.page import Page
from app.desktop.services import OPERATION_FAILED, ServiceRunner
from app.desktop.theme import AppColors


class _SectionTitle(QLabel):
    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setObjectName("settingsSectionTitle")
        self.setStyleSheet(
            f"color: {AppColors.TEXT_SECONDARY}; font-size: 13px; font-weight: 700;"
        )


class SettingsPage(Page):
    """Application settings including first-class Backup & Restore.

    Backups are full PostgreSQL dumps stored as user data. Restoring replaces
    the current database contents with the contents of a verified backup, so the
    UI asks for confirmation before any destructive restore.
    """

    def __init__(
        self,
        runner: ServiceRunner,
        title: str = "Settings",
        subtitle: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(title, subtitle, parent)
        self._runner = runner
        self._backup_location: Path | None = None

        self._build_backup_section()
        self._refresh_backup_location()

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def _build_backup_section(self) -> None:
        self.content_layout.addWidget(_SectionTitle("Backup & Restore"))

        hint = QLabel(
            "Keep your records safe with full database backups. Restoring replaces "
            "the current data with the contents of the selected backup."
        )
        hint.setObjectName("backupHint")
        hint.setWordWrap(True)
        self.content_layout.addWidget(hint)

        self._location_label = QLabel("")
        self._location_label.setObjectName("backupLocation")
        self._location_label.setWordWrap(True)
        self.content_layout.addWidget(self._location_label)

        buttons = QHBoxLayout()
        self._create_button = PrimaryButton("Create Backup")
        self._create_button.clicked.connect(self._on_create_backup)
        self._choose_button = SecondaryButton("Choose Folder...")
        self._choose_button.clicked.connect(self._on_choose_location)
        self._verify_button = SecondaryButton("Verify Backup...")
        self._verify_button.clicked.connect(self._on_verify_backup)
        self._restore_button = SecondaryButton("Restore from Backup...")
        self._restore_button.clicked.connect(self._on_restore_backup)

        buttons.addWidget(self._create_button)
        buttons.addWidget(self._choose_button)
        buttons.addWidget(self._verify_button)
        buttons.addWidget(self._restore_button)
        buttons.addStretch()
        self.content_layout.addLayout(buttons)

        self._status_label = QLabel("")
        self._status_label.setObjectName("backupStatus")
        self.content_layout.addWidget(self._status_label)
        self.content_layout.addStretch()

    # ------------------------------------------------------------------
    # Backup location
    # ------------------------------------------------------------------

    def _refresh_backup_location(self) -> None:
        result = self._runner.run(lambda services: services.backup().backup_dir)
        if result is OPERATION_FAILED:
            self._location_label.setText("Backup location is unavailable.")
            return
        self._backup_location = Path(result)
        self._location_label.setText(f"Backup location: {self._backup_location}")

    def _on_choose_location(self) -> None:
        default = str(self._backup_location) if self._backup_location else ""
        selected = QFileDialog.getExistingDirectory(self, "Choose Backup Folder", default)
        if selected:
            self._backup_location = Path(selected)
            self._location_label.setText(f"Backup location: {self._backup_location}")

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_create_backup(self) -> None:
        result = self._runner.run(
            lambda services: services.backup().create_backup(self._backup_location)
        )
        if result is OPERATION_FAILED:
            return
        self._status_label.setText(f"Backup created: {result.path.name} ({result.size_label})")
        QMessageBox.information(
            self,
            "Backup Created",
            f"Backup saved to:\n{result.path}\n\nSize: {result.size_label}",
        )

    def _on_verify_backup(self) -> None:
        path = self._pick_backup_file()
        if path is None:
            return
        result = self._runner.run(lambda services: services.backup().verify_backup(path))
        if result is OPERATION_FAILED:
            return
        if result.valid:
            self._status_label.setText(f"Backup verified: {result.path.name}")
            QMessageBox.information(self, "Backup Verified", f"The backup is valid:\n{result.path}")
        else:
            self._status_label.setText("Selected file is not a valid backup.")
            QMessageBox.warning(self, "Backup Invalid", f"The selected file is not a valid backup:\n{result.path}")

    def _on_restore_backup(self) -> None:
        path = self._pick_backup_file()
        if path is None:
            return
        dialog = ConfirmationDialog(
            "Restore Backup",
            "Restoring will replace the current data with the contents of the "
            "selected backup.\n\nThis cannot be undone.",
            parent=self,
            confirm_text="Restore",
            danger=True,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted or not dialog.confirmed:
            return
        result = self._runner.run(lambda services: services.backup().restore_backup(path))
        if result is OPERATION_FAILED:
            return
        self._status_label.setText(f"Restored from {result.source.name}")
        QMessageBox.information(
            self,
            "Restore Complete",
            f"Data was restored from:\n{result.source}",
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _pick_backup_file(self) -> Path | None:
        default = str(self._backup_location) if self._backup_location else ""
        selected, _ = QFileDialog.getOpenFileName(
            self, "Select Backup File", default, "LMS Backup (*.dump)"
        )
        return Path(selected) if selected else None
