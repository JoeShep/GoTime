# Architecture A Milestone 6 — Durable Provider-Dispatch Consumption

## Scope

Milestone 6 adds the exact persisted operation `provider_dispatch_started` as
an offline state transition. It is the irreversible boundary immediately
before future entry into the pinned provider SDK. No credential, client,
request, network call, token preflight, or provider response exists here.

The state-layer transaction validates the active aggregate, exact next AI case,
envelope, grant, reservation, frozen request identities, expiry, zero-retry
policy, and acknowledgement state. It then commits authoritative history first
and the replay-derived projection second. A future Milestone 8 launcher may
enter the SDK only after this full transaction returns successfully.

## Irreversible conversion

Before the event, case 01 has one reserved preflight operation slot and `$0.00`
reserved monetary exposure. After the event it has zero reserved preflight
slots, one consumed preflight slot, `$0.00` reserved monetary exposure, and
`$0.00` consumed monetary exposure. Remaining
case and aggregate capacity do not change. The reservation lifecycle records:

- `status=consumed`;
- `provider_dispatch_status=started`;
- `attempt_consumed=true`;
- `consumed_operation_count=1`; and
- the full `$0.00` conservative monetary reservation as consumed exposure.

Release is permanently unavailable after this transition. Response, timeout,
provider error, transport error, interrupted handling, or indeterminate future
dispatch cannot restore the attempt, capacity, or retry authority. A proven
failure before the history event commits leaves the reservation reserved and
the attempt unconsumed.

## Crash and durability semantics

A crash before authoritative history replacement leaves no dispatch event and
fresh replay sees the reserved state. A crash after history replacement but
before projection replacement recovers the consumed state from history exactly
once. The offline method returns only after both history and projection writes
complete; future SDK entry must occur only after that successful return.

## Command decision

Milestone 6 deliberately adds no public command. A standalone human-invoked
record command would create an unsafe delay between the durable event and SDK
entry. Milestone 8 will bind `record_provider_dispatch_started()` and immediate
pinned-SDK entry in one controlled same-shell process. The public inventory
therefore remains ten commands.

## Accounting and isolation

Reserved plus consumed preflight operations remains bounded by the canonical
maximum of eight. Authoritative test states validate 8/0, 7/1, 4/4, and 0/8
reserved/consumed combinations, while a ninth slot remains rejected. All eight
preflights may consume their operation slots while contributing `$0.00`
preflight monetary exposure. Case 01 consumed plus case 02 reserved therefore
derives `$0.00` consumed, `$0.00` reserved, and `$0.24` aggregate monetary
capacity.

The irreversible value is the attempt and operation slot, not positive dollar
spend. Consumed-to-reserved, consumed-to-released, deletion, release-after-
dispatch, and retry-restoration attacks remain rejected with zero monetary
exposure.

Provider execution, generation authority, dispatch authority, generic spending
authority, and retry authority remain false. The build-vs-adopt disposition is
still `defer_adoption`; custom Architecture A continues through Milestone 9,
with mandatory reassessment after committed Milestone 9 and before Milestone
10.

## Offline validation

After the approved budget-policy reconciliation, the current combined results
are 185 focused Milestones 1–6 tests and 1,201 full offline tests with 18
skipped. The focused grant/budget/dispatch/state subset passes 143 tests. The
backend (148), frontend (17), TypeScript, temporary-directory production build,
Python compilation, JSON/TOML parsing, frozen-v4 verification, and exact
ten-command rehearsal also pass. No provider operation occurred.

The counts below are retained as the historical Milestone 6 commit result:

- focused Milestone 6: 29 passed;
- focused Milestones 1–6: 184 passed;
- full offline experiments: 1,200 passed, 18 skipped;
- backend: 148 passed;
- frontend: 17 passed;
- TypeScript and temporary-directory production build: passed;
- Python compilation and JSON/TOML parsing: passed;
- frozen-v4 evaluation-set verification: passed with zero provider operations;
  and
- exact public-command rehearsal: passed with no aggregate state left in the
  repository.
