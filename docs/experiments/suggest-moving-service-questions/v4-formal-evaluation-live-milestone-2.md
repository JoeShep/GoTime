# Architecture A Milestone 2 — Deterministic Cases 07 and 08

## Scope and frozen outcomes

Milestone 2 adds one provider-incapable aggregate operation,
`deterministic_case_completed`, for exactly `eval-v4-07` and `eval-v4-08`.
It preserves aggregate identity
`suggest-moving-service-questions-v4-formal-evaluation-live-v1`, version 1,
and package digest
`1f6b1b979fd1a244489e0782bf4d37854bb1f800cca8dc4f5faeb06cff83699d`.

The implementation reuses the frozen formal-evaluation `bind_case` eligibility
boundary. It does not reproduce eligibility rules in the live state layer.
The exact terminal results are:

- `eval-v4-07`: empty, `known(false)`, provider ineligible;
- `eval-v4-08`: empty, `not_applicable`, provider ineligible.

Neither outcome is fallback, provider failure, generated text, or a provider
attempt. No user-facing prose is invented.

## Operation and state transition

The fixed internal order is `eval-v4-07`, then `eval-v4-08`. While the
aggregate is `in_progress`, each event changes only its intended case from
`untouched` with deterministic initialization pending to `terminal` with the
exact frozen deterministic outcome. Aggregate status remains `in_progress` and
the next AI case is replay-derived. Callers cannot provide a case ID.

Replay requires the exact case ID, frozen case-input identity, eligibility,
result, reason state, terminal marker, provider-request nonconstruction,
no-attempt marker, and zero spend. It rejects AI targets, swapped semantics,
identity changes, another-case mutation, acknowledgement/lifetime/budget or
counter mutation, duplicate persisted completion, and terminal reopening even
when the history and projection are correctly rehashed.

An exact repeated public invocation is idempotent and appends no event. A
conflicting second result fails closed. `eval-v4-08` cannot commit before
`eval-v4-07`.

## Provider non-entry and accounting

Tests replace the frozen provider-request constructor boundary with a function
that raises. Both deterministic cases finish eligibility binding with zero
constructor calls. The positive `eval-v4-01` control reaches that boundary
exactly once and stops there, before credentials, client construction,
networking, authorization, or dispatch.

All provider fields remain exactly as Milestone 1 initialized them: zero
reserved/consumed token preflights, generations, retries, and provider spend;
`spending_authorized=false`; and `provider_authority=false`. Deterministic
completion does not consume either eight-attempt provider limit.

## Durability, interruption, and expiration

The Milestone 1 authoritative history and replay-derived projection remain the
only persistence model. If 07 commits and a process stops, a fresh process sees
07 terminal and 08 pending; rerun skips 07 without a duplicate and commits only
08. If a crash follows history replacement but precedes projection replacement,
ordinary locked load rebuilds the stale projection without rewriting history.

Deterministic progression is unavailable outside `in_progress`. At the
inclusive expiration boundary, locked load first records `expired_paused`.
Thus expiration between cases preserves 07 terminal, leaves 08 pending, yields
no actionable AI case, and waits for Milestone 12 reviewed reactivation.

After both deterministic cases finish, all eight AI cases remain untouched and
the derived next AI case is `eval-v4-01`.

## Public commands and deferred work

The public inventory is six offline commands:

- `verify-foundation`
- `initialize`
- `inspect`
- `verify`
- `resolve-deterministic-cases`
- `close`

`resolve-deterministic-cases` validates the aggregate and resolves only the two
fixed deterministic cases. There is no arbitrary-case option or AI execution
command.

Milestones 4 and 7 still own provider grants, Milestone 5 owns prospective
budget accounting, Milestone 11 owns hard-gate acknowledgement, and Milestone
12 owns reviewed extension/reactivation. None is implemented here.

The integrity model remains the friends-and-family retained-journal-head model,
not hostile-filesystem cryptographic authenticity. Generated rehearsal state is
local, cleaned after use, and never committed.
