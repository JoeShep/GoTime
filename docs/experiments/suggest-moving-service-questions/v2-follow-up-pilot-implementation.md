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
clients and fake transport results. It neither constructs an OpenAI client nor
contains a live transport admission path. The public entry point validates the
committed execution manifest and stops at the closed repository authorization
before inspecting operator environment values.

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
