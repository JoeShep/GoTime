# NEXT_SESSION

## Current objective: approve the derived-attention technical design

Review the
[vertical-slice technical design](docs/technical-design/derived-attention-vertical-slice.md)
and approve or revise its domain, persistence, migration, reasoning, API,
interface, and implementation-increment choices before any implementation.

The reference Milestone is **Start selling our home**. The existing `Put
current home on the market` Task should become that Milestone without leaving a
duplicate action Task. Public-listing and builder-outreach actions belong in
conditional branches.

## Decisions requiring approval

* Use an independent Milestone domain concept and preserve the old Task's
  stable ID value during conversion.
* Resolve the home-sale Decision with one selected option, including a named
  parallel option, rather than multiple simultaneous selections.
* Derive activation from option associations plus a user keep-active override.
* Let derived Do now work outrank the legacy priority-first fallback while
  preserving existing priority data.
* Use a human-readable target window initially; defer structured date bounds
  until meaningful precision exists.
* Keep inactive Completed work outside ordinary counts/views but available
  through Show inactive work and finder/history.
* Review the farewell-party and notice/PTO relationship meanings before any
  family-data migration; the latter remains unclear.

The proposed sequence has four separately approved increments: Milestone and
Decision foundation; required subtasks/evidence/readiness; conditional
activation and safe revision; then rehearsed family-plan conversion and full
acceptance.

Do not define tables, Pydantic schemas, endpoint signatures, or components—and
do not change code, tests, runtime, or family data—until this design is
approved. A technical ADR may be appropriate after approval.

The governing principle remains:

> GoTime may derive, recommend, explain, and warn, but the user retains final
> authority.
