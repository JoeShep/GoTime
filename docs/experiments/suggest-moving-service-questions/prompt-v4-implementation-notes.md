# Prompt V4 Offline Freeze

Prompt v4 is an offline-only frozen experimental package implementing the
approved minimal design in `prompt-v4-design-memo.md`. It was motivated by the
single frozen-v3 response that passed structure and semantics and failed only
`storage_modality_overstatement`. The rejected field, trigger, wording, and
offsets remain historically unknowable; v4 does not guess them.

The semantic delta is limited to three instruction changes: explicit
separation of curated evidence from generated prose and byte-exact grounding;
an exact four-trigger runtime-alignment block; and a final silent rewrite and
recheck of the three generated user-facing fields. `grounding_summary` is
never rewritten. Deterministic preparation rejects a grounding source
containing `required`, `requirement`, `must`, or `will need` before a provider-
request object is constructed.

Prompt/schema identities advance to v4. The schema changes only literals and
generated root titles. The strict provider adaptation, fixture, curated
knowledge, provider, model, SDK, temperature, timeout, output-token limit,
zero-retry policy, fallback v2, semantic validation, and existing prose
validator remain unchanged.

The proven generation-gate architecture can be rebound through the same thin
version-specific request and transport-fingerprint adapters. Prompt text and
identity change the deterministic request, canonical attempt, and provider
fingerprint, so approved v3 preflight evidence cannot bind v4. A fresh,
separately versioned v4 token preflight would be required before any future
live v4 generation authorization.

The frozen package binds those three exact request identities in
`v4/request-identity.json`; focused tests independently recompute each value,
require literal equality, and reject mutation of any identity.

V4 has no FastAPI/frontend reachability, credential permission, live pilot,
authorization package, or provider operation. Freezing does not authorize
execution.

## Offline preflight-gate rebind

The proven preflight-only lifecycle is now rebound offline to run series
`moving-service-stage-b-v4-pilot-20260808`, sequence 1, fixture
`storage_unknown`. The inactive candidate binds the exact frozen-v4 manifest,
request-identity artifact, deterministic request, canonical attempt, provider
fingerprint, provider/model/SDK, and one-preflight/zero-generation scope.

All 12 fixed public commands pass an isolated network-disabled rehearsal using
4,242 synthetic tokens and synthetic cost `$0.0024242`. V2/v3 evidence is
rejected, credential-free request verification precedes credential access,
closure restores permanent closed state, and the generation-binding preview is
non-writing and non-authoritative. No live v4 preflight has occurred and no v4
generation candidate or authority exists.

Evidence approval no longer treats lifecycle-file presence as history proof.
The bounded evidence binds activation, final transaction, audit, consumption,
and closure bytes by SHA-256, with explicit token-preflight, non-reuse,
closure, and permanent-closed-state fields. Both review and generation-binding
preview independently validate the exact fixed-path lifecycle chain.

The semantic layer uses the complete candidate bindings/scope as its source of
truth, recomputes the expected active-manifest identity, validates activation
review and committed-then-closed transaction state, requires successful
credential/client audit outcomes, and enforces the whole-second UTC lifecycle
order. Tests separately cover stale-digest failures and self-consistent source
mutations whose downstream digests have all been recomputed.
