# Landlord Management System (LMS)

A simple, professional, lightweight landlord management system for Windows, designed around the rental practices commonly used by small landlords in Nepal.

**Version 1.0.0** — first production release.

## Status

**Production release:** 1.0.0
**Platform:** Windows 10/11 desktop (64-bit)
**Database:** PostgreSQL (17 or compatible)

## Key features

- Owners, properties, and rental spaces
- Tenants and rental agreements
- Utility configuration (electricity, water) with meter readings and tariffs
- Monthly billing with rent, utility, and meter-based line items
- Payments with partial-payment and overpayment/credit handling
- Security deposits with settlement and deductions
- Expenses
- Dashboard (occupancy, monthly summary, outstanding bills, recent activity)
- Reports with PDF and CSV export
- Database backup and restore (uses the PostgreSQL command-line tools)

## Technology

- Windows desktop (PySide6 / Qt)
- PostgreSQL (SQLAlchemy 2.x, Alembic migrations)
- Packaged as a self-contained Windows application (PyInstaller) — no Python required to run

## Install

- [Installation Guide (end users)](docs/LMS_INSTALLATION_GUIDE.md)

1. Install PostgreSQL (free from [postgresql.org](https://www.postgresql.org/download/windows/)).
2. Create a database and user (see the installation guide).
3. Copy the release `LMS` folder to your computer.
4. Create a `.env` file next to `LMS.exe` from the included template and set `DATABASE_URL`.
5. Run `LMS.exe --migrate` once to create the schema.
6. Double-click `LMS.exe` to start.

## Documentation

- [Installation Guide (end users)](docs/LMS_INSTALLATION_GUIDE.md)
- [Release Packaging (build guide)](docs/LMS_RELEASE_PACKAGING.md)
- [Master Specification](docs/LMS_MASTER_SPECIFICATION.md)
- [Development Protocol](docs/LMS_DEVELOPMENT_PROTOCOL.md)
- [Release Roadmap](docs/LMS_RELEASE_ROADMAP.md)

## Development Principle

> Simple outside, professional inside.

The locked specification is the source of truth. Development is performed milestone-by-milestone with automated tests and controlled change management.

## License

MIT — see [LICENSE](LICENSE).
