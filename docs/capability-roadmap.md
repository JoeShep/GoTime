## Capabilities
### Capability 1: Observe
> The engine has to understand the current world.

Questions it should eventually answer:
+ What is the goal?
+ Who is involved?
+ What has been completed?
+ What is blocked?
+ What time is it?
+ What deadlines exist?

Notice...
No recommendations yet.
Just understanding.

### Capability 2: Represent
> Now it needs an internal representation.

For the move:
Goal > Phases > Projects > Tasks > Dependencies
( Still no AI )

### Capability 3: Evaluate

This is where it starts thinking.

Examples:
+ What is blocked?
+ What is overdue?
+ Which projects are at risk?
+ What assumptions changed?

This is probably the first place we'll write interesting business logic.

### Capability 4: Recommend
Now it answers:
> What should I do next?
Notice how late this appears. That's because recommendation depends on everything before it.

The next design increment refines this capability through derived attention.
Working states are Do now, Coming soon, Later, and Waiting, calculated from
deterministic plan context rather than selected as manual task priorities. The
current four-level priority remains preserved while a no-AI baseline is tested
against representative family-plan tasks.

Only after that baseline identifies missing facts should GoTime define a
structured planning-knowledge contract. AI assistance may later propose
inspectable lead times, prerequisite patterns, durations, or timing windows,
but deterministic rules continue to combine knowledge with trusted plan state
and own the resulting attention and recommendation.

The manual walkthrough of the
[home-sale strategy reference scenario](reference-scenarios/home-sale-strategy.md)
is complete. The resulting
[technical design](technical-design/derived-attention-vertical-slice.md)
proposes a narrow vertical slice: recommend active leaf-level work with
context, derive reversible parent status and advisory Decision readiness,
activate conditional branches only after the user's choice, preserve inactive
work outside ordinary attention, and require explicit Milestone achievement.
Review and approve the design and increment sequence before implementation.

The first two bounded Increment 2 slices are accepted and deployed. GoTime now
supports one level of required subtasks, derived or visibly overridden parent
status, parent-aware dependency blocking, leaf-only Recommendation eligibility,
and explicit sibling ordering. Ordinary Tasks may be linked to Decisions as
preparation work, with readiness derived from effective Task status and option
selection remaining under user authority. Both active migrations added empty
relationship structures only; the family plan was not converted. Contextual
Recommendation reasoning remains later, separately approved work.

Before Increment 2 changes reasoning behavior, establish the approved
[Now, Plan, and Experiments presentation boundary](technical-design/now-plan-experiments.md).
This separates the primary Recommendation from complete plan management,
introduces progressive disclosure for the four Task phases, and removes
suspended experiments from the ordinary family interface without deleting
their code or evidence. Secondary Now attention remains empty until genuine
derived signals exist.

### Capability 5: Explain
This is the part I don't want to compromise on. Every recommendation should be accompanied by an explanation.

Example:
Recommendation > Evidence > Explanation
I think that's essential for user trust.
