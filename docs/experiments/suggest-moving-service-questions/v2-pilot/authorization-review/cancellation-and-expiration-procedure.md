# V2 Follow-Up Pilot Cancellation and Expiration

Every outcome retains or restores the permanent closed authorization.

Atomic activation is executable only in transaction state `committed`.
`prepared`, `authorization_installed`, `manifest_activated`,
`activation_recorded`, and `rollback_required` are recovery-only states.

- Human rejection before activation: discard the proposal; no sequence is consumed.
- Operator cancellation before credential access: close immediately; activated sequence is consumed.
- Expiration before execution: make no attempt, record expiration, close, and consume the sequence.
- Expiration after preflight: do not generate; record expiration and close.
- Provider or validation failure: do not retry or replace; preserve bounded audit and close.
- Prose rejection: select fallback v2, create no response evidence, and close.
- Successful generation: close repository authority while bounded evidence awaits mandatory review.
- Review approval or rejection: record bounded review and delete response evidence immediately.
- Evidence deletion failure: retain the audit marker, retry only the idempotent deletion operation, and never regenerate.
- Closure failure: retry only the idempotent closure operation; never reread a credential or repeat provider calls.

Consumption occurs at the earliest credential lookup, client construction,
preflight, generation, expiration, cancellation after activation, or bounded
post-activation failure. An active authorization never returns to unused state.

An interruption after active-file creation, manifest transition, or activation
evidence creation fails closed. An active file without its exact manifest, a
manifest without its exact file, a digest mismatch, missing evidence, or an
uncommitted journal never grants authority. Recovery restores the byte-exact
closed manifest, removes only the active authorization and temporary files,
preserves bounded evidence, records `rolled_back`, and is idempotent.

Sequence 1 ended by operator cancellation before credential access and is
permanently consumed. Sequence 2 is the next eligible preflight attempt and
must receive a fresh candidate, review package, activation, and live-call
approval. Its success or bounded failure writes `002-storage_unknown` evidence
and closes immediately; it is never retried.

Sequence-2 cancellation and recovery operate only on `002-storage_unknown`
active, activation, transaction, audit, evidence, consumption, and closure
paths. Recovery restores the exact permanent closed manifest without deleting,
rewriting, or treating sequence-1 records as authority.

The verified operator recovery command is:

```sh
sh scripts/experiments/suggest_moving_service_questions/close_v2_sequence_2_preflight_authorization_docker.sh \
  --reason "<success|activation_recovery|operator_cancellation|expiration|bounded_failure>"
```

It runs in the pinned evaluation image with networking disabled and is safe to
rerun. It never reads credentials or calls a provider.

An expired review package that was never activated uses a different fixed
cleanup operation. Its verifier passes the rendered TOML through the established
typed preflight validator: phase comes from `metadata.phase`, permissions come
from `authorization`, and request counts come from `scope`. A dry-run must
precede separate confirmation:

```sh
sh scripts/experiments/suggest_moving_service_questions/cleanup_v2_sequence_2_expired_review_package_docker.sh \
  --artifact-sha256 "<EXPIRED_ARTIFACT_SHA256>" \
  --installation-record-sha256 "<INSTALLATION_RECORD_SHA256>" \
  --activation-review-sha256 "<ACTIVATION_REVIEW_SHA256>"
```

The confirmed form adds `--confirm-delete --operator "<OPERATOR_ID>"`. It may
delete only the fixed `/tmp` rendered source and the three fixed sequence-2
review files. It writes an ignored bounded cleanup record, leaves repository
authority closed, and does not consume sequence 2.
