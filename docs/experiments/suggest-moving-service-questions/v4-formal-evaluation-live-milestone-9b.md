# Frozen-v4 formal evaluation Milestone 9B

Date: 2026-08-13

Status: implemented offline; awaiting human diff review. No live provider
operation, real credential, or Milestone 10 operation is authorized.

## Generation result lifecycle

Milestone 9B preserves the Milestone 8 atomic provider boundary and begins only
after the approved Milestone 9A review has produced the existing generation
eligibility binding:

`provider_dispatch_started` durable and consumed
→ provider outcome returned in memory
→ canonical frozen-v4 classification and validation
→ one bounded result and closure transition
→ validated evidence retained only for a machine-valid response
→ generation provider phase closed
→ validated case waits for Milestone 10 generation-evidence review.

The fixed generation execution entry calls this handler directly. There is no
human result-ingestion command and no second provider call. The coordination
CLI remains the same ten commands.

## Schemas, operations, and fixed synthetic identities

- Result schema: `suggest-moving-service-questions-v4-formal-evaluation-generation-result-v1`, version 1
- Evidence schema: `suggest-moving-service-questions-v4-formal-evaluation-generation-result-evidence-v1`, version 1
- Closure schema: `suggest-moving-service-questions-v4-formal-evaluation-generation-phase-closure-v1`, version 1
- Case-01 valid-result digest: `6add9501abe6fe0e52ce8d9e030afda0871187c2a1badf4b7d8f1fd299c9c637`
- Case-01 validated-evidence digest: `db870d3ad854ba4a3f044f4be12180f10c6e98ded63f2988970844786d96dc80`
- Case-01 phase-closure digest: `246d4eb519b8511fdf05c7ae8af3f134a63f16fa03e5a506369b5d4a051a514c`

The history operations are `generation_result_validated`,
`generation_validation_failed`, and `generation_provider_failed`. Each event
atomically retains its exact result, optional valid evidence, and closure. The
result/evidence bind the aggregate, case, envelope, generation grant and
reservation, actual retained generation dispatch event, frozen request and
attempt, provider fingerprint, provider/model/SDK, classification, and time.

The new result collections are introduced only by the first 9B transition.
Pre-9B projections retain their exact historical shape, so all approved
Milestone 9A result/evidence/review digests remain unchanged.

## Canonical validation and classification

The handler reuses `v4_formal_evaluation_runner.validate_case_response` and the
unchanged frozen-v4 models. The order remains response extraction/Pydantic
validation, semantic validation, prose validation, exact grounding validation,
and then the frozen version-2 fallback selection for content failures.

Outcomes remain distinct:

- `validated`: bounded structured response and evidence; status
  `awaiting_generation_evidence_review`;
- `structural_failure`, `semantic_failure`, or `prose_failure`: bounded machine
  rejection plus the exact frozen fallback identity; and
- `timeout`, `transport_error`, `provider_error`, or `outcome_unknown`: bounded
  provider failure without fallback or validated evidence.

Prose failure retains only content-free canonical violation codes and bounded
diagnostics (rule, field, offsets, trigger, and count). Rejected prose and the
arbitrary raw provider payload are not durable. Valid evidence retains only the
validated structured response needed by the later Milestone 10 review. No
credential, header, prompt/request body, environment dump, client object, or raw
exception representation is persisted.

Replay derives the diagnostic contract from the frozen validator constants. It
requires canonical codes and order, rule ID, allowed code-specific fields and
triggers, exact scalar types, nonnegative and bounded offsets/counts, valid
start/end spans, exact code-to-diagnostic correspondence, and the exact required
field set. Fully rehashed unknown-code, wrong-rule, wrong-field, negative or
excessive count/offset, short-span, oversized-trigger, and reordered-diagnostic
records fail closed. Canonical frozen diagnostics replay unchanged.

## Idempotency, replay, and recovery

One consumed generation dispatch permits one result. An exact rerun is
event-free; a conflicting result fails before mutation. Replay independently
requires the result dispatch digest to equal the actual retained generation
`provider_dispatch_started` event. Fully rehashed wrong-dispatch, wrong
envelope/grant/reservation/request/attempt/provider, evidence-drift,
missing-dispatch, and retained-result replacement/deletion attacks fail closed
relative to the retained ADR-0005 journal head.

If dispatch is durable but result history is absent after a crash, the derived
state is `dispatch_consumed_result_missing`: the attempt and monetary exposure
remain consumed, release and retry remain prohibited, and no result is
fabricated. If result history commits before projection replacement, fresh
replay reconstructs the exact result, evidence, closure, and pending-review
case state.

## Milestone boundaries

Machine-valid evidence closes the generation provider phase but does not close
the human lifecycle. The case remains blocked with generation evidence review
pending and cannot advance. Milestone 10 still owns generation-evidence human
grounding/quality review, evidence deletion, and the separate 24-hour deadline.
Milestone 9B implements none of those operations.

Application, workflow, SDK, and GoTime-controlled transport retries remain
zero. Permanent execution authorization remains
`closed_no_execution_authorized`. All rehearsals are synthetic and
network-disabled; real provider operations and real credentials are zero.

After this checkpoint is reviewed and committed, top-level Milestone 9 is
complete. The mandatory Temporal/Inngest/LangGraph reassessment is then the next
architectural activity and must occur before Milestone 10. Build-vs-adopt
remains `defer_adoption` through the entirety of Milestone 9.

## Validation

- dedicated Milestone 9B: 32 passed;
- focused Milestones 8–9B integration: 71 passed;
- focused authoritative state/generation/dispatch regression: 91 passed;
- apples-to-apples full offline experiments: 1,305 passed, 2 historical
  Docker-daemon-dependent skips;
- frozen foundation/permanent closed manifest: passed;
- read-only Python compilation, replay/history integrity, and scoped diff
  checks: passed.

The full suite used the existing pinned OpenAI 2.45.0 image with networking
disabled and the existing host zsh mounted read-only, matching the established
Milestone 8/9A-capable environment. Synthetic generation provider-entry counts
are exactly one in each dispatched outcome test. Real provider operations and
real credentials remain zero.
