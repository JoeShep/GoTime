# ADR-0008: Establish the milestone and decision foundation

## Status

Accepted for derived-attention Increment 1.

## Context

GoTime's current relocation plan persists executable Tasks and derives one
priority-first Recommendation. The home-sale reference scenario demonstrates
that answering “What should I do next?” also requires real-world outcomes,
user-owned choices, conditional work, and explanations connecting work to
purpose.

Increment 1 establishes only the durable Milestone and Decision foundation.
Task hierarchy, evidence links, readiness, conditional activation, inactive
work, and derived-attention Recommendation changes follow in later approved
increments.

## Decision

Add independent Milestone and Decision domain concepts to the singleton
relocation plan rather than treating either as a specialized Task.

A Milestone has a stable identifier, title, optional description, optional
earliest and latest target dates, and explicit user-confirmed achievement. The
date meanings are:

* equal earliest and latest dates represent an exact target;
* two different dates represent a bounded target window;
* earliest only represents open-ended timing such as after New Year; and
* neither date means timing is unknown.

A latest date without an earliest date is invalid, as is a latest date before
the earliest date. Milestone timing is planning guidance, not Task eligibility,
a start date, or a hard deadline. Achievement and reversal are narrow,
explicit user actions; completing related work cannot confirm a real-world
outcome.

A Decision has a stable identifier, title, optional description, one related
Milestone, and at least two ordered options. It is unresolved when no option is
selected and resolved when exactly one option is selected. A combined strategy
such as public listing plus builder outreach is represented as one named
option, not simultaneous selection of several options. Selection, revision,
and return to unresolved are explicit user actions. Neither deterministic
reasoning nor an AI model may select an option for the user.

Increment 1 persists these concepts in normalized SQLite structures and
returns them in the existing relocation-plan aggregate. It uses explicit
Pydantic request and response schemas, full-replacement edits for definitions,
and narrow state-change operations for achievement and selection. Ordered
options retain stable identifiers. Foreign keys, uniqueness, range checks, and
transactional validation protect relationships.

Create explicit indexes for Milestone-by-plan, Decision-by-plan, and
Decision-by-Milestone reads. Ordered Decision options are already covered by a
unique Decision/position constraint, so no redundant index is added.

The approved home-sale plan eventually contains two real-world Milestones:
**Start selling our home** and **Our home is under contract**. The existing
`Put current home on the market` Task will later be converted to the first
Milestone while preserving its stable identifier and traceable migration
evidence. Increment 1 creates no records and does not convert family data.

When later increments add derived attention, legacy
Critical/High/Medium/Low values remain stored and displayed during transition
but do not influence derived Do now selection. Conditional activation will be
derived from the selected option while allowing explicit keep-active
exceptions, and completed inactive work will remain available as history.

The user-authority rule governs every increment:

> GoTime may derive, recommend, explain, and warn, but the user retains final
> authority.

## Initial boundaries

Increment 1 does not add:

* parent Tasks or subtasks;
* evidence-producing work relationships or advisory Decision readiness;
* conditional Task activation or inactive-work presentation;
* Decision-revision handling for affected Tasks;
* derived-attention Recommendation changes;
* family-plan conversion;
* AI assistance or financial calculations; or
* removal and no-longer-applicable semantics.

The existing `Put current home on the market` Task and every current
relationship remain unchanged.

## Migration and compatibility

The schema migration is transactional, idempotent, and additive. Existing
normalized databases receive empty Milestone, Decision, and Decision-option
structures. Empty databases create the same final schema. Partially present or
unexpected structures fail closed. Existing Task, category, assignee, and
dependency rows remain unchanged.

An older backend can ignore unused additive tables, but it cannot safely
interpret Milestone or Decision records once users create them and will not
return those records to an older frontend. Future family-data conversion and
activation/hierarchy increments will be explicitly incompatible and require a
verified pre-migration backup for rollback.

Before candidate migration testing, the active database is backed up with
SQLite's online backup API and verified in an isolated Docker volume. Candidate
code never runs against the active volume until separately approved.

## Consequences

Positive:

* Real-world outcomes are distinct from executable work.
* Target windows can remain intentionally imprecise.
* Users retain explicit authority over achievement and choices.
* Ordered options and singular selection make Decision state deterministic.
* Later hierarchy, readiness, activation, and explanation work has stable
  concepts to reference.
* Existing Task contracts and data remain unchanged in Increment 1.

Negative:

* The plan aggregate and interface gain two new concept types and focused
  mutation flows.
* Older clients do not see Milestones or Decisions.
* Option replacement must protect an already selected option from accidental
  deletion.
* Once real Milestone/Decision records are created, code rollback may hide
  information even though the additive database remains readable.
