# ADR-0006: Persist the singleton MVP relocation plan in SQLite

## Status

Accepted for MVP Increment 1A.

## Context

GoTime's first product slice kept a hard-coded relocation scenario and user
inputs only in process/browser memory. The next useful product increment needs
one real family relocation plan to survive backend restarts. Authentication,
multiple goals, concurrent organizations, and generalized project management
remain out of scope.

## Decision

Use Python's standard-library SQLite support for one fixed relocation plan.
Persist the plan, its fixed ordered phases, tasks, task assignees, and task
dependencies in a small normalized schema. Keep persistence behind a dedicated
repository and expose only fixed relocation-plan API routes.

Task creation may use documented defaults. Task `PUT` is a full replacement:
every replaceable field must be present, including nullable description and
date fields. Omission is invalid; an explicit `null` intentionally clears a
nullable value. Status has its separate narrow `PATCH` operation.

Task status, category, and priority use bounded application enums backed by
SQLite constraints. A task's blocked state is derived at read time: a
non-completed task is blocked when any dependency is not completed. Blocked
state is not stored or directly editable.

The default Docker Compose environment stores the database in a named volume.
Tests use isolated temporary SQLite databases.

## Consequences

Positive:

- The family plan survives backend process/container restarts.
- No database service, ORM, authentication system, or deployment platform is
  required.
- Foreign keys and transactions keep phase/task/dependency changes coherent.
- The repository can later be replaced without coupling domain models to SQL.

Negative:

- The schema deliberately supports only one relocation plan.
- Phase editing and the frontend task-management experience remain deferred.
- SQLite is not selected here as a future multi-user or public-scale database.
