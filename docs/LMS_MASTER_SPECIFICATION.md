# Landlord Management System (LMS) — Master Specification

**Status:** LOCKED  
**Version:** 1.0 Planning Baseline  
**Target:** Windows desktop first; API/mobile later  
**Primary market:** Small landlords in Nepal

## 1. Product Goal

LMS is a simple, professional, lightweight landlord management system for landlords who typically own one or two houses and rent whole floors, flats, rooms, or combinations of rooms.

The application must minimize repeated data entry while preserving reliable financial history and providing a clean path to future mobile access.

## 2. Locked Product Principles

1. Simple outside, professional inside.
2. Configure once -> reuse automatically -> override only when necessary.
3. Minimize forms, fields, tables, and repetitive entry.
4. Financial calculations must be correct and testable.
5. Historical financial records must not be silently overwritten.
6. Desktop and future mobile/API must share the same business logic.
7. Avoid enterprise-scale complexity unless explicitly approved.
8. A feature is not complete until implementation, tests, database behavior, and acceptance criteria pass.
9. Locked architecture and business rules must not be changed casually.
10. Future-ready does not mean future-bloated.

## 3. Technology Contract

- Python 3.13+
- PySide6 desktop UI
- PostgreSQL
- SQLAlchemy 2.x
- Alembic
- FastAPI for future API
- Pydantic for API schemas/validation
- python-dotenv/configuration layer
- ReportLab for PDF reports/receipts
- PyInstaller for Windows packaging
- Git/GitHub

Do not replace the stack without explicit approval.

## 4. Architecture

```text
PySide6 Desktop
      |
      v
Application Services
      |
      v
Domain / Business Rules
      |
      v
Repositories / SQLAlchemy
      |
      v
PostgreSQL

Future:
Mobile -> FastAPI -> Same Application Services -> PostgreSQL
```

### Rules

- UI never directly accesses PostgreSQL.
- UI contains no financial/business calculations.
- API routes contain no business logic.
- Database queries stay in repositories.
- Business workflows stay in application/domain services.
- Desktop and API use the same business logic.
- No microservices.
- No duplicated billing/payment calculations.
- Financial operations are transactional.

## 5. Target Project Structure

```text
LandlordManagementSystem/
├── app/
│   ├── main.py
│   ├── core/
│   ├── domain/
│   │   ├── entities/
│   │   ├── enums/
│   │   ├── rules/
│   │   └── value_objects/
│   ├── application/
│   │   ├── services/
│   │   ├── commands/
│   │   ├── queries/
│   │   └── dto/
│   ├── infrastructure/
│   │   ├── database/
│   │   ├── repositories/
│   │   └── persistence/
│   ├── desktop/
│   │   ├── windows/
│   │   ├── views/
│   │   ├── widgets/
│   │   └── dialogs/
│   ├── api/
│   │   ├── app.py
│   │   ├── routes/
│   │   ├── schemas/
│   │   └── dependencies.py
│   ├── reports/
│   │   ├── services/
│   │   ├── templates/
│   │   └── exporters/
│   └── shared/
│       ├── dates/
│       ├── money/
│       └── utilities/
├── migrations/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── api/
│   └── e2e/
├── scripts/
├── docs/
├── .env.example
├── alembic.ini
├── pyproject.toml
├── README.md
└── LICENSE
```

Create files/directories only when required by the current milestone.

## 6. Core Modules

1. Dashboard
2. Properties / Rental Spaces
3. Tenants
4. Rental Agreements
5. Meters & Readings
6. Billing
7. Payments
8. Expenses
9. Deposits / Final Settlement
10. Reports
11. Settings
12. Backup / Restore

Do not create unnecessary standalone modules.

## 7. Rental Model

The system must support Nepal's practical rental structure:

- one property/house, sometimes two
- multiple floors
- whole-floor rental
- flat rental
- individual room rental
- multiple rooms rented together

A rental space is the key rentable unit. The UI should allow natural names such as `Ground Floor`, `First Floor Flat`, `Room 1`, or `First Floor - Room 1 & 2` without forcing unnecessary hierarchy.

## 8. Tenant

Keep tenant data lightweight. Typical core information:

- Name
- Phone
- Optional address/contact notes

Do not make unnecessary identity fields mandatory.

## 9. Rental Agreement

An agreement connects:

- tenant
- rental space
- rent
- start/end dates
- due day/rules
- utility configuration
- deposit

A space cannot have overlapping active agreements.

## 10. Electricity

Support:

- fixed electricity charge
- metered electricity

For metered electricity:

`consumption = current_reading - previous_reading`

`charge = consumption * applicable_tariff`

Rules:

- missing reading = pending, never silently estimated
- invalid/decreasing reading is rejected unless handled through controlled meter replacement
- tariff history uses effective dates
- historical bills retain their historical calculation basis

## 11. Water

Support:

- no charge
- fixed charge
- metered charge

The same historical and validation principles apply to metered water.

## 12. Meter Replacement

Meter replacement must preserve history:

```text
Old Meter -> Final Reading -> Replacement -> New Meter -> Initial Reading
```

Old readings remain associated with the old meter.

## 13. Tariffs

Utility tariffs have effective dates and historical values must remain available for historical calculations.

Example:

```text
01 Bhadra 2083 -> NPR 12/unit
01 Kartik 2083 -> NPR 13/unit
```

## 14. Calendar

The user-facing application supports both:

- AD / Gregorian
- BS / Bikram Sambat

Where dates are shown, both may be displayed. Internally, use a canonical date representation and reliable conversion. Do not maintain conflicting manually entered AD and BS dates.

## 15. Billing

Monthly billing is the primary billing model.

Flow:

```text
Agreement -> Rent + Utilities -> Monthly Review -> Confirmation -> Charges
```

Billing must prevent duplicate charges for the same applicable period.

Billing supports:

- rent
- fixed utilities
- metered utilities
- applicable proration
- review before confirmation
- confirmed historical charges
- corrections that preserve history

## 16. Billing State

Use a controlled lifecycle such as:

`Pending/Draft -> Reviewed -> Confirmed -> Paid/Partially Paid/Outstanding`

Confirmed financial records must not be casually edited.

## 17. Proration

Support proration for applicable move-in, move-out, and rent-change cases using the single locked system policy. Do not ask the landlord to manually calculate prorated amounts.

## 18. Payments

Supported methods include:

- Cash
- Bank Transfer
- eSewa
- Khalti
- Cheque
- Other

Payment functionality supports:

- full payment
- partial payment
- allocation to outstanding charges
- overpayment
- tenant credit
- corrections with history

Do not implement payment-gateway integration in V1.

## 19. Expenses

Keep expenses simple:

- date
- category
- amount
- description

Default categories may include Repairs, Electricity, Water, Cleaning, Property Tax, Insurance, and Other. This is not full accounting software.

## 20. Deposit / Move-Out

At move-out:

```text
Final meter readings
-> final charges
-> outstanding balance
-> deposit deductions
-> refund/final settlement
-> agreement closed
-> space available
```

## 21. Dashboard

The dashboard should emphasize:

- properties
- occupied/vacant spaces
- active tenants
- current month income
- outstanding amount
- overdue amount
- pending meter readings
- pending billing/review

Avoid excessive charts.

## 22. UX Principles

- few screens
- meaningful actions
- contextual creation
- minimal repeated entry
- useful defaults
- no unnecessary configuration
- clear validation messages
- user-friendly errors

Changing a default must never silently alter existing agreements or historical transactions.

## 23. Reports

V1 reports:

- Tenant Statement
- Payment Receipt
- Monthly Summary
- Property Summary
- Meter History

Use ReportLab for PDFs.

## 24. Security

- passwords, when applicable, are hashed
- secrets never hardcoded
- production API uses HTTPS
- API authentication/authorization required
- sensitive information should not be unnecessarily logged

## 25. Backup / Restore

Backup and restore are first-class operational capabilities. A backup is not considered tested until restoration has been successfully verified.

Application files and user data must be separated so upgrades do not destroy user data.

## 26. API / Mobile

Future API:

- FastAPI
- `/api/v1`
- structured Pydantic schemas
- authentication
- authorization
- HTTPS in production
- OpenAPI documentation

Mobile never connects directly to PostgreSQL.

Mobile is developed only after the desktop core and API foundation are stable. Do not lock a mobile framework yet.

Do not implement SMS, WhatsApp, push notifications, payment gateways, cloud sync, complex offline synchronization, or microservices in V1.

## 27. Testing Contract

Required test levels:

- unit
- integration
- API
- end-to-end

Critical tests include:

- agreement conflicts
- rent
- proration
- fixed/metered electricity
- fixed/metered water
- missing/decreasing meter readings
- meter replacement
- tariff history
- duplicate billing prevention
- payment allocation
- partial payment
- overpayment/credit
- deposit settlement
- move-out
- AD/BS conversion
- migrations
- backup/restore

A feature is complete only when implementation + business rules + tests + database behavior + acceptance criteria pass.

## 28. Release Strategy

Version format: `MAJOR.MINOR.PATCH`.

Windows production packaging uses PyInstaller. Database changes use Alembic. Releases require fresh-install, upgrade, migration, backup/restore, regression, and critical workflow verification.

## 29. Implementation Sequence

- Release 0.0: repository/project initialization
- Release 0.1: foundation
- Release 0.2: core data
- Release 0.3: meters/utilities
- Release 0.4: billing
- Release 0.5: payments
- Release 0.6: expenses/settlement
- Release 0.7: dashboard/reports
- Release 0.8: security/backup/hardening
- Release 0.9: API foundation
- Release 1.0: production release

## 30. Change Control

After this specification is accepted, changes require an explicit change request describing:

1. requested change
2. reason
3. impact
4. affected locked decisions
5. implementation/test impact

Do not silently redesign locked requirements.
