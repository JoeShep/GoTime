# AI-Assisted Reasoning

GoTime may use AI to help understand a user's circumstances and apply relevant
knowledge, but AI does not replace the deterministic reasoning engine.

The governing principle is:

> AI may propose interpretations, questions, and grounded guidance.
> Deterministic GoTime owns trusted state, validation, calculations,
> sequencing, and Recommendation eligibility. The user decides what new
> information becomes trusted state.

This document defines that boundary through the example of deciding when to
research moving companies and which moving-service models are worth
investigating.

## Two Distinct AI Capabilities

GoTime should not treat all AI-assisted work as one general capability. The
first useful roles fall into two categories with different inputs, risks,
evaluation criteria, and rollout paths.

### AI Capability A — State Discovery Assistance

AI may:

* Suggest a missing question.
* Interpret a bounded free-form answer.
* Identify ambiguity or a possible contradiction.
* Propose structured information for user confirmation.

This capability receives a narrow view of trusted state, known missing
information, and relevant curated question guidance. Its main risks are
misinterpreting the user, asking irrelevant or repetitive questions, and
presenting an inference as something the user said.

Evaluation should emphasize relevance, fidelity to the user's words, avoidance
of already-answered questions, and correct separation between a suggestion and
trusted state. Rollout can begin without live research because suggestions can
be grounded in curated knowledge and confirmed by the user.

### AI Capability B — Grounded Domain Guidance

AI may:

* Apply curated domain knowledge to trusted user state.
* Compare relevant domain options.
* Summarize current external evidence.
* Explain tradeoffs, sources, freshness, and uncertainty.

This capability receives trusted state plus selected curated knowledge or
current external evidence. Its main risks are unsupported claims, stale
guidance, omitted tradeoffs, false precision, and treating an option comparison
as a decision.

Evaluation should emphasize grounding, source coverage, freshness, balanced
tradeoffs, uncertainty disclosure, and reproducibility from the supplied
evidence. Rollout should begin with curated knowledge before introducing live
research.

Neither capability may write directly to trusted state, confirm an Assumption,
or make a consequential choice for the user.

## Running Example — Moving-Company Planning

Assume a family has a target move date and known origin and destination
regions, but has not selected a moving-service model.

Possible service models include:

* Full-service moving company
* Portable moving container
* Freight or shared-load service
* Rental truck

Useful planning context may include:

* Household size
* Willingness and ability to drive a truck
* Need for temporary storage
* Specialty-item handling
* Cost-versus-convenience preference
* Flexibility of the move window

GoTime must distinguish stable reasoning, maintained domain guidance,
time-sensitive external evidence, AI-generated suggestions, and information
the user has confirmed.

## Reasoning and Knowledge Flow

### 1. Guided User-State Discovery

GoTime first identifies which information is missing through deterministic
state inspection. It may present a curated question directly or ask State
Discovery Assistance to select or phrase the most useful next question.

Example questions include:

* Is minimizing hands-on work more important than minimizing cost?
* Can someone in the household drive a rental truck cross-country?
* Will storage between homes be necessary?
* Are there items requiring specialty handling?
* How firm is the move date?

The system must distinguish:

* A direct structured user answer
* A free-form answer awaiting interpretation
* An AI-proposed interpretation awaiting confirmation
* Information that remains unknown

AI does not decide that a requirement exists merely because it seems likely
from context.

### 2. Deterministic Reasoning

The deterministic core owns:

* Trusted state representation
* Input and contradiction validation
* Date arithmetic
* Dependencies and sequencing
* Decision readiness
* Known domain rules
* Recommendation eligibility
* Assumption status
* User-confirmation transitions
* Safe fallback Recommendations

For the moving example, deterministic code can determine that moving-service
research is required when the move is planned but the service model remains
unresolved. It can determine which required information is missing and whether
a Recommendation is eligible.

#### Timing Responsibility

Recommendations about when to begin mover research cross a strict boundary:

* Curated or live knowledge may supply applicable planning-window guidance.
* Deterministic code must apply approved guidance to the user-provided target
  move date, calculate dates, and compare those dates with the current date.
* AI may explain the calculated result, apply relevant context, and surface
  tradeoffs.
* AI must not own date arithmetic or silently invent a timing rule.

For example, an approved knowledge item might state that a particular kind of
move commonly warrants beginning research within a defined range before the
target date. Deterministic code calculates the corresponding calendar window.
AI may then explain why the earlier or later end of that window may be more
appropriate given confirmed circumstances.

### 3. Curated Domain Knowledge

Curated knowledge is maintained, versioned, attributable guidance for
information that is sufficiently stable to reuse.

Moving-service knowledge may include:

* Common service models
* Typical advantages and disadvantages
* Common planning dependencies
* Questions to ask providers
* Qualified research and booking windows
* Conditions that make storage or specialty services relevant

A curated item should carry:

```text
knowledge_id
topic
statement
source
source_type
reviewed_at
freshness_guidance
applicable_conditions
version
```

Curated knowledge can ground deterministic rules and AI guidance. It does not
become user state and should not be presented as universally applicable when
its conditions are not satisfied.

### 4. Live External Research

Live research is appropriate only when freshness materially affects the
answer, such as:

* Current provider service areas
* Current provider availability
* Current prices
* Current regulations
* Recent market conditions

General differences between full-service movers and portable containers belong
in curated knowledge. Whether a named company currently serves both locations
or has availability for a target week requires current evidence.

External evidence should carry:

```text
evidence_id
source_url
publisher
retrieved_at
claim
applicable_location
fresh_until
limitations
```

Live research should normally follow an explicit user action. Results should be
cached or reused while sufficiently current and should never silently become a
verified user fact.

### 5. AI-Assisted Interpretation and Synthesis

State Discovery Assistance may interpret a bounded free-form answer or suggest
the next missing question. Grounded Domain Guidance may compare service models
or summarize supplied current evidence.

AI may:

* Explain why a question matters.
* Relate confirmed circumstances to curated tradeoffs.
* Identify ambiguity for user review.
* Produce a grounded comparison of relevant options.
* Summarize cited, current external evidence.

AI may not:

* Select a moving company or service model automatically.
* Set the user's budget, dates, constraints, or preferences.
* Confirm an Assumption.
* Claim provider availability or pricing without current evidence.
* Calculate planning dates.
* Invent a timing rule.
* Write directly to trusted state.
* Initiate autonomous background research in the MVP.

### 6. User Confirmation Before Trusted State

The state transition is:

```text
AI suggestion
→ visible grounding and uncertainty
→ user review
→ explicit user confirmation
→ deterministic validation
→ trusted state update
→ deterministic re-reasoning
```

For example:

> Based on your need for temporary storage and preference not to drive a truck,
> portable-container and full-service options may be worth comparing. Should
> GoTime record that temporary storage is required?

Until the user confirms it, `temporary_storage_required` remains proposed
information. It cannot satisfy required information, change Decision
readiness, or trigger a trusted reasoning path.

## Responsibility Matrix

| Responsibility | Owner | Supporting role |
| --- | --- | --- |
| Validate trusted state and contradictions | Deterministic core | User supplies or confirms information |
| Identify known missing information | Deterministic core | AI may suggest which question to ask |
| Define stable moving guidance | Curated knowledge | Experts review and version it |
| Supply current provider facts | Live research | AI may summarize cited evidence |
| Calculate planning dates | Deterministic core | Curated or live knowledge supplies an approved rule |
| Compare relevant service models | User decides | AI may provide a grounded comparison |
| Propose an interpretation of free text | AI Capability A | User confirms or rejects it |
| Explain grounded tradeoffs | AI Capability B | Deterministic state and cited knowledge constrain it |
| Add information to trusted state | User confirmation plus deterministic validation | AI may only propose |

## Structured Context Supplied to AI

Every request should name one capability and provide only the context needed
for that capability.

```text
capability
goal_summary
relevant_trusted_state
open_decision
missing_information
constraints
preferences
unconfirmed_assumptions
deterministic_recommendation
curated_knowledge_items
external_evidence_items
requested_output
prompt_version
maximum_output_size
```

The context should exclude unrelated Goal history, raw logs, unbounded
conversation history, and unnecessary personal information.

State Discovery Assistance usually needs missing information and a bounded
user answer. Grounded Domain Guidance usually needs selected trusted state plus
curated knowledge or external evidence. Their context packages should not be
interchangeable by default.

## Structured AI Response

AI output should validate against a capability-specific schema rather than
returning an unbounded conversational answer.

```text
capability
summary
grounding_summary
reason_not_deterministic
suggested_questions[]
suggested_interpretations[]
relevant_knowledge_ids[]
relevant_evidence_ids[]
uncertainties[]
conflicts[]
proposed_state_updates[]
fallback_message
```

`grounding_summary` explains which supplied state, knowledge, and evidence
support the output. `reason_not_deterministic` explains why AI was needed
instead of a deterministic rule or curated static response.

For testability, `grounding_summary` must reference the applicable supplied
state and `knowledge_id` or `evidence_id` values; it must not introduce an
unsupported source. `reason_not_deterministic` must name the ambiguity,
interpretation, comparison, or synthesis that requires AI. A generic statement
such as "AI is helpful" is not valid.

Each proposed state update should include:

```text
field
proposed_value
basis
confidence_or_uncertainty
requires_user_confirmation: true
```

The response must not contain an instruction that directly mutates trusted
state.

## Sources, Freshness, Uncertainty, and Cost

### Sources

Every knowledge-dependent claim should reference a supplied `knowledge_id` or
`evidence_id`. Unsupported claims should invalidate the response or be clearly
excluded from user-facing guidance.

### Freshness

Evidence records should state retrieval or review date, freshness requirement,
and expiration guidance. Stale evidence may be shown only when its age and
limitations are visible and it remains safe to do so.

### Uncertainty

GoTime should distinguish:

* Missing user information
* Unconfirmed Assumptions
* AI interpretation uncertainty
* Source limitations
* Conflicting evidence

A confidence value is not proof and must not collapse these categories into one
generic score.

### Cost

Usage should be measured by named capability:

```text
capability
model
request_count
input_tokens
output_tokens
estimated_cost
cache_hit
external_research_cost
duration
```

The least expensive model that reliably performs the capability should be the
default. Prompts and outputs must be bounded, sufficiently current evidence
should be reused, and usage must remain within the configured monthly spending
ceiling. The MVP does not run autonomous background AI.

## Safe Fallback Behavior

If AI is unavailable, over budget, times out, or returns invalid output:

* Trusted state remains unchanged.
* Deterministic reasoning continues.
* The deterministic Recommendation remains visible.
* A curated question or moving-service checklist is used when available.
* The user can provide structured information directly.
* Partial AI output is not presented as verified guidance.
* Loading and error state resolve predictably.

An example fallback Recommendation is:

> Compare the moving-service models that fit your known needs and request
> quotes before the deterministically calculated planning deadline.

## First Narrow AI Experiment

The first experiment should be the named capability:

```text
suggest_moving_service_questions
```

It validates **AI Capability A — State Discovery Assistance**.

The detailed experiment contract is defined in
`docs/experiments/suggest-moving-service-questions.md`.

### Purpose

Given trusted relocation state and a small curated moving-service guide,
suggest the next one to three questions that would help the user determine
which service models are worth investigating.

### Inputs

* Move window
* Origin and destination regions
* Household size, if known
* Storage requirement, if known
* Willingness to drive, if known
* Cost-versus-convenience preference, if known
* Explicitly missing fields
* Relevant curated moving-service entries

### Output

* Up to three suggested questions
* A rationale for each question
* Referenced knowledge IDs
* The information each answer would clarify
* Explicit uncertainties
* No service-model selection

### Success Criteria

* Questions are relevant to supplied state.
* Known information is not requested again.
* Every rationale is grounded in supplied curated knowledge.
* Output validates against the schema.
* No suggestion mutates trusted state.
* The deterministic curated-question fallback remains useful.
* Cost and latency remain within declared per-call limits.

## Staged Experiment Roadmap

### Experiment 1 — Suggest Moving-Service Questions

Validates **Capability A — State Discovery Assistance**.

Use curated moving-service knowledge to suggest a small number of relevant
missing questions. No live research or trusted-state mutation is involved.

### Experiment 2 — Compare Relevant Moving-Service Models

Validates the first curated-knowledge use of **Capability B — Grounded Domain
Guidance**.

Given confirmed user requirements and curated service-model guidance, produce a
grounded comparison of only the relevant options. The user retains the
decision, and every tradeoff references supplied knowledge.

### Experiment 3 — Explain an Approved Booking Window

Validates bounded cooperation between deterministic reasoning and
**Capability B — Grounded Domain Guidance**.

Curated knowledge supplies approved booking-window guidance. Deterministic code
calculates dates from the user-provided target move date and determines the
current timing state. AI explains the deterministic result, applies confirmed
context, and surfaces tradeoffs. AI performs no date arithmetic and invents no
timing rule.

### Experiment 4 — Synthesize Current Provider Evidence

Validates live-evidence use by **Capability B — Grounded Domain Guidance**.

Introduce live research only for provider-specific, regulatory, pricing, or
availability questions where freshness materially affects the answer. Reuse
current evidence when possible and expose sources, retrieval dates,
limitations, and cost.

Each experiment requires separate evaluation and approval. Success at one stage
does not authorize the next.

## Explicitly Deferred Capabilities

The following remain outside the initial AI-assisted reasoning work:

* Live moving-company search in the first experiments
* Current quote or availability collection
* Provider ranking
* Automatic service-model selection
* Booking or contacting providers
* Autonomous monitoring or recurring background research
* Candidate-location scoring
* General-purpose conversational agents
* Unbounded plan generation
* Automatic writes to trusted state
* Vector-search infrastructure without demonstrated need
* AI-owned date arithmetic or validation
* Cross-domain AI orchestration

## Evaluation and Rollout

Each experiment should use fixed scenario fixtures and verify:

* Schema validity
* Grounding coverage
* Relevance to supplied state
* Avoidance of repeated questions
* Honest uncertainty
* Absence of unsupported claims
* User-confirmation boundaries
* Deterministic fallback behavior
* Cost and latency

Initial rollout should be limited to family or testers and triggered by an
explicit user action. Results should be compared with the deterministic
curated fallback before expanding usage.

## Key Design Questions

1. Is question suggestion the highest-value first capability, or would
   interpreting one bounded free-form answer provide a clearer proof?
2. What minimum moving-service knowledge must be curated before Experiment 1?
3. Which planning-window guidance is stable enough for curated use, and when
   does it require live verification?
4. What exact state fields may AI propose for confirmation?
5. Which fields should never accept an AI proposal?
6. How should the interface distinguish user facts, AI interpretations,
   curated guidance, and live evidence?
7. What confirmation language makes clear that the user establishes trusted
   state?
8. How should conflicting curated and live evidence be represented?
9. What freshness periods apply to general guidance and provider-specific
   evidence?
10. What per-call cost, latency, and output-size limits define success?
11. What deterministic Recommendation appears when a capability is unavailable
    or over budget?
12. Which scenario fixtures prove that suggestions respond appropriately to
    storage needs, self-driving willingness, budget sensitivity, and move
    timing?
13. Does the prototype need another deterministic input before Experiment 1
    has enough grounded context to be useful?
