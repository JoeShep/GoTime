# Architecture A Milestone 1 — Aggregate Coordination State

## Scope and identity

Milestone 1 implements only durable, non-executable coordination for the future
frozen-v4 formal evaluation. The aggregate is
`suggest-moving-service-questions-v4-formal-evaluation-live-v1`, version 1.
Its reproducible package digest binds the frozen evaluation-set ID and manifest,
frozen-v4 manifest, runner ID/version, execution-budget identity, all ten case
input identities, all eight provider request identity triples, both
deterministic-empty identities, the fixed AI order, seven-day lifetime, fixed
budget ceilings, and zero-retry rule. Operator timestamps and audit labels are
state, not immutable package identity.

The durable default path is:

`.local/evaluations/suggest-moving-service-questions/suggest-moving-service-questions-v4-formal-evaluation-live-v1/`

Generated state is local and must not be committed.

## State and transition model

The approved aggregate statuses are `prepared`, `approved`, `in_progress`,
`ready_to_finalize`, `expired_paused`, `abandoned`, and `closed`. Legal edges
are:

- `prepared` to `approved` or `abandoned`;
- `approved` to `in_progress` or `abandoned`;
- `in_progress` to `ready_to_finalize`, `expired_paused`, or `abandoned`;
- `expired_paused` to `in_progress` only through the deferred reviewed-extension
  hook, or to `abandoned`;
- `ready_to_finalize` or `abandoned` to `closed`.

There is no direct state replacement. Completion readiness will be derived from
all ten terminal outcomes in later milestones. Milestone 1 exposes no case
execution. Its internal synthetic seam rehearses only pure next-case derivation
and cannot persist provider authority, attempts, spend, or outcomes.

The retained Milestone 1 event grammar is exact:

- `aggregate_initialized`: no predecessor to exact `prepared` state;
- `aggregate_approved`: `prepared` to `approved`;
- `aggregate_started`: `approved` to `in_progress`;
- `aggregate_expired`: `prepared`, `approved`, or `in_progress` to
  `expired_paused` at or after expiry;
- `aggregate_ready_to_finalize`: `in_progress` to `ready_to_finalize`, accepted
  only when all ten cases are already terminal and no acknowledgement blocks;
- `aggregate_abandoned`: a nonclosed coordination state to `abandoned`; and
- `aggregate_closed`: `ready_to_finalize` or `abandoned` to `closed`.

Only status, derived next-case position, journal count, and journal head may
change in aggregate lifecycle events. Case records, acknowledgement fields,
counters, expiration, budget, labels, and immutable identity must remain
canonical-content identical. No Milestone 2, 5, 11, or 12 event is accepted.

Per-case coordination is limited to `untouched`, `in_progress`,
`awaiting_acknowledgement`, and `terminal`. Cases 07 and 08 are explicitly
marked as pending deterministic initialization; Milestone 2 owns their binding
and terminal outcomes.

## Membership and next case

All ten cases are immutable members in numeric order. AI execution order is
`eval-v4-01`, `02`, `03`, `04`, `05`, `06`, `09`, `10`. The caller cannot
select the next case. While the aggregate is `in_progress`, no case is active,
and no acknowledgement block exists, the next case is the first nonterminal AI
case in that order. Any active case, acknowledgement requirement, expiry, or
non-active aggregate status yields no next case.

The acknowledgement record starts with `acknowledgement_required=false`,
`acknowledged=false`, and null blocking case/outcome fields. Milestone 11 owns
the acknowledgement event; Milestone 1 fails closed while blocked.

## Lifetime, counters, and budget

Initialization records exactly seven calendar days from its UTC initialization
instant. The lifetime coordinates human work only. Observing an active state at
or after the boundary durably transitions it to `expired_paused`; case state,
counters, budget bindings, and expiration survive. There is no rollover.
Reviewed extension is a named fail-closed hook only; Milestone 12 owns extension
policy and history events.

The expiration boundary is inclusive. Before approval/start or resume can
create active coordination, the same locked load materializes expiration from
`prepared`, `approved`, or `in_progress`. At or after `expires_at`, the aggregate
therefore cannot become or return `in_progress` and cannot expose an actionable
next AI case. Replay also rejects a correctly rehashed `aggregate_started`
event timestamped at or after expiry. Only Milestone 12 may later define
reviewed reactivation.

Preflights consumed/reserved, generations consumed/reserved, retries, and
provider spend consumed/reserved start and remain exactly zero. Milestone 1 has
no counter mutation operation. Frozen ceilings are eight token preflights,
eight generations, zero retries, `$0.03` per AI case, and `$0.24` aggregate,
with `spending_authorized=false`. Milestone 5 owns prospective accounting.

## Durability and threat model

`aggregate-history.json` is the locked, append-only coordination history and
`aggregate.json` is its atomic replay-validated projection. Each event binds
the prior and resulting complete state and the previous event digest. Loading
checks the exact package, membership/order, per-case identities, legal status
edges, zero counters, fixed lifetime, cursor derivation, and snapshot equality
with retained history. This detects malformed state, stale identities, local
rollback relative to the retained head, illegal transitions, and inconsistent
manual edits.

History is authoritative and begins with `aggregate_initialized`. Replay
validates exact operation/state pairs, permitted fields, initialization,
monotonic canonical UTC timestamps, expiration timing, terminal behavior,
acknowledgement coherence, zero counters, `history_count == len(events)`, and
projection head equality with the terminal event digest. The stored next-case
field is compared with a fresh derivation.

Each update fsyncs and atomically replaces history before doing the same for the
projection, including containing-directory fsyncs. If interruption leaves the
projection missing or exactly equal to an earlier replay state, ordinary locked
load uniquely rebuilds only `aggregate.json` from valid newer history. History
is never rewritten during recovery and no recovery lifecycle event is needed
for this derived cache repair. A malformed history, projection ahead of
history, or projection that is not an exact prior replay state fails closed.

Under ADR-0005's friends-and-family model, this is integrity-checked relative
to the retained journal head. A hostile filesystem actor who consistently
rewrites all state and history is out of scope. This is not product persistence,
authentication, authorization, or GA-grade tamper resistance.

## Coordination-only boundary and commands

The live Milestone 1 modules import no OpenAI/provider client, networking
library, credential facility, provider-request type, or existing executable
runner. They cannot construct a client/request, access a key, activate a
manifest, authorize a preflight/generation, or spend. Frozen identity artifacts
are read only for binding and validation.

The complete public command inventory is five commands on
`v4_formal_evaluation_live_cli.py`:

- `verify-foundation`
- `initialize --operator LABEL --reviewer LABEL`
- `inspect [--resume --reviewer LABEL]`
- `verify`
- `close --reviewer LABEL [--abandon]`

Exact duplicate initialization of the same untouched `prepared` aggregate is
idempotent. A conflicting request fails closed and never resets state. Resume
records `prepared` to `approved` to `in_progress`; an already active resume is
idempotent. Expired resume fails until Milestone 12. Normal close requires
future completion readiness; explicit abandonment records `abandoned` then
`closed` without erasing history.

All state-loading commands use the same projection reconciliation. Therefore
`inspect`, `verify`, resume, and `close` can repair only a missing or provably
stale projection under the aggregate lock; none can alter valid history as a
recovery technique.

## Deferred ownership

- Milestone 2: deterministic initialization and terminal outcomes for 07/08.
- Milestone 5: prospective reservation, consumption, reconciliation, and
  aggregate budget enforcement.
- Milestone 11: hard-gate continuation acknowledgement event.
- Milestone 12: reviewed extension event and expired aggregate reactivation.

This milestone begins exact case-identity and durable pause/resume proof and
lays foundations for isolation, aggregate budgeting, and independent closure.
It does not claim the Architecture A guarantees or Milestone 17 proof complete.

The adversarial test matrix independently rehashes all six frozen budget
fields, extra membership, deterministic-case substitution, generation-case
request identity, premature finalization, and unauthorized expiration changes.
These fail on semantic validation rather than stale hashes.
