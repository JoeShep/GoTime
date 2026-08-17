# NEXT_SESSION

## Current objective: design derived attention

Define the smallest deterministic model that lets GoTime determine what
deserves the user's attention now without requiring manual ranking of every
task. This is a product-design milestone. Do not change application code,
schemas, APIs, persistence, or runtime configuration until the design and
representative baseline cases are reviewed and approved.

The working derived attention states are:

* **Do now**
* **Coming soon**
* **Later**
* **Waiting**

These are calculated states, not manually selected priorities. Their names and
precise rules remain provisional and must be validated against the real family
plan.

Potential deterministic inputs include:

* target and due dates;
* start dates and eligibility;
* dependencies and blocked state;
* progress status and momentum;
* immediate unblocking leverage;
* phase and sequencing context;
* user-specific constraints and consequences; and
* planning lead times and timing windows.

The existing Critical, High, Medium, and Low task priority field is expected to
be demoted or potentially retired from ordinary task creation and
Recommendation ranking. Preserve the field, its API and schema behavior, and
all stored values until replacement behavior is designed and validated.

## Required sequence

1. Define derived attention states and deterministic inputs.
2. Test a no-AI baseline against representative tasks in the real family plan.
3. Identify missing facts that prevent good recommendations.
4. Define a structured planning-knowledge contract for those facts.
5. Revisit and adapt the existing AI API pipeline to supply that contract.
6. Compare AI-enriched recommendations with the deterministic baseline.

The immediate session should stop after the design and no-AI baseline are
specified and reviewed. Do not jump ahead to the knowledge contract or AI
pipeline merely because likely missing facts can already be imagined.

## Future AI-assisted planning knowledge

AI-assisted planning knowledge is an intentional future capability, not an
optional polish item. An AI model may eventually propose structured knowledge
that users cannot reasonably be expected to provide, including typical lead
times, prerequisite patterns, likely durations, and recommended timing windows.

Each consequential knowledge item should be inspectable and carry appropriate
source, confidence, and freshness information. Users must be able to correct
consequential assumptions. Deterministic rules—not an opaque AI response—must
combine planning knowledge with actual family-plan state to produce attention
states and Recommendations.

Routine UI interaction must not invoke AI. Reusable knowledge should be cached,
and live research should occur only when freshness materially matters. Existing
credential boundaries, cost tracking, budgets, and operational-simplicity
principles remain applicable.

This direction does not authorize resuming the frozen moving-service experiment,
adding an AI model call, installing an SDK, accessing credentials, performing
live research, or implementing new AI infrastructure.

## Current implementation baseline

GoTime persists one singleton family relocation plan in SQLite. It supports
four ordered phases and tasks with status, zero or more configured categories,
assignee names, optional dates, stored four-level priority, and direct
dependencies. Blocking is derived. Completed tasks remain in collapsed
per-phase history sections and cannot be introduced as new dependencies.

The React experience supports task creation and full editing, narrow status
changes, dependency selection, a plan-wide finder, multi-category presentation,
and local OR category filtering including derived Uncategorized. Human browser
acceptance has passed for the multi-category and related responsive behavior.

The current stored-task Recommendation is deterministic. It considers only
incomplete, unblocked tasks whose start dates have arrived and orders eligible
tasks by stored priority, due state/date, in-progress status, immediate
unblocking leverage, phase order, and stable task ID. This is the baseline to
evaluate, not the assumed final attention model.

The earlier employment/commute reasoning remains a separate in-memory flow.
The moving-service AI experiment remains frozen with no new execution or
infrastructure authorized.

## Separate parked observations

Do not fold unrelated UX work into derived-attention design. The Parking Lot
retains phase-header Add actions and phase-prefilled creation, dependency
terminology, general task filters, dependency visualization, alternate views,
first-class People, related-task links, editable phases/categories, and
subtasks. Authentication, notifications, multiple goals, and generalized
project infrastructure also remain outside the current increment.

## Data safety and verification context

The verified post-migration backup remains outside the repository at:

`/home/joeshep/backups/gotime/20260817T001021Z-a32c31d-post-migration/`

Do not add that backup, database files, manifest contents, or family-plan data
to Git.

The multi-category implementation and browser refinements are complete in:

* `a32c31d` — multi-category support
* `bc1ba5a` — category interaction refinements
* `9242254` — responsive Bootstrap spacing utilities
* `da1d65e` — wider mobile task lists
* `120b6e8` — browser-acceptance closeout

Historical milestone detail remains in `SESSION_NOTES.md`; do not restore old
“next milestone” instructions to this handoff.
