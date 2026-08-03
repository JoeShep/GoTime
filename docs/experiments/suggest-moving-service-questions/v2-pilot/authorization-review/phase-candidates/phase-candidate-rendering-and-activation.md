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
