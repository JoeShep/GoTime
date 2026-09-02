# GoTime
GoTime helps people make better decisions while pursuing complex goals by combining strategic reasoning with operational sequencing.

It began with a simple question:

> **What should we do next?**

GoTime is designed to help people organize, prioritize, and complete meaningful goals. It starts by solving one very specific problem: planning and executing a major relocation. Over time, it will grow into a platform for managing any complex personal or family project, whether that's renovating a house, planning a wedding, starting a business, or preparing for retirement.

The goal is not to create another to-do list. Plenty of applications already do that well.

The goal is to help people make better decisions about their time by showing them the next piece of work that will move them closer to completing a goal.

## The First Real User

GoTime did not begin as an idea for a productivity application.

It began with a real problem.

My family is planning a move across the country. As we started planning, we realized the challenge wasn't simply keeping track of tasks. The challenge was understanding priorities, dependencies, timing, and deciding what to do next.

That relocation became the first real project GoTime was designed to support.

Because of that, every proposed feature should answer a simple question:

> **Would this have made planning and executing our move easier?**

If the answer is yes, the feature is probably aligned with GoTime's purpose.

If the answer is no, we should carefully consider whether it belongs in the product.


Guiding Principles
+ Simple enough to use every day.
+ Organized around goals instead of isolated tasks.
+ Prioritize work based on context, dependencies, and importance.
+ Support collaboration between family members.
+ Grow through thoughtful, incremental improvements instead of adding features for their own sake.

## Derived Attention

GoTime should determine what deserves the user's attention now rather than
requiring the user to manually rank every task. The product should derive an
attention state from the plan's current facts and explain why that state
applies.

The working attention states are:

* **Do now**
* **Coming soon**
* **Later**
* **Waiting**

These are calculated states, not manually selected task priorities. Their final
names and precise rules remain subject to validation against the real family
plan. Potential deterministic inputs include target and due dates, start dates
and eligibility, dependencies and blocked state, progress and momentum,
immediate unblocking leverage, phase and sequencing context, user-specific
constraints and consequences, and planning lead times or timing windows.

The existing Critical, High, Medium, and Low task priority field is expected to
be demoted or potentially retired from ordinary task creation and
recommendation ranking. Preserve the field and all stored values until derived
attention has been designed and validated.

## Now and Plan

GoTime's ordinary family experience should separate attention from plan
management. **Now** answers the product's central question with one primary
Recommendation, its concise explanation, and only Decisions or Milestones that
currently require attention or provide necessary context. **Plan** provides the
complete editable structure through compact Milestone and Decision sections,
search and filtering, and initially collapsed Task phases.

The persisted plan title is the user's **Our goal** on Now; a separate static
goal label should not compete with it. Additional Now items must wait for valid
derived-attention signals and must not be inferred from legacy priority alone.
Suspended experiments are not part of ordinary family navigation. The approved
presentation direction is detailed in the
[Now, Plan, and Experiments design](technical-design/now-plan-experiments.md).

The [home-sale strategy reference scenario](reference-scenarios/home-sale-strategy.md)
is the first concrete test of this direction. It combines a milestone window,
an unresolved decision, a hard financial constraint, comparison preferences,
incomplete evidence, conditional work, and route-specific dependencies. It
should explain why gathering realtor evidence deserves attention now without a
manual priority level or arbitrary start date. Its human-facing Milestone is
**Start selling our home**; the user confirms achievement only when the chosen
buyer-seeking channels are genuinely active.

## AI-Assisted Planning Knowledge

AI-assisted planning knowledge is an intentional future capability. An AI
model may propose structured knowledge that users cannot reasonably be expected
to supply, such as typical lead times, prerequisite patterns, likely durations,
and recommended timing windows. Consequential knowledge must be inspectable,
carry appropriate source, confidence, and freshness information, and allow the
user to correct consequential assumptions.

Deterministic rules—not an opaque AI response—must combine planning knowledge
with the family's actual plan state to derive attention and recommendations.
Routine UI interaction must not invoke AI. Reusable knowledge should be cached,
and live research should occur only when freshness materially affects the
result. Existing credential boundaries, cost tracking, budgets, and operational
simplicity remain applicable.

This direction does not authorize resuming the frozen moving-service experiment
or implementing new AI infrastructure. The intended sequence is:

1. Define derived attention states and deterministic inputs.
2. Test a no-AI baseline against representative tasks in the real family plan.
3. Identify missing facts that prevent good recommendations.
4. Define a structured planning-knowledge contract for those facts.
5. Revisit and adapt the existing AI API pipeline to supply that contract.
6. Compare AI-enriched recommendations with the deterministic baseline.

## Project Goals

The first milestone is to establish a solid application architecture before implementing core features.

The initial technology stack includes:

* React with TypeScript
* FastAPI
* Docker Compose

Additional technologies will be introduced only when they solve a real problem.

## Operating Principle

GoTime should remain inexpensive and operationally simple. Deterministic
reasoning comes first; curated knowledge is preferred over live research, and
AI is used only for selective, named capabilities with grounded, testable
outputs and deterministic fallback behavior.

For early family and tester use, the product should target approximately
$25–$50 per month or less, operate within a configurable monthly spending
ceiling, and remain deployable on small, maintainable infrastructure. See
`docs/cost-and-operations.md` for the complete guardrails.

## Documentation

* `docs/adr/` - Architecture Decision Records documenting significant technical decisions.
* `docs/product-vision.md` - The long-term vision for GoTime.
* `docs/reasoning-engine.md` - Defines how GoTime thinks
* `docs/ai-assisted-reasoning.md` - Defines bounded AI capabilities and their relationship to deterministic reasoning.
* `docs/cost-and-operations.md` - Defines cost and operational guardrails.
* `docs/capability-roadmap.md` - Defines what the reasoning engine can be expected to do, and where the dividing lines are between the AI and the app (For lack of a better way to put it)

Vision tells us why.
Reasoning Engine tells us what the engine must be capable of thinking about.
Capability Roadmap tells us what we build next to realize that vision.
The code implements those capabilities.
