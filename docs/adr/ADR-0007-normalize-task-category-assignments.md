# ADR-0007: Normalize optional task category assignments

## Status

Accepted for the multi-category task enhancement.

## Context

The singleton relocation plan originally required one bounded category stored
directly on each task. A task now needs zero or more equal category labels.
Selection order must not affect display order, duplicate assignments are
invalid, and existing single-category data must survive the change.

## Decision

Keep the six configured relocation categories as the bounded `TaskCategory`
enum and replace the scalar task field with a required `categories` collection
in create, full-replacement, and response schemas. An empty collection means
uncategorized; `Uncategorized` is never stored as a category.

Persist assignments in `task_categories`, keyed by `(task_id, category)`, with
a foreign key to `tasks` and the same bounded category constraint. The table
does not store a position because assignment order has no product meaning.
Application validation and repository reads return assignments in the
configured category order.

Opening a scalar-category database transactionally rebuilds the task and
relation tables and inserts each former scalar value as one assignment.
Legacy `administrative` values become `logistics` during that same migration.
Schema detection makes the migration idempotent.

The frontend category filter is local view state over the already-loaded plan.
It does not change persistence, task identity, or recommendation inputs.

## Consequences

Positive:

- Tasks may be uncategorized or carry any combination of configured labels.
- Database and model validation both prevent duplicate or unknown assignments.
- Existing assignments and all non-category task data remain intact.
- Category ordering is deterministic and independent of selection order.
- Recommendation logic remains unchanged.

Negative:

- The coordinated API contract changes from `category` to `categories`.
- Databases migrated to the normalized schema cannot be opened by an older
  application version that requires `tasks.category`.
- User-configurable categories remain a separate future schema decision.
