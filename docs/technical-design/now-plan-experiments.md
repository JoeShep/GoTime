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
