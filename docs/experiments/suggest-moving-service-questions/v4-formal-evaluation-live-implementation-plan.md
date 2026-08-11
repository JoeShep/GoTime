# Frozen-v4 Formal Evaluation Live Implementation Plan

## Status and fixed basis

This document plans implementation of Architecture A for the frozen-v4 formal
evaluation. It implements nothing and authorizes no credentials, client,
spending, token preflight, generation, or live state.

Authoritative basis:

- live architecture memo SHA-256
  `07d0cecdd2abde2ac3ce081b6f3812e5822cd1ba29ae936ca8dea16862e5fa9d`;
- recommendation `recommend_A`;
- frozen evaluation-set manifest
  `38c4db2e92368ead41f9c6f87146a83103ae7780328aa7423d13340239134e94`;
- execution-budget SHA-256
  `0d848bce8866023a5b7f7912795a6ee80b3aae471189f447911244da10777b6b`;
- request-identities SHA-256
  `a23de86e93c3b83b7d51ffa5f73c5d694cd8266c5013c6d14833ad64bddd40ee`.

The fixed execution order is `eval-v4-01` through `06`, then `09`, then `10`.
Cases `07` and `08` are deterministic. Limits are eight preflights, eight
generations, zero retries, `$0.03` per AI case, and `$0.24` aggregate. The
aggregate is seven-day coordination state; each preflight or generation grant
has a 15-minute activation-to-dispatch window.

Every implementation milestone below is offline/network-disabled until the
separate live-readiness milestone. Each is implemented, rehearsed, reviewed,
and committed before its dependent milestone begins.

## Non-negotiable proof and fallback rule

Before live readiness, Architecture A must cleanly prove:

1. exact per-case identity;
2. single-use provider consumption;
3. cross-case isolation;
4. prospective aggregate budget enforcement;
5. durable pause/resume and recovery; and
6. independent case closure.

Failure to prove any one item stops Architecture A and requires a reviewed
recommendation for Architecture B. No requirement may be weakened to preserve
Architecture A.

## Shared implementation rules

- Aggregate state coordinates; it never reads credentials, constructs a
  provider client, dispatches a request, or grants provider permission alone.
- Only an exact active phase grant can reach the future operator boundary.
- `provider_dispatch_started` consumes the phase attempt; indeterminate dispatch
  remains consumed, while proven pre-dispatch failure does not.
- Completed cases never reopen. Untouched cases remain untouched.
- A hard-gate result is terminal and blocks `next` until
  `hard_gate_continuation_acknowledged` is recorded.
- Validated evidence is reviewed/deleted in the same session when possible and
  never retained beyond 24 hours without the explicit deadline lifecycle.
- The offline formal-evaluation runner and all frozen artifacts remain unchanged.
- The local retained-head threat model from ADR-0005 applies; no GA-grade trust
  anchor or production persistence decision is introduced.

## Milestone 1 — Aggregate package and coordination state

**Scope.** Add immutable aggregate identity/configuration models plus locked,
durable coordination state. Bind the frozen set, runner, v4 manifest, ten case
members, eight request triples, two empty cases, operator/reviewer labels,
seven-day expiration, status, next-case cursor, counters, budget, outcomes,
extension history, and hard-gate blocks. Provider operations are absent.
Use the approved statuses `prepared`, `approved`, `in_progress`,
`ready_to_finalize`, `expired_paused`, `abandoned`, and `closed`; terminal case
outcomes, rather than a second aggregate status, prove completion readiness.

**Dependencies.** Committed architecture memo and frozen package verification.

**Likely files.** Add `v4_formal_evaluation_live_models.py`,
`v4_formal_evaluation_live_state.py`, and
`test_v4_formal_evaluation_live_state.py` under the existing experiment script
directory. Add a versioned live-state schema document under the experiment docs.

**Invariants.** Aggregate identity is non-executable; all identities and limits
are literal; state writes are locked/atomic; stale or mismatched state fails
closed; no credential/client/provider import is reachable.

**Tests.** Positive initialization/round-trip; wrong frozen digest, case
inventory, request identity, expiry, counter, cursor, or budget rejected;
network/client import audit; concurrent writer/atomic recovery; no authority
artifact emitted.

**Stop conditions.** Aggregate state can dispatch, mutate frozen inputs, or
cannot reconcile identity/counters from durable history.

**Deliverable/review boundary.** Coordination-only package and offline tests;
human diff review before deterministic initialization.

## Milestone 2 — Deterministic initialization and cases 07/08

**Scope.** Validate the frozen package, create aggregate state, and run cases
`07` (`known(false)`) and `08` (`not_applicable`) through the frozen
deterministic binding path. Write terminal outcomes and closures with zero
provider activity.

**Dependencies.** Milestone 1 and unchanged `bind_case` behavior in
`freeze_v4_formal_evaluation_set.py`.

**Likely files.** Add an initialization service and tests to the new live
modules; import frozen binding helpers rather than copying eligibility logic.

**Invariants.** No provider-request constructor, request identity, phase grant,
preflight, generation, credential access, spend, or retry for either case.

**Tests.** Constructor spy/raising positive boundary; exact empty outcomes and
closures; repeat initialization rejected/idempotent as designed; mutation of
known-false/not-applicable rejected; budget remains zero; generation entry is
unreachable.

**Stop conditions.** Either empty case requires provider preparation or cannot
be terminally represented without changing frozen v4.

**Deliverable/review boundary.** Initialized offline aggregate with two closed
cases; separate review because provider non-entry is foundational.

## Milestone 3 — AI case envelope model

**Scope.** Create one durable, non-authoritative envelope for each AI case.
Bind aggregate identity, case input, request/canonical/fingerprint triple,
provider/model/SDK, v4 manifest, `$0.03` ceiling, phase states, attempt state,
terminal outcome, review/deletion, and closure.

**Dependencies.** Milestones 1–2 and frozen request-identities package.

**Likely files.** Add `v4_formal_evaluation_live_cases.py` and focused tests.

**Invariants.** Literal identity equality; one envelope per fixed case; no
cross-case artifact accepted; envelope has no provider authority.

**Tests.** Eight exact positive bindings; wrong/cross-case triple, provider,
model, SDK, aggregate ID, budget, or case input rejected; duplicate/missing case
rejected; terminal envelope immutable; empty cases cannot instantiate envelopes.

**Stop conditions.** Case identities can cross-bind or an envelope must itself
be executable.

**Deliverable/review boundary.** Frozen envelope schema and isolation proof,
reviewed before any grant model.

## Milestone 4 — Preflight grant package

**Scope.** Implement offline rendering, installation, review, planning,
activation, consumption, closure, evidence, and evidence review for one exact
case preflight grant. Bind one credential lookup/client construction/token
preflight maximum, zero generations/retries, 15-minute dispatch window, case
ceiling, aggregate identity/budget reservation, and operator intent.

**Dependencies.** Milestone 3. Define an injected, fail-closed budget-reservation
port; the package cannot activate with the rejecting test implementation.
Milestone 5 supplies the reviewed accounting implementation before activation
becomes usable even in rehearsal.

**Likely files.** Add `v4_formal_evaluation_live_grants.py` and preflight tests;
adapt verified concepts from `v4_sequence_1_preflight.py` through live-specific
adapters without changing historical pilot files.

**Invariants.** Exact case/request identities; one token-count operation; no
generation; separate reviewed activation; expiry/non-reuse; evidence bound to
grant, dispatch, and aggregate history.

**Tests.** Complete network-disabled lifecycle; wrong case/request/SDK/operator,
expired grant, duplicate activation/dispatch, generation attempt, retry, stale
aggregate, cross-case evidence, closure mutation, and reuse rejected.

**Stop conditions.** Grant can outlive 15 minutes, substitute a case, generate,
or activate without prospective reservation.

**Deliverable/review boundary.** Preflight grant lifecycle operating only on a
fake adapter; independent human review.

## Milestone 5 — Prospective aggregate budget accounting

**Scope.** Implement atomic case and aggregate reservation, dispatch
consumption, and result reconciliation.

**Dependencies.** Milestones 1, 3, and the reservation-port contract from
Milestone 4; required by activation in M4/M7.

**Reservation model.** Each grant declares a conservative operation ceiling no
greater than the case's remaining `$0.03`. Activation atomically reserves that
amount against both case and aggregate remaining authority. An unused expired
grant with proven no dispatch releases its reservation. At
`provider_dispatch_started`, reservation becomes consumed exposure. A known
result reconciles to recorded actual/conservative cost and releases only proven
unused capacity; indeterminate dispatch retains the full reservation as
consumed exposure. Preflight measurement never rewrites the frozen case ceiling.

**Likely files.** Add `v4_formal_evaluation_live_budget.py` and budget tests;
state mutation remains under the aggregate lock.

**Invariants.** At most 8/8 attempts, zero retries, `$0.03` per case, `$0.24`
aggregate; header totals derived from case/grant records; no retrospective-only
check.

**Tests.** Eighth preflight/generation allowed, ninth rejected; per-case and
aggregate overage rejected; parallel reservation collision; unused expiry
release; dispatched/indeterminate non-release; exact reconciliation; forged
aggregate totals rejected.

**Stop conditions.** Two valid-looking grants can over-reserve, dispatched cost
can be released, or aggregate totals cannot be independently derived.

**Deliverable/review boundary.** Offline atomic budget engine; explicit human
review of reservation timing before integration.

## Milestone 6 — Dispatch event and attempt consumption

**Scope.** Implement the durable `provider_dispatch_started` seam in a
network-disabled transport harness. Before it, validate active grant, exact
request object/identities, aggregate/case state, reservation, expiry, intent,
and absence of a consumed attempt. Durably append the event and convert the
reservation to consumed exposure immediately before entering the pinned SDK
call boundary.

**Dependencies.** Milestones 4–5.

**Likely files.** Add `v4_formal_evaluation_live_dispatch.py` and fault-injection
tests. A later live adapter may wrap `openai_transport_v4.py`; do not change the
historical transport in this milestone.

**Invariants.** Provider entry is impossible without durable dispatch history;
one event maximum per phase; indeterminate state consumes; proven failure before
the event does not.

**Tests.** Crash before event (unused), crash after event/before SDK entry
(indeterminate/consumed), SDK exception, timeout, 5xx/provider error, response,
and process death before handling; duplicate/retry rejected; counters and
budget reconciled after restart.

**Stop conditions.** A crash gap can yield provider dispatch without durable
consumption, or recovery can restore a consumed attempt.

**Deliverable/review boundary.** Fault-injected dispatch contract with no real
SDK/client; separate safety review.

## Milestone 7 — Generation grant package

**Scope.** Add a generation grant distinct from preflight. Eligibility requires
exact completed preflight evidence and approved review, nonterminal case, valid
aggregate, cleared hard-gate block, available budget, and no prior generation.
Bind zero preflights, one generation, zero retries, 15 minutes, exact request
triple, preflight evidence/review, `$0.03` case ceiling, and operator intent.

**Dependencies.** Milestones 4–6.

**Likely files.** Extend the live grant module; adapt verified lifecycle ideas
from `v4_sequence_4_generation_gate.py` without modifying historical records.

**Invariants.** Preflight cannot authorize another case; generation uses the
same exact prepared request; no grant while blocked/expired/terminal.

**Tests.** Network-disabled happy path; missing/rejected/expired/cross-case
preflight evidence, wrong request triple, stale aggregate, hard-gate block,
budget exhaustion, second grant, retry, and reuse rejected.

**Stop conditions.** Generation can precede reviewed preflight, cross-bind, or
reuse a consumed phase.

**Deliverable/review boundary.** Synthetic-only generation grant lifecycle;
human review before credential boundary work.

## Milestone 8 — Same-shell human operator boundary

**Scope.** Add future operator-boundary design and network-disabled shell
rehearsal preserving direct human invocation, silent prompt, same process tree,
no credential argv/file, scoped enablement/intent, EXIT/INT/TERM/HUP cleanup,
and original exit code.

**Dependencies.** Milestones 4, 6, and 7.

**Command choice.** Use aggregate-aware generic coordinator commands for
read-only inspection and grant preparation, but two fixed provider-bearing
launchers (preflight and generation) with no free case argument. Each launcher
resolves the sole active grant and validates its embedded case/request identity.
This avoids eight copied scripts while preventing operator case substitution.
If the sole-active-grant proof is insufficient, switch to generated fixed
per-case/phase launchers; this is a human review checkpoint.

**Likely files.** Add live operator `.zsh` launchers, container wrappers, and
boundary tests; reuse ADR-0004 and existing v4 pilot trap/prompt patterns.

**Tests.** Network disabled; no active/multiple/wrong/expired grants; wrong
intent; missing credential; cleanup on all signals; exit-code preservation;
argv/environment/file leak audits; exact active case reaches fake transport.

**Stop conditions.** Codex-compatible launch path exists, free case input can
substitute identity, or credentials escape the process tree.

**Deliverable/review boundary.** Operator boundary rehearsal only; explicit
human security review before any live-capable packaging.

## Milestone 9 — Generation result, validation, diagnostics, closure

**Scope.** Ingest one dispatched generation result and apply existing Pydantic,
semantic, prose, fallback, bounded rejected-prose diagnostics, and transport
classification. Produce one outcome and independently close provider authority.

**Dependencies.** Milestones 6–8 and unchanged validators/fallback.

**Likely files.** Add a live result adapter importing validation behavior from
the proven v4 pilot/gate; do not copy or modify validators. Add result/closure
tests.

**Invariants.** Provider failure distinct from content rejection; rejected raw
prose not retained; fallback unchanged; one outcome; no replacement; closure
binds exact dispatch/grant/case.

**Tests.** Valid response, transport/provider failure, structural, semantic,
ordered prose rejection, fallback, bounded diagnostics, malformed/duplicate
JSON, wrong case audit, closure interruption/recovery, second outcome rejected.

**Stop conditions.** Rejected prose persists, classification conflates provider
and content failure, or a terminal attempt can be replaced.

**Deliverable/review boundary.** Synthetic result/closure package; separate
validator/fallback integrity review.

## Milestone 10 — Human review, deletion, and 24-hour deadline

**Scope.** Bind existing review fields/decisions to exact validated evidence,
then execute the explicit crash-recoverable deletion lifecycle and case closure.
Block `next` while evidence/review/deletion is incomplete.

**Dependencies.** Milestone 9 and deletion invariants from the offline runner.

**Recommended deadline behavior.** Choose option A: a deterministic
`review_deadline_expired` terminal case outcome at 24 hours. The transition
records that required human review was not completed, preserves the consumed
generation and exact evidence digest, performs the normal bounded deletion
transaction, and prohibits retry/replacement. It prevents `graduate`; absent an
independent hard-gate failure, recommend aggregate disposition
`remain_experimental`. It never invents review scores. Live readiness must prove
deadline enforcement independent of a later operator invocation and must review
the exact timer/scheduler mechanism; otherwise live authorization is blocked.

This recommendation is a required human policy checkpoint before code. No
silent file deletion is allowed: expiry, terminal outcome, deletion, and closure
must all be durable lifecycle events.

**Likely files.** Add live review/deletion/deadline services and tests; reuse
review models and canonical deletion transaction semantics without modifying
the offline runner.

**Tests.** Same-session review/delete; wrong evidence/case/reviewer; duplicate or
conflicting review; 23:59 allowed, exact 24:00 expiry; no scores on expiry;
progression blocked; deletion crash matrix/idempotency; deadline process crash;
case remains terminal and cannot regenerate.

**Stop conditions.** Evidence can exceed the hard limit silently, expiry deletes
without history, invents review, permits progress/retry, or cannot close safely.

**Deliverable/review boundary.** Offline deadline/deletion rehearsal; explicit
human approval of terminal semantics and enforcement mechanism.

## Milestone 11 — Hard-gate continuation acknowledgement

**Scope.** Add `hard_gate_continuation_acknowledged` after a terminal hard-gate
case and before `next` can advance.

**Dependencies.** Milestones 9–10.

**Likely files.** Add acknowledgement model/service/CLI operation and tests.

**Invariants.** Binds aggregate, case, terminal outcome digest, human label,
timestamp, and bounded note; changes no result, score, counter, budget,
authority, or retry state. Integrity/authority/closure stops are not
acknowledgeable.

**Tests.** Correct acknowledgement unblocks next untouched case; wrong/non-hard
case, nonterminal outcome, wrong digest, duplicate/conflicting actor, score
mutation, retry creation rejected; integrity stop remains blocked.

**Stop conditions.** Acknowledgement mutates results or bypasses evaluation-wide
fail-closed conditions.

**Deliverable/review boundary.** Offline acknowledgement gate; human policy
review.

## Milestone 12 — Aggregate extension

**Scope.** Add `aggregate_evaluation_extended` before expiry or from
`expired_paused`, with reviewer, reason, retained old expiry, and new seven-day
expiry. No automatic rollover.

**Dependencies.** Milestones 1, 5, and durable history conventions.

**Likely files.** Extend live state/history service and tests.

**Invariants.** Same aggregate/frozen identity; no change to cases, outcomes,
attempts, budgets, counters, terminal states, or grants; no expired/consumed
grant reactivation; every extension independently reviewed and replayable.

**Tests.** Before/after expiry; multiple sequential extensions; wrong reviewer,
reason, frozen ID, old expiry, or new duration rejected; active grant prevents
extension; crash/replay; counters and case digests byte-equivalent.

**Stop conditions.** Extension resets state, grants provider authority, or
cannot recover across multiple events.

**Deliverable/review boundary.** Extension-only offline package; separate review.

## Milestone 13 — Pause/resume across sessions

**Scope.** Implement aggregate-aware resume and next-case selection. Reproduce
session 1 (initialize, 07/08, close 01–03) and session 2 (replay, prove terminal,
no active grant, continue 04).

**Dependencies.** Milestones 1–12.

**Likely files.** Add resume/orchestration service and tests; no provider path.

**Invariants.** Durable history is replayed before action; completed cases and
consumed attempts never reopen; untouched cases need no recreation; no grant
survives overnight; stable order enforced.

**Tests.** Clean stop, expired aggregate, unused expired grant, dispatched
provider failure, awaiting review, interrupted deletion, hard-gate block,
multiple extensions, corrupted history, and wrong cursor. Cross-process
duplicate preflight/generation remains rejected.

**Stop conditions.** Resume depends on process memory, skips a block, recreates
cases, or restores provider authority.

**Deliverable/review boundary.** Multi-process/multi-session offline proof.

## Milestone 14 — Aggregate history and Architecture A state model

**Scope.** Consolidate the event schema and semantic replay for aggregate,
case, grant, budget, dispatch, result, review, deletion, closure,
acknowledgement, extension, recovery, and final report provenance.

**Dependencies.** Milestones 1–13; history invariants are implemented
incrementally, then frozen/reviewed here as one coherent model.

**Likely files.** Add a versioned event specification and live history/replay
module. Reuse ADR-0005 principles, not the offline JSON implementation as an
unreviewed production abstraction.

**Invariants.** Journal is lifecycle history; ledger is projection; aggregate
and per-case transitions bind each other without allowing cross-case mutation;
all ten closures and outcome digests bind final provenance. Retained-head threat
model remains explicit.

**Tests.** Hash-chain/replay, semantic operation map, partial mutation, stale
projection, cross-case substitution, event removal/reorder, budget/counter
reconciliation, interrupted recovery, report determinism, and total-local-
rewrite non-goal documentation.

**Stop conditions.** Aggregate history can overwrite case history or report
provenance cannot reconcile ten independent closures.

**Deliverable/review boundary.** Frozen live-evaluation event/state
specification and offline proof; significant decision review/ADR amendment if
the accepted ADR scope changes.

## Milestone 15 — Operator command surface

**Scope.** Design and then implement only offline versions of a small guided
surface: verify/initialize, start/resume, next, prepare/review grant, verify
active grant, review evidence/result, delete/close, acknowledge hard gate,
extend, recover, and finalize/verify. Provider-bearing launchers remain separate
human commands.

**Dependencies.** Milestones 1–14.

**Command recommendation.** Generic aggregate-aware coordinator commands must
derive/validate the next exact case; they may not accept arbitrary request
identity overrides. Use one fixed preflight and one fixed generation launcher
that resolve the sole active grant with no case argument. Fall back to generated
fixed per-case/phase launchers if negative tests cannot prove substitution
impossible.

**Likely files.** Add `v4_formal_evaluation_live_cli.py`, one offline wrapper,
two operator launchers, focused inventory tests, and a live operator runbook.

**Tests.** Every documented command executable network-disabled; wrong order,
case override, multiple active grants, duplicate commands, terminal case,
expired state, and recovery paths; help/inventory exact; no hidden live command.

**Stop conditions.** Operator must reason about raw digests/files, generic input
can cross-bind a case, or a provider-capable command becomes Codex-invocable.

**Deliverable/review boundary.** Fixed offline command inventory and runbook;
human usability/security review.

## Milestone 16 — Exact-command full offline rehearsal

**Scope.** Run the exact public commands as separate processes through all ten
cases, case-by-case, with synthetic transport.

**Dependencies.** Milestone 15.

**Likely files.** Add a network-disabled rehearsal script, assertion module,
exact-command inventory, and bounded synthetic result manifests under the live
evaluation experiment namespace.

**Scenarios.** Nominal completion; deterministic 07/08; all eight preflight and
generation reviews; human review/deletion; session pause/resume; aggregate
extension; hard-gate acknowledgement; provider failure; expired unused grant;
pre/post-dispatch crashes and ambiguity; interrupted deletion; deadline expiry;
recovery; final report. Preserve graduate/fail/remain-experimental scoring
fixtures without changing frozen cases.

**Tests.** Exact-command accounting, cross-process duplicate/non-reuse,
cross-case isolation, budget maxima, zero retries, closed state, no credentials,
network disabled, deterministic report provenance.

**Invariants.** Every public command is exercised; helper-only paths cannot
claim success; no real client/credential/network path is enabled; all scenarios
end in reconciled closed or explicitly recoverable state.

**Stop conditions.** Any claim relies on helper-only shortcuts, any command is
unexercised, or rehearsal leaves active authority/state inconsistency.

**Deliverable/review boundary.** Reviewed rehearsal package and bounded result
matrix; no live capability.

## Milestone 17 — Architecture A proof checkpoint

**Scope.** Independent review of evidence from milestones 1–16 against the six
non-negotiable guarantees.

**Dependencies.** Milestone 16 and clean frozen/historical integrity audit.

**Likely files.** Add a proof matrix/report binding tests, artifacts, command
inventory, and frozen identities; no implementation changes in the same review.

**Invariants.** Each guarantee has independent positive, adversarial, and
recovery evidence; frozen requirements are evaluated literally; a missing proof
cannot be waived by aggregate success elsewhere.

**Tests/review.** For each guarantee, identify positive proof, adversarial test,
recovery proof, and exact artifact/commit. Re-run frozen integrity, runtime
reachability, credential/network audits, and permanent closed-state validation.

Milestone 17 is an independent proof/review checkpoint, and no implementation
changes may occur during it. If the checkpoint finds a remediable implementation
defect or missing proof, stop the checkpoint without patching during review;
open a separate implementation milestone, implement the correction there,
rehearse and human-review it, commit it, and rerun Milestone 17 from the resulting
committed state. Milestone 17 passes only when all six Architecture A guarantees
are independently proven from committed state. If any one guarantee cannot be
cleanly proven after appropriate remediable defects have been addressed, or if
satisfying it would require weakening the guarantee, Architecture A must be
abandoned in favor of Architecture B. No guarantee may be weakened merely to
preserve Architecture A.

**Stop conditions.** Missing/ambiguous proof for any one guarantee.

**Deliverable/review boundary.** Exactly `recommend_A_ready` or
`fallback_to_B`. `fallback_to_B` stops all Architecture A live work; requirements
are not relaxed.

## Milestone 18 — Separate live-readiness package

**Scope.** Only after `recommend_A_ready`, design and review package rendering,
human values, fresh timestamps, phase-grant authorization, and possible provider
operations. This milestone is not automatically authorized by prior commits.

**Dependencies.** Milestone 17 approval, clean baseline, fresh integrity and
cost review, and explicit human permission.

**Likely files.** To be proposed in that future milestone; no paths or live
state are created now.

**Invariants.** All prior reviewed commits and frozen identities remain exact;
no aggregate package acts as provider authority; only one reviewed case/phase
grant can be active; permanent closed state is the start and recovery target.

**Tests.** Exact rendered-package identity, timestamp/lifetime boundaries,
operator inventory, no credential leakage, one-use activation/dispatch/closure,
budget reservation, recovery, non-reuse, and a network-disabled exact-command
rehearsal repeated from a clean state.

**Required review.** Exact aggregate/case/phase identities, operator inventory,
same-shell boundary, timestamps, costs, active/closed state, recovery, and
network capability. Provider operation still requires a separate explicit
human action.

**Stop conditions.** Any stale identity, failed proof, unresolved deadline
mechanism, active authority ambiguity, or missing closed-state restoration.

**Deliverable/review boundary.** A reviewed live-readiness package—not a live
call. No Stage C or product integration.

## Dependency map

| Milestone | Depends on | Safe combination? |
|---|---|---|
| 1 Aggregate state | Approved architecture | Keep separate foundational review |
| 2 Deterministic initialization | 1 | Keep separate: provider non-entry gate |
| 3 Case envelopes | 1–2 | Keep separate: identity/isolation freeze |
| 4 Preflight grants | 3 | Commit with fail-closed budget port; no usable activation |
| 5 Budget accounting | 1, 3–4 | Keep separate safety/integration review |
| 6 Dispatch consumption | 4–5 | Keep separate crash-boundary review |
| 7 Generation grants | 4–6 | Keep separate preflight-binding review |
| 8 Same-shell boundary | 4, 6–7 | Keep separate credential/security review |
| 9 Results and closure | 6–8 | Keep separate validator/privacy review |
| 10 Review/deadline/deletion | 9 | Keep separate policy/privacy review |
| 11 Hard-gate acknowledgement | 9–10 | May share rehearsal with 10; separate diff |
| 12 Aggregate extension | 1, 5, history conventions | May share resume rehearsal; separate diff |
| 13 Pause/resume | 1–12 | Integration milestone |
| 14 History/state specification | 1–13 | Consolidation/freeze review |
| 15 Operator surface | 1–14 | Separate usability/security review |
| 16 Exact-command rehearsal | 15 | Separate evidence-only review |
| 17 Proof checkpoint | 16 | Must remain independent/no code changes |
| 18 Live readiness | 17 approval | Must remain separate and explicitly authorized |

## File and module plan

### Add

- `v4_formal_evaluation_live_models.py`: immutable aggregate, case, grant,
  budget, event, acknowledgement, extension, and deadline models.
- `v4_formal_evaluation_live_state.py`: lock, atomic projection, lifecycle
  orchestration, initialization, resume, and recovery.
- `v4_formal_evaluation_live_cases.py`: exact frozen binding/envelope adapter.
- `v4_formal_evaluation_live_budget.py`: reservation/consumption/reconciliation.
- `v4_formal_evaluation_live_grants.py`: preflight/generation grant lifecycle.
- `v4_formal_evaluation_live_dispatch.py`: provider-dispatch seam and audit.
- `v4_formal_evaluation_live_history.py`: event semantics/replay/provenance.
- `v4_formal_evaluation_live_cli.py`: aggregate-aware offline/public workflow.
- fixed preflight/generation operator `.zsh` launchers and pinned wrappers.
- focused test modules by responsibility, exact-command rehearsal, runbook, and
  versioned live event/state specification.

### Reuse unchanged or through narrow adapters

- `freeze_v4_formal_evaluation_set.bind_case` for deterministic eligibility and
  exact case binding;
- `run_openai_stage_b_v4_pilot.py` metadata/request/attempt identity helpers;
- `v4_sequence_1_preflight.py` lifecycle and evidence-review patterns;
- `v4_sequence_4_generation_gate.py` exact-attempt, activation, validation,
  fallback, review/deletion, and closure patterns;
- ADR-0004 same-shell operator boundary and existing trap/prompt tests;
- offline runner review/outcome/scoring, journal, deletion, and report
  invariants as specifications and reusable pure helpers where safe.

Do not edit frozen evaluation artifacts or the offline runner. If sharing
requires refactoring historical pilot code, isolate the extraction in its own
milestone and prove historical byte/behavior integrity before adoption.

## Cross-cutting test strategy

Every milestone runs its focused suite plus frozen package digests, eight exact
request triples, empty-case provider non-entry, historical v2/v3/v4 integrity,
runtime/network reachability, compilation/parsing, whitespace, and permanent
closed-state checks as applicable. Integration milestones additionally run the
full offline/backend suite and frontend tests/build even though no runtime wiring
is expected.

Use fault injection at every durable boundary, separate cryptographic-format
checks from semantic checks, and execute public-command rehearsals in fresh
processes. Never treat pass counts alone as proof; human review inspects identity,
non-reuse, budget, closure, and recovery assertions directly.

## Human decision checkpoints

1. **Milestone 5:** approve reservation of each grant's declared conservative
   operation ceiling at activation, dispatch conversion, and conservative
   reconciliation.
2. **Milestone 8/15:** approve the generic coordinator plus fixed no-case-arg
   launchers; otherwise require generated fixed case/phase launchers.
3. **Milestone 10:** approve `review_deadline_expired` terminal semantics,
   `remain_experimental` scoring absent another hard gate, and a deadline
   enforcement mechanism that works without a later CLI invocation.
4. **Milestone 12/13:** confirm recovery semantics across any number of reviewed
   extensions and expiry during an unfinished non-provider lifecycle.
5. **Milestone 14:** confirm the adapted experimental persistence remains within
   ADR-0005 and does not imply production architecture.
6. **Milestone 17:** accept all six proof rows or mandate Architecture B.

## Recommended implementation phases

1. **Foundation:** milestones 1–2, aggregate state and deterministic cases.
2. **Identity/preflight/budget:** milestones 3, 4, then 5; Milestone 4 remains
   non-activating until Milestone 5 supplies the reviewed reservation engine.
3. **Consumption/generation/operator boundary:** milestones 6–8.
4. **Results/review/deletion/policy:** milestones 9–11, including the reviewed
   24-hour terminal behavior.
5. **Extension/resume/history:** milestones 12–14.
6. **Operator workflow/rehearsal:** milestones 15–16.
7. **Architecture proof:** milestone 17, with no implementation changes.
8. **Live readiness:** milestone 18 as a new explicitly authorized effort.

This sequence keeps provider capability impossible until every lower-level
identity, budget, consumption, recovery, and closure boundary has passed an
offline human review.
