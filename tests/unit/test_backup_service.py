from __future__ import annotations

from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy.engine import make_url

from app.application.services.backup_service import BackupService
from app.core.exceptions import BackupError
from app.infrastructure.backup import PostgresBackup, discover_pg_bin_dir


class FakeTool:
    def __init__(self, *, writes_file: bool = True, verify_result: bool = True) -> None:
        self.dump_calls: list[Path] = []
        self.restore_calls: list[Path] = []
        self.writes_file = writes_file
        self.verify_result = verify_result
        self.database_name = "lms_dev"

    def dump(self, target: Path) -> None:
        self.dump_calls.append(Path(target))
        if self.writes_file:
            Path(target).write_bytes(b"dummy dump archive")

    def restore(self, source: Path) -> None:
        self.restore_calls.append(Path(source))

    def verify_archive(self, path: Path) -> bool:
        return self.verify_result


@pytest.fixture
def backup_dir(tmp_path: Path) -> Path:
    directory = tmp_path / "backups"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


# ------------------------------------------------------------------
# create_backup
# ------------------------------------------------------------------


@pytest.mark.unit
def test_create_backup_writes_dump_in_default_dir(backup_dir: Path) -> None:
    service = BackupService(FakeTool(), backup_dir)

    result = service.create_backup()

    assert result.path.parent == backup_dir
    assert result.path.name.startswith("lms_backup_")
    assert result.path.suffix == ".dump"
    assert result.path.is_file()
    assert result.size_bytes == result.path.stat().st_size
    assert result.size_bytes > 0


@pytest.mark.unit
def test_create_backup_uses_explicit_target_dir(tmp_path: Path) -> None:
    service = BackupService(FakeTool(), tmp_path / "backups")
    target = tmp_path / "elsewhere"

    result = service.create_backup(target_dir=target)

    assert result.path.parent == target
    assert target.is_dir()


@pytest.mark.unit
def test_create_backup_raises_when_dump_not_written(backup_dir: Path) -> None:
    service = BackupService(FakeTool(writes_file=False), backup_dir)

    with pytest.raises(BackupError, match="not created"):
        service.create_backup()


@pytest.mark.unit
def test_backup_result_size_label() -> None:
    from app.application.services.backup_service import BackupResult

    small = BackupResult(path=Path("a.dump"), size_bytes=512, created_at=datetime.now())
    assert small.size_label == "512 B"

    large = BackupResult(path=Path("a.dump"), size_bytes=2048, created_at=datetime.now())
    assert large.size_label == "2.0 KB"


# ------------------------------------------------------------------
# verify_backup
# ------------------------------------------------------------------


@pytest.mark.unit
def test_verify_backup_reports_valid(backup_dir: Path) -> None:
    service = BackupService(FakeTool(verify_result=True), backup_dir)
    path = backup_dir / "lms_backup_1.dump"

    result = service.verify_backup(path)

    assert result.path == path
    assert result.valid is True


@pytest.mark.unit
def test_verify_backup_reports_invalid(backup_dir: Path) -> None:
    service = BackupService(FakeTool(verify_result=False), backup_dir)

    assert service.verify_backup(Path("bad.dump")).valid is False


# ------------------------------------------------------------------
# restore_backup
# ------------------------------------------------------------------


@pytest.mark.unit
def test_restore_backup_verifies_then_restores(backup_dir: Path) -> None:
    tool = FakeTool()
    service = BackupService(tool, backup_dir)
    source = backup_dir / "lms_backup_1.dump"
    source.write_bytes(b"dummy dump archive")

    result = service.restore_backup(source)

    assert tool.restore_calls == [source]
    assert result.source == source
    assert result.database == "lms_dev"


@pytest.mark.unit
def test_restore_backup_rejects_invalid_archive(backup_dir: Path) -> None:
    tool = FakeTool(verify_result=False)
    service = BackupService(tool, backup_dir)
    source = backup_dir / "bad.dump"

    with pytest.raises(BackupError, match="could not be verified"):
        service.restore_backup(source)

    assert tool.restore_calls == []


# ------------------------------------------------------------------
# list_backups
# ------------------------------------------------------------------


@pytest.mark.unit
def test_list_backups_returns_only_dumps_sorted(backup_dir: Path) -> None:
    (backup_dir / "old.dump").write_bytes(b"x")
    (backup_dir / "new.dump").write_bytes(b"y")
    (backup_dir / "notes.txt").write_text("nope", encoding="utf-8")
    service = BackupService(FakeTool(), backup_dir)

    files = service.list_backups()

    assert {path.name for path in files} == {"new.dump", "old.dump"}
    mtimes = [path.stat().st_mtime for path in files]
    assert mtimes == sorted(mtimes, reverse=True)


@pytest.mark.unit
def test_list_backups_missing_dir_returns_empty(tmp_path: Path) -> None:
    service = BackupService(FakeTool(), tmp_path / "does-not-exist")
    assert service.list_backups() == []


# ------------------------------------------------------------------
# PostgresBackup command construction
# ------------------------------------------------------------------

DB_URL = "postgresql+psycopg://lms_user:secret@localhost:5432/lms_dev"


@pytest.mark.unit
def test_postgres_backup_dump_command() -> None:
    tool = PostgresBackup(make_url(DB_URL), pg_bin_dir=r"C:\pg\bin")

    with patch("app.infrastructure.backup.subprocess.run") as run:
        run.return_value.returncode = 0
        tool.dump(Path("backup.dump"))

    command, kwargs = run.call_args.args[0], run.call_args.kwargs
    assert command[0] == r"C:\pg\bin\pg_dump.exe"
    assert command[command.index("--host") + 1] == "localhost"
    assert command[command.index("--port") + 1] == "5432"
    assert command[command.index("--username") + 1] == "lms_user"
    assert "--format=custom" in command
    assert "--no-owner" in command
    assert "--no-privileges" in command
    assert command[command.index("--file") + 1] == "backup.dump"
    assert command[-1] == "lms_dev"
    assert "secret" not in " ".join(command)
    assert kwargs["env"]["PGPASSWORD"] == "secret"


@pytest.mark.unit
def test_postgres_backup_restore_command() -> None:
    tool = PostgresBackup(make_url(DB_URL), pg_bin_dir=r"C:\pg\bin")

    with patch("app.infrastructure.backup.subprocess.run") as run:
        run.return_value.returncode = 0
        tool.restore(Path("backup.dump"))

    command = run.call_args.args[0]
    assert command[0] == r"C:\pg\bin\pg_restore.exe"
    assert command[command.index("--dbname") + 1] == "lms_dev"
    assert "--clean" in command
    assert "--if-exists" in command
    assert "--no-owner" in command
    assert command[-1] == "backup.dump"
    assert "secret" not in " ".join(command)


@pytest.mark.unit
def test_postgres_backup_verify_archive_ok(tmp_path: Path) -> None:
    tool = PostgresBackup(make_url(DB_URL), pg_bin_dir=r"C:\pg\bin")
    path = tmp_path / "backup.dump"
    path.write_bytes(b"archive")

    with patch("app.infrastructure.backup.subprocess.run") as run:
        run.return_value.returncode = 0
        assert tool.verify_archive(path) is True

    command = run.call_args.args[0]
    assert command[0] == r"C:\pg\bin\pg_restore.exe"
    assert command[-1] == str(path)


@pytest.mark.unit
def test_postgres_backup_verify_archive_invalid(tmp_path: Path) -> None:
    tool = PostgresBackup(make_url(DB_URL), pg_bin_dir=r"C:\pg\bin")
    path = tmp_path / "backup.dump"
    path.write_bytes(b"archive")

    with patch("app.infrastructure.backup.subprocess.run") as run:
        run.return_value.returncode = 1
        assert tool.verify_archive(path) is False


@pytest.mark.unit
def test_postgres_backup_verify_archive_empty_file(tmp_path: Path) -> None:
    tool = PostgresBackup(make_url(DB_URL), pg_bin_dir=r"C:\pg\bin")
    path = tmp_path / "empty.dump"
    path.write_bytes(b"")

    assert tool.verify_archive(path) is False


@pytest.mark.unit
def test_postgres_backup_raises_on_failure() -> None:
    tool = PostgresBackup(make_url(DB_URL), pg_bin_dir=r"C:\pg\bin")

    with patch("app.infrastructure.backup.subprocess.run") as run:
        run.return_value.returncode = 1
        run.return_value.stderr = b"connection refused"
        with pytest.raises(BackupError, match="pg_dump"):
            tool.dump(Path("backup.dump"))


@pytest.mark.unit
def test_postgres_backup_password_absent_when_url_has_none() -> None:
    tool = PostgresBackup(
        make_url("postgresql+psycopg://lms_user@localhost:5432/lms_dev"),
        pg_bin_dir=r"C:\pg\bin",
    )

    with patch("app.infrastructure.backup.subprocess.run") as run:
        run.return_value.returncode = 0
        tool.dump(Path("backup.dump"))

    assert "PGPASSWORD" not in run.call_args.kwargs["env"]


@pytest.mark.unit
def test_discover_pg_bin_dir_returns_path_or_none() -> None:
    result = discover_pg_bin_dir()
    assert result is None or isinstance(result, str)
