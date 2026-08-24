# NEXT_SESSION

## Current objective: human acceptance of persistent mobile navigation

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

The next frontend-only candidate replaces the provisional below-`sm` header
controls with a fixed, equal-width Now, Plan, and Find bottom navigation. At
`sm` and above the accepted desktop header is unchanged. Active mobile route
taps return that route to the top without adding history; an active Plan tap
also makes zero its newest saved workspace position. Ordinary switching saves
the actual deep Plan position and restores it on return.

Mobile Find opens the existing Offcanvas, which remains above and disables the
bar while open. Closing without a result restores the originating bottom Find
control; desktop focus return remains tied to the desktop trigger. One shared
safe-area-aware bottom accommodation keeps final route content and transient
notices above the fixed bar. Human acceptance and normal deployment remain
pending; the normal bind-mounted frontend is stopped.

The focused spacing correction removes stacked mobile bottom contributions
from the shell container, card body, route alert, and final Plan phase. The
single shared formula is now a 4rem (64px) base bar plus the device safe-area
inset plus a 1rem (16px) content gutter. The safe-area inset is included once
inside the fixed bar and once in the matching page reserve, so it is not
double-counted. At zero inset the targets remain at least 44px tall and the
structural maximum-scroll clearance above the bar is 16px.
The corrected isolated frontend is running at `http://localhost:20173`; its
backend, network, disposable volume, and 48-Task data set were preserved.

Human review is available at `http://localhost:20173` with isolated backend
`http://localhost:20000`. Compose project `gotime_mobile_nav_acceptance` uses
containers `gotime-mobile-nav-acceptance-frontend` and
`gotime-mobile-nav-acceptance-backend`, disposable volume
`gotime_mobile_nav_acceptance_data_8559604`, and isolated network
`gotime_mobile_nav_acceptance_net_8559604`. Its verified restored database has
48 unique Tasks (the preserved backup-manifest baseline), zero Milestones,
Decisions, or options, integrity `ok`, and no foreign-key violations.

Cross-route Recommendation targeting, secondary attention items, family-plan
conversion, and derived-attention Increment 2 have not begun.

Desktop navigation is not sticky. Returning Plan to the top before leaving it
correctly records the top as its latest saved position. Persistent access to
Now, Plan, and Find while deep in the desktop Plan may be reconsidered later.
Minor unrelated mobile-spacing inconsistencies remain deferred visual polish. Native
date-picker reliability still needs validation on a real mobile browser, and
eliminating SQLite byte changes from no-op backend initialization remains
deferred operational cleanup.
