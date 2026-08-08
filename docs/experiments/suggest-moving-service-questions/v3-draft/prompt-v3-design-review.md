# Prompt V3 Draft Design Review

Status: **draft, unfrozen, unauthorized, and invalid for live execution**.

## Evidence boundary

The consumed sequence-4 response passed Pydantic and semantic validation and
failed prose validation with `storage_modality_overstatement` followed by
`unsupported_service_selection_language`. The complete response was rejected,
fallback v2 was selected, and the raw response was not retained. Exact wording,
field, phrase, offsets, provider request ID, and token usage are unknowable and
are not reconstructed here.

## Identity and schema decision

Proposed prompt identifier: `moving-service-questions-prompt-v3`.

Schema v3 identity is required solely because `MovingServiceQuestionRequestV2`
and `MovingServiceQuestionResponseV2` require both prompt-v2 and schema-v2
literals. A later implementation should add literal-only v3 subclasses with
`moving-service-questions-prompt-v3` and
`moving-service-questions-schema-v3`. Fields, types, enums, constraints,
required lists, and extra-field behavior remain identical. This draft creates
no schema or runtime class.

## Exact semantic delta from frozen prompt v2

### Unchanged capability scope

The sole supported nonempty category, effective zero-or-one suggestion policy,
response shape, exact curated FMCSA statement, confirmation requirement,
fallback ownership, and all prohibitions on recommendation, research, dates,
mutation, selection, general chat, formal evaluation, Stage C, and production
remain unchanged. All five v2 prose validators remain unchanged.

### New modality constraints

User-facing storage fields are limited to may/might/could possibility forms.
The draft adds explicit prohibitions for `likely need`, `expected to need`, and
`necessary` in addition to v2's `required`, `requirement`, `must`, and `will
need`. The prompt explains that the question tests relevance; it does not
predict necessity.

### New service-selection constraints

The prohibition applies across user-facing fields even when punctuation or
intervening words prevent the current adjacency regex from matching. It states
that GoTime has not evaluated or selected the right service.

### Tightened `why_it_matters`

The field may explain planning relevance only. It may not recommend,
characterize, optimize, select, strengthen storage modality, or introduce
location, property, booking, provider, or arrangement facts.

### `services to request`

The phrase is allowed only inside exact `grounding_summary` mirroring. Other
user-facing fields should use neutral planning language. This resolves the
apparent tension without changing the curated statement or exact-equality rule.

### Literal identity changes

Prompt and schema literals advance to v3 in a later implementation. No other
schema semantics change.

### Unchanged grounding and confirmation

`grounding_summary` remains exact string equality with the supplied statement,
including `services to request`. `requires_user_confirmation` remains true.

## No-positive-example decision

Prompt v3 remains example-free. Explicit whitelists, blacklists, field scope,
and semantic prohibitions are sufficient for review. A positive example could
anchor output wording and is not necessary to resolve a design ambiguity.

## Prompt/validator consistency review

| Phrase class | Prompt v3 | Existing validator | Intended policy | Result |
| --- | --- | --- | --- | --- |
| may/might/could need or be needed | allowed | accepted | acceptable | aligned |
| required/requirement/must/will need with storage | prohibited | rejected | unacceptable | aligned |
| likely need/expected to need/necessary storage | prohibited | accepted | unacceptable | mismatch, prompt intentionally stricter |
| adjacent appropriate/best/suitable/recommended service nouns | prohibited | rejected | unacceptable | aligned |
| prohibited adjective separated by punctuation/extra words | prohibited | accepted | unacceptable | mismatch, prompt intentionally stricter |
| exact `services to request` in grounding | allowed | accepted through exact equality | acceptable | aligned |
| `services to request` outside grounding | prohibited | accepted | unacceptable | mismatch, prompt intentionally stricter |
| services to discuss / what to discuss / service needs | allowed | accepted | acceptable | aligned |

The mismatches are defense-in-depth gaps, not contradictions: prompt v3 is
intentionally stricter than unchanged validators. No phrase is both allowed by
the prompt and rejected by a validator. Exact grounding equality remains
compatible with the service-language restriction because grounding is the one
explicit exception.

## Synthetic review

The draft contains 28 hand-authored cases: 13 storage, 13 service, and two
mixed-field cases. Tests execute every case against the unchanged lexical
helpers and verify the five known prompt-stricter-than-validator boundaries.
Existing compliant, historical prose-failure, structural-failure, and
semantic-failure fixtures remain unchanged and continue to pass their existing
tests.

## Separate rejected-prose diagnostics

A later, separate milestone may design bounded records containing only
violation code, field, stable rule ID, offsets, and canonical fixed trigger.
It must retain no full response or surrounding text. That concern does not
change this prompt draft.

## Human-review questions

1. Are the cautious-modality constraints too narrow, too broad, or appropriate?
2. Should `likely need`, `expected to need`, and `necessary` remain prohibited even though the current validator accepts them?
3. Should `services to request` be confined to exact grounding-summary mirroring?
4. Is the tightened `why_it_matters` guidance sufficiently neutral?
5. Should prompt v3 remain example-free?
6. Is the proposed literal-only schema-v3 identity necessary and acceptable?
7. Is prompt v3 ready to freeze, should changes be requested, or should it be rejected?

No artifact in this directory is frozen, authoritative, or valid for live use.

