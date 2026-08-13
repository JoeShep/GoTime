# Frozen-v4 formal evaluation Milestone 9 ownership reconciliation

Date: 2026-08-12

Status: design clarification awaiting human review; Milestone 9 implementation
remains paused.

## Decision

Preserve the committed eighteen-milestone plan and refine top-level Milestone 9
into two separately reviewed and committed implementation checkpoints:

1. **Milestone 9A — Preflight result validation and reviewed-evidence gate**
2. **Milestone 9B — Generation result validation and provider-phase closure**

Top-level Milestone 9 is complete only when both checkpoints are committed.
Milestones 10–18 are not renumbered.

This record clarifies ownership and ordering; it does not revise the committed
implementation plan, architecture memo, frozen artifacts, or runtime behavior.

## Lifecycle dependency

The authoritative sequence is:

`preflight provider_dispatch_started`
→ provider outcome classification
→ validated, bounded preflight evidence
→ explicit human preflight evidence review
→ approved review establishes `generation_gate_binding_eligible`
→ generation grant and execution may become structurally eligible
→ generation provider outcome classification and machine validation
→ bounded validated generation evidence
→ Milestone 10 generation evidence review/deletion lifecycle

Machine validation is not equivalent to preflight evidence review. A generation
grant continues to require the exact evidence and its approved review record.

The human action between the completed preflight phase and a later generation
phase does not weaken Milestone 8's atomic boundary. Milestone 8 prohibits a
human gap between a single operation's durable `provider_dispatch_started` and
its immediate SDK entry; it does not prohibit deliberate human coordination
between two independently granted provider phases.

## Canonical preflight evidence review

Milestone 9A must reuse the frozen-v4 preflight review model established in
`v4_sequence_1_preflight.py`. The review:

- binds the exact preflight evidence digest and completed lifecycle history;
- binds the exact case, request, canonical attempt, provider fingerprint,
  frozen manifest, provider, model, SDK, prompt/schema, and provider-schema
  identities;
- records the exact input-token count and locally derived conservative maximum
  generation cost;
- requires a nonempty reviewer identity;
- accepts only `approve`, `reject`, or `request_changes`;
- requires the four explicit confirmations: token-count plausibility, cost
  within limit, frozen bindings confirmed, and evidence history confirmed;
- requires bounded, nonempty notes as specified by the canonical model;
- records a review timestamp after evidence creation and before the canonical
  15-minute preflight evidence-review deadline;
- is one-time and rejects absent, changed, already-reviewed, late, or
  cross-bound evidence; and
- sets `generation_gate_binding_eligible=true` only for an approved decision
  with all required confirmations.

The review cannot edit provider result content or fabricate evidence. Its
operator action must select the authoritative current evidence from state and
accept only the canonical review fields. It performs no provider operation and
grants no provider authority by itself. The durable review record is the exact
human approval prerequisite later bound by the generation grant.

The 15-minute preflight evidence-review window is part of the existing
preflight gate. It is distinct from Milestone 10's 24-hour retention deadline
for validated generation evidence.

## Milestone 9A scope

Milestone 9A owns:

- preflight provider outcome classification;
- exact preflight result validation;
- bounded preflight evidence creation;
- the canonical explicit human preflight evidence review and durable decision;
- generation-gate eligibility only after an approved exact review;
- preflight provider-phase closure;
- timeout, transport, provider-error, and indeterminate failure outcomes;
- one-attempt/one-result semantics, retained-head integrity, and zero retries;
  and
- the production evidence bridge needed for later generation-grant
  preparation.

Milestone 9A does not execute generation, validate generation output, implement
generation evidence review/deletion, authorize live execution, or begin
Milestone 10.

## Milestone 9B scope

Milestone 9B begins only after committed 9A can establish legitimate production
generation eligibility. It owns:

- generation execution through the unchanged Milestone 8 boundary, still
  subject to separate live authorization;
- generation provider outcome classification;
- the unchanged Pydantic/schema, semantic, and prose validation pipeline;
- frozen fallback behavior and bounded content-free rejection diagnostics;
- bounded validated generation evidence;
- one-attempt/one-result and zero-retry semantics;
- provider-phase closure and already-specified terminal machine outcomes; and
- the exact `awaiting human review/deletion` handoff to Milestone 10.

Milestone 9B does not perform human review of generated evidence, evidence
deletion, the 24-hour generation-evidence deadline, hard-gate continuation
acknowledgement, aggregate extension, final scoring, or Milestone 10 work.

## Milestone 10 scope remains unchanged

Milestone 10 continues to own the human lifecycle for validated generation
evidence: grounding/quality review, explicit evidence deletion, the 24-hour
review/deletion deadline, and the committed `review_deadline_expired` policy.
These responsibilities do not move into 9A or 9B.

Use the explicit terms **preflight evidence review** and **generation evidence
review** wherever the distinction affects ownership or sequencing.

## Architecture and reassessment checkpoints

The architecture memo already requires closing and reviewing exact preflight
evidence before preparing generation, so no architecture-memo edit is needed.
The implementation plan's wording remains historically intact and its committed
digest remains unchanged; this record is the authoritative ownership
clarification. Editing that plan would necessarily change its digest.

Build-vs-adopt remains `defer_adoption`. Architecture A remains custom through
all of top-level Milestone 9:

`9A committed` → `9B committed` → `Milestone 9 complete`
→ mandatory Temporal/Inngest/LangGraph reassessment
→ only then may Milestone 10 begin.

The reassessment is not triggered after 9A alone.

## Identity and authorization impact

This clarification changes no aggregate package, implementation-plan digest,
frozen-v4 manifest, evaluation set, execution budget, request identity, AI
envelope, preflight grant/reservation identity, generation grant/reservation
identity, validator, fallback, historical artifact, or permanent manifest.
Permanent status remains `closed_no_execution_authorized`; no live provider
execution is authorized.
