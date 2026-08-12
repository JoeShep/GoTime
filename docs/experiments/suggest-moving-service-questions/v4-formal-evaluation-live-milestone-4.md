# Architecture A Milestone 4 — Offline Preflight Grant Candidate

## Scope and identity

Milestone 4 adds schema
`suggest-moving-service-questions-v4-formal-evaluation-preflight-grant-v1`,
version 1, and the single persisted operation `preflight_grant_prepared`.
Preparation derives the current next AI case; callers cannot override case,
envelope, provider, model, request identity, ceiling, or expiry.

The immutable grant identity binds the aggregate/package, exact case and AI
envelope, case input, deterministic request, canonical attempt, provider
fingerprint, frozen-v4 manifest, provider/model/SDK and request configuration,
phase `preflight`, one attempt, zero retries, the `$0.00` preflight monetary
exposure, the distinct `$0.03` total case ceiling, single-use policy, and exact
activation/expiration window. Credentials and mutable lifecycle fields are
excluded.

`conservative_operation_ceiling_usd` derives from the canonical
`PREFLIGHT_CONSERVATIVE_PROVIDER_EXPOSURE_USD`. That source records the frozen
pricing model's lack of a separate token-counting or request/platform fee.
`per_case_provider_ceiling_usd` separately derives from
`PER_CASE_PROVIDER_CEILING_USD`. The fields intentionally differ: the former
is operation-specific monetary exposure; the latter is total case capacity.

The corrected fixed-time case-01 grant digest is
`757155c6427132e8ca3a5bdd37a0c3a93adfb0fb386684f403b1940fe0ca0913`.
The historical Milestone 4 digest
`4fd481a5a477a70982bd2ae7df0b5fa6450ad1c62248e4e48cf50e7c7bd6aba9`
bound `$0.03` as both values under the then-approved interpretation. Milestone
7's consistency gate exposed that interpretation conflict; history is not
rewritten.

## Lifecycle and lifetime

The modeled lifecycle vocabulary is `prepared`, `active`, `consumed`,
`expired`, and `closed`. The durable Milestone 4 lifecycle is `prepared` only;
later states require Milestones 5 and 6. It records an unused
attempt and budget authorization `unavailable_milestone_5`; provider, spending,
generation, and dispatch authority are false. The window is exactly 15 minutes:

`activated_at <= usable_time < expires_at`

At `now >= expires_at`, the candidate is expired and cannot activate. It is
also unusable whenever the seven-day aggregate is not active. No replacement,
extension, rollover, dispatch, consumption, or closure policy is introduced.

## Fail-closed budget port

Activation validates the exact candidate, aggregate, next-case position, and
both lifetimes before invoking the budget port. The production default always
denies because prospective accounting belongs to Milestone 5. Denial persists
no event or active authority and changes no counter.

Tests inject a local approving callable only to exercise the downstream
structural transition. Its result is ephemeral, labelled
`active_synthetic_only`, remains non-dispatchable with provider and spending
authority false, and is unreachable from the CLI. Runtime code contains no
approving implementation.

## Persistence, recovery, and safety

`preflight_grant_prepared` atomically binds one candidate to the derived next
case. History is committed first; fresh-process recovery rebuilds a stale
projection without rewriting history or duplicating the grant. Exact rerun
before expiry is event-free. Conflicting or expired replacement fails closed.

Correctly rehashed attacks against case, envelope, request, canonical attempt,
fingerprint, provider/model/SDK, manifest, phase, duration, ceiling, or
aggregate identity fail semantic replay. Deterministic cases cannot receive
grants; a fully rehashed persisted event targeting case 07 is rejected by the
exact next-enveloped-AI-case rule.

No path constructs a provider request/client, reads credentials, performs a
preflight/generation/network call, reserves budget, or introduces
`provider_dispatch_started`. Aggregate counters remain zero. The ADR-0005
friends-and-family retained-history threat model is unchanged.

Milestone 5 owns accounting; Milestone 6 dispatch consumption; Milestone 7
generation grants; Milestone 8 the same-shell provider boundary; Milestones 11
and 12 acknowledgement and reviewed extension.

## Public commands

The eight offline commands are `verify-foundation`, `initialize`, `inspect`,
`verify`, `resolve-deterministic-cases`, `bind-ai-case-envelopes`,
`prepare-preflight-grant`, and `close`. The new command accepts no identity
override and cannot activate the candidate.
