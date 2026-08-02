# Prompt v2 and Prose-Validation Design — Suggest Moving-Service Questions

## 1. Status and scope

```text
design date: 2026-08-02
capability: suggest_moving_service_questions
recommended prompt version: moving-service-questions-prompt-v2
Prompt v2 approved: false
Prompt v2 frozen: false
Prose checks approved: true
Prose checks implemented: true
Follow-up pilot authorized: false
Credential access authorized: false
Token preflight authorized: false
AI generation authorized: false
Stage C authorized: false
Production use authorized: false
```

This document designs a successor prompt, capability-specific prose checks,
and one follow-up pilot. It does not modify prompt v1, create a prompt-v2
artifact, change runtime validation, authorize execution, or create Stage C.

The recommendation is **Outcome A: prompt v2 plus narrow deterministic
checks**. Sequence 5 proved that the provider transport and existing structural
and semantic contracts can succeed, but human review rejected the prose as
ungrounded and slightly worse than the deterministic fallback. One controlled
follow-up with the same AI model identifier can test whether tighter boundaries
correct that specific failure. It cannot establish reliability or product
value.

## 2. Evidence and problem statement

The reviewed Stage B response:

* repeated the supplied destination in `your new home in Northern California`;
* inferred a `new home`, which was not present in the request;
* changed the approved `services to request` wording into the broader
  `appropriate moving services`; and
* used `whether temporary storage will be required`, strengthening the
  knowledge item's `possible need` modality.

`Northern California` was supplied only as trusted state. The inferred home,
selection adjective, and strengthened modality were not supplied anywhere.
The deterministic request serialization added no prose. Existing Pydantic and
GoTime semantic validation correctly passed the response because neither layer
currently evaluates prose relevance or grounding.

## 3. Version and contract decision

The proposed prompt identifier is:

```text
moving-service-questions-prompt-v2
```

Prompt v1 is immutable and remains bound to
`moving-service-questions-schema-v1`. The current Pydantic request and response
schemas each constrain `prompt_version` to the v1 literal. A v2 response cannot
pass those classes unchanged.

The recommended implementation decision is to create a separately versioned
v2 request/response contract with:

```text
request schema version: moving-service-questions-schema-v2
response schema version: moving-service-questions-schema-v2
knowledge fixture version: moving-service-storage-fixture-v2
```

The only intended schema-semantic change is the prompt/schema identity needed
to preserve exact version binding; existing fields, types, required status,
limits, and prohibitions must not be weakened. The v1 classes and frozen
provider-schema snapshot must remain usable for v1 artifact validation. The
implementation design must choose a capability-specific versioned model
boundary rather than widening the v1 prompt literal to accept arbitrary
versions.

This contract-version decision requires human approval before any prompt-v2
artifact or code is created. Prompt v2 will also require a new reviewed prompt
digest, provider-schema snapshot, run configuration, manifest binding, and
offline drift checks.

## 4. Prompt-v2 instruction design

Prompt v2 should preserve every v1 capability, missing-information, knowledge,
mutation, output, injection, token, retry, and execution boundary. It should
add the following capability-specific instructions.

### 4.1 Reasoning facts versus user-facing prose

Use supplied trusted-state facts only as bounded reasoning inputs. Availability
of a trusted fact does not make it relevant to repeat. Repeat a trusted-state
fact in `question`, `information_it_would_clarify`, or `why_it_matters` only
when that fact is necessary to identify the selected missing-information
category or make its question understandable.

For `temporary_storage_need`, origin and destination are not necessary to ask
the approved question. Omit origin names, destination names, and incidental
location details from those fields. Do not personalize prose with other known
facts merely because they are supplied.

Continue treating deterministic context as planning context, not user fact.
Its wording is not approved wording for the question or rationale. Do not copy
or paraphrase selection-oriented language from the open decision or current
recommendation.

### 4.2 Unsupported objects and arrangements

Do not infer or mention a home, house, property, residence, selected delivery
location, provider relationship, booking, or service arrangement unless that
fact is explicitly supplied and directly necessary to the selected missing
category. For the approved `temporary_storage_need` path, none is necessary.
The approved knowledge phrase `before final delivery` remains permitted because
it describes the knowledge scope, not a confirmed delivery arrangement.

### 4.3 Storage modality

Ask whether temporary storage **may be needed**. Across `question`,
`information_it_would_clarify`, `why_it_matters`, and `grounding_summary`, keep
the missing value uncertain and preserve the knowledge statement's `possible
need` modality. Do not describe storage as `required`, a `requirement`,
something the user `must` use, or something the user `will need`.

This is intentionally stricter than merely prohibiting a declarative claim.
Even an interrogative such as “Will storage be required?” is outside prompt
v2's approved wording policy. The rule does not prohibit
`reason_not_deterministic` from saying that user confirmation is required;
that statement concerns confirmation, not storage.

### 4.4 Service-selection language

Do not describe a mover, provider, service, or moving-service model as
`appropriate`, `best`, `suitable`, or `recommended`. Do not convert `services
to request` into language about selecting or identifying a desirable service,
provider, or model. Keep the question understandable without adding such
context.

### 4.5 Exact grounding summary

For the v2 `temporary_storage_need` path, require `grounding_summary` to equal
the `statement` of the referenced approved temporary-storage knowledge item
exactly after JSON decoding:

```text
For an interstate move handled by a household-goods mover, a possible need for temporary storage before final delivery is relevant when identifying the services to request.
```

No whitespace normalization is permitted. Leading or trailing whitespace,
changed internal whitespace, changed punctuation, omitted conditions, changed
modality, or appended text causes a mismatch. Exact equality is simpler to
audit than a special normalization algorithm and makes every broadened or
strengthened paraphrase mechanically visible.

The supplied knowledge ID remains required. For this path,
`relevant_knowledge_ids` should contain exactly
`moving-service.temporary-storage-planning.fmcsa.v1`, and the summary must equal
that item's supplied statement—not a separately hard-coded prose copy in
runtime validation. The prompt may state the rule without duplicating the
fixture-specific statement if doing so keeps the request as the single source
of the exact text.

This policy does not automatically generalize to future knowledge items. A
future item must be reviewed for length, suitability for user-facing exact
reproduction, and single-item versus multi-item grounding before it is enabled.
If multiple knowledge items later ground one suggestion, their presentation
and comparison rule require a new prompt and validator decision.

### 4.6 Examples

Do not add positive few-shot examples to prompt v2. Direct rules and exact
grounding equality target the observed failures without encouraging fixed
question wording. Adding an example would increase input size, introduce
anchoring, and itself require versioned review.

## 5. Capability-specific prose checks

The proposed validator runs only after the existing Pydantic response and
GoTime semantic validators and only for this named capability. It examines
each `temporary_storage_need` suggestion. It is not a general natural-language
rules engine.

Normalization for phrase matching should be limited to Unicode case-folding
and collapsing runs of whitespace. It should not stem words, infer entities,
or remove arbitrary punctuation. Exact grounding comparison uses no
normalization.

### 5.1 `irrelevant_location_reference`

Fields: `question`, `information_it_would_clarify`, `why_it_matters`.

Reject a case-folded, whitespace-normalized occurrence of the exact nonempty
`origin_region` or `destination_region` supplied in trusted state. Compare only
those two bounded request values. Do not reject every proper noun, maintain a
general place-name list, or infer locations from free text.

False-positive risk: a future storage question might legitimately distinguish
locations. That is unacceptable under this current fixture but could become
valid under a future knowledge/request contract. The rule must therefore be
enabled only for the reviewed temporary-storage path and revisited before such
a contract change.

### 5.2 `unsupported_home_or_property_assertion`

Fields: `question`, `information_it_would_clarify`, `why_it_matters`.

Reject this initial reviewed normalized phrase set:

```text
your new home
your house
your property
your residence
```

The rule targets direct second-person assertions. Do not reject generic `home`
or `homes`, the approved `household-goods mover`, or `before final delivery`.
This keeps neutral or future legitimate uses from being swept into a broad
property detector.

False-positive risk: a later trusted state could explicitly confirm a
residence. That fact is absent and irrelevant here. Future support would need
a category-specific exception approved with its request contract; the current
rule should not attempt inference.

### 5.3 `storage_modality_overstatement`

Fields: `question`, `information_it_would_clarify`, `why_it_matters`, and
`grounding_summary`.

For a `temporary_storage_need` suggestion, reject normalized storage-related
wording containing `required`, `requirement`, `must use storage`, or `will need
storage`, including interrogative uses. Matching must be tied to storage or the
selected storage field; a generic statement in `reason_not_deterministic` that
user confirmation “is required” is outside this check.

False-positive risk: “Is storage required?” is grammatically valid and does
not assert an answer. Rejecting it is nevertheless intentional because prompt
v2 adopts the narrower policy “may be needed.” Broader synonym detection stays
with human review unless a later observed failure justifies another reviewed
phrase.

### 5.4 `unsupported_service_selection_language`

Fields: `question`, `information_it_would_clarify`, `why_it_matters`.

Reject a small normalized token-pair/window rule when an adjective in:

```text
appropriate, best, suitable, recommended
```

directly modifies or immediately precedes one of:

```text
service, services, mover, movers, provider, providers,
moving-service model, moving-service models
```

Allow only punctuation or the token `moving` inside the matched noun phrase;
do not implement general sentiment or dependency parsing. Exact
`grounding_summary` equality separately prevents selection language there.

False-positive risk: these adjectives can be harmless in another capability,
but they imply selection in this one. Synonyms and distant grammatical
relationships can evade the check, so human review remains required.

### 5.5 `grounding_summary_mismatch`

Field: `grounding_summary` plus `relevant_knowledge_ids`.

Reject unless the suggestion references exactly the supplied approved
temporary-storage knowledge ID and the decoded summary string exactly equals
that referenced item's supplied `statement`. This catches condition omission,
modality strengthening, broadened paraphrases, appended claims, and formatting
changes.

False-positive risk: exact equality rejects harmless punctuation and whitespace
variation and reduces stylistic freedom. That is acceptable because
`grounding_summary` is an audit field; expressive value belongs in the
question. Future multi-item grounding requires a separately reviewed rule.

## 6. Validation outcome

Any single prose violation rejects the complete response. Do not repair text,
drop an individual suggestion, or retain a partially valid model result.

The evaluation runner should record a bounded top-level classification such as
`prose_validation_failure` and a stable, de-duplicated list of all detected
violation codes in this order:

1. `irrelevant_location_reference`
2. `unsupported_home_or_property_assertion`
3. `storage_modality_overstatement`
4. `unsupported_service_selection_language`
5. `grounding_summary_mismatch`

Recording multiple codes helps diagnosis without exposing response content.
The first violation must not short-circuit the remaining bounded checks. The
existing deterministic orchestration may then select its fallback; the model
and adapter still do not own fallback selection, and the rejected attempt
remains recorded as failed.

These checks do not replace human grounding review. Human review remains
responsible for unforeseen implied facts, indirect selection language,
semantic relevance, clarity, usefulness, and comparison with the deterministic
fallback.

## 7. Deterministic fallback reconciliation

This implementation milestone defines a separate deterministic fallback as
`moving-service-fallback-v2` inside the v2 package. Its reviewed question is
"Might you need temporary storage before final delivery?" and it uses the
exact conditional knowledge statement as its rationale. The historical v1
fallback and fixtures remain unchanged. The v2 fallback remains distinct from
`grounding_summary`: model grounding is always compared with the knowledge
statement supplied in the validated request, never with fallback prose or
identity.

Prompt v2 supports `temporary_storage_need` as its only nonempty
missing-information category. The system instructions state this explicitly,
and an offline deterministic request gate rejects a v2 request containing any
other nonempty category before response validation or future invocation.

## 8. Follow-up single-generation pilot

Proposed exact pilot identity and scope:

```text
run-series ID: moving-service-stage-b-v2-pilot-20260802
sequence: 1
fixture: storage_unknown
provider: OpenAI
AI model identifier: gpt-4.1-mini-2025-04-14
SDK pin: openai==2.45.0
maximum token-preflight requests: 1
maximum AI-generation requests: 1
automatic retries: 0
token-preflight timeout: 5 seconds
AI-generation timeout: 12 seconds
maximum output tokens: 500
maximum total spend: $0.03
human grounding review: required
formal evaluation authorized: false
Stage C authorized: false
production use authorized: false
```

The pilot requires a fresh exact token preflight for the exact v2 request and
one generation using the same provider and AI model identifier. It must use a
new frozen prompt-v2 artifact and digest, versioned request/response contract,
reviewed provider-schema snapshot, frozen pilot run configuration, and a new
short-lived single-use authorization. It must retain the existing zero-retry,
timeout, credential, budget, record, evidence-deletion, and immediate-closure
controls unless separately reviewed.

Pilot contract success additionally requires no prose violation codes. Human
grounding success requires no invented fact, scope overstatement, storage
necessity strengthening, provider/service recommendation, or FMCSA broadening.
The reviewer should use the existing bounded clarity, usefulness, and fallback
comparison fields.

One successful pilot would show that this observed failure is
boundary-correctable for one call. It would not establish a reliability rate,
authorize Stage C, or justify production use. A second rejection should trigger
a stop/retain-fallback decision before considering a different AI model.

## 9. Required offline implementation milestones

If the design is approved, later separately authorized work should proceed in
this order:

1. Approve the v2 contract-version decision and exact prose rules.
2. Draft, review, token-check, and freeze prompt v2 without changing prompt v1.
3. Add versioned Pydantic contracts and capability-specific prose validation;
   preserve all v1 artifact tests.
4. Generate and review a v2 OpenAI response-schema snapshot and run
   configuration with new digests.
5. Add fake-response tests for each violation, multiple violations, complete
   response rejection, fallback ownership, and false-positive boundaries.
6. Run all network-disabled suites and artifact drift checks.
7. Stop for a separate follow-up-pilot authorization decision.

No stronger AI model is proposed. The v1 prompt left relevance and paraphrase
boundaries insufficiently testable, so changing the AI model before testing
those boundaries would confound the experiment.

## 10. Remaining human decisions

The contract identity, exact grounding rule, phrase sets, failure codes,
multi-code recording, and follow-up pilot identity were approved for offline
implementation. Human review must still decide whether to:

* approve and freeze the exact prompt-v2 artifact;
* approve the schema-v2 contract artifacts;
* generate, review, and freeze the provider response-schema snapshot;
* approve and freeze a v2 run configuration; and
* later authorize a single follow-up pilot.

Prompt-v2 and schema-v2 artifact approval, freezing, and every execution status
remain false until those separate reviews.
