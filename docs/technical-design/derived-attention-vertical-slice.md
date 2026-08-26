# Derived-Attention Vertical Slice Technical Design

## Status and boundary

This document records the approved technical design for the
smallest end-to-end slice demonstrated by the
[home-sale strategy reference scenario](../reference-scenarios/home-sale-strategy.md).
ADR-0008 approves the Milestone and Decision foundation for Increment 1.

Detailed database tables, Pydantic schemas, endpoint signatures, components,
and migration code remain implementation concerns bounded by this design. Its
named items are domain concepts and relationships unless explicitly described
otherwise.

The governing principle is:

> GoTime may derive, recommend, explain, and warn, but the user retains final
> authority.

The human-facing reference Milestone is **Start selling our home**. It is
achieved only when the buyer-seeking channels selected by the family—a public
listing, builder or off-market outreach, or both—are genuinely active.
**Our home is under contract** is a second real-world Milestone. The eventual
employment-notice/PTO work depends on that second Milestone, while the
farewell-party Decision has no hard dependency on starting the sale.

## Current implementation audit

### Persistence and migration

The singleton relocation plan currently uses Python's standard-library SQLite
support behind `SQLiteRelocationPlanRepository`. Docker Compose mounts the
named `gotime_data` volume at `/app/data`; the backend defaults to
`/app/data/gotime.db` in that container.

The active normalized database has six application tables:

* `relocation_plans`: stable plan ID and title.
* `phases`: plan, title, nonnegative position, and unique position within the
  plan.
* `tasks`: plan and phase references, title, nullable description, bounded
  status, nullable start/due dates, and bounded priority.
* `task_categories`: a composite task/category key with the six-category check
  constraint and cascading task deletion.
* `task_assignees`: ordered names, unique by position and name within a Task,
  with cascading task deletion.
* `task_dependencies`: ordered direct Task-to-Task prerequisite relationships,
  with unique relationship and position, no self-reference, and cascading
  deletion only from the dependent side.

Foreign keys are enabled for repository connections. Primary keys and unique
constraints create SQLite-managed indexes; there are no explicit application
`CREATE INDEX` statements. The active database passed read-only integrity and
foreign-key checks during this audit.

There is no migration-version table or external migration framework. Repository
construction creates missing tables, detects the legacy scalar `tasks.category`
column, and, when present, runs a transactional `BEGIN IMMEDIATE` table rebuild.
That migration copies Task fields, assignees, and dependencies, translates the
legacy Administrative category to Logistics, normalizes category assignments,
and is idempotent because the legacy column is absent afterward. Tests build a
legacy database in isolation, verify preservation, and reopen it to prove
idempotence.

This convention is adequate for a bounded migration, but the new slice is
broader than the category change. It needs explicit preflight recognition of
old, partially migrated, and current states; one transaction for each schema or
family-data conversion; preservation assertions; and fail-closed handling of
unexpected relationships.

### Task behavior and contracts

The implemented Task domain object and response schema contain ID, title,
optional description, one phase, zero or more ordered categories, status,
assignees, optional dates, stored priority, direct dependency IDs, and derived
blocked state. Status is `not_started`, `in_progress`, or `completed`.

Create requests may use defaults for several Task fields, but `categories` is
required. Full-replacement Task updates require every replaceable property,
including explicit nulls for nullable values. A narrow status request changes
only status. Domain validation rejects blank titles, invalid timing, duplicate
categories/assignees/dependencies, unknown enum values, and self-dependency.
Repository validation rejects missing phases or Tasks, new completed
dependencies, and cycles. Existing completed dependencies may be retained or
removed during editing, but not re-added after removal.

Blocked state is calculated on read. An incomplete Task is blocked when any
direct dependency is incomplete. Completing or reopening a dependency retains
the stored edge and recalculates blocking. A completed Task is never reported
as blocked. Parent Tasks, subtasks, Milestones, Decisions, readiness,
conditional associations, and activation do not exist today.

### Recommendation behavior

The stored-plan Recommendation endpoint loads the complete plan and calls a
pure deterministic function. It excludes completed, blocked, and future-start
Tasks. Eligible Tasks are compared lexicographically by:

1. stored Critical/High/Medium/Low priority;
2. overdue, dated, and undated grouping;
3. due date;
4. In progress before Not started;
5. number of incomplete Tasks directly unblocked by this Task alone;
6. phase position; and
7. stable Task ID.

The response identifies one Task and phase, provides structured ranking
factors, lists directly unblocked Task IDs, and supplies `why` plus `why_now`
text. Empty, complete, and blocked-or-future plans receive distinct
no-actionable explanations. Successful plan mutations cause the frontend to
refetch the Recommendation.

The engine does not understand parent/leaf context, Decision leverage,
Milestone contribution, advisory readiness, activation, or inactive work. It
also still elevates stored priority, which the derived-attention direction
intends to demote without deleting existing data.

### Routes and frontend behavior

The fixed relocation API currently exposes plan retrieval, Recommendation
retrieval, Task creation, full Task replacement, and narrow Task-status change.
All mutations return the refreshed plan aggregate. There are no routes or
request/response schemas for Milestones, Decisions, options, hierarchy,
activation, or relationship previews.

The React experience loads that aggregate and uses one reusable editor for Task
creation and editing. It supports phase, categories, status, assignee names,
dates, priority, and searchable phase-grouped dependencies. Task cards show
status controls, Edit, priority/category labels, assignees, due date,
description, blocked state, and dependency titles.

The plan groups Tasks by ordered phase. Active Tasks appear in the phase body;
completed Tasks appear in collapsed per-phase `Completed (n)` sections. A
local category dropdown applies OR filtering and hides empty phases. The
plan-wide title finder ignores that category filter while searching, clears an
incompatible filter only on navigation, expands completed sections when
needed, and focuses/highlights the result. None of these views has an inactive
dimension today.

The existing interaction patterns provide useful extension points: aggregate
refresh after mutation, narrow state-change actions, the shared editor/card
presentation, local reveal/filter state, finder-assisted reveal, success/error
alerts, and controlled completed sections. The first slice does not need a
separate administration application.

### Existing tests to extend

`backend/tests/test_relocation_plan_repository.py` already covers
reconstruction, bounded fields, categories, dependencies, blocking/reopening,
completed-dependency rules, cycles with rollback, SQLite constraints, legacy
migration preservation, and idempotent reopen.
`backend/tests/test_relocation_plan_endpoint.py` covers complete replacement,
required properties, explicit clearing, status changes, validation errors, and
response reconstruction.
`backend/tests/test_relocation_plan_recommendation.py` covers every current
eligibility and ranking factor, explanations, no-actionable states, persisted
API behavior, and dependency-chain completion/reopening.

`frontend/src/RelocationPlan.test.tsx` covers editor lifecycle and complete
writes, Task cards, dependency selection, blocked state, status changes,
completed sections, category filtering, the plan-wide finder/reveal behavior,
responsive hooks, and errors. `frontend/src/RelocationPlanExperience.test.tsx`
covers Recommendation presentation, mutation refresh, and stale-response
protection. These are the appropriate suites to extend; `App.test.tsx` should
need only integration/layout adjustments, and the unrelated employment and
frozen AI-experiment suites should remain behaviorally unchanged.

## Read-only audit of the existing milestone-like Task

The active database contains exactly one Task titled `Put current home on the
market`. It is Not started. It has one direct prerequisite and three direct
dependents. The following classifications are provisional product semantics;
the stored database contains only undifferentiated Task dependency edges.

| Stored relationship | Provisional classification | Design treatment |
| --- | --- | --- |
| `Put current home on the market` depends on `Reengage with TN realtor` | Relationship should instead connect through the new Decision | Realtor work informs `Select the initial home-sale strategy`; the Decision and chosen work lead toward **Start selling our home**. Realtor completion alone is not a universal prerequisite for every conceivable buyer-seeking channel. |
| `Decide whether to have a farewell party` depends on `Put current home on the market` | Timing or sequencing guidance | Preserve the intent as a reviewed timing/support relationship, not an automatic hard block, unless the user confirms otherwise. |
| `Give 30 days’ notice / account for remaining PTO` depends on `Put current home on the market` | Unclear and requiring user review | The stored titles and empty descriptions do not establish why employment notice depends on starting the home sale. Migration must stop rather than guess. |
| `Reach home-sale contract milestone` depends on `Put current home on the market` | Genuine hard prerequisite | Reaching a sale contract requires a buyer-seeking channel to be active. Translate this to a reviewed relationship from **Start selling our home** to the downstream work/outcome. |

No current direct relationship was confidently classified as merely supporting
work. No relationship should be translated automatically from this table
without user approval immediately before the family-data migration.

## Recommended minimum domain and persistence approach

### Summary

Persist only the concepts whose state must survive reloads and whose semantics
cannot be reconstructed safely from the current Task graph:

* Milestones and their user-confirmed state.
* Decisions and their options/user selection.
* One-level parent/child Task relationships.
* Work-informs-Decision relationships.
* Task-to-option conditional associations.
* User activation exceptions.
* The minimum Decision/work-to-Milestone relationships needed for explanation
  and reviewed downstream behavior.

Derive parent status, Decision readiness, default activation, blocking,
attention eligibility, counts, and explanation factors. Do not persist those
derived results as competing sources of truth. Evidence requirements, hard
constraints, preferences, and evidence conclusions remain bounded Decision
information or Task notes in this slice; they do not require separate database
entities.

### Milestones

Three alternatives were considered:

1. **Treat a Milestone as an ordinary Task.** This reuses current storage but
   conflates real-world achievement with work completion, exposes irrelevant
   Task fields, and permits supporting work to assert achievement indirectly.
2. **Add a Task kind and specialize milestone behavior.** This preserves one
   collection but introduces type-dependent Task validation, status, editor,
   dependency, and recommendation rules throughout the current contract.
3. **Use a small independent Milestone domain concept.** This adds one durable
   concept but cleanly represents a target outcome, explicit confirmation, and
   cross-cutting relationships without pretending the outcome is executable
   work.

Recommend option 3. The first slice requires:

* a stable identity and human-facing name—**Start selling our home**;
* optional descriptive context;
* a target timing value that can express a human-readable window without false
  precision;
* timing intent identified as a target rather than a commitment;
* Pending or Achieved state;
* explicit user confirmation (and user correction/reopening) of achievement;
* association with the controlling Decision; and
* reviewed relationships to work that supports, is timed around, or truly
  depends on the Milestone.

For this slice, Milestone timing uses optional earliest and latest target dates.
Equal dates are exact, different dates are a bounded window, earliest only is
open-ended timing such as after New Year, and neither means timing is unknown.
A latest-only or reversed window is invalid. These dates are planning guidance,
not Task start dates or hard deadlines. A separate committed-timing field is
unnecessary now.

Achievement is a user-recorded real-world fact, not a consequence of Task
status. GoTime may recommend confirmation when selected channels appear ready,
but only the user changes Pending to Achieved.

### Decisions and options

A Decision minimally has stable identity, prompt/title, bounded supporting
information, credible options, Unresolved or Resolved state, the selected
option when resolved, and user-visible advisory readiness. The home-sale
Decision is **Select the initial home-sale strategy**.

Two option representations were considered:

1. **Allow multiple simultaneously selected options.** This can compose
   arbitrary channels but complicates what “resolved” means, revision diffs,
   option-specific notes, and activation combinations.
2. **Use exactly one selected option and include a combined option.** The
   credible set can include “Builder outreach and public listing in parallel,”
   keeping selection and revision singular.

Recommend option 2 for the first slice. It faithfully represents the scenario
with less state and a simpler audit trail. Arbitrary multi-selection can be
reconsidered only if real plans demonstrate combinations that cannot be named
responsibly as options.

The engine derives readiness as **Ready for consideration** only when all work
explicitly linked as informing the Decision is complete. Otherwise it reports
**Gathering information** and identifies the incomplete work. Readiness is
advisory: selecting an option while information remains incomplete requires a
clear warning and explicit user confirmation, not a server-side prohibition.
The engine never chooses an option.

A later revision uses the same user-owned selection action, preceded by an
affected-work preview. The previous selection and rationale should eventually
remain inspectable, but detailed Decision history is deferred from the first
slice. At minimum, no revision may silently deactivate In progress work or
alter Completed work.

### Parent Tasks and required subtasks

Represent hierarchy with one optional direct parent relationship from a Task
to another Task in the same plan. Enforce one level: a parent cannot itself
have a parent, and a child cannot have children. Every child is required in the
first slice. Optional children, weights, rollups, and deeper nesting are
deferred.

An outcome-oriented parent with children is context, not a Recommendation
candidate. Its status is calculated from child status:

* Not started when no child has begun.
* In progress when at least one child has begun and at least one remains
  incomplete.
* Completed when every child is Completed.

Automatic status remains child-authoritative: adding a required child or
reopening a child recalculates the parent, completing the last child completes
it, and a dependency pointing to the parent evaluates that effective status.
The implemented first slice also supports a user-confirmed manual override.
A conflicting direct status change warns and may be confirmed; the override is
visible, survives child changes, and is removed only through **Return to
automatic status**. This approved authority boundary supersedes the earlier
proposal to defer direct-parent overrides.

The difficult case is reopening or extending a completed parent after a
dependent Task has begun. The current engine would re-block every incomplete
dependent while leaving its progress status unchanged, and would leave a
Completed dependent as history. Preserve that deterministic behavior, but show
the affected downstream Tasks and require confirmation before the user reopens
a child or adds required work. Never silently roll back another Task's status.
Manually completing a parent warns that downstream work may become unblocked.

Use ordinary Task dependencies to sequence leaf work. In the reference
scenario, those relationships make `Contact the realtor` the first actionable
leaf rather than inventing a subtask-position ranking rule.

### Evidence and advisory readiness

Do not add an Evidence database entity in this slice. Decision information or
notes can describe expected evidence and conclusions; ordinary Tasks record the
work needed to obtain it.

Add only the semantic relationship **this Task informs this Decision**. Link
the outcome-oriented parent when all of its required children collectively
produce the evidence. A standalone Task may be linked directly when it has no
children. Avoid linking both parent and children for the same evidence outcome,
which would double-count readiness.

Readiness is derived from linked work's effective status. All linked work
complete means Ready for consideration. Any linked work incomplete means
Gathering information, with the incomplete titles available for explanation.
Newly discovered research can be added and linked, returning readiness to
Gathering information. The user can still select an option after acknowledging
the incomplete-evidence warning.

Do not record the family's actual minimum acceptable proceeds in fixtures or
public documentation. For the first slice, a private Decision note can state
that a minimum-net-proceeds constraint exists without exposing its value.

### Conditional activation

Three alternatives were considered:

1. **Persist one mutable active boolean per Task.** Simple reads, but selection
   changes would overwrite why a Task is active and make revision/manual
   exceptions hard to explain.
2. **Derive activation solely from the current selected option.** Preserves
   provenance but cannot retain work manually when circumstances differ or
   protect In progress work during revision.
3. **Derive default activation from option associations plus a small explicit
   user override.** Preserves provenance and supports exceptions without
   duplicating progress status.

Recommend option 3. A Task with no conditional association is active by
default. A conditional Task is active when its associated option is selected.
The same Task may be associated with more than one option when it is genuinely
shared. A persisted user “keep active” override may make it active regardless
of the selected option. Expose the resulting activation state in plan reads,
but do not store that derived result as an independent truth.

When the Decision is unresolved, its conditional branches are inactive. When
the user selects or revises an option, GoTime calculates the proposed active
set and presents the delta before applying it. Not started Tasks that belong
only to the old option may become inactive after that reviewed change. In
progress Tasks require an explicit keep-active or deactivate choice; there is
no silent default. Completed Tasks retain Completed status and remain available
as history even if their branch is now inactive. Manual activation records an
explicit override rather than changing status or option membership.

Inactive work is hidden from ordinary phase lists and excluded from active and
completed counts, attention-state evaluation, blocking influence on active
work, and Recommendations. A plan-level **Show inactive work** control reveals
it with a clear Inactive label. The title finder remains plan-wide: inactive
results are labeled, and selecting one enables the reveal before navigating,
while preserving the existing category-filter behavior where compatible.

Dependencies crossing activation boundaries need a fail-safe rule. An active
Task with an incomplete inactive prerequisite is not actionable; GoTime should
surface the inconsistency and offer review, never ignore the dependency and
make the Task appear ready. Option selection and manual activation should warn
about such crossings before commit.

### Milestone relationships

The first slice needs only enough relationship meaning to explain progress and
translate the reviewed legacy graph:

* a Decision advances or controls a Milestone;
* work supports a Milestone, is timed around it, or depends on its achievement;
  and
* option-associated work reaches the Milestone through its controlling
  Decision.

These relationship kinds need not become separate domain entities. They can be
bounded relationship semantics. A generic graph engine is unnecessary.

## Deterministic Recommendation design

The slice adds a derived-attention path without deleting stored priority or
changing legacy behavior for unrelated work.

Evaluate in this order:

1. Derive parent status from required leaf statuses.
2. Derive Decision readiness from linked evidence-producing work.
3. Derive effective activation from conditional associations, the selected
   option, and user keep-active overrides.
4. Build candidates from active leaf or standalone Tasks that are incomplete,
   not blocked by an incomplete dependency, and not before a genuine
   user-supplied eligibility date. Parent Tasks and inactive Tasks are not
   candidates.
5. Give an actionable evidence-producing candidate a derived Do now reason
   when it advances an unresolved consequential Decision connected to a
   pending Milestone. Within equivalent derived candidates, prefer In progress,
   real timing urgency, direct unblocking leverage, phase order, and stable ID.
   Do not use stored priority to establish this derived reason.
6. After option selection, give actionable Tasks in active selected branches
   their Decision and Milestone context and choose the next leaf using the same
   deterministic tie-breaks.
7. If no derived-attention candidate exists, retain the current Recommendation
   comparator as a compatibility fallback for unrelated Tasks. Existing
   priority data remains preserved and continues to affect only that fallback
   until the broader attention baseline is approved.

For the reference scenario, leaf dependencies make `Contact the realtor` the
first available evidence-producing action. The parent `Reengage with the
realtor` is not eligible because it has children. The eventual explanation
should read like:

> **Do now: Contact the realtor**
>
> Part of: Reengage with the realtor
>
> This work will provide market evidence needed to select the initial
> home-sale strategy and determine which work should proceed toward Start
> selling our home.

As children progress, the parent becomes In progress. When every required
child is complete, the parent becomes Completed and the Decision becomes Ready
for consideration. If linked evidence work remains incomplete, explain:

> You can select a home-sale strategy now, but the expected market evidence is
> incomplete: [work titles]. Review this gap before continuing.

That message warns; it does not disable selection. Once the user selects an
option, recompute activation and recommend only active leaf work:

> **Do now: [next active leaf action]**
>
> This work is part of the selected [strategy name] approach and advances Start
> selling our home.

Inactive work is excluded because it does not currently belong to the active
plan, not because it is completed or Not started. Completion of all supporting
work may produce:

> The selected buyer-seeking channels may now be active. Confirm whether Start
> selling our home has been achieved.

Only the user's confirmation changes the Milestone state.

The main product risk is coexistence with the legacy priority-first fallback.
For the acceptance scenario, a derived Do now candidate must take precedence
over fallback candidates. Before implementation, the user should approve that
bounded precedence and the test fixtures should include unrelated urgent work
to expose surprising interactions.

## API and interface boundaries

### API behavior

Extend the existing fixed-plan aggregate and mutation style rather than
creating a generic project-management API. The first slice needs behavior for:

* retrieving Milestones, Decisions/options, enriched Tasks, derived readiness,
  derived activation, hierarchy, and explanation context with the plan;
* creating and fully editing a Milestone's name, context, and target window;
* explicitly marking a Milestone Achieved or returning it to Pending through a
  narrow state action;
* creating and fully editing a Decision and its ordered credible options;
* previewing and then selecting or revising one option, including the
  incomplete-evidence warning and affected-work activation delta;
* creating/editing a Task with an optional parent, optional informs-Decision
  link, optional option associations, and optional keep-active override;
* changing leaf status through the existing narrow status pattern while
  returning recalculated parent/readiness/blocking state; and
* returning a Recommendation with parent, Decision, Milestone, activation, and
  advisory-warning context.

The design does not prescribe endpoint paths or Pydantic field layouts. It does
require explicit full-replacement semantics wherever an aggregate definition
is replaced, narrow operations for consequential state transitions, validation
of every referenced ID, and transactional preview/commit protection against a
stale Decision revision.

### Interface behavior

Add compact Milestone and Decision cards above the phase list, near the current
Recommendation and plan heading. Reuse the existing card, form, notice, and
narrow-action patterns rather than introducing separate administration screens.

The Milestone card shows **Start selling our home**, its open-ended target
window, Pending/Achieved state, related Decision, and an explicit
achievement action with confirmation. The Decision card shows its prompt, options,
Gathering information/Ready for consideration advisory state, incomplete linked
work, selected option, and select/revise action. A warning does not disable the
user's confirmation.

Extend the Task editor only with bounded relationship controls: parent Task,
Decision informed, conditional option associations, and manual keep-active.
Do not add advanced hierarchy management. A parent card nests its one-level
children or otherwise presents them as a clearly related group; its status is
read-only/derived. Leaf cards retain current status controls. Recommendation
presentation adds `Part of`, Decision, and Milestone explanation context.

Add **Show inactive work** above the phase list, independent of category
filtering. Inactive cards use the normal Task presentation plus an Inactive
label and activation explanation. Ordinary phase emptiness and `Completed (n)`
counts consider only active work. The finder continues searching the whole
plan, labels inactive results, enables Show inactive work when navigating to
one, and then uses the established reveal/focus/highlight behavior.

Decision revision first shows affected active Tasks. The user chooses which In
progress Tasks remain active; Completed work is untouched. The commit action is
disabled until every In progress deactivation has an explicit choice.

## Migration and compatibility design

### Treatment of `Put current home on the market`

Convert its conceptual role to the Milestone **Start selling our home**. Do not
retain a duplicate action Task. Recommend preserving the existing stable ID
value as the Milestone's identifier in its new type-specific namespace. That
provides a direct audit trail without a permanent mapping entity; migration
tests and logs should explicitly assert that the source Task ID became the
Milestone ID.

The source Task's Task-only properties do not automatically define Milestone
meaning. The migration must set the approved human name, Pending state, target
window, and controlling Decision explicitly. Actual public-listing and
builder-outreach actions belong to conditional branches, not to a shadow copy
of the old Task.

Before conversion, review every direct relationship again against the then-
current database:

* replace the realtor prerequisite with work-informs-Decision plus
  Decision-to-Milestone relationships;
* translate the contract relationship as a genuine dependency on Milestone
  achievement;
* translate the farewell relationship only as approved timing/support meaning;
* stop for user direction on notice/PTO or any other unclear edge; and
* fail closed if the titles, IDs, counts, or relationships differ from the
  approved migration fixture.

All unrelated Task IDs, fields, assignees, dependencies, categories, statuses,
phase placement, and ordering must remain byte-for-byte or semantically equal
as appropriate. New realtor subtasks and conditional branches are approved
family-plan additions, not facts to infer from the old dependency graph; their
exact content must be reviewed separately before migration.

### Safe migration sequence

Use the repository's transactional, idempotent migration convention but add a
clear schema-state discriminator rather than relying on destructive trial and
error. Separate additive schema support from the later family-data conversion.
The conversion transaction must either produce one Milestone and no duplicate
source Task with every reviewed relationship represented, or roll back fully.

Immediately before any eventual schema or family-data migration:

1. Quiesce writes or use SQLite's backup API to create a fresh verified backup
   outside Git.
2. Record checksum, integrity/foreign-key checks, schema, counts, application
   commit, and the approved relationship snapshot.
3. Restore that backup into a new isolated Docker volume.
4. Run the proposed migration and current application only against the isolated
   volume.
5. Verify preservation, idempotent reopen, API behavior, Recommendations, the
   full acceptance walkthrough, and a documented restore back to the pre-change
   state.
6. Only after review, repeat against the active volume with writes quiesced.

Do not modify the existing verified backup or construct a legacy database now.

Once the source Task is converted or hierarchy/activation data is used, an
older application is not compatible: it cannot read the new concepts, would
miscount inactive work, could recommend parent/inactive Tasks, and expects the
old Task dependency graph. Rollback after family-data conversion therefore
means stopping the new application, restoring the fresh pre-migration backup,
and running the matching old commit—not executing an untested down-migration on
the active database.

## Proposed implementation increments

Each increment requires separate approval and should end in a usable,
reviewable state.

### Increment 1: Milestone and Decision foundation

* **User-visible outcome:** The plan can show, create, and edit a Milestone and
  one Decision with ordered options; the user can select, revise, or clear an
  option and explicitly confirm or reverse Milestone achievement.
* **Backend/frontend areas:** Add bounded domain behavior, additive persistence,
  plan projection, focused mutations, compact cards, forms, and state actions.
* **Migration implications:** Additive schema only; do not convert the real
  Task or add scenario records yet. Old code can ignore unused additive data.
* **Reasoning added:** None beyond displaying unresolved/resolved and
  Pending/Achieved facts; the engine never chooses an option or achievement.
* **Tests:** Persistence/reload, bounded options, full edits, state actions,
  explicit achievement, API errors, and card/form behavior. Advisory readiness
  and its warning override begin in Increment 2.
* **Browser acceptance:** Create/edit both cards, choose/revise/clear an option,
  and confirm/reopen a Milestone without changing Tasks.
* **Rollback boundary:** Revert application code while additive tables remain
  unused, or restore the increment backup if records were created.

### Increment 2: Required subtasks, evidence link, and derived context

The first bounded slice implements only required subtasks and effective parent
status. It uses additive `task_hierarchy` and
`task_parent_status_overrides` tables, leaves existing records unrelated, and
does not begin evidence links, Decision readiness, or contextual Recommendation
work. Parent groups collapse independently by browser session; phase counts
exclude summaries; filtering retains a matching parent for context; targeting
expands the phase, completed section, and parent group.

* **User-visible outcome:** A parent groups one level of required subtasks;
  leaf progress derives parent status and advisory Decision readiness; the
  Recommendation selects a leaf and explains parent/Decision/Milestone context.
* **Backend/frontend areas:** Extend Task relationships and projection,
  validation, derived status/blocking/readiness, editor/card grouping, and the
  Recommendation response/presentation.
* **Migration implications:** Add the hierarchy and relationship support, but
  validate it in isolated fixtures before changing the family plan.
* **Reasoning added:** Leaf-only eligibility, reversible parent status,
  work-informs-Decision readiness, and derived Do now precedence with legacy
  fallback outside the slice.
* **Tests:** One-level enforcement, every-child-required rollup, final-child
  completion, reopening/adding work, dependencies on parents, downstream
  warnings, readiness/warning override, leaf selection, explanations, and
  unrelated fallback regression.
* **Browser acceptance:** Complete/reopen realtor fixture subtasks, observe the
  parent/readiness changes, and verify the parent is never recommended.
* **Rollback boundary:** Do not use new relationships in the active family plan
  until the new code is accepted; otherwise restore the increment backup.

### Increment 3: Conditional activation and safe revision

* **User-visible outcome:** Selecting an option activates its branches;
  inactive work is hidden by default, revealable, excluded from counts and
  Recommendations, and findable with a label. Revision previews affected work
  and protects In progress/Completed Tasks.
* **Backend/frontend areas:** Option associations, activation derivation and
  override, revision preview/commit, plan filtering/counts, finder reveal,
  editor controls, and Recommendation eligibility.
* **Migration implications:** Additive relationship support; once conditional
  data is created, older application behavior is unsafe.
* **Reasoning added:** Effective activation, inactive dependency consistency
  warnings, active-branch leaf selection, and activation explanations.
* **Tests:** Shared option work, unresolved Decision, keep-active override,
  stale preview, revision of Not started/In progress/Completed work,
  cross-activation dependencies, counts, completed sections, category-filter
  interaction, finder reveal, and inactive Recommendation exclusion.
* **Browser acceptance:** Select and revise strategies, inspect the delta,
  retain active work, reveal inactive branches, find an inactive Task, and
  verify active/completed alignment and counts.
* **Rollback boundary:** Restore the pre-increment backup and matching code;
  do not rely on an older application to interpret activation.

### Increment 4: Reviewed family-plan conversion and end-to-end acceptance

* **User-visible outcome:** The real plan uses **Start selling our home**, the
  home-sale Decision, realtor parent/subtasks, and reviewed conditional
  branches with no duplicate `Put current home on the market` Task.
* **Backend/frontend areas:** Idempotent family-data conversion, preservation
  checks, and any bounded copy refinements found in rehearsal.
* **Migration implications:** Preserve the source ID as the Milestone ID,
  translate only approved relationships, preserve unrelated data, and fail
  closed on drift. Create/rehearse a fresh backup before active migration.
* **Reasoning added:** No new rules; this increment exercises the rules from
  Increments 1–3 on the reference scenario.
* **Tests:** Exact migration fixture, unexpected-state rollback, idempotence,
  unrelated-row equivalence, no duplicate Task/Milestone, reviewed edges,
  backup/restore rehearsal, complete suites, and production build.
* **Browser acceptance:** Run the seven-step scenario below on the isolated
  restored volume, then repeat on active data only after explicit approval.
* **Rollback boundary:** Stop the new application and restore the fresh
  verified pre-migration backup with its matching application commit.

## End-to-end acceptance walkthrough

The fixture contains:

* Milestone: **Start selling our home**, open-ended post-New Year target,
  Pending.
* Decision: **Select the initial home-sale strategy**, Unresolved.
* Parent Task: **Reengage with the realtor**.
* Required leaf Tasks: contact the realtor, schedule the meeting, prepare
  questions/scenarios, gather relevant information, meet, and record the
  assessment/follow-ups, sequenced with ordinary dependencies where necessary.
* Conditional public-listing, repair-first, and builder-outreach work.

### 1. Initial Recommendation

The user sees **Do now: Contact the realtor**, `Part of: Reengage with the
realtor`, and an explanation that it gathers market evidence for the home-sale
Decision and advances **Start selling our home**. GoTime derives that the leaf
is active, actionable, and connected through evidence work to a consequential
Decision and pending Milestone. It does not use manual priority or an arbitrary
start date.

### 2. Subtask and parent progress

As required leaves begin, the parent changes from Not started to In progress.
The next unblocked leaf becomes the Recommendation. Completing the last leaf
derives Completed for the parent and satisfies dependencies pointing to it.
Reopening a child reverses the parent status after an affected-downstream-work
warning; GoTime never changes downstream progress status silently.

### 3. Advisory Decision readiness

With all linked realtor work complete, the Decision card shows Ready for
consideration. If a new builder-purchase research Task is added and linked, it
returns to Gathering information and identifies that missing work. The Select
action remains available with a warning because readiness advises rather than
controls the user.

### 4. Decision selection

The user chooses the distinct option **Builder outreach and public listing in
parallel**. GoTime does not choose it. The user sees the activation preview and
confirms the change.

### 5. Branch activation and inactive hiding

Builder-outreach and as-is public-listing work becomes active. Repair-first work
remains preserved and inactive. Ordinary phase lists, counts, completed
sections, attention, and Recommendations exclude it. Show inactive work reveals
it with an Inactive label. Finder search returns it with that label and reveals
its location on selection. GoTime recommends the next actionable leaf from the
active branches.

### 6. Decision revision after work begins

The user revises the strategy. GoTime previews every Task whose activation
would change. Not started work can be deactivated after review. Every In
progress Task requires an explicit retain/deactivate choice; there is no silent
deactivation. Completed work retains its status and remains available as plan
history. The user can retain or manually activate work that remains applicable.

### 7. Explicit Milestone achievement

Completing branch Tasks does not mark the Milestone Achieved. GoTime may show
that the selected channels appear ready and ask for confirmation. Only after
the buyer-seeking channels are genuinely active does the user mark **Start
selling our home** Achieved. The user can correct that fact by returning it to
Pending.

## Approved choices and remaining risks

The following consequential choices are approved:

1. Use an independent Milestone domain concept instead of a specialized
   Task, while preserving the old Task's stable ID value during conversion.
2. Use one selected Decision option with a named parallel option instead of
   multi-select options.
3. Use derived activation from option associations plus a persisted
   keep-active override, rather than a mutable active boolean.
4. Ignore legacy priority in future derived Do now selection while preserving
   its data and transitional display.
5. Make employment notice/PTO depend on **Our home is under contract**, and do
   not make the farewell-party Decision depend on starting the sale.
6. Use optional earliest/latest target dates with the approved exact, bounded,
   open-ended, and unknown meanings.
7. Keep inactive Completed work absent from ordinary counts and views but
   available through Show inactive work and finder/history.

Additional risks are parent reopening after downstream progress, active work
depending on inactive prerequisites, stale Decision-revision previews,
partially migrated databases, and older-application incompatibility after
family-data conversion. Each requires explicit validation and fail-closed
behavior, not inference.

Increment 1 implements only the Milestone and Decision foundation. It adds the
three empty additive tables, explicit API schemas and mutations, and compact
plan controls without changing Task or Recommendation behavior or converting
family-plan records. Its automated and isolated restored-volume migration
verification passed on 2026-08-18. The additive active migration, isolated
browser acceptance, accepted frontend deployment, and disposable-environment
teardown were completed safely by 2026-08-19. The active family plan remains
unconverted and contains no Milestones, Decisions, or Decision options.
The first bounded Increment 2 slice—required subtasks and effective parent
status—passed complete human acceptance and was deployed on 2026-08-25. Its
additive active migration created empty hierarchy and manual-override tables;
all preexisting logical data remained identical and no family relationship was
created. Evidence links, Decision readiness, contextual Recommendation
reasoning, conditional activation, and family conversion remain unstarted and
require separate approval.
# Implemented preparation-readiness slice

The second Increment 2 slice uses normalized `decision_preparation_tasks` rows
and derives advisory Decision readiness from linked Tasks' effective statuses.
Decision writes validate complete relationship sets transactionally, and
hierarchy writes reject later parent/child duplication. The Plan aggregate
returns linked IDs, readiness, and completed count. The Decision editor is the
only relationship editor; card expansion is versioned session state and View
task reuses the existing transient Plan targeting path. Recommendation ranking
and contextual explanation remain unchanged.
