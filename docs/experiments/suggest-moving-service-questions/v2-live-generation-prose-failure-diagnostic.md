# V2 Live-Generation Prose-Failure Diagnostic

## Scope and evidence boundary

This is an offline diagnosis of the consumed sequence-4 generation attempt. It
does not reconstruct the rejected response. The raw provider response was not
retained, and no wording beyond the bounded audit may be attributed to it.

Known from exact historical records:

- Pydantic and GoTime semantic validation passed.
- Prose validation failed, in stable order, with
  `storage_modality_overstatement` and
  `unsupported_service_selection_language`.
- The complete response was rejected without partial salvage.
- `moving-service-fallback-v2` / `fallback-temporary-storage-v2` was selected.
- No validated response evidence was written.
- The authorization was consumed and permanent closed authority was restored.

Unknown: the fields, phrases, offsets, capitalization, punctuation, provider
request identifier, and surrounding response text that triggered either rule.
Synthetic examples below demonstrate actual validator behavior, not the live
wording or its exact cause.

## Validator behavior map

All phrase matching uses Unicode `casefold()`, splits on arbitrary whitespace,
and rejoins with one ASCII space. It does not normalize punctuation, stem words,
or infer grammar.

| Check | Fields | Trigger | Character |
| --- | --- | --- | --- |
| `irrelevant_location_reference` | `question`, `information_it_would_clarify`, `why_it_matters` | Exact normalized origin or destination phrase with word boundaries | Exact policy enforcement for this fixture; low false-negative scope, future-category false-positive risk |
| `unsupported_home_or_property_assertion` | same three fields | Exact normalized `your new home`, `your home`, `your house`, `your property`, or `your residence` | Conservative guardrail; deliberately narrow, so indirect assertions can escape |
| `storage_modality_overstatement` | the three prose fields plus `grounding_summary` | Text contains the word `storage` anywhere and also `required`, `requirement`, `must`, or `will need` anywhere | Exact reviewed policy enforcement implemented as a broad lexical guardrail |
| `unsupported_service_selection_language` | the three prose fields | `appropriate`, `best`, `suitable`, or `recommended` immediately followed by a reviewed service/mover/provider noun pattern | Conservative diagnostic guardrail; narrow adjacency creates known false negatives |
| `grounding_summary_mismatch` | `grounding_summary`, `relevant_knowledge_ids` | IDs are not the exact one-item tuple or summary is not byte-for-string equal to the supplied statement | Exact policy enforcement; intentionally rejects harmless formatting drift |

The storage rule does not require the modality word to modify `storage`; both
only need to occur in the same inspected field. This can reject an unrelated
use of `must` alongside `storage`. Conversely, `need`, `likely need`,
`expected to need`, and `necessary` are outside the lexical set even when they
may sound stronger than the prompt's preferred cautious modality.

The service rule uses the regex shape `adjective + whitespace + noun`. The noun
set includes service(s), moving service(s), mover(s), provider(s), service
model(s), and moving-service model(s). Punctuation or an intervening adjective
breaks the match. It does not inspect `grounding_summary` or
`reason_not_deterministic`; exact grounding equality separately constrains the
former.

## Synthetic storage-modality matrix

These results come from the unchanged `_contains_storage_modality_overstatement`
used by the v2 prose validator.

| Synthetic input | Result | Interpretation / match to intent |
| --- | --- | --- |
| Temporary storage may be needed. | accept | Clearly cautious; matches intent |
| Temporary storage might be needed. | accept | Clearly cautious; matches intent |
| Temporary storage could be needed. | accept | Clearly cautious; matches intent |
| Temporary storage may need to be arranged. | accept | Cautious; matches intent |
| Do you need temporary storage? | accept | Borderline neutral question; reasonable |
| You likely need temporary storage. | accept | Stronger prediction; possible false negative |
| You are expected to need temporary storage. | accept | Stronger prediction; possible false negative |
| Temporary storage is necessary. | accept | Strong overstatement; clear false negative |
| Is temporary storage required? | reject | Intentional, including interrogative use |
| Is temporary storage a requirement? | reject | Intentional exact trigger |
| You must arrange temporary storage. | reject | Intentional exact trigger |
| You will need temporary storage. | reject | Intentional exact trigger |

Requested phrase disposition: `required`, `requirement`, `must`, and `will
need` reject when `storage` is present. Bare `need`, `may need`, `may be
needed`, `might need`, `could need`, `likely need`, and `expected to need` are
accepted. The accepted stronger forms show that this is not a complete modality
classifier.

## Synthetic service-selection matrix

These results come from the unchanged `_contains_selection_language` used by
the v2 prose validator.

| Synthetic input | Result | Interpretation / match to intent |
| --- | --- | --- |
| Which services to request | accept | Neutral request language |
| Which moving services to request | accept | Mirrors supplied knowledge |
| Services that may be needed | accept | Descriptive, nonselective |
| Services to discuss | accept | Neutral discussion language |
| Available service options | accept | Descriptive; `available` is not reviewed |
| Possible service needs | accept | Neutral need language |
| Appropriate, moving services | accept | Punctuation false negative |
| Appropriate local moving services | accept | Intervening-token false negative |
| Appropriate moving services | reject | Exact selection adjective/noun match |
| Best moving services | reject | Exact match |
| Suitable movers | reject | Exact match |
| Recommended service model | reject | Exact match |

Requested phrase disposition: `appropriate`, `best`, `suitable`, and
`recommended moving services` reject. `services to request`, `moving services
to request`, `services that may be needed`, `services to discuss`, `service
options`, and `service needs` are accepted. The guardrail is narrower than a
general prohibition on selecting services.

## Prompt-v2 causal review

No phrase can be established as the live cause. Exact prompt text supports
these bounded assessments:

| Prompt text | Assessment | Reason |
| --- | --- | --- |
| “ask whether temporary storage may be needed” (line 43) | clearly safe | Directly specifies cautious modality |
| “describe temporary storage only as a possible need or something that may be needed” (54–57) | clearly safe | Explicit field-wide boundary and blacklist |
| “Do not describe a service…as appropriate, best, suitable, or recommended” (59–61) | clearly safe | Exact prohibited adjectives |
| “Do not select, recommend, compare, rank, or score…” (60–62) | clearly safe | Explicitly blocks selection framing |
| “relevant when identifying the services to request” (34–37) | possibly contributing | Repeats generalized service-planning language that can invite paraphrase |
| “Make `why_it_matters` … concise” (82–83) | possibly contributing | Requires a rationale without a positive safe form, leaving paraphrase latitude |
| “reason_not_deterministic…why user confirmation is needed” (86–88) | unrelated | `reason_not_deterministic` is outside both surviving checks |
| JSON placeholders such as “concise grounded rationale” (101) | possibly contributing | Gives structure but little lexical guidance for the rationale |

The prompt already contains strong prohibitions, so the live codes do not prove
a simple omission. They show that one sampled response did not follow two
explicit instructions. The supplied knowledge phrase and open-ended rationale
field are plausible pressures, not established causes.

## Calibration disposition

`storage_modality_overstatement`: **correct but under-documented**, with known
false positives from its same-field co-occurrence rule and known false negatives
for `necessary`, `likely need`, and `expected to need`. Its four reviewed
triggers should remain unchanged until policy explicitly expands them.

`unsupported_service_selection_language`: **correctly calibrated as a narrow
conservative guardrail**, but under-documented at the punctuation/intervening-
token boundary. It intentionally catches the reviewed adjective/noun pairs and
does not claim semantic completeness.

Neither guardrail should be weakened because the live response failed. The
synthetic matrices support retaining both unchanged.

## Prompt-v3 disposition

Disposition: **prompt_v3_recommended**.

The narrowest proposed changes are:

1. Require each user-facing storage field to use `may be needed`, `might be
   needed`, or another explicitly enumerated cautious form; prohibit `required`,
   `requirement`, `must`, `will need`, `likely need`, `expected to need`, and
   `necessary` in those fields.
2. Prohibit `appropriate`, `best`, `suitable`, and `recommended` anywhere in
   the three user-facing fields, not only when adjacent to a service noun.
3. State that `why_it_matters` must explain relevance without identifying,
   optimizing, choosing, or recommending services.
4. Permit `services to request` only when it mirrors the supplied knowledge;
   otherwise prefer neutral `service needs` or omit service-planning language.

These are prompt recommendations only. Prompt v3 must be separately drafted,
reviewed, versioned, and frozen. The current validators should not change in
that milestone unless a separate policy review approves expanded triggers.

## Rejected-response diagnostic retention

Disposition: **add_bounded_rejected_prose_diagnostics** in a separate reviewed
milestone.

Recommended record: violation code, field name, stable rule identifier,
character offsets, and a canonical matched trigger from the fixed validator
vocabulary. Do not retain an arbitrary surrounding span. For exact lexical
rules, the canonical trigger can be derived deterministically and need not copy
provider text. Grounding mismatch should record only mismatch kind and field,
not either string. Store no full response, provider envelope, trusted state,
prompt, credential, or exception text.

This would distinguish which field and rule fired while keeping privacy and
retention risk low. Complexity is moderate because validators must return
structured matches rather than booleans. The principal risk is allowing a
future “short span” feature to grow into rejected-content retention; fixed
canonical triggers and schema length limits should prevent that.

No live provider call, credential access, client construction, token preflight,
or generation occurred during this diagnostic milestone.
