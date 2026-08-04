# Offline V2 Follow-Up Pilot Implementation

## Status

```text
capability: suggest_moving_service_questions
implementation: offline fake-boundary only
run series: moving-service-stage-b-v2-pilot-20260802
sequence: 1
fixture: storage_unknown
follow-up pilot authorized: false
credential access authorized: false
token preflight authorized: false
AI generation authorized: false
formal evaluation authorized: false
Stage C authorized: false
production use authorized: false
```

This implementation proves the isolated v2 control path with injected fake
OpenAI SDK-shaped clients and provider responses. The reviewed OpenAI transport
mechanics perform fake exact-token preflight and fake generation against the
frozen v2 prompt, deterministic request JSON, and strict provider schema. It
neither constructs a real OpenAI client nor contains a live transport admission
path. The public entry point stops at closed repository authorization before
inspecting operator environment values.

## Frozen bindings

The runner verifies the exact frozen v2 manifest bytes and every digest stored
in that manifest before preparing a request. It loads:

- prompt `moving-service-questions-prompt-v2`;
- Pydantic request and response schema `moving-service-questions-schema-v2`;
- deterministic fallback `moving-service-fallback-v2`;
- the reviewed OpenAI strict response-schema snapshot;
- the frozen follow-up pilot configuration;
- OpenAI AI model identifier `gpt-4.1-mini-2025-04-14`;
- SDK pin `openai==2.45.0` as configuration evidence only.

The deterministic compact request contains only the validated v2 request
fields. The provider-request seam fixes temperature 0, 500 output tokens,
12-second generation timeout, zero retries, `store: false`, `stream: false`,
`background: false`, disabled truncation, and no tools. The frozen
configuration separately fixes a five-second exact token-preflight timeout.

## Authorization boundary

The permanent execution state is represented by:

- `v2-pilot/execution-manifest.json`;
- `v2-pilot/closed-execution-manifest.json`;
- `v2-pilot/openai-execution-authorization.toml`.

Both are closed. A later proposal may replace the manifest binding with one
reviewed, short-lived authorization for exactly one credential read, one
client construction, one fresh preflight, and one generation for sequence 1.
Operator intent and `GOTIME_MOVING_SERVICE_EVAL_ENABLED=1` cannot broaden that
repository authorization.

The exact future CLI shape is:

```text
python scripts/experiments/suggest_moving_service_questions/run_openai_stage_b_v2_pilot.py \
  --run-series moving-service-stage-b-v2-pilot-20260802 \
  --sequence 1 \
  --fixture storage_unknown \
  --operator-intent AUTHORIZE_ONE_STORAGE_UNKNOWN_V2_PREFLIGHT_AND_GENERATION
```

It is intentionally unusable in the committed closed state. No credential is
shown or requested by this documentation.

## Validation and fallback

The fake generation result remains untrusted. The runner decodes exactly one
JSON object without repair, validates it with the v2 Pydantic response class,
applies the existing capability semantics, and then applies all five prose
checks in stable order. Any prose violation rejects the complete response and
records every violation code. Only then may deterministic orchestration record
fallback `fallback-temporary-storage-v2`. Human grounding review remains
pending for every structurally and automatically valid nonempty response.

## Records and closure

The bounded paths are:

```text
.local/evaluations/suggest-moving-service-questions/
  moving-service-stage-b-v2-pilot-20260802/
    001-storage_unknown-generation-pilot.json
    001-storage_unknown-reviewed-response.json
    001-storage_unknown-generation-pilot-closure.json
```

The audit contains identities, frozen digests, bounded attempt booleans, fake
token and cost values, validation outcomes, prose codes, fallback metadata,
human-review placeholders, and closure state. It excludes credentials,
authorization headers, system instructions, serialized requests, trusted
state, provider envelopes, and raw exception text. Validated response evidence
contains only the structured response needed for later human review. It is
owner-only and ignored by Git. Review sign-off requires immediate deletion;
otherwise deletion is due no later than 30 days after generation. The audit
reserves bounded deletion-deadline, deletion-status, and deletion-timestamp
fields so the existing reviewed explicit deletion lifecycle can be applied
without retaining response content in its deletion record.

The capability-specific closure operation atomically restores the exact closed
manifest template, verifies the permanent closed authorization digest, removes
any distinct temporary active authorization, and writes bounded owner-only
closure evidence. It is safe to rerun. Offline tests exercise both the runner's
closure seam after success and bounded failure and the exact repository
restoration operation. No closure path reads credentials or constructs a
client.

## Version isolation

The v2 runner has a new module, execution manifest, authorization validator,
run series, output directory, and sequence history. It does not import into
FastAPI or the frontend. It does not modify v1 fallback, request/response
schemas, fixtures, authorization, Stage A/Stage B records, or lifecycle
evidence. V1 authorization identities fail the v2 validator, and the v2
identities are not admitted by the v1 runner.

## Offline transport and client boundary

`openai_transport_v2.py` is a thin verifier around the reviewed OpenAI
Responses transport. It changes no provider mechanics. It substitutes the
frozen v2 provider-schema identity and verifies the v2 timeouts, limits,
strict-output mode, AI model identifier, and parameters. The existing frozen
pricing configuration remains the source for token-cost arithmetic.

Offline construction tests pass a synthetic credential explicitly to fake
constructors and verify the official base URL, `max_retries=0`, and an HTTP
client created with `trust_env=false`. Conventional OpenAI environment names
are rejected. Owned client and HTTP resources close. The committed closed
manifest prevents the public runner from inspecting any environment.

## Review, deletion, and Docker lifecycle

The v2 lifecycle accepts only bounded human-review fields and validates the
owner-only response evidence against schema v2 and its recorded digest. Review
sign-off deletes evidence immediately and creates a content-free deletion
record; the recorded 30-day deadline supports explicit later deletion. The
operation is idempotent. Closure restores and verifies the exact permanent
closed manifest and records bounded evidence without credential access.

The v2 Docker launcher and wrapper fix the run series, sequence, fixture, and
operator-intent literal. Host and container checks reject a missing credential
before Python starts. The credential is forwarded by environment-variable name
only. The committed launcher exposes only a synthetic self-test using a
read-only root and repository mount, host UID/GID, and `--network none`; other
invocations stop while repository execution remains closed.

Human review of this integration is still required. No short-lived execution
authorization was generated. Credential access, token preflight, generation,
formal evaluation, Stage C, FastAPI/frontend exposure, and production use all
remain unauthorized.

## Inactive authorization review package

An inactive, non-authoritative review package now exists under
`v2-pilot/authorization-review/`. It contains the candidate, its external
digest manifest, a human checklist, and future activation and cancellation
procedures. The candidate binds the exact frozen v2 package, permanent closed
state, run identity, provider settings, counts, timeouts, spend ceiling, record
paths, and single-use policy.

The candidate has placeholder approver and UTC timestamps, carries no active
permission, and cannot satisfy the manifest-bound execution validator. The
permanent closed execution manifest remains byte-for-byte authoritative.
Activation requires a separately rendered artifact, new digest, reviewed
manifest diff, exact human identity and timestamps, and explicit approval in a
later milestone. Package preparation and dry-run validation inspect no
credential environment, construct no client, and make no network request.

## Two-gate reconciliation

The future live-capable workflow is now represented offline as two mutually
exclusive phases for the same sequence-1 pilot attempt. A preflight
authorization permits one credential lookup, one client construction, and one
exact token count, while generation remains false and unreachable. A later
generation authorization permits one credential lookup, one client
construction, and one generation, while token preflight remains false and
unreachable. Neither phase authorizes formal evaluation, Stage C, or production
use. The permanent committed execution manifest remains closed.

Successful preflight writes separate owner-only audit and evidence records:

```text
.local/evaluations/suggest-moving-service-questions/
  moving-service-stage-b-v2-pilot-20260802/
    001-storage_unknown-preflight.json
    001-storage_unknown-preflight-evidence.json
    001-storage_unknown-preflight-review.json
    001-storage_unknown-preflight-evidence-consumption.json
```

The evidence contains only frozen identities and digests, deterministic request
and provider-payload digests, bounded provider identity and parameters, token
count, cost ceiling, timing, and review state. It excludes prompts, serialized
request content, trusted state, credentials, headers, envelopes, and raw
exceptions. Human review is append-only in a separate digest-bound record.
Rejection or expiration blocks generation.

Generation verifies the exact evidence and review digests plus the frozen
manifest, prompt, schema, payload, request, provider, AI model identifier, SDK,
timeouts, parameters, and cost. It creates an exclusive consumption record
before invoking fake generation and cannot perform token preflight. A failed
generation cannot reuse the consumed evidence. Automated success still requires
human grounding review and the existing response-evidence deletion lifecycle.

Separate preflight and generation Docker launchers fix the phase and run
identity. Their committed forms are offline-only, use synthetic credentials,
run with `--network none`, and stop when the permanent repository authority is
closed. Missing credentials stop before Docker or Python. No active artifact,
approver, timestamp, real credential, client, or provider request was created
by this reconciliation.

The inactive candidate remains byte-for-byte unchanged. It is compatible as a
non-authoritative umbrella review ceiling because it already requires separate
preflight and generation approval; future activation must render two distinct
active artifacts rather than activate its combined proposed-permission view.

## Inactive phase-specific candidates

Two narrower review candidates now live under
`v2-pilot/authorization-review/phase-candidates/`. The preflight candidate
proposes one credential lookup, one client construction, one preflight, and
zero generations. The generation candidate proposes one credential lookup,
one client construction, zero preflights, and one generation. Both bind the
unchanged umbrella candidate digest and the complete frozen-v2 package. Both
remain inactive, non-authoritative, placeholder-bound, and invalid for
execution.

Offline loaders reject path substitution, symlinks, digest drift, duplicate
TOML keys, unknown fields, mixed versions, phase overlap, broadened limits, and
unresolved values in active validation. Dry-run renderers may write only a new
owner-only file under `/tmp`; they never replace the permanent closed
authorization. The generation renderer additionally requires exact immutable
preflight evidence and approved review records, verifies their digests,
freshness, unused state, run and frozen bindings, token count, cost, request
digest, canonical-attempt digest, provider fingerprint, reviewer, and review
timestamp.

The maximum activation-to-expiration window is 900 seconds. Approval cannot be
in the future, activation cannot precede approval, and generation approval or
activation cannot precede preflight review. Phase authority is single use at
the earliest irreversible attempt boundary and never returns to unused state.
Preparation and activation remain separate milestones. No approver or timestamp
placeholder was resolved, no credential environment was inspected, and no
client or network operation occurred. Permanent closed repository authority,
formal-evaluation prohibition, Stage C prohibition, and production prohibition
remain unchanged.

## Preflight rendering CLI

The phase-specific preflight candidate has one stable offline renderer:
`render_v2_preflight_authorization_candidate.py`. It requires an absolute new
output file under the real `/tmp` directory plus explicit approver, reason, and
whole-second UTC approval, activation, and expiration values. The maximum
activation window remains 900 seconds. No scope, identity, permission, limit,
digest, provider, AI model identifier, fixture, sequence, or target-authority
override is exposed.

The command verifies the exact candidate, phase manifest, umbrella candidate,
frozen v2 package, and permanent closed state through the reviewed loader and
renderer. It creates an owner-only file exclusively and prints only the path
and SHA-256 digest. The result remains outside the repository and authoritative
evaluation path; rendering does not install it, alter the execution manifest,
or grant execution authority. Generation rendering remains unsupported. This
milestone inspected no credential environment, constructed no client, and made
no network request.

## Preflight installation and activation review

The rendered preflight artifact can now move through two additional offline,
non-authoritative states. Installation verifies exact `/tmp` source bytes,
owner-only permissions, candidate and frozen bindings, active validity, closed
repository authority, and unused sequence state before exclusively copying the
bytes into the fixed ignored `authorization-review/` directory. A bounded
installation record identifies the artifact and closed-state evidence without
retaining prompts, requests, environment data, or credentials.

A separate append-only review records `approve`, `reject`, or
`request_changes`. Approval creates eligibility only; it does not change the
manifest or write the future active authorization. Rejection and requested
changes permanently block the installed artifact from the dry-run planner. The
planner verifies all three exact digests, current validity, approval, closed
state, conflict absence, and unused sequence, then reports the future active
destination and required transition without writing them.

Rendering, installation, activation review, and activation are therefore four
distinct operations. The fourth remains unimplemented and unauthorized. The
permanent closed execution manifest remains authoritative. This milestone read
no credential or credential environment, constructed no client, and performed
no preflight, generation, or network operation.
