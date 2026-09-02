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

The completed Increment 2 slices are accepted and deployed. GoTime now
supports one level of required subtasks, derived or visibly overridden parent
status, parent-aware dependency blocking, leaf-only Recommendation eligibility,
and explicit sibling ordering. Ordinary Tasks may be linked to Decisions as
preparation work, with readiness derived from effective Task status and option
selection remaining under user authority. Contextual Recommendations now use
structured deterministic Decision-preparation signals without overriding
existing urgency and timing. The first family conversion created the accepted
Tennessee home-marketing Milestone, Decision, preparation parent, and required
subtasks; no other family-data conversion is authorized.

The first deterministic Recommendation calibration is also accepted and
deployed. Eligibility precedes attention, due-today/overdue work is protected,
deadline pressure reaches actionable prerequisite frontiers, actual next-state
leverage and momentum are bounded, viewer-local dates are explicit, and legacy
priority is the weakest meaningful fallback. The family baseline confirms that
Critical priority alone no longer places **Wash windows (test)** in the bounded
Recommendation list. Defining Do now/Coming soon/Later/Waiting as broader
outputs remains a later capability slice.

The approved
[Now, Plan, and Experiments presentation boundary](technical-design/now-plan-experiments.md)
separates the primary Recommendation from complete plan management,
introduces progressive disclosure for the four Task phases, and removes
suspended experiments from the ordinary family interface without deleting
their code or evidence. Accepted planning behavior is available normally while
the shared experiment flags remain false.

### Family go-live order

The phase-wide fixed-Milestone timing prototype was rejected after human
acceptance and was not deployed. Family-MVP scheduling continues to use
explicit Task **Due by** dates and actual dependencies; optional Task duration
estimates are not part of the MVP.

Post-go-live work proceeds in this order:

1. Private family access and operational reliability.
2. Automated backups and verified restore.
3. One-way calendar publishing.
4. Deterministic opt-in notifications and reminders.
5. Reviewed moving guidance with sources and freshness dates.
6. Reconsidered explicit-work Milestone timing, only if real use demonstrates
   a need.

### Capability 5: Explain
This is the part I don't want to compromise on. Every recommendation should be accompanied by an explanation.

Example:
Recommendation > Evidence > Explanation
I think that's essential for user trust.
