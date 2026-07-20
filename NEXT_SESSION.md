# NEXT_SESSION

## Goal

Design the first version of GoTime's reasoning engine by observing how an experienced project manager plans a real relocation.

The objective is not to create a task hierarchy. The objective is to discover how GoTime should think.

## Tasks

* [ ] Role-play a relocation planning session.
* [ ] Capture every question the project manager asks.
* [ ] Record every recommendation and the reasoning behind it.
* [ ] Identify facts, rules, and inferences revealed during the conversation.
* [ ] Note any new domain concepts that emerge naturally.
* [ ] Update `docs/reasoning-engine.md` with the results.

## Success Criteria

By the end of the session we should understand:

* What information the reasoning engine requires.
* How it reaches recommendations.
* How it explains its recommendations.
* Which domain concepts naturally emerge from the planning conversation.

Domain terms such as Goal, Project, Phase, Task, Milestone, and Dependency should be refined only after the reasoning process is better understood.

## Notes

Treat the conversation as requirements discovery.

Do not design the database.

Do not design user interfaces.

Focus entirely on understanding how GoTime should reason about a complex goal.

# First Reasoning Loop

## Status

Implementation complete, reviewed, and verified. The changes are ready to commit.

## Scenario

The user wants to relocate from Tennessee to Northern California.

The target location has not been selected.

The spouse's employment requirements are still unclear.

Several downstream decisions depend on location.

## Expected Recommendation

> Clarify spouse employment requirements before choosing a final target location.

## Explanation

- Employment location affects housing affordability.
- Employment location affects commute viability.
- The target location decision is only partially ready.
- Housing search and neighborhood research depend on that decision.

## Implementation Scope

- Create in-memory models for:
  - Goal
  - SuccessCriterion
  - Constraint
  - Preference
  - Decision
  - Assumption
  - Recommendation
- Hard-code one relocation scenario.
- Implement one deterministic reasoning rule.
- Return one Recommendation with an explanation.
- Add tests for the reasoning rule.

## Out of Scope

- Database
- Authentication
- AI model calls
- Generic rule engine
- Frontend forms
- Multiple goals

## Review Focus

- Confirm the primary Recommendation is useful and trustworthy.
- Review whether the endpoint exposes the right explanation detail.
- Decide whether the existing static frontend should consume this endpoint in
  the next slice.

# Next Session (/19/2026) State Change and Re-Reasoning

## Previous Milestone

The first in-memory reasoning loop is complete, tested, verified through Docker, committed, and pushed.

The current backend:

* Builds one hard-coded relocation Goal snapshot.
* Identifies an unresolved employment-related dependency.
* Produces one deterministic primary Recommendation.
* Explains why the Recommendation matters now.
* Exposes the result through `GET /api/recommendations/primary`.
* Includes focused reasoning and endpoint tests.

## Next Objective

Demonstrate that GoTime can update its Recommendation when the known state changes.

The next slice should prove this loop:

```text
Represent state
→ Reason
→ Recommend
→ Change state
→ Re-reason
→ Produce a different Recommendation
```

## Initial State

The spouse's employment requirements are unclear.

The target-location Decision is only partially ready.

### Expected Recommendation

> Clarify spouse employment requirements before choosing a final target location.

## Updated State

The spouse's employment requirements have been clarified.

The separate Assumption that suitable employment exists in one or more viable candidate regions remains unconfirmed.

### Expected Recommendation

> Evaluate candidate locations against the clarified employment requirements.

The engine should not yet recommend selecting a final location because other information may still be unresolved, including:

* Housing affordability
* Commute viability
* Healthcare access
* Environmental risk
* Availability of suitable employment

## Implementation Scope

* Add the minimum state needed to distinguish:

  * Employment requirements unclear
  * Employment requirements clarified
* Build or derive a second immutable Goal snapshot representing the updated state.
* Add one deterministic reasoning path for the updated state.
* Return a different primary Recommendation for that state.
* Preserve the existing Recommendation for the original state.
* Add focused tests proving:

  * The original state produces the original Recommendation.
  * The updated state produces the new Recommendation.
  * The two states produce different results.
  * Both API responses remain valid and explained.

## Modeling Guidance

Keep the implementation narrow.

Do not introduce a generic state-management system or rule engine.

Clarifying employment requirements should not validate the Assumption that suitable employment exists.

The model should continue to distinguish:

* **Required information:** What employment conditions are acceptable?
* **Assumption:** Suitable employment exists within viable candidate regions.

Use immutable snapshots or model copies rather than mutating the existing Goal.

## API Question

Choose the smallest API design that demonstrates both states clearly.

Possible approaches include:

* A second temporary endpoint for the updated scenario.
* A query parameter selecting the scenario state.
* A narrowly defined request body that supplies the changed state.

Prefer the option that adds the least infrastructure while keeping the state transition understandable and testable.

Do not add persistence yet.

## Out of Scope

* Database persistence
* Authentication
* AI model calls
* Generic rule-engine infrastructure
* Generic dependency graphs
* Frontend forms
* User accounts
* Multiple Goals
* Production state management
* Broad domain-model expansion

## Review Focus

* Does the Recommendation genuinely change because the input state changed?
* Is the second Recommendation useful and appropriately cautious?
* Is the distinction between required information and Assumption validation preserved?
* Does the implementation remain deterministic and easy to understand?
* Is the API sufficient to demonstrate re-reasoning without prematurely designing persistence?
* Are explanations clear about what changed and why the Recommendation changed?

## Definition of Done

This slice is complete when:

* The original state produces the employment-requirements Recommendation.
* The updated state produces a different candidate-location evaluation Recommendation.
* Both reasoning paths have focused tests.
* The API exposes both results in a clear, minimal way.
* Docker verification passes.
* No persistence, generic rules framework, or unnecessary abstraction has been introduced.

## Implementation Status

Implementation is complete, reviewed, and verified. The next planned work is
described in the Later Slice below.

The temporary API proof supports:

* No query parameter or `employment_requirements=unclear` for the original
  Recommendation.
* `employment_requirements=clarified` for the updated Recommendation.
* HTTP 422 for unsupported query values or recognized states without an
  applicable reasoning path.

## Later Slice

After state change and re-reasoning are proven, connect the existing frontend concept screen to the Recommendation endpoint.
