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

The future local artifact is:

```text
.local/evaluations/suggest-moving-service-questions/
  moving-service-stage-b-v2-pilot-20260802/
    001-storage_unknown-preflight-authorization.toml
```

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
