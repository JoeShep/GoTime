# ADR-0009: Use React Router for declarative client routing

## Status

Accepted for the first Now/Plan/Experiments structural increment.

## Context

GoTime's single React page currently combines the persisted Recommendation,
the complete editable Plan, and suspended experiments. The approved
presentation direction requires canonical Now and Plan locations, an optional
Experiments location, accessible active navigation, direct loading, and normal
browser Back and Forward behavior.

Hand-written History API routing would duplicate established URL matching,
navigation, redirect, and accessibility behavior. The current lockfile resolves
React 19.2.7, React DOM 19.2.7, Vite 6.4.3, and TypeScript 5.8.3. Development
uses Node 24.18.0, while builds and the frontend image use Node 24.18.1. React
Router 8.3.0 requires React and React DOM 19.2.7 and Node 22.22 or newer, so the
current stable release fits every existing baseline without an upgrade.

## Decision

Use `react-router` 8.3.0 in Declarative Mode. Wrap the application in
`BrowserRouter` and declare routes with `Routes`, `Route`, and `Navigate`.
Do not add `react-router-dom`; React Router 7 documents `react-router` as the
primary package for Declarative Mode.

The router owns:

* URL matching and active navigation state;
* a replace redirect from `/` to `/now`;
* canonical `/now` and `/plan` routes;
* the default-off conditional `/experiments` route;
* normal not-found behavior; and
* browser Back, Forward, direct-load, and refresh behavior.

The Experiments route exists only when `VITE_ENABLE_EXPERIMENTS` is exactly
`true`. It is absent from ordinary family navigation even when enabled.

Accepted planning capabilities are not part of this optional route boundary.
Normal Now and Plan rendering, Milestones, Decisions, readiness, required
subtasks, contextual Recommendations, and their targeting/editing behavior are
available with both shared experiment flags false. On the backend, only the
suspended prototype Recommendation and moving-service experiment endpoints use
`GOTIME_ENABLE_EXPERIMENTS`; persisted-plan APIs do not.

Future Plan expansion and scroll position belong to browser-session workspace
state, not the router and not SQLite. A small provider plus `sessionStorage`,
keyed by persisted plan ID, may own that transient state. Later Finder and
Recommendation navigation will use an understandable task-target URL through
Plan so the destination can be expanded, scrolled to, focused, and highlighted.

This increment does not adopt data loaders, route actions, Framework Mode,
server-side rendering, or router-owned server-state management. Existing API
clients and component state continue to own data retrieval and mutation.

## Consequences

Positive:

* Now, Plan, and optional Experiments receive stable, linkable locations.
* Established routing behavior replaces bespoke History API code.
* Normal routes do not initialize the suspended experiment state machine.
* Future task-target navigation and browser-session Plan restoration have a
  clear boundary without changing persisted family data.

Negative:

* The frontend gains one runtime dependency.
* Router compatibility now depends on the existing React 19.2.7 and Node 24
  baselines recorded in the lockfile and container image.
* Direct route loading requires the frontend host to retain its existing SPA
  fallback behavior.

Deferred:

* phase collapsing and browser-session Plan restoration;
* cross-route Finder and Recommendation targets and their exact URL shape;
* persistent mobile Find navigation;
* the unified Add menu;
* secondary Now attention; and
* derived-attention Increment 2.
