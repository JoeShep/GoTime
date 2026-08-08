# Frozen-v3 Live Generation Prose-Failure Postmortem

Status: bounded offline postmortem; no provider operation performed.

## Historical evidence boundary

The retained generation audit (`71d3754e...`), closure (`e441c401...`),
preflight-consumption record (`3c443dd2...`), and closed manifest
(`18a22d62...`) prove that exactly one generation was attempted with no
preflight and no retry. Pydantic and semantic validation passed. Prose
validation failed only with `storage_modality_overstatement`; the complete
response was rejected, no partial salvage occurred, fallback
`moving-service-fallback-v2` / `fallback-temporary-storage-v2` was selected,
no validated response evidence was created, and permanent closure was restored.

The records do not contain the rejected response, matched field, lexical
trigger, offsets, provider request ID, or token usage. The exact generated
wording and exact lexical cause are therefore unknowable. They must not be
reconstructed or inferred from the single violation code.

## Committed validator behavior

`storage_modality_overstatement` inspects `question`,
`information_it_would_clarify`, `why_it_matters`, and `grounding_summary` for a
`temporary_storage_need` suggestion. After Unicode case-folding, collapsing
all whitespace runs to one ASCII space, and applying word boundaries, a field
is rejected when it contains the word `storage` anywhere and at least one of
this exact closed trigger set:

| Canonical trigger | Example normalized match |
| --- | --- |
| `required` | `storage ... required` |
| `requirement` | `requirement ... storage` |
| `must` | `storage ... must` |
| `will need` | `storage ... will need` |

The trigger need not grammatically modify `storage`; same-field co-occurrence
is sufficient. Capitalization and whitespace variation do not matter.
Punctuation may separate `storage` and the trigger, while word boundaries
prevent substrings such as `mustard` and `requirementful` from matching.

The rule is third in the stable five-rule order. Earlier rules do not suppress
it, later rules do not replace it, and all detected codes are returned in
policy order. The historical one-code list proves no other rule fired, but
does not identify the field or trigger.

Frozen prompt v3 explicitly prohibits all four validator triggers in the
three user-facing fields. It additionally prohibits stronger forms the narrow
validator does not recognize, including `necessary`, `likely need`, and
`expected to need`. `grounding_summary` is instead required to mirror the
approved knowledge statement exactly; that statement contains `storage` but
none of the four triggers. The prompt consistently asks whether storage may,
might, or could be needed. No prompt-v3 instruction positively encourages a
validator trigger. The open-ended generation task can still fail to follow an
explicit instruction, but the retained evidence cannot establish why it did.

Disposition: the validator behaved according to its committed lexical
specification. Its known same-field co-occurrence breadth and narrow trigger
vocabulary are unchanged.

## Bounded rejected-prose diagnostics

Future prose failures may include an observational `rejected_prose_diagnostics`
array in the bounded audit. Each item contains only:

```json
{
  "violation_code": "storage_modality_overstatement",
  "rule_id": "moving-service-prose-v2.1",
  "field": "question",
  "start_offset": 33,
  "end_offset": 42,
  "canonical_trigger": "will need",
  "occurrence_count": 1
}
```

Offsets refer to the transient validated field before it is discarded. The
canonical trigger comes from a closed deterministic vocabulary; original
matched text is not copied. Repeated occurrences of the same canonical trigger
in one field are represented by the first span plus a bounded count. Other
rules use fixed canonical phrases or mismatch identifiers. Supplied locations
are represented as `supplied_origin_region` or
`supplied_destination_region`, never by copying their values. Non-lexical
grounding mismatches use zero-length offsets and fixed mismatch identifiers.

The record never contains a complete response, complete field, surrounding
span, provider envelope, raw provider response, credential, or new request
payload. It answers only which rule fired, in which field, for which canonical
trigger, and where the transient match occurred.

The original violation-code collector remains the behavioral oracle. On a
rejection, the diagnostic collector must produce the identical ordered code
set or validation fails closed with an internal drift error. Synthetic tests
prove unchanged accept/reject decisions and code ordering.

## Privacy and retention finding

Synthetic audit scans confirm that complete responses, complete field values,
distinctive prefix/suffix prose, raw provider output, and credential material
are absent. No validated response-evidence file is written for prose failure.
The diagnostic metadata remains useful without preserving rejected prose.

## Prompt-v4 decision memo

Disposition: **prompt-v4 design milestone recommended**, but not implementation
or freezing yet.

- Historical fact: prompt v3 was followed well enough to pass structure and
  semantics, but the result contained a same-field `storage`/trigger
  combination recognized by the committed rule.
- Source/test fact: prompt v3 already explicitly prohibits every current
  modality trigger and requires possibility language.
- Safe inference: another prompt iteration may improve instruction salience,
  especially immediately adjacent to output-field requirements.
- Unknown: which trigger, field, sentence structure, or competing instruction
  caused the live rejection.

The validator should remain unchanged. A later v4 design review may consider
only a small prompt-only reorganization: repeat the closed four-trigger ban at
the final output checklist; require a last lexical self-check of the three
user-facing fields; and separate the immutable `grounding_summary` exception
from user-facing modality instructions. Selecting a field-specific rewrite,
adding an example, or targeting one of the four triggers would be speculative
without rejected text and should not be presumed.

No credential access, client construction, token preflight, generation, or
network operation occurred during this milestone.
