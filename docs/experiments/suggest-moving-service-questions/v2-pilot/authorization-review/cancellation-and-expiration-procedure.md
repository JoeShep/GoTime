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
