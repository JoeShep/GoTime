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
non-writing and non-authoritative.

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

## Offline generation-candidate resolution

The one live frozen-v4 sequence-1 preflight succeeded with 2,852 input tokens
and a conservative maximum generation cost of `$0.0019408`. Its exact evidence
digest is `f1f99523...`; its timely approved review digest is `12b71c10...`.
The full current lifecycle history revalidates before resolution, including
consumption, non-reuse, closure, and the permanent closed manifest.

A separate inactive sequence-4 generation candidate is now resolved against
those exact bytes. The candidate explicitly binds the frozen request-identity
artifact and proposes one generation, zero token preflights, zero retries, a
12-second timeout, 500 output tokens, `$0.03` maximum spend, and mandatory
post-response grounding review. Its 12-command workflow passes five isolated,
network-disabled scenarios. Resolution is non-authoritative: no live v4
generation has occurred and no generation authority or timestamp package
exists.

The live boundary treats completed preflight history and current generation
state as separate invariants. Historical validation proves the preflight
closed against the permanent manifest without requiring the repository to
remain closed during a later generation activation. The live verifier then
validates the complete active authorization against the resolved candidate and
recomputes the sole valid active generation manifest. The CLI verifier and
live runner share this implementation, and all checks precede credential
lookup.

The exact-command rehearsal no longer substitutes minimal preflight evidence.
It creates realistic authorization-through-review preflight records with the
existing lifecycle functions, validates them while generation state is
actively exact, and exercises wrong-authorization and wrong-manifest failures
through the live entry boundary before synthetic credential access.
