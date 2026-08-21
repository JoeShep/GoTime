# NEXT_SESSION

## Current objective: accept shared Find and Plan scroll restoration

Human-test the shared cross-route Find panel and browser-session Plan scroll
restoration at `http://localhost:18173`. The disposable project is
`gotime_shared_find_acceptance`; it is isolated from `gotime_gotime_data` and
must remain running until acceptance is reported.

The candidate replaces the inline Plan Finder with a shared header action,
preserves Finder reveal/filter behavior across routes, and stores only a
versioned Plan scroll position in plan-ID-scoped `sessionStorage`. The mobile
header Find button remains provisional until future bottom navigation.

Do not deploy or close this increment before human acceptance. Recommendation
cross-route targeting, unified Add, mobile bottom navigation, secondary
attention items, family-plan conversion, and derived-attention Increment 2 have
not begun.

Minor unrelated mobile-spacing inconsistencies remain deferred visual polish.
