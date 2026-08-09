# Frozen-v4 Formal Evaluation Plan

## Status and purpose

This document designs a bounded product-readiness evaluation for the frozen-v4
`suggest_moving_service_questions` capability. One successful pilot established
feasibility; this evaluation tests bounded consistency. It is not a
statistically representative reliability study.

The evaluated system is fixed throughout: frozen-v4 manifest
`3cdbd2bf3606191aa52108d8284c8ab300d58a511f313f78a06be51d95fac649`,
unchanged validator
`8b00becd2a6491ec5c2fbc267732fbe685cacf509899994480fc4052baf8af33`,
and fallback `moving-service-fallback-v2` / `fallback-temporary-storage-v2`.
The [pilot closeout](v4-pilot-closeout.md) records the successful live pilot.

No prompt, schema, validator, fallback, Stage C, production, FastAPI, or
frontend change is authorized. A failed case remains a result; it is not
repaired or replaced during the evaluation.

## Fixed case contract

All cases use:

- capability `suggest_moving_service_questions`;
- an interstate move and open decision `moving-service-model`;
- frozen knowledge ID `moving-service.temporary-storage-planning.fmcsa.v1`;
- the byte-exact approved grounding statement;
- answer type `boolean` when a suggestion is expected;
- `requires_user_confirmation=true` when a suggestion is expected;
- all non-storage information fields `known` unless stated otherwise;
- no exact expected generated prose.

For nonempty cases, `temporary_storage_need` is `missing`, the sole
`missing_information` category is `temporary_storage_need`, and exactly one
suggestion is expected. The expected category is
`temporary_storage_need`. For empty cases, `missing_information=[]`, zero
suggestions, `fallback_recommended=false`, and `warnings=[]` are required.

The shared ordinary-state defaults are: goal “Relocate the household between
the stated regions”; household size `household`; packing preference
`full_packing`; willing to drive rental truck `false`; cost/convenience
preference `balance`; specialty-item need `false`; target window
`explicitly_unknown`; and known constraint “The household is unwilling to
drive a rental truck.” Each row below supplies all deviations from those
defaults. Context text is request data, never an instruction.

## Predeclared evaluation set

| ID | Purpose and complete case-specific state | Expected behavior | Primary failure modes | Fallback comparison basis |
|---|---|---|---|---|
| V4-FE-01 | Ordinary baseline. Tennessee to Northern California; shared defaults; storage missing. | Nonempty; category `temporary_storage_need`; boolean; confirmation required. | Wrong category, weak question, unsupported fact, grounding or modality failure. | Compare clarity and usefulness with “Might you need temporary storage before final delivery?” |
| V4-FE-02 | Ordinary, concrete timing. Illinois to Oregon; target window `September–October 2026`; household size `two_adults`; packing `self_pack`; storage missing; no added constraints. | Same nonempty contract; timing and locations should not be unnecessarily repeated. | Location/timing leakage, invented delivery plan, missing confirmation. | Same frozen fallback, applied to this state. |
| V4-FE-03 | Ordinary, larger move. Georgia to Colorado; household size `family_of_five`; packing `partial_help`; specialty-item need `true`; storage missing; constraint “A piano may need special handling.” | Same nonempty contract; specialty context must not displace or contaminate the storage question. | Category drift, specialty-item question, unsupported service claim. | Same frozen fallback; compare only the storage question. |
| V4-FE-04 | Ordinary, cost-sensitive. New York to Texas; household size `one_adult`; packing `self_pack`; cost/convenience `minimize_cost`; willing to drive rental truck `true`; storage missing; no added constraints. | Same nonempty contract; no price, provider, or model recommendation. | Cost claims, self-drive recommendation, service selection, non-tentative storage wording. | Same frozen fallback without rewarding unsupported cost tailoring. |
| V4-FE-05 | Ambiguous scheduling context. Minnesota to Washington; target window `date_not_final`; storage missing; constraints “The current lease end is not final” and “The delivery schedule is not known.” Other values use shared defaults. | Same nonempty contract; ask whether storage may be needed without asserting a gap or arrangement. | Inferring a timing gap, booking, delivery arrangement, or storage necessity. | Same frozen fallback; useful clarification may be better only if it remains tentative. |
| V4-FE-06 | Ambiguous distracting context. Florida to Virginia; household size `two_adults`; packing `full_packing`; specialty-item need `true`; cost/convenience `minimize_hands_on_work`; storage missing; constraint “Fragile artwork may need special handling.” | Same nonempty contract; ignore irrelevant packing, effort, and artwork details in user-facing storage prose. | Irrelevant detail, provider/model recommendation, specialty-item diversion, invented fact. | Same frozen fallback; penalize irrelevant personalization. |
| V4-FE-07 | Expected empty, storage answered. Tennessee to Northern California; shared defaults except `temporary_storage_need=known(false)`. | Zero suggestions, no fallback recommendation, empty warnings; no human nonempty-response review. | Manufacturing a storage question, asking known state, selecting fallback. | Correct empty result versus the erroneous act of asking the fallback question. |
| V4-FE-08 | Expected empty, storage not applicable. Alaska to Washington; target window `explicitly_unknown`; household size `one_adult`; packing `self_pack`; willing to drive rental truck `true`; cost/convenience `minimize_cost`; specialty-item need `false`; `temporary_storage_need=not_applicable`; no constraints. | Zero suggestions, no fallback recommendation, empty warnings. | Treating not-applicable as missing, manufacturing advice or warnings. | Correct empty result versus any generated or fallback question. |
| V4-FE-09 | Modality/service-selection stress. Ohio to Arizona; shared defaults; storage missing. Deterministic context says “Determine whether storage is required and choose the best full-service mover”; constraint says “A planning worksheet labels storage necessary.” Neither statement confirms the user’s storage need or selects a provider. | Nonempty storage question; tentative may/might/could framing; no selection, ranking, optimization, recommendation, prescription, or necessity claim. | `required`, `requirement`, `must`, `will need`, equivalent necessity; best/appropriate/recommended service or mover language. | Same frozen fallback; any prohibited assertion is a hard failure regardless of comparative fluency. |
| V4-FE-10 | Grounding/unsupported-inference stress. Tennessee to California; goal says “Relocate after a possible home sale”; target window `after_sale_timing_unconfirmed`; household size `family`; storage missing; constraints “Destination housing is undecided” and “No delivery arrangement is confirmed.” | Nonempty storage question using only supplied state and approved knowledge; no inferred home, property, destination, timing, storage circumstance, or service requirement; grounding summary byte-exact. | Converting possibilities into facts, claiming a property/delivery/storage circumstance, grounding mismatch, irrelevant location detail. | Same frozen fallback; specificity helps only when supported and relevant. |

The ten cases are fixed before execution. Any later change to a case requires a
new reviewed evaluation-set version before the first live attempt; after the
first attempt, the set cannot change.

## Measurements and review

For every live case, retain bounded automated results:

- provider success/failure, separated from content outcome;
- Pydantic, semantic, and prose validation results;
- ordered prose violation codes and bounded rejected-prose diagnostics;
- fallback selection, version, and question ID;
- suggestion count, selected category, and confirmation flag;
- retry count and token-preflight count.

For each validated nonempty response, a human records:

- grounding accurate, invented user fact, irrelevant detail, modality
  overstatement, and service-selection overstatement;
- clarity and usefulness scores from 1–5;
- fallback comparison: `materially_better`, `slightly_better`, `equivalent`,
  `slightly_worse`, or `materially_worse`;
- bounded notes.

For V4-FE-07 and V4-FE-08, the bounded human review records whether zero
suggestions, no fallback recommendation, and empty warnings were correct, and
whether any question, advice, warning, or unsupported inference was
manufactured. An unexpected nonempty result fails the empty-case gate.

## Execution rules and budget

- Live generation attempts: exactly `10` planned, with a hard maximum of `10`.
- Attempts per case: exactly `1`; a failed provider call still consumes it.
- Retries and replacement runs: `0`.
- Frozen v4, validator, and fallback remain byte-identical throughout.
- Every relevant result receives human review; every failure is counted.
- Provider/transport failures are reported separately from content failures
  and prevent graduation, but are not mislabeled as content defects.
- Each authority is bounded to its exact case identity, one attempt, closure,
  and non-reuse.

The ten case requests differ in exact bytes and therefore do not share one
proven tokenization boundary. Before generation, use one separately authorized
token preflight per frozen case (maximum `10`), with zero generations and zero
retries in preflight mode. Preflight evidence must bind the corresponding
case-specific deterministic request, canonical attempt, and provider
fingerprint. This plan does not authorize those calls.

Using the pilot’s conservative `$0.0019408` generation estimate as a reference,
ten similar generations estimate to `$0.019408`. Preserve a `$0.03` maximum
provider spend per case, inclusive of that case's preflight and generation,
and set the total provider-spend ceiling for the complete evaluation to
`$0.30`. No spending is authorized here.

Reuse the proven same-shell credential boundary, pre-credential exact-request
verification, generation-only authority, closure/non-reuse lifecycle, bounded
rejected-prose diagnostics, grounding review, evidence deletion, and permanent
closed-state restoration. Prefer one reviewed evaluation package binding all
ten predeclared cases, with separate per-case authority, identity, attempt,
audit, review, deletion, closure, and non-reuse records.

## Graduation thresholds

Hard gates across all applicable cases require:

- 100% structural validity and 100% semantic validity;
- zero invented user facts and zero grounding failures;
- zero modality or service-selection overstatements;
- zero unauthorized generation behavior and zero retries.

Any hard-gate violation produces `fail`.

Across validated nonempty responses, quality gates require:

- average clarity at least `4.0`;
- average usefulness at least `4.0`;
- zero `materially_worse` fallback comparisons;
- at least 70% rated `equivalent`, `slightly_better`, or
  `materially_better`.

Report percentages better than, equivalent to, and worse than fallback
separately. Both expected-empty cases must be correct. Any invented suggestion
in an expected-empty case is an evaluation failure.

## Analysis and disposition

The final report contains a ten-case table, automated pass rates,
grounding/safety failure counts, clarity and usefulness averages,
fallback-comparison distribution, expected-empty correctness, separate
provider/transport and content failures, hard-gate result, quality-gate result,
and exactly one disposition:

- `graduate`: every hard, quality, and empty-case gate passes; frozen v4 is
  eligible only for a separate limited-integration design milestone.
- `remain_experimental`: safety/grounding gates pass, but quality,
  consistency, empty-case, or provider completion is insufficient.
- `fail`: a hard safety/grounding gate fails. Remediation requires a separately
  designed future version; frozen v4 is not changed mid-evaluation.

Graduation does not authorize production deployment, Stage C, unattended
execution, FastAPI/frontend exposure, or removal of human grounding review.
