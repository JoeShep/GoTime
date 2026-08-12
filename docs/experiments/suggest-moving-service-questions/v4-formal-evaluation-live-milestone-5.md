# Architecture A Milestone 5 — Prospective Provider-Budget Accounting

## Scope and identity

Milestone 5 adds offline, durable prospective accounting before any provider
dispatch. Its reservation schema is
`suggest-moving-service-questions-v4-formal-evaluation-provider-budget-reservation-v1`,
version 1. The exact history operations are `provider_budget_reserved` and
`provider_budget_released`; neither represents dispatch or consumption.

For the fixed synthetic time `2026-08-10T12:00:00Z`, the first case-01
reservation digest is
`8edf28f8378a97796b197bdcb0d0b5bc64b59fbcb2260d5627e313c87c4daec0`.
Its immutable identity binds the aggregate/package, exact case and envelope,
prepared grant digest, preflight phase, one operation, zero retries, exact
reservation time, `$0.00` preflight monetary amount, `$0.03` case ceiling, and `$0.24`
aggregate ceiling. Credentials and mutable lifecycle state are excluded.

The historical digest
`cbc71820cc3d801a09d90dedb0b279882bccae85da8dd482651a64f6eb1a462a`
bound a `$0.03` preflight reservation under the then-approved interpretation.
The corrected reservation remains mandatory because it reserves one operation
slot and exact grant authorization even though its monetary amount is zero.

## Exact arithmetic and prospective rules

All monetary arithmetic uses `Decimal` and canonical two-decimal strings.
Binary floats are not accepted. Policy values come from the existing frozen
model constants; the budget layer introduces no independent ceiling literals.

Before mutation, the engine enforces:

`case consumed + case reserved + requested <= $0.03`

`aggregate consumed + aggregate reserved + requested <= $0.24`

`preflights consumed + preflights reserved + 1 <= 8`

Generation reserved/consumed fields remain zero and retries remain zero.
Aggregate totals are independently derived from exact case reservations and
reconciled against the stored inspection projection and aggregate counters.
Callers cannot provide a case, amount, count, phase, ceiling, grant, envelope,
provider, or model override.

The first reservation targets the derived next case `eval-v4-01` and reuses
its exact prepared grant and immutable envelope. It prospectively reserves one
preflight operation slot and `$0.00` monetary exposure, leaving `$0.03` case
capacity and `$0.24` aggregate capacity. Deterministic cases and non-next AI
cases are ineligible. Dollar checks and operation-count checks remain separate;
a zero-dollar reservation cannot bypass the eight-preflight maximum.

Grant and reservation collections retain at most one exact record for each of
the eight AI cases. A later next-case event adds its grant and reservation
without deleting, replacing, or rebinding any earlier case record. Released
records remain authoritative history while contributing zero active exposure;
reserved records across distinct cases contribute independently to their case
ceilings and collectively to the aggregate ceiling and operation limit.

## Reservation, authorization, and idempotency

The durable sequence is:

`prepared grant → exact validation → prospective check → durable reservation → scoped offline activation`

The operational Milestone 4 budget gate now accepts only a grant whose exact
reservation is already present in authoritative aggregate history. Successful
reservation changes the grant to scoped `active` state with:

- `preflight_budget_authorized=true`;
- `preflight_grant_active=true`;
- `preflight_spending_authorized=true`;
- `provider_authority=false`;
- generic `spending_authorized=false`;
- `generation_authorized=false`;
- `dispatch_authorized=false`;
- `retry_authorized=false`; and
- `provider_execution_authorized=false`.

These fields authorize only the recorded offline preflight budget/grant scope.
They do not create provider execution capability. An exact rerun returns the
same reservation without another event, count, or amount. A conflicting,
released, parallel, cross-case, or replacement reservation fails closed.

## Release and expiration

Milestone 5 implements one exact pre-dispatch release:

`reserved → released`

Release requires all of the following durable facts:

- the grant is at or beyond its inclusive 15-minute expiry;
- `provider_dispatch_status=not_started`;
- the reservation still has zero consumed exposure; and
- the proof/reason is `expired_unused_dispatch_not_started`.

The `$0.00` monetary amount and one reserved operation slot then return to
available capacity; consumed monetary exposure remains zero. Release remains
meaningful because it restores the operation slot. Release before expiry,
release with ambiguous dispatch state, over-release, negative accounting, or
replacement after release fails closed.

If the seven-day aggregate expires, the reservation survives unchanged and no
new reservation or dispatch becomes possible. Proven-unused expiry release may
still close the pre-dispatch exposure; there is no automatic reset or Milestone
12 extension.

## History, recovery, and Milestone 6 hook

Both budget operations use the Milestone 1 history-first atomic protocol.
Crashes after history replacement and before projection replacement recover the
exact reservation/release from authoritative history, without duplicate events
or double-counting.

Because runtime AI case closure belongs to later milestones, multi-case
progression tests use a test-only `AggregateStore` subclass with an explicitly
synthetic case-advance history operation. Production replay does not recognize
that operation. The fixture proves that case 01's released record survives a
case 02 reservation, that all eight distinct case reservations coexist with
eight operation slots and `$0.00` preflight monetary exposure, and that a fully rehashed ninth-count attack
fails. It does not implement dispatch, consumption, or a public advancement
path.

Correctly rehashed attacks against amount, case, grant, envelope, phase,
operation count, ceilings, derived totals, negative values, over-release,
deterministic/future cases, duplicates, or authorization without a reservation
fail semantic replay.

Milestone 6 exclusively owns `provider_dispatch_started`, conversion of
reserved exposure/operation count to consumed exposure, and indeterminate
dispatch handling. Milestone 5 defines `provider_dispatch_status=not_started`
and leaves consumed exposure at zero; it does not implement the future event.

## Provider isolation and public commands

Provider request-constructor, client-constructor, and network call counts are
all zero. No credential, token preflight, generation, provider call, retry,
dispatch event, or generation grant exists.

The ten offline commands are:

1. `verify-foundation`;
2. `initialize`;
3. `inspect`;
4. `verify`;
5. `resolve-deterministic-cases`;
6. `bind-ai-case-envelopes`;
7. `prepare-preflight-grant`;
8. `authorize-preflight-budget`;
9. `release-preflight-budget`; and
10. `close`.

The two budget commands accept no case or policy inputs. The build-vs-adopt
disposition remains `defer_adoption`: custom Architecture A continues through
Milestone 9, with mandatory Temporal/Inngest/LangGraph reassessment after
committed Milestone 9 and before Milestone 10.

## Offline validation

- focused Milestones 1–5: 155 passed;
- full offline experiments: 1,171 passed, 18 skipped;
- backend: 148 passed;
- frontend: 17 passed;
- frontend production build: passed using a temporary output directory because
  the pre-existing repository `dist` directory is not writable by this user;
- exact ten-command rehearsal: passed and cleaned its temporary state;
- Python syntax compilation and JSON/TOML parsing: passed; and
- aggregate/envelope/grant identities, frozen formal set, permanent closed
  manifest, and historical regressions: passed.
