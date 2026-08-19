# NEXT_SESSION

## Current objective: complete Increment 1 safely

Implement only the approved Milestone and Decision foundation in
[ADR-0008](docs/adr/ADR-0008-derived-attention-foundation.md) and the
[technical design](docs/technical-design/derived-attention-vertical-slice.md).

The active database is protected by the verified pre-Increment-1 backup at
`/home/joeshep/backups/gotime/20260819T015944Z-10a7ead-pre-increment-1/`.
The normal backend is stopped and must remain stopped; candidate migration may
run only on test databases and isolated restored volumes.

Increment 1 adds empty Milestone, Decision, and ordered-option persistence to
existing databases; explicit schemas and focused APIs; compact create/edit and
state controls; and tests. It does not create real family-plan records or
convert `Put current home on the market`.

Do not begin hierarchy, evidence links/readiness, activation, inactive-work
views, Decision impact handling, derived Recommendations, family-data
conversion, AI, financial calculations, or removal behavior.

The governing principle remains:

> GoTime may derive, recommend, explain, and warn, but the user retains final
> authority.
