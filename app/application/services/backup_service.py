from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from app.core.exceptions import BackupError
from app.core.logging import get_logger
from app.infrastructure.backup import PostgresBackup

logger = get_logger(__name__)

_BACKUP_FILENAME = "lms_backup_{timestamp}_{token}.dump"


@dataclass(frozen=True)
class BackupResult:
    path: Path
    size_bytes: int
    created_at: datetime

    @property
    def size_label(self) -> str:
        size = float(self.size_bytes)
        for unit in ("B", "KB", "MB", "GB"):
            if size < 1024 or unit == "GB":
                if unit == "B":
                    return f"{int(size)} B"
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{self.size_bytes} B"


@dataclass(frozen=True)
class VerificationResult:
    path: Path
    valid: bool


@dataclass(frozen=True)
class RestoreResult:
    source: Path
    database: str
    restored_at: datetime


class BackupService:
    """Application service for creating, verifying and restoring backups.

    A backup is a full PostgreSQL dump of the configured database stored as
    user data, separated from the application installation so that upgrades
    never destroy user data. Restoration replaces the current database contents
    with the contents of a verified backup.
    """

    def __init__(self, tool: PostgresBackup, backup_dir: Path) -> None:
        self._tool = tool
        self._backup_dir = Path(backup_dir)

    @property
    def backup_dir(self) -> Path:
        return self._backup_dir

    @property
    def database_name(self) -> str:
        return self._tool.database_name

    def create_backup(self, target_dir: Path | None = None) -> BackupResult:
        directory = Path(target_dir) if target_dir is not None else self._backup_dir
        directory.mkdir(parents=True, exist_ok=True)
        created_at = datetime.now()
        target = directory / _BACKUP_FILENAME.format(
            timestamp=created_at.strftime("%Y%m%d_%H%M%S"), token=uuid4().hex[:8]
        )

        logger.info(
            "Creating database backup",
            extra={"extra_fields": {"database": self.database_name, "target": str(target)}},
        )
        self._tool.dump(target)

        if not target.is_file() or target.stat().st_size == 0:
            raise BackupError("The backup file was not created.")

        result = BackupResult(path=target, size_bytes=target.stat().st_size, created_at=created_at)
        logger.info(
            "Backup created",
            extra={"extra_fields": {"path": str(result.path), "size_bytes": result.size_bytes}},
        )
        return result

    def verify_backup(self, path: Path) -> VerificationResult:
        source = Path(path)
        valid = self._tool.verify_archive(source)
        logger.info(
            "Backup verified",
            extra={"extra_fields": {"path": str(source), "valid": valid}},
        )
        return VerificationResult(path=source, valid=valid)

    def restore_backup(self, path: Path) -> RestoreResult:
        source = Path(path)
        if not self.verify_backup(source).valid:
            raise BackupError("The selected backup could not be verified. Restore was aborted.")

        logger.warning(
            "Restoring database backup",
            extra={"extra_fields": {"database": self.database_name, "source": str(source)}},
        )
        self._tool.restore(source)

        result = RestoreResult(source=source, database=self.database_name, restored_at=datetime.now())
        logger.info(
            "Database restored",
            extra={"extra_fields": {"database": result.database, "source": str(result.source)}},
        )
        return result

    def list_backups(self) -> list[Path]:
        if not self._backup_dir.is_dir():
            return []
        files = [path for path in self._backup_dir.iterdir() if path.is_file() and path.suffix == ".dump"]
        files.sort(key=lambda path: path.stat().st_mtime, reverse=True)
        return files
