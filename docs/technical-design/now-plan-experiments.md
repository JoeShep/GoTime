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
