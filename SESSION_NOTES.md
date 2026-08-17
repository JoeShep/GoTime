# Session Notes

## 2026-08-16 — Multi-category browser-acceptance corrections

- Reused one controlled category-dropdown component for the plan filter and
  task editor, preserving internal selection/Clear all interactions while
  adding outside-click and Escape dismissal with trigger-focus restoration.
- Kept finder searching plan-wide; selection now clears only an incompatible
  category filter, announces that through the existing notice, and reveals,
  expands, scrolls to, focuses, and highlights hidden active or completed work.
- Added mobile-only task-card density rules below `575.98px` while preserving
  desktop utility classes, control tap targets, and existing priority/category
  badge styling.
- Focused plan verification passed 39 tests. Full verification passed all 59
  frontend tests, all 189 backend tests, and the production frontend build.
- No browser automation is configured or installed; final responsive visual
  acceptance remains for human browser review.

## 2026-08-16 — Relocation vocabulary cleanup

- Preserved the stable `move` phase ID and changed its user-facing title from
  `Complete the move` to `Make the move`, including existing seeded databases.
- Reduced the bounded task categories to Employment, Family, Financial,
  Healthcare, Housing, and Logistics across backend validation, SQLite
  constraints, frontend types, and the task editor.
- Added an idempotent legacy SQLite migration that reconciles Administrative
  tasks to Logistics and rebuilds the task/relationship tables by copying all
  rows, preserving task IDs, phase assignments, status, dates, priority,
  assignees, dependencies, and all other stored task fields.
- Added backend reload/migration and frontend vocabulary regressions; focused
  validation passed 35 backend tests and 32 frontend tests.
- Added only the approved future notes for user-defined project phases,
  user-defined categories, and subtasks/task hierarchy to the existing Parking
  Lot content.
- Kept multi-category tasks, editable phases/categories, People, related-task
  links, subtasks, priority redesign, dependency graph changes, and alternate
  views unimplemented.

## 2026-08-15 — Plan-wide task finder

- Passed hands-on verification for matching, keyboard and pointer navigation,
  completed-task reveal, focus/highlight, editor visibility, and no-results behavior.
- Added a frontend-only accessible autocomplete that locates active and
  completed tasks using case-insensitive title matching without filtering or
  rearranging phase lists.
- Kept result metadata bounded to title, phase, category, and completed state,
  with keyboard and pointer selection plus a concise no-results message.
- Selecting a result preserves task state, expands only the required completed
  section, scrolls and focuses the task article, and applies a lightweight
  reduced-motion-aware visual locator cue.
- Converted completed accordions to controlled per-phase expansion while
  preserving user-controlled open sections and existing task controls.
- Hid the finder throughout add and edit drafts; Cancel and successful saves
  restore it, while failed saves leave it hidden with the draft intact.
- Kept general task filtering, phase-header Add actions, phase-prefilled
  creation, and dependency terminology changes as unimplemented observations.

## 2026-08-15 — Task editor action ergonomics

- Hid the page-level `Add task` action while either add or edit mode is open;
  Cancel and successful saves restore it through the existing draft lifecycle,
  while failed saves retain the editor.
- Moved the editor's only primary and Cancel controls directly below its
  heading in a compact, responsive top-sticky action area within the card.
- Added operation-specific `Create task`, `Save changes`, `Creating…`, and
  `Saving…` labels while preserving native form submission and validation.
- Kept both actions disabled during a pending request and added a save guard to
  prevent intentional duplicate execution.
- Preserved editor scroll/focus, dependency selection, and completed-task
  behavior. Phase-header Add actions and dependency terminology remain
  unimplemented usage observations.
- Added focused coverage for action visibility and restoration, labels,
  pending states, duplicate-request prevention, sticky structure, failure
  retention, and existing scroll/focus behavior.

## 2026-08-15 — Completed task lifecycle and dependency semantics

- Kept completed tasks as stored phase history while separating them from
  active work in collapsed per-phase `Completed (n)` sections with working Edit
  and status controls.
- Prevented completed tasks from being introduced as new dependencies in both
  repository validation and the dependency picker. Existing completed
  relationships remain visible, searchable, and removable during editing.
- Preserved direct dependency rows across status changes. Completed
  dependencies stop blocking, reopening restores blocking, and transitive
  behavior remains derived without persisting extra relationships.
- Preserved completed-task exclusion and status-triggered recalculation in the
  deterministic recommendation flow.
- Added repository, endpoint, recommendation integration, picker, presentation,
  reopening, and `C → B → A` regression coverage.
- Left priority, task search, People/Users, assignment identities, categories,
  phases, related links, dependency visualization, Add/Save interaction,
  alternate views, authentication, and AI work unchanged.

## 2026-08-14 — Relocation-plan first-use usability verification

- Passed hands-on verification in the running application for generic
  assignee guidance, unassigned task creation, dependency editing, edit
  scroll/focus behavior, and searchable phase-grouped dependency selection.
- Passed 9 focused backend tests, 16 focused frontend tests, the full 177-test
  backend suite, the full 36-test frontend suite, the production frontend
  build, backend compilation, and rebuilt Compose runtime health checks.

## 2026-08-13 — Relocation-plan first-use usability follow-up

- Removed real-person assignee placeholders and made unassigned tasks valid in
  both create and full-replacement update contracts; unassigned tasks are
  labeled clearly in the plan.
- Preserved the complete dependency edit flow for existing tasks and added
  focused coverage for adding and removing dependencies after creation.
- Made Edit scroll the complete editor into view and focus the title field.
- Replaced the flat dependency list with case-insensitive search and
  relocation-phase grouping, excluding the edited task while preserving hidden
  selections during filtering. Backend cycle validation remains authoritative.
- Added focused API and UI regressions for unassigned tasks, generic
  placeholders, edit focus/scroll, dependency editing, phase grouping, search,
  and selection preservation.
- Deferred multiple categories, People, related links, transitive dependency
  storage, priority/ranking redesign, alternate views, AI, authentication, and
  notifications exactly as directed by the approved first-use review.
- The pre-existing unrelated `docs/parking-lot.md` working-tree change was
  excluded from this patch.

## 2026-08-13 — MVP Increment 2 deterministic next-task recommendation

- Added a read-only singleton-plan recommendation endpoint and bounded response
  model with structured ranking factors.
- Added a transparent actionable-task filter: incomplete, dependency-unblocked,
  and started as of the current date.
- Added explicit lexicographic ranking by priority, due state/date, in-progress
  status, direct unblocking leverage, phase order, and stable task ID.
- Added clear empty/completed/blocked-or-future no-actionable states without an
  opaque score or AI.
- Made the stored-task recommendation the primary React recommendation and kept
  the existing employment/commute flow as a separate planning section.
- Refreshes the recommendation from the API after successful plan mutations, so
  completing the current task can reveal the next task without a reload.
- Added focused engine, API, and frontend tests for eligibility, every ranking
  tie-break, explanations, no-actionable state, and mutation-driven refresh.
- No task schema, mutation API, AI experiment, authentication, notification, or
  multi-plan behavior changed. `docs/parking-lot.md` was not modified.

## 2026-08-13 — MVP Increment 1B persistent relocation-plan UI

- Added a typed frontend client for the fixed relocation-plan API.
- Added a React-Bootstrap plan view that renders all four phases, empty states,
  persisted task details, dependencies, and backend-derived blocked state.
- Added one bounded task editor for create and full-replacement update. Edit
  drafts hydrate every replaceable field, and blank nullable fields are sent as
  explicit `null` values.
- Added narrow task-status updates and clear success, validation, loading, and
  network-error states.
- Added focused UI tests for loading/rendering, create, complete PUT behavior,
  status changes, dependency selection/self-exclusion, blocked presentation,
  validation errors, and network failure.
- Preserved the existing deterministic recommendation experience. Stored-task
  recommendation ranking is deferred to the next approved product increment.
- No backend, AI experiment, authentication, notification, or multi-plan work
  was added. `docs/parking-lot.md` was not modified.

## 2026-08-13 — MVP Increment 1A persistent relocation-plan backend

- Added bounded `RelocationPlan`, `Phase`, and `Task` product models for one
  family relocation plan. Status, category, and priority use explicit MVP
  vocabularies; assignee names are bounded and dates are optional.
- Added a standard-library SQLite repository with normalized plan, phase, task,
  assignee, and dependency tables. A named Compose volume preserves the default
  database across backend container replacement.
- Added fixed GET/create/replace/status API operations under
  `/api/relocation-plan`; no generic goal/project API was introduced.
- Derived blocked state on every read: a non-completed task is blocked when any
  dependency is incomplete. Blocked state is not stored or editable.
- Enforced existing phases/tasks, no self-dependencies, unique dependencies,
  cycle rejection with transaction rollback, bounded values, and valid date
  ordering.
- Added repository reconstruction and API tests covering persistence, task
  mutation, status transitions, dependencies, blocking, invalid references,
  cycles, and schema constraints.
- Focused persistence/API/recommendation validation passed 69 tests; the full
  backend suite passed 160 tests. No historical AI experiment suite was run.
- Preserved the existing recommendation behavior. No frontend task UI,
  authentication, AI, notifications, research, or generalized multi-goal
  infrastructure was added.

## 2026-08-13 — Post-Milestone-9 framework reassessment

- Completed the required design-only checkpoint after top-level Milestone 9.
- Recommended `freeze_ai_infrastructure_and_return_to_product`: adopt no
  framework and pause additional custom evaluation infrastructure.
- Confirmed Milestones 1–9 already provide the bounded experiment's durable
  replay, budget/grant controls, atomic dispatch, same-shell credentials,
  zero-retry enforcement, preflight review gate, generation validation/evidence,
  closure, and fail-closed recovery.
- Assessed Temporal as the strongest future heavy-duty durability candidate,
  Inngest as a plausible event-driven hosted option, and LangGraph as a poor
  current fit for GoTime's deterministic, non-agentic core. None removes enough
  current work to justify migration or operations now.
- Classified Milestone 10 and Milestones 16–18 as necessary only on a future
  path toward live evaluation, with Milestones 11–15 deferrable or potentially
  reducible after a human-reviewed scope refresh. The historical plan and
  numbering were not changed or bypassed.
- Recorded that no additional implementation is needed to park the experiment:
  preserve `closed_no_execution_authorized`, create no live state, and retain
  the committed artifacts/tests.
- Set the next framework checkpoint to a demonstrated product need or a future
  proposal to unfreeze live-evaluation work, rather than a calendar date.
- No runtime, test, framework, dependency, provider, credential, frozen
  artifact, implementation-plan, architecture-memo, or Milestone 10 change was
  made.

## 2026-08-13 — Architecture A Milestone 9B

- Added versioned bounded generation result, evidence, and provider-phase
  closure models with explicit validated, structural, semantic, prose, timeout,
  transport, provider-error, and unknown-outcome classifications.
- Wired generation provider return directly into canonical frozen-v4
  validation and one history-first result transition. Exact reruns are
  event-free; conflicts and retained-history replacement fail closed.
- Bound replay to the actual retained generation `provider_dispatch_started`
  event and added fully rehashed semantic attacks for dispatch, immutable
  identities, evidence drift, missing dispatch, and retained-result deletion.
- Preserved frozen fallback behavior and content-free prose diagnostics. Raw
  rejected output, arbitrary provider payload, credentials, headers, request
  content, environment, and exception representations are not retained.
- Valid machine evidence leaves the case awaiting Milestone 10 generation
  evidence review and blocks next-case progression. No human generation review,
  deletion, deadline, scoring, acknowledgement, or extension behavior exists.
- Preserved every committed Milestone 9A digest by introducing 9B projection
  collections only at the first 9B event rather than changing historical state.
- Rehearsed the literal fixed generation launcher and Docker wrapper through the
  production execution entry and real 9B handler using only the lower-level
  synthetic provider seam in the network-disabled environment.
- Permanent authorization remains closed, retries remain zero, and real
  provider operations and real credentials remain zero. Framework reassessment
  remains after reviewed/committed 9B and before Milestone 10.
- Validation passed 21 dedicated 9B tests, 61 focused Milestones 8–9B tests, 91
  authoritative state/generation/dispatch regressions, and the apples-to-apples
  full offline suite at 1,295 passed with the same two historical
  Docker-daemon-dependent skips. Frozen foundation/permanent status and
  read-only Python compilation also passed.
- Corrected the final-review prose-diagnostic replay gap without changing any
  schema or fixed digest. Replay now enforces the frozen code order, rule ID,
  code-specific field/trigger domain, exact types and fields, bounded
  offsets/counts, valid spans, and exact code/diagnostic correspondence.
  Fully rehashed representative attacks fail while canonical diagnostics replay
  exactly. Corrected validation is 32 dedicated 9B tests, 51 focused 9A–9B,
  71 focused 8–9B, and 1,305 full-offline passes with the same two skips.

## 2026-08-12 — Architecture A Milestone 9A

- Corrected final-review replay findings without changing canonical identities:
  validated result history now requires exact evidence atomically, and result
  dispatch identity must equal the actual retained dispatch event at the
  authoritative before-state journal head. Added fully rehashed persisted
  attacks for missing evidence and a valid-looking wrong dispatch digest.
- Added versioned bounded preflight result, evidence, human-review, and closure
  models bound to the exact consumed dispatch, case, envelope, grant,
  reservation, request/attempt, and provider identities.
- Wired the Milestone 8 preflight return directly into automatic bounded result
  handling. Case 01 retains 2,852 input tokens and locally derives `$0.0019408`;
  arbitrary raw payloads and exception text are not persisted.
- Added explicit `preflight_result_validated`, `preflight_provider_failed`, and
  `preflight_evidence_reviewed` history operations with exact rerun idempotency,
  conflict rejection, retained-head immutability, and history-first recovery.
- Added the fixed provider-free preflight evidence review action. It resolves
  the current evidence, requires the configured reviewer, canonical decision,
  four explicit confirmations, bounded notes, and a timestamp satisfying the
  frozen 15-minute review deadline.
- Machine-valid evidence remains review-pending and generation-ineligible.
  Only exact approval creates the existing production generation evidence
  binding. Reject/request-changes and provider failures remain consumed,
  terminal, no-retry, and generation-ineligible.
- Preserved the ten-command coordination CLI, Milestone 7 synthetic-evidence
  isolation, permanent closed live authorization, and zero generation provider
  entries. Milestone 9B and Milestone 10 were not begun.
- Validation passed 18 dedicated Milestone 9A tests, the focused live-state and
  result boundary suites, and the full offline experiment suite with 1,251
  passed and 23 environment-dependent skips. Backend passed 148 tests and
  frontend passed 17 tests; TypeScript, production build, read-only Python and
  JSON/TOML parsing, frozen-v4 verification, shell syntax, and scoped diff
  checks also passed. The existing host zsh was mounted read-only into the
  network-disabled image for the exact Milestone 8 launcher suite; all 20
  launcher/process tests passed, including the 9A result-handler handoff.
- Build-vs-adopt remains `defer_adoption`; reassessment remains after committed
  9B/top-level Milestone 9 and before Milestone 10.

## 2026-08-12 — Milestone 9 ownership reconciliation

- Stopped Milestone 9 implementation at the committed reviewed-preflight
  ownership gate; no code or tests were changed.
- Confirmed the canonical frozen-v4 gate requires an explicit human preflight
  evidence review with reviewer identity, approve/reject/request-changes
  decision, four confirmations, bounded notes, exact evidence/history binding,
  and a timely review timestamp. Machine validation cannot substitute for it.
- Recorded a design-only clarification preserving the eighteen-milestone plan:
  Milestone 9A owns preflight result validation/evidence and the canonical
  preflight evidence review; Milestone 9B owns generation result validation and
  provider-phase closure. Top-level Milestone 9 completes only after both
  checkpoints are committed.
- Preserved Milestone 10 ownership of generated-evidence grounding/quality
  review, deletion, and the separate 24-hour deadline.
- Left the digested implementation plan and architecture memo unchanged. The
  architecture already requires preflight evidence review before generation;
  the separate reconciliation record is the authoritative ownership
  clarification.
- Build-vs-adopt remains `defer_adoption`. Mandatory framework reassessment
  remains after both 9A and 9B are committed and before Milestone 10.
- No runtime, test, frozen identity, provider, credential, network, live
  authorization, Milestone 9 implementation, or Milestone 10 change occurred.

## 2026-08-12 — Milestone 8 review corrections

- Preserved the fixed same-shell architecture while adding early sourced-script
  refusal to both operator launchers.
- Rehearsed the unchanged preflight launcher through its unchanged Docker
  wrapper with xtrace enabled. A lower-level test-only process/import seam
  supplied synthetic authorization and provider entry; Docker argv retained
  only the credential variable name, never its value.
- Wired the execution boundary to the canonical OpenAI client factory and
  exercised `max_retries=0`, `trust_env=False`, fixed base URL, frozen timeout,
  and zero construction-time/provider-network calls through the actual boundary.
- Added isolated post-credential checks for aggregate expiry, grant expiry,
  released reservation, and concurrent consumption, each with an exact
  pre-dispatch diagnostic.
- Reconciled the 18-to-2 skip change: the identical full-offline path originally
  lacked zsh and skipped sixteen zsh-only cases plus two Docker-dependent cases.
  The read-only host-zsh mount enables those sixteen; the same two Docker cases
  remain skipped, so coverage was not reduced.
- Corrected validation passed 20 Milestone 8 tests, 222 focused Milestones 1–8
  tests, and 1,254 full-offline tests with the two Docker-dependent skips.
- No live authorization, provider operation, real credential, Milestone 9
  result handling, framework, or frozen-identity change was introduced.

## Architecture A Milestone 8

- Continued from the partial production-closed execution boundary without
  restarting or changing Milestone 7 state.
- Added fixed preflight and generation zsh launchers. Preflight owns the silent
  same-shell credential/process-tree lifecycle; generation remains a pre-prompt
  readiness-only failure while evidence/live authorization are absent.
- Added exact precheck, local client-preparation seam, post-secret revalidation,
  durable dispatch, and immediate synthetic entry ordering. Synthetic seams are
  subclass-only and the fixed wrapper is network-disabled.
- Reused the frozen 5/12-second timeouts and pinned OpenAI 2.45.0 client policy:
  application/transport retries are zero and client construction explicitly
  uses `max_retries=0` with `trust_env=False`.
- Provider results are returned only to a future Milestone 9 interface and are
  not persisted. No live key, provider call, network access, result validation,
  or closure behavior was introduced.
- Validation passed: 13 Milestone 8 tests and 215 focused Milestones 1–8 tests.
  The final full-offline run passed 1,247 tests with 2 skipped.
  Backend passed 148 tests and frontend passed 17 tests;
  TypeScript/production build, Python/JSON/TOML parsing, frozen-foundation
  verification, zsh/sh syntax, and scoped diff checks. Host zsh was mounted
  read-only into the pinned network-disabled image; no dependency was installed.
- Build-vs-adopt remains `defer_adoption`; reassessment remains after committed
  Milestone 9 and before Milestone 10.

## Architecture A Milestone 7

- Began fresh from committed reconciliation `5117e442ad735b4c8409b6da3883a64bcc9aa01b`.
- Added the version-1 generation grant and phase-generic reservation accounting
  with exact Decimal exposure and an independent generation-slot invariant.
- Fixed-time case-01 grant is
  `b8eeaa9ed4fa16037cb2fa6e0ce2588cebe75ec3152e6676e9dc249b3f3c95f8`;
  reservation is `80cea3386b18852029fa814d2022e7642b9cd4e978abf8695d04d148fadfae49`.
- Verified `$0.0019408` exposure, `$0.0280592` case remainder, and `$0.2380592`
  aggregate remainder after corrected zero-dollar preflight consumption.
- Production generation preparation is fail-closed until retained preflight
  evidence/review exists. Synthetic evidence is confined to a test subclass
  whose operations production replay rejects.
- Corrected cost provenance so the 500-token output bound comes from the exact
  frozen-v4 request configuration embedded in the envelope, with no independent
  Milestone 7 policy literal. Fixed grant and reservation digests are unchanged.
- Added replay-valid retained consumed-generation fixtures for 8/0, 7/1, 4/4,
  and 0/8 combinations plus fully rehashed targeting, evidence, authority,
  prior-record, and preflight-history attacks. Production has no generation
  consumption operation and failed preparation is durably side-effect free.
- Added explicit immutable-history retention for complete prior generation
  evidence/grant/reservation records and dispatch-consumed preflight grant and
  reservation identities. Fully reconciled deletion/replacement attacks fail
  on those invariants, and narrow test-only candidate overrides prove exact
  reruns are event-free while conflicting reruns leave state/history unchanged.
- Recorded the human decision `retain_ADR_0005_threat_model`: these retention
  guarantees are relative to the retained authoritative journal head. Total
  internally consistent replacement of earlier history, its suffix, the
  retained head/projection, and all unkeyed hashes is outside scope. Detecting
  that stronger hostile-filesystem attack would require a separately trusted
  anchor and is intentionally deferred, not missing Milestone 7 behavior.
- No public command, provider/SDK/client/network/credential path, generation
  dispatch, Milestone 8, or Milestone 9 behavior was added.
- Corrected validation passed: 17 Milestone 7 tests, 202 focused Milestones
  1–7 tests, 1,218 full offline tests with 18 skipped, 148 backend tests, 17
  frontend tests, TypeScript, temporary-directory frontend build, read-only
  Python/JSON/TOML validation, and frozen foundation verification.
- Build-vs-adopt remains `defer_adoption`; reassessment remains after committed
  Milestone 9 and before Milestone 10.

## Frozen-v4 budget-policy reconciliation

- Completed a design-only lineage review after Milestone 7 stopped on
  `budget_policy_conflict`.
- Found that `$0.03` originated as a hard per-call guardrail, was later refined
  into an inclusive Architecture A per-case ceiling, and was then used under
  the approved interpretation as the token-preflight operation amount.
- Implemented the approved recommendation while retaining `$0.03` per case and
  `$0.24` aggregate: the frozen no-separate-fee preflight now has `$0.00`
  monetary exposure plus one irreversible operation slot.
- Corrected the case-01 synthetic grant digest from historical `4fd481a5...`
  to `757155c6...` and reservation digest from historical `cbc71820...` to
  `8edf28f8...`; aggregate/envelope/frozen identities remain unchanged.
- Updated reservation, release, dispatch, multi-case, crash/replay, and
  irreversible-history proofs so operation-slot safety is independent of
  positive dollar exposure. Case-01 generation headroom `$0.0019408 <= $0.03`
  is verified without implementing generation grants.
- No frozen artifact, provider action, credential/client/network path, or
  public command changed. Milestone 7 remains blocked pending review and
  commit of this focused correction.
- Validation passed: 143 focused grant/budget/dispatch/state tests, 185 focused
  Milestones 1–6 tests, 1,201 full offline tests with 18 skipped, 148 backend
  tests, 17 frontend tests, TypeScript, temporary-directory frontend build,
  Python compilation, JSON/TOML parsing, frozen-v4 verification, and the exact
  ten-command rehearsal.

## Architecture A Milestone 6 dispatch-consumption boundary

- Added exact persisted `provider_dispatch_started` semantics bound to the
  current case, envelope, grant, reservation, and frozen request identities.
- Dispatch start irreversibly converts the full reserved preflight slot and
  `$0.03` exposure to consumed while preserving total committed exposure and
  remaining capacity.
- Added idempotency, release prohibition, semantic attacks, pre/post-history
  crash tests, mixed multi-case accounting, and 8/0, 7/1, 4/4, 0/8 coverage.
- Deliberately added no public command. Milestone 8 owns the same-process
  transition-to-SDK integration; Milestone 6 remains offline and provider-free.
- Passed 29 focused Milestone 6 tests, 184 focused Milestones 1–6 tests, and
  1,200 full offline experiment tests with 18 skipped. Backend (148), frontend
  (17), TypeScript, temporary-directory production build, syntax/data parsing,
  frozen-v4 verification, and the offline public-command rehearsal also pass.
- Preserved `defer_adoption` and the mandatory post-Milestone-9,
  pre-Milestone-10 framework reassessment.

## Architecture A Milestone 5 prospective budget accounting

- Added version-1 exact-cent `Decimal` provider-budget reservations bound to
  the aggregate, derived next case, AI envelope, prepared grant, preflight
  phase, one operation, zero retries, and frozen `$0.03`/`$0.24` ceilings.
- Added exact `provider_budget_reserved` and proven-unused
  `provider_budget_released` history operations, derived per-case/aggregate
  totals, independently reconciled counters, idempotency, and history-first
  crash recovery.
- The fixed case-01 reservation digest is
  `cbc71820cc3d801a09d90dedb0b279882bccae85da8dd482651a64f6eb1a462a`.
  That is the historical pre-reconciliation digest. The corrected current
  digest is `8edf28f8378a97796b197bdcb0d0b5bc64b59fbcb2260d5627e313c87c4daec0`;
  it reserves one preflight slot and `$0.00`, leaving `$0.03` case and `$0.24`
  aggregate monetary capacity.
- Release requires an expired grant plus durable `dispatch_status=not_started`
  proof. No dispatch event, consumption, generation grant, retry, credential,
  provider client/request, or network capability was added.
- Added argument-free `authorize-preflight-budget` and
  `release-preflight-budget`; the public inventory is ten commands.
- Corrected durable collection semantics so each AI case may retain one exact
  grant and reservation. Test-only synthetic sequencing proves released case
  01 coexists with reserved case 02, all eight case records coexist at the
  aggregate boundary, and a fully rehashed ninth-count attack fails. No
  production case-advance or consumption operation was added.
- Preserved `defer_adoption` and the mandatory post-Milestone-9,
  pre-Milestone-10 framework reassessment. `docs/parking-lot.md` remains
  untouched.

## Approved Architecture A build-vs-adopt decision

- Completed a design-only comparison of the committed custom control plane,
  LangGraph/LangSmith, Temporal, Inngest, and the OpenAI Agents SDK using
  official documentation and current pricing accessed 2026-08-11.
- Recorded the human-approved `defer_adoption` disposition. Architecture A
  proceeds unchanged through Milestones 5–9 after this documentation is
  reviewed and committed; Milestone 5 prospective budgets is next and no
  infrastructure PoC is required first.
- Added a mandatory reassessment after committed Milestone 9 and before
  Milestone 10, focused on Temporal, Inngest, and LangGraph. It is not a
  predetermined migration. The OpenAI Agents SDK is not adopted for this
  control-plane problem.
- Kept eligibility, frozen identities, envelopes/grants, budgets, dispatch
  consumption, validators/fallback, evidence policy, scoring, and closure
  explicitly GoTime-owned.
- Identified history storage/replay, crash recovery, durable timers, human
  waits, scheduling, and worker recovery as the strongest later delegation
  candidates.
- Milestone 5 remains paused only until this decision record is reviewed and
  committed. No implementation, dependency, live state, credential, provider,
  staging, or commit action occurred, and `docs/parking-lot.md` was not
  modified.

## Architecture A Milestone 4 offline preflight grants

- Added version-1 offline preflight grant candidates and exact
  `preflight_grant_prepared` history semantics.
- Bound preparation to the derived next AI case, exact envelope/request triple,
  frozen provider metadata, one attempt, zero retries, `$0.03` ceiling, and a
  15-minute window expiring inclusively at `now >= expires_at`.
- Added a production budget port that always denies until Milestone 5; no
  active grant, reservation, authority, or counter mutation is persisted.
- A test-injected approval is ephemeral and retains provider, spending, and
  dispatch authority as false.
- Added replay attacks, boundary/idempotency/recovery tests, constructor
  non-entry, and the eighth offline command `prepare-preflight-grant`.
- Preserved frozen identities/history and did not alter `docs/parking-lot.md`.
- Corrected the grant ceiling source so both fields derive from the canonical
  frozen `PER_CASE_PROVIDER_CEILING_USD`, with no duplicate Milestone 4 literal.
- Added a fully rehashed persisted case-07 grant attack; replay rejects it as
  outside the exact next enveloped AI case.

## Architecture A Milestone 3 AI case envelopes

- Added envelope schema
  `suggest-moving-service-questions-v4-formal-evaluation-ai-case-envelope-v1`,
  version 1, for exactly AI cases 01–06, 09, and 10.
- Bound each case to the aggregate/package, frozen case input, exact
  request/canonical/fingerprint triple, v4 manifest, prompt/schema,
  provider/model/SDK, frozen request configuration, one/one/zero limits, and
  `$0.03` ceiling; all eight unsalted envelope digests are unique.
- Added only `ai_case_envelopes_bound`, an atomic fixed-set operation after
  deterministic cases are terminal. Exact rerun is event-free; substitution,
  replacement, partial, extra, and deterministic-case binding fail closed.
- Added `bind-ai-case-envelopes` as the seventh coordination-only command with
  no arbitrary case or metadata input.
- Added fully rehashed semantic attacks, fresh-process replay, history-first
  projection recovery, and expiration-before/after binding coverage.
- Preserved deterministic 07/08 outcomes, next AI case 01, zero provider
  counters/spend, false provider/spending authority, and inactive phase states.
  No credential, client, network, request, grant, reservation, preflight, or
  generation was introduced. No commit was made.

## Architecture A Milestone 2 deterministic closure

- Added exact `deterministic_case_completed` history semantics for only
  `eval-v4-07` and `eval-v4-08`, changing the intended pending deterministic
  case to an immutable terminal outcome without changing aggregate lifecycle.
- Reused the frozen `bind_case` eligibility boundary. Recorded 07 as empty
  `known(false)` and 08 as empty `not_applicable`, in fixed 07-then-08 order.
- Added `resolve-deterministic-cases` as the sole new public command; callers
  cannot select arbitrary cases and exact reruns append no duplicate events.
- Proved provider-constructor non-entry independently for 07 and 08 and added an
  AI-positive control that stops at constructor entry without credentials,
  clients, network, authorization, or provider execution.
- Added fully rehashed semantic attacks for swapped outcomes, AI targeting,
  case-input changes, counter/budget/lifetime mutation, another-case mutation,
  duplicate completion, conflict, and terminal reopening.
- Proved partial 07-only fresh-process recovery, rerun of only 08, recovery when
  history commits before projection, and expiration between cases without
  reset. After both complete, all AI cases remain untouched and next is 01.
- Preserved all zero provider counters/spend, `spending_authorized=false`, the
  aggregate package identity, frozen artifacts, and closed execution manifest.
  Milestones 4/5/7/11/12 remain unimplemented. No commit was made.

## Architecture A Milestone 1 aggregate coordination

- Added immutable aggregate identity
  `suggest-moving-service-questions-v4-formal-evaluation-live-v1` with exact
  frozen set, v4, runner, budget, ten-case input, eight request-triple, two
  deterministic-empty, lifetime, order, and zero-retry bindings.
- Added locked atomic local state at `.local/evaluations/suggest-moving-service-questions/<aggregate-id>/`
  using SHA-256-chained aggregate history and a replay-validated snapshot.
- Added explicit legal aggregate transitions, seven-day synthetic-clock expiry,
  fresh-process pause/resume, deterministic next-AI-case derivation, initial
  acknowledgement blocking fields, bounded operator/reviewer labels, and
  fail-closed Milestone 12 extension hook.
- Bound frozen 8/8/0, `$0.03` case, and `$0.24` aggregate limits while keeping
  `spending_authorized=false`; all consumed/reserved/spend/retry counters remain
  exactly zero and have no mutation command.
- Added five offline commands: foundation verification, initialization,
  inspect/resume, state verification, and close/abandon. Exact duplicate
  untouched initialization is idempotent; conflicts never reset state.
- Added focused tests for identity reproducibility, membership/order,
  transitions, idempotency, expiry, fresh-process recovery, next case,
  acknowledgement block, zero counters, frozen budget, retained-head rollback,
  malformed state, exact commands, and absence of provider/network/credential
  capability.
- Left deterministic cases 07/08 pending Milestone 2. Prospective budget,
  acknowledgement events, and extension behavior remain deferred to Milestones
  5, 11, and 12. No provider capability, runtime integration, frozen artifact
  change, historical record change, or commit was introduced.
- Corrected the human diff-review findings with a self-contained
  `aggregate_initialized` history, one exact operation-semantic validator,
  canonical UTC/monotonic event checks, ten-terminal-case finalization checks,
  coherent acknowledgement validation, and exact journal count/head
  reconciliation.
- Made aggregate history authoritative and the snapshot recoverable only when
  missing or exactly equal to an earlier replay state. History and projection
  replacements now fsync both file and containing directory; fault injection
  proves recovery after history commit and unchanged state before history
  commit without duplicate events.
- Added correctly rehashed semantic-mutation coverage for wrong operations,
  case state, case order, case-input identity, budget, acknowledgement,
  timestamps, count/head, and premature finalization, plus exact expiration
  boundary and next-case blocking/terminal coverage.
- Closed the remaining lifetime gap: locked load now materializes inclusive
  expiry from `prepared`, `approved`, or `in_progress` before resume can start
  coordination, and replay rejects `aggregate_started` at/after `expires_at`.
  Synthetic clocks prove start succeeds one second before expiry and fails
  closed with no next case exactly at or after expiry.
- Expanded independent correctly rehashed attacks across all six frozen budget
  fields, extra membership, deterministic-case substitution, AI provider
  fingerprint mutation, premature finalization, and unauthorized expiration
  extension. All fail semantically without adding later-milestone behavior.

## Frozen-v4 formal evaluation runner

- Added offline runner identity
  `suggest-moving-service-questions-v4-formal-evaluation-runner-v1` without
  changing the frozen evaluation set, v4 artifacts, validator, or fallback.
- Implemented exact 8+2 eligibility, case-specific identity verification,
  synthetic preflight and generation adapters, same-request-object reuse,
  one-attempt/no-replacement enforcement, cross-case preflight isolation, and
  aggregate budget checks.
- Added bounded case outcomes, separate transport/content failure semantics,
  mandatory synthetic grounding review and evidence deletion, and deterministic
  final reports implementing the approved hard, quality, and empty-case gates.
- Rehearsed nominal graduation, hard-gate failure, quality-gate insufficiency,
  and provider failure entirely offline. Added a fixed eleven-command,
  network-disabled public surface with an explicit deletion command.
- Corrected the human-review findings with a durable atomic `.local` ledger,
  cross-process attempt consumption, complete contradictory-empty hard gates,
  evidence-bound review, explicit idempotent deletion, and ledger-only report
  finalization with deterministic provenance.
- Replaced snapshot-only durability with a separate sequence-numbered,
  SHA-256-chained transition journal and a replay-validated ledger projection.
  Added exact bounded preflight and closure artifacts, field-for-field review
  reconciliation, and persisted deletion transactions recoverable after every
  meaningful interruption boundary without retaining response content.
- Strengthened replay with operation-specific transition semantics, integrity-checked
  state-changing recovery, full committed deletion-transaction validation, and
  complete lifecycle closure bindings. Added fully rehashed semantic mutation,
  preflight-forgery, and post-recovery deletion-idempotency coverage.
- Added journal-bound recovery-basis artifacts with uniquely derived projection,
  transaction, or combined repair classification; completed fully rehashed
  counter, automated-rejection, and provider-failure lifecycle proof matrices.
- Bound exact recovery pre-state before mutation with paired
  `recovery_prepared`/`recovery_completed` transitions, including resumable
  prepared recovery and before-state projection/transaction/artifact bindings.
- Clarified that the offline hash chain detects corruption and inconsistent or
  semantically invalid local mutations relative to its retained journal head;
  total consistent rewrite without an external trust anchor is a non-goal.
- Clarified canonical-content transaction validation (formatting-equivalent JSON
  is accepted) and documented the full `prepared` → `removal_prepared` →
  `evidence_removed` → `committed` deletion lifecycle.
- Bound automated-rejection fallback identity into the bounded generation audit
  so closure validation cannot accept a rehashed outcome that erases fallback.
- Recommended one future reviewed package with eight exact single-use
  sub-authorities, subject to a separate live design/review milestone.
- No credential, OpenAI client, provider operation, live preflight/generation,
  authorization, spending authority, or runtime integration was introduced.

## Frozen-v4 preflight-gate offline rebind

- Chose fresh run series `moving-service-stage-b-v4-pilot-20260808`, sequence
  1, fixture `storage_unknown`, independently of all v2/v3 history.
- Added an inactive preflight-only candidate and manifest bound to the exact
  frozen-v4 manifest, request-identity artifact, request/canonical digests, and
  provider fingerprint.
- Preserved credential-free verification before lookup and reuse of the exact
  verified prepared request by the transport.
- Rebound the fixed 12-command operator, same-shell, evidence-review, closure,
  cleanup, and non-authoritative generation-binding-preview workflow.
- Passed the exact-command network-disabled rehearsal with 4,242 synthetic
  tokens, synthetic cost `$0.0024242`, one preflight, zero generations, zero
  retries, permanent closure, and second-use rejection.
- Frozen v1/v2/v3/v4, validator, fallback, and historical v2/v3 records remain
  unchanged. No live v4 preflight, credential access, client, provider call,
  generation authority, or generation request occurred.
- Corrected the human-review finding by replacing lifecycle-file presence
  checks with exact fixed-path semantic and SHA-256 validation across the
  authorization, activation, final transaction, audit, consumption, closure,
  evidence, and permanently closed execution state. Review and binding preview
  now validate the chain independently.
- Strengthened source semantics against the fixed candidate: complete rendered
  scope, activation-review and active-manifest bindings, committed-then-closed
  transaction fields, credential/client success, closed-manifest identity, and
  whole-second UTC ordering. The positive fixture now invokes the real lifecycle
  functions; 48 semantic mutations recompute every downstream digest and still
  fail closed.

## Prompt-v4 implementation and offline freeze

- Implemented only the approved minimal v4 prompt delta after the single v3
  modality rejection; the unavailable historical wording was not guessed.
- Added literal-only v4 request/response identities and a title-only strict
  provider-schema adaptation.
- Added deterministic grounding-source rejection for the exact closed trigger
  set before provider-request construction; grounding remains byte-exact.
- Frozen request/response fixtures, policy cases, grounding cases, schema diff,
  request configuration, adaptation evidence, and authoritative digests.
- Preserved the exact v2 prose-validator bytes, fallback v2, frozen v1/v2/v3,
  historical records, and permanent closed state.
- Confirmed the generation-gate architecture needs only thin v4 rebinding, but
  a fresh v4 preflight is required because request identity changes.
- No credential, client, preflight, generation, network request, or live v4
  authorization occurred.

## Frozen-v3 live prose-failure postmortem

- Recorded that the single live frozen-v3 generation passed structural and
  semantic validation, failed only `storage_modality_overstatement`, selected
  fallback v2, created no validated response evidence, received no grounding
  review or retry, and restored permanent closure.
- Preserved the audit, closure, consumption, preflight, and frozen artifacts as
  immutable history. The rejected prose remains unavailable and was not
  reconstructed; its exact lexical cause is unknowable.
- Added observational rejected-prose diagnostics containing only rule, field,
  original-field offsets, closed canonical trigger, and occurrence count.
- Proved diagnostics do not change validator decisions or code order and do
  not retain complete fields, surrounding prose, raw provider output, or
  credentials.
- Recommended a separate narrow prompt-v4 design review while retaining the
  current modality validator unchanged. No provider operation occurred.

## Frozen-v3 generation-candidate resolution

- Bound a separate inactive resolved generation candidate to the exact approved
  live v3 sequence-1 preflight evidence and review without changing either
  historical record.
- Recorded 2,542 input tokens, conservative maximum cost `$0.0018168`, exact
  request/canonical/provider bindings, and the non-writing binding preview.
- Preserved the original unresolved candidate as historical design input.
- Rehearsed all five generation scenarios through the exact public commands
  with networking disabled, zero generation preflights, one fake generation
  per scenario, grounding review/deletion, closure, and non-reuse.
- Generation remains unauthorized; no live generation timestamp, credential,
  client, or provider request was created.

## Frozen-v3 sequence-1 preflight workflow

- Started a distinct v3 run series rather than rewriting or extending consumed
  v2 history: `moving-service-stage-b-v3-pilot-20260807`, sequence 1.
- Added an inactive preflight-only candidate bound to the exact frozen-v3
  request, canonical attempt, provider fingerprint, limits, and closed state.
- Added fixed render, install, review, plan, activation, verification,
  same-shell preflight, evidence review, generation-binding preview, closure,
  and expired-review cleanup commands.
- The network-disabled exact-command rehearsal produced one fake 2,300-token
  preflight, zero generation calls, immediate approved evidence review,
  permanent closure, and second-use rejection.
- The generation-binding operation is dry-run-only and non-authoritative; live
  generation remains blocked pending real v3 evidence and later candidate
  versioning.
- No real credential, client, provider call, authorization, or timestamp
  package was created.

## Frozen-v3 sequence-4 generation-gate rebinding

- Verified every frozen-v3 digest before constructing the v3 request.
- Determined `fresh_v3_preflight_required`: prompt v3 changes the deterministic
  request, canonical attempt, and provider fingerprint, and its exact provider
  token count is not knowable offline.
- Added a distinct inactive v3 generation candidate with unresolved fresh-v3
  preflight placeholders; live rendering fails closed outside synthetic state.
- Versioned the fixed sequence-4 generation lifecycle, same-shell operator,
  grounding review, evidence deletion, closure, command inventory, and runbook
  without changing the reviewed architecture.
- Rehearsed all 11 public commands under Docker networking disabled across
  compliant, historical prose rejection, structural failure, semantic failure,
  and prompt-policy stress scenarios. Each used one fake generation, zero
  preflights, restored permanent closure, and rejected reuse.
- Preserved frozen v1/v2/v3 artifacts, historical sequence records, fallback
  v2, and the existing semantic/prose validators. No credential or provider
  operation occurred.

## Prompt-v3 freezing milestone

- Promoted the approved draft into a complete frozen experimental package with
  prompt `moving-service-questions-prompt-v3` and schema
  `moving-service-questions-schema-v3`.
- Added literal-only v3 request/response models, a machine-readable v2/v3
  schema-diff proof, title-only provider-schema adaptation, field-by-field
  review, frozen fixtures, synthetic language cases, and authoritative digests.
- Preserved the exact approved modality, service-selection,
  `why_it_matters`, grounding exception, and no-positive-example decisions.
- Kept all five v2 prose validators and `moving-service-fallback-v2`
  unchanged.
- Added drift, mixed-identity, semantic-invariant, and runtime-isolation tests.
- No live configuration, authorization, credential access, model call, or
  FastAPI/frontend reachability was added.

## Sequence-4 live prose-failure diagnostic

- Preserved the live audit and closure as immutable evidence; the raw rejected
  response remains unavailable and was not reconstructed.
- Added isolated matrices for storage-modality and service-selection lexical
  behavior without changing the validators or frozen fixtures.
- Recommended a narrow prompt v3 and separately reviewed bounded diagnostic
  metadata using canonical triggers rather than retained response text.
- No credential, client, preflight, generation, or provider operation occurred.

## Prompt-v3 drafting milestone

- Added an isolated, non-executable prompt-v3 delta for human review.
- Preserved the response shape, curated knowledge, grounding equality,
  confirmation requirement, fallback, and all five existing prose validators.
- Proposed only literal prompt/schema v3 identity changes for a later
  implementation because the existing v2 classes bind both literals.
- Added 28 synthetic language cases and prompt/validator consistency checks;
  positive examples remain excluded and generation remains unauthorized.

## Sequence-4 generation-gate milestone

- Corrected the final-review findings: exact generation request verification
  now precedes credential inspection, and rehearsal invokes every public
  command rather than substituting lifecycle functions.
- Added machine-checked command coverage and retained network-disabled fake
  generation for compliant, prose-rejected, structural-failure, and independent
  semantic-failure scenarios.
- Added scenario-specific assertions over audits, evidence, reviews, deletion,
  fallback identity, closure, and non-reuse; every printed rehearsal success
  field now has a checked backing assertion.
- Verified approved sequence-4 preflight evidence and review exact bytes.
- Added an inactive generation-only candidate bound to those digests.
- Added fixed `004-storage_unknown-generation` paths and pinned commands.
- Reused frozen request, layered validation, stable prose checks, fallback,
  grounding review, evidence deletion, and permanent closure conventions.
- Passed the full network-disabled generation rehearsal and repository suites.
- No credential or provider operation occurred during this offline milestone.

## Session 0 -- Workstation

### Completed

- Built WSL2 workstation
- Configured Git
- Configured GitHub SSH
- Installed Oh My Zsh
- Installed Starship
- Created workstation repository

### Lessons

- Inspect before changing.
- Document decisions.
- Keep configuration intentional.

I think we've discovered our project documentation hierarchy

This is the structure I'd like us to use consistently:

README.md
    ↓
What is this project?

ADR
    ↓
Why did we make major decisions?

Architecture docs
    ↓
How is the project organized?

SESSION_NOTES.md
    ↓
What happened over time?

NEXT_SESSION.md
    ↓
What are we doing next?

TODO.md
    ↓
What remains to be done?

---

## Session 1
Here's the workflow I'd like us to adopt
+ Review NEXT_SESSION.md (our current objective).
+ Review TODO.md (anything still outstanding).
+ Make any adjustments based on what we've learned.
+ Execute the plan.
+ Update SESSION_NOTES.md.
+ Commit.

Here's how I'd like our first coding session to go

Not "today we're going to scaffold React."

Instead:

Today we're going to prove that the architecture works.

By the end of the session, I want us to have:

A gotime repository with a clean structure.
React (TypeScript) running.
FastAPI running.
Docker Compose starting both.
The React frontend making an HTTP call to FastAPI.
The browser displaying "Hello, GoTime!" from the backend.
Everything committed.

That will be our Version 0.0.1.

It's tiny, but it's real.
...

---

## Session 2 -- Application Bootstrap

### Completed

- Corrected the `make session` command to use `scripts/begin.sh`.
- Added a Vite, React, and TypeScript frontend.
- Added a FastAPI backend with `GET /api/health`, returning `{ "status": "ok" }`.
- Added one root `docker-compose.yml` for the frontend and backend.
- Configured the frontend to call `/api/health` and display the backend status.
- Verified the frontend production build and backend Python syntax.

### Pending

- Docker Compose runtime verification could not run on this workstation because
  Docker is not installed.
- Make the initial commit after that verification.

---

## Session 3 -- Version 0.0.2 Concept Screen

### Completed

- Reframed the current milestone around proving GoTime's central question:
  "What should I do next?"
- Replaced the frontend health-check placeholder with a single static screen.
- Presented a hard-coded relocation goal, one recommended next step, and two
  upcoming steps.
- Explicitly deferred persistence, authentication, editing, and task-management
  workflows.
- Kept the FastAPI health endpoint and Docker Compose foundation in place for
  later iterations.

### Next

- Put the screen in front of its intended user and learn whether the recommended
  next step feels immediately useful.

---

## Session 4 -- Frontend Development Workflow

### Completed

- Adopted React-Bootstrap, Bootstrap utilities, and SCSS as frontend
  conventions, with the decision recorded in ADR-0003.
- Refactored the concept screen to use React-Bootstrap components and
  project-specific SCSS modules for shared variables and mixins.
- Configured Docker Compose for frontend live reload using a source bind mount,
  a container-managed `node_modules` volume, and file-watch polling.
- Verified the running frontend container uses the source bind mount and runs
  Vite in development mode.

### Next

- Define GoTime's domain language—Goal, Project, Task, Milestone, and
  Dependency—before designing a database or additional infrastructure.

## Session 5 -- 'Whiteboarding', or how I went from a todo app to a reasoning engine
(this is copied straight from CGPT's response to my attempt to explain what I wanted to app to do for us)

I think we need to define the engine's responsibilities
If I were writing them today, they'd be:
+ Understand -- What is the user trying to accomplish?
+ Model -- Build a representation of the plan.
+ Predict -- Estimate durations, dependencies, and risks.
+ Monitor -- Watch for changes.
+ Adapt -- Recalculate when something changes.
+ Recommend -- Answer: What should I do next?
+ Explain -- Perhaps the most important responsibility. Never just say: "Do this." Always answer: Why?

This leads to an important realization

I don't think "AI" belongs everywhere.

I think AI belongs primarily in these places:

+ building an initial plan,
+ estimating timelines,
+ identifying missing work,
+ explaining recommendations,
+ summarizing progress,
+ answering questions.

Everything else should be deterministic. For example: Task assignments. Permissions. Notes. Attachments. Those don't need AI.

If we can define how GoTime reasons, then every subsequent decision becomes easier:

+ The domain model exists to support the reasoning engine.
+ The database exists to persist the domain model.
+ The UI exists to expose the reasoning engine.
+ AI exists to enhance the reasoning engine.

I think GoTime has three kinds of knowledge.

1. Facts
Things the user tells us.

Examples:
+ Move date
+ Family members
+ Budget
+ House under contract

2. Rules
Things GoTime knows.

Examples:
+ Movers should usually be booked 8–12 weeks in advance.
+ Utility transfers should occur shortly before occupancy.
+ Vehicle registration deadlines vary by state.

3. Inference
What GoTime concludes.

Examples:
You should schedule movers this week.
or
This task is blocked because closing has not occurred.

That separation is powerful because it means we can improve the reasoning engine without changing the user's data.

We decided to design the reasoning engine by role-playing real planning conversations rather than starting with a database schema. The conversation itself will be treated as a source of requirements for the engine.

Session 6 -- The API acted as a project mgr and asked me questions about our move. It resulted in some changed ideas about how this app will behave

Here's the complete list of ideas I think we generated today
New concepts
Strategic Reasoning
Operational Reasoning
Decision Filters
Decision Readiness
Backward Planning
Sequencing Engine
Continuous Re-evaluation
Recommendation Transparency
Conversation Engine
Plan Invalidation
Waiting for Information
Refined concepts
Constraints → Decision Filters
Tasks → Outputs of reasoning
Projects → Vehicles toward goals
Recommendations → Explained recommendations
Risks → Inputs into reasoning rather than standalone objects
Important distinctions

### Action
> Something someone does.

### Decision
>Something someone chooses.

### Event
>Something that happens.

Those three affect sequencing differently.

### Waiting vs Blocked
Another subtle distinction.

Blocked: Can't continue because prerequisite work isn't complete.

Waiting: Can't continue because external information hasn't arrived.

Very different reasoning.

### Assumptions

These became first-class citizens.

Examples:
+ house sells
+ spouse finds employment
+ destination remains unchanged

The engine should know these are assumptions rather than facts.

### Plan Invalidation
We distinguished ordinary risks from events that should cause the engine to stop optimizing the current plan and instead reconsider it from the ground up.

### Success Factors
I'm actually least confident about this one.

The examples you gave—your spouse finding meaningful work and access to high-quality healthcare—could fit under "Definition of Success" instead of becoming a separate concept.

I'd hold off on creating a new category until we see whether it recurs in other domains.

---

## Session 7 -- First In-Memory Reasoning Loop

### Completed

- Added minimal in-memory models for Goal, SuccessCriterion, Constraint,
  Preference, Decision, Assumption, and Recommendation.
- Represented one hard-coded Tennessee-to-Northern-California relocation
  scenario.
- Added one deterministic, relocation-specific rule that recommends clarifying
  spouse employment requirements before selecting a final target location.
- Included why, why now, relevant dependencies, blocked downstream work, and
  the related employment Assumption in the Recommendation.
- Exposed the primary Recommendation at
  `GET /api/recommendations/primary`.
- Added focused reasoning and endpoint tests.

### Modeling Decisions

- Explanation remains embedded in Recommendation, as anticipated by the domain
  model.
- Decision readiness and Assumption status use only the states needed by this
  scenario.
- Downstream work and dependencies remain descriptive values. No generic rule
  engine, dependency graph, persistence layer, or Action model was introduced.
- No ADR was needed because these choices follow the existing MVP and domain
  documentation.

### Verification

- Backend tests: 3 passed.
- Python compilation: passed.
- Whitespace validation with `git diff --check`: passed.
- Docker verification passed: `GET /api/health` returned `{"status":"ok"}` and
  `GET /api/recommendations/primary` returned the expected updated contract.

### Next

- Review the first recommendation payload and decide whether it is the right
  contract for the first frontend-backed reasoning experience.

---

## Session 8 -- State Change and Re-Reasoning

### Completed

- Added the minimum relocation-specific state needed to distinguish unclear
  from clarified spouse employment requirements.
- Derived the clarified Goal snapshot from the original with `model_copy`
  without mutating the original snapshot.
- Preserved the original Recommendation for unclear requirements.
- Added a second deterministic Recommendation to evaluate candidate locations
  against clarified employment requirements.
- Preserved the unconfirmed suitable-employment Assumption and the structured
  relationship to the `target-location` Decision in both Recommendations.
- Added the temporary `employment_requirements` query parameter; omitted and
  `unclear` values are equivalent, while `clarified` selects the second proof
  snapshot.
- Added explained HTTP 422 responses for unsupported query values and
  recognized states without an applicable reasoning path.

### Modeling Decisions

- `EmploymentRequirementsStatus` and
  `Goal.relocation_employment_requirements_status` are relocation-specific
  scenario state for this proof, not finalized universal Goal fields.
- A broader CurrentState model, generic fact system, persistence layer, state
  manager, rule engine, and dependency graph remain deferred.
- Clarifying requirements does not validate the separate Assumption that
  suitable employment exists in a viable candidate region.
- No ADR was needed because the temporary query contract and scenario state do
  not establish durable production architecture.

### Verification

- Backend tests: 10 passed.
- Python compilation: passed.
- Whitespace validation with `git diff --check`: passed.
- Docker Compose rebuilt successfully; the backend was healthy and the
  frontend started.
- Docker endpoint checks passed for health, default, unclear, clarified, and
  unsupported-query behavior.

### Next

- Review the two-state reasoning flow and API proof before committing.

---

## Session 9 -- Frontend Recommendation Integration

### Completed

- Replaced the static recommendation and upcoming-step content with the live
  primary Recommendation returned by the backend.
- Added endpoint-specific TypeScript models and one focused fetch function.
- Displayed what is recommended, why, why now, relevant dependencies, blocked
  downstream work, and the related employment Assumption.
- Added a visually secondary temporary scenario control for unclear and
  clarified spouse employment requirements.
- Added loading and error states.
- Prevented obsolete requests from replacing the result for the latest selected
  state through request cancellation and a current-request guard.
- Kept `related_decision_id` and other implementation identifiers out of the
  rendered interface.
- Added focused frontend component tests and development-only test tooling.

### Modeling and UI Boundaries

- The scenario selector demonstrates state change; it is not a proposed
  production editing workflow and does not persist anything.
- Clarified employment requirements remain distinct from the unconfirmed
  Assumption that suitable employment exists.
- No routing, global state manager, forms infrastructure, generalized API
  client, or backend change was introduced.
- No ADR was needed because the integration follows the established frontend
  conventions and uses a temporary proof control.

### Verification

- Frontend tests: 5 passed.
- Frontend production build: passed.
- Backend tests: 10 passed.
- Backend Python compilation: passed.
- Docker Compose rebuild passed; the backend was healthy and the frontend was
  running.
- The frontend proxy returned the expected unclear and clarified contracts.
- Whitespace validation with `git diff --check`: passed.

### Next

- Review the live experience with its intended user before selecting the next
  milestone.

---

## Session 10 -- One Concrete Employment Requirement

### Completed

- Replaced the temporary clarified/unclear scenario state with one authoritative
  optional `acceptable_work_arrangement` value on the in-memory Goal snapshot.
- Added supported remote, hybrid, on-site, and flexible work arrangements.
- Replaced the confirmation-only frontend interaction with a focused select and
  submit action attached to the initial Recommendation.
- Kept draft selection local so re-reasoning begins only when the user submits.
- Added deterministic, value-specific reasoning about how each arrangement
  affects candidate-location evaluation.
- Replaced the temporary `employment_requirements` query with the optional
  `work_arrangement` query and rejected unexpected query parameters.
- Preserved loading, cancellation, stale-response, and error behavior.

### Modeling and Product Boundaries

- No work-arrangement value means the requirement remains unclear and preserves
  the original Recommendation.
- A submitted value is the sole evidence that this requirement is clarified;
  no separate status can contradict it.
- Work arrangement is only one part of employment suitability.
- Suitable employment in a viable candidate region remains an unconfirmed
  Assumption for every work arrangement.
- State remains local and in memory. No persistence or general state system was
  introduced.
- Candidate locations are not yet scored or compared.

### Verification

- Frontend tests: 5 passed.
- Frontend production build: passed.
- Backend tests: 17 passed.
- Backend Python compilation: passed.
- Docker Compose rebuilt successfully; backend health and frontend startup
  passed.
- Frontend proxy checks passed for the default request and all four supported
  work arrangements.
- Unsupported work arrangements, the retired parameter, and arbitrary unknown
  query parameters returned HTTP 422.
- Whitespace validation with `git diff --check`: passed.

### Next

- Capture one acceptable commute limit for the hybrid or on-site path and use
  it as another concrete input to candidate-location reasoning.

---

## Session 11 -- One Concrete Commute Requirement

### Completed

- Added `acceptable_commute_minutes` as a maximum acceptable one-way commute
  for hybrid and on-site arrangements.
- Treated the submitted positive whole-number value as a hard user-provided
  evaluation boundary, not an observed or calculated commute.
- Changed hybrid and on-site reasoning without a limit to recommend defining
  the longest workable one-way commute.
- Changed reasoning with a limit to recommend evaluating candidate locations
  against both the arrangement and the submitted boundary.
- Added a focused commute-limit input after a successful hybrid or on-site
  work-arrangement submission.
- Kept the draft value local and re-reasoned only after explicit submission.
- Added endpoint validation for zero, negative, decimal, invalid, and
  arrangement-incompatible values.
- Preserved loading, cancellation, stale-response, and error behavior.

### Modeling and Product Boundaries

- The commute limit is narrowly scoped relocation state and does not expand the
  generic `Constraint` model.
- A likely workplace location and credible travel-time evidence are still
  required before a candidate can be evaluated. Hybrid frequency also remains
  unknown.
- The engine does not calculate travel time or claim that a candidate location
  passes or fails.
- Suitable employment remains an unconfirmed Assumption.
- State remains local and in memory. No persistence, location scoring, mapping
  integration, or generalized state infrastructure was introduced.

### Verification

- Frontend tests: 6 passed.
- Frontend production build: passed.
- Backend tests: 28 passed.
- Backend Python compilation: passed.
- Docker Compose rebuilt successfully; backend health and frontend startup
  passed.
- Supported default, arrangement-only, hybrid-with-limit, and
  on-site-with-limit contracts returned HTTP 200.
- Invalid and contradictory commute-limit contracts returned HTTP 422.
- Whitespace validation with `git diff --check`: passed.

### Next

- Capture one likely workplace area for hybrid or on-site work and use it to
  recommend gathering credible travel-time evidence without calculating routes
  or scoring candidate locations.

---

## Session 12 -- One Likely Workplace Area

### Completed

- Added `likely_workplace_area` as trimmed, bounded free-form planning context
  on the in-memory relocation Goal snapshot.
- Accepted the value only for hybrid or on-site work with a valid maximum
  one-way commute.
- Rejected blank, whitespace-only, over-length, and prerequisite-incompatible
  values.
- Added a focused workplace-area input after a successful commute-limit
  submission.
- Kept draft input local and submitted only an explicitly confirmed, trimmed
  value.
- Advanced the Recommendation to gathering credible one-way travel-time
  evidence between candidate locations and the likely workplace area.
- Preserved loading, cancellation, stale-response, and error behavior.

### Modeling and Product Boundaries

- The workplace area is opaque user-provided text. It may describe a city,
  neighborhood, employment corridor, or approximate region.
- It is not a confirmed employer location, verified workplace, normalized city,
  geocoded place, or generic location entity.
- The engine does not calculate routes, use travel-time data, or score
  candidate locations.
- Traffic conditions and travel mode remain unresolved. Hybrid frequency also
  remains unresolved for hybrid work.
- Suitable employment remains an unconfirmed Assumption.
- State remains local and in memory. No persistence, search, autocomplete,
  mapping, or generalized state infrastructure was introduced.

### Verification

- Frontend tests: 7 passed.
- Frontend production build: passed.
- Backend tests: 39 passed.
- Backend Python compilation: passed.
- Docker Compose rebuilt successfully; backend health and frontend startup
  passed.
- Supported hybrid and on-site workplace-area contracts returned HTTP 200.
- Blank, over-length, contradictory, and unexpected query contracts returned
  HTTP 422.
- Whitespace validation with `git diff --check`: passed.

### Next

- Capture one intended commute travel mode and use it to make the manual
  evidence-gathering Recommendation more specific without calculating routes
  or scoring candidate locations.

---

## Session 13 -- Intended Commute Travel Mode

### Completed

- Added `intended_commute_travel_mode` as user-provided relocation planning
  context with `drive`, `public_transit`, and `either` values.
- Defined `either` to mean that driving and public transit are both acceptable
  and evidence should be gathered for both, not that the mode is unknown.
- Accepted a mode only after hybrid or on-site work, a maximum one-way commute,
  and a likely workplace area were supplied.
- Added deterministic progression from gathering a workplace area, to
  clarifying travel mode, to gathering mode-specific manual evidence.
- Added a focused travel-mode select after successful workplace-area
  submission.
- Kept draft selection local and re-reasoned only after explicit submission.
- Preserved loading, cancellation, stale-response, and error behavior.

### Modeling and Product Boundaries

- Travel mode represents intended planning context, not observed travel
  behavior.
- Driving recommendations retain unresolved typical traffic conditions.
- Public-transit recommendations retain unresolved schedules, transfers, and
  station access.
- Hybrid frequency remains unresolved for hybrid work.
- No route, travel time, workplace, candidate viability, or suitable
  employment has been verified.
- State remains local and in memory. No persistence, route or transit APIs,
  candidate scoring, generic evidence model, or AI call was introduced.

### Verification

- Frontend tests: 8 passed.
- Frontend production build: passed.
- Backend tests: 57 passed.
- Backend Python compilation: passed.
- Docker Compose rebuilt successfully; backend health and frontend startup
  passed.
- All three travel modes passed through the frontend proxy for hybrid and
  on-site work.
- Unsupported, contradictory, and unexpected query contracts returned HTTP
  422.
- Whitespace validation with `git diff --check`: passed.

### Next

- Review what the deterministic prototype already proves and decide where
  AI-assisted interpretation or suggestion would add genuine value while
  remaining grounded, transparent, and testable.
- Treat hybrid commute frequency as a possible future deterministic input, not
  the committed next implementation milestone.

---

## Session 14 -- Fake Moving-Service Question Adapter

### Completed

- Added a capability-specific fake adapter for
  `suggest_moving_service_questions`.
- Constructed a bounded AI-shaped request from narrow trusted experiment
  fixtures rather than the production `Goal`.
- Added a small storage-question knowledge fixture explicitly labeled as
  unsuitable for real-model evaluation.
- Added deterministic complete-response validation for versions, counts,
  unique IDs, unique categories, normalized question text, open Decision
  references, supplied knowledge references, approved missing information,
  answer types, confirmation requirements, output bounds, and forbidden extra
  fields.
- Added a fixed-priority deterministic fallback for the five approved
  moving-service information categories.
- Added valid, zero-suggestion, invalid, unavailable, timeout,
  budget-unavailable, and AI-disabled fixture paths.
- Added a temporary fixture-only experiment endpoint with strict query
  validation.
- Added an explicitly triggered secondary frontend experiment beneath the
  primary Recommendation.
- Added useful fallback presentation, grounding disclosure, local dismissal,
  and local-only boolean confirmation.
- Added bounded observability with exact source and fallback values and a
  `$0.00` fake-adapter cost.

### Product and Architecture Boundaries

- No real model, AI SDK, credential, live research, vector infrastructure,
  persistence, or external telemetry was added.
- No generic AI abstraction or cross-domain capability framework was added.
- Moving-service fields were not added to the current `Goal`.
- The suggestion and its answer cannot update trusted state or trigger
  re-reasoning.
- Invalid responses are rejected completely; valid-looking suggestions from
  an invalid response are not retained.
- The temporary scenario query selects a trusted fixture only and is not a
  proposed production API.
- User-facing copy says "Experimental suggestion" or "Suggested from GoTime's
  planning guide" rather than exposing adapter mechanics.
- The fixture validates the contract, not AI product value or moving-industry
  knowledge quality.

### Verification

- Frontend tests: 17 passed.
- Frontend production build: passed.
- Backend tests: 87 passed.
- Backend Python compilation: passed.
- Docker Compose rebuilt successfully; backend health and frontend startup
  passed.
- All seven experiment fixture paths returned HTTP 200 through the frontend
  proxy.
- Unsupported fixtures and unexpected parameters returned HTTP 422.

### Next

- Review the fake-adapter boundary and decide whether to approve the contract.
- Reconcile the older draft `v1` JSON artifacts with the approved contract in a
  separate bounded slice before considering real-model evaluation.
- Do not introduce a real model until curated statements have approved sources
  and the fake-adapter contract has passed review.

---

## Session 15 -- V1 Moving-Service Artifact Reconciliation

### Completed

- Replaced the legacy nested-claim knowledge artifact with the exact runtime
  storage implementation fixture.
- Replaced the legacy fallback order, names, and claim references with the
  exact runtime fallback questions and missing-information contracts.
- Replaced legacy scenarios with `storage_unknown`, `complete`, and a
  contract-only multiple-gap fixture.
- Added valid, zero-suggestion, and deliberately invalid response fixtures for
  runtime schema and semantic validation.
- Replaced legacy expected themes with exact execution, fallback, and bounded
  observability expectations.
- Added separate manifest readiness fields and explicit ineligibility reasons.
- Rewrote the artifact evaluator to use runtime Pydantic models, request
  construction, response validation, fallback selection, and orchestration.
- Added backend anti-drift tests covering artifact compatibility and production
  independence from documentation files.
- Corrected experiment-document differences involving runtime state statuses,
  knowledge scope, duplicate detection, and real-model knowledge readiness.

### Boundaries

- The artifact package is contract-test eligible.
- The artifact package is not real-model-evaluation eligible.
- No moving-industry source research was performed.
- The storage statement remains an implementation fixture without an approved
  grounding source.
- Production code does not load the artifacts from `docs/`.
- No real model, SDK, credential, live research, vector infrastructure,
  persistence, provider abstraction, or external telemetry was introduced.

### Verification

- Artifact compatibility tests: 12 passed.
- Backend tests: 89 passed.
- Frontend tests: 17 passed.
- Frontend production build: passed.
- Backend Python compilation: passed.
- Docker Compose rebuilt successfully; backend health and frontend startup
  passed.
- All seven fake-adapter experiment paths returned HTTP 200 through the
  frontend proxy.
- Whitespace validation with `git diff --check`: passed.

### Next

- Review and approve the reconciled artifact package.
- If approved, plan a separate curated-knowledge review slice before any
  real-model evaluation work.

---

## Session 16 -- Reviewed Storage-Question Knowledge

### Completed

- Replaced the implementation-only storage statement with one bounded,
  source-backed statement for interstate household-goods movers.
- Reviewed the FMCSA handbook *Your Rights and Responsibilities When You Move*
  and recorded its supporting sections, publication metadata, limitations,
  freshness policy, and corroborating federal regulation.
- Added a stable approved knowledge ID and incremented the knowledge item and
  fixture versions.
- Updated runtime data, artifact scenarios, response fixtures, fallback
  references, observability expectations, and anti-drift tests consistently.
- Added conservative request-size enforcement against the 3,000-token
  experiment ceiling.
- Marked the package eligible only for a controlled real-model evaluation of
  the `storage_unknown` question suggestion.

### Boundaries

- Readiness does not mean production approval, complete moving-service
  knowledge, or readiness for service-model comparison.
- The reviewed item does not apply to portable containers, rental trucks,
  brokers, providers, pricing, availability, rankings, or recommendations.
- The deterministic fallback selection and trusted-state behavior are
  unchanged.
- Production remains independent from files under `docs/`.
- No real model, SDK, credential, live application research, persistence,
  vector infrastructure, or external telemetry was introduced.

### Verification

- Artifact compatibility tests: 12 passed.
- Backend tests: 90 passed.
- Frontend tests: 17 passed.
- Frontend production build: passed.
- Backend Python compilation: passed.
- The serialized `storage_unknown` request is 2,610 bytes, a conservative
  upper bound below the 3,000-token experiment ceiling.
- Docker Compose rebuilt successfully; backend health, frontend startup, and
  all seven experiment paths through the frontend proxy passed.

### Next

- Review and commit the knowledge-curation milestone.
- Only after approval, design a separate real-model adapter and controlled
  evaluation run against the frozen deterministic fallback.

---

## Sequence-3 single-shell preflight reconciliation

- Preserved sequence-1 and sequence-2 historical records; sequence 2 closed
  before credential lookup and made no provider request.
- Added a distinct inactive sequence-3 preflight candidate and manifest.
- Added fixed `003-storage_unknown` render, review, activation, preflight, and
  closure tooling in the pinned evaluation environment.
- Added one human-run zsh operator command that prompts, exports, launches,
  closes, and unsets within one process tree.
- Rehearsed the exact public workflow with a synthetic credential, fake client,
  and networking disabled; one fake preflight and zero generation calls ran,
  and the permanent closed manifest was restored.

## Sequence-3 zsh EXIT-trap correction

- Confirmed that `local status=$?` assigned to zsh's reserved read-only
  `status` parameter after the successful live preflight and closure.
- Renamed only that local variable to `exit_code`, preserving the incoming exit
  code, all signal traps, variable cleanup, and closure/recovery behavior.
- Added focused success, failure, INT, TERM, HUP, non-disclosure, and closure-
  failure coverage.
- Recorded that successful live-preflight evidence must receive human review
  within its deadline before the same operator session ends.

## Sequence-4 offline preflight versioning

- Preserved sequences 1, 2, and 3 as immutable consumed history and left all
  frozen v1/v2 artifacts unchanged.
- Added a distinct inactive sequence-4 candidate and manifest plus fixed
  `004-storage_unknown` preparation, activation, preflight, recovery, and
  same-shell operator commands.
- Added a bounded pinned preflight-evidence review command supporting approve,
  reject, and request changes; late approval fails closed.
- Rehearsed the exact public sequence-4 workflow with networking disabled,
  synthetic credentials, one fake preflight, zero generation calls, immediate
  evidence review, permanent closure, and non-reuse rejection.

## Sequence-4 runbook readiness commands

- The first post-commit operational run stopped safely before human values
  because the runbook did not expose exact command-inventory and rehearsal
  commands, although their underlying tests existed.
- Added fixed host-shell readiness wrappers requiring no host Python, real
  credential, network access, or real sequence-4 state.
- The documented inventory validates all nine public commands and fixed
  sequence identity. The documented rehearsal runs the exact isolated public
  workflow through immediate evidence review, closure, cleanup, and non-reuse.

## Frozen-v4 generation-candidate resolution

- Verified the completed live frozen-v4 sequence-1 preflight lifecycle from
  exact current source records: evidence `f1f99523...`, approved review
  `12b71c10...`, 2,852 input tokens, and conservative maximum cost
  `$0.0019408`.
- Created separate unresolved and resolved inactive sequence-4 generation
  candidate packages. The resolved package binds the frozen-v4 manifest,
  prompt/schema/provider schema, request-identity artifact, exact request,
  canonical attempt, provider fingerprint, and approved live evidence.
- Preserved the proven generation-only scope: one credential lookup, one
  client, zero token preflights, one generation, zero retries, 12-second
  timeout, 500 output tokens, `$0.03` ceiling, and mandatory grounding review.
- Rehearsed all 12 future public commands across compliant, prose-rejection,
  structural-failure, semantic-failure, and prompt-policy-stress scenarios
  with networking disabled. Bounded rejection diagnostics retain no rejected
  response prose; successful evidence is reviewed and deleted.
- Generation remains unauthorized. No live v4 generation, credential access,
  client construction, provider request, or live timestamp preparation
  occurred in this milestone.

### Live-boundary corrections

- Split completed-preflight historical validation from current execution-state
  validation so an exact active generation manifest does not invalidate the
  already-closed preflight history.
- Added shared complete active-authorization, activation/transaction, and
  derived active-manifest validation used by both the public verifier and live
  entry point before credential lookup.
- Added an actual-live-verifier synthetic active-state path and 36 negative
  boundary mutations; the unchanged 12-command, five-scenario rehearsal still
  closes permanently with zero generation-path preflights and one fake
  generation per case.
- Replaced the rehearsal's minimal preflight evidence with a realistic
  render-through-evidence-review lifecycle created by the existing v4
  preflight functions. The live entry now verifies that history while the
  exact generation manifest is active and rejects wrong authorization and
  manifest states with zero credential, client, or provider boundary calls.
# 2026-08-16 — Multi-category task enhancement

- Replaced the required scalar task category with a required zero-or-more
  `categories` request/response collection; empty is valid, omission on create
  or full replacement is invalid, and duplicates/unknown values are rejected.
- Added normalized `task_categories` persistence and a transactional,
  idempotent migration that preserves current and legacy scalar assignments,
  task data, assignees, and dependencies.
- Added checkbox-style multi-category editing, ordered wrapping card labels,
  derived Uncategorized presentation, and a local OR category filter that
  hides empty phases while leaving the plan-wide finder independent.
- Kept deterministic task recommendation behavior unchanged and recorded the
  schema/API decision in ADR-0007.
- Focused verification passed 40 backend tests and 35 frontend tests before the
  final contract regressions were added. Final verification passed all 189
  backend tests, all 53 frontend tests, the production frontend build, and a
  rebuilt Docker Compose runtime. The persisted family plan migrated in place
  and returned every existing task with a `categories` collection.
- Automated runtime verification confirmed backend health, the complete
  persisted-plan response, and frontend availability. Interactive browser
  verification remains to be performed by a human reviewer.
