# ADR-0010: Persist required subtasks and derive parent Task status

## Status

Accepted for the first derived-attention Increment 2 slice.

## Context

GoTime needs to represent an outcome-oriented Task as a summary over required,
independently actionable work. The existing Task table has no hierarchy and its
stored status is directly editable. Adding a parent identifier to every Task
would mix relationship lifecycle and ordering into the Task record, while
rewriting stored status on every child mutation would lose the ordinary status
needed when the final child is detached.

The approved behavior also gives the user final authority: a parent normally
tracks its children, but a conflicting manual status may be confirmed and must
remain visible until explicitly returned to automatic behavior. This replaces
the earlier technical-design proposal to defer direct parent overrides.

## Decision

Add two relationship tables through one transactional, idempotent repository
migration:

* `task_hierarchy(child_task_id, parent_task_id, position)` stores one required
  parent and user-controlled sibling order;
* `task_parent_status_overrides(parent_task_id, status)` stores only a confirmed
  manual parent override.

No existing Task is related automatically. Repository validation enforces one
level, one parent, and a shared phase. A child cannot move phase independently;
moving a parent moves its children only after confirmation.

The existing `tasks.status` remains the durable ordinary/leaf status. A parent
without an override projects an automatic status from all children: all Not
started is Not started, all Completed is Completed, and every other mixture is
In progress. A confirmed override becomes the effective parent status until
the user returns it to automatic status. Detaching the final child copies the
parent's current effective status into `tasks.status` before the relationship
is removed, preserving its meaning as an ordinary Task.

Dependencies on a parent use its effective status. A parent's prerequisites
also block each child, while a child's own dependencies continue to apply.
Parent summaries are excluded from phase counts and Recommendations; children
remain ordinary candidates. Finder and Recommendation reveal expand the parent
group around a targeted child.

The API projects stored, automatic, manual, and effective status explicitly.
Conflicting parent status and parent phase changes use stable 409 responses so
the client can warn and retry with an explicit confirmation. Returning to
automatic status is a narrow mutation.

## Consequences

Positive:

* Existing Task records and display fields remain intact and attach/detach is
  lossless.
* Rollup and dependency behavior are deterministic and reversible.
* Manual authority is explicit instead of silently drifting from child state.
* Additive tables can remain empty until family-plan relationships are chosen.

Negative:

* Effective status must be projected consistently anywhere Tasks are read.
* Legacy application versions cannot understand relationships created later.
* SQLite check-and-write mutations remain serialized at the repository boundary.

Deferred:

* nested or optional subtasks;
* Decision evidence/readiness and contextual Recommendation explanation;
* conditional activation and family-plan conversion.
