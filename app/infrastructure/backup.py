from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from sqlalchemy.engine import URL

from app.core.exceptions import BackupError
from app.core.logging import get_logger

logger = get_logger(__name__)


def discover_pg_bin_dir() -> str | None:
    """Locate a directory containing the PostgreSQL client tools.

    Resolution order: tools on ``PATH``, then common Windows install locations.
    """
    executable = shutil.which("pg_dump")
    if executable:
        return str(Path(executable).parent)

    if os.name == "nt":
        program_files = Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
        base = program_files / "PostgreSQL"
        if base.is_dir():
            versions = [entry for entry in base.iterdir() if entry.is_dir()]
            versions.sort(key=lambda entry: entry.name, reverse=True)
            for version in versions:
                candidate = version / "bin"
                if (candidate / "pg_dump.exe").exists():
                    return str(candidate)
    return None


def _tool_path(pg_bin_dir: str | None, name: str) -> str:
    if pg_bin_dir:
        suffix = ".exe" if os.name == "nt" else ""
        return str(Path(pg_bin_dir) / f"{name}{suffix}")
    return name


class PostgresBackup:
    """Drives the PostgreSQL client tools to dump and restore the database.

    This is the infrastructure boundary for backup/restore. It translates a
    SQLAlchemy database URL into pg_dump/pg_restore/psql invocations and never
    leaks credentials into command lines or logs (the password travels only via
    the ``PGPASSWORD`` environment variable).
    """

    def __init__(self, url: URL, pg_bin_dir: str | None = None) -> None:
        self._url = url
        self._pg_bin_dir = pg_bin_dir or discover_pg_bin_dir()

    @property
    def database_name(self) -> str:
        return self._url.database or ""

    def dump(self, target: Path) -> None:
        """Create a full custom-format (compressed) dump of the database."""
        command = [
            _tool_path(self._pg_bin_dir, "pg_dump"),
            *self._connection_args(),
            "--format=custom",
            "--no-owner",
            "--no-privileges",
            "--file",
            str(target),
            self.database_name,
        ]
        self._run(command)

    def restore(self, source: Path) -> None:
        """Restore the database from a custom-format dump, replacing existing objects."""
        command = [
            _tool_path(self._pg_bin_dir, "pg_restore"),
            *self._connection_args(),
            "--dbname",
            self.database_name,
            "--clean",
            "--if-exists",
            "--no-owner",
            "--no-privileges",
            str(source),
        ]
        self._run(command)

    def verify_archive(self, path: Path) -> bool:
        """Return True when ``path`` is a non-empty, restorable pg_dump archive."""
        if not path.is_file() or path.stat().st_size == 0:
            return False
        command = [_tool_path(self._pg_bin_dir, "pg_restore"), "--list", str(path)]
        try:
            self._run(command, capture_output=True)
            return True
        except BackupError:
            return False

    def check_connection(self) -> bool:
        """Return True when the database answers a trivial query."""
        command = [
            _tool_path(self._pg_bin_dir, "psql"),
            *self._connection_args(),
            "--dbname",
            self.database_name,
            "--tuples-only",
            "--no-align",
            "--command",
            "SELECT 1",
        ]
        try:
            self._run(command, capture_output=True)
            return True
        except BackupError:
            return False

    def _connection_args(self) -> list[str]:
        args: list[str] = []
        if self._url.host:
            args.extend(["--host", self._url.host])
        if self._url.port:
            args.extend(["--port", str(self._url.port)])
        if self._url.username:
            args.extend(["--username", self._url.username])
        return args

    def _run(self, command: list[str], capture_output: bool = False) -> None:
        env = os.environ.copy()
        if self._url.password:
            env["PGPASSWORD"] = self._url.password
        tool = Path(command[0]).name
        logger.info(
            "Running PostgreSQL tool",
            extra={"extra_fields": {"tool": tool, "database": self.database_name}},
        )
        try:
            result = subprocess.run(command, env=env, capture_output=capture_output, check=False)
        except FileNotFoundError as exc:
            raise BackupError(
                f"PostgreSQL tool not found: {tool}. Install the PostgreSQL client "
                "tools or set PG_BIN_DIR."
            ) from exc
        if result.returncode != 0:
            detail = ""
            if capture_output:
                detail = (result.stderr or b"").decode(errors="replace").strip()
            message = f"PostgreSQL tool failed: {tool} exited with {result.returncode}"
            if detail:
                message = f"{message}. {detail}"
            raise BackupError(message)
