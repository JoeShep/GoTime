# Frozen-v4 budget-policy reconciliation

## 1. Executive summary

Architecture A Milestone 7 correctly stopped with `budget_policy_conflict`.
The conflict is not evidence that the frozen generation estimate is too high.
It results from assigning the entire `$0.03` guardrail to the preflight
token-count operation, consuming that amount at dispatch, and then also
requiring the generation reservation to fit beneath the same `$0.03` case
ceiling.

The source record distinguishes four facts:

- The earliest policy calls `$0.03` a **hard per-call ceiling**, not a cost
  estimate and not a preflight price.
- The approved v4 evaluation plan later describes `$0.03` as the maximum
  provider spend per case, inclusive of preflight and generation.
- The frozen case-bound budget reduces the eligible set from ten to eight,
  fixes eight preflights, eight generations, zero retries, and `$0.24`
  aggregate spend, but contains no operation-specific preflight dollar value.
- The exact v4 preflight produced 2,852 input tokens and `$0.0019408` as the
  **conservative maximum generation cost**. The frozen pricing record says no
  separate token-counting or request/platform fee was documented.

Recommendation: retain `$0.03` as Architecture A's conservative total
per-case safety ceiling and `$0.24` as its aggregate ceiling, but use an exact
operation-specific monetary ceiling of `$0.00` for the token-count preflight
under the frozen pricing model. Continue to consume the preflight operation
slot irreversibly at `provider_dispatch_started`; monetary exposure for that
operation is zero because the frozen evidence records no separate fee. Use the
case-specific conservative generation maximum derived from exact preflight
evidence—`$0.0019408` for the proven case-01 request—as the generation
reservation. This is Option A.

At the design-review stage this was a recommendation requiring human approval,
not an implementation or a change to frozen policy. The outcome below records
the subsequent approval and focused implementation. Milestone 7 remains
blocked pending review and commit of that implementation.

### Approved implementation outcome

The recommendation was subsequently approved and implemented as a focused
Milestones 4–6 correction. The canonical preflight monetary source is now
`PREFLIGHT_CONSERVATIVE_PROVIDER_EXPOSURE_USD = "0.00"`; the `$0.03` case and
`$0.24` aggregate ceilings remain unchanged. The corrected synthetic case-01
grant digest is
`757155c6427132e8ca3a5bdd37a0c3a93adfb0fb386684f403b1940fe0ca0913`,
and the corrected reservation digest is
`8edf28f8378a97796b197bdcb0d0b5bc64b59fbcb2260d5627e313c87c4daec0`.
Preflight still reserves and irreversibly consumes one operation slot. This
correction awaits human diff review and commit; Milestone 7 remains blocked.

## 2. Original budget-policy lineage

The entries below distinguish source wording from later interpretation.

| Value | First source found | Exact source meaning | Frozen? | Later use and current source | Match? |
| --- | --- | --- | --- | --- | --- |
| `$0.01` | `provider-selection.md`, commit `39f5b33e` (2026-07-30) | “target per call” | Research baseline, later carried into readiness records; not a v4 budget field | It remains a comparative target, not an Architecture A accounting constant | Yes; it has not become an authorization amount |
| `$0.03` | `provider-selection.md`, commit `39f5b33e` | “hard per call” | Frozen in `v1/openai-run-configuration.toml` as `maximum_per_call_spend` | The v4 plan calls it maximum spend per case; Architecture A uses `PER_CASE_PROVIDER_CEILING_USD`; Milestone 4 also uses it as the preflight operation ceiling | Mixed: the per-case safety use is a later conservative policy; the preflight-cost use does not match the original label |
| `$0.24` | `v4-formal-evaluation/execution-budget.json`, commit `97886f8c` (2026-08-09) | `maximum_provider_spend_usd` for the case-bound evaluation | Yes; digest `0d848bce...` | `AGGREGATE_PROVIDER_CEILING_USD`; Architecture A documents eight `$0.03` case ceilings | The value matches; its explicit multiplication rationale was documented later |
| `8` preflights | same frozen execution budget | `maximum_token_preflights` | Yes | `MAX_TOKEN_PREFLIGHTS` | Yes |
| `8` generations | same frozen execution budget | `maximum_generation_attempts` | Yes | `MAX_GENERATIONS` | Yes |
| `0` retries | same frozen execution budget and earlier transport policy | `retries` | Yes | `MAX_RETRIES` | Yes |
| `$0.0019408` | completed frozen-v4 preflight evidence and resolved generation candidate | `conservative_maximum_generation_cost` for the exact 2,852-token request | Yes as retained v4 pilot evidence/candidate binding; not a universal value for every case | Reused by the generation gate for that exact request | Yes when treated as case-01 generation exposure |
| `$0.03` preflight operation ceiling | Architecture A Milestone 4 | `conservative_operation_ceiling_usd` for phase `preflight` | Durable grant content, but not a frozen-v4 source artifact | `v4_formal_evaluation_live_grants.py` derives it from `PER_CASE_PROVIDER_CEILING_USD` | No operation-specific source supports this interpretation |

The earlier v1 series ceilings were `$0.20` target, `$0.60` hard, and `$10`
monthly. They belong to the original 20-call planning context. The frozen v4
case-bound budget explicitly superseded only the approved plan's provisional
live-call budget and reduced the execution set to eight provider-eligible
cases.

## 3. Meaning of `$0.03`

### Explicit source evidence

The first repository statement is unambiguous: `$0.03` is a **hard per-call
ceiling**. The frozen v1 run configuration repeats this as
`maximum_per_call_spend = "0.03"`. Provider-selection arithmetic estimated an
OpenAI hard call at only `$0.002000` for 3,000 uncached input tokens plus 500
output tokens; `$0.03` was a safety guardrail, not an estimate of expected
spend.

The approved v4 formal-evaluation plan later says: “Preserve a `$0.03` maximum
provider spend per case, inclusive of that case's preflight and generation.”
That wording is the first explicit total-case interpretation.

### Later Architecture A interpretation

The Architecture A memo binds a `$0.03` “case ceiling” to each AI envelope and
says the eight case ceilings sum to `$0.24`. Its implementation plan carries
that interpretation into prospective accounting. This is a defensible,
stricter refinement of the original guardrail, but it is later terminology;
it should not be presented as the original meaning.

### Current implementation behavior

Milestones 4–6 use `$0.03` twice: as the total per-case ceiling and as the
preflight operation's conservative reservation. Dispatch then converts the
full `$0.03` from reserved to consumed exposure. This exhausts the case before
generation.

### Inference

The complete lineage supports treating `$0.03` as a conservative total-case
safety ceiling in Architecture A, while operation reservations must reflect
their own canonical cost model. It does not support treating `$0.03` as the
estimated or conservative monetary cost of the token-count request.

## 4. Meaning and derivation of `$0.24`

The frozen `execution-budget.json` directly fixes `$0.24` as
`maximum_provider_spend_usd` alongside eight provider-eligible cases. That
artifact does not state the multiplication formula. The subsequent
Architecture A memo explicitly states that eight `$0.03` case ceilings sum to,
but cannot expand, `$0.24`. Therefore:

- `$0.24` itself is frozen policy, not an inference;
- `$0.24 = 8 × $0.03` is explicitly documented Architecture A rationale;
- the multiplication rationale is not embedded in the earlier execution
  budget artifact.

The frozen v4 runner reinforces the intended practical accounting: it counts
preflight and generation operations separately, but its synthetic dollar
spend sums each case's `synthetic_conservative_cost_usd`, which is the
generation cost derived from preflight evidence. It does not add `$0.03` for
each token-count operation.

## 5. Preflight cost model

The preflight is not local tokenization. The transport calls the provider's
`client.responses.input_tokens.count` interface for the exact request, using
the `/v1/responses/input_tokens` endpoint and a five-second timeout. Historical
execution therefore required a credential and provider client, and it is an
operation counted against the eight-preflight maximum.

For the completed frozen-v4 preflight:

- exact input count: `2,852` tokens;
- output assumption used after counting: `500` tokens;
- uncached input price: `$0.40` per million tokens;
- output price: `$1.60` per million tokens;
- token-counting fee: `no_separate_fee_documented_as_of_2026-07-30`;
- request/platform fee: `no_separate_fee_documented_as_of_2026-07-30`.

The calculation performed after token counting is:

```text
(2,852 × $0.40 / 1,000,000) + (500 × $1.60 / 1,000,000)
= $0.0011408 + $0.0008000
= $0.0019408
```

Crucially, the audit and candidate call this
`conservative_maximum_generation_cost`. It estimates the future generation;
it is not the cost of the input-token-count request.

The exact conservative preflight monetary maximum available from the frozen
pricing model is therefore `$0.00`: no separate token-counting fee and no
request/platform fee were documented. This statement is scoped to the frozen
model and its effective date; it is not a general assertion that the endpoint
can never be billed. No separate nonzero preflight ceiling was frozen.

## 6. Generation cost model

`$0.0019408` is the conservative maximum for the exact generation request
measured by the completed case-01 preflight. It assumes all 2,852 input tokens
are billed at the higher uncached-input price and all 500 allowed output tokens
are used. It is bound in the resolved v4 generation candidate together with
the preflight evidence and review digests, deterministic request, canonical
attempt, and provider fingerprint.

For the other seven AI cases, the correct generation ceiling is the same
canonical formula applied to each case's own exact provider token-count
evidence. `$0.0019408` must not silently become a universal generation value.
The frozen runner's synthetic per-case costs follow this case-specific model.

## 7. Where semantic drift occurred

### Milestone 4

The field `conservative_operation_ceiling_usd` was populated from
`PER_CASE_PROVIDER_CEILING_USD`. This faithfully encoded the then-approved
policy interpretation that the `$0.03` total case ceiling also served as the
preflight conservative monetary operation ceiling.

### Milestone 5

Milestone 5 correctly implemented the approved prospective rule—consumed plus
reserved plus requested must fit within the case and aggregate ceilings—but
reserved the grant's then-approved `$0.03` preflight amount. It consistently
propagated Milestone 4's reviewed policy interpretation.

### Milestone 6

Milestone 6 correctly and conservatively converts the full reservation at the
irreversible dispatch boundary. Its irreversible accounting mechanics are not
the source of the conflict. It consistently propagated the same reviewed
interpretation through irreversible reserved-to-consumed accounting.

The reviewed Milestones 4–6 were correct implementations of the policy then in
force; the prior runtime did not perform an unsafe provider operation. The
later-discovered problem was a cross-phase policy inconsistency: consuming the
full `$0.03` case monetary ceiling for preflight left no headroom for
generation's positive conservative monetary exposure. Milestone 7's mandatory
pre-implementation budget-consistency gate exposed that the two phases could
not coexist under that interpretation. This reconciliation therefore
distinguishes the unchanged total case ceiling from phase-specific preflight
monetary exposure; it does not correct an implementation defect in Milestones
4–6.

## 8. Reconciliation options

### Option A — phase-specific conservative operation ceilings

Retain `$0.03` total per case and `$0.24` aggregate. Reserve `$0.00` monetary
exposure plus one operation slot for preflight under the frozen pricing model.
Reserve the exact case-specific conservative generation maximum afterward.
This matches the original guardrail's safety purpose, the v4 plan's inclusive
case ceiling, the frozen runner's spend calculation, and exact operation
economics. Indeterminate preflight dispatch still consumes its operation slot;
there is simply no separately documented monetary charge to consume.

### Option B — `$0.03` per provider call

This matches the earliest wording literally, but it conflicts with the later
inclusive per-case rule. If both preflight and generation independently had a
`$0.03` ceiling, the theoretical eight-case maximum would be `$0.48`, not the
frozen `$0.24`. A new total-case/aggregate policy would be required. This is
unnecessary because the preflight has no separately documented fee.

### Option C — reconcile conservative consumption to actual usage

The architecture memo says actual cost is reconciled against unchanged case
and aggregate ceilings, so later reconciliation was contemplated. Known
provider usage could reduce conservative consumed exposure; indeterminate
dispatch would retain the full conservative amount. However, the preflight
evidence supplies a generation estimate rather than a billed preflight cost,
and no provider-usage result is necessary to know the frozen preflight fee
model. Reserving and consuming `$0.03`, then reconciling it to zero, adds state,
failure modes, and a temporary generation block without improving safety.

### Option D — raise the total per-case ceiling

No source supports a higher case ceiling. This would weaken a deliberate
safety bound and would require revisiting the aggregate policy and bound
identities. Arithmetic convenience is not sufficient justification.

### Option E — change the generation ceiling

No source supports lowering `$0.0019408`. It is an exact, conservative result
of frozen input count, output bound, and pricing. Altering it to make the
budget fit would weaken the evidence gate.

## 9. Recommended policy

Approve Option A with these exact meanings:

- `$0.03`: total provider-exposure safety ceiling for one Architecture A AI
  case, inclusive of preflight and generation; its historical origin remains
  documented as a hard per-call guardrail.
- preflight operation ceiling: `$0.00` under the frozen pricing artifact's
  no-separate-fee model, while still reserving and consuming one preflight
  operation slot;
- generation operation ceiling: the exact case-specific conservative maximum
  derived from provider token-count evidence and frozen pricing—`$0.0019408`
  for the proven case-01 request;
- per-case total ceiling: `$0.03`;
- aggregate ceiling: `$0.24`;
- preflights: maximum eight; generations: maximum eight; retries: zero;
- dispatch: remains the irreversible attempt boundary, including for
  indeterminate outcomes.

This preserves conservative safety without treating unused headroom as if it
were expected spend.

## 10. Milestones 4–6 impact

Human approval would require a focused corrective milestone before Milestone
7:

- Milestone 4: bind the preflight operation ceiling to the frozen preflight
  fee model rather than `PER_CASE_PROVIDER_CEILING_USD`.
- Milestone 5: reserve `$0.00` monetary exposure and one preflight operation
  slot; retain all per-case/aggregate enforcement and durable ledger rules.
- Milestone 6: consume the one operation slot and the exact `$0.00` monetary
  reservation at `provider_dispatch_started`; retain irreversibility,
  idempotency, crash recovery, release prohibition, and zero retries.

No provider execution, result reconciliation, generation grant, or frozen
artifact rewrite is required for that correction.

## 11. Frozen identity and digest impact

Under the recommendation, no frozen formal-evaluation artifact changes:

- `execution-budget.json` and its digest remain unchanged;
- the frozen-v4 manifest and evaluation-set manifest remain unchanged;
- request identities, canonical attempts, provider fingerprints, cases,
  validators, fallback, and evidence remain unchanged;
- AI envelope digests remain unchanged because their `$0.03` case ceiling is
  retained;
- the aggregate package identity remains unchanged because its `$0.03` case,
  `$0.24` aggregate, 8/8 operation, and zero-retry policy remain unchanged;
- the formal evaluation set identity remains unchanged.

The immutable live control-plane records that bind the operation amount do
change:

- every affected preflight grant digest changes because
  `conservative_operation_ceiling_usd` changes from `$0.03` to `$0.00`,
  including the historical synthetic case-01 digest
  `4fd481a5a477a70982bd2ae7df0b5fa6450ad1c62248e4e48cf50e7c7bd6aba9`;
- every affected preflight budget-reservation digest changes because its
  reservation amount and grant binding change, including the historical
  synthetic case-01 digest
  `cbc71820cc3d801a09d90dedb0b279882bccae85da8dd482651a64f6eb1a462a`;
- event digests, history heads, and replay-derived projections for synthetic
  M4–6 state change accordingly.

There is no committed live aggregate state to migrate. Schema names and
versions need not change merely because the approved policy interpretation is
reconciled, but that choice should be confirmed during the corrective review.
This is a runtime control-plane correction, not a revision of the frozen
evaluation package.

## 12. Risks

- “No separate fee documented” could become stale for a future provider or
  pricing date. The correction must bind to this frozen provider/pricing
  artifact, not generalize `$0.00` globally.
- Some reviewers may prefer reserving a nonzero unknown-fee allowance. No such
  canonical value exists; adopting one would be a new policy decision and
  would change bound digests.
- Changing grant and reservation digests requires updating reviewed synthetic
  identities and adversarial fixtures with explicit historical notes.
- Actual generation usage reconciliation remains a separate later decision.
  It is not needed to resolve this pre-generation conflict.

## 13. Required human decision

Human review approved Option A's operation-specific preflight monetary ceiling
while retaining all frozen case, aggregate, count, and retry limits. The
remaining decision is whether the focused implementation diff correctly
realizes that policy and may be committed.

## 14. Exact next step before Milestone 7

Keep Milestone 7 blocked. Human-review and commit the focused Milestones 4–6
correction separately. Only then resume Milestone 7 using the exact
case-specific generation conservative cost.

## 15. Implemented-correction validation

The focused implementation produced these reviewed-current identities and
results:

- corrected synthetic case-01 preflight grant:
  `757155c6427132e8ca3a5bdd37a0c3a93adfb0fb386684f403b1940fe0ca0913`;
- corrected synthetic case-01 reservation:
  `8edf28f8378a97796b197bdcb0d0b5bc64b59fbcb2260d5627e313c87c4daec0`;
- focused grant/budget/dispatch/state tests: 143 passed;
- focused Milestones 1–6: 185 passed;
- full offline experiments: 1,201 passed, 18 skipped;
- backend: 148 passed;
- frontend: 17 passed;
- TypeScript and temporary-directory production build: passed;
- Python compilation: 158 files passed;
- JSON/TOML parsing: 63/23 files passed;
- frozen-v4 verification: passed with zero provider operations; and
- ten-command rehearsal: passed through the focused state suite.

The validation image was pre-existing, used with networking disabled and the
repository mounted read-only, and installed no dependency. The aggregate
package digest remains
`1f6b1b979fd1a244489e0782bf4d37854bb1f800cca8dc4f5faeb06cff83699d`.
The execution-budget, implementation-plan, and permanent closed-manifest
digests remain unchanged.
