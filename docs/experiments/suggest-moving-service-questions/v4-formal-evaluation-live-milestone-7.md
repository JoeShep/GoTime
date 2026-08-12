# Architecture A Milestone 7 — generation grants

## Status

Implemented offline for human diff review. No provider execution, credential
access, SDK entry, network authority, generation dispatch, or Milestone 8/9
behavior is present.

## Grant and evidence contract

The generation grant schema is
`suggest-moving-service-questions-v4-formal-evaluation-generation-grant-v1`,
version 1. It binds one exact AI case and envelope, the frozen request,
canonical attempt, provider fingerprint, provider/model/SDK configuration,
frozen-v4 manifest, approved preflight evidence and review identities,
generation phase, one operation slot, zero retries, and a 15-minute lifetime.

At fixed synthetic time `2026-08-11T12:00:00Z`, case `eval-v4-01` has:

- reviewed-evidence binding `2262c4c319cc5cc87810c73b752fb84c07683edc1360603468c367ec5391d715`;
- generation grant `b8eeaa9ed4fa16037cb2fa6e0ce2588cebe75ec3152e6676e9dc249b3f3c95f8`;
- generation reservation `80cea3386b18852029fa814d2022e7642b9cd4e978abf8695d04d148fadfae49`.

The grant is usable only for `activated_at <= now < expires_at`; at exactly
`expires_at` it is unusable. Expiry cannot create a replacement or retry.
Generation reservation release is intentionally fail-closed in Milestone 7:
the approved policy does not yet say that releasing unused budget permits a
replacement attempt, and no public generation lifecycle is reachable. A later
review may add proven-non-dispatch release without creating retry authority.

## Evidence dependency and production reachability

Generation requires an exact consumed preflight plus retained, validated,
approved preflight evidence and review bound to the same case/request. Current
Architecture A production state has no operation that records that result and
review prerequisite. Milestone 9 owns the result lifecycle.

Production generation preparation is therefore intentionally fail-closed.
Tests use a subclass-only synthetic evidence operation. Production replay does
not recognize it, the CLI cannot invoke it, and no configuration switch enables
it. This proves Milestone 7 structure without weakening the real evidence gate.

## Exact accounting

The existing reservation schema remains
`suggest-moving-service-questions-v4-formal-evaluation-provider-budget-reservation-v1`,
version 1. Generation uses `phase = generation`, exact Decimal monetary
exposure, and one independent generation operation slot.

For case 01:

`(2,852 × $0.40 / 1,000,000) + (500 × $1.60 / 1,000,000) = $0.0019408`.

The `500` maximum-output-token bound is read from the canonical frozen-v4
request configuration embedded in the exact AI envelope
(`request_configuration.model_parameters.maximum_output_tokens`). Milestone 7
does not define an independent output-token policy literal.

After corrected zero-dollar preflight dispatch:

- case remaining monetary capacity is `$0.0280592`;
- aggregate remaining monetary capacity is `$0.2380592`;
- preflight counters are one consumed and zero reserved;
- generation counters are one reserved and zero consumed.

Accounting derives across all retained preflight and generation records. The
authoritative invariant is
`generations_reserved + generations_consumed <= MAX_GENERATIONS`; the canonical
maximum is 8. Zero retries is independent. Generation never mutates preflight
history or counters.

Replay-valid test-only history covers 8/0, 7/1, 4/4, and 0/8
reserved/consumed generation-slot combinations. A subclass-only synthetic
consumption operation represents retained future terminal records; production
event grammar rejects it and exposes no transition that consumes generation.
The ninth-slot proof appends a fully rehashed malicious event and reaches the
explicit canonical `MAX_GENERATIONS` invariant.

Persisted, rehashed semantic attacks cover deterministic/non-next targeting,
missing/foreign/altered/ineligible evidence, authority without reservation,
premature dispatch/provider/retry authority, prior-record deletion or
replacement, and attempted mutation of irreversible preflight history.
Production preparation without reviewed evidence is also verified to leave
history, grants, reservations, counters, and authority unchanged across a
fresh-process load.

Relative to the retained authoritative journal head, transition-level attacks
remove or replace complete, internally reconciled generation
evidence/grant/reservation sets while retaining later-case history. Replay
rejects them through explicit append-only identity invariants. Separate
reconciled transition attacks replace the consumed preflight grant and its
matching reservation, or replace only the consumed reservation while retaining
its exact grant; both are rejected independently of the consumed-lifecycle
restoration proof. Exact grant and reservation reruns remain event-free, while
test-only candidate overrides prove conflicting reruns fail before history,
accounting, or authority can change.

This guarantee intentionally retains the ADR-0005 threat model. Milestone 7
does not claim to detect an attacker who replaces the entire earlier journal,
every dependent suffix event, the retained head and projection, and every
unkeyed SHA-256 value with one internally consistent history. Stronger
authenticated history would require a separately trusted anchor such as a
signature, keyed MAC, external checkpoint, WORM store, or separately trusted
transactional persistence. That capability is deferred and is not a missing
Milestone 7 implementation.

## Authority, public surface, and isolation

An active offline grant reports scoped generation budget/grant/spending
authorization while `dispatch_authorized=false`,
`provider_execution_authorized=false`, and `retry_authorized=false`.

`provider_dispatch_started` remains the sole irreversible architectural
dispatch boundary. Milestone 7 does not dispatch generation or add a competing
event. Milestone 8 must couple the durable boundary to immediate SDK entry in
one controlled process.

No generation command is added because production cannot satisfy the evidence
prerequisite. The inventory remains 10 commands with no free case, evidence,
amount, phase, provider, model, SDK, or lifetime input. Static and
network-disabled tests establish zero provider constructors, clients, network
calls, credential reads, and SDK entry.

Build-vs-adopt remains `defer_adoption`; custom Architecture A continues
through Milestone 9. Mandatory Temporal/Inngest/LangGraph reassessment remains
after committed Milestone 9 and before Milestone 10.
