# NEXT_SESSION

## Current objective: human acceptance of unified Plan Add

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

Complete the focused notice retest before any deployment or closeout. Verify
task-specific copy, close and six-second expiry, dismissal on filter/Add/Find
interaction, absence for compatible or unfiltered creation, and unchanged Task
reveal/focus/highlight/count/scroll behavior.
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
