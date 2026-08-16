from __future__ import annotations

import csv
import io
from collections.abc import Sequence
from pathlib import Path

from app.core.exceptions import ReportError


def render_csv(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    """Render headers and rows as comma-separated values using the stdlib csv module."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(list(headers))
    writer.writerows([list(row) for row in rows])
    return buffer.getvalue()


def write_csv(path: str | Path, headers: Sequence[str], rows: Sequence[Sequence[str]]) -> Path:
    """Write headers and rows to a UTF-8 CSV file, returning the written path."""
    target = Path(path)
    try:
        with target.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle, lineterminator="\n")
            writer.writerow(list(headers))
            writer.writerows([list(row) for row in rows])
    except OSError as exc:
        raise ReportError(f"Could not write CSV file {target}: {exc}") from exc
    return target
