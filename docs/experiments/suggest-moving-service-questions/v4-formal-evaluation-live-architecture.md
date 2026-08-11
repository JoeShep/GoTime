# Frozen-v4 Formal Evaluation Live Architecture

## Status and recommendation

Recommendation: `recommend_A`.

Use one reviewed aggregate evaluation package with eight exact, independent
case envelopes. Each envelope contains two sequential, separately activated,
single-use phase grants: token preflight, then generation. This preserves one
coherent ten-outcome evaluation without allowing the aggregate package or a
case envelope to make an unrestricted provider call.

This is design only. It creates no authority, spending permission, credential
path, provider client, live state, or runtime integration.

## Fixed identities and scope

The aggregate package binds:

- evaluation set
  `suggest-moving-service-questions-v4-formal-evaluation-set-v1` and its
  manifest SHA-256
  `38c4db2e92368ead41f9c6f87146a83103ae7780328aa7423d13340239134e94`;
- runner `suggest-moving-service-questions-v4-formal-evaluation-runner-v1`;
- frozen-v4 manifest
  `3cdbd2bf3606191aa52108d8284c8ab300d58a511f313f78a06be51d95fac649`;
- execution-budget SHA-256
  `0d848bce8866023a5b7f7912795a6ee80b3aae471189f447911244da10777b6b`;
- request-identities SHA-256
  `a23de86e93c3b83b7d51ffa5f73c5d694cd8266c5013c6d14833ad64bddd40ee`;
- all ten case IDs and deterministic case-input identities;
- the exact request, canonical-attempt, and provider-fingerprint identities for
  `eval-v4-01`–`06`, `09`, and `10`;
- deterministic-empty status and absent provider identities for
  `eval-v4-07` and `eval-v4-08`;
- eight preflights maximum, eight generations maximum, one of each per eligible
  case, zero retries, zero empty-case provider requests, and a `$0.24` ceiling;
- named operator and evaluator/reviewer identities; and
- aggregate status: `prepared`, `approved`, `in_progress`, `ready_to_finalize`,
  `expired_paused`, `abandoned`, or `closed`.

The aggregate package authorizes only creation and coordination of the listed
case/phase candidates within those bounds. It is not provider authority, does
not authorize spending by itself, and cannot substitute one case identity for
another. Only an exact, reviewed, active phase grant may permit its one
provider operation.

## Case envelopes and phase grants

Each generation-eligible case has one envelope bound to its case-input digest,
request digest, canonical-attempt digest, provider fingerprint, provider,
model, pinned SDK, aggregate-package identity, `$0.03` case ceiling, and durable
case state. It permits at most one preflight, one generation, and zero retries.
The eight case ceilings sum to, but cannot expand, the `$0.24` aggregate limit.
Reviewed preflight evidence records the case's measured/estimated cost but does
not rewrite or lower its frozen `$0.03` authority ceiling. Actual cost is
reconciled against both the unchanged case ceiling and aggregate ceiling.

Within an envelope, use separate preflight and generation phase grants. A
preflight grant permits exactly one token-count operation and zero generations.
It closes after success, failure, or indeterminate dispatch. Its exact evidence
must be reviewed and bound to the same case identities before a generation
grant can be prepared. A generation grant permits exactly one generation and
zero token preflights. Phase grants are short-lived, independently reviewed,
atomically activated, consumed once, and permanently non-reusable. Expiry never
restores an attempt or changes completed history.

This two-grant design is slightly more explicit than one multi-phase authority,
but it makes the preflight review gate and the absence of latent generation
permission mechanically clear.

## Sequencing and human review

Execute generation-eligible cases case-by-case in stable case-ID order:

`eval-v4-01` → `eval-v4-02` → `eval-v4-03` → `eval-v4-04` → `eval-v4-05` →
`eval-v4-06` → `eval-v4-09` → `eval-v4-10`.

1. prepare, review, activate, and run the case preflight;
2. close and review its preflight evidence;
3. prepare, review, activate, and run its generation;
4. close the generation phase and apply automated validation/fallback rules;
5. immediately perform the required grounding/quality review for a validated
   nonempty response;
6. explicitly delete response evidence and close the case; then
7. proceed to the next unfinished case.

Case-by-case execution shortens authority and evidence lifetimes, keeps request
binding visible, exposes cost incrementally, and leaves a clean resume point.
A preflight-first batch would reduce context switching but would retain eight
evidence bindings longer and increase cross-case and freshness risk.

Grounding review and evidence deletion are mandatory before proceeding to the
next generation case. Automated rejection or provider failure has no validated
response evidence to review, but still requires audit, closure, and terminal
non-reuse.

The preferred validated-response retention is same-session review followed
immediately by evidence deletion. When review must be postponed, retention is
bounded to 24 hours from validated-response evidence creation. Until review and
deletion complete, the next case is blocked. Reaching 24 hours does not silently
delete evidence, authorize a retry, or permit replacement generation; it
requires an explicit recovery or terminal disposition consistent with the
existing evaluation lifecycle. Before live execution is authorized, the
implementation milestone must enforce this deadline and define the exact
recovery/terminal transition.

## Multi-session execution

The aggregate evaluation identity is durable and may span operator sessions;
phase grants are short-lived and operation-specific. Completed cases remain
terminal, consumed attempts remain consumed, and untouched cases remain
available. Expired grants close or recover without erasing outcomes or forcing
the aggregate package to be recreated. A later session authenticates and
replays durable evaluation history, reconciles aggregate counters, selects the
next unfinished case, and prepares only that case's next eligible phase.

Use a seven-calendar-day aggregate execution window, set only by a later
reviewed implementation/activation step. No live timestamp is chosen here. The
window bounds how long new phase grants may be prepared; it is not provider
authority. On expiry, the aggregate moves to `expired_paused`: completed
outcomes, consumed attempts, budget accounting, and untouched cases remain
durable, but no phase grant may be prepared. A human-reviewed extension may
resume the same aggregate identity only after frozen identities, counters,
closed-state restoration, and absence of active grants are revalidated.

An extension is permitted either before expiry while `in_progress` or after
expiry while `expired_paused`. It is recorded as
`aggregate_evaluation_extended`, binds the unchanged frozen evaluation-set and
aggregate identities, preserves every completed outcome, consumed authority,
counter, budget amount, and terminal state, and creates a new seven-calendar-day
expiration from the reviewed extension event. It records a human reviewer and
bounded reason. It grants no provider authority and never reactivates an expired
or consumed phase grant. There is no fixed extension-count maximum at this
stage: every extension is a separate reviewed decision in durable aggregate
history. Final completion closes the aggregate permanently; explicit
abandonment also closes it without erasing history.

Each phase grant has a 15-minute activation-to-dispatch window. If it expires
before dispatch, it closes unused and consumes no attempt; a fresh grant for
the same unused phase requires a new review. Dispatch consumes the grant, so
response handling and closure may finish after the window without reviving
authority. Phase grants never remain active overnight.

An unfinished reviewed-response lifecycle blocks movement to the next case
until review and deletion complete. Stopping between fully closed cases is the
preferred pause boundary.

## Failure continuation and stop policy

A provider/transport failure, automated structural/semantic/prose rejection,
human `reject`, human `request_changes`, or hard-gate safety result consumes the
case's sole generation attempt and makes that case terminal. It does not cancel
untouched cases: the evaluation continues to collect all ten fixed outcomes.
A provider failure remains distinct from content unsafety, and final scoring
uses the already frozen rules.

If the terminal outcome fails any frozen hard gate, the aggregate records an
explicit `hard_gate_continuation_acknowledged` event before `next` may prepare
another case. It binds the operator identity, failed case/outcome, and
acknowledgement time. It records human awareness of the terminal hard-gate
result; it does not change that case, scoring, authority, budget, or non-reuse
state and cannot authorize a retry. Provider failure, human rejection, or
`request_changes` needs this acknowledgement only when its recorded outcome
also constitutes a hard-gate failure.

Stop evaluation-wide and fail closed only when continued execution cannot be
trusted: identity or frozen-package mismatch, journal/projection or aggregate
counter inconsistency, budget exhaustion/breach, ambiguous attempt dispatch,
multiple active grants, inability to restore closed authority state, or
unresolved evidence/recovery integrity. Recovery may restore the same bounded
lifecycle; it may never rerun or replace provider work.

Provider dispatch is the exact consumption boundary: the future transport
adapter records a durable `provider_dispatch_started` event immediately before
invoking the pinned SDK method, after all local checks and request serialization
are complete. If that event cannot be durably recorded, transport must not be
called. Once it is recorded, the case provider attempt is considered consumed
unless the system can prove dispatch never occurred under the pre-dispatch
rule. A dispatched attempt remains consumed regardless of response, timeout,
provider error, transport error, or interrupted response handling. An
activation or local preparation failure before `provider_dispatch_started`
consumes no provider attempt.

Activation interrupted before provider dispatch consumes no provider attempt;
the inactive/expired candidate is closed and may be replaced only by a newly
reviewed grant for the same still-unused phase. Once dispatch begins—or whether
dispatch occurred is indeterminate—the phase is consumed. Timeouts and shell
exit after dispatch are terminal provider outcomes with no retry.

## Deterministic cases

During aggregate initialization, explicitly append and close the deterministic
outcomes for `eval-v4-07` (`known(false)`) and `eval-v4-08`
(`not_applicable`) through the frozen deterministic binding path. Initialization
must prove zero provider-request construction, zero phase grants, zero
preflights, zero generations, and absent provider identities. Recording them as
named initialization transitions makes their contribution to the ten outcomes
auditable without ceremonial operator authorities.

## Aggregate budget enforcement

Before any phase activation, atomically reserve that exact case/phase against
both the case envelope and aggregate counters. Activation fails unless:

- the case phase is unused and has no competing active grant;
- projected totals remain at most eight preflights, eight generations, and
  `$0.24`;
- retries remain zero and the case ceiling remains at most `$0.03`; and
- the two deterministic cases still have zero provider activity.

Dispatch converts the reservation to consumed even on provider failure or an
indeterminate result. A proven no-dispatch interruption releases only the
reservation, never a consumed attempt. Closure reconciles phase audit, case
counters, and aggregate counters. Finalization derives totals from case history
and compares them with the aggregate ledger; it does not trust a summary alone.
The `$0.24` value is a ceiling, not spending authorization.

## Durable history and recovery

Reuse the existing experimental offline ledger/journal conventions minimally
for this bounded live evaluation: one aggregate identity in the journal
genesis, one durable record per case, case-specific preflight and generation
artifacts, explicit review/deletion/closure, and aggregate report provenance.
The hash-chained journal remains authoritative lifecycle history and the ledger
remains a replay-validated projection. Live phase-grant, activation,
consumption, and closure artifacts must be added by a separate implementation
milestone; the current offline runner is not modified or treated as authority.

The experimental JSON storage is acceptable for this controlled evaluation
under ADR-0005's retained-head threat model. It is not selected as product
persistence. The future GA security-hardening trigger in the Parking Lot still
requires a separate production persistence/security decision.
This design adds no GA-grade hostile-environment protection, and the aggregate
identity is not authentication. Public/GA identity, persistence, transactional,
and security architecture remains a separate milestone.

Recovery rules are:

- interrupted activation with proven no dispatch closes the candidate without
  consuming the operation;
- timeout, shell exit, or indeterminate state after dispatch consumes the phase
  and records a provider failure;
- postponed review retains evidence for at most 24 hours, blocks the next case,
  and then requires the explicit recovery/terminal disposition defined before
  live authorization;
- interrupted evidence deletion resumes the same transaction and deletion
  identity;
- session exit between cases leaves closed cases terminal and untouched cases
  available; and
- an expired phase grant is closed/recovered independently of the longer-lived
  aggregate identity.

Every state-changing recovery is integrity-checked, preserves counters, and
never silently invokes transport.

## Authority and credential lifecycle

For each eligible case:

`aggregate approved` → `case available` → `preflight grant reviewed/active` →
`human same-shell preflight` → `preflight consumed/closed` → `evidence reviewed`
→ `generation eligible` → `generation grant reviewed/active` →
`human same-shell generation` → `generation consumed/closed` →
`automated result` → `human review when applicable` → `evidence deleted` →
`case terminal`.

The human operator directly runs the fixed credential-bearing same-shell
launcher; Codex never launches it. Prompt once per provider operation—once for
preflight and once for generation—so credentials exist only inside the
short-lived phase process tree. A whole-session credential would reduce prompts
but broaden exposure across cases and blur independent authority boundaries.

At the current development/friends-and-family stage, operator and reviewer
fields use simple human-readable names, for example `Joe Shepherd`. They are
bounded audit labels, not authenticated accounts, certificates, signatures, or
production identity. Stronger identity semantics require the separate future
public/GA security design.

## Finalization and operator workflow

Finalization requires all ten cases terminal, every applicable human review
complete, all validated response evidence deleted, every phase grant
closed/consumed/expired, reconciled case and aggregate counters, no active
provider authority, and restoration of permanent closed execution state. The
report binds all ten outcomes and their closures to aggregate history and uses
only `graduate`, `remain_experimental`, or `fail` under the frozen scoring rules.

The smallest practical operator workflow is:

1. `start/resume` validates the aggregate and records deterministic cases;
2. `next` displays the next unfinished case and its exact eligible phase;
3. `prepare/review preflight` creates the short-lived preflight grant;
4. the human runs preflight in the fixed same-shell launcher;
5. `review preflight` binds its exact evidence and closes that phase;
6. `prepare/review generation` creates the short-lived generation grant;
7. the human runs generation in the fixed same-shell launcher;
8. `review result` records automated and human review;
9. `delete/close` deletes validated evidence and closes the case;
10. acknowledge a hard-gate result when applicable, then repeat `next`; and
11. `finalize/verify` reconciles and closes the aggregate evaluation.

For example, session 1 initializes the aggregate, records cases 07/08, completes
cases 01–03, verifies no grant remains active, and stops. Session 2 runs
`start/resume`, proves 01–03 are terminal and non-reusable, retains 04–06 and
09–10 without recreating them, and begins case 04 with a new short-lived
preflight grant. Aggregate progress survives; phase grants do not.

Recovery is exposed through the same high-level workflow, not hidden provider
retry commands. Implementation may group read-only preview and verification,
but authoritative activation, review, deletion, and closure transitions remain
explicit.

## Architecture A versus B

| Concern | Architecture A: aggregate plus case envelopes | Architecture B: eight independent packages |
|---|---|---|
| Operator burden | One evaluation context and guided next-case workflow | Eight package reviews and manual aggregation |
| Implementation | Aggregate counter/recovery logic plus isolated cases | Simpler packages, more orchestration duplication |
| Cross-case risk | Must prove strict identity isolation | Naturally isolated, but manual mix-up risk remains |
| Recovery/resume | One history identifies the exact resume point | Eight histories require external reconciliation |
| Auditability | One provenance chain with ten closures | Strong per-case records, separate aggregate proof needed |
| Authority lifetime | Long-lived non-executable identity; short phase grants | Eight package lifetimes to manage independently |
| Budget control | Atomic case and aggregate enforcement | Per-case limits are simple; aggregate limit is retrospective unless added separately |

Architecture A is preferable because the evaluation is one fixed bounded
product-readiness decision. Its added aggregate accounting is justified by
lower operator burden, direct resumability, and prospective budget enforcement,
provided implementation proves cross-case isolation and single-use phase
consumption. Architecture A must be abandoned in favor of Architecture B if
implementation cannot cleanly prove any one of: exact per-case identity,
single-use provider consumption, cross-case isolation, prospective aggregate
budget enforcement, durable pause/resume and recovery, or independent case
closure. Failure of any one guarantee is a fallback trigger; no guarantee may
be weakened to preserve Architecture A.

## Acceptance and next implementation boundary

Architecture A satisfies the design criteria for exact request identity,
independent one-use consumption, zero retries, deterministic suppression,
prospective aggregate budgeting, independent closure, cross-case isolation,
multi-session resume, recovery without replay, and ten-outcome report
provenance.

The minimum separately reviewed implementation components are:

- immutable aggregate-package and case-envelope schemas;
- separate preflight/generation grant, activation, consumption, and closure
  records;
- atomic per-case and aggregate reservation/counter reconciliation;
- same-shell live launchers that Codex cannot invoke;
- live lifecycle journal/artifact validation and recovery extensions;
- operator-facing `next`/prepare/review/close/finalize orchestration; and
- network-disabled rehearsals proving identity isolation, budget enforcement,
  interruption recovery, closure, and non-reuse before any live preparation.

## Fixed design-level event names

- `provider_dispatch_started`: durably marks entry into the pinned provider SDK
  call and consumes the exact case/operation attempt subject only to the proven
  pre-dispatch exception above.
- `hard_gate_continuation_acknowledged`: records human awareness of a terminal
  hard-gate result before untouched cases continue; it changes neither the
  failed outcome nor scoring and grants no retry.
- `aggregate_evaluation_extended`: records a reviewed extension of the
  non-executable aggregate coordination lifetime; it grants no provider
  authority and resets no case, attempt, terminal state, counter, or budget.
