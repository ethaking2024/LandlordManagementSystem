# LMS Release Packaging — Build Guide

This document describes how to produce the Windows release of LMS (a PyInstaller "onedir" build) and how the packaged application locates resources, configuration, and user data.

---

## 1. What the release contains

The build produces a folder `packaging/dist/LMS/` containing:

- `LMS.exe` — the windowed desktop application entry point
- `_internal/` — bundled Python modules, Qt plugins, and dependencies
- `alembic.ini` + `migrations/` — bundled so `LMS.exe --migrate` works on a fresh machine
- `assets/app.ico` — the application icon
- `env.example` (copied by the build script) — template for the user's `.env`

The output is a folder, not a single file. Distributing the folder is the supported method: it is robust, starts fast, and is easier for antivirus software to trust.

---

## 2. Build requirements

- Windows
- Python 3.13
- The development environment from `pyproject.toml` (PyInstaller is installed automatically by the build script)

---

## 3. Build command

From the repository root:

```powershell
.\scripts\build_release.ps1
```

The script:

1. Installs PyInstaller if missing.
2. Regenerates the application icon (`scripts/create_icon.py` → `packaging/assets/app.ico`).
3. Runs the quality gates: unit tests, Ruff, Mypy (skip with `-SkipTests -SkipChecks`).
4. Runs PyInstaller against `packaging/LMS.spec`.
5. Copies `.env.example` next to the produced `LMS.exe`.
6. Runs `LMS.exe --self-check` and writes `packaging/dist/self-check.json`.

The equivalent manual build is:

```powershell
python -m PyInstaller --noconfirm --clean `
    --distpath packaging/dist --workpath packaging/build packaging/LMS.spec
```

> The `--distpath` / `--workpath` flags keep all build artifacts under `packaging/`
> so the repository root stays clean.

---

## 4. Packaging layout and data boundaries

| Item | Location | Purpose |
| --- | --- | --- |
| Program code + resources | `_internal/` (PyInstaller bundle) | Read-only; replaced on upgrade |
| User configuration | `.env` next to `LMS.exe` | Edited by the landlord |
| Backups / user data | `%LOCALAPPDATA%\LMS\Backups` (default `BACKUP_DIR`) | Survive upgrades |

User configuration and backups are deliberately kept **outside** the `_internal/` bundle so application upgrades never destroy them.

### Resource resolution

`app/packaging.resource_path()` returns:

- the PyInstaller `_MEIPASS` directory when frozen, or
- the repository root when running from source.

It is used for `alembic.ini`, `migrations/`, and `assets/app.ico`.

### Configuration resolution

`app/core/config.py` resolves `.env` in this order when frozen:

1. next to the executable (`<exe dir>\.env`)
2. the user data directory (`%LOCALAPPDATA%\LMS\.env`)

When running from source it uses `.env` in the working directory (historical behaviour).

---

## 5. Packaged-app command-line modes

`LMS.exe` accepts two setup/validation flags before the normal GUI start:

| Flag | Purpose |
| --- | --- |
| `LMS.exe --migrate` | Apply Alembic migrations to the configured database; exit `0` on success. First-run setup. |
| `LMS.exe --self-check [--report <path>]` | Validate configuration, database connectivity, and backup tooling; write a JSON report; exit `0`/`1`. |

These are packaging/setup aids, not part of the normal user workflow.

---

## 6. Verification checklist

After a build:

1. `packaging/dist/LMS/LMS.exe` exists.
2. `packaging/dist/self-check.json` reports `exit_code: 0` when a database is configured and reachable.
3. Fresh-install migration: `LMS.exe --migrate` against an empty database completes with exit `0`.
4. Backup/Restore availability: the self-check `backup_restore_availability` check is `ok` when PostgreSQL tools are installed.

---

## 7. Versioning

- `app/core/version.py` holds `VERSION` (dotted, e.g. `0.8.5`) and `RELEASE_LABEL` (e.g. `0.8E`).
- `pyproject.toml` mirrors `VERSION`.
- `packaging/version_info.txt` mirrors the same version for the Windows file resource and must be updated alongside `app/core/version.py` when releasing a new version.
- The sidebar version label is derived from `RELEASE_LABEL`.

Keep the three in sync for every release.