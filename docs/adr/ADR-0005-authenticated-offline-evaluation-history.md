# ADR-0005: Integrity-Check Offline Formal-Evaluation History

## Status

Accepted for the frozen-v4 offline formal-evaluation runner.

## Context

The formal-evaluation runner spans separate CLI processes and must enforce one
attempt per frozen case. A mutable current-state snapshot can detect internal
inconsistency, but it cannot demonstrate that a terminal outcome was not reset
to an earlier state. Response-evidence deletion also spans multiple filesystem
operations and can be interrupted after content removal but before projection
update.

## Decision

Use three distinct sources with explicit responsibilities:

- `transition-journal.json` is the authoritative logical lifecycle history.
  Every transition is sequence-numbered, binds the previous transition and
  previous/new case-state digests, and is SHA-256 chained from a fixed genesis
  derived from the frozen evaluation-set, runner, and execution-budget IDs.
  Replay also derives and checks operation-specific state progression, attempt
  counters, terminal status, and exact required/prohibited artifact bindings;
  hash continuity alone is insufficient.
- Bounded preflight, review, deletion, and closure artifacts are authoritative
  evidence for their individual operations and are semantically revalidated.
- `ledger.json` is a current-state projection only. Every command replays the
  journal and rejects a projection mismatch before acting.

Validated-response deletion uses a persisted `prepared` → `removal_prepared` →
`evidence_removed` → `committed` transaction. `prepared` establishes the
transaction and intended deletion; `removal_prepared` proves the bounded
deletion artifact is durable before response-evidence removal;
`evidence_removed` records that response evidence is absent; and `committed`
binds the completed deletion into the hash-chained lifecycle and checked
projection. Before recovery mutates any durable state, it writes
a bounded basis containing the exact observed projection, transaction, and
  artifact identities and binds that basis with a `recovery_prepared`
transition. Recovery then completes the same deletion identity without
recreating response content or reopening generation and appends a linked
`recovery_completed` transition. Classification is derived from the anchored
before-state and replay-validated after-state. A read-only consistency check does
not mutate history. Committed transactions and terminal closures remain subject
to full semantic validation on ordinary loads.

Deletion transaction files are validated by canonical content, not by a single
required JSON byte layout. The persisted JSON is parsed and normalized through
the runner's canonical serialization before comparison. Insignificant formatting
differences such as whitespace or key order are accepted; semantic field or
lifecycle changes are rejected. This matches the offline integrity threat model.

All state remains ignored `.local` synthetic evaluation state. This decision
does not add live authorization, credentials, provider access, or runtime
integration.

This JSON ledger/journal/artifact design is scoped only to offline formal-
evaluation state. It does not choose or automatically become GoTime's future
production persistence, database, event-store, or transaction architecture.
Any product integration must make that decision separately. It may reuse the
invariants established here—hash-chained transitions, single-use operations,
auditability, and recovery semantics—without reusing this storage implementation.

## Threat Model and Non-Goals

This offline evaluation infrastructure detects accidental corruption, partial
or inconsistent mutation, stale ledger projections, missing/reordered/mismatched
journal transitions, unsupported lifecycle transitions, duplicate or replacement
attempts through the supported CLI, cross-case evidence substitution, interrupted
recovery inconsistencies, and semantically invalid artifacts or transitions—even
when the affected local artifact hashes have been recomputed. The journal is
locally tamper-evident relative to its retained trusted head; replay and bounded
lifecycle artifacts provide the semantic checks.

It does not provide cryptographic authenticity against an attacker with
unrestricted write access to every local evaluation file who can replace the
retained journal head, rewrite the entire journal from a prior point, rewrite
the ledger and every lifecycle/recovery artifact, and consistently recompute all
unkeyed SHA-256 digests. Defending against that attacker requires a separately
trusted or non-rewriteable anchor, such as a keyed MAC/signature, an externally
retained checkpoint, append-only/WORM storage, or separately trusted
transactional persistence. Those mechanisms are outside this runner's scope.

This ADR does not select GoTime's future production database, event store,
persistence model, transaction system, or security architecture. Product
integration requires a separate persistence and security decision.

## Consequences

Positive:

- Canonical snapshot rollback cannot erase consumed attempts or terminal cases.
- Exact preflight history is retained and validated before generation.
- Human-review fields and case closures are checked semantically, not only by
  digest shape.
- Evidence deletion is idempotent and recoverable at every persisted boundary.
- Final reports can bind the terminal journal, projection, closures, and all
  terminal outcomes.

Negative:

- Offline synthetic state has more files and stricter recovery logic.
- Journal replay adds bounded work to every command.
- Corrupt or partially copied state fails closed and requires the documented
  recovery path.
