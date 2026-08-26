# ADR-0011: Link preparation Tasks to Decisions and derive advisory readiness

## Status

Accepted and deployed for the second derived-attention Increment 2 slice on
2026-08-26.

## Context

A family Decision often depends on completing ordinary work first. That work
must remain independently actionable and recommendable; readiness must advise
rather than take the Decision away from the user.

## Decision

Persist a normalized many-to-many `decision_preparation_tasks` relationship
with `(decision_id, task_id)` uniqueness, foreign keys, and a Task lookup index.
The additive migration is transactional, idempotent, and creates no links.

Readiness is projected from current links and each Task's effective status.
Zero links means **No preparation tracked**; any incomplete Task means
**Preparation incomplete**; one or more links all completed means **Ready to
decide**. Parent Tasks honor derived/manual effective status. Links never create
dependencies or mutate Tasks.

Decision create/edit validates the complete set in its SQLite write
transaction. Unknown, cross-Plan, duplicate, and parent/child pairs are
rejected. Hierarchy attachment also rejects a prospective parent and child
already linked to the same Decision and names the Decision to edit first.

Selecting or revising an option while not ready requires explicit accessible
confirmation; clearing a selection does not. Readiness neither selects nor
endorses an option and does not assess evidence quality.

The Decision editor owns relationship management. Cards show resolution and
readiness separately, preserve collapsed preparation expansion in versioned
session state, and reuse Plan's transient Task targeting for **View task**.

## Consequences

Readiness responds immediately without duplicated stored state. Older clients
cannot display created links. Contextual Recommendations, structured evidence,
conditional activation, and family-data conversion remain deferred.
