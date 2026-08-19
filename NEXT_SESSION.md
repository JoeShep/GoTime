# NEXT_SESSION

## Current objective: review Increment 1 before active migration

Review the implemented Milestone and Decision foundation in
[ADR-0008](docs/adr/ADR-0008-derived-attention-foundation.md) and the
[technical design](docs/technical-design/derived-attention-vertical-slice.md).

The active database is protected by the verified pre-Increment-1 backup at
`/home/joeshep/backups/gotime/20260819T015944Z-10a7ead-pre-increment-1/`.
The normal backend is stopped and the active database remains unmigrated.
Automated suites, the production frontend build, and a twice-started isolated
candidate migration rehearsal passed without changing any original row.

The next approval is permission to run this reviewed additive migration against
the active database and restart the normal stack. Then perform human browser
acceptance. Do not create real Milestones or Decisions or convert `Put current
home on the market` as part of that operational step.

Do not begin hierarchy, evidence links/readiness, activation, inactive-work
views, Decision impact handling, derived Recommendations, family-data
conversion, AI, financial calculations, or removal behavior.

The governing principle remains:

> GoTime may derive, recommend, explain, and warn, but the user retains final
> authority.
