# NEXT_SESSION

## Current objective: select the next bounded increment

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

Cross-route Recommendation targeting, persistent mobile bottom navigation,
secondary attention items, family-plan conversion, and derived-attention
Increment 2 have not begun.

Desktop navigation is not sticky. Returning Plan to the top before leaving it
correctly records the top as its latest saved position. Persistent access to
Now, Plan, and Find while deep in the desktop Plan may be reconsidered later;
persistent mobile bottom navigation remains planned. Minor unrelated
mobile-spacing inconsistencies remain deferred visual polish. Native
date-picker reliability still needs validation on a real mobile browser, and
eliminating SQLite byte changes from no-op backend initialization remains
deferred operational cleanup.
