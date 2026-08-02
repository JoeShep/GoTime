# Stage B Grounding-Failure Diagnostic

## Status and authorization

Diagnostic date: 2026-08-02

Capability: `suggest_moving_service_questions`

This document is an offline diagnosis of the reviewed and rejected Stage B
sequence-5 result. It does not reconstruct the deleted response-evidence file.
It uses the bounded audit, review, deletion, and closure records; the reviewed
phrases preserved in the human-review record and milestone instructions; and
the frozen repository artifacts that produced the request.

Current authorization remains:

```text
Prompt changes authorized: false
Prompt v2 frozen: false
New pilot implementation authorized: false
Credential access authorized: false
Token preflight authorized: false
AI generation authorized: false
Stage C authorized: false
Production use authorized: false
```

The permanent closed authorization digest remains
`6e3ca9cb4488764f012703ab77daae4f4b952895100f7d935935aeb6a0978be5`.
The reviewed response evidence was deleted at review sign-off. Its bounded
audit, rejected human-review record, deletion record, and closure record remain
locally available without response content.

## Pilot outcome

The bounded records establish:

* exact input preflight succeeded with 2,176 tokens;
* one generation succeeded with 250 output tokens;
* provider structured output, Pydantic validation, and GoTime semantic
  validation all passed;
* human grounding review failed;
* the result was rated `slightly_worse` than the deterministic fallback;
* the response introduced an unsupported user fact and a scope overstatement;
* closure succeeded and every active execution permission returned to false;
* reviewed response evidence was deleted immediately after sign-off.

The rejected review preserved this bounded explanation:

> The response asks the correct storage question and is clear, but it is
> slightly worse than the deterministic fallback because it adds unsupported
> destination wording (“your new home in Northern California”) and broadens
> the rationale to “appropriate moving services.” Safer wording would ask
> whether temporary storage may be needed and stay within the approved FMCSA
> scope.

### Documentation consistency

The prompt-v2 design milestone factually closed out the Stage B design and
go/no-go documents. They now record that sequence 5 is consumed, the review was
rejected, the repository is closed, response evidence was deleted, and Stage C
remains unauthorized. Historical pre-execution material is labeled as such and
is not authority for another attempt.

## Exact request boundary

The validated `storage_unknown` request was serialized without added prose in
the frozen declaration order. Relevant values were:

### Trusted state

```text
goal_summary: Relocate the household from Tennessee to Northern California.
move_type: interstate
origin_region: Tennessee
destination_region: Northern California
temporary_storage_need.status: missing
temporary_storage_need.value: null
```

Northern California therefore appeared twice in `trusted_state`: once in the
goal summary and once as the destination region. It was a supplied trusted
planning fact. The request did not say that a new home had been selected,
purchased, occupied, or otherwise confirmed.

### Missing information

```text
category_id: temporary_storage_need
state_field: temporary_storage_need
answer_type: boolean
reason_missing: temporary_storage_need has not been confirmed.
```

The missing-information item supplied neither destination wording nor a claim
that storage was required. It described only an unconfirmed need.

### Deterministic planning context

```text
open decision title: Determine which moving-service models deserve investigation
current recommendation: Clarify unresolved moving-service needs before
  investigating service models.
research stage: moving_service_research
```

Northern California was not present in deterministic context. This context did
contain broader service-model investigation language. The frozen prompt called
it planning context and prohibited restating it as a user fact, but did not
clearly prohibit using its vocabulary in explanatory prose.

### Curated knowledge

The only approved claim was:

> For an interstate move handled by a household-goods mover, a possible need
> for temporary storage before final delivery is relevant when identifying the
> services to request.

The knowledge used `possible need` and `services to request`. It did not use
`new home`, `appropriate moving services`, or `will be required`.

### Serialization

`serialize_request_deterministically()` used the validated Pydantic request and
`model_dump_json(exclude_none=False, exclude_defaults=False)`. It checked the
top-level declaration order and appended no label or prose. Serialization
faithfully exposed the values above; it did not originate any rejected phrase.

## Phrase-by-phrase source trace

| Reviewed phrase | Present source | Absent sources | Diagnosis |
| --- | --- | --- | --- |
| `Northern California` | Trusted-state goal summary and `destination_region` | Missing-information item, deterministic context, curated claim | Supplied trusted fact, but incidental to resolving `temporary_storage_need`. |
| `your new home` | None | Every bounded request section and curated knowledge | Unsupported inference by the external AI model from relocation plus destination. It violated the existing prohibition on deriving or asserting a new user fact from relationships among supplied facts. |
| `your new home in Northern California` | Only the location component was supplied | No source established a selected “new home” | Mixed output: an available trusted location was combined with an invented home fact and unnecessarily repeated in user-facing prose. |
| `appropriate moving services` | None verbatim | Trusted state, missing information, curated knowledge | Unsupported broadening by the external AI model. The nearby deterministic context discussed moving-service models that “deserve investigation,” which plausibly encouraged selection-oriented vocabulary, but did not support “appropriate.” |
| `services to request` | Curated knowledge | — | Approved, deliberately narrow wording. |
| `whether temporary storage will be required` | None | Trusted state, missing information, deterministic context, curated knowledge | Unsupported strengthening by the external AI model from an unknown possible need to a future requirement formulation. It did not assert that storage was required, but it was less cautious than the approved modality. |

## Prompt-gap analysis

Prompt v1 contained meaningful safeguards:

* use only user facts from trusted state;
* do not derive or assert a new user fact from relationships among supplied
  facts;
* use deterministic context only as planning context;
* do not broaden curated knowledge;
* ask whether temporary storage `may be needed`;
* do not state that storage is required;
* keep rationales within the approved temporary-storage scope.

Those rules make `your new home` and `appropriate moving services` instruction
violations rather than authorized behavior. The prompt was nevertheless
ambiguous in three operational ways:

1. It distinguished facts usable for reasoning from deterministic planning
   context, but did not distinguish facts available for reasoning from facts
   necessary to repeat in user-facing prose. A model could treat every trusted
   fact as useful personalization.
2. It prohibited asking about known state, but did not explicitly prohibit
   mentioning an irrelevant known location while asking about a missing field.
3. Its cautious `may be needed` instruction was attached most directly to the
   natural-language question. It did not explicitly require that same modality
   in `information_it_would_clarify`, `why_it_matters`, and
   `grounding_summary`.
4. It allowed paraphrases of curated knowledge. Although it prohibited
   broadening, it did not give a testable lexical boundary between `services to
   request` and selection-oriented phrases such as `appropriate moving
   services`.

The prompt therefore had both a clear instruction-following failure and gaps
that made the failure easier. Fixing the gaps is a semantic prompt change and
requires a new prompt version, new digest, new human review, new frozen
bindings, and a new pilot series or explicitly versioned pilot continuation.

## Validator-gap analysis

The Pydantic response schema correctly enforced required fields, types,
lengths, literals, arrays, and extra-field prohibition. It could not assess
whether free text was grounded.

`validate_response()` correctly enforced:

* unique IDs, categories, and normalized questions;
* selection of an actually missing category;
* the supplied answer type;
* the open decision ID;
* supplied knowledge IDs only.

It did not compare prose with trusted state or curated knowledge. Consequently
it could not detect an invented home, irrelevant location repetition,
selection-oriented paraphrasing, or strengthened storage modality. This is why
schema and semantic validation passed while human grounding review failed.

## Proposed prompt v2 changes

If separately authorized, prompt v2 should add capability-specific rules
equivalent to:

1. Use trusted-state facts for reasoning only when relevant. Repeat a trusted
   fact in `question` or explanatory prose only when it is necessary to identify
   the missing information being requested.
2. For `temporary_storage_need`, do not mention origin, destination, a home,
   residence, selected property, or delivery location beyond the approved
   phrase `before final delivery`. The destination is not needed to ask the
   storage question.
3. Do not infer a home, property, booking, provider relationship, or other user
   fact from the goal summary, regions, decision context, or relationships
   among request fields.
4. In every suggestion text field, describe temporary storage only as a
   `possible need`, something that `may be needed`, or information that remains
   unconfirmed. Do not use `required`, `requirement`, `must`, or `will need` for
   the missing storage value.
5. Preserve `services to request` exactly when expressing the knowledge claim.
   Do not replace it with `appropriate`, `best`, `suitable`, `practical`, or
   `recommended` services or moving-service models.
6. Require `grounding_summary` to quote the supplied temporary-storage
   statement exactly for this v2 capability. This removes paraphrase drift from
   the field intended to demonstrate grounding; it is a structural safeguard,
   not a positive question example.

Positive question examples should remain omitted initially. The failure is
specific enough to address with direct rules, and an example could again
anchor wording rather than test instruction following.

## Proposed narrow deterministic checks

Outcome A should include a small capability-specific validator layered after
the existing semantic checks. It should not become a general prose-grounding
framework.

Recommended checks for a `temporary_storage_need` suggestion:

1. Reject the exact normalized `origin_region` or `destination_region` in the
   generated `question` and `information_it_would_clarify`. Neither is needed
   to identify the storage gap.
2. Reject home/property assertions in those two fields using a very small
   reviewed phrase set such as `your new home`, `your home`, `new house`, or
   `new residence`. Do not attempt general entity inference.
3. Reject storage-necessity terms (`required`, `requirement`, `must`, and the
   phrase `will need`) across `question`, `information_it_would_clarify`,
   `why_it_matters`, and `grounding_summary`.
4. Require normalized `grounding_summary` to equal the supplied curated
   statement exactly under prompt v2.
5. Reject selection adjectives (`appropriate`, `best`, `suitable`,
   `practical`, `recommended`) when they modify or immediately precede
   `service`, `services`, `mover`, `movers`, `provider`, `providers`, or
   `moving-service model(s)` in explanatory fields.

These checks should reject the entire response without repair or salvage and
retain human grounding review for every later pilot or formal response.

## False-positive and false-negative risks

* Location-literal rejection is low risk for this one storage category because
  neither region is needed. It would be inappropriate as a generic rule for
  questions where geography is the missing information.
* A small home/property phrase set catches this observed failure but cannot
  prove that every user fact is grounded. Expanding it into semantic entity
  detection would be brittle.
* Necessity terms are reliable for this missing boolean, but could reject a
  grammatically harmless phrase such as “whether storage is required.” That is
  intentional for prompt v2 because the approved policy prefers possible-need
  wording. The historical v1 fallback still says “Will you need” and remains
  unchanged. The v2 package defines a separate possible-need fallback and the
  exact conditional knowledge statement without rewriting that evidence.
* Selection-adjective checks catch the observed broadening but synonyms can
  evade them, and words such as `practical` may be legitimate elsewhere. Keep
  the check restricted to adjacent service/provider nouns and retain human
  review.
* Exact grounding-summary equality reduces expressive variation but provides a
  strong, auditable knowledge boundary. The natural-language question remains
  the field in which the AI model can add value.

## Answers to the review questions

1. **Was Northern California in the request?** Yes, twice in trusted state.
2. **Trusted state or deterministic context?** Trusted state only; not
   deterministic context.
3. **Did the prompt prohibit incidental location details?** Not explicitly. It
   prohibited asking about known state and inventing facts, but did not say to
   omit irrelevant trusted facts from prose.
4. **Did it distinguish reasoning facts from facts worth repeating?** No, not
   sufficiently.
5. **Why did `services to request` become `appropriate moving services`?** The
   external AI model made an unsupported paraphrase. Broader service-model
   investigation vocabulary in deterministic context likely increased the
   risk, but no request field authorized the claim.
6. **Could the current semantic validator detect the problems?** No. It
   validates references and structure, not prose entailment or relevance.
7. **What suits deterministic checks?** Exact location repetition for this
   category, a small observed home/property phrase set, storage-necessity
   wording, exact grounding-summary equality, and narrowly adjacent
   selection-oriented terms.
8. **What still requires prompt tightening or human review?** Relevance,
   implicit facts, paraphrase entailment, and unforeseen synonyms. Human review
   remains mandatory.
9. **Does correction require prompt v2?** Yes. Every proposed instruction is a
   semantic change under the frozen prompt-versioning rule.
10. **Is another pilot with the same AI model identifier justified?** Yes, but
    only after prompt v2 and checks are separately approved, implemented,
    frozen, and offline-tested. The pilot proved transport and contract
    reliability; one controlled retry can test whether the observed grounding
    failures were boundary-correctable. It cannot establish production value
    or authorize Stage C.

## Recommendation

Recommend **Outcome A: prompt v2 plus narrow deterministic checks**.

Prompt v1 was directionally correct but did not make relevance-to-prose and
paraphrase boundaries testable enough. Deterministic checks alone would not
address the ambiguity, while prompt-only changes would leave the three observed
failure forms mechanically undetected. Stopping the capability is premature
after one contract-valid pilot, but the deterministic fallback remains the
preferred product behavior unless a later reviewed pilot demonstrates a clear
grounding and usefulness improvement.

The narrowest next milestone is a documentation-only prompt-v2 design and
validator-rule specification. It must stop for human review before modifying
the frozen prompt, runtime validation, provider bindings, or authorization.
