# Relocation Plan First-Use Review

## Context

This review captures observations from the first hands-on use of GoTime with a real relocation task list.

The most important finding is methodological: using a rudimentary working product exposed product-model and interaction issues that were difficult to anticipate through architecture and design work alone.

Continue the development rhythm:

> Build → use → observe friction → make a small improvement → use again.

## What is working

The current MVP provides a useful first product loop:

- A persistent relocation plan.
- Four relocation phases.
- Task creation and editing.
- Task status.
- Assignees.
- Categories.
- Start and due dates.
- Dependencies.
- Derived blocked state.
- A deterministic “What should I do next?” recommendation.
- Automatic recommendation refresh after plan changes.

This is sufficient to begin learning from real use.

## First-use observations

### 1. Assignment is optional and sometimes shared

Many relocation tasks are joint decisions or shared actions and do not need a specific assignee.

Other tasks clearly belong to one person or several people.

Current direction:

- Unassigned tasks are normal.
- Multiple assignees remain supported.
- Do not require an assignee merely to make the data appear complete.

Potential future direction:

Introduce first-class People so participants can be defined once and reused across tasks, decisions, filters, and recommendations.

A future model may distinguish:

- assignees — who is responsible for doing or deciding something;
- people involved or affected — who the work concerns.

Do not add this distinction yet.

### 2. Never seed real-person placeholder names

The current UI includes Joe/Sarah placeholder names.

Remove these.

Standing product rule:

> Never prefill a real person’s name unless the user explicitly supplied that person for that purpose.

Use empty inputs or clearly generic instructional text instead.

Do not infer or guess household members.

### 3. A task may belong to multiple categories

Real relocation tasks often span more than one useful category.

A single-category field is likely too restrictive.

Examples could include:

- Healthcare + California setup
- Employment + Move timing
- Housing + Financial
- Moving logistics + Travel

This should be addressed as a deliberate data-model change rather than folded into a small UI patch.

### 4. Dependencies are discovered over time

A task may be created before its dependencies exist.

Dependencies therefore must be editable after task creation.

The UI should make adding and removing dependencies from an existing task straightforward.

### 5. Related is not the same as dependent

Some tasks are conceptually related without either blocking the other.

Categories do not fully express this relationship.

Future direction:

Add lightweight task links separate from dependencies.

Start with a simple relationship such as:

- related to

Do not introduce a large Jira-style relationship taxonomy until usage demonstrates a need.

### 6. Dependency chains should be derived

If:

A depends on B

and:

B depends on C

GoTime should understand the chain:

C → B → A

A is indirectly blocked by C.

Do not automatically persist an additional direct dependency from A to C.

Keep direct dependencies as entered by the user and derive transitive dependency relationships from the graph.

### 7. Edit interaction needs stronger feedback

Clicking Edit currently changes the edit area elsewhere on the page without necessarily making that change visible to the user.

Immediate improvement:

Clicking Edit should scroll the edit form into view and move focus appropriately.

### 8. “Priority” is conceptually ambiguous

The current low / medium / high / critical field mixes several concepts.

In relocation planning, nearly every unfinished task may eventually become critical as time passes.

The more meaningful factors appear to include:

- time pressure;
- due date;
- lead time;
- dependency leverage;
- consequence or importance;
- explicit human override.

Dependency leverage should be derived rather than entered by the user.

Do not redesign ranking during the immediate UX patch, but treat the current Priority field as provisional.

Future review should consider whether it becomes:

- Importance;
- optional manual override;
- or another narrower concept,

while urgency is derived from timing and dependency structure.

### 9. The dependency picker will not scale as a flat checkbox list

With a realistic relocation plan, a flat list quickly becomes cumbersome.

Immediate improvement:

- searchable dependency selection;
- grouping by phase;
- stable useful ordering within groups.

Possible future improvements may group/filter by category or relationship.

Do not build a graphical dependency editor yet.

### 10. One task view will not be enough

Real use will eventually require multiple ways to inspect the same plan.

Likely useful views include:

- by phase;
- by category;
- by person;
- by due date;
- blocked vs. actionable;
- sooner vs. later;
- priority/importance;
- related task group.

Sections should eventually be collapsible and navigable.

Do not build all views now.

## First usability improvement

Document the five items that were selected for immediate implementation:

1. Remove real-name placeholders.
2. Keep assignee optional.
3. Make dependencies editable after creation.
4. Scroll/focus the edit form.
5. Add searchable, phase-grouped dependency selection.

Status:

Implemented and accepted in commit:

`ca8ce39 Improve relocation plan first-use usability`

## Ongoing usage observations

### Completed tasks

Completed tasks need to be handled in some way other than simply remaining in the normal task list with status `completed`.

Possible future treatments include a collapsed Completed section or hiding completed tasks by default while preserving them as plan history.

This observation was promoted into the completed-task lifecycle enhancement.
Completed tasks remain in their phase history and are presented in a collapsed
`Completed (n)` section, separate from active work.

### Completed dependencies

When a task is completed:

- it should no longer block downstream tasks;
- it should no longer appear as a candidate in the dependency picker;
- existing dependency relationships should remain recorded so sequencing history is preserved.

This observation was promoted into the same lifecycle enhancement. Completed
tasks cannot be introduced as new dependencies. Existing relationships remain
visible and removable during editing, completed dependencies do not block, and
reopening a dependency restores blocking without recreating the relationship.

### Priority remains problematic

Continued real use reinforces that the current `low / medium / high / critical` Priority field is not useful enough.

It appears to mix:

- importance;
- urgency;
- time pressure;
- due dates;
- dependency leverage;
- consequence;
- explicit human override.

This strengthens the earlier observation rather than creating a separate issue.

Do not redesign this yet.

### Family members and assignment identities

Family members will eventually need to be defined once and selectable for task assignment rather than repeatedly entered as names.

Before implementation, determine whether these should be:

- reusable People records;
- actual GoTime Users/accounts;
- or separate concepts that can be linked.

Do not assume every participant must have a GoTime account.

### Task search

Plan-wide task search will be needed as the task list grows.

### Category vocabulary

`Administrative` and `Logistics` currently feel too close in meaning.

Continue observing real task categorization before changing the taxonomy.

### Phase vocabulary

`Complete the move` and `Settle in` currently feel too close in meaning.

Continued use should determine whether they need clearer definitions, different names, different boundaries, or consolidation.

### Add Task interaction

The `Add Task` button can be confusing while the new-task form is already open.

It has been clicked accidentally when the intended action was Save.

Possible improvement:

- disable or hide `Add Task` while the new-task form is open.

Do not choose the interaction yet.

If tasks continue to be listed under phase sections, consider adding an
`Add task` action to each phase header. It could open the existing task form
with that phase already selected. Preserve this as a future observation; do not
implement it yet.

### Save action placement

The Save button at the bottom of the form creates increasing friction.

As the dependency list grows, Save moves well below the fold.

Even with few dependencies, reaching the Save action can require awkward scrolling.

Possible approaches include:

- a sticky action area;
- Save near the top of the editor;
- another persistently visible Save action.

Choose the solution based on continued hands-on use.

### Dependency terminology

The term `Dependencies` is proving ambiguous about relationship direction.
Clearer wording might include `Depends on` or `Blockers`; task cards already
use `Depends on`. Continue observing usage before choosing or implementing new
terminology.

## Candidate next improvements

Do not treat this as a committed roadmap.

When continued use is materially impeded, review the observations above and select the smallest useful improvement.

Current likely candidates include:

- Add Task / Save interaction;
- task search.

Completed-task and completed-dependency behavior was intentionally promoted
and implemented before selecting another candidate.

Larger model or vocabulary decisions should continue to accumulate evidence before implementation.

## Development rule

Do not automatically convert every observation into Codex work.

Preserve the observation first.

Promote it into implementation only when hands-on use demonstrates that the change is worthwhile
