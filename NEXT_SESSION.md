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

# Frontend Recommendation Integration

## Status

Implementation is complete, reviewed, and verified.

The existing concept screen now:

* Loads the original Recommendation from the backend by default.
* Displays the complete human-readable explanation, dependencies, blocked
  work, and related employment Assumption.
* Uses a temporary scenario control to request either the unclear or clarified
  employment-requirements snapshot.
* Handles loading, failed requests, and obsolete responses.

## Intended-User Feedback

The current frontend is acceptable for this stage and successfully demonstrates
the end-to-end reasoning loop.

The interface is still too early to evaluate meaningfully for layout or visual
refinement. Do not begin a redesign yet.

The current language feels clinical and dry because it exposes internal
reasoning vocabulary too directly, including phrases such as:

* Partially ready
* Relevant dependencies
* Blocked downstream work
* Unconfirmed assumption

This language is acceptable for the current proof. Future user-facing copy
should translate internal reasoning concepts into warmer, more natural
guidance. For example:

> **What to focus on now**
>
> Clarify what kind of work would be acceptable for your spouse before
> narrowing the location search.

## Deferred Language and UI Concerns

Treat the clinical language and early visual design as documented product
concerns, not immediate polishing tasks. Revisit them after the interaction and
reasoning model are more mature, when user feedback can evaluate the experience
in a more meaningful context.

# Meaningful State Input

## Status

Implementation is complete, reviewed, and verified.

* The temporary scenario selector has been replaced with a realistic
  confirmation action attached to the current Recommendation.
* The user can confirm that spouse employment requirements have been clarified.
* That confirmation triggers re-reasoning and produces a new Recommendation.
* The suitable-employment Assumption remains unconfirmed.
* The interaction remains intentionally local and non-persistent.
* Frontend, backend, Docker, and integration verification all pass.

# Next Milestone — Capture One Concrete Employment Requirement

## Status

Implementation is complete, reviewed, and verified.

* The user can submit one actual requirement: an acceptable remote, hybrid,
  on-site, or flexible work arrangement.
* No submitted value preserves the original Recommendation and means the
  requirement remains unclear.
* The submitted value is represented on the in-memory Goal snapshot and is the
  only source of truth for whether this requirement has been clarified.
* Each accepted value produces meaningful, deterministic reasoning about how
  to evaluate candidate locations.
* The suitable-employment Assumption remains unconfirmed for every value.
* Work arrangement remains only one part of employment suitability.
* Candidate locations are not yet scored or compared.
* State remains intentionally local and non-persistent.
* Frontend, backend, Docker, integration, and query-validation checks pass.

# Next Milestone — Capture One Concrete Commute Requirement

## Status

Implementation is complete and verified.

* Hybrid and on-site paths ask for the longest acceptable one-way commute.
* The user can submit a positive whole-number limit in minutes.
* `acceptable_commute_minutes` is represented as a hard, user-provided
  evaluation boundary in the in-memory Goal snapshot.
* Contradictory arrangements and invalid limits return HTTP 422.
* The Recommendation uses the limit when explaining how candidate locations
  should be evaluated.
* The engine does not treat the limit as an observed commute, calculate travel
  time, or claim that any candidate location passes or fails.
* A likely workplace location and credible travel-time evidence are still
  required. Hybrid frequency also remains unknown.
* Suitable employment remains an unconfirmed Assumption.
* State remains intentionally local and non-persistent.
* Frontend, backend, Docker, integration, compilation, and whitespace
  verification pass.

# Next Milestone — Capture a Likely Workplace Area

## Status

Implementation is complete and verified.

* The user can provide one free-form likely workplace area after submitting a
  hybrid or on-site arrangement and maximum one-way commute.
* The value is trimmed, limited to 120 characters, and treated as opaque
  user-provided planning context.
* The API rejects blank, over-length, and prerequisite-incompatible values.
* The Recommendation advances from defining commute requirements to gathering
  credible one-way travel-time evidence.
* The engine does not verify or normalize the area, geocode it, calculate a
  route, or claim that any candidate location passes or fails.
* Traffic conditions and travel mode remain unresolved. Hybrid frequency also
  remains unresolved for hybrid work.
* Suitable employment remains an unconfirmed Assumption.
* State remains intentionally local and non-persistent.
* Frontend, backend, Docker, integration, compilation, and whitespace
  verification pass.

# Next Milestone — Capture an Intended Commute Travel Mode

## Status

Implementation is complete and verified.

* `intended_commute_travel_mode` records user-provided relocation planning
  context as `drive`, `public_transit`, or `either`.
* `either` means driving and public transit are both acceptable and evidence
  should be gathered for both; it does not mean unknown.
* A mode is accepted only after hybrid or on-site work, a maximum one-way
  commute, and a likely workplace area have been supplied.
* A supplied mode changes the Recommendation by identifying which manual
  travel-time evidence should be gathered.
* Mode-specific explanations preserve unresolved driving traffic, transit
  schedules, transfers, station access, and hybrid frequency where applicable.
* No route, travel time, workplace, candidate viability, or suitable
  employment has been verified.
* State remains intentionally local and non-persistent.
* Frontend, backend, Docker, integration, compilation, and whitespace
  verification pass.

# Next Session — Decide Where AI Assistance Should Enter GoTime

## Objective

Review the deterministic reasoning prototype and decide where AI-assisted
interpretation or suggestion should first enter GoTime.

## Questions to Examine

* What does the deterministic engine already prove?
* Which current Recommendations, explanations, and scenario inputs are still
  scripted?
* Which responsibilities should remain deterministic?
* Which narrow capability would genuinely benefit from AI?
* How would AI-generated suggestions remain grounded in known state,
  transparent to the user, and covered by repeatable tests?
* Is another deterministic input necessary before introducing AI assistance?

## Expected Outcome

Select one narrow, evidence-backed capability for a future milestone, or decide
that the deterministic prototype needs one more input first. Do not begin AI
integration merely because the current scripted flow has reached a natural
review point.

Hybrid commute frequency remains a possible future deterministic input, but it
is not the committed next implementation milestone.

## Out of Scope

* Implementing an AI model call
* Selecting broad AI infrastructure
* Replacing deterministic validation or state transitions
* Persistence or authentication
* Mapping, routing, geocoding, or transit integrations
* Candidate-location scoring
* Broad frontend redesign

Keep the empty `docs/adr/ADR-0001-monorepo.md` issue separate from this
session.

# First Fake-Adapter Slice — Suggest Moving-Service Questions

## Status

Implementation is complete, verified, and ready for review.

The slice now:

* Constructs a bounded `suggest_moving_service_questions` request from narrow
  trusted experiment fixtures.
* Invokes one capability-specific fake adapter after an explicit user action.
* Validates the complete structured response deterministically.
* Rejects invalid responses without retaining individual suggestions.
* Uses one frozen deterministic fallback question when an applicable gap
  remains.
* Returns a valid no-question result when all supported information is known.
* Presents one optional question beneath the primary deterministic
  Recommendation.
* Lets the user dismiss the suggestion, inspect its grounding, or confirm a
  boolean answer locally.
* Leaves the current trusted `Goal` unchanged and does not trigger
  re-reasoning.
* Records bounded observability with a `$0.00` fake-adapter cost.

The temporary fixture endpoint supports:

* `storage_unknown`
* `complete`
* `invalid_ai_response`
* `adapter_unavailable`
* `adapter_timeout`
* `budget_unavailable`
* `ai_disabled`

Unsupported fixtures and unexpected query parameters return HTTP 422.

## Review Focus

* Confirm that the request contains only approved experiment context.
* Confirm that response validation rejects the complete invalid response.
* Confirm that fallback guidance remains useful and is not presented as an
  error.
* Confirm that source labels are helpful without emphasizing implementation
  mechanics.
* Confirm that local answer confirmation cannot update trusted state.
* Decide whether the in-code fallback baseline and temporary fixture artifacts
  should be reconciled with the older draft `v1` JSON artifacts in a separate
  documentation-and-fixture slice.

## Explicitly Not Proven

This slice does not prove that AI adds product value or that the experiment
knowledge is sufficient for real-model use. No real-model work may begin until
curated statements have approved sources, the knowledge fixture is versioned
for that purpose, and the fake-adapter contract is approved.

# V1 Artifact Reconciliation — Suggest Moving-Service Questions

## Status

Implementation is complete, verified, and ready for review.

The older `v1` package now:

* Uses the exact runtime knowledge-item, missing-information, fallback,
  trusted-state, request, and response vocabulary.
* Contains executable `storage_unknown`, `complete`, and contract-only
  multiple-gap request fixtures.
* Contains valid, zero-suggestion, and eight invalid response fixtures.
* Records expected valid, invalid, fallback, unavailable, timeout,
  budget-unavailable, disabled, no-question, and observability outcomes.
* Delegates request construction, response validation, fallback selection, and
  orchestration expectations to the runtime implementation.
* Separates contract-test readiness from real-model-evaluation readiness.
* Is contract-test eligible and explicitly ineligible for real-model
  evaluation.

The knowledge artifact contains only the current storage implementation
fixture. It is valid for fake-adapter and compatibility testing, has no
approved real-model grounding source, and does not imply that the broader
six-model knowledge set is complete.

Production runtime remains independent from `docs/`. Backend anti-drift tests
load the package; application execution does not.

## Review Focus

* Confirm the artifact package contains no legacy nested claim schema.
* Confirm manifest readiness values and reasons are accurate.
* Confirm artifact compatibility tests use runtime behavior rather than a
  second implementation.
* Confirm the narrow knowledge boundary is not overstated.
* Confirm no real-model work begins until a separately reviewed knowledge
  curation step satisfies the documented gate.

# Next Session — Curate Knowledge for the First Real-Model Evaluation

## Status

Implementation complete and verified. The approved FMCSA-backed fixture is
eligible only for a controlled real-model evaluation of the `storage_unknown`
question suggestion. No real model has been connected.

## Previous Milestone

The moving-service experiment artifacts have been reconciled with the approved runtime contract.

The current experiment now has:

* A bounded request contract.
* A structured response contract.
* A fake adapter.
* Complete-response validation.
* A deterministic fallback.
* A browser-based experiment flow.
* Executable artifact fixtures.
* Runtime anti-drift tests.
* Separate readiness flags for:

  * Contract testing
  * Real-model evaluation

The artifact package is currently:

* `contract_test_eligible: true`
* `real_model_evaluation_eligible: true`

This readiness is limited to the controlled `storage_unknown` evaluation. It
does not mean production approval, complete moving-service knowledge, or
readiness for service-model comparison.

## Next Objective

Create the smallest reviewed, source-backed moving-service knowledge fixture needed to evaluate:

`suggest_moving_service_questions`

against the `storage_unknown` scenario.

This session should determine whether a real model can be given trustworthy, bounded knowledge for suggesting this question:

> Will you need temporary storage between homes?

The session should not connect a real model.

## Product Question

Can GoTime ground one useful moving-service question in reviewed domain knowledge without requiring a broad moving-industry knowledge library?

## Knowledge Scope

Curate only the knowledge needed to establish that temporary storage needs can affect which moving-service approaches are practical to investigate.

The knowledge should support question discovery.

It does not need to provide:

* A complete comparison of moving-service models.
* A recommended moving-service model.
* Provider-specific guidance.
* Pricing.
* Availability.
* Booking windows.
* Rankings.
* Current market research.

## Required Knowledge Item Fields

Each approved knowledge item must include:

* `knowledge_id`
* `service_model`
* `statement`
* `tradeoff_category`
* `applicable_conditions`
* `source`
* `reviewed_at`
* `freshness_guidance`
* `version`

The statement must be:

* Narrow.
* Directly supported by the cited source.
* Relevant to the storage question.
* Free of provider selection or ranking.
* Stable enough that live research is unnecessary.
* Appropriate for a controlled question-suggestion evaluation.

## Source Requirements

Use authoritative or primary sources where reasonably available.

For each source, record:

* Publisher
* Title
* Stable locator
* Date accessed or reviewed
* The specific claim it supports
* Any limitations

The source must be read and reviewed rather than merely collected.

Do not use:

* Unattributed AI summaries.
* Unsupported generalizations.
* Placeholder citations.
* Provider marketing as evidence for broad industry-wide claims unless its limitations are explicit.
* Current pricing or availability claims.
* Information that requires live research to remain reliable.

## Review Questions

For each proposed statement, ask:

* Is this statement necessary for the `storage_unknown` fixture?
* Does the source directly support it?
* Is the wording narrower than or equal to what the source establishes?
* Does it avoid recommending a service model?
* Does it avoid implying that temporary storage is definitely required?
* Is it stable enough for curated knowledge?
* What freshness guidance should apply?
* Would the statement remain useful if the user ultimately does not need storage?
* Does the complete bounded request remain within the experiment’s token budget?

## Artifact Updates

After the knowledge has been reviewed:

* Update `curated-knowledge.json`.
* Update the manifest knowledge version.
* Update any affected request or expected-result fixtures.
* Update knowledge references where necessary.
* Preserve compatibility with the runtime `CuratedKnowledgeItem` model.
* Keep production runtime independent from files under `docs/`.

Do not mark the package as real-model eligible merely because the JSON validates.

## Readiness Decision

At the end of the session, explicitly decide whether:

`real_model_evaluation_eligible`

can change from `false` to `true`.

It may become `true` only if:

* Every included statement has an approved source.
* Every statement is narrowly supported.
* Review and freshness metadata are complete.
* The artifact/runtime compatibility tests pass.
* The full request remains within the declared token budget.
* The fake-adapter and deterministic-fallback tests still pass.
* No placeholder or unreviewed knowledge remains in the evaluated fixture.

If any requirement remains unmet, keep the flag `false` and record the exact ineligibility reasons.

## Deliverables

The session should produce:

* One or more reviewed knowledge statements sufficient for the storage-question fixture.
* Complete source and freshness metadata.
* Updated versioned artifacts.
* Updated readiness metadata.
* Tests confirming artifact/runtime compatibility.
* A brief review note explaining what the knowledge is approved to support.
* An explicit statement of what it is not approved to support.

## Out of Scope

Do not add:

* A real model adapter.
* An AI SDK.
* API credentials.
* Live web research during application execution.
* Provider recommendations.
* Provider rankings.
* Quotes or availability.
* Booking-window logic.
* A complete six-model moving-service library.
* Vector infrastructure.
* Persistence.
* Automatic trusted-state updates.
* General-purpose chat.
* Background AI activity.

## Definition of Done

This milestone is complete when:

* The storage-question knowledge fixture contains no placeholders.
* Every included statement has been human-reviewed against an identifiable source.
* Statements are bounded to the first experiment.
* Freshness guidance and versions are recorded.
* Runtime and artifact compatibility tests pass.
* The deterministic fallback remains unchanged and useful.
* The package’s real-model readiness status is reviewed explicitly.
* No real model has been connected.

## Later Milestone

Only after the knowledge fixture is approved should GoTime design the real-model adapter and controlled evaluation run.

That later milestone should compare real-model suggestions against the frozen deterministic fallback using the approved fixtures, rubric, cost ceiling, and latency limits.
