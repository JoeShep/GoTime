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
one possible channel. The manual walkthrough must determine whether that task
remains a separate executable action, is renamed, or is eventually replaced by
a broader milestone representation.

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

`Reengage with the realtor` deserves attention now because it is actionable,
produces evidence required for a consequential decision, and unlocks multiple
downstream branches. That conclusion should follow from the scenario's facts,
not from a manually assigned Critical/High/Medium/Low priority or an arbitrary
task start date.

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

## Unresolved product-design questions

The manual walkthrough must keep these questions explicit:

* How should decision evidence and its confidence be represented?
* How should conditional task activation work?
* Can a decision be revised, and how should prior outcomes and rationale be
  retained?
* How should private financial constraints be stored or hidden?
* How does a target milestone window become more precise?
* How should estimated net proceeds be calculated without creating false
  precision?
* Does an evidence need require a first-class domain concept, or can it
  initially be represented through ordinary tasks and notes?

These questions are active design work, not commitments to new persistence or
interface concepts.

## Next design exercise

Walk through this scenario manually and determine the smallest representation
GoTime needs to produce and explain the five-step actionable sequence above.
The walkthrough should identify which existing plan facts are sufficient,
which meanings cannot be recovered from current tasks and dependencies, and
which missing facts are essential.

Stop after proposing that minimal representation for review. Do not design a
schema or interface until the walkthrough has shown what the product actually
needs.
