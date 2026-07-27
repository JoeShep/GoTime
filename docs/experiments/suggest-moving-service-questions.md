# Experiment — Suggest Moving-Service Questions

## Experiment Status and Scope

```text
capability: suggest_moving_service_questions
AI capability: State Discovery Assistance
phase: design
```

This experiment tests whether bounded AI assistance can identify a useful
missing question while a user is deciding which moving-service models are
worth investigating.

The experiment does not:

* Select or recommend a moving-service model.
* Search for or recommend a provider.
* Calculate dates.
* Supply or invent booking windows.
* Perform live research.
* Interpret an answer into trusted state.
* Modify trusted state or confirm an Assumption.
* Replace deterministic Recommendation eligibility or sequencing.
* Generate a plan.

The experiment may conclude that AI should not be used for this capability.
Passing schema validation or producing polished language is not enough to
justify product integration.

## Hypothesis

> Given bounded trusted relocation state, an unresolved moving-service-model
> Decision, explicitly missing information, and curated moving-service
> knowledge, AI can suggest zero to three relevant questions that improve
> Decision readiness without inventing facts, repeating known information, or
> selecting an option.

One high-value question is the expected default. A response should include a
second or third question only when each adds distinct, material value that the
first question does not provide.

Success would show that AI can prioritize context-sensitive discovery questions
and explain why they matter.

Success would not show that AI can:

* Choose a service model or provider.
* Safely interpret the user's answer.
* Compare current providers, pricing, or availability.
* Supply planning-window guidance.
* Perform date arithmetic.
* Improve the final relocation outcome.
* Replace deterministic validation, eligibility, or sequencing.

## Why This May Be AI-Worthy

A deterministic checklist can identify missing fields and present a fixed
question. The possible value of AI is narrower:

* Select the most useful question from several grounded possibilities based on
  interacting circumstances.
* Avoid questions made irrelevant by combinations of trusted facts.
* Explain why a question matters in the current situation.
* Identify when no supplied knowledge supports an additional useful question.

Different wording alone is not sufficient value. The experiment must compare
AI output with a frozen deterministic baseline. If a small maintainable
checklist performs as well, GoTime should keep the capability deterministic.

## Deterministic Trigger and Eligibility

The deterministic core owns eligibility. AI cannot decide when it should run.

The capability may be offered only when:

* The move is classified as interstate.
* A moving-service-model Decision exists and remains unresolved.
* Deterministic reasoning has identified missing information.
* Compatible curated moving-service knowledge is available.
* The capability, prompt, baseline, and fixture versions are supported.
* The monthly experiment budget remains available.
* The user explicitly requests or accepts AI assistance.

The eligibility result should be structured:

```text
eligible
ineligible_reason
decision_id
missing_information
knowledge_fixture_version
baseline_version
budget_available
```

If any prerequisite is absent, GoTime does not call AI and uses deterministic
behavior.

## Trusted Input Context

The following fields define an **experiment context contract**. They are not
claims about fields that already exist on the production `Goal` model.

```text
goal_summary
move_type
origin_region
destination_region
target_move_window
household_size
temporary_storage_need
packing_preference
willing_to_drive_rental_truck
cost_vs_convenience_preference
special_handling_needs
known_constraints
missing_information
open_decision
deterministic_recommendation
unconfirmed_assumptions
```

Optional information must distinguish:

* A known value
* Explicitly unknown
* Not applicable
* Not supplied to this capability

The context excludes:

* Entire conversation history
* Entire Goal history
* Unrelated personal details
* Raw application logs
* Current web research
* Provider-specific information
* Unconfirmed AI interpretations

The target move window may be supplied as context, but this experiment neither
calculates dates nor applies booking-window guidance.

## Curated Moving-Service Fixture

The experiment uses a small, versioned fixture rather than a broad knowledge
base.

It should contain one reviewed item for each category:

1. Full-service interstate carrier
2. Moving broker
3. Portable storage container
4. Rental truck
5. Freight or trailer service
6. Labor-only assistance

Each item contains:

```text
knowledge_id
service_model
description
relevant_circumstances
typical_tradeoffs
information_needed_to_evaluate_fit
source
reviewed_at
freshness_guidance
version
```

The fixture needs only enough information to ground questions about storage,
packing, driving willingness, cost sensitivity, specialty handling, and other
documented fit considerations.

The fixture does not include:

* Providers
* Current pricing
* Current availability
* Current regulations
* Booking-window rules
* Unsupported claims about which model is best

## Frozen Deterministic Baseline

The deterministic fallback is also the experiment baseline. It must be fully
defined and versioned before the first AI evaluation run.

The baseline includes:

* A curated checklist of moving-service questions.
* A mapping from each question to the information it clarifies.
* Deterministic applicability filters.
* Rules for removing questions about known information.
* A fixed priority ordering.
* Behavior when no checklist question remains.

Baseline behavior is:

1. Remove questions whose answers are already known.
2. Remove questions that deterministic state makes inapplicable.
3. Apply the frozen priority ordering.
4. Return the highest-priority remaining question or a structured no-question
   result.

The baseline version, checklist, filters, and priority ordering must not be
revised in response to individual AI outputs. A change requires an explicit,
versioned experiment revision and a new evaluation run. This prevents the
comparison target from moving during the experiment.

## AI Request Contract

The request is bounded and capability-specific:

```text
capability
prompt_version
request_id
trusted_state
missing_information
open_decision
deterministic_recommendation
curated_knowledge_items
baseline_version
maximum_suggestions
maximum_output_tokens
```

Required fixed value:

```text
capability: suggest_moving_service_questions
```

The request permits at most three suggestions, but directs the model to prefer
one high-value suggestion. Additional suggestions require distinct, material
value.

The request contains only the selected experiment context and relevant
knowledge items. It does not contain an unbounded conversation or Goal history.

## AI Response Contract

The response allows zero to three suggestions:

```text
capability
prompt_version
request_id
suggestions
no_suggestion_reason
```

Each suggestion contains:

```text
question
why_it_matters
information_it_would_clarify
affected_decision_id
relevant_knowledge_ids
grounding_summary
reason_not_deterministic
uncertainties
requires_user_confirmation
```

Contract rules:

* `suggestions` contains zero to three entries.
* One suggestion is the expected default.
* Every additional suggestion must clarify different information and add
  material value.
* `no_suggestion_reason` is required when `suggestions` is empty.
* `no_suggestion_reason` is absent when suggestions exist.
* `requires_user_confirmation` is always `true`.
* The response contains no command, patch, or proposed automatic state change.

`grounding_summary` identifies the supplied trusted context and knowledge IDs
that support the question. It cannot introduce an unsupported source.

`reason_not_deterministic` identifies the contextual ambiguity or interaction
that required AI prioritization. A generic claim that AI is helpful is invalid.

The later UI is not required to show every returned suggestion at once. It may
present only the highest-priority valid suggestion while retaining other valid
suggestions for later use or evaluation.

## Field Visibility

User-facing fields:

* `question`
* `why_it_matters`
* A concise form of `grounding_summary`
* Uncertainty that materially affects interpretation

Internal or diagnostic fields:

* `affected_decision_id`
* `relevant_knowledge_ids`
* `reason_not_deterministic`
* Full uncertainty codes
* Capability, prompt, fixture, baseline, and request versions

`information_it_would_clarify` may support presentation and later deterministic
routing. It is not the user's answer and does not satisfy missing information.

## Suggestion-Quality Rules

Every suggestion must follow these rules:

* Do not ask for information already present in trusted state.
* Do not repeat the deterministic Recommendation as a question.
* Do not ask unrelated questions.
* Ask one concept per question.
* Do not ask a compound question that cannot map to one missing-information
  category.
* Reference at least one supplied curated knowledge item.
* Explain how the answer could affect the open Decision.
* Do not assume that an unknown fact has a particular value.
* Do not recommend a moving-service model or provider.
* Do not claim that one service model is best.
* Do not use unsupported provider, pricing, regulatory, booking-window, or
  availability claims.
* Prefer the smallest number of high-value questions.
* Include a second or third question only for distinct, material value.
* Do not disguise advice as a question.
* Return zero suggestions when supplied context and knowledge do not support a
  useful additional question.

Evaluation should penalize unnecessary suggestions, lower-value additions, and
responses that appear complete only because they contain more questions.

## User Experience Contract

The interaction boundary is:

```text
Deterministic Recommendation
→ optional AI assistance offered
→ user explicitly requests or accepts assistance
→ AI-suggested question with grounding and uncertainty
→ user answers, dismisses, or asks why
→ answer remains untrusted
→ user confirms a structured interpretation
→ deterministic validation
→ trusted state may change
→ deterministic re-reasoning
```

Possible user actions are:

* Answer the suggested question.
* Add the question to the plan.
* Dismiss it as irrelevant.
* Ask why it matters.
* Correct a later AI interpretation.

This experiment ends at question suggestion. It does not define or implement
free-form answer interpretation. No answer enters trusted state without
explicit confirmation and deterministic validation.

## Deterministic Fallback

The frozen baseline is also the useful non-AI fallback.

It applies when:

* AI is unavailable.
* The monthly budget is exhausted.
* The user declines AI assistance.
* The model times out.
* The response fails schema validation.
* The response lacks grounding.
* Curated knowledge is unavailable or incompatible.
* Prompt or fixture versions do not match.

The deterministic Recommendation remains visible. The baseline supplies its
highest-priority applicable question or reports that no checklist question
remains. The user can continue without AI and is never blocked.

## Fixed Test Fixtures

All fields below are experiment fixtures, not existing production `Goal`
fields.

### Scenario A — Storage Likely

Trusted context:

* Temporary storage may be needed.
* The user does not want to drive a rental truck.
* Packing preference is unknown.

Expected themes:

* Clarify packing involvement or storage/service responsibility.
* Do not ask about driving willingness again.
* Questions should differ from the self-drive fixture.

### Scenario B — Cost-Sensitive and Willing to Self-Drive

Trusted context:

* Cost is a high priority.
* The user is willing to drive.
* Storage is not needed.

Expected themes:

* Clarify loading labor, packing involvement, or acceptable hands-on effort.
* Do not ask about storage or driving willingness.

### Scenario C — Convenience-Sensitive

Trusted context:

* The user wants minimal hands-on work.
* Specialty items may exist.
* Budget tolerance is unknown.

Expected themes:

* Clarify specialty handling or budget tolerance.
* Do not recommend full-service moving.

### Scenario D — Core Information Already Known

Trusted context:

* Storage need is known.
* Packing preference is known.
* Driving willingness is known.
* Cost preference is known.

Expected behavior:

* Identify another gap supported by the fixture, such as specialty handling, or
  return zero suggestions.
* Do not repeat known questions.

### Scenario E — No Applicable Knowledge

Trusted context:

* Missing information exists.
* Supplied curated items do not ground a useful question about it.

Expected behavior:

* Return zero suggestions.
* State that supplied knowledge does not support another useful question.

## Evaluation Gates

Passing one gate does not imply passage of the next.

### Gate 1 — Valid Output

The result:

* Passes schema validation.
* Uses only knowledge IDs supplied in the request.
* Contains no unsupported claims.
* Does not ask for known information.
* Does not attempt state mutation.
* Obeys suggestion-count and confirmation rules.

Invalid output is discarded and the deterministic fallback is used.

### Gate 2 — Useful Output

Human review confirms that the suggestion:

* Is relevant.
* Is context-sensitive.
* Could improve Decision readiness.
* Provides value beyond different wording.
* Is at least as useful as the frozen deterministic fallback.
* Uses the smallest justified number of questions.

A structurally valid result that fails this gate is not evidence of a useful AI
capability.

### Gate 3 — Promotion-Ready Capability

Across the fixed evaluation set, the capability:

* Performs reliably.
* Meets declared grounding thresholds.
* Remains within cost and latency budgets.
* Has a dependable deterministic fallback.
* Demonstrates consistent user value.
* Does not create unacceptable human-review or deterministic-filtering burden.

Only a capability that passes all three gates may be proposed for a later
product-integration slice.

## Automated Evaluation

Automated checks cover:

* Schema validity.
* Zero to three suggestions.
* Correct capability, request, and prompt versions.
* Valid affected Decision ID.
* Knowledge IDs exist in the request.
* `requires_user_confirmation` is always `true`.
* Known-information categories are not requested.
* Normalized questions are not duplicated.
* Additional questions clarify distinct information.
* No provider, pricing, regulation, availability, or booking-window claim.
* No state-mutation field or command.
* Empty results include `no_suggestion_reason`.
* Input and output remain within size limits.
* Cost and latency logs exist.

Automated validation establishes Gate 1. It cannot establish usefulness or
promotion readiness by itself.

## Human Evaluation

Human reviewers assess:

* Relevance
* Context sensitivity
* Question clarity
* Potential effect on Decision readiness
* Grounding quality
* Honest uncertainty
* Value beyond alternate wording
* Comparison with the deterministic fallback
* Meaningful differences across fixtures
* Whether the suggestion implies a preferred service model
* Whether every additional question adds material value

The implementation design must define a small scoring rubric and pass threshold
before evaluation begins. Human review establishes Gate 2 and contributes to
Gate 3.

## Baseline Comparison

Every fixture runs through:

1. The frozen deterministic baseline.
2. The AI capability.

Compare:

* Relevance
* Repetition
* Context sensitivity
* Usefulness of rationale
* Number of questions
* Cost
* Latency

The experiment succeeds only when AI provides material, repeatable benefit over
the frozen fallback. Better phrasing alone is not sufficient.

## Cost and Operational Budget

Initial experiment limits:

```text
maximum input: 4,000 tokens
maximum output: 700 tokens
maximum suggestions: 3
expected default suggestions: 1
target cost per call: $0.01 or less
hard cost ceiling per call: $0.03
monthly experiment ceiling: $10
target latency: 5 seconds or less
hard timeout: 15 seconds
automatic model retries: 0
background calls: prohibited
routine-render calls: prohibited
```

These are experiment limits, not production pricing commitments.

The least expensive model that reliably meets the contract should be preferred,
but provider and model selection remain explicitly deferred.

Logging should record:

```text
capability
prompt_version
fixture_version
baseline_version
input_tokens
output_tokens
estimated_cost
latency
validation_result
cache_status
fallback_reason
```

## Cache Contract

User-facing experiment operation may reuse a previously validated result for
identical context.

The cache key includes:

```text
capability
prompt_version
normalized_trusted_state_hash
missing_information_hash
curated_fixture_version
baseline_version
```

Rules:

* Never cache or reuse invalid or ungrounded output.
* Invalidate when trusted state, missing information, prompt, fixture, or
  baseline version changes.
* Allow explicitly uncached runs during controlled evaluation.
* Record cache status in capability logs.
* Never treat a cached suggestion as trusted state.

## Failure Modes

| Failure | Detection | Safe behavior |
| --- | --- | --- |
| Invalid JSON or schema | Schema validator | Discard response; use fallback |
| Unknown knowledge ID | Grounding validator | Discard response; use fallback |
| Unsupported factual claim | Grounding validator or review | Reject response; use fallback |
| Question about known information | Deterministic validator | Reject suggestion; use next valid suggestion or fallback |
| Duplicate questions | Normalized comparison | Reject duplicates; use one valid suggestion or fallback |
| Irrelevant question | Human rubric | Record Gate 2 failure; do not promote |
| Overly broad or compound question | Automated rule or human review | Reject suggestion; use fallback |
| Unnecessary additional question | Human comparison | Penalize usefulness score |
| Timeout | Hard request deadline | Cancel request; use fallback |
| Budget exhausted | Deterministic pre-call check | Do not call AI; use fallback |
| Curated knowledge unavailable | Eligibility check | Do not call AI; use fallback |
| Prompt or fixture mismatch | Version validation | Reject request or response; use fallback |
| Baseline mismatch | Version validation | Do not evaluate until versions align |

No failure changes trusted state or blocks the user.

## Explicitly Deferred Work

This experiment defers:

* Free-form answer interpretation
* Production moving-service Decision and state modeling
* Automated question-to-field mapping
* Live research
* Provider search or ranking
* Quote collection
* Booking
* Current provider availability
* Current pricing
* Current regulations
* Booking-window logic
* General moving-service comparison
* Automatic writes to trusted state
* General-purpose chat
* Cross-domain orchestration
* Vector databases
* Background agents
* Production persistence for AI suggestions
* Model-provider selection
* Model selection

## Experiment Completion Criteria

The design is ready for a later implementation slice when:

* Input and output schemas are unambiguous.
* Curated knowledge fixtures are defined.
* The deterministic baseline checklist, filters, priority, and version are
  frozen.
* Test fixtures and expected qualities are documented.
* Automated Gate 1 checks are specified.
* The Gate 2 human rubric and pass threshold are declared.
* Gate 3 promotion thresholds are declared.
* Fallback behavior is complete.
* Cost and latency limits are declared.
* Cache identity and invalidation are defined.
* User-confirmation boundaries are explicit.
* No unresolved question would force an implementer to invent product
  behavior.

Implementation completion is not the same as experiment success. The
capability should be promoted only if it passes all three evaluation gates.

## Open Decisions for a Later Implementation Slice

The design intentionally leaves these decisions for a bounded implementation
proposal:

* The exact JSON Schema representation.
* The content and source review of the six curated fixture items.
* The baseline checklist text and fixed priority ordering.
* The Gate 2 scoring scale and pass threshold.
* The Gate 3 reliability and grounding thresholds.
* The exact test-run count.
* The provider and model.
* How a later interface presents one suggestion when multiple valid
  suggestions are returned.

These decisions must be resolved before the first AI evaluation run, not
invented during evaluation.
