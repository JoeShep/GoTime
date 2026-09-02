# ADR-0013: Reject phase-wide fixed-Milestone timing

## Status

Rejected after human acceptance review on 2026-09-02. The prototype commits
remain in Git history but were never deployed.

## Context

The prototype applied one fixed Milestone date to every active Task in one
selected Phase and used optional Task elapsed-time ranges for backward
scheduling. Human review found that this collapsed the distinction between an
organizational Phase and an outcome Milestone, duplicated Plan and Now inside a
timing panel, made optional estimates feel required, and gave advisory duration
estimates too much apparent Recommendation weight.

## Decision

Do not ship phase-wide Milestone timing or Task duration estimates in the
family MVP. Phases organize related work; their order is not a hard dependency.
Task dependencies express required sequencing and may cross Phases. Real Task
**Due by** dates provide explicit calendar pressure and may propagate backward
through actual dependencies. **Do not recommend before**, status, actionable
unblocking, Decision readiness and preparation, and the accepted deterministic
ranking remain authoritative. Phase order remains only stable ordering/tie
context. No runtime AI is required.

GoTime must not apply a Milestone date automatically to an entire Phase, treat
missing estimates as incomplete user work, list every Phase Task in a
Milestone timing panel, let duration estimates appear to dominate
Recommendations, or blur Phase organization with Milestone outcomes.

## Future timing boundary

If forecasting returns, a Milestone will relate only to explicitly selected
outcome-critical work. Dependencies may pull in required prerequisites across
Phases. Estimates remain optional; missing estimates reduce forecast confidence
instead of creating a checklist-like demand. The interface should summarize
useful conclusions rather than duplicate Plan, and timing-derived attention
must remain advisory and secondary to real deadlines and actual dependencies.
Any new design must be validated with real family use before implementation.
