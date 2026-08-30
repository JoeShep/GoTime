# ADR-0013: Lean deterministic fixed-Milestone timing

## Status

Accepted for candidate implementation on 2026-08-29.

## Decision

GoTime adds optional elapsed-calendar-day ranges to actionable Tasks and a
distinct fixed-date mode to Milestones. A fixed-date Milestone may explicitly
govern at most one phase. No phase may have two unachieved fixed-date anchors.

The relationship is stored in `milestone_governed_phases`; migration assigns
none. Task bounds are nullable, paired integers from 0 through 3,650. Parents
derive remaining duration from their required-subtask graph.

The deterministic calculation expands active top-level phase work through
required subtasks and incomplete dependencies. Sequential dependencies add,
independent branches overlap, joins wait, completed work contributes zero, and
unknown remaining duration makes timing incomplete. Fixed-date states use the
caller-supplied evaluation date. Timing contributes a bounded signal only to
the actionable critical frontier; overdue and due-today work stays protected.
Stored Task dates are never rewritten.

## Boundary

This slice excludes multiple phases, roots, exclusions, Decision-option
scenarios, date-setting prompts, capacity scheduling, generated estimates, AI,
research, calendars, and notifications. Target windows retain their existing
behavior and do not run backward calculation.
