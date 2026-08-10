# Frozen-v4 Formal Evaluation Runner

## Status and identity

The offline runner identity is
`suggest-moving-service-questions-v4-formal-evaluation-runner-v1`. It evaluates
the immutable
`suggest-moving-service-questions-v4-formal-evaluation-set-v1`; it is not a new
prompt or evaluation-set version.

This milestone enables synthetic rehearsal only. It provides no credential
path, provider client, network access, live authorization, or spending
authority.

## Execution model

The runner produces exactly ten terminal outcomes:

- eight generation-eligible cases, each with one synthetic preflight and one
  synthetic generation maximum;
- two deterministic empty cases (`eval-v4-07` and `eval-v4-08`) with no provider
  request construction, preflight, or generation.

Retries and replacement runs are prohibited. Durable, locked local state at
`.local/evaluations/suggest-moving-service-questions/v4-formal-evaluation-runner-v1`
binds the runner, frozen set, case-input identities, attempt counters, terminal
outcomes, reviews, deletions, and closures across separate command processes.
`transition-journal.json` is the authoritative append-only logical lifecycle
history. Every transition is sequence-numbered and SHA-256 chained from a fixed
genesis binding. Replay derives each transition's before/after attempt counters,
terminal flag, allowed state progression, and exact required/prohibited artifact
map from the operation and validated case states; rehashing a semantically false
transition cannot make it valid. Initialization is represented by the immutable
genesis rather than a mutable initialization transition. Case completion is
bound by the terminal lifecycle transition and its closure. Report finalization
does not mutate case history (avoiding a self-referential report transition) and
instead binds the already-terminal journal digest. Operation artifacts are
authoritative bounded evidence;
`ledger.json` is only a validated current-state projection. Every command
replays the journal and rejects any projection mismatch. Files use mode-`0600`
temporary writes, file locking, `fsync`, and atomic `os.replace`; this is
ignored operational state and is never committed. The
aggregate limits remain eight
preflights, eight generations, zero retries, and a non-authoritative `$0.24`
provider ceiling. The same request object whose three frozen identities are
verified is passed to the network-incapable synthetic transport.

## Integrity threat model

The local history is hash-chained, integrity-checked, and replay-validated. It
is designed to detect accidental corruption, partial/inconsistent changes,
stale projections, broken journal continuity, invalid state transitions,
cross-case substitution, supported-CLI replacement attempts, and interrupted
recovery errors. Semantic validation still rejects malformed transitions and
lifecycle artifacts when their individual local hashes are recomputed.

The retained journal head is the local trust boundary. This runner does not
claim cryptographic authenticity against an attacker who can replace that head
and consistently rewrite every journal transition, ledger projection, lifecycle
artifact, recovery basis, and later SHA-256 digest. That stronger threat model
requires a keyed signature/MAC, externally retained checkpoint, WORM/append-only
storage, or separately trusted persistence, all of which are out of scope.

Case states are `pending`, `deterministic_empty_complete`, `preflight_ready`,
`preflight_complete`, `generation_ready`, `generation_complete`,
`transport_failure`, `automated_rejected`, `awaiting_human_review`,
`human_review_complete`, and `case_complete`. Provider/transport failure is
separate from structural, semantic, and prose rejection.

Each bounded outcome records eligibility, counts, transport classification,
validation results, ordered prose codes, bounded diagnostics, fallback,
expected-empty correctness, human-review measures, exact request identities,
and bounded lifecycle digests. Rejected response prose is never retained.

## Scoring

The runner implements the approved hard, quality, and empty-case gates without
changing the frozen plan. A hard safety or grounding violation produces `fail`.
Passing hard gates with insufficient quality produces `remain_experimental`.
Only passing every hard and quality gate plus both empty cases produces
`graduate`. A transport failure consumes its case attempt and prevents
graduation, yielding `remain_experimental` unless another hard gate fails; it is
not treated as content unsafety.

Every report says: “This is a bounded product-readiness evaluation, not a
statistically representative reliability study.” Synthetic reports are
explicitly marked and cannot be mistaken for live evidence.

Validated nonempty responses require an evidence-bound `approve`, `reject`, or
`request_changes` human review. Review cannot trigger generation. Validated
synthetic evidence remains in the local state directory until an explicit,
case/evidence/review-bound deletion command removes it. The bounded deletion
artifact retains no response content, repeated deletion is idempotent, and the
case cannot become terminal before deletion succeeds. Deletion uses a persisted
`prepared` → `removal_prepared` → `evidence_removed` → `committed` transaction.
`prepared` establishes the transaction and intended deletion;
`removal_prepared` makes the bounded deletion artifact durable before response
evidence is removed; `evidence_removed` records that response evidence is absent;
and `committed` binds completion into the hash-chained history and checked
projection. The recovery command
finishes any interrupted deletion without recreating response content or
changing the deletion identity. Before any repair, it persists an exact
pre-repair basis and appends `recovery_prepared`; completion links that basis
to one semantically validated `recovery_completed` transition with unchanged attempt counters;
already-consistent recovery is a history-preserving no-op. Committed deletion
transactions and closures are revalidated against the complete applicable
preflight, generation-audit, historical evidence, review, deletion, transaction,
and terminal-outcome bindings on every load.

Transaction validation is exact at the canonical-content level. JSON is parsed
and normalized with the runner's canonical serialization; whitespace and key
ordering are not security-significant, while semantic field and lifecycle-state
changes are rejected.

Each state-changing recovery writes its bounded recovery-basis artifact before
mutation and binds it into the hash-chained journal. Replay derives exactly one
classification from that retained before-state and the replay-validated after-state:
projection-only repair, deletion-transaction-only commit, or combined
reconciliation. A prepared recovery survives interruption and resumes the same
event; it cannot be replaced by a conflicting preparation.

## Offline public commands

These eleven commands are the fixed public surface for this milestone. The
explicit eleventh command makes evidence deletion independently visible rather
than hiding it in review or report finalization. Every
command uses the pinned image with `--network none` and a read-only workspace.

1. `scripts/experiments/suggest_moving_service_questions/verify_v4_formal_evaluation_set.sh`
2. `scripts/experiments/suggest_moving_service_questions/preview_v4_formal_evaluation_package.sh`
3. `scripts/experiments/suggest_moving_service_questions/rehearse_v4_formal_evaluation.sh`
4. `scripts/experiments/suggest_moving_service_questions/run_v4_formal_evaluation_empty_case.sh`
5. `scripts/experiments/suggest_moving_service_questions/run_v4_formal_evaluation_preflight_case.sh`
6. `scripts/experiments/suggest_moving_service_questions/run_v4_formal_evaluation_generation_case.sh`
7. `scripts/experiments/suggest_moving_service_questions/record_v4_formal_evaluation_review.sh`
8. `scripts/experiments/suggest_moving_service_questions/delete_v4_formal_evaluation_evidence.sh`
9. `scripts/experiments/suggest_moving_service_questions/finalize_v4_formal_evaluation_report.sh`
10. `scripts/experiments/suggest_moving_service_questions/verify_v4_formal_evaluation_result.sh`
11. `scripts/experiments/suggest_moving_service_questions/close_v4_formal_evaluation_state.sh`

All case operations validate and append the same hash-chained journal, then
update the checked ledger projection. Report
finalization loads the ten existing terminal outcomes and never invokes
preflight, generation, or review helpers. The report binds the ledger version
and digest, terminal journal digest and transition count, every closure digest,
and every terminal outcome digest. Each synthetic preflight is retained as a
bounded case/request-identity artifact and is validated before generation. The
rehearsal covers nominal
`graduate`, hard-gate `fail`, quality-gate
`remain_experimental`, and provider-failure `remain_experimental` runs. Focused
tests additionally keep structural, semantic, and bounded prose rejection
distinct. The public rehearsal launches each operation as a separate CLI
process and reports `cross_process_second_preflight_rejected=true` and
`cross_process_second_generation_rejected=true` after explicit duplicate
attempts fail before synthetic transport.

## Future live architecture recommendation

Prefer architecture A: one reviewed evaluation package with eight exact,
case-specific, single-use sub-authorities. This keeps one frozen set and one
aggregate budget review while preserving individual request identity,
preflight binding, attempt consumption, audit, closure, and non-reuse.

The tradeoff is a more careful aggregate ledger and recovery design than eight
unrelated packages. Before any live work, that design must prove that closing or
failing one sub-authority cannot mutate another, completed cases cannot be
replaced, and the outer package cannot expand the frozen budget. This document
does not implement or authorize that live architecture.

The offline mapping is intentionally direct: the journal genesis models the
future aggregate package identity; each case record models one sub-authority;
per-case attempt counters and terminal flags model consumption and non-reuse;
the reconciled totals model the aggregate budget; closure digests model
independent case closure; and the terminal-outcome digest map models aggregate
report auditability. The ledger projection is not authority by itself. None of
these synthetic records is live authority.
