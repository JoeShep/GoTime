# Now, Plan, and Experiments presentation boundary

## Status and scope

This document records the approved product direction following the read-only
audit of the Increment-1 interface. ADR-0009 selects React Router 8.3.0 in
Declarative Mode for the first structural increment. That increment establishes
the route and Experiments boundaries while leaving later workspace behavior
deferred.

This work must remain separate from derived-attention Increment 2. It changes
where existing capabilities appear; it does not add required subtasks,
work-informs-Decision relationships, advisory readiness, or contextual
Recommendations.

## Audit conclusion

The current page combines three different concerns:

1. the persisted Recommendation and Task-plan experience;
2. the Milestone and Decision foundation; and
3. suspended employment-planning and moving-service experiments.

The main source of scrolling is the 47 active Task cards rendered inside four
permanently expanded phases. Moving the suspended experiments out of the family
interface removes substantial clutter, but separating Now from Plan and making
phases collapsible provides the transformative reduction.

Nothing from the experimental prototype should be deleted, commented out, or
hidden with CSS at this stage. Its implementation, deterministic endpoints,
tests, and documentation remain useful evidence for later redesign.

## Now

`/now` is the default landing experience. `/` opens `/now`.

Now contains, in order:

* compact family navigation;
* GoTime branding and **What should I do next?**;
* the persisted plan title labeled **Our goal**, replacing the separate static
  Today's Goal text;
* one primary persisted Recommendation with a concise explanation;
* up to three additional attention items, but only after genuine
  derived-attention behavior can produce them;
* Decisions only when advisory-ready or otherwise requiring attention;
* Milestones only when approaching their target window, requiring user
  confirmation, or providing context for recommended work; and
* a clear route to Plan.

Legacy Critical, High, Medium, and Low values must not be used to manufacture
secondary Now items while Increment 2 signals are unavailable.

## Plan

`/plan` uses a compact Plan heading and does not repeat the large Now hero.
It contains:

* one Add menu offering Task, Milestone, and Decision without remembering the
  previous type;
* compact, separate-but-linked Milestone and Decision sections;
* collapsed summaries for those concepts with expandable details;
* the plan-wide finder and category filter;
* Expand all and Collapse all controls; and
* initially collapsed Task phases, with multiple phases allowed open.

Phase expansion state is retained for the browser session. Ordinary Now/Plan
switching and browser Back also preserve the Plan's scroll position and phase
expansion state.

Finder and Recommendation navigation into Plan must reveal the destination,
expand its phase and completed section when needed, scroll to it, and use the
established focus/highlight behavior. A return-to-top control remains optional
and should be reconsidered only after the new structure is tested.

## Navigation

`/now` and `/plan` are canonical locations. Desktop uses compact Now and Plan
navigation. Mobile uses persistent Now, Plan, and Find navigation. Find opens a
focused search panel and navigates its result into Plan rather than embedding
the complete Plan in the search experience.

ADR-0009 selects the established `react-router` package rather than hand-written
History API routing. The router owns URLs, active navigation, redirects, and
Back/Forward behavior. Future Plan expansion and scroll state remain transient
browser-session workspace state rather than router server state or SQLite data.

## Experiments boundary

Suspended frontend experiments are default-off behind an explicit build-time
flag such as `VITE_ENABLE_EXPERIMENTS`. When enabled, `/experiments` contains:

* the employment-planning Recommendation;
* the work-arrangement and commute-input sequence;
* the suggested-question experiment; and
* experiment-specific loading, answer, dismissal, retry, and fallback states.

Experiments do not appear in ordinary family navigation. When disabled, the
route uses normal not-found behavior. Normal Now and Plan code must not import
the experimental state machine.

Experimental backend endpoints are also default-off behind an explicit server
setting such as `GOTIME_ENABLE_EXPERIMENTS`. Enabling either boundary does not
authorize AI calls, live research, provider credentials, or spending. Existing
deterministic endpoints and their tests remain preserved behind the boundary.
Development documentation must explain both flags and their default-off
behavior when the boundary is implemented.

The following presentation concepts remain relevant to future derived
attention even though their suspended implementations move behind Experiments:

* Why this is recommended.
* Why it matters now.
* Relevant dependencies.
* Blocked downstream work.
* Related assumptions.

They should be redesigned against trusted persisted-plan facts rather than
copied from the employment prototype into Now.

## Component and state implications

The current application renders the persisted Recommendation, complete Plan,
and employment prototype from one page. The structural implementation will
need to separate those responsibilities while preserving the existing
Recommendation refresh behavior after relevant Task mutations.

Finder state, category filters, completed-section expansion, editor state,
Task references, and navigation highlighting currently belong to the Plan
component. Cross-route reveal behavior and browser-session preservation require
an explicit owner. The design should retain state at the navigation shell or
in a bounded session store rather than couple Now to Plan internals.

The single Add menu should open the existing focused editors; it should not
create a new administration screen. Milestones and Decisions remain distinct
but linked concepts and should not be merged into one card type merely to
simplify navigation.

## Implementation order

1. Select the routing dependency and document the architectural decision.
2. Extract and default-off gate the Experiments frontend and backend.
3. Introduce the Now/Plan/Find navigation shell.
4. Extract the persisted Recommendation into Now.
5. Add collapsible phases and browser-session state preservation.
6. Add cross-route Finder and Recommendation reveal behavior.
7. Consolidate Add controls.
8. Define secondary Now attention only when Increment 2 supplies valid signals.
9. Review Increment 2 against the completed presentation boundary.

Each structural increment should remain independently reviewable. Do not begin
derived-attention Increment 2 as part of this redesign.

## First structural increment status

The first increment implements `/` → `/now`, canonical `/now` and `/plan`,
accessible active navigation, normal not-found behavior, and the conditional
`/experiments` route. Now contains only the persisted plan title and current
persisted-task Recommendation. Plan retains the accepted management interface
with expanded phases, separate Add controls, finder, filters, and completed
sections.

The extracted Experiments page has no Plan dependency and is absent unless
`VITE_ENABLE_EXPERIMENTS` is exactly `true`. Its two deterministic backend
routes return 404 unless `GOTIME_ENABLE_EXPERIMENTS` is exactly `true`.

Human browser acceptance passed for the route boundaries, default-off
Experiments behavior, shared segmented navigation, and responsive page-shell
spacing. The accepted frontend and backend were deployed to the normal stack
with both flags disabled. The isolated acceptance project and its disposable
database were then removed without touching the normal data volume. The first
structural increment is complete; implementation order resumes at collapsible
phases and browser-session Plan state.

## Collapsible-phase increment status

The next bounded increment makes every Task phase an independently controlled,
initially collapsed section. Its full header is a native button containing the
phase title, filtered or unfiltered remaining/completed counts, and a directional
chevron. Compact Expand all and Collapse all controls operate on visible phases;
Collapse all also closes every completed subsection.

Expansion is transient browser-tab state. A versioned record at
`gotime:plan:<plan-id>:expansion` in `sessionStorage` contains only expanded
phase IDs and expanded completed-subsection phase IDs. It is never sent to the
API or SQLite. Unknown IDs are discarded and malformed or incompatible records
fall back to all-collapsed state. Plan scroll-position preservation remains a
later structural increment.

Entering category filtering snapshots the current phase expansion once and
opens every matching phase. Filter changes do not replace that snapshot, users
may still toggle visible phases, and clearing restores the snapshot. Temporary
filter-driven expansion is not persisted as the ordinary no-filter session
state. Finder selection opens only the destination phase and, for completed
Tasks, its completed subsection while retaining the established filter-clear,
focus, scroll, and highlight behavior.

Human browser acceptance passed for initial and independent expansion, counts,
completed subsections, global controls, filtering and snapshot restoration,
Finder reveal, route and refresh persistence, status-change stability, and
desktop/mobile presentation. The accepted frontend was deployed without
restarting the backend or changing the active database. Every database count
and stable row-content hash matched before and after deployment. The disposable
acceptance containers, network, volume, and temporary Compose files were then
removed. This increment is complete.

The next structural work remains Plan scroll restoration and cross-route Finder
and Recommendation reveal. Unified Add and mobile bottom navigation follow in
the approved sequence. Those items, secondary attention, family-plan
conversion, and derived-attention Increment 2 have not begun.

## Shared Find and Plan scroll restoration

This bounded increment replaces the inline Plan Finder with one shared
header **Find** action available from Now and Plan. It opens a React-Bootstrap
off-canvas dialog, fetches a current persisted-plan snapshot each time it opens,
and searches Task titles plan-wide without coupling to category filtering.
Desktop uses a right-side panel; mobile uses a nearly full-width panel. The
header action is intentionally distinct from the Now/Plan routes and remains a
provisional mobile treatment until persistent bottom navigation is designed.

A selected result is held only as transient React context. Selection from Now
pushes one `/plan` history entry; selection already on Plan does not navigate
again. After the panel finishes closing, Plan consumes the target once through
the established reveal path: retain a compatible category filter or clear an
incompatible one, open only the destination phase and any completed subsection,
scroll, focus, and temporarily highlight. Refresh cannot replay the transient
target or highlight.

Plan scroll position uses a separate versioned session record at
`gotime:plan:<plan-id>:scroll`. Writes are bounded to one per animation frame,
the value is restored once after Plan data and expansion state are ready, and
invalid or stale values are ignored while out-of-range values are clamped to
the rendered page. Find targeting takes precedence over restoration and saves
the resulting destination. Now opens at the top without clearing Plan state.
No workspace state is sent to the API or SQLite.

Browser acceptance exposed a route-teardown ordering defect: the original
cleanup read live `window.scrollY` after Now had moved the viewport to zero,
overwriting the valid Plan position. The corrected lifecycle records the last
Plan-owned position from Plan scroll events, uses a layout-effect cleanup before
route layout changes, and never derives the teardown value from Now's viewport.
Restoration still runs once after expansion and category-filter state are
applied. Finder destinations override restoration, update the Plan-owned
position after scrolling, and remain transient for focus and highlighting.

Category filters are now a third versioned Plan workspace record at
`gotime:plan:<plan-id>:filters`. Values are restored in configured order before
scroll restoration; malformed, stale, duplicate, and unknown identifiers fall
back to no filter. Clearing an incompatible filter through Find persists that
empty state. The explanatory notice names the selected Task, uses non-layout
informational status presentation, supports explicit dismissal, expires after
approximately six seconds, and disappears on later filter or Find interaction.
It is never stored. Find remains visually separate from route navigation but is
centered and sized to the inner Now/Plan targets rather than their padded outer
container.

Automated verification for the corrected candidate passed all 100 frontend
tests and the production build. Complete human acceptance then passed for the
shared Find panel, cross-route navigation and browser history, restored Plan
workspace state, transient targeting, filter-cleared notice, and responsive
Find-button sizing and alignment.

The accepted frontend was deployed by rebuilding the normal frontend image and
recreating only `gotime-frontend-1`, with Experiments disabled. The normal
backend was not rebuilt, restarted, or recreated. Frontend serving, Now, Plan,
Plan and Recommendation API proxying, the client-side Experiments not-found
boundary, and both disabled experimental APIs passed runtime verification.

Before deployment, the active database was 221,184 bytes with SHA-256
`cf158547d56c158d16ed442bae279a4a7d27ef266a78d15b258e007f69c656c1`.
The first Plan API read after the backend's independent reboot restart lazily
initialized the repository; its existing idempotent default-phase updates
changed SQLite file metadata and the byte checksum. The final file remained
221,184 bytes with SHA-256
`f7b533dec39ee57207928a92b61af4de87a4219791454dcc9ba78b1476e9d036`.
Integrity remained `ok`, foreign-key checks remained empty, and every table
count and stable row-content hash matched before and after. All 49 Task IDs
remained unique, and Milestones, Decisions, and Decision options remained
empty. Repeated reads caused no further file change.

After verification, only the `gotime_shared_find_acceptance` frontend and
backend containers, disposable volume
`gotime_shared_find_acceptance_data_f08054d`, isolated network
`gotime_shared_find_acceptance_net_f08054d`, and temporary Compose directory
were removed. Normal resources, the active volume, verified backup, and
manifests were untouched. This increment is complete.

Desktop navigation is not sticky. Scrolling Plan to the top before leaving
correctly makes the top the latest saved position. Persistent mobile bottom
navigation remains planned, and persistent Now, Plan, and Find access while
deep in the desktop Plan may be reconsidered later. Unrelated mobile-spacing
polish remains deferred. Cross-route Recommendation targeting, unified Add,
persistent mobile bottom navigation, secondary attention items, family-plan
conversion, and derived-attention Increment 2 were not started.

## Unified Plan Add candidate

Plan now presents one prominent text-labeled **Add** dropdown beside the compact
**Family plan** heading. Its responsive flex header keeps the action at the
upper right on desktop and permits a clean wrap on narrow screens. The menu
uses accessible dropdown semantics and lists, in order: **Task — Something that
needs to be done**, **Milestone — An important outcome or moment**, and
**Decision — A choice that needs to be made**. It closes by toggle, outside
selection, Escape, or choice; Escape returns focus to Add, and every opening
starts without a remembered creation type. Now has no Add action.

Each choice coordinates the existing Task, Milestone, or Decision editor rather
than introducing a parallel form. Only one creation editor can be active. Its
first meaningful field receives focus, Add and Find cannot launch conflicting
transient interfaces while the editor is active, validation retains the draft,
and save disabling remains scoped to that editor. Cancel preserves the captured
Plan position, restores focus to Add, and does not change workspace state.

Successful Task creation reuses the established Finder reveal path against the
aggregate returned by the existing API: it opens only the selected phase,
preserves unrelated phases, retains a compatible category filter or clears and
persists an incompatible one with the Task-specific transient notice, scrolls
and focuses the new card, applies the bounded highlight, updates counts, and
saves the resulting Plan position. Successful Milestone and Decision creation
similarly use their returned Plan aggregate, then scroll, focus, highlight, and
save the new card location. Creation focus and highlighting are transient and
are not persisted or replayed.

Initial focused verification passed 70 tests; the then-complete frontend suite
passed all 107 tests; the production frontend build and `git diff --check`
passed. No backend, schema, API, ADR, or database files changed in that initial
frontend-only candidate. Its isolated acceptance environment was retained
through the later notice, title-uniqueness, and success-feedback corrections,
then removed after complete acceptance and normal deployment as recorded below.

### Prospective title uniqueness extension

The unified Add candidate now treats titles as unique within one Plan and the
same entity type. Tasks compare across all phases and statuses, including
completed work; Milestones compare with Milestones; Decisions compare with
Decisions. Cross-type title matches are valid. Canonical comparison trims
surrounding whitespace, collapses consecutive internal whitespace, and applies
Unicode-aware case-insensitive comparison without otherwise rewriting the
stored display title.

The repository remains authoritative for Task, Milestone, and Decision POST and
full PUT. It performs the canonical duplicate check and mutation under one
immediate SQLite write transaction, excludes the edited record, and permits an
edit whose canonical title is unchanged even if prospective enforcement finds
legacy duplicates. Conflicts return HTTP 409 with stable `duplicate_task_title`,
`duplicate_milestone_title`, or `duplicate_decision_title` codes and bounded
human messages. No schema, index, trigger, title key, migration, or active-data
conversion is introduced.

The frontend shares one canonicalization utility across all three existing
editors. A current aggregate conflict produces inline invalid title feedback
without a request. An authoritative stale or concurrent conflict keeps the
draft open, restores the save control, focuses the title, and avoids global
errors and all successful-reveal side effects. Changing to a nonconflicting
title clears the error; unchanged self-edits and cross-type matches remain
valid.

The read-only active audit found no Task, Milestone, or Decision duplicate
groups. The disposable audit found one permitted Task group in Plan
`family-relocation-plan`, canonical title `notice timeout test`, IDs
`notice-timeout-test-bb118b9d-04d0-4d33-a77c-f336611c57c1` and
`notice-timeout-test-cb948a97-1cec-44a4-8bdc-3cc16a0b4b1d`; both stored titles
are `Notice timeout test`, phase `decide`, status `not_started`. Those records
remain unchanged and do not block canonical-equivalent edits.

Focused backend verification passed 42 tests and the complete backend suite
passed 207 tests. Backend compilation passed. Focused frontend verification
passed 77 tests, the complete frontend suite passed 114 tests, and the
production build and `git diff --check` passed.

### Unified Add deployment closeout

Complete human acceptance included Add placement and menu behavior, reuse of
all three editors, successful-creation reveal, transient filter-cleared
feedback, title-conflict recovery, and removal of redundant persistent Task
creation, edit, and status success banners. The visible card, status, counts,
focus, and bounded highlight provide successful-operation confirmation.

Accepted frontend and backend images were deployed together with both
experiment flags false and without a migration or data conversion. The active
canonical-title audit found no duplicate Task, Milestone, or Decision groups.
The approved duplicate Task API probe returned HTTP 409 and
`duplicate_task_title`, created no row, and left every ordered-row hash
unchanged. The active Plan remained at 49 unique Tasks and zero Milestones,
Decisions, and Decision options with integrity `ok` and no foreign-key
violations.

Backend initialization/no-op write activity changed SQLite file metadata and
bytes, but not logical content; eliminating those no-op byte changes remains
deferred. The isolated acceptance containers, disposable database volume,
network, and temporary Compose directory were removed after normal runtime and
data verification.

Cross-route Recommendation targeting, secondary attention items, family-plan
conversion, and derived-attention Increment 2 were not started. Unrelated mobile-spacing polish, real-mobile
native date-picker validation, and possible persistent desktop Now/Plan/Find
access deep in Plan remain deferred.

## Persistent mobile bottom-navigation candidate

Below Bootstrap's existing `sm` breakpoint, PageFrame renders one labelled,
fixed bottom navigation with equal-width text targets in the order Now, Plan,
Find. The provisional mobile header wrapper and controls are absent rather than
merely duplicated or visually hidden. At `sm` and above, only the accepted
desktop header renders and its structure, sizing, and ordinary link behavior
remain unchanged.

Now and Plan remain real links with `aria-current="page"`. A tap on the active
mobile link prevents redundant router navigation and scrolls that route to the
top, using smooth motion unless the browser requests reduced motion. The Plan
workspace owner handles two bounded window events: it snapshots the actual
deep position before a mobile route departure and writes zero before an
intentional active-Plan return-to-top. Phase, completed-section, filter, and
scroll state otherwise retain the accepted session behavior, including Back,
Forward, refresh, Now-at-top, and Find destinations replacing saved position.

Find remains a button and opens the single existing Offcanvas without changing
the URL. Its expanded/pressed state mirrors the panel; the mobile navigation is
inert beneath the modal and its Bootstrap backdrop. Offcanvas focus containment
and dismissal are unchanged, so a non-selection close restores the precise
desktop or mobile trigger that opened it. Result selection continues through
the existing Plan targeting, filter compatibility, focus, bounded highlight,
and saved-position flow.

One mobile CSS custom-property boundary combines the fixed navigation height
with `env(safe-area-inset-bottom, 0px)`. Shared PageFrame bottom accommodation
keeps final Now, Plan, editor, validation, notice, and not-found content clear;
the transient filter notice receives the same offset. The accommodation is
absent at `sm` and above. The bar uses a restrained border/shadow, visible focus
treatment, minimum tap height, non-color active decoration, and a z-index below
the Offcanvas and backdrop without overflow suppression or fixed offsets.

Focused navigation, workspace, Find, routing, and unified-Add verification
passed 38 tests. The complete frontend suite passed all 122 tests and the
production build passed. No backend, schema, API, database, title-uniqueness,
or ADR file changed. Human acceptance and normal deployment remain pending.

The candidate is isolated at `http://localhost:20173` with backend
`http://localhost:20000` in project `gotime_mobile_nav_acceptance`. Its unique
frontend/backend containers share only network
`gotime_mobile_nav_acceptance_net_8559604`; only the backend mounts disposable
volume `gotime_mobile_nav_acceptance_data_8559604`. SQLite's backup API restored
the verified preserved backup, whose manifest baseline is 48 unique Tasks; the
current backend added only the empty additive Milestone, Decision, and option
tables. Integrity is `ok`, foreign keys are clean, and neither acceptance
container mounts or joins `gotime_gotime_data` or the normal network.
