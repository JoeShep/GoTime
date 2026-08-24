# NEXT_SESSION

## Current objective: final focused human acceptance of unified Add

The frontend-only unified Add candidate is ready for human acceptance at
`http://localhost:19173` (isolated backend `http://localhost:19000`). Plan has
one Add menu beside **Family plan**, ordered Task, Milestone, Decision, using
the existing creation editors. The normal bind-mounted frontend remains
stopped; the normal backend is healthy and the active database is unchanged.

All broad human acceptance passed. A focused correction removed the persistent
generic `Task added` banner: incompatible-filter creation now shows only the
established task-specific, dismissible, six-second notice, while compatible or
unfiltered creation relies on the accepted reveal feedback. Final human retest
is limited to this notice lifecycle; the native Firefox Responsive Design Mode
date-picker behavior remains explicitly out of scope.

The final candidate extension adds prospective, plan-scoped title uniqueness
within each of Tasks, Milestones, and Decisions. Comparison trims surrounding
whitespace, collapses internal whitespace, and ignores capitalization with
Unicode-aware comparison. Cross-type matches remain allowed. Backend POST/PUT
is authoritative and transactional; the frontend provides immediate inline
accessible validation and maps stale 409 conflicts back to the title field.

Complete the focused duplicate-title and notice retest before any deployment or
closeout. Existing disposable duplicates remain untouched and unchanged
canonical edits remain valid. Verify rejection has no reveal, filter, phase,
highlight, or saved-scroll side effects.

The final acceptance correction removes the redundant persistent success
banners after a successful Task full edit or Task status change. The changed
card, status placement, and counts remain the confirmation; validation,
duplicate-title, request-error, and filter-cleared notice paths remain intact.
Retest one Task edit and one status change, confirming the visible changes and
the absence of generic success banners. Do not close or deploy the increment.
Human-created acceptance records are disposable and must never be copied to the
active family plan.

Cross-route Recommendation targeting, persistent mobile bottom navigation,
secondary attention items, family-plan conversion, and derived-attention
Increment 2 have not begun.

Desktop navigation is not sticky. Returning Plan to the top before leaving it
correctly records the top as its latest saved position. Persistent access to
Now, Plan, and Find while deep in the desktop Plan may be reconsidered later;
persistent mobile bottom navigation remains planned. Minor unrelated
mobile-spacing inconsistencies remain deferred visual polish.
