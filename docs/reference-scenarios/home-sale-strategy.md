# Home-Sale Strategy Reference Scenario

## Purpose and status

This is GoTime's first concrete reference scenario for milestone-driven
planning and derived attention. It describes a real planning situation in
enough detail to test whether GoTime can determine what deserves attention
without relying on manually assigned task priority or an arbitrary start date.

The scenario and vocabulary are product-design inputs, not finalized database
entities, Pydantic schemas, API contracts, or interface designs. The exact
minimum acceptable proceeds is intentionally omitted from this public
reference scenario.

## Provisional vocabulary

* **Milestone:** A meaningful outcome or state that organizes related work
  around a target date or window.
* **Decision:** An unresolved choice whose outcome can change which work is
  relevant.
* **Decision option:** One credible outcome under consideration.
* **Hard constraint:** A condition an option must satisfy to remain viable.
* **Preference:** A criterion used to compare viable options rather than
  automatically reject them.
* **Evidence need:** Information required to make a responsible decision,
  possibly expressed as a range or confidence-qualified estimate.
* **Conditional work:** Work that becomes relevant only if a particular
  decision option is selected.
* **Hard prerequisite:** Work without which an outcome cannot occur.
* **Supporting or timed work:** Work coordinated with a milestone but not
  required for every route to that milestone.

These distinctions are intended to generalize to plans such as weddings,
vacations, and parties. For example, a venue decision can activate different
preparation work while a wedding date window still organizes every viable
route.

## Milestone: current-home sale campaign is launched

The milestone is the broader moment when the sale campaign for the current
home is launched. It is achieved when the marketing channels selected by the
family become active. Those channels could include:

* a public listing;
* builder or other off-market outreach; or
* both in parallel.

The current target is a post-New Year window. This is not yet a precise,
committed date and may become more specific after consultation with the
realtor.

The existing task `Put current home on the market` should not be treated as the
definition of this milestone without further design. A public listing is only
one possible channel. The completed walkthrough did not resolve whether that
Task remains a separate executable action, is renamed as public-listing work,
or is eventually replaced by the broader Milestone representation.

## Decision: select the initial home-sale strategy

The unresolved decision is **Select the initial home-sale strategy**. Current
credible decision options are:

* Publicly list the house in its current, as-is condition, potentially at a
  lower price.
* Complete selected repairs and then publicly list it.
* Pursue a builder or other off-market buyer.
* Pursue builder outreach and public-market preparation in parallel.
* Revise the approach after receiving initial market feedback.

The initial selection does not necessarily end the decision forever. Changed
market evidence may justify revisiting it.

## Evidence needed from the realtor

The family needs a ballpark market assessment, not definitive answers. It
should provide enough evidence to compare the credible strategies and should
address:

* current owner-occupant interest in the neighborhood, given the number of
  teardowns and new-construction projects;
* a plausible sale-price range for an as-is public listing;
* whether the visibly nonfunctioning pool would merely reduce the likely price
  or make an as-is public listing impractical;
* a plausible builder or off-market offer range;
* which repairs, if any, would materially improve marketability or expected net
  proceeds;
* approximate timing, uncertainty, and risk for each route; and
* material differences in commissions, concessions, preparation costs, repair
  costs, carrying costs, or other scenario-dependent expenses.

Ranges and confidence-qualified estimates are sufficient when precision is not
available. GoTime should not imply that uncertain evidence is exact.

## Financial constraint and comparison preferences

The hard constraint is:

> Retain at least the family's minimum acceptable net proceeds after the sale.

Four financial ideas must remain distinct:

* **Gross sale price** is the amount paid for the home before deductions.
* **Scenario-specific costs** are the commissions, concessions, preparation,
  repairs, carrying costs, and other expenses that vary by route.
* **Estimated net proceeds** are the estimated gross sale price less the
  relevant scenario-specific costs. They should normally be expressed as a
  range with uncertainty rather than as false precision.
* **Minimum acceptable net proceeds** is the private threshold an option must
  satisfy to remain viable.

The family's historical minimum-sale-price assumption remains useful as an
input or estimate because many transaction costs were expected to be mostly
static. It is not the underlying hard constraint.

Among options that satisfy the hard constraint, the family prefers:

* greater expected net proceeds;
* greater confidence in the estimate;
* less upfront spending;
* less repair work and household disruption;
* greater certainty;
* suitable launch and closing timing; and
* lower risk that the expected result will not materialize.

A lower gross sale price may therefore remain acceptable when it produces
sufficient net proceeds with materially lower cost, effort, delay, or risk.

## Conditional work and dependencies

Repair completion is not a universal hard prerequisite for this milestone:

* An as-is public listing may require no repair work.
* A repair-first public listing activates only the selected repair work.
* Builder or off-market outreach should not be blocked by public-listing
  preparation.
* If both channels are selected, their work can proceed in parallel.

Some work may still be a hard prerequisite for a specific route. Other work
may merely support the campaign or need to be timed near its launch. The route
must be known before GoTime can distinguish those relationships responsibly;
an existing task dependency alone should not be assumed to encode that
meaning.

## Why the realtor deserves attention now

The current actionable sequence is:

1. Reengage with the realtor.
2. Obtain enough market evidence to compare credible sale strategies.
3. Decide the initial home-sale strategy.
4. Activate only the work required by the selected strategy.
5. Coordinate the active work toward the post-New Year sale-launch milestone.

`Reengage with the realtor` describes the outcome of meeting with the realtor
and obtaining the initial assessment. Its next actionable subtask deserves
attention now because that work is ready, produces evidence required for a
consequential decision, and unlocks multiple downstream branches. That
conclusion should follow from the scenario's facts, not from a manually
assigned Critical/High/Medium/Low priority or an arbitrary task start date.

This demonstrates an important derived-attention pattern:

```text
actionable evidence-gathering work
  -> decision readiness
  -> selected option
  -> conditional work becomes relevant
  -> coordinated progress toward the milestone window
```

Planning knowledge may help interpret typical preparation, lead times, timing
windows, and prerequisite patterns. Deterministic reasoning must still combine
that knowledge with the family's actual constraint, preferences, evidence, and
plan state.

## Completed manual reasoning walkthrough

The walkthrough confirms the behavior GoTime should eventually support. It
does not select database entities, Pydantic schemas, API contracts, or
interface components.

### State 1: work is actionable

The plan has the post-New Year sale-launch Milestone, the open home-sale
strategy Decision, a missing realtor assessment, the parent Task `Reengage with
the realtor`, and actionable subtasks under that parent.

GoTime should recommend an actionable leaf-level subtask:

> **Do now: Contact the realtor**
>
> Part of: Reengage with the realtor
>
> This work will provide market evidence needed to select a home-sale strategy
> and determine which work should proceed toward the sale-launch milestone.

The attention state and explanation are derived because the subtask is
actionable, contributes to required evidence, helps unlock a consequential
Decision, and advances a meaningful Milestone. Neither manual priority nor an
arbitrary start date is required.

### State 2: the parent progresses through required subtasks

`Reengage with the realtor` represents the completed outcome of meeting with
the realtor and obtaining the initial assessment, not merely scheduling the
meeting. Possible required subtasks are:

* Contact the realtor.
* Schedule the meeting.
* Prepare the questions and sale scenarios.
* Gather relevant information beforehand.
* Meet with the realtor.
* Record the assessment and follow-up questions.

The smallest provisional behavior supports one level of subtasks and treats
every subtask as required. GoTime recommends actionable leaf-level subtasks,
while the parent supplies their purpose and context.

Parent status is derived automatically:

* **Not started** when no required subtask has begun.
* **In progress** when at least one required subtask has begun and one or more
  remain incomplete.
* **Completed** when every required subtask is complete.

Completing the final required subtask automatically completes the parent and
satisfies dependencies that point to the parent. This is a reversible
convenience, not irreversible system authority. Reopening a subtask, adding
required work, or otherwise correcting the plan recalculates the parent. The
exact interaction for a direct parent-status override remains an implementation
design question.

### State 3: the Decision becomes ready

When the required realtor work is complete, GoTime may derive that the
home-sale strategy Decision is ready for consideration. If the meeting exposes
another gap—for example, the realtor must research recent builder purchases—new
evidence-producing work may be added and the Decision can remain in a
gathering-information state.

Decision readiness is advisory. GoTime may warn that expected evidence is
incomplete, but the user may still select an option. GoTime must never select a
Decision option automatically.

> GoTime may derive, recommend, explain, and warn, but the user retains final
> authority.

### State 4: conditional work activates

When the user selects a strategy:

* work associated with a selected Decision outcome becomes active;
* work associated only with unselected outcomes remains preserved but
  inactive;
* inactive work is hidden by default and can be revealed through Show inactive
  work;
* inactive work is excluded from ordinary counts, attention states, and
  Recommendations;
* search can still locate inactive work, identifies it as inactive, and lets
  the user reveal its location; and
* users may manually activate work when circumstances require it.

Activation is separate from progress status. Status describes whether work is
Not started, In progress, or Completed. Activation describes whether the work
currently belongs to the active plan. An inactive Task is not equivalent to a
Not started Task.

Selecting builder outreach plus an as-is public listing therefore activates
the builder-outreach and as-is public-listing branches, preserves repair-first
work as inactive, and lets GoTime recommend actionable leaf-level work from the
active branches.

### State 5: a Decision is revised

A Decision may be revised after work has begun. GoTime must:

* never delete alternate-branch work merely because it is inactive;
* never silently deactivate an In progress Task;
* show which Tasks would be affected and ask which should remain active;
* preserve completed work as plan history; and
* let the user retain or reactivate Tasks when reality differs from the
  original branch assumptions.

The detailed revision workflow remains implementation-design work.

### State 6: the Milestone is achieved

Completing supporting Tasks does not prove that the real-world sale campaign
has launched. When the selected sale channels are genuinely active, the user
explicitly marks the Milestone achieved. GoTime may prompt or recommend that
confirmation, but it must not assert the real-world outcome automatically.

## Smallest provisional representation

The walkthrough exposes this minimum set of domain concepts and relationships:

* a Milestone with a target date or window and explicit user-confirmed
  achievement;
* a Decision with options and an unresolved or resolved state;
* advisory Decision readiness;
* one level of required subtasks;
* automatically derived, reversible parent-Task status;
* a relationship showing that work informs a Decision;
* conditional work associated with Decision outcomes;
* activation state separate from Task progress status;
* relationships connecting Decisions and work to Milestones; and
* user-visible reasoning explanations.

For the initial slice, evidence requirements, hard constraints, and preferences
may remain information recorded within the Decision rather than separate
first-class domain concepts. Whether Evidence need eventually becomes its own
domain concept remains open.

This list defines required product meaning. It does not imply one database
entity per concept, nor does it define a Pydantic schema, API shape, interface,
or AI model. The implementation design should seek the fewest durable concepts
that preserve these semantics.

## Proposed smallest implementation slice

The first vertical slice should prove the main reasoning loop in this order:

1. Represent one Milestone with a target window and explicit user-confirmed
   achievement, one user-owned Decision with options, one parent Task with one
   level of required subtasks, and the minimum relationships that connect the
   work to the Decision and Milestone.
2. Derive parent status from required subtasks and recommend only actionable,
   active leaf-level Tasks with an explanation of their parent context,
   Decision-unlocking value, and Milestone contribution.
3. Derive advisory Decision readiness from completion of the identified
   evidence-producing work while still allowing the user to decide before or
   after that point. Only the user selects an option.
4. Activate work associated with selected outcomes; preserve other branches as
   inactive, omit them from ordinary counts and Recommendations, and make them
   deliberately revealable and findable.
5. Let the user explicitly confirm Milestone achievement; never infer the
   real-world event from completed supporting work.

For this slice, users may manually record evidence requirements, constraints,
preferences, option descriptions, and the Milestone window as ordinary
Decision or Milestone information. Users also remain responsible for selecting
and revising options, adding newly discovered evidence work, manually
activating exceptions, and confirming achievement.

Deterministic behavior is limited to leaf-level recommendation eligibility,
reversible parent-status derivation, advisory readiness from identified work,
branch activation after a user choice, inactive-work exclusion, and the
reasoning explanation. This is sufficient to test value without automating the
Decision itself.

Defer nested or optional subtasks, detailed direct-parent overrides, structured
evidence/confidence, first-class Constraint or Preference representation,
calculated net proceeds, private-value controls, general Decision revision
workflows and history, automatic Milestone-window refinement, planning-knowledge
integration, AI assistance, and generalized cross-plan behavior.

### Observable acceptance scenario

Given the documented sale-launch Milestone, strategy Decision, realtor parent
Task and required subtasks, and conditional sale-strategy branches:

1. GoTime recommends `Contact the realtor` as Do now and explains its parent,
   evidence, Decision, and Milestone context.
2. Completing required leaf Tasks advances and finally completes the parent,
   making the Decision advisory-ready; reopening one reverses that derivation.
3. The user selects builder outreach plus an as-is public listing, which makes
   those branches active while repair-first work remains preserved, inactive,
   hidden from ordinary views and counts, excluded from Recommendations, and
   discoverable through explicit reveal or search.
4. GoTime recommends the next actionable leaf Task from an active branch.
5. Completing that work does not complete the Milestone; the user confirms the
   launch only after the selected channels are genuinely active.

Review and approve this proposed slice before any schema, API, or interface
design begins.

## Remaining product-design questions

The walkthrough resolved the minimum behavioral direction but leaves these
questions open:

* How should Decision evidence and confidence eventually be structured?
* What direct parent-status override, if any, should exist?
* Should the existing `Put current home on the market` Task remain separate,
  become conditional public-listing work, or be replaced by the Milestone?
* What exact review interaction should protect In progress work when a Decision
  is revised, and how should previous outcomes and rationale be retained?
* How should private financial constraints be stored or hidden?
* How does a target Milestone window become more precise?
* How should estimated net proceeds be calculated without creating false
  precision?
* Does Evidence need require a first-class domain concept, or can it continue
  to use ordinary Tasks and Decision information?

These remain product-design questions, not commitments to persistence or
interface structures.
