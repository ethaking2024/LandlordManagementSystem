# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec for the LMS desktop application (release 1.0.0).
#
# Build with: python -m PyInstaller --noconfirm --clean packaging/LMS.spec
# Output: packaging/dist/LMS/LMS.exe
#
# Bundled resources:
#   alembic.ini + migrations/  - required by "LMS.exe --migrate" for first-run setup
#   assets/app.ico             - application/window icon
#
# User configuration (.env) and backups are NOT bundled; they live next to the
# executable and in %LOCALAPPDATA%\LMS\Backups respectively so they survive
# application upgrades.

import os

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

script_path = os.path.normpath(os.path.join(SPECPATH, "..", "app", "main.py"))
icon_path = os.path.normpath(os.path.join(SPECPATH, "assets", "app.ico"))
version_path = os.path.normpath(os.path.join(SPECPATH, "version_info.txt"))

datas = [
    (os.path.normpath(os.path.join(SPECPATH, "..", "alembic.ini")), "."),
    (os.path.normpath(os.path.join(SPECPATH, "..", "migrations")), "migrations"),
    (icon_path, "assets"),
    *collect_data_files("nepali_datetime"),
]

hiddenimports = [
    "sqlalchemy.dialects.postgresql.psycopg",
    "psycopg",
    "psycopg_binary",
    "pydantic",
    "pydantic_settings",
    "nepali_datetime",
    *collect_submodules("alembic", filter=lambda name: "testing" not in name),
]

a = Analysis(
    [script_path],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "pytest",
        "_pytest",
        "ruff",
        "mypy",
        "PyQt5",
        "PyQt5.QtCore",
        "PyQt5.QtGui",
        "PyQt5.QtWidgets",
        "PyQt5.Qt",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name="LMS",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=icon_path,
    version=version_path,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    name="LMS",
)

