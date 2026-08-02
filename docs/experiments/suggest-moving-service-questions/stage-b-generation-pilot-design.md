# Stage B Single-Generation Pilot Design — Suggest Moving-Service Questions

## 1. Status and Scope

```text
design date: 2026-08-01
capability: suggest_moving_service_questions
Stage B design approved: true
offline Stage B implementation authorized: true
offline Stage B implementation complete: true
credential access authorized: false
token preflight authorized: false
AI generation authorized: false
formal evaluation authorized: false
production use authorized: false
```

### Completed pilot closeout

Stage B sequence `5` completed on 2026-08-02. Exact token preflight, one
generation, provider structured output, Pydantic validation, and GoTime
semantic validation succeeded. Human grounding review rejected the response
and rated it `slightly_worse` than the deterministic fallback because it
introduced an unsupported user fact and broadened the approved grounding
scope. The validated response evidence was deleted at review sign-off,
sequence `5` is consumed, the manifest is restored to the permanent closed
authorization, and Stage C remains unauthorized.

The prospective controls below are retained as the historical design that
governed the completed pilot. They are not authority to reactivate or repeat
Stage B.

This document designs one evaluation-only generation pilot. It does not create
an authorization artifact, change the active authorization, expose the
experiment through the application, or authorize a provider request. The
manifest remains bound to the permanent closed authorization.

Stage B is not part of the fixed 20-slot formal evaluation, which remains a
separate Stage C decision. A Stage B result must never be counted, copied, or
promoted into the Stage C denominator.

## 2. Historical Pilot Scope

```text
run-series ID: moving-service-stage-b-pilot-20260801
sequence: 5
fixture: storage_unknown
maximum credential reads: 1
maximum client constructions: 1
maximum token-preflight requests: 1
maximum AI-generation requests: 1
automatic retries: 0
maximum input tokens: 3000
maximum output tokens: 500
token-preflight timeout: 5 seconds
AI-generation timeout: 12 seconds
maximum authorized spend: $0.03
formal evaluation authorized: false
production use authorized: false
```

The pilot used a new series because Stage A sequences belonged to a different
preflight-only authorization history. Stage B sequences `1`, `2`, and `3` were
consumed by credential-stage failures, sequence `4` was consumed by a bounded
generation failure, and sequence `5` was consumed by the completed reviewed
attempt. No sequence in this series is currently eligible. Only
`storage_unknown` was eligible; its fresh preflight and one generation formed
one indivisible pilot attempt.

## 3. Proposed Authorization Artifact

The later artifact should be capability-specific and versioned:

```text
proposed path:
  docs/experiments/suggest-moving-service-questions/v1/
  openai-stage-b-execution-authorization.toml
proposed version: moving-service-openai-stage-b-authorization-v1
proposed status while inactive: candidate_pending_explicit_approval
operator-intent literal:
  AUTHORIZE_ONE_STORAGE_UNKNOWN_STAGE_B_PREFLIGHT_AND_GENERATION
```

Its exact final bytes must bind:

* capability `suggest_moving_service_questions`;
* prompt path, version, and SHA-256
  `583a4bdf59c4c4ac67c82928415710c3d5c21ac9912ebd4888a026b8fd4acbf2`;
* run-configuration path and SHA-256
  `e665e04b56d8aeaa01f4c9df2fd2f5f4eed37150802fdba869cba54d1e5bc782`;
* provider-schema path and SHA-256
  `9e5a3a667a1049d150734fd16669dad98cc982c2dc7a9a18f3e0b8cb3e891afb`;
* request, response, and knowledge-fixture versions;
* provider `OpenAI`;
* AI model identifier `gpt-4.1-mini-2025-04-14`;
* SDK pin `openai==2.45.0`;
* the one series, sequence, and fixture above;
* maximum spend `$0.03` and all request-count limits above;
* exact approving human, whole-second UTC approval and expiration times, and
  a reviewed short duration, provisionally 900 seconds; and
* single-use and failure-consumes-sequence policies.

The only proposed permission pattern is:

```toml
[authorization]
credential_access_authorized = true
token_preflight_authorized = true
ai_generation_authorized = true
formal_evaluation_authorized = false
```

The artifact must also state `production_use_authorized = false`. Unknown or
missing sections and fields fail closed. Environment values, credential
presence, command-line arguments, and operator intent cannot create or widen
repository authority. Stage A and Stage C artifacts cannot substitute for the
exact Stage B path, version, digest, status, permissions, and scope.

The committed authorization remains the permanent closed artifact throughout
design and implementation. A short-lived final Stage B artifact may be created
only after separate implementation review.

## 4. Gate Order and Single-Use Enforcement

The later runner must enforce this order:

```text
host-side credential presence/nonempty check
→ Docker startup
→ container-side credential presence/nonempty check
→ Stage B Python runner startup
→ frozen-artifact integrity
→ exact Stage B manifest authorization
→ series, sequence, and fixture validation
→ ignored output path and atomic non-overwrite reservation
→ token, per-call, and monthly budget checks
→ exact operator-intent check
→ credential access
→ pinned synchronous client construction
→ fresh token preflight
→ preflight evidence verification and consumption
→ one AI-generation request
→ JSON parsing without repair
→ Pydantic response validation
→ GoTime semantic validation
→ bounded audit finalization
→ human-review handoff
→ immediate repository closure
```

The two launcher checks test only whether the named variable exists and is
nonempty. They must not print, hash, measure, log, or otherwise expose its
value. Failure at either check occurs before the Python runner and before audit
reservation, so it does not consume sequence `5` and cannot reach client
construction or a network operation.

The exact audit path must be reserved with exclusive creation before credential
value retrieval by Python. That reservation is the local concurrency gate:
another process cannot reach preflight or generation for the same pilot slot.
Every failure after the reservation consumes the sequence. The record is never
deleted to retry or replace the pilot.

## 5. Fresh-Preflight Evidence

Stage A evidence is ineligible. Stage B calls `preflight()` after constructing
the provider request for its own attempt and retains the returned evidence only
in memory within the same transport instance and client lifetime.

The Stage B runner should wrap the transport result in a small, immutable,
capability-specific evidence object containing the exact authorization digest,
run-series ID, sequence, fixture, request fingerprint, audit-record path, an
opaque in-memory attempt token, and the preflight completion time. The wrapper
must not support serialization. The runner creates the attempt token only after
exclusive audit reservation and never accepts one from a caller.

Generation may proceed only when all of these checks pass:

* preflight succeeded and returned an integer count no greater than 3,000;
* preflight has no timeout or unavailable classification;
* conservative pre-generation cost is no greater than `$0.03`;
* evidence was created after the Stage B audit reservation and during the same
  runner invocation;
* evidence carries the same opaque attempt token, authorization digest, series,
  sequence, fixture, and reserved audit path as the pending generation;
* repository authorization remains active and unexpired immediately before
  generation;
* evidence object has not already been consumed;
* evidence fingerprint equals a freshly calculated generation fingerprint;
* prompt text, deterministic request JSON, strict provider schema, provider,
  AI model identifier, model parameters, output limit, timeout, retry count,
  and `store`/`stream`/`background` settings are unchanged; and
* the frozen prompt, run configuration, and provider-schema digests still
  match immediately before generation.

The existing transport fingerprint covers the common input, structured-output
schema, AI model identifier, temperature, maximum output tokens, storage,
background, streaming, timeout, and retries. Artifact verification supplies
the prompt, run-configuration, and provider-schema bindings. The Stage B
validator supplies the authorization digest and exact series/fixture scope.

`generate()` consumes the in-memory evidence before invoking the provider. A
timeout or provider error still leaves it consumed. The evidence is not
serializable, is never written to disk, and cannot authorize a second call.
Evidence from another runner invocation, an earlier authorization window, or a
different audit reservation is stale even if its request fingerprint matches.

## 6. Generation and Validation Behavior

The one Responses API generation uses exactly:

```text
AI model identifier: gpt-4.1-mini-2025-04-14
temperature: 0
max_output_tokens: 500
strict JSON Schema: enabled
store: false
stream: false
background: false
tools: none
timeout: 12 seconds
automatic retries: 0
```

Provider-managed automatic prompt caching is allowed under the frozen protocol;
GoTime does not create cache keys, reorder work, or reuse generated responses.

Provider output remains untrusted. Validation is deliberately layered:

1. Extract exactly one output-text item. Refusal, incomplete status, extra
   output items, or missing text fails.
2. Parse exactly one JSON object with duplicate keys rejected. Do not repair,
   strip fields, infer values, or salvage partial content.
3. Run `MovingServiceQuestionResponse.model_validate()` and record the
   Pydantic result separately.
4. Run `validate_response(request, raw_response)` for GoTime semantic rules,
   including supplied knowledge/category/decision references and uniqueness.
5. Require human review of every free-text field before grounding can pass.

The implementation may factor a small capability-specific validation helper so
Pydantic and semantic failures can be recorded distinctly. Runtime
`validate_response()` remains authoritative; its rules are not weakened.

## 7. Success Criteria

### Transport success

* Fresh preflight succeeds.
* Exactly one generation completes within its 12-second request timeout.
* No retry occurs and client resources close.
* Input, output, cached-input, and uncached-input usage are recorded when
  reported; missing optional metadata is explicitly marked unavailable.
* Provider-reported usage produces a cost no greater than `$0.03`.

### Contract success

* Exactly one schema-valid response object is returned with no extra fields.
* `capability`, prompt version, and schema version match.
* Suggestions contain every required field.
* `requires_user_confirmation` is `true`.
* `warnings` is empty and `fallback_recommended` is `false`.
* Only supplied knowledge IDs and `temporary_storage_need` are referenced.
* No known state is questioned.

### Grounding success

Human review confirms no invented user fact, no claim that storage is required,
no provider or moving-service-model recommendation, and no pricing,
availability, timing, quality, or unsupported moving-industry claim. Any
grounding must remain within the conditional FMCSA statement.

### Product observation

The reviewer selects exactly one bounded comparison against the deterministic
fallback:

* `materially_better`
* `slightly_better`
* `equivalent`
* `slightly_worse`
* `materially_worse`

This observation is descriptive. One pilot cannot establish product value,
reliability, or a production decision.

## 8. Failure Behavior

Every failure consumes its Stage B sequence, is never retried or replaced,
prevents another generation, and produces or finalizes the exclusive bounded
record. The repository must be restored to closed authorization afterward.

| Failure | Bounded phase/classification | Required stop |
| --- | --- | --- |
| Authorization or artifact mismatch | `authorization` | Before environment access |
| Credential missing/invalid | `credential` | Before client construction |
| Client construction failure | `client_construction` | Before network access |
| Token preflight timeout/unavailable | `preflight_timeout` / `preflight_unavailable` | No generation |
| Invalid count, over 3,000 tokens, or cost over `$0.03` | `preflight_gate` / `budget` | No generation |
| Generation authentication failure | `generation_authentication_failed` | Evidence remains consumed |
| Generation permission failure | `generation_permission_denied` | Evidence remains consumed |
| Generation model/resource unavailable | `generation_model_unavailable` | Evidence remains consumed |
| Generation rate limited | `generation_rate_limited` | Evidence remains consumed |
| Generation invalid request | `generation_invalid_request` | Evidence remains consumed |
| Generation connection failure | `generation_connection_failed` | Evidence remains consumed |
| Generation provider unavailable | `generation_provider_unavailable` | Evidence remains consumed |
| Generation timeout | `generation_timeout` | Evidence remains consumed |
| Refusal | `refusal` | Reject output |
| Incomplete response | `incomplete_response` | Reject output |
| Malformed or duplicate-key JSON | `malformed_json` | No repair |
| Provider-schema failure | `provider_schema` | Reject output |
| Pydantic failure | `pydantic_validation` | Reject output |
| GoTime semantic failure | `semantic_validation` | Reject output |
| Human grounding failure | `human_grounding` | Contract result remains separate; pilot fails grounding |

Unexpected programming errors remain visible, but the reserved record must be
left in a bounded `unexpected_failure` state without exception text. The safe
deterministic fallback may be evaluated only as metadata after failure; it does
not turn the failed AI attempt into success and does not mutate state.

## 9. Bounded Audit Record

Proposed path:

```text
.local/evaluations/suggest-moving-service-questions/
  moving-service-stage-b-pilot-20260801/
  005-storage_unknown-generation-pilot.json
```

The record may contain:

* run-series ID, sequence, fixture, capability, and pilot status;
* prompt, authorization, run-configuration, and provider-schema identities and
  digests;
* provider, AI model identifier, and SDK version;
* credential/client attempted and succeeded booleans;
* preflight attempted/succeeded, exact input tokens, duration, and bounded
  failure classification;
* generation attempted/succeeded, output tokens, cached/uncached input tokens,
  cache status, provider request ID, finish status, refusal status, incomplete
  reason, generation duration, and total duration;
* conservative preflight cost and provider-usage-based actual estimated cost;
* JSON extraction, Pydantic validation, and semantic-validation booleans and
  bounded error codes;
* fallback available/used/reason metadata;
* normalized question text and referenced knowledge IDs;
* human-review status, grounding checklist booleans, product-observation enum,
  reviewer identity, review timestamp, and short bounded notes; and
* explicit closure status and closed-authorization digest.

It must exclude API keys, authorization headers, system instructions,
serialized requests, full provider envelopes, trusted-state payloads,
conversation history, arbitrary exception text, and raw user answers.

## 10. Human-Review Evidence and Retention

Human grounding review requires the validated free-text response, not merely a
normalized question. Retain one separate evidence file containing only the
validated `MovingServiceQuestionResponse` object—never the provider envelope,
prompt, request, credential, or trusted-state payload.

Proposed path:

```text
.local/evaluations/suggest-moving-service-questions/
  moving-service-stage-b-pilot-20260801/
  005-storage_unknown-reviewed-response.json
```

The evidence file should be ignored by Git, created exclusively with owner-only
permissions where supported, and referenced from the audit record by SHA-256.
Encryption is not proposed for this synthetic bounded fixture because it would
introduce a separate key-management boundary; filesystem access control is the
smaller design. Delete the evidence and raw local audit record within 30 days
of pilot execution or immediately after review sign-off and aggregation,
whichever occurs first. Retain only the reviewed aggregate outcome in Git.

The offline lifecycle now implements this retention rule. Human-review sign-off
deletes evidence immediately; otherwise an explicit capability-specific
operation enforces the recorded 30-day deadline. Both paths write a bounded,
owner-only deletion record and update the audit lifecycle fields.

## 11. Smallest Offline Implementation Plan

1. Add a capability-specific Stage B authorization validator with an exact
   path/version/status/permission/scope allowlist and frozen bindings.
2. Add a script-only Stage B runner. Do not import it from FastAPI, backend
   startup, frontend, or the normal fake-only runner.
3. Reuse existing validated `storage_unknown` request construction, frozen
   prompt loading, deterministic JSON serialization, transport artifact
   verification, client factory, `preflight()`, and `generate()`.
4. Reserve the one audit path atomically before credential access.
5. Bind generation to the same in-memory request and fresh preflight object;
   do not add serialized evidence or a reusable token-count cache.
6. Add capability-specific parsing/validation orchestration that distinguishes
   extraction, Pydantic, semantic, and grounding outcomes without weakening
   `validate_response()`.
7. Finalize bounded audit data for every known failure and success path, close
   all client resources, and expose no full payload in logs.
8. Produce the ignored response-evidence file only after Pydantic and semantic
   validation succeed, and manage it through the approved explicit retention
   lifecycle.
9. Add an offline closure helper or reviewed closure procedure that restores
   the permanent closed manifest and removes the short-lived artifact after
   success, failure, or expiration. Tests operate only on temporary repository
   copies and fake clients.

No generic provider registry, model router, prompt framework, retry layer,
application service, or formal-series runner is needed.

## 12. Required Offline Tests

Implementation approval must require tests proving:

* closed authorization rejects Stage B before environment access;
* Stage A and Stage C/formal authorization patterns cannot substitute;
* wrong fixture, sequence, series, artifact digest, AI model identifier, SDK
  pin, prompt digest, run-configuration digest, or schema digest is rejected;
* missing, failed, stale, mismatched, or reused preflight evidence is rejected;
* generation cannot run before preflight;
* one fresh preflight object permits at most one generation attempt;
* the second generation is rejected even after timeout or provider failure;
* timeout and unavailable errors remain distinct and bounded with no retries;
* refusal and incomplete output are rejected distinctly;
* malformed or duplicate-key JSON is never repaired;
* provider-schema, Pydantic, semantic, and human-grounding failures remain
  distinguishable;
* exact cost, cache, and usage arithmetic is bounded and checked;
* audit and evidence files omit prohibited content and cannot be overwritten;
* concurrent or repeated attempts cannot pass the atomic record reservation;
* no backend route, application module, frontend file, or production config can
  reach Stage B generation; and
* temporary-repository simulations restore the permanent closed authorization
  after success, every known failure, and expiration.

All tests use injected fake clients and network-disabled environments. No test
reads process credentials or imports a network-capable runner into application
code.

## 13. Human Review and Later Activation Sequence

1. Review and approve this design.
2. Implement and commit the offline Stage B validator, runner, records, and
   tests while authorization remains closed.
3. Run complete network-disabled backend, experiment, and frontend checks.
4. Reconfirm the dedicated OpenAI project, project-scoped credential,
   permissions for both input-token counting and Responses generation, model
   access, spend/rate controls, training opt-out, and accepted retention.
5. Generate a short-lived Stage B proposal under `/tmp` showing exact artifact
   bytes, digest, manifest diff, audit path, and execution command.
6. Human approves only the exact repository switch.
7. Human separately authorizes one preflight-plus-generation attempt.
8. Operator supplies the API key only to the bounded process environment.
9. Run exactly one Stage B attempt; no retry or replacement.
10. Remove the key from the bounded process environment.
11. Restore the permanent closed authorization immediately, preserving bounded
    evidence for review.
12. Complete human grounding/product review, apply the retention decision, and
    commit only the closed-state aggregate outcome.

## 14. Remaining Decisions

Repository-side decisions are resolved: the run-series, sequence, fixture,
operator-intent literal, 900-second maximum window, human-review schema,
evidence retention, bounded tombstones, and closure lifecycle are implemented
and offline tested. Before generating a new activation package, a human must
reconfirm the private OpenAI project, project-scoped credential permissions for
both token counting and Responses generation, model access, spend/rate
controls, training opt-out, and accepted provider retention. Repository switch
approval and one-attempt execution approval remain separate later decisions.

## 15. Readiness Decision

```text
Stage B design ready for human review: true
Stage B design approved: true
offline Stage B implementation authorized: true
offline Stage B implementation complete: true
credential access authorized: false
token preflight authorized: false
AI generation authorized: false
formal evaluation authorized: false
production use authorized: false
```

The private account controls were reconfirmed on 2026-08-02. Sequence `5` is
complete and consumed; no fresh Stage B activation-package review is pending.
The human review rejected the response, the response evidence was deleted, and
the active authorization is permanently closed. The frozen prompt, run
configuration, provider response-schema snapshot, and their digests remain
unchanged. Stage C remains unauthorized.
