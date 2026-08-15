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

## Immediate follow-up

Implement only the friction that interferes with continued use:

1. Remove real-name placeholders.
2. Keep assignee optional.
3. Verify dependencies are editable after creation.
4. Scroll/focus the edit form when Edit is selected.
5. Replace the flat dependency picker with a searchable, phase-grouped picker.

Then resume entering and using the real relocation plan.

## Next design sequence

After the immediate usability patch, review the larger observations in this order:

1. Multi-category task model.
2. People and reusable participant identities.
3. Related-task links distinct from dependencies.
4. Dependency-chain visualization and derived graph information.
5. Priority / importance / urgency model.
6. Alternate task views and navigation.

Do not assume every item needs implementation. Continue to let hands-on use determine which change comes next.