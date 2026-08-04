# V2 Phase-Candidate Rendering and Activation

These committed candidates are inactive review inputs. They are not execution
authority and must never replace the permanent closed authorization.

## Preflight

After separate human approval, render the preflight candidate to an exclusive,
ignored local file for sequence 1. Rendering requires the exact candidate and
umbrella digests, frozen-v2 verification, approver, reason, and ordered
whole-second UTC timestamps. The maximum activation-to-expiration window is
900 seconds. The rendered artifact may authorize one preflight and zero
generations. Activation remains a later reviewed repository-binding operation.

The supported offline rendering command is:

```text
python scripts/experiments/suggest_moving_service_questions/render_v2_preflight_authorization_candidate.py \
  --output /tmp/gotime-v2-preflight-authorization.toml \
  --approver "<APPROVER_ID>" \
  --approved-at "<APPROVED_AT_WHOLE_SECOND_UTC_Z>" \
  --activated-at "<ACTIVATED_AT_WHOLE_SECOND_UTC_Z>" \
  --expires-at "<EXPIRES_AT_WHOLE_SECOND_UTC_Z>" \
  --reason "<AUTHORIZATION_REASON>"
```

All six arguments are required. The output must be an absolute, nonexistent
regular-file path beneath an existing real directory under `/tmp`; relative
paths, traversal, prefix confusion, symlinks, repository paths, and
`.local/evaluations` paths fail closed. The file is created exclusively with
owner-only permissions. The activation-to-expiration window is at most 900
seconds.

Success prints only:

```text
output_path=<absolute path>
sha256=<64-character lowercase digest>
```

Exit codes are: `2` argument error, `3` path-policy error, `4` candidate or
frozen-integrity error, `5` authorization-value validation error, and `6`
exclusive-write error. Failure diagnostics are bounded and written to stderr.
The rendered `/tmp` file is review evidence only: it is not installed, not
referenced by the execution manifest, and not authoritative merely because it
exists. Generation rendering is not supported by this CLI.

## Non-authoritative installation and activation review

Rendering, installation, activation review, and activation are four separate
operations. A previously rendered artifact may be copied byte-for-byte into
the fixed ignored review area with:

```text
python scripts/experiments/suggest_moving_service_questions/install_v2_preflight_authorization_for_review.py \
  --source /tmp/gotime-v2-preflight-authorization.toml \
  --expected-sha256 "<RENDERED_ARTIFACT_SHA256>"
```

The installed artifact and append-only installation record are fixed at:

```text
.local/evaluations/suggest-moving-service-questions/
  moving-service-stage-b-v2-pilot-20260802/authorization-review/
    001-storage_unknown-preflight-rendered.toml
    001-storage_unknown-preflight-installation.json
```

Installation preserves exact bytes, uses owner-only files and directory,
verifies the closed repository and absence of attempt conflicts, and leaves the
execution manifest unchanged. The staged artifact remains non-authoritative.

Review that exact installation without activating it using:

```text
python scripts/experiments/suggest_moving_service_questions/review_v2_preflight_authorization_activation.py \
  --artifact-sha256 "<INSTALLED_ARTIFACT_SHA256>" \
  --reviewer "<REVIEWER_ID>" \
  --decision "<approve|reject|request_changes>" \
  --reviewed-at "<WHOLE_SECOND_UTC_Z>" \
  --notes "<BOUNDED_NOTES>"
```

The append-only review is written to
`authorization-review/001-storage_unknown-preflight-activation-review.json`.
Approval means only that the installed bytes are eligible for a later atomic
activation while still valid. Rejection or `request_changes` permanently
blocks planning for that installed artifact.

The non-writing prerequisite planner is:

```text
python scripts/experiments/suggest_moving_service_questions/plan_v2_preflight_authorization_activation.py \
  --artifact-sha256 "<INSTALLED_ARTIFACT_SHA256>" \
  --installation-record-sha256 "<INSTALLATION_RECORD_SHA256>" \
  --activation-review-sha256 "<ACTIVATION_REVIEW_SHA256>"
```

It reports the future active destination, expected digest, required manifest
transition, closure path, deadline, and remaining confirmations. It writes
nothing. The future active path remains unwritten.

Stable exit codes across these commands are: `2` argument, `3` path policy,
`4` source integrity, `5` candidate/frozen integrity, `6` closed state, `7`
conflicting state, `8` validity window, `9` installation write, `10` review
validation, `11` review write, and `12` activation prerequisite. Existing
destination, prior record, active authority, attempt evidence, expiration,
digest drift, and consumed sequence all fail closed without overwrite or
repair.

The future local artifact is:

```text
.local/evaluations/suggest-moving-service-questions/
  moving-service-stage-b-v2-pilot-20260802/
    001-storage_unknown-preflight-authorization.toml
```

After installation, approval, and the non-writing plan have been reviewed, the
future atomic activation command is:

```text
python scripts/experiments/suggest_moving_service_questions/activate_v2_preflight_authorization.py \
  --artifact-sha256 "<INSTALLED_ARTIFACT_SHA256>" \
  --installation-record-sha256 "<INSTALLATION_RECORD_SHA256>" \
  --activation-review-sha256 "<ACTIVATION_REVIEW_SHA256>" \
  --operator "<OPERATOR_ID>" \
  --operator-intent "activate exactly one v2 moving-service preflight authorization"
```

This command may be used only in a separately authorized milestone while the
reviewed artifact is valid. The transaction creates the exact active bytes,
atomically installs an exact preflight-only manifest, and records bounded
activation evidence. Authority exists only when the active file, manifest,
activation evidence, and committed journal all agree; partial state fails
closed.

Durable transaction states are `prepared`, `authorization_installed`,
`manifest_activated`, `activation_recorded`, and `committed`. Recovery may use
`rollback_required` and finishes at `rolled_back`. Exclusive writes, fsyncs,
and same-filesystem atomic renames protect the transition. Idempotent recovery
restores the exact closed manifest and removes only active/temporary files.

Activation exit codes are: `2` argument, `3` input integrity, `4` review
validation, `5` validity window, `6` closed state, `7` conflict, `8`
transaction preparation, `9` active-authorization write, `10` manifest
transition, `11` activation-record write, `12` transaction commit, and `13`
recovery required. Validation has used synthetic roots only; the committed
manifest remains closed and generation remains unauthorized.

Preflight authority is consumed at the first credential lookup, client
construction, token-preflight attempt, expiration, post-activation
cancellation, or bounded failure. It never returns to unused active state.

## Generation

Generation rendering is unavailable until immutable preflight evidence and an
append-only approved review record exist. Rendering verifies both file digests,
all frozen and run bindings, freshness, unused state, token count, conservative
cost, request digest, canonical-attempt digest, provider fingerprint, reviewer,
and review timestamp. Approval and activation cannot precede review.

The future local artifact is:

```text
.local/evaluations/suggest-moving-service-questions/
  moving-service-stage-b-v2-pilot-20260802/
    001-storage_unknown-generation-authorization.toml
```

The artifact may authorize one generation and zero preflights. It is consumed
at the first credential lookup, client construction, evidence-consumption
operation, generation attempt, expiration, post-activation cancellation, or
bounded failure. A failed generation cannot be retried.

Both phases require independent human approval and a separate later activation
operation. Expiration, rejection, cancellation, or failure leaves or restores
the permanent closed manifest. No candidate, renderer, operator flag, or local
artifact broadens Stage C, formal-evaluation, production, FastAPI, or frontend
authority.
