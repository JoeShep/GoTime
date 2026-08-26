# NEXT_SESSION

## Current objective: required-subtask candidate awaiting human acceptance

The first derived-attention Increment 2 slice adds one level of required
subtasks without converting family data. Parent/child membership and order are
stored in an additive hierarchy table; confirmed manual parent status overrides
use a second additive table. Automatic parent status is derived from children,
dependencies use effective parent status, parent prerequisites block children,
and parent summaries are excluded from counts and Recommendations.

Plan now offers **Part of**, **Add subtask**, independently session-collapsed
groups, completion summaries, visible manual overrides, and **Return to
automatic status**. Finder and Recommendation targeting reveal a child inside
its parent group. The candidate must remain isolated until human acceptance;
Decision readiness, evidence links, contextual Recommendation work, and family
conversion have not begun.

The consolidated UX correction replaces the separate subtask visibility link
with a count-aware progress button and rotating chevron. Expanded children have
keyboard-accessible Move up/down controls backed by one transactional complete-
sibling reorder endpoint. **Part of** is now a checkbox plus searchable,
phase-scoped eligible-parent picker with category/status context and an inline
missing-parent error. Candidate-introduced browser confirmations are replaced
by one focus-contained application modal for parent phase moves, manual parent
status, downstream-unblocking completion, and first-child status changes.

Human acceptance is available at `http://localhost:22173` (isolated backend
`http://localhost:22000`). The disposable database begins with the verified
snapshot and preserves all human-created records; before this correction it
contained 52 Tasks and empty hierarchy/override tables. Human-created
relationships remain disposable and must never be copied to active data. The
normal frontend is stopped, the normal backend remains healthy and unchanged,
and the active database checksum remains
`9b5e14b5d04799f8972f4875fa66fc82f8601221b206dda18e69d8651c7a66bd`.

The unified Add and plan-wide title-uniqueness increment passed complete human
acceptance and is deployed to the normal stack at `http://localhost:5173`.
Plan has one Add menu beside **Family plan**, ordered Task, Milestone, Decision,
using the existing editors and successful-creation reveal behavior. Separate
Add controls and redundant Task creation, edit, and status success banners are
absent; the task-specific, dismissible, expiring filter-cleared notice remains.

Prospective, plan-scoped title uniqueness applies within each of Tasks,
Milestones, and Decisions. Comparison trims surrounding
whitespace, collapses internal whitespace, and ignores capitalization with
Unicode-aware comparison. Cross-type matches remain allowed. Backend POST/PUT
is authoritative and transactional; the frontend provides immediate inline
accessible validation and maps stale 409 conflicts back to the title field.

The normal active-data audit found no canonical duplicate groups. Deployment
retained 49 unique Tasks and zero Milestones, Decisions, or Decision options;
all stable ordered-row hashes matched. The isolated acceptance containers,
volume, network, and temporary Compose directory were removed. No acceptance
records were copied to the family plan.

The accepted frontend increment replaces the provisional below-`sm` header
controls with a fixed, equal-width Now, Plan, and Find bottom navigation. At
`sm` and above the accepted desktop header is unchanged. Active mobile route
taps return that route to the top without adding history; an active Plan tap
also makes zero its newest saved workspace position. Ordinary switching saves
the actual deep Plan position and restores it on return.

Mobile Find opens the existing Offcanvas, which remains above and disables the
bar while open. Closing without a result restores the originating bottom Find
control; desktop focus return remains tied to the desktop trigger. One shared
safe-area-aware bottom accommodation keeps final route content and transient
notices above the fixed bar. Human acceptance passed and the accepted frontend
is deployed to the normal stack at `http://localhost:5173`.

The focused spacing correction removes stacked mobile bottom contributions
from the shell container, card body, route alert, and final Plan phase. The
single shared formula is now a 4rem (64px) base bar plus the device safe-area
inset plus a 1rem (16px) content gutter. The safe-area inset is included once
inside the fixed bar and once in the matching page reserve, so it is not
double-counted. At zero inset the targets remain at least 44px tall and the
structural maximum-scroll clearance above the bar is 16px.
The mobile PageFrame now also uses a `100dvh` flex height chain and a mobile-only
white shell background, so short Now and not-found content reaches the fixed
bar without changing the established Plan gutter or desktop body background.

Normal smoke verification passed for frontend serving, Now, Plan, and the
frontend API proxy with Experiments disabled. The normal backend was not
rebuilt or restarted. The active database checksum remained
`9b5e14b5d04799f8972f4875fa66fc82f8601221b206dda18e69d8651c7a66bd`.
The isolated acceptance containers, volume, network, and temporary Compose
directory were removed after successful deployment verification.

The accepted frontend increment adds a compact **View task** button to a
Primary Recommendation only when its existing response includes a stable
`task_id`. It pushes `/plan` once and reuses the transient shared-Find target,
so Plan owns compatible/incompatible category-filter handling, phase and
completed-section expansion, scrolling, focus, highlighting, and saved scroll
position. The target is consumed once and is never encoded in the URL.

If the Task disappeared before Plan loads, Plan remains open and shows the
dismissible, expiring notice **The recommended task is no longer available.**
No Recommendation ranking, backend, API, schema, or database behavior changed.
Complete human acceptance passed. The accepted frontend is deployed at
`http://localhost:5173` with Experiments disabled; the normal backend retained
its identity, original start time, and zero restarts. Now, Plan, both live APIs,
the View-task navigation path, and disabled experimental endpoints passed
smoke verification. The active database remained logically and byte-for-byte
unchanged. The disposable acceptance containers, volume, network, and temporary
Compose directory were removed.

Secondary attention items and family-plan conversion have not begun. The
remaining derived-attention Increment 2 slices have not begun.

Desktop navigation is not sticky. Returning Plan to the top before leaving it
correctly records the top as its latest saved position. Persistent access to
Now, Plan, and Find while deep in the desktop Plan may be reconsidered later.
Minor unrelated mobile-spacing inconsistencies remain deferred visual polish. Native
date-picker reliability still needs validation on a real mobile browser, and
eliminating SQLite byte changes from no-op backend initialization remains
deferred operational cleanup.
