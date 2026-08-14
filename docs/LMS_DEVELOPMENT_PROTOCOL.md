# LMS Development Protocol — OpenCode + Nemotron Ultra

**Status:** LOCKED DEVELOPMENT RULESET

This document controls how the LMS implementation is performed. The Master Specification is the product source of truth; this document is the implementation behavior contract.

## 1. Inspect Before Acting

Before modifying an existing milestone, inspect the current repository, relevant files, migrations, tests, configuration, and Git status. Do not assume a file exists or that an earlier implementation is correct.

## 2. Respect Locked Decisions

Do not casually change:

- technology stack
- architecture
- module boundaries
- business rules
- database philosophy
- financial history rules
- API/mobile strategy

If a genuine conflict is discovered, stop and report it rather than silently redesigning.

## 3. Work One Milestone at a Time

Only implement the current release/milestone. Do not jump ahead into future functionality unless a dependency is strictly required and documented.

Each milestone must end in a testable state.

## 4. No Feature Creep

Do not add:

- SMS
- WhatsApp
- payment gateways
- complex accounting
- cloud synchronization
- advanced offline sync
- microservices
- unnecessary dashboards/charts
- unnecessary configuration tables/screens

unless the active specification explicitly requires them.

## 5. No Overengineering

Avoid unnecessary:

- abstract base classes
- factories
- interfaces
- dependency frameworks
- event buses
- CQRS infrastructure
- microservices
- duplicated models

Use the simplest professional design that satisfies the specification.

## 6. Architecture Boundaries

- UI calls application services.
- API routes call application services.
- Services contain workflows/business operations.
- Domain contains business rules.
- Repositories handle persistence.
- SQLAlchemy models stay in infrastructure/persistence.
- API schemas stay separate from ORM models.
- Reports consume service/application data.

Never place SQL directly in PySide6 views or API route handlers.

## 7. Financial Safety

Financial data includes charges, payments, meter readings, tariffs, agreements, deposits, and settlements.

Never destroy or silently rewrite financial history to make current data convenient.

Use controlled corrections/history where required.

Financial operations must be transactional.

## 8. Database Rules

- PostgreSQL is the production database.
- SQLAlchemy 2.x is the ORM.
- Alembic is the migration mechanism.
- Schema changes require migrations.
- Do not manually modify production tables as a normal development shortcut.
- Use constraints where appropriate for data integrity.

## 9. Testing Rules

Never mark work complete merely because the program launches.

For each milestone:

1. implement
2. run focused tests
3. fix failures
4. run relevant regression tests
5. verify acceptance criteria
6. report results

Never delete or weaken a test simply to make an implementation pass.

## 10. Error Handling

Expected business errors should become meaningful domain/application exceptions and user-friendly messages.

Do not use broad silent handlers such as `except Exception: pass`.

Unexpected errors must be logged at the correct application boundary.

Do not expose Python tracebacks to normal end users.

## 11. Configuration

Do not hardcode database passwords, API secrets, or environment-specific paths.

Use the project configuration layer and `.env.example` for documented environment variables.

## 12. Git Discipline

Keep commits small and meaningful.

Preferred sequence:

`feature -> tests -> review -> merge -> release tag`

Do not mix unrelated changes into one milestone commit.

Do not rewrite published history unless explicitly requested.

## 13. Token-Efficient Reporting

Do not repeatedly print the entire architecture or unchanged files.

After a task, report only:

1. Objective
2. Files changed
3. Important implementation decisions
4. Tests run and results
5. Acceptance criteria status
6. Remaining blocker, if any

Show complete file contents only when specifically needed.

## 14. Preserve Existing Functionality

When modifying an existing feature, preserve working behavior unless the locked specification explicitly changes it.

Run regression tests after significant changes.

## 15. Stop on Ambiguity

If a requirement is genuinely ambiguous and the decision materially affects architecture, financial correctness, database design, or user workflow:

- identify the ambiguity
- explain the conflict
- propose the smallest safe options
- stop for approval

Do not invent a new permanent business rule.

## 16. Definition of Done

A task is done only when:

- code is implemented
- architecture boundaries are respected
- required migrations exist
- required tests pass
- acceptance criteria pass
- no known critical regression remains
- documentation is updated when needed

## 17. Release Discipline

A release candidate requires the tests and checks specified by the Master Specification. Production release additionally requires fresh installation, upgrade, migration, backup/restore, and critical end-to-end workflow verification.

## 18. First Principle

When choosing between two technically valid implementations, prefer the one that is:

- simpler
- easier to test
- easier to maintain
- easier for a small landlord to use
- consistent with the locked architecture

Do not optimize for theoretical scale at the expense of simplicity.
