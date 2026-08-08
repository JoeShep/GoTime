# Prompt V4 Design Memo

Status: design only; unimplemented, unfrozen, unauthorized, and invalid for
live execution.

Recommendation: **proceed** to a separate implementation/freeze milestone,
subject to preserving the exact-grounding rule described below.

## Evidence boundary

### Established historical facts

One frozen-v3 generation passed Pydantic and semantic validation and failed
only `storage_modality_overstatement`. The complete response was rejected,
fallback v2 was selected, no response evidence or grounding review existed,
there was no retry, and permanent closure was restored. Rejected prose was not
retained.

### Established source facts

The unchanged validator inspects `question`,
`information_it_would_clarify`, `why_it_matters`, and `grounding_summary`. A
field fires when normalized text contains `storage` plus `required`,
`requirement`, `must`, or `will need`. Its SHA-256 remains
`8b00becd2a6491ec5c2fbc267732fbe685cacf509899994480fc4052baf8af33`.

Frozen prompt v3 already requires may/might/could possibility framing,
prohibits all four runtime triggers plus broader policy forms, prohibits
service selection, constrains `why_it_matters`, preserves exact grounding, and
contains no positive examples.

### Inference

Moving a short closed-trigger check immediately next to final-output issuance
is likely to make the runtime boundary more salient. This is an instruction-
following improvement, not evidence that prompt position caused the live
failure.

### Unknowns

The actual field, trigger, wording, offsets, and instruction interaction are
unknowable. Prompt v4 must not target any one field or phrase as the historical
cause.

## V3 failure-surface analysis

1. **Position.** The main modality paragraph appears well before the per-field
   checklist, response template, and final JSON-only instruction. The final
   output boundary does not repeat the exact four runtime triggers.
2. **Repetition and dilution.** Modality policy is repeated indirectly in
   `why_it_matters`, but the closed validator set is stated only once. The
   prompt contains many equally imperative scope, grounding, selection,
   formatting, and schema rules after it.
3. **Grounding tension.** V3 says the user-facing fields must use cautious
   modality while `grounding_summary` is copied exactly and “is not rewritten
   under this rule.” This is internally consistent for the approved source,
   which has no runtime trigger, but the exception makes an all-field lexical
   check less obvious.
4. **Separation.** Curated knowledge is identified as bounded evidence, and
   exact grounding is specified, but generated prose and mechanically copied
   grounding are not summarized as two distinct output modes at the final
   boundary.
5. **Inspection coverage.** V3 does not explicitly instruct a final inspection
   of all four validator-inspected fields.
6. **No deterministic self-check.** It lists prohibited forms but never says to
   scan, rewrite, and recheck immediately before returning JSON.
7. **Faithful grounding.** Nothing in the approved source requires stronger
   modality. However, the phrase “copy the exact statement” could dominate a
   more general prose instruction if a future source drifted. That is a design
   risk, not an explanation of the historical response.
8. **Prompt density.** The prompt is necessarily detailed. No paragraph is
   clearly unrelated enough to delete safely in this narrow milestone;
   editorial compression would add review risk without directly aligning the
   runtime trigger set.

## Minimal prompt-v4 design

Prompt v4 should preserve prompt v3 byte-for-semantic-content except for the
following small additions and one clarification. It remains example-free.

### 1. Grounding and generated-field separation

Add immediately before the existing exact-grounding paragraph:

> Treat curated knowledge as evidence, not as a writing style to imitate in
> generated user-facing prose. `question`, `information_it_would_clarify`, and
> `why_it_matters` must independently obey the possibility-language rules.
> `grounding_summary` remains a byte-exact copy of the approved statement and
> is not paraphrased. The approved statement must itself contain none of the
> closed runtime triggers listed below; if it does, do not generate a
> suggestion.

This deliberately does **not** adopt “summarize faithfully while softening the
source.” Paraphrasing would violate exact grounding-summary equality. A future
source containing a trigger must fail closed before generation rather than be
silently rewritten. The frozen source currently satisfies both constraints.

### 2. Closed lexical prohibition

Add a short named block after the existing modality paragraph:

> Closed runtime lexical rule: none of `question`,
> `information_it_would_clarify`, `why_it_matters`, or `grounding_summary` may
> contain the whole word `required`, `requirement`, or `must`, or the phrase
> `will need`. This exact four-trigger rule is narrower than the broader policy
> prohibitions above; both sets remain binding.

This is required for explicit runtime-validator alignment. It does not replace
the broader v3 policy against `likely need`, `expected to need`, `necessary`,
or equivalent assertions.

### 3. Final lexical self-check

Insert immediately before “Return exactly one JSON object”:

> Before returning JSON, inspect every generated value for `question`,
> `information_it_would_clarify`, `why_it_matters`, and `grounding_summary`.
> Case-insensitively check for the whole-word triggers `required`,
> `requirement`, and `must`, and for `will need` after treating whitespace as a
> single space. If any trigger appears in a field that may be rewritten,
> rewrite that field using may/might/could possibility language and check all
> four fields again. Never rewrite `grounding_summary`; if its exact approved
> source contains a trigger, return no suggestion. Perform this check silently
> and do not add fields, warnings, commentary, or reasoning to the JSON.

This is a conceptual self-check, not chain-of-thought disclosure and not a new
schema field.

## Exact conceptual diff

| Change | Classification | Scope |
| --- | --- | --- |
| Add evidence-versus-writing-style clarification | grounding/user-facing separation | one paragraph |
| State exact four-trigger/all-four-field rule | required for runtime-validator alignment | one short block |
| Add rewrite/recheck instruction at final output boundary | salience improvement | one paragraph |
| State grounding source drift fails closed rather than being paraphrased | grounding/user-facing separation | two sentences |
| Retain broader v3 modality and service rules | unchanged | no edit |
| Retain exact grounding equality | unchanged | no edit |
| Retain no-positive-example policy | unchanged | no edit |
| Remove or broadly rewrite other prompt prose | not proposed | none |

Estimated size change: approximately 150–210 words, or roughly 190–270 input
tokens depending on provider tokenization. No deletion is proposed in the
first v4 draft because the benefit of editorial compression is less direct
than the review risk. A later mechanical review may remove exact duplication
only if semantic equivalence is proven.

## Adversarial offline matrix

Prompt-policy behavior and unchanged runtime behavior must be asserted
separately.

| Case | Field / construction | Prompt-v4 expectation | Existing validator expectation |
| --- | --- | --- | --- |
| 1 | `storage is required` | rewrite before output | reject: modality |
| 2 | `storage is a requirement` | rewrite before output | reject: modality |
| 3 | `storage must be discussed` | rewrite before output | reject: modality |
| 4 | `storage will need discussion` | rewrite before output | reject: modality |
| 5 | trigger in `question` | rewrite and recheck | reject: modality |
| 6 | trigger in `information_it_would_clarify` | rewrite and recheck | reject: modality |
| 7 | trigger in `why_it_matters` | rewrite and recheck | reject: modality |
| 8 | trigger in `grounding_summary` | no suggestion; never paraphrase grounding | reject: modality, and likely grounding mismatch if changed |
| 9 | hypothetical approved source contains a trigger | configuration/preparation must fail closed; no generation | exact copy would reject; softened copy would fail grounding equality |
| 10 | `storage may be needed` | allow | accept |
| 11 | `storage might be needed` | allow | accept |
| 12 | `storage could be needed` | allow | accept |
| 13 | `appropriate moving services` | rewrite under unchanged selection policy | reject: service selection |
| 14 | modality trigger plus service-selection trigger | rewrite both before output | reject both in stable order |
| 15 | `storage is likely necessary` plus punctuation-separated selection wording | prohibit under broader prompt policy | validator may accept; documented defense-in-depth gap |

Additional variants should cover capitalization, tabs/newlines in `will need`,
punctuation, same-field non-grammatical co-occurrence, all four fields, and the
exact frozen grounding statement. Offline tests must demonstrate that the
prompt policy is stricter than—not contradictory to—the unchanged validator.

## Schema and version decision

- Prompt identity: `moving-service-questions-prompt-v4`.
- Schema identity: `moving-service-questions-schema-v4`.

Schema v4 is required only because the repository intentionally couples prompt
and schema version literals for fail-closed identity. The structural schema,
fields, types, enums, limits, required lists, nested models,
`additionalProperties`, and extra-field rejection remain unchanged. Provider,
model, SDK, timeout, output-token limit, retry count, fallback v2, grounding
source, and deterministic behavior also remain unchanged.

## Risks and tradeoffs

- Repetition increases prompt size and does not guarantee model compliance.
- A silent self-check is still an instruction, not deterministic enforcement;
  the unchanged validator remains authoritative.
- Applying the closed rule to `grounding_summary` is safe only because the
  approved source currently contains no trigger. Source drift must fail closed.
- Prompt v4 remains intentionally stricter than the runtime validator for
  `likely need`, `expected to need`, `necessary`, and non-adjacent selection
  wording.
- Adding positive examples could anchor wording and is not justified by the
  retained evidence; the no-positive-example policy should remain.
- Another live failure would not justify weakening the validator. The new
  bounded diagnostics should instead identify the future field and canonical
  trigger without retaining prose.

## Decision criteria and disposition

The proposed v4 is materially narrower than a rewrite: it adds explicit
all-field runtime alignment, separates generated prose from exact grounding,
and places a lexical check at the final output boundary. It does not guess the
historical wording, change validators or fallback, expand scope, or require a
provider call to test.

Disposition: **proceed** to a separately authorized implementation/freeze
milestone. That milestone must first prove the frozen grounding statement has
no closed trigger, create literal-only v4 schemas, run the adversarial matrix
offline, preserve validator SHA-256, and keep all live authorization false.
