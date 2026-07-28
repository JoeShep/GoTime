# Experiment — Suggest Moving-Service Questions

## Experiment Status and Scope

```text
capability: suggest_moving_service_questions
primary AI capability: State Discovery Assistance
phase: design
status: approved for fake-adapter contract work
```

This experiment tests whether bounded AI assistance can use trusted relocation
state, explicitly missing information, and a small curated moving-service
knowledge set to suggest useful questions that help the user determine which
moving-service models deserve investigation.

The experiment primarily validates **State Discovery Assistance**. Curated
knowledge grounds the suggested questions, but this experiment does not
validate the broader Grounded Domain Guidance capability of producing a
service-model comparison.

The capability may suggest a question. It does not decide what the user should
choose, and its output does not become trusted state.

The experiment does not:

* Select a moving company.
* Select or recommend a moving-service model.
* Compare, rank, or score moving-service models.
* Perform live web research.
* Calculate dates or apply booking windows.
* Modify trusted state or confirm an Assumption.
* Generate an unbounded move plan.
* Replace deterministic Recommendation eligibility or sequencing.
* Interpret free-form answers.
* Run autonomously or in the background.

The experiment may conclude that AI should not be used for this capability.
Schema-valid output or more polished wording is not sufficient evidence of
product value.

## 1. Hypothesis

> Given bounded trusted relocation state, explicitly identified missing
> information, an unresolved moving-service Decision, and a small curated
> moving-service knowledge set, AI can suggest zero to three relevant,
> nonduplicative questions that improve the user's readiness to investigate
> moving-service models without inventing facts, repeating known information,
> or selecting an option.

One high-value question is the expected default. A response may contain a
second or third question only when each question targets a different approved
missing-information category and provides distinct, material value.

Zero suggestions is a valid result. The model must not manufacture a gap or a
question to fill a quota.

Success would show that AI can prioritize context-sensitive discovery
questions and provide a grounded explanation of why each question matters. It
would not show that AI can:

* Choose a service model or provider.
* Interpret an answer safely.
* Produce a complete service-model comparison.
* Improve the final relocation outcome.
* Replace deterministic validation, state transitions, or sequencing.

## 2. User Value

Moving-service research requires users to understand distinctions they may
never have encountered before. A user may not know that temporary storage,
packing responsibility, willingness to drive, specialty-item handling, or the
balance between cost and hands-on work can affect which service models are
practical to investigate.

This capability should help the user understand what matters next without
requiring prior moving-industry knowledge. It should make it easier to:

* Notice a relevant unresolved circumstance.
* Focus on the most useful question rather than a long checklist.
* Understand why the answer could affect moving-service research.
* Avoid spending time investigating clearly incompatible approaches.
* Continue making progress while retaining control of every Decision.

The core GoTime experience remains:

> What should I do next?

The deterministic Recommendation remains the primary product output. An
AI-suggested question is optional supporting assistance that may help the user
supply information needed to act on that Recommendation.

## 3. Entry Conditions

The deterministic engine owns capability eligibility. AI cannot decide when it
should run.

The capability may be offered only when:

* The move is classified as interstate.
* Origin and destination regions are present.
* A target move window exists or is explicitly unknown.
* A moving-service-model Decision exists and remains unresolved.
* Deterministic sequencing has reached the moving-service research stage.
* Deterministic state inspection has identified at least one relevant
  information gap or unresolved conflict.
* Every eligible gap includes an approved category identifier, allowlisted
  state-field mapping, and supported answer type.
* Compatible, reviewed, versioned moving-service knowledge is available.
* The prompt, schema, and knowledge-fixture versions are supported.
* The user explicitly requests or approves AI assistance.
* The experimental AI budget remains available.

The capability must not run:

* When a screen renders.
* On every keystroke or routine state change.
* Merely because the deterministic Recommendation is displayed.
* Automatically after an earlier response.
* In the background.
* When any deterministic eligibility condition fails.

The deterministic eligibility result should be structured:

```text
eligible
ineligible_reason
decision_id
research_stage
eligible_missing_information
knowledge_fixture_version
prompt_version
schema_version
budget_available
```

If the request is ineligible, GoTime does not call the adapter. It preserves
the deterministic Recommendation and uses the deterministic fallback when an
applicable fallback question exists.

## 4. Trusted Input Contract

The request contains a narrow experiment context. These fields define the
capability contract; they do not imply that all fields already exist on the
production `Goal` model.

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
specialty_item_needs
known_constraints
explicit_missing_information
open_moving_service_decision
current_deterministic_recommendation
prompt_version
maximum_output_size
```

Optional state must distinguish among:

```text
known
explicitly_unknown
not_applicable
not_supplied
```

Absence must not be interpreted as a known negative value. A value omitted
from the capability request must not be treated as missing information unless
the deterministic system explicitly includes it in
`explicit_missing_information`.

Each eligible missing-information entry must contain:

```text
category_id
state_field
answer_type
allowed_enum_values
reason_missing
```

Contract rules:

* `category_id` is a deterministic, allowlisted category identifier.
* `state_field` is the deterministic mapping to the trusted-state vocabulary.
* `answer_type` is `boolean` or `enum`.
* `allowed_enum_values` is required for an enum and absent for a boolean.
* The AI may select a supplied category to ask about.
* The AI may not create a category, state-field mapping, answer type, or enum
  value.

The target move window may be supplied as context, but this capability neither
calculates dates nor applies planning-window guidance.

The request explicitly excludes:

* Full Goal history.
* Unrelated personal information.
* Raw conversation history.
* Application logs.
* Live provider information.
* Current prices, quotes, or availability.
* Unconfirmed AI interpretations.
* Unbounded free-form project context.
* Data included merely because it is easy to retrieve.

## 5. Curated Knowledge Contract

The experiment uses a small, reviewed, versioned knowledge fixture rather than
a general knowledge base.

The minimum fixture represents:

1. Full-service interstate carrier.
2. Moving broker.
3. Portable storage container.
4. Freight or trailer-based service.
5. Rental truck.
6. Labor-only moving help.

Each knowledge item contains:

```text
knowledge_id
service_model
statement
tradeoff_category
applicable_conditions
source
reviewed_at
freshness_guidance
version
```

For this question-suggestion experiment, the fixture needs only enough reviewed
knowledge to establish why the following information may affect which service
models deserve investigation:

* Temporary storage need.
* Packing responsibility.
* Loading and unloading responsibility.
* Willingness to drive a rental truck.
* Cost-versus-convenience preference.
* Specialty-item handling.

Each statement must be bounded, attributable, and applicable only under its
documented conditions. A statement must not imply that one service model is
best for the user.

The following richer content can wait for the later service-model comparison
experiment:

* Comprehensive advantages and disadvantages.
* Model rankings or recommendations.
* Detailed regulatory guidance.
* Booking-window guidance.
* Current pricing.
* Provider availability or service areas.
* Location-specific suitability.
* Full comparisons across service models.

The draft knowledge fixture is not eligible for a real-model experiment until:

* Every included statement has a reviewed source.
* Review dates and freshness guidance are populated.
* The complete fixture is assigned a version.
* The request references that exact version.

## 6. AI Request Contract

The request envelope is capability-specific and bounded:

```text
capability
trusted_state
missing_information
deterministic_context
curated_knowledge_items
requested_output
prompt_version
schema_version
knowledge_fixture_version
maximum_questions
maximum_output_tokens
```

Required fixed value:

```text
capability: suggest_moving_service_questions
```

`missing_information` contains only deterministic entries from the trusted
input contract:

```text
category_id
state_field
answer_type
allowed_enum_values
reason_missing
```

`deterministic_context` contains only:

```text
open_decision
current_recommendation
research_stage
applicable_known_constraints
```

`requested_output` directs the adapter to:

* Return zero to three structured question suggestions.
* Prefer one high-value question.
* Use only supplied missing-information categories.
* Use only supplied curated knowledge.
* Return zero suggestions when no useful grounded question is supported.
* Avoid selecting a service model or provider.
* Avoid proposing or commanding a trusted-state mutation.

The request does not contain unbounded Goal history, conversation history, or
project context.

## 7. AI Response Contract

The response is structured:

```text
capability
prompt_version
schema_version
suggestions
fallback_recommended
warnings
```

Each suggestion contains:

```text
question_id
question
why_it_matters
information_it_would_clarify
affected_decision_id
selected_missing_information_category
relevant_knowledge_ids
grounding_summary
reason_not_deterministic
uncertainties
suggested_answer_type
requires_user_confirmation
```

Contract rules:

* `suggestions` contains zero to three entries.
* One suggestion is the expected default.
* Each suggestion selects exactly one supplied missing-information category.
* Multiple suggestions may not select the same category.
* `question_id` values are unique within the response.
* `suggested_answer_type` must equal the answer type supplied for the selected
  category.
* The response does not contain `proposed_state_field`.
* The response cannot create a state field, category, answer type, or enum
  value.
* `requires_user_confirmation` is always `true`.
* `fallback_recommended` may be `true` when no useful grounded question is
  available or deterministic behavior is preferable.
* `warnings` contains only bounded warning codes defined by the schema.
* The response contains no command, patch, or proposed automatic state change.

`grounding_summary` identifies the supplied trusted context and knowledge IDs
that support the question. It must not introduce an unsupported source or
claim.

`reason_not_deterministic` identifies the contextual interaction or ambiguity
that justified AI prioritization. A generic statement such as "AI is helpful"
is invalid.

`information_it_would_clarify` describes the purpose of an answer. It is not
the answer and cannot satisfy missing information.

A zero-suggestion response is valid. It must not invent a question to fill a
quota.

## 8. Question-Quality Rules

Every suggestion must:

* Be answerable by the user.
* Ask only about a supplied missing or conflicting information category.
* Avoid duplicating a known fact.
* Be relevant to the open moving-service Decision.
* Be grounded in at least one supplied curated knowledge item.
* Explain why the answer matters to moving-service research.
* Use natural, nontechnical language.
* Avoid assuming the answer.
* Ask one concept at a time.
* Avoid combining unrelated questions.
* Avoid unnecessary sensitive information.
* Remain safe and useful if the user declines to answer.
* Avoid presenting advice as a question.
* Avoid implying that a service model or provider is preferred.
* Avoid unsupported pricing, availability, regulatory, provider, or
  booking-window claims.

A second or third suggestion must:

* Select a different missing-information category.
* Add distinct, material value.
* Not be a rephrasing of another suggestion.

The model should return fewer suggestions rather than include a weak,
duplicative, or manufactured question.

## 9. Deterministic Validation

Normal code validates the complete response before any suggestion is shown.

Validation includes:

* The response matches the supported schema.
* Capability, prompt, and schema versions match the request.
* The response contains zero to three suggestions.
* Every `question_id` is present and unique.
* Every selected missing-information category was supplied in the request.
* No two suggestions target the same missing-information category.
* Every affected Decision ID exists and remains open.
* Every referenced knowledge ID was supplied in the request.
* Every suggested answer type matches the selected category.
* Every enum category retains the deterministic set of allowed values.
* `requires_user_confirmation` is always `true`.
* No suggestion targets a field already known or not applicable.
* Question and response lengths remain within limits.
* No state-field proposal or mutation command is present.
* No prohibited provider, model-selection, date, research, or planning claim
  is present.
* `fallback_recommended` and warning codes are schema-valid.

Duplicate detection remains intentionally simple in v1:

1. Reject multiple suggestions targeting the same missing-information
   category.
2. Normalize question text for case, surrounding whitespace, repeated
   whitespace, and punctuation.
3. Reject exact normalized duplicates.
4. Apply a small, deterministic token-overlap or string-similarity threshold
   for near-exact duplication.

The experiment does not introduce embeddings, vector search, or vector
infrastructure.

Any validation failure rejects the complete response. GoTime must not partially
accept, retain, or display individual suggestions from an invalid response.
The deterministic fallback is used instead.

## 10. User Experience Contract

The initial UI presents at most one valid AI-suggested question at a time, even
though the response contract permits zero to three suggestions.

Example:

> **Something else worth clarifying — AI suggestion**
>
> Will you need temporary storage between homes?
>
> This matters because storage needs can change which moving-service models
> are practical to investigate.

Available actions:

* **Answer this**
* **Not relevant**
* **Why are you asking?**

The UI must:

* Label the question as an AI suggestion.
* Show why it matters.
* Preserve the deterministic Recommendation as the primary product output.
* Never present an inferred fact or answer as true.
* Let the user reject or dismiss the suggestion.
* Avoid implying that the user must answer to continue.
* Require explicit confirmation before saving any answer.
* Present only supported boolean or enum answer controls.
* Avoid free-form answer input in the initial experiment.

If a valid response contains multiple suggestions, deterministic presentation
logic selects one to show. Other suggestions may be retained only for
controlled evaluation or later presentation; they do not become trusted state
and are not shown simultaneously in the initial UI.

## 11. Trusted-State Transition

The only permitted state transition is:

```text
AI suggests a question
→ user chooses to answer
→ UI presents a deterministic boolean or enum control
→ user supplies an answer
→ deterministic validation
→ user confirms the answer and its meaning
→ trusted state updates
→ deterministic engine re-reasons
```

The deterministic system already knows the selected category's state-field
mapping and supported answer values. AI does not interpret the answer and does
not propose the destination state field.

The AI suggestion itself must never:

* Satisfy required information.
* Change Decision readiness.
* Confirm or invalidate an Assumption.
* Create a Preference or Constraint.
* Replace the current Recommendation.
* Trigger a trusted reasoning path.

Free-form answer interpretation is a separate, deferred capability.

## 12. Deterministic Fallback

The deterministic fallback is both the useful no-AI path and the comparison
baseline for the experiment.

The initial curated question list may include:

* Will temporary storage be needed between homes?
* Are you willing to drive a rental truck?
* Would you rather minimize cost or minimize hands-on work?
* Do you want the moving service to pack your belongings?
* Are there specialty items that require special handling?

Fallback selection:

1. Remove questions for fields that are already known.
2. Remove questions made inapplicable by trusted state.
3. Retain only questions whose category, state-field mapping, and answer type
   are approved.
4. Apply a frozen priority ordering.
5. Return the highest-priority applicable question or a structured no-question
   result.

The fallback remains available when:

* AI is unavailable.
* The response is invalid.
* The monthly budget is exhausted.
* The user declines AI assistance.
* The request times out.
* Curated knowledge is unavailable or incompatible.
* Prompt, schema, or fixture versions do not match.

The fallback baseline must be frozen, versioned, and tested before any
real-model evaluation. It must not be revised in response to individual model
outputs. A baseline change requires a new version and a new evaluation run.

The deterministic Recommendation remains visible, and the user is never
blocked by AI failure or refusal.

## 13. Test Fixtures

All fixture fields are experiment context, not claims about the current
production `Goal` model.

### Scenario A — Storage Unknown

Known:

* The move is interstate.
* The user does not want to drive a rental truck.
* Temporary storage need is unknown.

Expected:

* A storage-related question is strongly relevant.
* The system does not ask whether the user will self-drive.
* The question uses the approved storage category and boolean or enum mapping.
* No service model is selected or recommended.

### Scenario B — Cost Sensitivity Unknown

Known:

* Storage is not needed.
* Packing help is desired.
* Cost-versus-convenience preference is unknown.

Expected:

* A cost-versus-convenience tradeoff question is relevant.
* The system does not repeat the packing preference.
* The question uses the approved cost-versus-convenience enum.
* No service model is selected or recommended.

### Scenario C — Most Inputs Already Known

Known:

* Storage need.
* Packing preference.
* Driving willingness.
* Cost preference.
* Specialty-item needs.

Expected:

* The response contains fewer questions or zero suggestions.
* `fallback_recommended` may be `true`.
* The model does not manufacture a gap merely to fill the quota.
* No known information is requested again.

### Scenario D — Conflicting or Ambiguous State

Known:

* Convenience is recorded as most important.
* A strict moving budget is also recorded.
* The deterministic system marks the related tradeoff category as conflicting
  and eligible for clarification.

Expected:

* The AI may suggest clarifying the approved cost-versus-convenience category.
* The question identifies the tradeoff without assuming which value should
  win.
* The AI does not resolve the conflict.
* Any answer remains subject to deterministic validation and user
  confirmation.

### Optional Scenario E — No Applicable Knowledge

Known:

* A missing-information category exists.
* The supplied curated knowledge does not ground a useful question about it.

Expected:

* The response contains zero suggestions.
* `fallback_recommended` is `true`.
* The model does not use outside knowledge to manufacture a question.

## 14. Evaluation Rubric

Evaluation has separate validity, usefulness, and promotion gates.

### Automated Validity

Automated evaluation measures:

* Schema validity.
* Capability and version validity.
* Suggestion-count validity.
* Knowledge-reference validity.
* Decision-reference validity.
* Category and answer-type validity.
* Confirmation-boundary validity.
* Known-state respect.
* Duplicate detection.
* Output-size compliance.
* Absence of mutation commands and prohibited claims.

Any failed automated validity check rejects the complete response and invokes
the deterministic fallback.

### Human Usefulness Review

Human reviewers score each valid response from 1 to 5 for:

* Relevance.
* Grounding.
* Nonduplication.
* Usefulness.
* Clarity.
* Respect for known state.
* Respect for missing-state boundaries.
* Appropriate number of questions.
* Value beyond the deterministic baseline.

Reviewers also record:

* Whether a suggestion implies a preferred service model.
* Whether its rationale is supported by supplied knowledge.
* Whether every additional suggestion adds material value.
* Whether the user accepts, rejects, or ignores the displayed suggestion.

### Measured Operational Criteria

The experiment measures:

* Schema-valid response rate.
* Hallucination rate.
* Unsupported-reference rate.
* User acceptance, rejection, and ignore rate.
* Cost per invocation.
* Latency.
* Fallback invocation rate.
* Fallback quality.

### Failure

The experiment fails if it produces:

* Any automatic trusted-state mutation.
* Any provider or service-model selection.
* Repeated requests for known information.
* Unsupported references or claims.
* A manufactured gap in Scenario C.
* An AI-resolved conflict in Scenario D.
* Unreliable structured output.
* Cost or latency above the declared ceilings.
* A deterministic fallback that is not independently useful.
* No material, repeatable value beyond the frozen deterministic baseline.
* A safety burden that requires extensive post-processing or human repair.

Passing automated validation alone is not experiment success.

## 15. Cost and Latency Budget

Initial provisional experiment limits:

```text
maximum input tokens: 3,000
maximum output tokens: 500
maximum suggestions: 3
expected default suggestions: 1
model calls: 1 per explicit user action
automatic retries: 0
target estimated cost per call: $0.01 or less
hard estimated cost ceiling per call: $0.03
monthly experiment ceiling: $10
target latency: 5 seconds or less
hard timeout: 12 seconds
live research: prohibited
background calls: prohibited
routine-render calls: prohibited
```

These are experiment budgets, not vendor or production pricing commitments.
No final model or provider is selected by this document. A later evaluation
should use the least expensive model that reliably satisfies the contract.

The deterministic system checks the monthly ceiling before making a request.
No automatic retry occurs in v1. A timeout, invalid response, or transient
failure resolves to the deterministic fallback rather than another model call.

### Cache Policy

A user-facing experiment may reuse a previously validated response only for
identical normalized context.

The cache key includes:

```text
capability
prompt_version
schema_version
normalized_trusted_state_hash
missing_information_hash
knowledge_fixture_version
fallback_baseline_version
```

Rules:

* Never cache or reuse invalid or ungrounded output.
* Invalidate when trusted state, missing information, prompt, schema,
  knowledge fixture, or baseline version changes.
* Permit explicitly uncached runs during controlled evaluation.
* Record cache status in observability data.
* Never treat a cached suggestion as trusted state.

## 16. Observability

Log the minimum metadata needed to evaluate reliability, cost, latency, and
user response:

```text
capability
prompt_version
schema_version
scenario_or_fixture_id
model_identifier
knowledge_fixture_version
fallback_baseline_version
referenced_knowledge_ids
input_tokens
output_tokens
estimated_cost
duration
schema_valid
fallback_used
fallback_reason
suggestion_count
displayed_question_id
selected_missing_information_category
user_disposition
cache_status
```

`user_disposition` supports:

```text
accepted
rejected
ignored
not_shown
```

Do not log by default:

* Full prompts.
* Raw conversation history.
* Unnecessary trusted-state values.
* Sensitive user answers.
* Entire model responses when bounded evaluation metadata is sufficient.

Logs do not become trusted Goal state. Retention and access policies must be
defined before collecting real-user experimental data.

## 17. Success Criteria

The experiment succeeds only if:

* Suggestions respond materially to supplied state.
* Questions do not repeat known information.
* Questions target only approved missing or conflicting categories.
* Rationales are grounded in supplied curated knowledge.
* Structured output validates reliably.
* No output automatically mutates trusted state.
* The confirmation boundary remains intact.
* The deterministic fallback remains useful.
* Cost and latency remain within the declared budget.
* Intended users find at least some suggestions meaningfully helpful.
* AI demonstrates material, repeatable value beyond different wording of the
  deterministic fallback.

Success at this experiment validates only the bounded question-suggestion
capability. It does not authorize service-model comparison, live research,
answer interpretation, autonomous operation, or any other deferred capability.

## 18. Explicitly Deferred Work

This experiment defers:

* Live moving-company research.
* Provider recommendations.
* Provider rankings.
* Quotes and availability.
* Booking-window implementation.
* Automatic service-model selection.
* Full moving-service-model comparison.
* Free-form answer interpretation.
* General-purpose chat.
* Autonomous background AI.
* Vector database or embedding infrastructure.
* Cross-domain suggestion orchestration.
* Automatic writes to trusted state.
* Provider or model selection.
* Production persistence for AI suggestions.
* General moving-plan generation.

## 19. Staged Implementation Recommendation

The experiment should be implemented in two separately reviewed steps.

### Step 1 — Fake or Deterministic Adapter

The first adapter returns fixed fixture responses and validates:

* Request construction.
* Schema validation.
* Complete-response rejection behavior.
* Deterministic fallback behavior.
* UI presentation.
* User-confirmation boundaries.
* Observability.

This step proves that GoTime can enforce the contract independently of a model.
It does not prove that AI adds product value, produces useful questions, or
outperforms the deterministic baseline.

Before Step 1 is complete:

* The deterministic fallback baseline must be frozen and versioned.
* Baseline applicability and priority rules must have focused tests.
* Valid, invalid, empty, duplicate, unsupported-reference, and over-limit fake
  responses must be covered.
* The UI must show no more than one suggestion at a time.
* Boolean and enum confirmation flows must preserve the trusted-state boundary.
* Observability must record both suggestion and fallback outcomes.

### Step 2 — Real-Model Adapter

A real-model experiment may begin only after:

* Curated knowledge statements have reviewed sources.
* The knowledge fixture is complete and versioned.
* Fake-adapter contract tests pass.
* The deterministic fallback baseline is frozen, versioned, and tested.
* Cost, latency, and evaluation collection are ready.

The real-model adapter must use the same request and response contracts as the
fake adapter. Introducing a model does not relax deterministic validation,
fallback behavior, confirmation boundaries, or observability requirements.

Every fixed scenario must run through both:

1. The frozen deterministic fallback baseline.
2. The real-model capability.

The experiment should advance only if the model provides material, repeatable
benefit beyond the baseline. Better phrasing alone is not sufficient.

## 20. Open Decisions Before Implementation

The following decisions remain for a bounded implementation proposal:

* The exact allowlisted state fields in the first request.
* The exact missing-information category identifiers.
* The boolean and enum values supported by each category.
* The minimum curated statements and reviewed sources.
* The exact JSON Schema representation.
* The prompt, schema, fixture, and baseline version identifiers.
* The deterministic fallback question wording and fixed priority order.
* The deterministic rule for selecting one returned suggestion for display.
* The normalized-text near-duplicate threshold.
* The human evaluation scoring threshold.
* The promotion-ready schema-validity and grounding thresholds.
* The required number of repeated real-model fixture runs.
* The model characteristics required for reliable structured output.
* The exact mechanism for recording accepted, rejected, ignored, and
  not-shown suggestions.
* Whether user-facing caching is enabled during initial testing.
* The retention and access policy for experiment observability data.
* The deterministic event or state that means the user has reached the
  moving-service research stage.

These decisions must be resolved before the relevant implementation or
evaluation step. They must not be invented during a real-model evaluation run.
