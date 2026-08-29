# Session Notes

## 2026-08-20 — Segmented Now/Plan navigation refinement

- Replaced the visually plain Now/Plan links with one cohesive segmented
  navigation control while retaining link semantics and React Router behavior.
- Added an immediately visible dark-green active state, bordered light inactive
  state, hover/pressed treatment, and a keyboard focus ring. React Router's
  `aria-current="page"` continues to identify the active location.
- Positioned the control at the upper right on desktop and made its two links
  equal-width, full-available-width tap targets at the existing mobile
  breakpoint. No absolute/fixed positioning, `!important`, or overflow masking
  was added.
- Focused and complete frontend tests and the production build passed. The
  isolated acceptance frontend was updated without touching its preserved
  database; final human navigation acceptance remains pending.
- A follow-up mobile spacing review found stacked top padding from the shared
  shell, container, card body, and navigation, plus Plan's route-specific top
  padding. Mobile now uses reduced shared top padding and one shared gap below
  navigation; Plan removes its redundant mobile top padding while retaining it
  from the desktop breakpoint upward.
- Responsive spacing-class coverage, all 76 frontend tests, and the production
  build passed. No horizontal inset, card, typography, or navigation-style rule
  changed; one final 390×844 visual check remains pending.

## 2026-08-19 — First Now/Plan/Experiments structural increment

- Selected stable `react-router` 8.3.0 in Declarative Mode and recorded
  ADR-0009. The existing lockfile already resolves React and React DOM 19.2.7,
  and development/build/container Node 24 satisfies the router's Node 22.22
  minimum; no React, Vite, TypeScript, Node, or build-architecture upgrade was
  required.
- Added `/` to `/now` replacement, canonical `/now` and `/plan`, accessible
  active navigation, and normal not-found behavior. Now shows the persisted
  plan title as **Our goal** and the persisted Task Recommendation; Plan retains
  the accepted management interface and expanded phases.
- Extracted the employment and moving-service prototypes into a self-contained
  Experiments page. The frontend route and both deterministic backend endpoints
  require separate exact `true` flags and remain absent by default; enabling
  them grants no AI, research, credential, or spending authority.
- Kept Task, Milestone, Decision, finder, category-filter, completed-section,
  editor, and Recommendation behavior covered without changing persistence or
  beginning Increment 2.
- Stopped only the bind-mounted normal frontend before source edits. The normal
  backend remained healthy on the unchanged active database. Automated suites
  passed, including default-off and enabled experiment modes.
- Restored the verified backup with SQLite's backup API into the isolated
  `gotime_now_plan_acceptance_data_db02bce` volume. The candidate runs at
  `http://localhost:16173` in project `gotime_now_plan_acceptance`, using only
  `gotime_now_plan_acceptance_net_db02bce` and alternate backend port 18000.
  Integrity, foreign keys, all original counts, normal endpoints, direct route
  serving, and default-off experimental endpoints passed. Human acceptance
  remains pending; the isolated environment is intentionally still running.

## 2026-08-19 — Now, Plan, and Experiments direction

- Audited the rendered interface and confirmed that it combines the persisted
  Recommendation and Task plan, the Milestone/Decision foundation, and
  suspended employment-planning and moving-service experiments.
- Identified the 47 active Task cards in four permanently expanded phases as
  the dominant scrolling cause. Moving experiments removes substantial
  clutter; separating Now from Plan and collapsing phases provides the larger
  reduction.
- Approved `/now` as the default attention experience and `/plan` as the
  complete editing experience, with desktop Now/Plan navigation and persistent
  mobile Now/Plan/Find navigation. The persisted plan title becomes **Our
  goal**; legacy priority cannot supply secondary Now items.
- Approved browser-session Plan expansion/scroll preservation, cross-route
  reveal behavior, compact linked Milestone/Decision sections, and one Add
  menu that does not remember its prior type.
- Preserved suspended prototype code, endpoints, tests, and documentation
  behind a future default-off frontend/backend Experiments boundary. Enabling
  it will not authorize AI, research, credentials, or spending.
- Kept explanation, timing, dependency, downstream-work, and assumption
  concepts for later derived-attention redesign rather than copying their
  experimental implementations into Now.
- Deferred an ADR until an established routing dependency and state-ownership
  approach are selected. No navigation work or Increment 2 implementation has
  begun.

## 2026-08-19 — Increment 1 acceptance and closeout

- Human browser acceptance passed for the existing plan and Recommendation,
  Milestone and Decision workflows, explicit user authority, narrow mutation
  stability, readable dates and badges, and the responsive layout refinements.
- Formally rebuilt and recreated only the normal frontend from accepted commit
  `23c9f3c`. Health, plan, Recommendation, frontend, and frontend-proxy checks
  passed; the healthy normal backend was not rebuilt or restarted.
- Confirmed the active database remained byte-for-byte and logically unchanged
  during frontend deployment. It still contains no Milestones, Decisions, or
  Decision options, and no family-plan Task or relationship was converted.
- Verified the acceptance containers, network, and database volume belonged
  only to the isolated `gotime_increment1_acceptance` project, then removed
  those disposable resources and their temporary Compose directory. Normal
  Docker resources and the verified pre-Increment-1 backup were preserved.
- Increment 1 is closed. Increment 2 has not begun; its required subtasks,
  work-informs-Decision relationships, advisory readiness, and contextual
  Recommendations require review and execution planning first.

## 2026-08-19 — Balanced mobile page insets

- Applied one responsive intro wrapper to align GoTime branding, the main
  question, and Today's Goal with the established 16-pixel mobile inset.
- Applied the same responsive alignment to the Primary Recommendation panel,
  Persistent Plan header/actions, and Milestones/Decisions header/actions.
- Left Task, Milestone, Decision, phase, and completed-section cards outside
  those wrappers so the accepted wider mobile content remains unchanged.
- Added responsive-class coverage. Final human visual acceptance in the
  preserved isolated environment remains pending.

## 2026-08-19 — Mobile finder spacing follow-up

- Grouped the task finder and category filter in one responsive wrapper so the
  label, input, and filter button share an 8-pixel mobile inset while retaining
  their existing desktop alignment.
- Reduced only the mobile gap between the search input and category button;
  input and button sizing, the wider mobile Task cards, and Milestone/Decision
  styling remain unchanged.
- Added focused responsive-class coverage. Final human mobile acceptance in
  the preserved isolated environment remains pending.

## 2026-08-18 — Increment 1 browser-acceptance refinements

- Preserved the isolated acceptance database containing one test Milestone,
  one test Decision, and four options while refining only the frontend.
- Made status badges compact, rendered date-only targets with abbreviated
  month names, constrained the latest-date picker to the earliest target, and
  added inline invalid-window feedback without discarding entered values.
- Removed the Milestone/Decision mutation callback that unnecessarily refreshed
  the unchanged task Recommendation and replaced the shared saving flag with
  per-action pending state. Narrow mutations now update cards in place without
  changing page height or disabling unrelated controls.
- Added mobile-only Milestone/Decision title and metadata typography plus
  wrapping and minimum-width behavior for Decision option rows. No global
  overflow suppression or `!important` override was added.
- Headless Chrome at a 390-pixel viewport measured a 394-pixel document width.
  The cause was an existing Bootstrap Row's negative gutters inside a
  zero-horizontal-padding Recommendation card body, not a Milestone or
  Decision card. A mobile-only margin correction was applied to that row.
- Focused and complete frontend tests and the production build passed. Final
  human reacceptance in the preserved isolated environment remains pending;
  the normal stack must not be updated to this refinement until approval.

## 2026-08-18 — Increment 1 Milestone and Decision foundation

- Added additive, transactional, idempotent persistence for Milestones,
  Decisions, and ordered Decision options. Existing databases receive empty
  new structures; no family-plan record is converted automatically.
- Added explicit request/response schemas and focused create/edit, Milestone
  achievement/reversal, and Decision selection/revision/unresolve actions.
- Added compact React-Bootstrap plan controls for Milestone target guidance,
  explicit achievement, ordered options, and user-controlled selection. Task
  and Recommendation behavior remains unchanged.
- Added migration, constraint, CRUD, API, and frontend behavior coverage.
  Backend compilation and all 195 backend tests passed; all 63 frontend tests
  and the production frontend build passed.
- Restored the verified pre-Increment-1 backup with SQLite's backup API into a
  uniquely named temporary volume, then started only the candidate image with
  `network=none`, no ports, and no active-volume mount. Every original-table
  row hash and count matched; 49 Task IDs remained unique; the three new tables
  were empty; integrity, foreign keys, health, plan, and Recommendation passed.
- A second candidate startup against that temporary volume proved migration
  idempotence. Only the temporary container and volume were removed afterward.
- The active `gotime_gotime_data` database remains unchanged and unmigrated.
  The normal backend remains stopped pending explicit approval to migrate and
  restart it. No real family-plan Milestone, Decision, Task, or relationship
  was changed.

## 2026-08-18 — Increment 1 architecture approval and safety gate

- Approved the independent Milestone and Decision foundation and recorded it
  in ADR-0008, including optional earliest/latest target dates, explicit
  achievement, ordered singular Decision selection, and the user-authority
  principle.
- Added **Our home is under contract** as the second real-world Milestone.
  Employment notice/PTO will eventually depend on that Milestone; the
  farewell-party Decision will not depend on starting the sale.
- Confirmed that future derived Do now selection ignores stored legacy priority
  while preserving priority data and transitional display.
- Created a fresh SQLite-online backup outside Git and successfully restored it
  into an isolated Docker volume using the deployed image's normal root runtime
  identity. The verification container was unprivileged, used `network=none`,
  published no ports, and mounted no active volume.
- Verified exact schema and row equality, all 49 unique Task IDs, aggregate
  counts, integrity, foreign keys, and health/plan/Recommendation endpoints.
  Removed only the temporary verification resources afterward.
- Stopped the normal backend before schema-bearing edits. The active
  `gotime_gotime_data` volume remains preserved and must not be mounted by
  candidate code.

## 2026-08-17 — Derived-attention vertical-slice technical design

- Renamed the human-facing home-sale Milestone to **Start selling our home**,
  achieved only when the user confirms that the selected public,
  builder/off-market, or parallel buyer-seeking channels are genuinely active.
- Decided that the existing `Put current home on the market` Task should
  conceptually become this Milestone and must not remain as a duplicate action
  Task. Applicable executable work belongs in conditional public-listing and
  builder-outreach branches.
- Audited the current SQLite schema/migration convention, Task validation and
  dependencies, recommendation/explanation engine, fixed-plan routes and
  schemas, React editor/cards/views/filter/finder/completed behavior, and the
  backend/frontend tests that would be extended. The audit was read-only.
- Queried the active SQLite database through an immutable, query-only
  connection. Integrity and foreign-key checks passed. Exactly one matching
  milestone-like Task exists with one direct prerequisite and three direct
  dependents; no data was changed.
- Provisionally classified the realtor relationship as work that should inform
  the new Decision, the home-sale-contract work as genuinely dependent on
  Milestone achievement, the farewell-party edge as timing guidance, and the
  notice/PTO edge as unclear and requiring user review.
- Recommended independent Milestone and Decision domain concepts, one selected
  option including a named parallel strategy, one-level required subtasks,
  work-informs-Decision links, derived readiness, option associations plus a
  keep-active override, and bounded Decision/work-to-Milestone relationships.
  Evidence, constraints, and preferences remain Decision information rather
  than separate entities in the first slice.
- Recommended preserving the old Task's stable ID value as the new Milestone
  ID, translating relationships only after review, preserving all unrelated
  data, failing closed on drift, and rehearsing a fresh verified backup and
  isolated-volume migration before touching the active database.
- Proposed four reviewable increments: Milestone/Decision foundation;
  required subtasks/evidence/readiness and contextual Recommendation;
  conditional activation/safe revision; then rehearsed family-plan conversion
  and end-to-end acceptance.
- No application code, schema, API contract, test, runtime, container, backup,
  manifest, or persisted family-plan data was changed. No ADR was created
  because the technical choices still require approval.

## 2026-08-17 — Home-sale manual reasoning walkthrough

- Completed the six-state manual walkthrough from actionable realtor work,
  through required subtasks and advisory Decision readiness, to conditional
  branch activation, Decision revision, and explicit Milestone achievement.
- Established that Recommendations target actionable, active leaf-level Tasks
  and explain their parent purpose, evidence contribution, Decision-unlocking
  effect, and Milestone contribution without manual priority or an arbitrary
  start date.
- Selected one level of required subtasks for the minimum provisional
  representation. Parent status is derived automatically and reversibly;
  completing the last required subtask completes the parent and satisfies
  dependencies pointing to it.
- Kept Decision readiness advisory and option selection under user authority.
  Additional evidence work may keep a Decision in a gathering-information
  state, but incomplete expected evidence does not prevent the user from
  deciding.
- Distinguished activation from Task progress status. Unselected conditional
  work remains preserved but inactive, hidden by default, excluded from
  ordinary counts, attention, and Recommendations, and discoverable through an
  explicit inactive-work reveal or identified search result.
- Recorded revision safeguards: never delete alternate branches, never
  silently deactivate In progress work, disclose affected Tasks, preserve
  completed history, and let users retain or reactivate work.
- Confirmed that supporting-work completion cannot prove a real-world
  Milestone. GoTime may prompt, but the user explicitly confirms achievement.
- Captured the governing principle: GoTime may derive, recommend, explain, and
  warn, but the user retains final authority.
- Proposed a narrow end-to-end slice and made review/approval its next
  objective. No database entity, Pydantic schema, API contract, interface,
  application, test, runtime, AI, or persisted family-plan change was made.
- Added a separate Parking Lot consideration for safely removing incomplete
  work, including relationship inspection and distinctions among Remove from
  plan, No longer applicable, and Permanent deletion.

## 2026-08-17 — Home-sale strategy reference scenario

- Established the current-home sale campaign launch as GoTime's first concrete
  reference scenario for milestone-driven planning and derived attention. The
  Milestone is reached when the family's selected public, builder/off-market,
  or parallel marketing channels become active in a currently approximate
  post-New Year window.
- Recorded `Select the initial home-sale strategy` as a revisable Decision with
  credible as-is public, repair-first public, builder/off-market, parallel, and
  market-feedback options.
- Distinguished the minimum acceptable net proceeds hard constraint from gross
  sale price, scenario-specific costs, estimated net proceeds, and the
  preferences used to compare otherwise viable options. The private threshold
  was intentionally omitted from the public scenario.
- Recorded the ballpark realtor evidence needed to compare options, including
  ranges, confidence, timing, costs, and risk, without treating unavailable
  certainty or false precision as a requirement.
- Defined provisional Milestone, Decision option, Evidence need, Conditional
  work, Hard prerequisite, and Supporting or timed work language, and refined
  the existing Decision, Hard constraint, and Preference distinctions. These
  remain domain concepts rather than committed database entities, Pydantic
  schemas, APIs, or interface controls.
- Documented why `Reengage with the realtor` deserves attention now: it is
  actionable, supplies required evidence, and unlocks a consequential Decision
  controlling multiple downstream branches. This reasoning does not depend on
  manual task priority or an arbitrary start date.
- Set the next product-design activity to a manual walkthrough of the scenario
  to identify the smallest representation needed before proposing schema or
  interface changes. No application, persisted data, runtime, test, schema,
  API, or ADR change was made.

## 2026-08-16 — Derived-attention product direction

- Selected derived attention as the next product-design objective: GoTime
  should calculate what deserves attention now instead of asking users to
  manually rank every task.
- Recorded provisional Do now, Coming soon, Later, and Waiting states and the
  deterministic plan inputs that may contribute to them. Names and exact rules
  remain subject to validation against representative tasks in the real family
  plan.
- Agreed that the stored Critical/High/Medium/Low field should be demoted or
  potentially retired from ordinary task creation and ranking, while preserving
  the field and all existing data until replacement behavior is validated.
- Established AI-assisted planning knowledge as an intentional later
  capability for structured lead times, prerequisite patterns, durations, and
  timing windows. Consequential knowledge remains inspectable, sourced,
  confidence/freshness-aware, and user-correctable; deterministic rules retain
  ownership of attention and Recommendation results.
- Sequenced the work from a no-AI baseline, through identification and
  contracting of missing knowledge, to later adaptation of the existing AI API
  pipeline and comparison with the baseline. No AI experiment, infrastructure,
  schema, API, or runtime work was authorized.
- Replaced the accumulated historical `NEXT_SESSION.md` instructions with a
  concise current handoff. Historical implementation detail remains preserved
  in this file, while unrelated UX observations remain in the Parking Lot.

## 2026-08-16 — Multi-category browser-acceptance corrections

- Human browser acceptance passed for existing assignment preservation;
  multi-category selection and canonical ordering; Uncategorized save,
  display, filtering, reload, and new-task-default behavior; OR filtering and
  deduplication; hidden phases and filtered completed counts; finder
  independence plus compatible/incompatible-filter navigation; completed-task
  reveal; dropdown persistence, dismissal, and Escape focus restoration; mobile
  category wrapping and density; wider active/completed lists and alignment;
  and restored desktop spacing.
- Confirmed the verified post-migration backup exists outside Git at
  `/home/joeshep/backups/gotime/20260817T001021Z-a32c31d-post-migration/`.
- Closeout verification passed 39 focused frontend tests, all 60 frontend
  tests, all 189 backend tests, and the production frontend build. The live
  health, plan, and stored-task recommendation endpoints each returned HTTP
  200.
- Reused one controlled category-dropdown component for the plan filter and
  task editor, preserving internal selection/Clear all interactions while
  adding outside-click and Escape dismissal with trigger-focus restoration.
- Kept finder searching plan-wide; selection now clears only an incompatible
  category filter, announces that through the existing notice, and reveals,
  expands, scrolls to, focuses, and highlights hidden active or completed work.
- Used responsive Bootstrap utilities for task-card padding and spacing below
  `sm`, avoiding `!important`; retained mobile-only SCSS only for typography
  while preserving desktop density, control tap targets, and existing
  priority/category badge styling.
- Followed browser review with a mobile-only outer-density pass: reduced the
  page and main-content gutters, phase-body indentation, completed-body
  indentation, phase-to-list spacing, and inter-card gaps while preserving the
  accepted task-card interior and exact desktop defaults.
- Added responsive layout assertions for the application shell, phase bodies,
  and aligned active/completed lists. The focused 48-test frontend run, full
  60-test frontend suite, and production build passed; emitted CSS inspection
  confirmed the custom gutter rules remain inside the mobile media query and
  Bootstrap's default desktop card/accordion rules remain present.
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

- Added accessible parent targeting to contextual subtask Recommendation cards.
  Only the parent title after **Part of:** is a native link-style button, named
  `View parent task [title]`; it sends the parent ID through the existing
  Recommendation Task-target path. Focused coverage confirms phase/completed
  reveal, parent expansion, focus/highlight, compatible child targeting,
  keyboard-focus semantics, and no parent control for top-level Tasks.
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

# 2026-08-20 — Now/Plan/Experiments structural increment closeout

- Human browser acceptance passed for the persisted Now and Plan separation,
  canonical routing and redirects, Back/Forward behavior, normal not-found
  handling, default-off Experiments boundary, shared segmented navigation, and
  responsive page-shell presentation.
- Accepted the remaining unrelated mobile-spacing inconsistencies as deferred
  visual polish so they do not delay the functional navigation sequence.
- Built and deployed the normal frontend and backend from accepted commit
  `3c525aac2519b9d62332ff48bfa73c98ceaa5a5f` with both Experiments flags
  disabled. Health, frontend routing and proxying, Plan, and Recommendation
  checks passed; both experimental API routes remained unavailable.
- Verified the active database before and after deployment. Integrity and
  foreign keys passed, every table count and stable row-content hash matched,
  and Milestones, Decisions, and Decision options remained empty. SQLite file
  metadata changed during normal backend startup, but logical content did not.
- Removed only the isolated `gotime_now_plan_acceptance` containers, network,
  disposable database volume, and temporary Compose directory after confirming
  their project labels and mounts were separate from normal GoTime resources.
  The verified pre-migration backup and `gotime_gotime_data` were untouched.
- The first structural increment is complete. Phase collapsing, Plan session
  state, cross-route reveal, the unified Add menu, mobile Find navigation,
  secondary attention items, and derived-attention Increment 2 have not begun.

# 2026-08-20 — Collapsible Plan phases candidate

- Added accessible full-width phase-header buttons with remaining/completed
  counts, directional chevrons, independent expansion, and compact Expand all
  and Collapse all controls. Completed subsections remain independently
  collapsed and Collapse all resets them.
- Added versioned, plan-ID-scoped `sessionStorage` state for expanded phases and
  completed subsections. Missing, malformed, incompatible, and stale records
  safely produce or retain only valid phase IDs. No state is persisted through
  the API or SQLite.
- Category filtering snapshots pre-filter expansion once, opens matching
  phases, retains user toggles without replacing the snapshot, and restores it
  on clear. Finder opens only its destination phase and opens the completed
  subsection when required while preserving existing filter, focus, scroll,
  and highlight behavior.
- Focused verification passed 46 tests. The complete frontend suite passed all
  82 tests, the production build passed, and `git diff --check` passed. Backend
  source and tests were unchanged.
- Restored the verified backup with SQLite's backup API into disposable volume
  `gotime_phase_collapse_acceptance_data_0660de4`. The isolated database has 49
  unique Tasks, expected relationship counts, empty Increment-1 entities,
  integrity `ok`, and no foreign-key violations.
- Left the candidate running at `http://localhost:17173` in Compose project
  `gotime_phase_collapse_acceptance`. Neither acceptance container mounts
  `gotime_gotime_data`; the normal frontend remains stopped, while the normal
  backend remains healthy and the active database is byte-for-byte unchanged.
- Human acceptance remains pending. Cross-route Finder, Plan scroll restoration,
  unified Add, mobile bottom navigation, secondary attention items, family-plan
  conversion, and derived-attention Increment 2 were not started.

# 2026-08-20 — Collapsible Plan phases closeout

- Human browser acceptance passed for all phase-collapse behavior: initial and
  multiple expansion, accessible keyboard headers, filtered and unfiltered
  counts, independent completed sections, global controls, category-filter
  expansion and restoration, Finder reveal, Now/Plan and refresh persistence,
  status-count stability, and desktop/mobile presentation without observed
  overflow, flicker, or page jumps.
- Built the normal frontend from accepted commit `73a7edd9720fa4933baaa6eeb036eeea8184a3b8`
  with Experiments disabled and recreated only `gotime-frontend-1`. The existing
  backend remained running and healthy throughout. Frontend serving, API
  proxying, Plan, and Recommendation checks passed; both experimental API
  routes remained 404.
- Active database evidence matched exactly before and after deployment: size,
  modification timestamp, SHA-256, integrity, foreign keys, every table count,
  and every stable row-content hash. Milestones, Decisions, and Decision options
  remained empty.
- Removed only `gotime-phase-collapse-acceptance-frontend`,
  `gotime-phase-collapse-acceptance-backend`, volume
  `gotime_phase_collapse_acceptance_data_0660de4`, network
  `gotime_phase_collapse_acceptance_net_0660de4`, and their temporary Compose
  directory after confirming project labels, mounts, and isolation. Normal
  resources, `gotime_gotime_data`, and the verified backup were untouched.
- Phase and completed-subsection expansion remains versioned, plan-ID-scoped
  browser-tab `sessionStorage` state; no workspace state is stored in SQLite or
  sent through the API. Remaining unrelated mobile spacing stays deferred
  visual polish.
- Cross-route Finder, Plan scroll restoration, unified Add, mobile bottom
  navigation, secondary attention items, family-plan conversion, and
  derived-attention Increment 2 were not started.

# 2026-08-20 — Shared Find and Plan scroll-restoration candidate

- Replaced the inline Plan Finder with a shared, text-labeled header action on
  Now and Plan. It opens an accessible right-side off-canvas panel, refreshes
  its plan snapshot on each opening, reports phase and status context, and
  supports explicit, Escape, and backdrop dismissal with focus return.
- Kept Find plan-wide and category-independent. A result from Now adds one Plan
  history entry; selection already on Plan adds none. Plan consumes the target
  once after panel closure, retaining compatible filters or clearing an
  incompatible one, and reuses the accepted phase/completed reveal, scroll,
  focus, and temporary-highlight behavior.
- Added versioned, plan-ID-scoped `sessionStorage` for Plan scroll position.
  Restoration waits for Plan data and expansion state, clamps page bounds,
  ignores malformed or stale values, and yields to Find destinations. Scroll
  writes are bounded to animation frames and never reach the API or SQLite.
- Focused coverage and the complete frontend suite passed (89 tests), the
  production frontend build passed, and backend/schema files remained
  unchanged. No ADR was needed because ADR-0009 already assigns transient Plan
  workspace state to a small provider plus `sessionStorage`.
- Restored the verified pre-Increment-1 backup through SQLite's backup API into
  disposable volume `gotime_shared_find_acceptance_data_f08054d`. The isolated
  database migrated to the current additive schema, retained 49 unique Tasks,
  passed integrity and foreign-key checks, and has no Milestones, Decisions, or
  Decision options.
- Left Compose project `gotime_shared_find_acceptance` running at
  `http://localhost:18173` (backend `http://localhost:18000`) for human review.
  Its containers use only the named disposable volume and network. The normal
  frontend remains stopped, the normal backend remains healthy, and the active
  database is byte-for-byte unchanged.
- Human acceptance and normal deployment are pending. Cross-route
  Recommendation navigation, unified Add, persistent mobile bottom navigation,
  secondary attention items, family-plan conversion, and derived-attention
  Increment 2 were not started.

## Browser-acceptance corrections

- Diagnosed why direct refresh restored Plan scroll while route navigation did
  not: passive route cleanup read `window.scrollY` after Now had moved the
  viewport to zero and replaced the saved Plan position. Plan now tracks its
  last owned scroll value immediately on scroll events, bounds storage writes,
  and uses layout lifecycle cleanup without consulting Now's viewport.
- Restores expansion, completed-subsection, and category-filter session state
  before the one-time scroll restoration. Finder still overrides restoration;
  its resulting position becomes the next ordinary return position without
  persisting or replaying focus and highlight state.
- Added versioned, plan-ID-scoped category-filter `sessionStorage`, configured
  ordering, safe invalid-data handling, route/refresh restoration, and
  persistence of compatible or Finder-cleared filter state.
- Replaced the persistent generic filter banner with a Task-specific,
  dismissible informational notice. It is fixed outside document flow to avoid
  page jumps, expires after about six seconds, and clears on filter changes,
  new Find actions, routing, or remount.
- Centered the distinct Find action beside the segmented navigation and matched
  its computed line-height, padding, border, radius, and minimum height to the
  inner Now/Plan targets while preserving tap targets and responsive structure.
- Focused route, filter, notice, and Finder regressions passed. The complete
  frontend suite passed all 100 tests and the production build passed. Human
  retesting in the isolated environment remains pending.

# 2026-08-23 — Shared Find and Plan workspace-restoration closeout

- Complete human acceptance passed for shared Find from Now and Plan, the
  off-canvas panel, cross-route targeting and browser-history behavior,
  session-restored Plan workspace state, corrected route restoration, the
  transient filter-cleared notice, and responsive Find-button alignment. The
  shared action replaces the inline Plan Finder.
- Phase, completed-section, category-filter, and Plan-scroll records remain
  versioned, plan-ID-scoped `sessionStorage`. Finder destinations override
  restoration and become the next saved Plan position. Target focus and
  highlighting remain transient and do not replay after refresh or later
  navigation. The Task-specific filter-cleared notice is dismissible, expires
  after about six seconds, and is never persisted.
- Built `gotime-frontend:latest` from accepted commit
  `408546bf431cdc85c09934e58ccb3c0444b8379e` and recreated only
  `gotime-frontend-1` with `VITE_ENABLE_EXPERIMENTS=false`. Frontend serving,
  Now, Plan, Plan and Recommendation proxy calls, client-side Experiments
  not-found handling, and both disabled experimental APIs passed. The normal
  backend retained container `f1728652cb2086f2aed3ae63db66e4a1f5618c24264d011bf15ed62c7d9676bb`,
  image `b533f1f2fea957a51dcf3624811d3d220fca8d5effa65ece5cb20d8722ec82ee`,
  its original reboot start time, and restart count zero.
- The active database began at 221,184 bytes with SHA-256
  `cf158547d56c158d16ed442bae279a4a7d27ef266a78d15b258e007f69c656c1`.
  Its first Plan read after the backend's independent reboot restart lazily ran
  the existing idempotent repository initialization and same-value default-phase
  updates, changing only SQLite file metadata and its byte checksum. Final size
  remained 221,184 bytes and final SHA-256 was
  `f7b533dec39ee57207928a92b61af4de87a4219791454dcc9ba78b1476e9d036`.
  Integrity was `ok`, foreign-key checks were empty, all table counts and stable
  row hashes matched, all 49 Task IDs remained unique, and Milestones,
  Decisions, and Decision options remained empty. Repeated reads produced no
  further file change.
- Removed exactly `gotime-shared-find-acceptance-frontend`,
  `gotime-shared-find-acceptance-backend`, volume
  `gotime_shared_find_acceptance_data_f08054d`, network
  `gotime_shared_find_acceptance_net_f08054d`, and
  `/tmp/gotime-shared-find-acceptance-f08054d/`. Normal containers, the active
  volume and network, verified backups, manifests, and unrelated Docker
  resources were untouched.
- Desktop navigation is not sticky. Scrolling Plan to the top before leaving
  correctly saves the top; persistent Now, Plan, and Find access deep in the
  desktop Plan may be reconsidered later. Persistent mobile bottom navigation
  remains planned, and unrelated mobile-spacing polish remains deferred.
- Cross-route Recommendation targeting, unified Add, persistent mobile bottom
  navigation, secondary attention items, family-plan conversion, and
  derived-attention Increment 2 were not started.

# 2026-08-23 — Unified Plan Add candidate

- Added one responsive Add dropdown beside the compact Family plan heading on
  Plan, and removed the separate Add Task, Add Milestone, and Add Decision
  controls. The ordered menu copy is Task — Something that needs to be done;
  Milestone — An important outcome or moment; Decision — A choice that needs to
  be made. Now remains recommendation-focused with no Add control.
- Reused the existing three creation editors with initial-field focus, one-flow
  coordination, scoped saving state, preserved validation drafts, cancel focus
  return, and captured-scroll restoration. Add closes shared Find; Find cannot
  open over an unsaved creation editor.
- Successful Task creation consumes the returned Plan aggregate and reuses the
  established phase/filter/notice/scroll/focus/highlight path. Successful
  Milestone and Decision creation reveal their returned cards with the same
  bounded focus and highlight treatment. Resulting positions replace the saved
  Plan scroll position; transient creation targeting does not replay.
- Focused verification passed 70 tests, the full frontend suite passed all 107
  tests, the production build passed, and `git diff --check` passed. No backend,
  schema, API, ADR, or database files changed.
- Built candidate image `gotime-unified-add-frontend:candidate-7a91c2e` and
  restored the verified pre-Increment-1 backup with SQLite's backup API into
  disposable volume `gotime_unified_add_acceptance_data_7a91c2e`. The isolated
  database has integrity `ok`, no foreign-key violations, 49 unique Tasks, and
  zero Milestones, Decisions, or Decision options.
- Left Compose project `gotime_unified_add_acceptance` running at
  `http://localhost:19173` (backend `http://localhost:19000`) with containers
  `gotime-unified-add-acceptance-frontend` and
  `gotime-unified-add-acceptance-backend` connected only to network
  `gotime_unified_add_acceptance_net_7a91c2e`. Neither container mounts or joins
  normal data or networking. The normal bind-mounted frontend remains stopped;
  the original normal backend remains healthy with restart count zero.
- The active database remained exactly 221,184 bytes, mtime_ns
  `1787514115744690963`, and SHA-256
  `f7b533dec39ee57207928a92b61af4de87a4219791454dcc9ba78b1476e9d036`,
  with integrity `ok`, no foreign-key violations, identical table counts and
  stable row hashes, 49 unique Tasks, and zero Increment-1 entities.
- Human acceptance and normal deployment remain pending. Cross-route
  Recommendation targeting, persistent mobile bottom navigation, secondary
  attention items, family-plan conversion, and derived-attention Increment 2
  were not started. Unrelated mobile-spacing polish remains deferred.

# 2026-08-23 — Unified Add notice correction

- Human acceptance passed every unified Add behavior except successful Task
  feedback with an incompatible category filter. Task save unconditionally set
  the persistent generic `Task added` success state before the existing reveal
  path correctly produced its task-specific transient filter-cleared notice.
- Removed only the generic successful-creation assignment. Task editing and
  status success messages, validation and request errors, and Milestone and
  Decision behavior remain unchanged. Compatible and unfiltered Task creation
  now relies on phase reveal, scroll, focus, highlight, and count updates.
- Reused the established fixed informational notice without adding another
  mechanism. It names the created Task, has an accessible close control,
  expires after six seconds, clears on category-filter, Add, or Find
  interaction, is not persisted, does not take focus, and does not replay.
- Focused notice and Plan regressions passed 57 tests; the complete frontend
  suite passed all 109 tests; the production build and `git diff --check`
  passed. Backend, schema, API, ADR, database, and native date-input files were
  unchanged.
- Before frontend replacement, the human-tested disposable database remained
  healthy with 52 unique Tasks, one Milestone, one Decision, two Decision
  options, integrity `ok`, no foreign-key violations, size 221,184 bytes, and
  SHA-256 `99de5dfc6eeeefd1bf5c16291025729402985b66f28f9dce1a92a8fd6b270e4b`.
  These records must remain intact for the final focused retest.

# 2026-08-23 — Plan-wide duplicate-title candidate extension

- The required read-only active audit found no canonical duplicate Task,
  Milestone, or Decision groups. The disposable audit found one allowed Task
  group in `family-relocation-plan`: canonical `notice timeout test`, IDs
  `notice-timeout-test-bb118b9d-04d0-4d33-a77c-f336611c57c1` and
  `notice-timeout-test-cb948a97-1cec-44a4-8bdc-3cc16a0b4b1d`, both stored as
  `Notice timeout test` in phase `decide` with status `not_started`. No records
  were repaired or changed.
- Added prospective per-Plan, per-type uniqueness for Task, Milestone, and
  Decision titles. Canonical comparison trims, collapses internal whitespace,
  and case-folds Unicode. Tasks compare across all phases and statuses;
  cross-type titles remain valid. Canonical-equivalent self-edits remain valid,
  including for legacy duplicate groups.
- Backend POST and full PUT checks execute with their writes inside immediate
  SQLite transactions. Stable 409 codes and bounded messages identify each
  entity type. No schema, migration, trigger, denormalized key, or active-data
  conversion was added.
- The three reused editors share one frontend comparison utility. Proven local
  conflicts and authoritative backend conflicts remain inline at the title,
  preserve drafts, restore save controls, and cause no reveal or workspace
  effects. Backend conflicts focus the title; a unique change clears the error.
- Before candidate container work, acceptance had 55 unique Tasks, one
  Milestone, one Decision, two Decision options, integrity `ok`, no foreign-key
  violations, size 221,184 bytes, and SHA-256
  `46c01214f5af7b3a59b28d000ae63189d6c6e5a5d2ce85ef26a2ca7def4c04d0`.
  The active database remained 221,184 bytes with SHA-256
  `f7b533dec39ee57207928a92b61af4de87a4219791454dcc9ba78b1476e9d036`.
- Focused backend tests passed 42; the complete backend suite passed 207;
  backend compilation passed. Focused frontend tests passed 77; the complete
  frontend suite passed 114; the production frontend build and
  `git diff --check` passed.
- Recreated only the isolated acceptance backend and frontend from the focused
  candidate while retaining volume `gotime_unified_add_acceptance_data_7a91c2e`.
  Runtime Plan, proxy, and health checks returned 200, and a read-only duplicate
  probe returned the stable 409 payload. Post-replacement integrity remained
  `ok`, foreign keys remained clean, and every count and stable row hash
  matched. Existing startup initialization changed only SQLite file metadata
  and byte checksum to
  `a9d82c974795715c2c89bd6030fd43a19ddf77842c9e06859cac9b727a9c513d`.
  The active database, normal backend, and stopped normal frontend were
  unchanged.

# 2026-08-23 — Task success-banner acceptance correction

- Removed only the redundant persistent success messages after successful Task
  full edits and Task status changes. Successful edits still close the editor
  and render returned Task data; status changes still move Tasks, update phase
  and completed counts, refresh dependent state, and retain the established
  Recommendation callback behavior.
- Preserved validation and duplicate-title feedback, backend and unexpected
  request errors, and the dismissible six-second filter-cleared informational
  notice. Task creation, Milestone and Decision behavior, native date inputs,
  workspace state, focus, and scrolling are unchanged.
- Added focused assertions for successful edit rendering without a banner,
  successful status movement without a banner, and visible failed-status
  feedback. Stabilized the existing stale-conflict scroll assertion by waiting
  for initial Plan restoration before capturing its rejection baseline.
- Focused frontend verification passed 70 tests; the complete frontend suite
  passed all 115 tests; the production frontend build passed. No backend,
  schema, API, ADR, or database source files changed.
- Before replacement, the preserved acceptance database had 58 unique Tasks,
  three Milestones, two Decisions, and four Decision options, integrity `ok`,
  no foreign-key violations, size 221,184 bytes, and SHA-256
  `443410e44f1f8428946de41b7204dd55acc58affab453997e9f413d5ffd3bce4`.
  Stable row hashes were recorded for post-replacement comparison. The normal
  frontend remained stopped; the normal backend remained healthy and
  unchanged; the active database remained byte-for-byte unchanged at SHA-256
  `f7b533dec39ee57207928a92b61af4de87a4219791454dcc9ba78b1476e9d036`.

# 2026-08-23 — Unified Add acceptance, deployment, and closeout

- Complete human acceptance passed for unified Add, all three reused creation
  editors and reveal paths, corrected transient Task feedback, prospective
  per-type title uniqueness, inline conflict recovery, and the final removal of
  redundant Task edit/status success banners.
- The pre-deployment active audit found no canonical duplicate groups among
  Tasks, Milestones, or Decisions. The database was 221,184 bytes, mtime_ns
  `1787514115744690963`, SHA-256
  `f7b533dec39ee57207928a92b61af4de87a4219791454dcc9ba78b1476e9d036`,
  integrity `ok`, and foreign-key clean. It contained 49 unique Tasks, zero
  Milestones, zero Decisions, and zero Decision options.
- Pre-deployment stable ordered-row hashes were: decision options, decisions,
  and milestones `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`;
  phases `77e694dd42fa94fb15d3fb75f452ff37aab2fb590f2d317e68e24c3ea8130340`;
  relocation plans `2c2620d61df783578e34379c44863b0ab43678a69076dc48e0494ab9d4bb888a`;
  task assignees `58d8e5d6f8ac36df50c3fbfde48da0420a09686e74fa9180d198656d98c63c73`;
  task categories `6134fca669f6fda7c70139fbc70db66edcf73fd697f1cda6960bbc00be3617b0`;
  task dependencies `46549ba537ed2d21636759600647a7a3a04286d56ec2a3902cbdb07af4b61d75`;
  and Tasks `167e1cc3b57658c50f04fe9ea7d71ba872fed6d69821ef38c5561fdc9e35dc17`.
- Built and deployed normal images `gotime-frontend` image SHA
  `830167f0903763b5ddc03b93a45eced30d47298451b6b817b6a27a44ad357253`
  and `gotime-backend` image SHA
  `d8aedab223dded275d35f30eb9717c23b7821d9e4dd6f5c94f6888ab384c7056`.
  Recreated only `gotime-frontend-1` and `gotime-backend-1`; both started with
  restart count zero, their experiment flags explicitly false, normal ports
  and proxy intact, and `gotime_gotime_data` preserved.
- Normal frontend, `/now`, `/plan`, Plan and Recommendation APIs, frontend API
  proxy, and both health paths returned 200. Root retains its client redirect
  to `/now`; disabled `/experiments` uses the client not-found route, no
  Experiments navigation is present, and both experimental APIs returned 404.
  Deployed source contains unified Add copy and shared title validation and
  omits the removed Task edit/status success strings.
- The non-mutating normal Task duplicate probe returned HTTP 409 with
  `duplicate_task_title` and created no Task. Post-deployment integrity remained
  `ok`, foreign keys remained clean, canonical audits remained empty, every
  table count and stable ordered-row hash matched, and all 49 Task IDs remained
  unique. Final size remained 221,184 bytes; mtime_ns became
  `1787540386457385549`; SHA-256 became
  `9b5e14b5d04799f8972f4875fa66fc82f8601221b206dda18e69d8651c7a66bd`.
  The byte change reflects known no-op SQLite write activity; logical content
  was identical before and after.
- Removed exactly acceptance containers
  `gotime-unified-add-acceptance-frontend` and
  `gotime-unified-add-acceptance-backend`, volume
  `gotime_unified_add_acceptance_data_7a91c2e`, network
  `gotime_unified_add_acceptance_net_7a91c2e`, and temporary directory
  `/tmp/gotime-unified-add-acceptance-7a91c2e/`. Normal resources, verified
  backups, manifests, and unrelated Docker resources were untouched.
- Cross-route Recommendation targeting, persistent mobile bottom navigation,
  secondary attention items, family-plan conversion, and derived-attention
  Increment 2 were not started. Unrelated mobile-spacing polish, real-mobile
  native date-picker validation, possible persistent desktop Now/Plan/Find
  access deep in Plan, and elimination of no-op initialization writes remain
  deferred.

# 2026-08-23 — Persistent mobile bottom-navigation candidate

- Replaced the below-`sm` provisional header navigation with one semantic,
  fixed, equal-width Now, Plan, and Find bottom bar. Only the established
  desktop header renders at `sm` and above. Active route styling includes
  `aria-current`; Find exposes expanded/pressed state while remaining a button.
- Active mobile route taps scroll to the top without adding history, respecting
  reduced motion. Plan directly persists zero for an intentional active tap;
  leaving a deep Plan snapshots the actual position before navigation, and an
  ordinary return restores it. Existing Back, Forward, refresh, filter, phase,
  completed-section, and Finder destination behavior remains intact.
- Reused the single existing Find Offcanvas. The bottom bar becomes inert below
  its backdrop, while modal focus containment, Escape/backdrop/close dismissal,
  trigger-specific focus return, and result targeting remain unchanged.
- Added a shared mobile navigation-height/safe-area boundary and one PageFrame
  bottom accommodation. The transient filter-cleared notice uses the same
  offset; desktop spacing and all accepted horizontal insets/card density are
  unchanged.
- Focused navigation, workspace, Find, routing, and unified-Add tests passed 38;
  the complete frontend suite passed 122; the production build passed; and
  `git diff --check` passed. Backend, schema, API, database, title-uniqueness,
  and ADR files were unchanged; ADR-0009 already owns routing and session
  workspace boundaries, so no new ADR was needed.
- Before candidate work, the active database remained 221,184 bytes, mtime_ns
  `1787540386457385549`, and SHA-256
  `9b5e14b5d04799f8972f4875fa66fc82f8601221b206dda18e69d8651c7a66bd`,
  with integrity `ok`, no foreign-key violations, 49 Tasks, zero Milestones,
  Decisions, or options, and the accepted stable ordered-row hashes. The normal
  bind-mounted frontend was stopped before edits; the unchanged normal backend
  remained healthy.
- Built isolated frontend image `gotime-mobile-nav-frontend:candidate-8559604` and left
  project `gotime_mobile_nav_acceptance` running at
  `http://localhost:20173` with backend `http://localhost:20000`. Containers
  `gotime-mobile-nav-acceptance-frontend` and
  `gotime-mobile-nav-acceptance-backend` connect only to network
  `gotime_mobile_nav_acceptance_net_8559604`; only the backend mounts volume
  `gotime_mobile_nav_acceptance_data_8559604`.
- Restored the preserved manifest-bound backup through SQLite's backup API.
  Its expected baseline contains 48 unique Tasks, 75 assignees, 48 category
  assignments, and 45 dependencies. Current additive initialization left zero
  Milestones, Decisions, and options; integrity is `ok` and foreign keys are
  clean. Acceptance health, Plan, Recommendation, direct Now/Plan, and frontend
  proxy requests returned HTTP 200.
- After candidate work, the active database retained the exact baseline size,
  mtime_ns, checksum, counts, integrity/foreign-key results, and every stable
  ordered-row hash. Neither acceptance container mounts `gotime_gotime_data` or
  joins the normal network; the normal frontend remains stopped and the normal
  backend identity, start time, and restart count remain unchanged.
- Human acceptance and normal deployment remain pending. Desktop navigation
  remains nonsticky and may be reconsidered separately. Cross-route
  Recommendation targeting, secondary attention items, family-plan conversion,
  derived-attention Increment 2, unrelated spacing polish, native date-picker
  emulator behavior, and backend no-op initialization writes were not changed.

# 2026-08-23 — Mobile bottom-spacing acceptance correction

- Traced the excessive bottom gap to stacked spacing: the original shared
  mobile reserve was 3.75rem plus the safe-area inset plus 1rem, while the
  application container and card body each contributed `pb-4` and the final
  Plan phase contributed `mb-3`. At zero safe-area inset those explicit
  contributions totaled about 140px before incidental borders and matched the
  reported 150–160px visual region.
- Consolidated mobile accommodation into one PageFrame calculation: 4rem base
  navigation height plus `env(safe-area-inset-bottom, 0px)` plus a 1rem content
  gutter. Safe-area padding remains inside the fixed bar, the bar stays at
  `bottom: 0`, and the inset is added exactly once to both bar height and the
  corresponding page reserve. The 44px minimum targets sit within the 64px
  zero-inset bar with modest vertical inset.
- Removed only redundant mobile bottom padding/margins. Responsive Bootstrap
  spacing preserves the accepted desktop layout, and ordinary phase spacing
  remains unchanged except that the final mobile phase no longer adds a second
  trailing spacer. Notices continue to use the shared navigation boundary;
  modal and Offcanvas layering is unchanged.
- Focused and complete frontend verification and the production build passed.
  No trustworthy browser layout engine was installed, so dimensions are
  structurally established as a 64px zero-inset bar and 16px final-content
  clearance; final 390 x 844 visual measurement remains a human acceptance
  check.
- Focused coverage passed 68 tests, the complete frontend suite passed all 123
  tests, the production build passed, and `git diff --check` passed. Rebuilt
  and recreated only `gotime-mobile-nav-acceptance-frontend` with image
  `gotime-mobile-nav-frontend:spacing-correction`; routes, proxy, and both
  health endpoints passed. The preserved acceptance database remained 221,184
  bytes with SHA-256
  `e4dc8e04cd49cbbd2ec683fb7f22346f87839f4ada223a4e9205d3799592bc88`,
  integrity `ok`, no foreign-key violations, and unchanged counts and stable
  ordered-row hashes.
- The normal frontend remains stopped and the normal backend retained its
  identity, start time, healthy status, and zero restart count. The active
  database remained byte-for-byte unchanged at 221,184 bytes, mtime_ns
  `1787540386457385549`, and SHA-256
  `9b5e14b5d04799f8972f4875fa66fc82f8601221b206dda18e69d8651c7a66bd`;
  integrity is `ok`, foreign keys are clean, and established logical counts
  remain unchanged.

# 2026-08-23 — Short mobile content-surface correction

- The remaining gray strip was not clearance padding: the PageFrame shell was
  transparent over the gray body, and its short card/container height ended
  before the fixed navigation. Below `sm`, the shell now forms a `100dvh`
  column flex layout with the container and card stretching through the
  available content region and a mobile-only card-color background.
- The existing 64px navigation height, one-time safe-area calculation, and
  16px Plan content gutter are unchanged. Long Plan content still determines
  document height normally; desktop shell/body colors and spacing are
  untouched.

# 2026-08-23 — Persistent mobile navigation acceptance and closeout

- Complete human acceptance passed for the fixed below-`sm` Now, Plan, and Find
  navigation; active-route return-to-top behavior; deep Plan restoration;
  browser history; Find layering, focus return, and targeting; safe-area-aware
  content accommodation; the corrected 64px zero-inset bar and 16px Plan
  gutter; and the short-page white content surface. Desktop navigation remains
  unchanged and nonsticky.
- Built normal image `gotime-frontend:latest` from accepted commit
  `5fbfda9e1169fd1f3e41ced3f09f929b64fece91`, verified its production bundle
  with `VITE_ENABLE_EXPERIMENTS=false`, and recreated only
  `gotime-frontend-1`. Frontend serving, `/now`, `/plan`, Plan API proxying,
  desktop header source, and the accepted mobile navigation and spacing bundle
  content passed smoke verification.
- The healthy normal backend retained image
  `d8aedab223dded275d35f30eb9717c23b7821d9e4dd6f5c94f6888ab384c7056`,
  start time `2026-08-24T02:50:36.992026018Z`, and restart count zero; it was
  not rebuilt, restarted, or recreated. The active database remained unchanged
  with SHA-256
  `9b5e14b5d04799f8972f4875fa66fc82f8601221b206dda18e69d8651c7a66bd`.
- Removed exactly acceptance containers
  `gotime-mobile-nav-acceptance-frontend` and
  `gotime-mobile-nav-acceptance-backend`, volume
  `gotime_mobile_nav_acceptance_data_8559604`, network
  `gotime_mobile_nav_acceptance_net_8559604`, and temporary directory
  `/tmp/gotime-mobile-nav-acceptance-8559604/`. Normal resources and unrelated
  Docker resources were preserved. No next increment was started.

# 2026-08-25 — Cross-route Recommendation targeting candidate

- Confirmed the existing persisted Recommendation contract already includes a
  stable nullable `task_id`; no backend or API-contract work was necessary.
  Added one content-width, dark-green **View task** button with a 44px minimum
  target to recommended Task cards only. The card remains nonclickable.
- Now marks the existing transient target as Recommendation-origin and pushes
  `/plan` once. Plan reuses the accepted Find reveal path for filter
  compatibility, phase/completed expansion, scroll, focus, temporary highlight,
  and saved position, then consumes the target. A missing Task stays on Plan
  with a dismissible, expiring **The recommended task is no longer available.**
  notice. No query-string target or title lookup was introduced.
- Focused Recommendation, Find, routing, and workspace coverage passed 28
  tests; the complete frontend suite passed all 129 tests; the production build
  with Experiments disabled passed; and `git diff --check` passed. Backend,
  schema, API, ADR, Recommendation ranking, and database files were unchanged.
- Because the normal frontend is source-bind-mounted, it was stopped before
  isolated acceptance preparation. The normal backend retained container
  identity, healthy status, original start time, and zero restarts. The active
  database remained 221,184 bytes with SHA-256
  `9b5e14b5d04799f8972f4875fa66fc82f8601221b206dda18e69d8651c7a66bd`.
- Left isolated project `gotime_recommendation_targeting_acceptance` running at
  `http://localhost:21173` with backend `http://localhost:21000`, containers
  `gotime-recommendation-targeting-acceptance-frontend` and
  `gotime-recommendation-targeting-acceptance-backend`, disposable volume
  `gotime_recommendation_targeting_acceptance_data_b14e2c9`, and network
  `gotime_recommendation_targeting_acceptance_net_b14e2c9`. Its verified backup
  baseline contains 49 Tasks and no Milestones, Decisions, or options;
  integrity is `ok` and foreign keys are clean. Neither container mounts or
  joins normal data/network resources. Human acceptance and deployment remain
  pending.

# 2026-08-25 — Cross-route Recommendation targeting closeout

- Complete human acceptance passed for the compact **View task** action,
  normal Now-to-Plan history and Back behavior, compatible and incompatible
  filters, active and completed Task reveal, focus and temporary highlighting,
  saved Plan position, one-time target consumption, and the missing-Task
  notice.
- Built normal image `gotime-frontend:latest` from accepted commit
  `ca97c32ee4a440694a5943b0a302900bece06a7a` with image SHA
  `a5dcac532fde263947bada386897e71645782854aedcff02b2c5c8d218d2a60a`
  and recreated only `gotime-frontend-1` with
  `VITE_ENABLE_EXPERIMENTS=false`. `/now`, `/plan`, Recommendation and Plan API
  proxy requests, live Recommendation-to-Plan Task identity, and the deployed
  targeting tests passed. Both experimental APIs returned 404.
- The normal backend was not rebuilt, restarted, or recreated. It retained
  image `d8aedab223dded275d35f30eb9717c23b7821d9e4dd6f5c94f6888ab384c7056`,
  start time `2026-08-24T02:50:36.992026018Z`, healthy status, zero restarts,
  and `GOTIME_ENABLE_EXPERIMENTS=false`.
- The active database remained byte-for-byte and logically unchanged at
  221,184 bytes with SHA-256
  `9b5e14b5d04799f8972f4875fa66fc82f8601221b206dda18e69d8651c7a66bd`;
  integrity remained `ok`, foreign keys remained clean, and all concise table
  counts matched the pre-deployment baseline.
- Removed exactly `gotime-recommendation-targeting-acceptance-frontend`,
  `gotime-recommendation-targeting-acceptance-backend`, volume
  `gotime_recommendation_targeting_acceptance_data_b14e2c9`, network
  `gotime_recommendation_targeting_acceptance_net_b14e2c9`, and temporary
  directory `/tmp/gotime-recommendation-targeting-acceptance-b14e2c9/`.
  No derived-attention or other feature work began.

# 2026-08-25 — Required subtasks and derived parent status candidate

- Began from clean closeout `de5ba863bfca686f2d1c32540899c2a3fd514b59`.
  Recorded the persistent hierarchy/manual-status architecture in ADR-0010.
  The migration is additive, transactional, and idempotent; it creates no
  relationships automatically and requires no active-data conversion.
- Added one-level same-phase required subtasks, user-controlled order,
  confirmed parent phase moves, attach/detach preservation, reversible derived
  status, visible confirmed manual overrides, dependency propagation, leaf-only
  phase counts, and parent-summary Recommendation exclusion.
- Plan reuses the Task editor for **Part of** and **Add subtask**. Groups are
  collapsed independently by session; filtering preserves parent context; Find
  and Recommendation targets reveal a child within its parent. No Decision
  readiness, evidence-link, contextual Recommendation, or family conversion
  work was started.
- A fresh verified SQLite backup was made before source edits. Focused backend
  hierarchy tests passed 6 tests and the complete backend suite passed 213.
  Focused frontend coverage passed 58 tests, the complete frontend suite passed
  132, and the production build passed.
- Backup `/tmp/gotime-required-subtasks-backup-20260825/gotime-pre-required-subtasks.db`
  is 221,184 bytes with SHA-256
  `4d9b9ee0b849bf1a11b47d722464cb7608c04b1c2cbcbdb1a18d82a44b89b908`,
  integrity `ok`, clean foreign keys, 49 Tasks, and no Milestones, Decisions,
  options, hierarchy rows, or overrides. Migration on disposable rehearsal
  volume `gotime_required_subtasks_rehearsal_data_c4a18d2` created the two
  empty tables and ordering index without changing logical counts; restoring
  the backup returned the disposable file to the exact backup checksum.
- Isolated acceptance project `gotime_required_subtasks_acceptance` is running
  at `http://localhost:22173` with backend `http://localhost:22000`, containers
  `gotime-required-subtasks-acceptance-frontend` and
  `gotime-required-subtasks-acceptance-backend`, volume
  `gotime_required_subtasks_acceptance_data_c4a18d2`, and network
  `gotime_required_subtasks_acceptance_net_c4a18d2`. Only those two containers
  join the network; only the backend mounts the disposable volume. Integrity,
  foreign keys, baseline counts, Plan, Recommendation, and proxy checks pass.
  Both experiment flags are disabled.
- The bind-mounted normal frontend remains stopped. The normal backend retains
  container identity `4d13c8380a8a7de1e6754b317ab5e7ef851937bb716922b60afa6453807bab6a`,
  its original start time, healthy status, and zero restarts. Active database
  SHA-256 remains
  `9b5e14b5d04799f8972f4875fa66fc82f8601221b206dda18e69d8651c7a66bd`.

# 2026-08-25 — Required-subtask consolidated UX correction

- Added a narrow `PUT /api/relocation-plan/tasks/{parent_task_id}/subtasks/order`
  mutation. It rejects duplicate IDs, requires the exact current child set,
  verifies the parent, performs one transactional CASE update, is a write-free
  no-op for an already-current order, and returns the updated Plan. No schema,
  migration, hierarchy, dependency, or derived-status semantics changed.
- Replaced the separate Show/Hide link with the count-aware progress/chevron
  button. Expanded subtasks now have bounded Move up/down actions with immediate
  persistence, disabled boundaries, preserved expansion/scroll state, and
  focus retention on the moved Task.
- Replaced the native **Part of** select with **This task is a subtask**, a
  searchable alphabetical phase-scoped eligible-parent picker, category/status
  context, selected-parent summary and Change action, and inline required-parent
  validation. Unchecking persists detachment through the existing full editor.
- Replaced candidate-introduced browser confirmations with one accessible
  React-Bootstrap modal using specific consequences and actions for conflicting
  parent status, manual completion/downstream unblocking, parent phase moves,
  and first-child derived-status changes. Cancel/Escape restore trigger focus;
  ordinary errors remain inline or in the established error path.
- Focused backend coverage passed 11 tests. Affected frontend coverage passed
  46 tests and the production build passed. Complete suites are intentionally
  deferred until final acceptance/closeout. Before replacing isolated
  containers, the preserved acceptance volume contained 52 Tasks, zero
  hierarchy/override rows, integrity `ok`, clean foreign keys, and Task row hash
  `25d7ca8b815869af610dd2026a9af885a57aebb5e1fce1fc60eab424b03f2a75`.
- Rebuilt and recreated only the isolated acceptance backend/frontend. Every
  count and stable row hash matched afterward; integrity remained `ok` and
  foreign keys clean. The SQLite file checksum changed from `7cb4c3bf...` to
  `98209210...` from the already-known no-op repository initialization write,
  with no logical mutation. The active database remained byte-for-byte at
  `9b5e14b5d04799f8972f4875fa66fc82f8601221b206dda18e69d8651c7a66bd`,
  and the normal backend retained its identity, health, start time, and zero
  restarts.

# 2026-08-25 — Required-subtask visual correction

- Replaced both phase and subtask inline chevron glyphs with one reusable SVG
  component. Its fixed 1.25rem nonshrinking box rotates without changing layout;
  the progress control remains inline-flex, count-aware, wrapping, and fully
  clickable with unchanged `aria-expanded` and session behavior.
- Scoped confirmation-modal titles to 1.25rem with normal line wrapping. Modal
  semantics, body copy, actions, dismissal, and focus restoration are unchanged.
- The 46 affected frontend tests and production build passed; complete suites
  were intentionally not run. Recreated only the isolated acceptance frontend.
  The backend identity stayed unchanged, and the acceptance database remained
  byte-for-byte at SHA-256 `d7d6d16d10f4b45a6395fbfb5d3f87c5ee563ede350fe2f631dfd3e7e69fee7d`
  with 52 Tasks, one hierarchy row, integrity `ok`, and clean foreign keys.

# 2026-08-25 — Required-subtask acceptance, deployment, and closeout

- Complete human acceptance passed for required-subtask hierarchy, derived and
  manual parent status, dependency behavior, targeting, editor/picker flows,
  atomic ordering, accessible confirmation modals, and the final chevron/title
  visual corrections. Accepted HEAD was
  `57f22235eb8f7cbf2b15660b026b0ab9dd103f8f` with a clean worktree.
- Verified the preserved 221,184-byte backup at
  `/tmp/gotime-required-subtasks-backup-20260825/gotime-pre-required-subtasks.db`
  with SHA-256
  `4d9b9ee0b849bf1a11b47d722464cb7608c04b1c2cbcbdb1a18d82a44b89b908`;
  its manifest remained intact with SHA-256
  `f3ca3656e3b3dd525ecb3b73e938c001172cdcd999471a43ff15fe6028a9c6e9`.
- Backend compilation passed; the complete backend suite passed 218 tests; the
  complete frontend suite passed 137 tests; the production frontend build and
  `git diff --check` passed.
- Rebuilt and recreated normal containers `gotime-backend-1` and
  `gotime-frontend-1` with both experiment flags explicitly false. Backend
  container `ab1c4d9615bc4807a430cee0c08e1c3bd695d31e3c3ab4137d440dfeca87fa9f`
  runs image `b21f6d6addafcf92d6d57f957f82f5d612823d956eb04fb0a577a39607494559`;
  frontend container `566d268f207e91fc0f082354250eafb331f74aae6288bb82e75b4466c1500393`
  runs image `7615e07177f8420a37e060615defe8b22e0ca93e5f1eeebaf5137bea5ba11fd5`.
- The active migration added `task_hierarchy` and
  `task_parent_status_overrides`, both with zero rows. Before/after counts and
  stable row hashes matched for every preexisting table: 49 Tasks, 76
  assignees, 50 category assignments, 45 dependencies, four phases, one plan,
  and zero Milestones, Decisions, or options. Integrity remained `ok`; foreign
  keys remained clean. Expected SQLite bytes changed from SHA-256
  `9b5e14b5d04799f8972f4875fa66fc82f8601221b206dda18e69d8651c7a66bd`
  to `2dbb364950d30009a0ff9b76dac91cec8dac5b65a870426faa282646afeb8531`;
  no logical content changed and no family relationship was created.
- `/now`, `/plan`, direct and proxied Plan APIs, Recommendation, and disabled
  experimental endpoints passed normal smoke verification. Complete automated
  coverage confirms parent summaries are excluded from Recommendations; no live
  hierarchy probe was created.
- Removed exactly acceptance containers
  `gotime-required-subtasks-acceptance-frontend` and
  `gotime-required-subtasks-acceptance-backend`, volume
  `gotime_required_subtasks_acceptance_data_c4a18d2`, network
  `gotime_required_subtasks_acceptance_net_c4a18d2`, and directory
  `/tmp/gotime-required-subtasks-acceptance-c4a18d2/`. Preserved the verified
  backup and manifest. Decision readiness, contextual Recommendation work, and
  family-data conversion were not started.
# 2026-08-25 — Decision preparation and advisory readiness candidate

- Began from clean closeout `adbc3b0d4f9ef664363c42bc6edfb7a044bd00af`.
- Recorded ADR-0011 for normalized preparation links, effective-status
  readiness, advisory confirmation, and hierarchy safeguards.
- Added Decision-editor plan-wide preparation selection, readiness/progress
  cards, session-collapsed work rows, and shared Plan Task targeting.
- Created a fresh SQLite online backup before edits; stopped the normal
  bind-mounted frontend; candidate code never used the active database.
- Corrected an acceptance-only blocking Plan-load failure: the disposable
  frontend omitted `VITE_API_PROXY_TARGET`, so its Vite proxy attempted
  localhost inside the container and returned 500 while the backend returned
  200 directly. Dockerized frontends now default to the Compose `backend`
  service; local non-container Vite development retains its localhost default.
- Refined the acceptance presentation without changing APIs or data: the exact
  shared fixed-box chevron now serves preparation progress, Milestones and
  Decisions start independently collapsed with versioned plan-scoped session
  state, compact collapsed summaries preserve readiness context, and Task
  targeting opens its containing controls before using the existing reveal.
  The Decision editor now shows compact removable selections and exposes a
  bounded candidate panel only during active nonempty search.
- Refined readiness terminology to **No preparation tasks** while preserving
  the stored enum and derivation. A compact accessible information control now
  explains all readiness badges through focus or click with Escape/outside
  dismissal and focus return; expanded empty Decisions prompt the user to add
  preparation Tasks.
- Compacted the Task editor dependency picker into independently collapsible
  phase groups using the shared fixed-box chevron. New Task editors start with
  every phase collapsed; edit sessions initially open phases containing saved
  dependencies. Phase headings report selected counts, and collapsing never
  clears selections.
- Dependency search temporarily derives visibility and expansion from matches
  without mutating the editor's local phase state. Clearing search restores the
  exact pre-search expansion set, including multiple open phases and selections
  that were filtered from view. No browser-session persistence, eligibility,
  ordering, validation, API, backend, schema, or data behavior changed.

# 2026-08-26 — Decision preparation readiness acceptance, deployment, and closeout

- Human acceptance passed for Decision preparation readiness and the final
  dependency-picker review. Accepted product candidate was
  `bab82c40f879ddca780241186bfeb2a944e5c524`; test-only commit
  `0afc4c3bb2d738860716c619e2ed766d57c63e5f` updated two stale collapsed-state
  interactions without changing production behavior.
- Focused frontend coverage passed 45 tests; the complete frontend suite passed
  144 tests; the production build and `git diff --check` passed. The complete
  backend suite passed 220 tests with pinned development dependencies, and
  backend compilation passed.
- Recreated and verified backup
  `/tmp/gotime-decision-preparation-backup-20260826/gotime-pre-decision-preparation.db`
  at SHA-256 `6642cbf28dcbaf1c569411468b4891dac698f011fb37d3859c229dcc084420d6`;
  manifest SHA-256 is
  `2b09098639ffa765996e89e90db1343daf989ab5c05fb145b1b06185f85ce538`.
  Isolated migration created one empty preparation table, preserved all prior
  stable hashes, and exact restore returned to the backup checksum.
- Rebuilt and recreated normal containers with Experiments explicitly false.
  Backend container `452240df2bb316c6ee9d37ca50e41f525a328650bf3217c0c9364f835d29ec87`
  runs image `305c28d1ef866146a2014ce3e761830c6787a802d82f045cb6a41d4a12d139e2`;
  frontend container `da08f557c19dd8396a5f1ef23bf0d8b4fdfcaff4e6efa2123500b8b809418f2a`
  runs image `0178ff7616bd95d9bef191c523c568093ca8b47b5a8ee59f57e9320df0fd8e05`.
  Both had zero restarts; backend health was healthy.
- The additive migration added `decision_preparation_tasks` with zero rows.
  Before/after counts and stable hashes matched for all preexisting tables: 49
  Tasks, 76 assignees, 50 category assignments, 45 dependencies, four phases,
  one plan, and zero Milestones, Decisions, options, hierarchy links, or parent
  overrides. Integrity remained `ok` and foreign keys clean. Expected SQLite
  bytes changed from SHA-256
  `2dbb364950d30009a0ff9b76dac91cec8dac5b65a870426faa282646afeb8531`
  to `da902f7617f983db404657bc22d410a435d4775bd02d1d68f706ddbfae60854c`.
- `/now`, `/plan`, direct and proxied Plan and Recommendation reads, readiness
  UI/API contracts, normal rendering, and disabled experimental endpoints
  passed without live probe records. No family-plan Decision or relationship
  was created.
- Removed exactly acceptance containers
  `gotime-decision-preparation-acceptance-frontend` and
  `gotime-decision-preparation-acceptance-backend`, volume
  `gotime_decision_preparation_acceptance_data_a11`, and network
  `gotime_decision_preparation_acceptance_net_a11`. The referenced temporary
  Compose directory was already absent after the environment interruption.
  Preserved the verified backup and manifest. Contextual Recommendations and
  later Increment 2 work were not started.

# 2026-08-27 — First family Milestone/Decision conversion rehearsal

- Began from clean, pushed closeout `84598c6c2554ef70a2629e93fb4b4052804dd6fc`.
  The active database was inspected read-only and matched SHA-256
  `09bf1f9c2453254c0319b58d1bd3beb59bc8c37f4701bdb6269d0b87749f9f7a`,
  integrity `ok`, no foreign-key violations, 49 Tasks, and zero Milestone,
  Decision, option, preparation, hierarchy, or override rows.
- The only plausible parent match was Task
  `reengage-with-tn-realtor-e71dd74d-01e4-4338-9a94-0570bec0f3d2`, **Reengage
  with TN realtor**, in `prepare` / **Prepare for the move**. No requested child
  had a plausible existing match. Housing is the existing `housing` identity;
  Anne and Joe are the established family/Housing pair.
- Added a narrow transactional, exact-ID, fingerprint-guarded conversion plus
  focused tests and conversion documentation. Tests cover exact target state,
  idempotence, unrelated-row preservation, derived readiness and contextual
  Recommendation tracing, partial-target rejection, and injected rollback.
- Copied the active database byte-for-byte into isolated volume
  `gotime_tennessee_home_conversion_acceptance_data_v1`, verified the checksum,
  and applied the conversion only there. The manifest is preserved at
  `/tmp/gotime-family-conversion-audit-20260827/conversion-manifest.json`.
  Counts became 53 Tasks, one Milestone, one Decision, three options, one
  preparation link, four hierarchy links, 48 dependencies, and zero overrides.
  Integrity and foreign keys passed; a rerun returned `unchanged`.
- Left isolated review running at `http://localhost:25173` with backend
  `http://localhost:25174`, Experiments enabled, and the accepted application
  images. Normal services, production flags, and the active family database
  were not changed.
- Corrected the candidate after review to explicitly clear the reused parent's
  temporary UI-test start date `2026-08-13` and due date `2026-09-01`. The
  parent retains High priority; all four children remain undated at neutral
  medium priority. The manifest names both date removals as approved mutations.
- Recreated the isolated database volume from a freshly checksum-verified copy
  of the unchanged active database, applied the corrected conversion, verified
  exact target relationships and stable baseline projection, and confirmed an
  unchanged rerun. Focused tests passed 3 tests and `git diff --check` passed.

# 2026-08-28 — Accepted planning production-boundary correction

- Confirmed the family conversion remains canonical at **List publicly**,
  **Seek builder offers directly**, and **Pursue both paths**, including the
  matching Milestone achievement description. No conversion IDs, logic, or
  isolated records changed.
- Audited the shared flags and made their narrow route set explicit. Accepted
  Milestone, Decision/readiness, preparation, hierarchy/derived-status, and
  contextual-Recommendation APIs and UI remain normal product behavior with
  both flags false. `/experiments`, `/api/recommendations/primary`, and
  `/api/experiments/moving-service-question` remain gated.
- Added focused false-flag regression tests while retaining existing true-flag
  experiment coverage. No new permanent feature flag was needed.
- Focused verification passed 66 backend and 67 frontend tests. Backend
  compilation and the production frontend build with
  `VITE_ENABLE_EXPERIMENTS=false` passed. The corrected isolated environment
  runs at ports 25173/25174 with both shared flags false; accepted Plan and
  contextual-Recommendation APIs return 200 while both direct and proxied
  prototype endpoints return 404.
- Replacing only the isolated containers preserved every logical count and
  stable row hash. SQLite startup changed the isolated file checksum from
  `f33aa79f83218fed3246133a639c232892bb8c7211e7b5b92aad8015ed076e1c`
  to `6bcd0da85377e0b482e3f4daeec258d9ecb62105032686849749a798f6445a93`;
  integrity remained `ok` and foreign keys remained clean.

# 2026-08-28 — First family conversion deployment and closeout

- Deployed accepted commit `a62cad8fbfdcbb4a1139fdc7629612c09340f28c`.
  Complete verification passed 234 backend and 154 frontend tests, backend
  compilation, the production frontend build with Experiments false, and
  `git diff --check`.
- Verified source SHA-256
  `09bf1f9c2453254c0319b58d1bd3beb59bc8c37f4701bdb6269d0b87749f9f7a`,
  integrity `ok`, clean foreign keys, exact source identities, counts, and
  stable hashes. The authoritative backup and evidence are preserved under
  `/home/joeshep/backups/gotime/20260828-first-family-conversion-closeout/`;
  checksum manifest SHA-256 is
  `a96a8d1be87c107d7b8afea3216b49e677f698d09d27da50d13ea0e981112fec`.
  The identical `/tmp/gotime-family-conversion-production-backup-20260828/`
  source remains temporarily available but is not authoritative.
- Exact restore to isolated volume
  `gotime_family_conversion_restore_rehearsal_20260828` reproduced the source
  checksum. A fresh Python 3.12 conversion rehearsal reproduced the accepted
  checksum `72008256c2bd3dd90dde4307f891fdc0e4cb01c7a425c4e6a9d625ba143fff67`,
  manifest, counts, and stable hashes.
- Stopped normal services to prevent concurrent writes, then transactionally
  applied the exact accepted conversion. The active idempotency rerun returned
  `unchanged` with the same byte checksum and logical hashes. After normal
  repository startup, SHA-256 was
  `f33aa79f83218fed3246133a639c232892bb8c7211e7b5b92aad8015ed076e1c`;
  integrity remained `ok`, foreign keys clean, and all accepted counts/hashes
  matched.
- Rebuilt normal services with `GOTIME_ENABLE_EXPERIMENTS=false`,
  `VITE_ENABLE_EXPERIMENTS=false`, and proxy
  `VITE_API_PROXY_TARGET=http://backend:8000`. Direct and proxied Plan and
  contextual Recommendation APIs returned 200; both prototype endpoints
  returned 404. `/now` and `/plan` served normally, and automated routing
  coverage confirmed `/experiments` uses the normal not-found experience.
- Removed only the port-25173/25174 review containers, volume
  `gotime_tennessee_home_conversion_acceptance_data_v1`, network
  `gotime_tennessee_home_conversion_acceptance_net_v1`, and temporary Compose
  file `/tmp/gotime-tennessee-home-conversion-acceptance.compose.yml`. No seed
  resource existed. No other family conversion, status mutation, option
  selection, AI call, research, or later increment began.
- Independently recalculated every durable artifact checksum, successfully
  verified the copied `checksums.sha256`, and compared source/durable trees by
  path, type, size, mode, and content with no missing, added, or changed file.
  Restore-rehearsal volume `gotime_family_conversion_restore_rehearsal_20260828`
  remains retained.

# 2026-08-27 — Contextual Decision-preparation Recommendation candidate

- Began from clean, pushed Decision-readiness closeout
  `86b19251eac467adcd482c915bc1a501168c5df1`. Reviewed Recommendation,
  readiness, hierarchy, dependency, activation, and targeting architecture.
- Recorded ADR-0012. The current Plan aggregate supplies every required fact,
  so this slice adds no database schema, migration, AI call, external research,
  or family-data conversion.
- Added the approved Recommendation hierarchy beside the canonical eligibility
  and ranking explanation in `docs/reasoning-engine.md`. The technical design
  and ADR link to that section; README intentionally retains the approved
  audience-facing visualization copy and links to the canonical explanation.
- Added structured Task/Decision Recommendation candidates and signals for
  ready Decisions, direct and parent-inherited preparation, and deep or
  branching dependency-frontier work. Resolved Decisions and inactive branches
  contribute nothing; multiple Decisions preserve every explanation without
  stacking rank influence. Existing priority, timing, urgency, eligibility,
  and stable ordering remain authoritative before contextual tie-breaking.
- Added consistent primary/upcoming Task and Decision cards, accessible compact
  multi-Decision disclosure, existing Task metadata, immediate recalculation,
  and transient reveal/focus/highlight targeting for existing Decision cards.
- Focused backend verification passed 44 tests and backend compilation. Focused
  frontend verification passed 17 tests across four files; the production
  frontend build passed. Complete suites are deferred to final human acceptance
  as authorized.
- Reserved isolated acceptance at `http://localhost:24173` with an isolated
  backend, frontend, database volume, and network and Experiments enabled.
  Normal services and the active family database remain out of scope and
  untouched. No family-plan Decision or preparation relationship is created.
- Consolidated the contextual-Recommendation frontend UX before acceptance:
  single and disclosed multi-Decision titles now reuse transient Decision
  targeting; redundant priority, absent-restriction, and repeated Why-now prose
  is suppressed while timing and relationship context remain. Milestones stack
  full width, and expanded Decision cards use a responsive one/two-column grid
  without stretching. Thirty focused frontend tests and the production build
  pass; complete suites remain deferred to human acceptance.

# 2026-08-27 — Contextual Recommendations acceptance, deployment, and closeout

- Human acceptance passed for contextual Decision-preparation Recommendations,
  targetable single/multiple Decision context, reduced explanatory prose, and
  the final responsive Milestone/Decision layout. The layout is accepted for
  this increment while remaining open to later refinement. README intentionally
  keeps the audience-facing Recommendation hierarchy image;
  `docs/reasoning-engine.md` is the canonical behavioral explanation.
- Accepted commits were `cda3f8d5a67961a45539e419df3d3ab69d3cfbb2`,
  `bb6410c41c5ff2671a599e925f93037d23428ace`,
  `9fb42da499b38e80a80c75e5e870199e191b94ab`, and
  `02c326477e43c301b78de45dec2be22f995957ac`. Complete backend verification
  passed 230 tests with pinned development dependencies and compilation passed;
  complete frontend verification passed 153 tests, the production build passed,
  and `git diff --check` passed. Initial environment-shape and concurrent-load
  attempts were corrected before deployment and clean reruns passed.
- Pre-deployment database SHA-256 was
  `da902f7617f983db404657bc22d410a435d4775bd02d1d68f706ddbfae60854c`;
  integrity was `ok` and foreign keys were clean. Counts were 49 Tasks, 76
  assignees, 50 category assignments, 45 dependencies, four phases, one plan,
  and zero Milestones, Decisions, options, preparation links, hierarchy links,
  or parent overrides.
- Rebuilt and recreated normal services with `GOTIME_ENABLE_EXPERIMENTS=false`,
  `VITE_ENABLE_EXPERIMENTS=false`, and
  `VITE_API_PROXY_TARGET=http://backend:8000`. Backend container
  `f524ad1b7d176cb99ee2db506f0641319e12126c3e54682bf82e1f4380dd1ccf`
  runs image `0ae4e164818003663ac0c4cbd0e83d9217c4962ee8b7c5efdc21f7469bd44268`;
  frontend container
  `d81ed09e4a184ad6634ab5753f40957f104c4495f36c754b167585b2ee58aec2`
  runs image `04516d74b28e0961f498cc5484423d030243120ec4721feff7aa753c07144c0d`.
  Both had zero restarts and backend health was healthy.
- Direct and proxied Plan/Recommendation responses matched; `/now`, `/plan`,
  frontend proxying, normal Task rendering, and disabled experimental API/UI
  boundaries passed without probe records. The active Plan retained 49 Tasks
  and zero Decisions or relationships.
- Post-startup SHA-256 was
  `09bf1f9c2453254c0319b58d1bd3beb59bc8c37f4701bdb6269d0b87749f9f7a`.
  Every logical count and stable row hash matched, integrity remained `ok`, and
  foreign keys remained clean. Exact byte comparison found only SQLite header
  bytes 28 and 96 changed: the change counter and version-valid-for values
  advanced from 117 to 118. Running the accepted repository initializer against
  a byte-for-byte pre-deployment copy produced the identical post-startup hash,
  proving a no-row/no-schema initialization transaction—not a migration or live
  data mutation—caused the two-byte write.
- Stable hashes remained: plans
  `2c2620d61df783578e34379c44863b0ab43678a69076dc48e0494ab9d4bb888a`,
  phases `77e694dd42fa94fb15d3fb75f452ff37aab2fb590f2d317e68e24c3ea8130340`,
  Tasks `f25a1c68a3070611f22b2d44eb5a59b7148ece17901d21c72c7d82e27806cc21`,
  assignees `f48e530c451580111b46d897df93106639159180de737024667389e133429815`,
  categories `11133af06a50d2861d67f7b6da27a4c7899ea529d3b0690d761d375df97c1c68`,
  and dependencies
  `bbf459be9ccffd21ba2ccc078943726bebff1923b835c73a0ec3b8a9f26eb5c1`.
  Every empty Milestone/Decision/relationship table retained the canonical empty
  hash `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`.
- Removed exactly acceptance containers
  `gotime-contextual-recommendations-acceptance-frontend` and
  `gotime-contextual-recommendations-acceptance-backend`, volume
  `gotime_contextual_recommendations_acceptance_data_c12`, network
  `gotime_contextual_recommendations_acceptance_net_c12`, Compose file
  `/tmp/gotime-contextual-recommendations-acceptance.compose.yml`, and seed
  configuration `/tmp/seed-gotime-contextual-recommendations.sh`. No later
  Increment 2 or AI-assisted work began.

# 2026-08-28 — Deterministic Recommendation-ranking calibration candidate

- Began the focused deterministic Recommendation-ranking calibration from clean
  closeout lineage `255bee582c136a3e283773a3c884186a802d2dae`. No schema,
  family-data, normal-service, or production-configuration change was required.
- Implemented eligibility-first ranking, viewer-local Recommendation evaluation
  dates, protected overdue/due-today pressure, dependency/parent deadline
  propagation, parent/child Recommendation holds, bounded actual-unlock,
  readiness, momentum, Decision-context, and transitional-priority signals,
  and concise two-reason explanations. Task UI language now says **Do not
  recommend before**, **Due by**, and **Recommendations begin**.
- Focused backend verification passed 45 tests with pinned dependencies and
  compilation passed. Focused frontend verification passed 63 tests, including
  the viewer-local-midnight refetch regression. The false-flag production build passed and
  `git diff --check` passed.
- Recorded the pre-calibration copied-family ordering as **Wash windows (test)**,
  **Test task with Dependency**, then **Decide how long APES should continue
  working in Tennessee before moving**. The isolated candidate orders **Test
  task with Dependency**, **Decide how long APES should continue working in
  Tennessee before moving**, then **Contact the realtor**. The disappearance of
  undated **Wash windows (test)** from the bounded upcoming list is specifically
  caused by demoting its legacy Critical priority below date pressure, momentum,
  actual unlocks, and Decision preparation.
- Created a byte-identical active-database copy in volume
  `gotime_ranking_calibration_acceptance_data_20260828`; source and copy checksum
  were `f33aa79f83218fed3246133a639c232892bb8c7211e7b5b92aad8015ed076e1c`
  before isolated startup. Post-startup counts remain 53 Tasks, one Milestone,
  one Decision, three options, one preparation link, four hierarchy links, 48
  dependencies, 85 assignee assignments, 54 category assignments, and zero
  overrides. Integrity is `ok`, foreign keys are clean, and all stable row hashes
  match the active source.
- Isolated acceptance is running at `http://localhost:26173` and backend
  `http://localhost:26174`, with both experiment flags false. Normal services
  and the active database were not mutated or restarted.
- Consolidated acceptance correction: Recommendation cards suppress a
  preparation sentence only when the same structured **Helps prepare** control
  is rendered; compact surfaces retain the reason. The Task form gives
  Assignees its own row and groups two equal desktop timing columns in an
  accessible **Recommendation timing (optional)** fieldset that stacks below
  the large breakpoint.
- Applied the approved copy-only correction to Milestone
  `put-tennessee-home-on-market-2027` in the disposable acceptance database.
  Its checksum changed from
  `6bcd0da85377e0b482e3f4daeec258d9ecb62105032686849749a798f6445a93`
  to `496eba140d5684a6458efebdddf5ccc1ff7da9f810cca236b0d3b794bd374df5`.
  Counts are identical; only the `milestones` stable hash changed, from
  `91f6ceed8e607ce4c9f610bc9adcd7da6cc282d0e7e8d63e2dfdf9949b54a5e2`
  to `c4a0f477b90345184d2668da3ddfd0aa7926a3991f99b88fca91403d28fe96fa`.
  All other stable hashes are identical, integrity is `ok`, foreign keys are
  clean, and the immediate rerun reported `unchanged`. The acceptance manifest
  is `/tmp/gotime-tennessee-milestone-description-v2-acceptance.json`.
  Restarting the unchanged isolated backend advanced SQLite bookkeeping bytes,
  so the currently running disposable copy checksum is
  `823820ffcedd4265c1a46c01502b63dc222d2698751c7cb3a37549da739dc97f`;
  its counts and stable hashes remain exactly the verified post-correction
  values.

# 2026-08-29 — Existing-Task edit return correction

- Added a focused Plan-navigation correction from accepted lineage
  `9c4a9b1fa60d01abf1f00bd01e7e79c5b950b338`. Existing-Task Save now resolves
  the Task from the returned Plan, reveals its current phase, Completed section,
  and parent group, then restores its Edit focus and a temporary highlight.
  Scrolling is centered only when needed and respects reduced motion.
- Cancel restores the original scroll position and Edit control. Failed
  validation or persistence retains the editor and draft.
  A saved Task hidden by the active category filter leaves that filter intact
  and presents **Task saved but hidden by the current filter.** with a focused
  **Show task** action that reuses the established Task targeting path.
- Focused frontend verification passed 87 tests across seven affected files.
  The production frontend build with `VITE_ENABLE_EXPERIMENTS=false` and
  `git diff --check` passed.
- Rebuilt and recreated only the isolated frontend at
  `http://localhost:26173` with `VITE_ENABLE_EXPERIMENTS=false` and proxy target
  `http://backend:8000`. Backend container
  `478228de8c731a24b42a10cd19f2cd23f2434b1faf92965a64cb37d3623feec1`
  retained its original start time and zero restarts. The copied database
  checksum remained
  `330d21cb17ea71952291d1ae5e424c35dbcf2be8bb4cb24a5451239e9b002eae`.

# 2026-08-29 — Return-to-Task highlight correction

- Clarified the existing Task-card treatment as a location/orientation cue.
  Successful Save and Cancel now show the same full return border for three
  seconds. It then fades for 350ms without affecting layout; reduced-motion
  viewers receive the same three-second static cue followed by immediate
  removal. Failed editors remain open and receive no highlight.
- Kept the established `is-found` targeting boundary for Task, Finder,
  Recommendation, and parent navigation. The separate future possibility of
  highlighting the changed field/value after editing is recorded in the
  Parking Lot and was not implemented.
- Focused frontend verification passed 98 tests across eight affected files.
  The production build with `VITE_ENABLE_EXPERIMENTS=false` and
  `git diff --check` passed.
- Recreated only the isolated frontend at `http://localhost:26173`. Frontend
  container `55bae2c5be15822f14d9721ecd85e3b4f1628f4e9e1280390bad9ba79f0c00aa`
  runs image
  `06cb030bc535e9cfedc46970ea3bf3d53efbea603def64c82fa86ac79956f832`.
  Backend container
  `478228de8c731a24b42a10cd19f2cd23f2434b1faf92965a64cb37d3623feec1`
  retained its original start time and zero restarts. The copied database
  checksum remained
  `00c794a198f124436d968be1e2e2c9c63a42e57836ed5f8b79e2a2c70d6ea7fe`.
