# NEXT_SESSION

## Multi-category browser-acceptance corrections

The focused frontend follow-up is implemented and awaits final human responsive
visual acceptance. The shared category dropdown behavior keeps checkbox and
Clear all interactions open, dismisses on outside click or Escape, returns
focus to the trigger after Escape, and preserves normal trigger toggling.

The plan-wide finder remains independent while searching. Selecting a task
that is hidden by the active category filter now clears that filter, uses the
existing success notice to explain why, reveals the phase and completed section
when needed, and preserves the established scroll/focus highlight. Selecting a
visible result leaves the filter intact. Mobile-only SCSS below Bootstrap's
`sm` breakpoint tightens task-card padding, spacing, title, and supporting
metadata while leaving desktop density, tap targets, and pill styling intact.

## Multi-category task enhancement

The approved multi-category enhancement is implemented. Tasks now carry a
required API `categories` collection containing zero or more configured
category identifiers; `[]` is valid and means uncategorized, while omission,
duplicates, and unknown identifiers are rejected. Existing scalar assignments
migrate transactionally into normalized `task_categories` rows, including the
direct Administrative-to-Logistics legacy path, without changing task or
relationship identities.

The editor provides an open-on-selection checkbox menu with selected labels and
Clear all. Cards and finder results show every category in configured order or
derived Uncategorized text. A separate non-persisted Categories filter uses OR
behavior across the six categories and Uncategorized, hides empty phases, and
keeps filtered completed counts; the plan-wide task finder remains independent.
Recommendation logic is unchanged. ADR-0007 records the persistence and API
decision. User-configurable categories remain in the Parking Lot.

## Relocation vocabulary cleanup

The approved relocation vocabulary cleanup is implemented and ready for human
review. The stable `move` phase ID now displays as `Make the move`, so existing
task phase assignments remain intact. The current category vocabulary is
Employment, Family, Financial, Healthcare, Housing, and Logistics.

Opening an older SQLite plan reconciles Administrative tasks in place to
Logistics and rebuilds the category constraint while copying task, assignee,
and dependency rows without changing their identities or other fields. Focused
backend and frontend regressions cover migration, reload, labels, and selectable
options. User-defined phases/categories and subtasks are recorded only in the
Parking Lot; multi-category tasks and the other deferred features remain
unimplemented.

## Plan-wide task finder

The approved frontend-only plan-wide task finder is implemented and passed
hands-on verification. In normal plan mode, an accessible autocomplete finds
active and completed tasks using case-insensitive title matching. Results show
only the task title, phase, category, and completed state. Selecting one keeps
the phase layout intact, expands its completed section when necessary, scrolls
and focuses the task card, and applies a lightweight reduced-motion-aware
locator cue without changing task or recommendation state.

The finder is hidden whenever the task editor is open and returns after Cancel
or a successful save; a failed save retains the editor and keeps the finder
hidden. Keyboard navigation supports Up/Down, Enter, Escape, and ordinary Tab
behavior. Phase-header Add actions, phase-prefilled creation, dependency
terminology changes, and general task filtering remain unimplemented.

## Task editor action ergonomics

The approved frontend-only editor ergonomics enhancement is implemented and
passed hands-on verification. The page-level `Add task` action is hidden in
both add and edit modes, then returns after Cancel or a successful save. The
single editor action area sits below the editor heading and remains top-sticky
within the card, with responsive wrapping and operation-specific labels.

Create and replacement requests continue to use the existing API operations.
Pending submissions show `Creating…` or `Saving…`, disable both editor actions,
and are guarded against duplicate execution. Existing editor scroll/focus,
dependency selection, completed-task lifecycle, and failed-save retention are
unchanged. Do not implement phase-header Add actions, phase-prefilled creation,
dependency terminology changes, or any other parked product observation.

## Completed task lifecycle and dependency semantics

The approved lifecycle enhancement is implemented and passed hands-on
verification. Within each phase, unfinished tasks remain in the active list
and completed tasks move into a collapsed `Completed (n)` history section.
Status and Edit controls remain available there so a completed task can be
inspected or reopened.

Direct dependency relationships survive completion and reopening. Completed
dependencies do not block; reopening restores derived blocking. Completed tasks
cannot be introduced as new dependencies, while an existing completed
dependency remains visible and removable during editing. Recommendation
eligibility continues to exclude completed work and refresh after status
changes. Continue using the real relocation plan before selecting another
change; do not begin priority, search, People, category, phase, related-link,
alternate-view, authentication, or AI work.

## Relocation-plan first-use usability follow-up

The approved first-use follow-up is implemented and passed hands-on
verification. Tasks may now be unassigned; the editor uses no real-person
placeholder names and displays unassigned tasks explicitly. Editing a task
scrolls its complete form into view, focuses the title, and continues to
support adding and removing direct dependencies.

The dependency picker is searchable and grouped in relocation-phase order. It
excludes the task being edited and preserves selections when filtering, while
the backend remains authoritative for cycles and invalid dependencies. Resume
entering and using the real relocation task list; do not yet implement multiple
categories, first-class People, related-task links, persisted transitive
dependencies, priority redesign, alternate views, AI, authentication, or
notifications.

## MVP Increment 2 — deterministic stored-task recommendation

GoTime's primary recommendation now comes from the persistent singleton
relocation plan. Only incomplete, unblocked tasks whose start date has arrived
are eligible. The engine uses an explicit lexicographic order: user priority,
due state/date, in-progress status, direct downstream unblocking leverage, phase
order, then task ID. The API returns the chosen task, phase, explanation,
unblocking context, and structured ranking factors; it returns a clear bounded
no-actionable state when appropriate.

The React plan experience refreshes the recommendation after successful task
creation, replacement, or status change. The older employment/commute reasoning
remains available as a separate planning section and was not deleted. Future
work may refine deterministic ranking using demonstrated family needs, but do
not introduce AI, opaque scoring, multi-plan infrastructure, authentication, or
notifications without a separately approved increment.

## MVP Increment 1B — persistent relocation-plan UI

The main React screen now loads the singleton SQLite relocation plan and shows
its four ordered phases and stored tasks. Users can add tasks, fully edit every
supported field, select dependencies, and change status. Blocked tasks and
their dependency context are visible, successful writes update the screen from
the authoritative API response, and backend validation/network failures are
shown without discarding an in-progress edit.

The existing deterministic recommendation experience remains alongside the
plan and is unchanged. The next product increment may make stored task state
help answer “What should I do next?”, but task-based ranking was deliberately
not started here. Do not resume the parked AI evaluation milestones, add
authentication/notifications, or generalize the singleton plan without a new
approved increment.

## MVP Increment 1A — persistent relocation-plan backend

The backend now has a focused SQLite repository and fixed API for one family
relocation plan. Four ordered phases are seeded once; tasks can be created,
replaced, retrieved, and moved through `not_started`, `in_progress`, and
`completed`. Tasks retain bounded category, assignees, optional dates, priority,
and dependencies. Blocked state is derived from incomplete dependencies and is
never independently editable.

Focused and full backend validation pass. Increment 1B should add the smallest
frontend plan/task-maintenance experience against this API. Do not generalize
to multiple goals/projects, add authentication/notifications, or connect the
parked AI evaluation infrastructure. The existing recommendation experience is
unchanged and does not yet rank persisted tasks.

## Post-Milestone-9 framework reassessment

The design-only reassessment recommends
`freeze_ai_infrastructure_and_return_to_product`. Milestones 1–9 already prove
the bounded evaluation's difficult identity, budget, dispatch, credential,
zero-retry, result-validation, evidence, and recovery semantics. Temporal,
Inngest, and LangGraph could improve generic timers/waits/worker recovery, but
GoTime has no demonstrated near-term workflow need that repays migration or new
operations.

Do not begin Milestone 10 while this recommendation awaits human review. If
approved, preserve the experiment in `closed_no_execution_authorized` state and
return to MVP planning. No additional AI implementation is required merely to
park it safely. Revisit frameworks only when the product demonstrates multiple
long-running workflows, unattended waits/timers, concurrent worker needs, or
when an explicitly approved live evaluation is being unfrozen. The historical
implementation plan and build-vs-adopt record remain unchanged.

## Architecture A Milestone 9B generation result boundary

Milestone 9B is implemented offline and awaits human diff review. The existing
Milestone 9A approval is the sole production generation prerequisite. After the
unchanged Milestone 8 generation dispatch boundary, provider output is handled
automatically by the canonical frozen schema/semantic/prose pipeline. One
bounded result and closure are durable; valid output creates bounded evidence
and leaves the case `awaiting_generation_evidence_review`, while content and
provider failures remain distinct, consumed, terminal, and non-retryable.

Rejected prose and arbitrary raw provider output are not retained. Replay binds
every result to the actual retained generation dispatch, preserves exact
idempotency, and recovers history-first after projection interruption. The
coordination CLI remains ten commands, live authorization remains closed, and
no real provider or Milestone 10 operation occurred. After 9B review and commit,
top-level Milestone 9 is complete; perform the mandatory framework reassessment
next, before beginning Milestone 10.

Final-review correction now also rejects fully rehashed noncanonical prose
diagnostics by enforcing the frozen code/rule/field/trigger/order and bounded
offset/count contract. Fixed result/evidence/closure identities are unchanged.

## Architecture A Milestone 9A preflight result and review gate

Milestone 9A is implemented offline and awaits human diff review. The unchanged
Milestone 8 preflight execution boundary now hands its in-memory outcome
directly to versioned bounded result/evidence handling. A valid case-01 result
records 2,852 tokens and locally derives `$0.0019408`; machine validation leaves
generation ineligible until the separate fixed human preflight evidence review
records an exact approval with all four canonical confirmations before the
15-minute deadline. Reject and request-changes decisions are terminal and do
not permit retry or generation.

The coordination CLI remains ten commands. Human review uses the fixed
provider-free `review_v4_formal_evaluation_live_preflight_evidence_docker.sh`
entry point, which resolves case/evidence from authoritative state. No live
provider call, real credential, raw provider payload retention, or generation
provider entry was introduced. Do not begin 9B before 9A human review and
commit. Framework reassessment remains after committed 9B/top-level Milestone
9 and before Milestone 10.

Human review found and the correction now closes two replay-only gaps:
`preflight_result_validated` requires its exact evidence atomically, and its
dispatch digest must resolve the actual retained `provider_dispatch_started`
event. Canonical result/evidence/review identities and review policy are
unchanged.

## Architecture A Milestone 9 ownership reconciliation

Milestone 9 implementation is paused pending human review of the design-only
ownership clarification in
`docs/experiments/suggest-moving-service-questions/v4-formal-evaluation-milestone-9-ownership-reconciliation.md`.
Preserve the eighteen-milestone numbering and implement top-level Milestone 9
through two separately reviewed and committed checkpoints: 9A owns preflight
result validation, bounded evidence, and the exact canonical human preflight
evidence review that alone may establish generation eligibility; 9B owns
generation execution/result validation, bounded diagnostics/evidence, and
provider-phase closure. Milestone 10 continues to own human review and deletion
of validated generation evidence plus its 24-hour deadline.

Do not begin 9A before approval of the reconciliation. After approval, complete
and commit 9A, then complete and commit 9B. Only after both are committed is
top-level Milestone 9 complete. The mandatory Temporal/Inngest/LangGraph
reassessment follows completed Milestone 9 and must precede Milestone 10.
Build-vs-adopt remains `defer_adoption`, and permanent live authorization
remains `closed_no_execution_authorized`.

## Architecture A Milestone 8 same-shell boundary

Milestone 8 continues offline from `6043cbc`. The fixed human-run zsh preflight
launcher performs credential-free readiness, silent same-shell credential
entry, final revalidation, durable `provider_dispatch_started`, and immediate
synthetic provider entry with cleanup and preserved exit status. Production is
closed before prompting because Milestone 18 live authorization is absent;
generation is also blocked by absent production reviewed evidence. The pinned
SDK is 2.45.0 with explicit zero retries; frozen preflight/generation timeouts
remain 5/12 seconds. No provider operation or Milestone 9 behavior exists.
Both launchers reject sourcing before changing the caller, and the unchanged
preflight launcher is rehearsed through its unchanged Docker wrapper with
xtrace enabled. The boundary is wired to the canonical client factory, whose
actual constructor arguments prove `max_retries=0` and `trust_env=False`.
Aggregate expiry, grant expiry, released reservation, and concurrent consumption
are independently revalidated before dispatch. The full-suite skip reduction
from 18 to 2 comes from mounting the existing host zsh read-only: sixteen
zsh-only tests run, while two Docker-daemon-dependent rehearsals remain skipped.
Corrected validation passed 20 Milestone 8 tests, 222 focused Milestones 1–8
tests, and 1,254 full-offline tests with those two documented skips.

Build-vs-adopt remains `defer_adoption`; reassess after committed Milestone 9
and before Milestone 10.

## Architecture A Milestone 7 generation grants

Milestone 7 is implemented offline and awaits human diff review. The version-1
generation grant binds the exact case/envelope/request triple and reviewed
preflight evidence for 15 minutes, with one generation slot and zero retries.
Case 01 reserves `$0.0019408`, leaving `$0.0280592` case and `$0.2380592`
aggregate monetary capacity. Its fixed-time grant digest is
`b8eeaa9ed4fa16037cb2fa6e0ce2588cebe75ec3152e6676e9dc249b3f3c95f8`.

Production preparation remains fail-closed because retained preflight
result/review state does not exist yet. Tests use a production-inaccessible
evidence harness. No command, dispatch, provider execution, credential, client,
or network path was added. The generation cost now reads the maximum output
bound from the frozen-v4 request configuration rather than defining a local
policy literal. Replay-valid test-only histories cover all 8/0 through 0/8
reserved/consumed boundaries and fully rehashed semantic attacks. Complete
prior-record deletion/replacement and consumed-preflight identity rewrites are
rejected by explicit history-retention invariants relative to the retained
authoritative journal head; API-level conflicting grant/reservation reruns are
side-effect free. Per ADR-0005, total internally consistent replacement of the
journal, suffix, retained head, projection, and unkeyed hashes remains outside
scope and would require a separately trusted anchor. This is an intentional
threat-model boundary, not missing Milestone 7 work. Do not begin Milestone 8
before final review and commit.

## Frozen-v4 budget-policy reconciliation

The approved reconciliation is committed as a focused Milestones 4–6
correction. Preflight now reserves `$0.00`
monetary exposure plus one operation slot; dispatch irreversibly consumes that
slot while monetary exposure remains zero. The corrected case-01 grant digest
is `757155c6427132e8ca3a5bdd37a0c3a93adfb0fb386684f403b1940fe0ca0913`
and reservation digest is
`8edf28f8378a97796b197bdcb0d0b5bc64b59fbcb2260d5627e313c87c4daec0`.
The `$0.03` case ceiling, `$0.24` aggregate ceiling, frozen identities, and
irreversible attempt semantics are unchanged.

## Architecture A Milestone 6 dispatch-consumption boundary

Milestone 6 records offline `provider_dispatch_started` as the exact
irreversible reserved-to-consumed boundary. The `$0.00` preflight monetary
exposure remains zero while one preflight slot converts to consumed; release
and retry are permanently prohibited. Crash-before-history remains reserved,
while crash-after-history recovers consumed exactly once.

No public command was added: Milestone 8 must call the state transaction and
enter the pinned SDK immediately afterward in one controlled process. No SDK,
credential, client, request, or network capability exists yet. Human diff
review is required before commit or Milestone 7.

## Architecture A Milestone 5 prospective budget accounting

Milestone 5 now reserves exact prospective preflight exposure atomically under
the aggregate lock. Schema
`suggest-moving-service-questions-v4-formal-evaluation-provider-budget-reservation-v1`,
version 1, uses `provider_budget_reserved` and proven-unused
`provider_budget_released`. The fixed case-01 reservation digest is
`cbc71820cc3d801a09d90dedb0b279882bccae85da8dd482651a64f6eb1a462a`.

The historical interpretation reserved one preflight slot and `$0.03` of
prospective capacity. The approved reconciliation supersedes it: the current
reservation uses one
slot and `$0.00`, leaving `$0.03` for case 01 and `$0.24` aggregate monetary
capacity. Exact rerun is event-free. Expired unused capacity returns only with
durable `not_started` dispatch proof. Scoped preflight budget/grant authority
is true, while provider, execution, generation, dispatch, retry, and generic
spending authority remain false. Milestone 6 dispatch consumption is not
implemented. Grant and reservation collections now retain one exact record per
AI case, so released case-01 history coexists with a later case-02 reservation
and all eight case records can be represented without deletion. Human diff
review is required before commit or Milestone 6.

## Approved Architecture A build-vs-adopt decision

The accepted disposition is `defer_adoption`. After this documentation is
reviewed and committed, proceed with the custom Architecture A implementation
through Milestones 5–9; the immediate next milestone is Milestone 5,
prospective budgets. No framework PoC is required first.

After Milestone 9 is committed and before Milestone 10 begins, perform a
mandatory reassessment of Temporal, Inngest, and LangGraph for generic durable
execution. This is a reassessment, not a predetermined migration. The OpenAI
Agents SDK is not adopted for this control-plane problem. No framework,
runtime change, live state, or provider authority was introduced here.

## Architecture A Milestone 4 offline preflight grant candidate

The aggregate now durably prepares one exact derived-next-case preflight grant
candidate under schema
`suggest-moving-service-questions-v4-formal-evaluation-preflight-grant-v1`,
version 1, using `preflight_grant_prepared`. It binds the 01 envelope/request
metadata, single-use zero-retry policy, `$0.03` ceiling, and exact 15-minute
inclusive-expiry window.

The production budget port always denies until Milestone 5. Denial adds no
event or authority; all counters remain zero. A test-only injected approval is
ephemeral and still cannot dispatch. History recovery, idempotency, rehashed
identity attacks, expiry, and provider-constructor/network non-entry are
covered offline. The public inventory is eight commands. Human diff review is
required before commit; do not begin Milestone 5.

The grant layer now sources both ceiling bindings directly from the canonical
frozen `PER_CASE_PROVIDER_CEILING_USD` without a duplicate literal. Persisted,
fully rehashed deterministic-case targeting is also rejected explicitly.

## Architecture A Milestone 3 AI case envelopes

Eight exact non-authoritative AI envelopes now bind the aggregate, frozen case
input, request/canonical/fingerprint triple, v4 prompt/schema/provider metadata,
pinned model/SDK and request configuration, `$0.03` case policy, and inactive
phase placeholders. Their schema is
`suggest-moving-service-questions-v4-formal-evaluation-ai-case-envelope-v1`,
version 1, and all eight canonical digests are unique.

The one-time `ai_case_envelopes_bound` event requires active coordination and
terminal deterministic cases 07/08. It binds the complete fixed-order set,
replays durably, recovers after history-first interruption, and is idempotent.
Fully rehashed cross-case, identity, provider/model/manifest/budget,
missing/extra, duplicate-digest, and deterministic-target attacks fail closed.

The public inventory is seven commands with `bind-ai-case-envelopes`. Provider
authority/counters/spend remain false/zero, all phase states remain
`not_authorized`, and next AI case remains 01. Milestones 4/5/6/7/8/11/12 are
unimplemented. Human diff review is required before commit; do not begin
Milestone 4.

## Architecture A Milestone 2 deterministic closure

The aggregate now has one narrowly scoped persisted operation,
`deterministic_case_completed`, for the frozen deterministic-empty cases only.
It reuses the canonical frozen eligibility boundary and records exact terminal
outcomes: `eval-v4-07` is empty `known(false)` and `eval-v4-08` is empty
`not_applicable`. Fixed order, exact identity/reason validation, idempotent
rerun, partial fresh-process recovery, history-first crash recovery, and
inclusive-expiry blocking are covered offline.

Constructor-spy tests prove zero provider-request constructor calls for 07 and
08; an AI-positive control reaches the constructor boundary once and stops
before any provider operation. All provider counters and spend remain zero,
spending authorization remains false, and all AI cases remain untouched with
`eval-v4-01` derived next after both deterministic completions.

The public inventory is now six commands with the addition of
`resolve-deterministic-cases`. Milestones 4/7 provider grants, Milestone 5
accounting, Milestone 11 acknowledgement, and Milestone 12 extension remain
unimplemented. Human diff review is required before commit; do not begin
Milestone 3.

## Architecture A Milestone 1 aggregate coordination

The coordination-only aggregate package is implemented offline as
`suggest-moving-service-questions-v4-formal-evaluation-live-v1`. It binds the
exact frozen ten-case package, fixed AI order, runner, budget, request triples,
seven-day lifetime, zero-retry rule, and closed historical execution manifest.
Locked hash-chained history plus a replay-validated snapshot survives fresh
processes and detects retained-head rollback, malformed state, identity/order
drift, illegal transitions, and nonzero provider counters.

The five commands only verify, initialize, inspect/resume, verify state, and
close/abandon coordination. No credential, provider request/client, network,
preflight/generation grant, spending authority, deterministic case execution,
or runtime integration exists. Cases 07/08 remain explicitly pending Milestone
2 initialization. Budget accounting, acknowledgement events, and reviewed
extensions remain owned by Milestones 5, 11, and 12 respectively.

Focused network-disabled tests and exact-command rehearsal pass. The milestone
now also has operation-specific semantic replay, exact history count/head
reconciliation, acknowledgement and finalization invariants, canonical UTC
event ordering, and crash recovery for a missing or provably stale derived
projection. History remains authoritative and unchanged during recovery.
Correctly rehashed illegal mutations fail semantically. The corrected milestone
also prevents `prepared` or `approved` coordination from starting at or after
the inclusive expiration boundary; it materializes `expired_paused` first and
exposes no actionable next case. The explicit adversarial matrix now covers all
six budget fields, extra/substituted cases, generation identity, premature
finalization, and unauthorized lifetime extension. It is ready for another
human diff review; do not commit or begin Milestone 2 before that review.

## Frozen-v4 formal evaluation runner

An offline-only runner now targets the immutable ten-case frozen-v4 evaluation
set with an 8-generation/2-deterministic-empty execution model. It enforces one
attempt per eligible case, zero retries, exact per-case request identities,
bounded synthetic preflight/generation counts, mandatory human review and
evidence deletion, non-replacement, cross-case isolation, and deterministic
graduation scoring.

The corrected eleven-command surface is network-disabled and uses one locked,
SHA-256-chained `.local` transition journal across processes, with `ledger.json`
as a validated projection. Exact preflight and closure artifacts, semantic
review reconciliation, and crash-recoverable deletion transactions now prevent
canonical snapshot rollback and stranded evidence deletion. Human review,
explicit idempotent evidence deletion, and final report generation are now
case/evidence-bound
rather than disconnected previews. It produces clearly marked
synthetic reports for nominal `graduate`, hard-gate `fail`, quality-gate
`remain_experimental`, and provider-failure `remain_experimental` rehearsals.
Journal replay now derives operation-specific counters, terminal semantics, and
artifact bindings; durable recovery is hash-chained and replay-validated, and committed deletion
transactions plus complete closure lifecycles are semantically revalidated.
Recovery classification is now derived from a pre-mutation recovery basis
anchored by `recovery_prepared` and linked to `recovery_completed`; fully
rehashed counter and terminal-lifecycle mutation matrices
prove semantic rejection independently of hash freshness.
These integrity claims are relative to the retained local journal head; total,
consistent malicious rewriting of all local state is explicitly out of scope.
Deletion transaction integrity is defined over canonical JSON content rather
than insignificant formatting bytes, and the documented lifecycle includes the
durable `removal_prepared` boundary.
Another focused human diff review is the next milestone. No live evaluation
authorization, spending, credential access, provider operation, or runtime
integration exists.

## Resolved frozen-v4 generation candidate

The live frozen-v4 sequence-1 preflight succeeded with 2,852 input tokens and
conservative maximum generation cost `$0.0019408`; its evidence was reviewed
and approved before the deadline. The consumed, non-reusable lifecycle remains
permanently closed.

An inactive sequence-4 generation candidate is now resolved offline against
the exact v4 evidence/review, request identities, and lifecycle history. Its 12
fixed commands pass five network-disabled scenarios, including bounded rejected-
prose diagnostics, grounding review/deletion, closure, and non-reuse. The next
milestone is human diff review. Do not prepare generation timestamps or
activate authority before that review; no live v4 generation has occurred.

The corrected live boundary independently validates historically closed v4
preflight records and the exact current active-generation manifest. It also
validates the complete active authorization against the resolved candidate
before credential access. Human diff review remains required before commit;
no live generation package or timestamps exist.

The rehearsal fidelity correction now builds full synthetic preflight history
through the actual lifecycle functions and exercises positive and negative
states through the live entry boundary. The public command inventory remains
12; another human diff review is required before commit.

## Frozen-v4 preflight-gate follow-up

Frozen v4 passed post-commit integrity review. A new offline-only preflight
workflow now uses `moving-service-stage-b-v4-pilot-20260808`, sequence 1,
fixture `storage_unknown`. Its inactive candidate is bound to the exact v4
request identities; v2/v3 evidence cannot satisfy it.

The 12-command public workflow passed a network-disabled rehearsal with one
synthetic preflight, zero generations, same-shell credential isolation,
immediate evidence review, non-authoritative generation-binding preview,
closure, non-reuse, and expired-package cleanup. The later live sequence-1
preflight succeeded and was timely reviewed; its authority is consumed and
cannot be reused. Generation remains unauthorized.

Lifecycle approval now validates the exact authorization, activation, final
transaction, audit, consumption, closure, and permanent-closed chain. Evidence
binds those records by SHA-256, and the binding preview independently repeats
the validation; presence-only history checks are no longer accepted.
Complete authorization scope, activation-manifest identity, final transaction
semantics, credential/client outcomes, and the UTC lifecycle timeline are also
validated from their source records. Semantic-mutation tests recompute all
downstream digests to prove that a self-consistent but wrong chain fails.

## Frozen prompt-v4 follow-up

The approved minimal prompt-v4 design is now implemented and frozen offline.
It adds explicit evidence/generated-prose/grounding separation, the exact four-
trigger runtime-alignment rule, and a final silent user-facing-field lexical
self-check. Exact grounding is never paraphrased; prohibited grounding now
fails before provider-request construction. Validator and fallback v2 remain
unchanged.

The existing generation gate can be mechanically rebound, but prompt v4 has a
new deterministic request, canonical attempt, and provider fingerprint. The
next eligible milestone is post-commit review of the frozen package. Any later
live path requires a fresh separately versioned v4 token preflight first.
Generation remains unauthorized.

## Frozen-v3 rejected-prose diagnostics

The one consumed live frozen-v3 generation passed structural and semantic
validation, then failed only `storage_modality_overstatement`; fallback v2 was
selected and permanent closure was restored. Rejected prose was intentionally
not retained, so the exact field, trigger, and wording are unknowable.

Future prose failures now record only bounded rule/field/offset/canonical-
trigger metadata, with behavioral-equivalence and privacy tests. The existing
validators and fallback are unchanged. The next eligible design milestone is a
narrow prompt-v4 review focused on instruction salience; it must not assume the
unavailable historical wording or authorize another live attempt.

## Resolved frozen-v3 generation candidate

The inactive frozen-v3 sequence-4 generation candidate is now deterministically
resolved against the approved live v3 sequence-1 preflight evidence. The exact
binding is 2,542 input tokens, conservative maximum cost `$0.0018168`, evidence
digest `0de37564...`, review digest `5e61e2a7...`, and binding-preview digest
`58d6c4d6...`. The resolved candidate remains non-authoritative, placeholder-
bound, and invalid for execution; generation remains unauthorized.

The next milestone is final human review of the resolved candidate, its 12
fixed public commands, and the exact five-scenario rehearsal. A fixed,
dry-run-by-default expired-review cleanup command is included. No live v3
generation has occurred.

## Frozen-v3 token-preflight workflow

A distinct frozen-v3 preflight workflow now uses run series
`moving-service-stage-b-v3-pilot-20260807`, sequence 1, and prefix
`001-storage_unknown`. It is fixed to the exact frozen-v3 deterministic
request, canonical attempt, and provider fingerprint. The complete public
workflow passes a network-disabled rehearsal with one fake preflight, zero
generation, immediate approved evidence review, a non-writing generation-gate
binding preview, closure, cleanup, and non-reuse.

The next milestone is final human review of the committed v3 preflight
candidate, public commands, same-shell boundary, evidence-review deadline, and
synthetic rehearsal. Do not prepare live timestamps until that review passes.
After a later successful live v3 preflight and same-session evidence approval,
a separate offline milestone must version the resolved v3 generation candidate
before live generation can be reconsidered.

## Frozen-v3 generation-gate follow-up

The frozen-v3 sequence-4 generation gate is now versioned and fully rehearsed
offline, but it is intentionally blocked from live preparation. Prompt v3
changes the deterministic request (`952b8003...`), canonical attempt
(`d9d81418...`), and provider fingerprint (`a5895ad5...`), so the approved v2
preflight evidence cannot authorize the v3 request. The exact remaining step is
a separately versioned, reviewed, network-capable v3 token-preflight workflow;
only its approved token count and evidence/review digests may resolve the
generation candidate. Do not prepare v3 generation timestamps first.

The v3 gate otherwise preserves the reviewed architecture: credential-free
exact-attempt verification, zero generation preflights, one generation, zero
retries, same-shell credential handling, unchanged semantic/prose validators,
fallback v2, grounding review, evidence deletion, closure, and non-reuse. Five
network-disabled exact-command scenarios pass, including the documented
prompt-policy-stricter-than-validator stress case.

## Frozen prompt-v3 follow-up

The approved prompt-v3 draft is now materialized as a frozen, offline-only
experimental package. Prompt and schema identities advance to v3; the schema
change is literal/title-only, the provider schema removes titles only, all five
v2 prose validators remain unchanged, and deterministic fallback remains
`moving-service-fallback-v2`. The package has no live pilot configuration,
authorization path, backend/frontend reachability, credential permission, or
generation authority.

The generation-gate versioning and network-disabled rehearsal are complete.
The next eligible milestone is fresh v3 preflight versioning and rehearsal.
Do not prepare live timestamps or expose prompt v3 at runtime before that work
is reviewed. Bounded rejected-prose diagnostics remain separate.

## Sequence-4 generation-gate design

The consumed live sequence-4 generation passed structural and semantic
validation but failed the unchanged v2 prose guardrails for storage modality
and service-selection language. The raw rejected response was intentionally not
retained. An offline diagnostic maps the exact lexical behavior and recommends
a narrowly scoped prompt v3 while preserving both validators. Any prompt-v3
drafting or bounded rejected-prose diagnostic metadata requires a separate
reviewed milestone; generation remains unauthorized.

The approved prompt-v3 design uses explicit may/might/could
modality, broader prompt-level service-selection prohibitions, neutral
`why_it_matters` guidance, and confinement of `services to request` to exact
grounding mirroring. Literal-only v3 Pydantic identities and a strict provider
schema are now frozen. The package remains example-free, unauthorized, and
unreachable from production runtime.

Sequence-4 preflight succeeded, was reviewed before its deadline, closed, and
is consumed. The approved evidence binds 2,228 input tokens, conservative cost
`$0.0016912`, and the exact frozen request/provider identities. A distinct
inactive generation-only candidate and fixed offline workflow passed the
network-disabled end-to-end rehearsal. Generation remains unauthorized; no
live generation timestamps may be prepared until final human review.

The two findings from the first final review have been corrected offline:
exact request verification precedes credential inspection, and the synthetic
rehearsal executes and accounts for every public generation command. A new
rehearsal-assertion finding is also corrected: four independently executed
scenarios now substantiate every printed success claim from actual lifecycle
records. A new bounded final human review is still required before any live
timestamps.

## Sequence-4 preflight readiness

Sequences 1, 2, and 3 are consumed historical attempts. Sequence 4 now has a
distinct inactive candidate, fixed `004-storage_unknown` workflow, corrected
same-shell credential boundary, and a pinned immediate evidence-review command.
The complete public workflow passed a network-disabled synthetic rehearsal with
one fake preflight, zero generation calls, immediate approved evidence review,
permanent closure, and non-reuse rejection. Before any live timestamps, perform
the two exact Phase-0 readiness commands now documented in the sequence-4
operator runbook, then perform the bounded human readiness review. Every
successful live preflight must be
reviewed before its evidence deadline in the same session. Generation, formal
evaluation, Stage C, and production remain unauthorized.

## Goal

Design the first version of GoTime's reasoning engine by observing how an experienced project manager plans a real relocation.

The objective is not to create a task hierarchy. The objective is to discover how GoTime should think.

## Tasks

* [ ] Role-play a relocation planning session.
* [ ] Capture every question the project manager asks.
* [ ] Record every recommendation and the reasoning behind it.
* [ ] Identify facts, rules, and inferences revealed during the conversation.
* [ ] Note any new domain concepts that emerge naturally.
* [ ] Update `docs/reasoning-engine.md` with the results.

## Success Criteria

By the end of the session we should understand:

* What information the reasoning engine requires.
* How it reaches recommendations.
* How it explains its recommendations.
* Which domain concepts naturally emerge from the planning conversation.

Domain terms such as Goal, Project, Phase, Task, Milestone, and Dependency should be refined only after the reasoning process is better understood.

## Notes

Treat the conversation as requirements discovery.

Do not design the database.

Do not design user interfaces.

Focus entirely on understanding how GoTime should reason about a complex goal.

# First Reasoning Loop

## Status

Implementation complete, reviewed, and verified. The changes are ready to commit.

## Scenario

The user wants to relocate from Tennessee to Northern California.

The target location has not been selected.

The spouse's employment requirements are still unclear.

Several downstream decisions depend on location.

## Expected Recommendation

> Clarify spouse employment requirements before choosing a final target location.

## Explanation

- Employment location affects housing affordability.
- Employment location affects commute viability.
- The target location decision is only partially ready.
- Housing search and neighborhood research depend on that decision.

## Implementation Scope

- Create in-memory models for:
  - Goal
  - SuccessCriterion
  - Constraint
  - Preference
  - Decision
  - Assumption
  - Recommendation
- Hard-code one relocation scenario.
- Implement one deterministic reasoning rule.
- Return one Recommendation with an explanation.
- Add tests for the reasoning rule.

## Out of Scope

- Database
- Authentication
- AI model calls
- Generic rule engine
- Frontend forms
- Multiple goals

## Review Focus

- Confirm the primary Recommendation is useful and trustworthy.
- Review whether the endpoint exposes the right explanation detail.
- Decide whether the existing static frontend should consume this endpoint in
  the next slice.

# Next Session (/19/2026) State Change and Re-Reasoning

## Previous Milestone

The first in-memory reasoning loop is complete, tested, verified through Docker, committed, and pushed.

The current backend:

* Builds one hard-coded relocation Goal snapshot.
* Identifies an unresolved employment-related dependency.
* Produces one deterministic primary Recommendation.
* Explains why the Recommendation matters now.
* Exposes the result through `GET /api/recommendations/primary`.
* Includes focused reasoning and endpoint tests.

## Next Objective

Demonstrate that GoTime can update its Recommendation when the known state changes.

The next slice should prove this loop:

```text
Represent state
→ Reason
→ Recommend
→ Change state
→ Re-reason
→ Produce a different Recommendation
```

## Initial State

The spouse's employment requirements are unclear.

The target-location Decision is only partially ready.

### Expected Recommendation

> Clarify spouse employment requirements before choosing a final target location.

## Updated State

The spouse's employment requirements have been clarified.

The separate Assumption that suitable employment exists in one or more viable candidate regions remains unconfirmed.

### Expected Recommendation

> Evaluate candidate locations against the clarified employment requirements.

The engine should not yet recommend selecting a final location because other information may still be unresolved, including:

* Housing affordability
* Commute viability
* Healthcare access
* Environmental risk
* Availability of suitable employment

## Implementation Scope

* Add the minimum state needed to distinguish:

  * Employment requirements unclear
  * Employment requirements clarified
* Build or derive a second immutable Goal snapshot representing the updated state.
* Add one deterministic reasoning path for the updated state.
* Return a different primary Recommendation for that state.
* Preserve the existing Recommendation for the original state.
* Add focused tests proving:

  * The original state produces the original Recommendation.
  * The updated state produces the new Recommendation.
  * The two states produce different results.
  * Both API responses remain valid and explained.

## Modeling Guidance

Keep the implementation narrow.

Do not introduce a generic state-management system or rule engine.

Clarifying employment requirements should not validate the Assumption that suitable employment exists.

The model should continue to distinguish:

* **Required information:** What employment conditions are acceptable?
* **Assumption:** Suitable employment exists within viable candidate regions.

Use immutable snapshots or model copies rather than mutating the existing Goal.

## API Question

Choose the smallest API design that demonstrates both states clearly.

Possible approaches include:

* A second temporary endpoint for the updated scenario.
* A query parameter selecting the scenario state.
* A narrowly defined request body that supplies the changed state.

Prefer the option that adds the least infrastructure while keeping the state transition understandable and testable.

Do not add persistence yet.

## Out of Scope

* Database persistence
* Authentication
* AI model calls
* Generic rule-engine infrastructure
* Generic dependency graphs
* Frontend forms
* User accounts
* Multiple Goals
* Production state management
* Broad domain-model expansion

## Review Focus

* Does the Recommendation genuinely change because the input state changed?
* Is the second Recommendation useful and appropriately cautious?
* Is the distinction between required information and Assumption validation preserved?
* Does the implementation remain deterministic and easy to understand?
* Is the API sufficient to demonstrate re-reasoning without prematurely designing persistence?
* Are explanations clear about what changed and why the Recommendation changed?

## Definition of Done

This slice is complete when:

* The original state produces the employment-requirements Recommendation.
* The updated state produces a different candidate-location evaluation Recommendation.
* Both reasoning paths have focused tests.
* The API exposes both results in a clear, minimal way.
* Docker verification passes.
* No persistence, generic rules framework, or unnecessary abstraction has been introduced.

## Implementation Status

Implementation is complete, reviewed, and verified. The next planned work is
described in the Later Slice below.

The temporary API proof supports:

* No query parameter or `employment_requirements=unclear` for the original
  Recommendation.
* `employment_requirements=clarified` for the updated Recommendation.
* HTTP 422 for unsupported query values or recognized states without an
  applicable reasoning path.

## Later Slice

After state change and re-reasoning are proven, connect the existing frontend concept screen to the Recommendation endpoint.

# Frontend Recommendation Integration

## Status

Implementation is complete, reviewed, and verified.

The existing concept screen now:

* Loads the original Recommendation from the backend by default.
* Displays the complete human-readable explanation, dependencies, blocked
  work, and related employment Assumption.
* Uses a temporary scenario control to request either the unclear or clarified
  employment-requirements snapshot.
* Handles loading, failed requests, and obsolete responses.

## Intended-User Feedback

The current frontend is acceptable for this stage and successfully demonstrates
the end-to-end reasoning loop.

The interface is still too early to evaluate meaningfully for layout or visual
refinement. Do not begin a redesign yet.

The current language feels clinical and dry because it exposes internal
reasoning vocabulary too directly, including phrases such as:

* Partially ready
* Relevant dependencies
* Blocked downstream work
* Unconfirmed assumption

This language is acceptable for the current proof. Future user-facing copy
should translate internal reasoning concepts into warmer, more natural
guidance. For example:

> **What to focus on now**
>
> Clarify what kind of work would be acceptable for your spouse before
> narrowing the location search.

## Deferred Language and UI Concerns

Treat the clinical language and early visual design as documented product
concerns, not immediate polishing tasks. Revisit them after the interaction and
reasoning model are more mature, when user feedback can evaluate the experience
in a more meaningful context.

# Meaningful State Input

## Status

Implementation is complete, reviewed, and verified.

* The temporary scenario selector has been replaced with a realistic
  confirmation action attached to the current Recommendation.
* The user can confirm that spouse employment requirements have been clarified.
* That confirmation triggers re-reasoning and produces a new Recommendation.
* The suitable-employment Assumption remains unconfirmed.
* The interaction remains intentionally local and non-persistent.
* Frontend, backend, Docker, and integration verification all pass.

# Next Milestone — Capture One Concrete Employment Requirement

## Status

Implementation is complete, reviewed, and verified.

* The user can submit one actual requirement: an acceptable remote, hybrid,
  on-site, or flexible work arrangement.
* No submitted value preserves the original Recommendation and means the
  requirement remains unclear.
* The submitted value is represented on the in-memory Goal snapshot and is the
  only source of truth for whether this requirement has been clarified.
* Each accepted value produces meaningful, deterministic reasoning about how
  to evaluate candidate locations.
* The suitable-employment Assumption remains unconfirmed for every value.
* Work arrangement remains only one part of employment suitability.
* Candidate locations are not yet scored or compared.
* State remains intentionally local and non-persistent.
* Frontend, backend, Docker, integration, and query-validation checks pass.

# Next Milestone — Capture One Concrete Commute Requirement

## Status

Implementation is complete and verified.

* Hybrid and on-site paths ask for the longest acceptable one-way commute.
* The user can submit a positive whole-number limit in minutes.
* `acceptable_commute_minutes` is represented as a hard, user-provided
  evaluation boundary in the in-memory Goal snapshot.
* Contradictory arrangements and invalid limits return HTTP 422.
* The Recommendation uses the limit when explaining how candidate locations
  should be evaluated.
* The engine does not treat the limit as an observed commute, calculate travel
  time, or claim that any candidate location passes or fails.
* A likely workplace location and credible travel-time evidence are still
  required. Hybrid frequency also remains unknown.
* Suitable employment remains an unconfirmed Assumption.
* State remains intentionally local and non-persistent.
* Frontend, backend, Docker, integration, compilation, and whitespace
  verification pass.

# Next Milestone — Capture a Likely Workplace Area

## Status

Implementation is complete and verified.

* The user can provide one free-form likely workplace area after submitting a
  hybrid or on-site arrangement and maximum one-way commute.
* The value is trimmed, limited to 120 characters, and treated as opaque
  user-provided planning context.
* The API rejects blank, over-length, and prerequisite-incompatible values.
* The Recommendation advances from defining commute requirements to gathering
  credible one-way travel-time evidence.
* The engine does not verify or normalize the area, geocode it, calculate a
  route, or claim that any candidate location passes or fails.
* Traffic conditions and travel mode remain unresolved. Hybrid frequency also
  remains unresolved for hybrid work.
* Suitable employment remains an unconfirmed Assumption.
* State remains intentionally local and non-persistent.
* Frontend, backend, Docker, integration, compilation, and whitespace
  verification pass.

# Next Milestone — Capture an Intended Commute Travel Mode

## Status

Implementation is complete and verified.

* `intended_commute_travel_mode` records user-provided relocation planning
  context as `drive`, `public_transit`, or `either`.
* `either` means driving and public transit are both acceptable and evidence
  should be gathered for both; it does not mean unknown.
* A mode is accepted only after hybrid or on-site work, a maximum one-way
  commute, and a likely workplace area have been supplied.
* A supplied mode changes the Recommendation by identifying which manual
  travel-time evidence should be gathered.
* Mode-specific explanations preserve unresolved driving traffic, transit
  schedules, transfers, station access, and hybrid frequency where applicable.
* No route, travel time, workplace, candidate viability, or suitable
  employment has been verified.
* State remains intentionally local and non-persistent.
* Frontend, backend, Docker, integration, compilation, and whitespace
  verification pass.

# Next Session — Decide Where AI Assistance Should Enter GoTime

## Objective

Review the deterministic reasoning prototype and decide where AI-assisted
interpretation or suggestion should first enter GoTime.

## Questions to Examine

* What does the deterministic engine already prove?
* Which current Recommendations, explanations, and scenario inputs are still
  scripted?
* Which responsibilities should remain deterministic?
* Which narrow capability would genuinely benefit from AI?
* How would AI-generated suggestions remain grounded in known state,
  transparent to the user, and covered by repeatable tests?
* Is another deterministic input necessary before introducing AI assistance?

## Expected Outcome

Select one narrow, evidence-backed capability for a future milestone, or decide
that the deterministic prototype needs one more input first. Do not begin AI
integration merely because the current scripted flow has reached a natural
review point.

Hybrid commute frequency remains a possible future deterministic input, but it
is not the committed next implementation milestone.

## Out of Scope

* Implementing an AI model call
* Selecting broad AI infrastructure
* Replacing deterministic validation or state transitions
* Persistence or authentication
* Mapping, routing, geocoding, or transit integrations
* Candidate-location scoring
* Broad frontend redesign

Keep the empty `docs/adr/ADR-0001-monorepo.md` issue separate from this
session.

# First Fake-Adapter Slice — Suggest Moving-Service Questions

## Status

Implementation is complete, verified, and ready for review.

The slice now:

* Constructs a bounded `suggest_moving_service_questions` request from narrow
  trusted experiment fixtures.
* Invokes one capability-specific fake adapter after an explicit user action.
* Validates the complete structured response deterministically.
* Rejects invalid responses without retaining individual suggestions.
* Uses one frozen deterministic fallback question when an applicable gap
  remains.
* Returns a valid no-question result when all supported information is known.
* Presents one optional question beneath the primary deterministic
  Recommendation.
* Lets the user dismiss the suggestion, inspect its grounding, or confirm a
  boolean answer locally.
* Leaves the current trusted `Goal` unchanged and does not trigger
  re-reasoning.
* Records bounded observability with a `$0.00` fake-adapter cost.

The temporary fixture endpoint supports:

* `storage_unknown`
* `complete`
* `invalid_ai_response`
* `adapter_unavailable`
* `adapter_timeout`
* `budget_unavailable`
* `ai_disabled`

Unsupported fixtures and unexpected query parameters return HTTP 422.

## Review Focus

* Confirm that the request contains only approved experiment context.
* Confirm that response validation rejects the complete invalid response.
* Confirm that fallback guidance remains useful and is not presented as an
  error.
* Confirm that source labels are helpful without emphasizing implementation
  mechanics.
* Confirm that local answer confirmation cannot update trusted state.
* Decide whether the in-code fallback baseline and temporary fixture artifacts
  should be reconciled with the older draft `v1` JSON artifacts in a separate
  documentation-and-fixture slice.

## Explicitly Not Proven

This slice does not prove that AI adds product value or that the experiment
knowledge is sufficient for real-model use. No real-model work may begin until
curated statements have approved sources, the knowledge fixture is versioned
for that purpose, and the fake-adapter contract is approved.

# Historical Milestone — V1 Artifact Reconciliation

The status below records the package before the later FMCSA knowledge-curation
milestone. Current readiness is documented in the sections that follow.

## Status

Implementation is complete, verified, and ready for review.

The older `v1` package now:

* Uses the exact runtime knowledge-item, missing-information, fallback,
  trusted-state, request, and response vocabulary.
* Contains executable `storage_unknown`, `complete`, and contract-only
  multiple-gap request fixtures.
* Contains valid, zero-suggestion, and eight invalid response fixtures.
* Records expected valid, invalid, fallback, unavailable, timeout,
  budget-unavailable, disabled, no-question, and observability outcomes.
* Delegates request construction, response validation, fallback selection, and
  orchestration expectations to the runtime implementation.
* Separates contract-test readiness from real-model-evaluation readiness.
* Is contract-test eligible and explicitly ineligible for real-model
  evaluation.

The knowledge artifact contains only the current storage implementation
fixture. It is valid for fake-adapter and compatibility testing, has no
approved real-model grounding source, and does not imply that the broader
six-model knowledge set is complete.

Production runtime remains independent from `docs/`. Backend anti-drift tests
load the package; application execution does not.

## Review Focus

* Confirm the artifact package contains no legacy nested claim schema.
* Confirm manifest readiness values and reasons are accurate.
* Confirm artifact compatibility tests use runtime behavior rather than a
  second implementation.
* Confirm the narrow knowledge boundary is not overstated.
* Confirm no real-model work begins until a separately reviewed knowledge
  curation step satisfies the documented gate.

# Next Session — Curate Knowledge for the First Real-Model Evaluation

## Status

Implementation complete and verified. The approved FMCSA-backed fixture is
eligible only for a controlled real-model evaluation of the `storage_unknown`
question suggestion. No real model has been connected.

## Previous Milestone

The moving-service experiment artifacts have been reconciled with the approved runtime contract.

The current experiment now has:

* A bounded request contract.
* A structured response contract.
* A fake adapter.
* Complete-response validation.
* A deterministic fallback.
* A browser-based experiment flow.
* Executable artifact fixtures.
* Runtime anti-drift tests.
* Separate readiness flags for:

  * Contract testing
  * Real-model evaluation

The artifact package is currently:

* `contract_test_eligible: true`
* `real_model_evaluation_eligible: true`

This readiness is limited to the controlled `storage_unknown` evaluation. It
does not mean production approval, complete moving-service knowledge, or
readiness for service-model comparison.

## Next Objective

Create the smallest reviewed, source-backed moving-service knowledge fixture needed to evaluate:

`suggest_moving_service_questions`

against the `storage_unknown` scenario.

This session should determine whether a real model can be given trustworthy, bounded knowledge for suggesting this question:

> Will you need temporary storage between homes?

The session should not connect a real model.

## Product Question

Can GoTime ground one useful moving-service question in reviewed domain knowledge without requiring a broad moving-industry knowledge library?

## Knowledge Scope

Curate only the knowledge needed to establish that temporary storage needs can affect which moving-service approaches are practical to investigate.

The knowledge should support question discovery.

It does not need to provide:

* A complete comparison of moving-service models.
* A recommended moving-service model.
* Provider-specific guidance.
* Pricing.
* Availability.
* Booking windows.
* Rankings.
* Current market research.

## Required Knowledge Item Fields

Each approved knowledge item must include:

* `knowledge_id`
* `service_model`
* `statement`
* `tradeoff_category`
* `applicable_conditions`
* `source`
* `reviewed_at`
* `freshness_guidance`
* `version`

The statement must be:

* Narrow.
* Directly supported by the cited source.
* Relevant to the storage question.
* Free of provider selection or ranking.
* Stable enough that live research is unnecessary.
* Appropriate for a controlled question-suggestion evaluation.

## Source Requirements

Use authoritative or primary sources where reasonably available.

For each source, record:

* Publisher
* Title
* Stable locator
* Date accessed or reviewed
* The specific claim it supports
* Any limitations

The source must be read and reviewed rather than merely collected.

Do not use:

* Unattributed AI summaries.
* Unsupported generalizations.
* Placeholder citations.
* Provider marketing as evidence for broad industry-wide claims unless its limitations are explicit.
* Current pricing or availability claims.
* Information that requires live research to remain reliable.

## Review Questions

For each proposed statement, ask:

* Is this statement necessary for the `storage_unknown` fixture?
* Does the source directly support it?
* Is the wording narrower than or equal to what the source establishes?
* Does it avoid recommending a service model?
* Does it avoid implying that temporary storage is definitely required?
* Is it stable enough for curated knowledge?
* What freshness guidance should apply?
* Would the statement remain useful if the user ultimately does not need storage?
* Does the complete bounded request remain within the experiment’s token budget?

## Artifact Updates

After the knowledge has been reviewed:

* Update `curated-knowledge.json`.
* Update the manifest knowledge version.
* Update any affected request or expected-result fixtures.
* Update knowledge references where necessary.
* Preserve compatibility with the runtime `CuratedKnowledgeItem` model.
* Keep production runtime independent from files under `docs/`.

Do not mark the package as real-model eligible merely because the JSON validates.

## Readiness Decision

At the end of the session, explicitly decide whether:

`real_model_evaluation_eligible`

can change from `false` to `true`.

It may become `true` only if:

* Every included statement has an approved source.
* Every statement is narrowly supported.
* Review and freshness metadata are complete.
* The artifact/runtime compatibility tests pass.
* The full request remains within the declared token budget.
* The fake-adapter and deterministic-fallback tests still pass.
* No placeholder or unreviewed knowledge remains in the evaluated fixture.

If any requirement remains unmet, keep the flag `false` and record the exact ineligibility reasons.

## Deliverables

The session should produce:

* One or more reviewed knowledge statements sufficient for the storage-question fixture.
* Complete source and freshness metadata.
* Updated versioned artifacts.
* Updated readiness metadata.
* Tests confirming artifact/runtime compatibility.
* A brief review note explaining what the knowledge is approved to support.
* An explicit statement of what it is not approved to support.

## Out of Scope

Do not add:

* A real model adapter.
* An AI SDK.
* API credentials.
* Live web research during application execution.
* Provider recommendations.
* Provider rankings.
* Quotes or availability.
* Booking-window logic.
* A complete six-model moving-service library.
* Vector infrastructure.
* Persistence.
* Automatic trusted-state updates.
* General-purpose chat.
* Background AI activity.

## Definition of Done

This milestone is complete when:

* The storage-question knowledge fixture contains no placeholders.
* Every included statement has been human-reviewed against an identifiable source.
* Statements are bounded to the first experiment.
* Freshness guidance and versions are recorded.
* Runtime and artifact compatibility tests pass.
* The deterministic fallback remains unchanged and useful.
* The package’s real-model readiness status is reviewed explicitly.
* No real model has been connected.

## Later Milestone

Only after the knowledge fixture is approved should GoTime design the real-model adapter and controlled evaluation run.

That later milestone should compare real-model suggestions against the frozen deterministic fallback using the approved fixtures, rubric, cost ceiling, and latency limits.

# Next Milestone — Design the Controlled Real-Model Evaluation

## Objective

Design the controlled real-model evaluation for:

`suggest_moving_service_questions`

The evaluation should determine whether a real model provides material,
repeatable value beyond the frozen deterministic fallback for the approved
`storage_unknown` fixture.

This is an evaluation-design milestone, not a production rollout. Do not
implement or enable the real-model adapter until its boundary, controls,
credentials, evaluation protocol, and failure behavior have been reviewed.

## Design Scope

Define:

* A provisional, capability-specific model adapter boundary that preserves the
  approved runtime request and response contracts.
* Evaluation-only credentials and configuration that cannot silently enable
  production or background use.
* The exact fixed scenarios to run, including the approved `storage_unknown`
  fixture and required negative or no-question controls.
* A fixed repeated-run count for each model and scenario combination.
* The minimum schema-validity threshold required to continue evaluation.
* Automated and human checks for grounded knowledge use, unsupported claims,
  hallucinations, known-state repetition, and prohibited recommendations.
* The existing per-call cost ceiling, monthly experiment ceiling, target
  latency, and hard timeout.
* A comparison method against the frozen deterministic fallback that measures
  usefulness rather than wording alone.
* A bounded human review process, reviewer rubric, and result-recording format.
* Explicit promotion criteria and failure criteria.
* A safe rollback path to the fake adapter or deterministic fallback when the
  model is unavailable, invalid, over budget, too slow, or not demonstrably
  better.

## Required Boundaries

The design must:

* Keep the experiment limited to
  `suggest_moving_service_questions`.
* Preserve complete-response validation and rejection.
* Preserve explicit user invocation and the trusted-state confirmation
  boundary.
* Use only the approved, versioned storage knowledge for the controlled
  `storage_unknown` evaluation.
* Keep the frozen deterministic fallback as both the comparison baseline and
  safe no-model path.
* Prevent evaluation credentials or configuration from becoming production
  defaults.
* Define how evaluation observability excludes full prompts, full responses,
  sensitive answers, and unnecessary trusted state.
* Stop the evaluation when cost, latency, validity, grounding, or safety limits
  are exceeded.

## Out of Scope

Do not:

* Roll the capability out to production users.
* Add autonomous or background model calls.
* Add provider recommendations, rankings, pricing, availability, or live
  research.
* Expand the knowledge fixture beyond what an approved evaluation scenario
  requires.
* Add vector infrastructure, persistence, general-purpose chat, or generic
  cross-domain AI abstractions.
* Change trusted-state behavior or allow model output to write state.

## Expected Deliverable

Produce a reviewed evaluation protocol that is precise enough to implement in
a later, separately approved slice. Stop before adding a provider SDK,
credentials, or a real-model adapter.

# Next Session

## Current state

The controlled real-model evaluation for
`suggest_moving_service_questions` now has:

- A frozen, reviewed prompt artifact:
  - `docs/experiments/suggest-moving-service-questions/v1/real-model-prompt.toml`
- Frozen prompt SHA-256:
  - `583a4bdf59c4c4ac67c82928415710c3d5c21ac9912ebd4888a026b8fd4acbf2`
- A capability-specific, script-only, network-incapable adapter scaffold
- Deterministic request serialization
- Frozen-prompt verification
- Existing runtime response validation and deterministic fallback ownership
- An in-memory fake transport only
- Bounded local evaluation records
- A provisionally selected provider and AI model for transport design:
  - Provider: OpenAI
  - AI model identifier: `gpt-4.1-mini-2025-04-14`
- A narrowly revised protocol permitting unavoidable provider-managed prompt
  caching

The following remain unauthorized:

- Provider-specific transport implementation
- OpenAI SDK installation
- Credential creation or access
- Network calls
- Real-model execution
- Browser or FastAPI exposure
- Production use

## Next objective

Design the provider-specific OpenAI transport for the existing script-only
evaluation scaffold.

This is a design milestone only.

The design should define:

- The exact OpenAI Responses API request payload
- How the frozen system instructions and deterministic request JSON are
  supplied
- Strict JSON Schema adaptation for the existing response schema
- Exact preflight token counting through `/v1/responses/input_tokens`
- Usage and cached-token extraction
- Conservative cost calculation
- Twelve-second timeout behavior
- Zero automatic retries
- Error translation into the existing bounded adapter errors
- `store: false`
- Evaluation-only credential isolation
- OpenAI Python SDK and API-version pinning
- Offline mock and recorded-payload testing
- Authorization gates that continue to prevent any real call

## Required boundaries

Do not:

- Install the OpenAI SDK
- Add provider transport code
- Add or read credentials
- Add environment variables to repository files
- Modify the frozen prompt
- Modify the prompt digest
- Make a network request
- Call the OpenAI API
- Authorize provider-transport implementation
- Authorize real-model execution
- Expose the evaluation through FastAPI or the frontend
- Create a generic AI provider abstraction

## Terminology

Use explicit terms in explanations and documentation:

- **AI model** for the external generative system
- **AI model identifier** for `gpt-4.1-mini-2025-04-14`
- **Pydantic request schema** and **Pydantic response schema** for validated
  Python data structures
- **Domain object** for GoTime concepts such as Goal or Decision
- **Database entity** for future persistence structures

Avoid ambiguous phrases such as “send the request model to the model.”

## Startup check

At the beginning of the session:

1. Read `AGENTS.md`, `NEXT_SESSION.md`, and `TODO.md`.
2. Review the provider-selection and real-model-evaluation documents.
3. Confirm the working tree is clean.
4. Summarize the current authorization state.
5. Propose the provider-transport design plan.
6. Do not implement until the design is reviewed and approved.
