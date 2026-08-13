# Frozen-v4 formal evaluation Milestone 9A

Date: 2026-08-12

Status: implemented offline; awaiting human diff review. No live provider
operation or generation provider operation is authorized.

## Result lifecycle

Milestone 9A extends the unchanged Milestone 8 preflight boundary:

`provider_dispatch_started` durable and consumed
→ provider outcome returned in memory
→ bounded classification/validation
→ durable result and, for success, bounded evidence
→ review pending with generation eligibility false
→ explicit human preflight evidence review
→ durable immutable decision
→ reviewed terminal preflight phase.

The provider result is handled in the same controlled execution call stack. A
human never copies or submits raw provider output. The sole human step is the
separate preflight evidence review between the completed preflight operation
and any later generation operation.

## Schemas and fixed case-01 identities

- Result: `suggest-moving-service-questions-v4-formal-evaluation-preflight-result-v1`, version 1
- Evidence: `suggest-moving-service-questions-v4-formal-evaluation-preflight-result-evidence-v1`, version 1
- Review: `suggest-moving-service-questions-v4-formal-evaluation-preflight-evidence-review-v1`, version 1
- Closure: `suggest-moving-service-questions-v4-formal-evaluation-preflight-phase-closure-v1`, version 1
- Fixed-time case-01 result digest: `f201e07af862bcdfcdfba8d7baeb544d3ff4b6045d49fd140e66a15dbdf7bcac`
- Fixed-time case-01 evidence digest: `449b336abd271eff6697df20828fb8254a569c28993411098f2aee1be535c1af`
- Fixed-time approved-review digest: `aa39e8d302a6cba5f79a83847b865ccbdb585cd03fff6b0d5ccf4995f0158004`

Each identity is canonical SHA-256 over its versioned immutable content. The
result binds aggregate, case, envelope, preflight grant/reservation, exact
dispatch event, request/attempt/provider identities, provider/model/SDK,
classification, token count, local exposure, and timestamp. No secret is bound.

Case 01 accepts the canonical 2,852 input tokens. Its conservative generation
exposure remains locally derived from frozen pricing and request configuration:
`$0.0019408`. Provider-returned price is not accepted.

## Authoritative operations and closure

The explicit journal operations are:

- `preflight_result_validated`: atomically retains the bounded validated result,
  evidence, and a `review_pending` provider-phase closure;
- `preflight_provider_failed`: retains only a bounded failure classification and
  terminal provider-failed closure; and
- `preflight_evidence_reviewed`: retains the exact human decision, replaces only
  the pending closure with its terminal reviewed closure, and creates the
  existing generation evidence binding only for approval.

Exact result/review reruns are event-free. Conflicting outcomes or decisions
fail before mutation. Retained results, evidence, reviews, and terminal closures
cannot be deleted or replaced by later transitions relative to the retained
ADR-0005 journal head.

Replay requires every `preflight_result_validated` event to contain both its
validated result and exact matching evidence as one inseparable transition; a
validated result cannot be reinterpreted through a provider-failure closure.
The result and evidence dispatch identity must also equal the actual retained
`provider_dispatch_started` event at the authoritative before-state journal
head, rather than merely containing a valid-looking downstream SHA-256.

Provider execution and review consequences remain distinct:

- valid result: evidence exists, `review_pending`, generation ineligible;
- timeout, transport error, provider error, unknown outcome, or invalid result:
  consumed attempt, bounded failure, no reviewable evidence, no generation;
- review `approve`: terminal approved closure and exact generation binding;
- review `reject`: terminal rejected closure, generation ineligible;
- review `request_changes`: terminal changes-requested closure, generation
  ineligible, with no retry or replacement preflight.

## Canonical human preflight evidence review

The fixed provider-free entry point is:

`scripts/experiments/suggest_moving_service_questions/review_v4_formal_evaluation_live_preflight_evidence_docker.sh`

It resolves the current case and evidence from authoritative state. It accepts
only the canonical review fields: aggregate reviewer identity, decision,
reviewed-at timestamp, four explicit confirmations, and bounded notes. It
accepts no case, evidence digest, provider, model, request, grant, reservation,
budget, credential, or provider-operation override.

Decisions are exactly `approve`, `reject`, and `request_changes`. All decisions
require a nonempty canonical reviewer and nonempty notes of at most 500
characters. Approval requires all four confirmations independently:

- token count plausible;
- cost within limit;
- frozen bindings confirmed; and
- evidence history confirmed.

The review timestamp cannot predate evidence or be in the future. The canonical
preflight review deadline comes from `v4_sequence_1_preflight.py`: evidence
creation plus exactly 15 minutes. Approval requires both the review timestamp
and current time to be strictly before that boundary; approval at or after the
deadline fails closed. This is not Milestone 10's separate 24-hour generation
evidence lifecycle.

Machine validation never sets generation eligibility. Only the exact approved
review creates the existing
`suggest-moving-service-questions-v4-formal-evaluation-preflight-evidence-binding-v1`
record with `generation_gate_binding_eligible=true`. The real production state
path can then prepare a generation grant, but Milestone 9A never enters or
dispatches generation.

## Privacy and recovery

Arbitrary provider payloads and exception text are not durable. Evidence
retains only bounded identities, the token count, locally derived exposure, and
timestamps. It excludes credentials, authorization headers, request/prompt
content, environment data, HTTP headers/client representations, and arbitrary
response metadata.

If dispatch is consumed but no result history exists after a process loss,
state derives `dispatch_consumed_result_missing`: retry and release remain
false, no result is fabricated, and generation remains ineligible. If result or
review history commits before projection interruption, fresh replay restores
the exact state without another provider call or event.

## Boundaries

The coordination CLI remains exactly ten commands. The human review action is a
separate fixed entry point and performs no credential access or provider call.
The historical Milestone 7 synthetic evidence operation remains test-only and
production replay continues to reject it.

Permanent status remains `closed_no_execution_authorized`. Tests use network
disabled synthetic preflight entry only. Real provider operations, real
credentials, and generation provider entries are all zero. Milestone 9B—not
this milestone—owns generation execution/result validation and is next after
9A review and commit. The framework reassessment remains after committed 9B,
when top-level Milestone 9 is complete, and before Milestone 10. Milestone 10's
generation evidence review/deletion/deadline lifecycle remains unimplemented.
