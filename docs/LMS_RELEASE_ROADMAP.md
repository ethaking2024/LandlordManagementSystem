# LMS Release Roadmap

**Planning status:** Locked  
**Implementation style:** milestone-based, tested releases

## Release 0.0 — Initialization

Purpose: establish the clean repository and authoritative documentation.

Deliverables:

- master specification
- development protocol
- release roadmap
- initialization instructions
- README
- Git-ready project metadata

No business functionality.

## Release 0.1 — Foundation

Deliverables:

- Python project configuration
- application package
- configuration layer
- logging
- exception foundation
- PostgreSQL connection/session infrastructure
- SQLAlchemy foundation
- Alembic initialization
- test infrastructure
- minimal application startup

Acceptance: application starts, database connection path is validated, migrations can run, tests execute.

## Release 0.2 — Core Data

Entities:

- owner
- property
- rental space
- tenant
- rental agreement

Deliverables:

- ORM models
- migrations
- repositories
- services
- validation
- focused tests
- initial desktop workflows

Acceptance: landlord can create and manage the basic rental structure without direct database interaction.

## Release 0.3 — Utilities

Deliverables:

- electricity fixed/metered
- water no/fixed/metered
- meters
- readings
- tariff history
- meter replacement
- AD/BS handling

Acceptance: valid readings and utility calculations work correctly; invalid readings are rejected; history is preserved.

## Release 0.4 — Billing

Deliverables:

- monthly rent calculation
- utility calculation
- proration
- billing periods
- duplicate prevention
- review/confirmation workflow
- historical calculation integrity

Acceptance: monthly charges are correct and reproducible from stored historical data.

## Release 0.5 — Payments

Deliverables:

- payment entry
- payment methods
- allocation
- partial payment
- overpayment/credit
- outstanding/overdue state
- receipt data

Acceptance: payment balances and allocations remain correct under normal and edge cases.

## Release 0.6 — Expenses and Settlement

Deliverables:

- expense recording
- move-out
- final meter readings
- deposit deductions
- settlement/refund
- agreement closure
- space availability

Acceptance: complete move-out workflow produces a correct final state.

## Release 0.7 — Dashboard and Reports

Deliverables:

- dashboard
- tenant statement
- payment receipt PDF
- monthly summary
- property summary
- meter history

Acceptance: reports use application/service calculations and do not duplicate financial logic.

## Release 0.8 — Hardening

Deliverables:

- authentication/security hardening as applicable
- backup
- restore
- logging improvements
- error handling
- data-integrity review
- regression suite

Acceptance: critical data recovery and integrity scenarios pass.

## Release 0.9 — API Foundation

Deliverables:

- FastAPI application foundation
- `/api/v1`
- authentication
- Pydantic schemas
- selected core endpoints
- OpenAPI documentation
- API tests

Acceptance: API calls the same application services as desktop and passes API/security tests.

## Release 1.0 — Production

Deliverables:

- full regression
- migration validation
- fresh install validation
- upgrade validation
- backup/restore verification
- PyInstaller build
- Windows installer
- documentation
- release notes
- stable Git tag

Acceptance: production release criteria are all satisfied.

## Future Mobile Phase

After stable desktop and API foundations:

- select mobile framework
- build mobile MVP
- consume `/api/v1`
- reuse server business rules
- add mobile-specific UX only

Mobile framework and cloud provider remain intentionally unlocked until this phase.
