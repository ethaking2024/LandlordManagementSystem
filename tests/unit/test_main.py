from __future__ import annotations

import pytest


@pytest.mark.unit
def test_self_check_flag_calls_runner_with_report(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.main as main

    captured: list[str | None] = []
    monkeypatch.setattr(
        "app.packaging.run_self_check",
        lambda report: captured.append(report) or 0,
    )
    monkeypatch.setattr("sys.argv", ["LMS.exe", "--self-check", "--report", "out.json"])

    assert main.main() == 0
    assert captured == ["out.json"]


@pytest.mark.unit
def test_migrate_flag_calls_migrations(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.main as main

    monkeypatch.setattr("app.packaging.run_database_migrations", lambda: 0)
    monkeypatch.setattr("sys.argv", ["LMS.exe", "--migrate"])

    assert main.main() == 0


@pytest.mark.unit
def test_self_check_flag_without_report_uses_none(monkeypatch: pytest.MonkeyPatch) -> None:
    import app.main as main

    captured: list[str | None] = []
    monkeypatch.setattr(
        "app.packaging.run_self_check",
        lambda report: captured.append(report) or 0,
    )
    monkeypatch.setattr("sys.argv", ["LMS.exe", "--self-check"])

    assert main.main() == 0
    assert captured == [None]
