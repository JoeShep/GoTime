# OpenAI Transport Design — Suggest Moving-Service Questions

## 1. Status and Scope

```text
capability: suggest_moving_service_questions
design date: 2026-07-31
provider: OpenAI
AI model identifier: gpt-4.1-mini-2025-04-14
provider-transport design: human-reviewed and approved
provider-transport implementation authorized: false
SDK installation authorized: false
credentials authorized: false
real-model execution authorized: false
production use authorized: false
```

This is a capability-specific design for a future transport behind the existing
script-only evaluation scaffold. It does not authorize implementation,
dependency installation, credential access, or an API request. It does not
create a generic OpenAI client or provider abstraction.

The transport would convert one verified `MovingServiceProviderRequest` into
one untrusted `MovingServiceTransportResult`. The runner would continue to own
authorization, fixture selection, token and spending gates, run-series control,
record writing, and deterministic fallback. Existing runtime validation would
remain authoritative.

The corresponding run configuration is approved and frozen at
`docs/experiments/suggest-moving-service-questions/v1/openai-run-configuration.toml`.
Its SHA-256 digest is
`e665e04b56d8aeaa01f4c9df2fd2f5f4eed37150802fdba869cba54d1e5bc782`.
Freezing it does not authorize implementation, credentials, or execution.

## 2. Frozen Inputs and Non-Negotiable Boundaries

```text
prompt artifact: docs/experiments/suggest-moving-service-questions/v1/real-model-prompt.toml
prompt SHA-256: 583a4bdf59c4c4ac67c82928415710c3d5c21ac9912ebd4888a026b8fd4acbf2
prompt version: moving-service-questions-prompt-v1
request schema: moving-service-questions-schema-v1
response schema: moving-service-questions-schema-v1
knowledge fixture: moving-service-storage-fixture-v2
maximum input tokens: 3,000
maximum output tokens: 500
token-preflight timeout: 5 seconds
AI-generation timeout: 12 seconds
automatic retries: 0
```

The design does not change the frozen prompt, deterministic compact request
JSON, Pydantic request schema, Pydantic response schema, or deterministic
fallback ownership. It does not add tools, live research, conversation state,
background execution, streaming, response reuse, or application-managed
caching.

## 3. Official Interfaces and Version Pinning

The approved implementation proposal is the official OpenAI Python SDK pinned
to the experiment-specific release `openai==2.45.0`. This is not a general
GoTime dependency standard. The research date's official repository identifies
2.45.0 as its latest release. The dependency and its transitive lock changes
would require separate review before installation. A later run series must
record the configured pin, resolved package version, lockfile entry, Python
version, and SDK version. Changing the pin requires review and a new offline
dry-run verification, but does not by itself require a prompt-version change.

The transport would use only these versioned API paths exposed by that SDK:

```text
POST /v1/responses/input_tokens
POST /v1/responses
```

OpenAI does not document a date-based API-version request header for these
interfaces. Reproducibility therefore comes from the immutable AI model
identifier, the exact SDK pin, the `/v1` paths, the frozen request configuration,
and recorded provider response metadata. Availability and SDK/API compatibility
must be reconfirmed immediately before implementation approval.

Official sources:

* [GPT-4.1 mini model](https://developers.openai.com/api/docs/models/gpt-4.1-mini)
* [Responses API](https://developers.openai.com/api/docs/guides/responses-vs-chat-completions)
* [Structured model outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
* [Counting tokens](https://developers.openai.com/api/docs/guides/token-counting)
* [Prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching)
* [OpenAI Python SDK](https://github.com/openai/openai-python)

## 4. Exact Generation Request

The future transport would construct the following logical Responses API
request. Placeholder values identify inputs; they are not example prompt or
response content.

```json
{
  "model": "gpt-4.1-mini-2025-04-14",
  "instructions": "<exact system_instructions loaded from the verified frozen TOML>",
  "input": "<exact deterministic compact JSON for the validated Pydantic request>",
  "text": {
    "format": {
      "type": "json_schema",
      "name": "moving_service_question_response_v1",
      "strict": true,
      "schema": "<mechanically adapted MovingServiceQuestionResponse JSON Schema>"
    }
  },
  "max_output_tokens": 500,
  "temperature": 0,
  "store": false,
  "background": false,
  "stream": false,
  "truncation": "disabled"
}
```

The transport must use the SDK's typed `responses.create` interface, not a raw
or untyped escape hatch. It must not use the SDK's Pydantic parse helper as a
substitute for GoTime validation. The returned text remains untrusted and must
be parsed as exactly one JSON object by the existing adapter, then passed to
`validate_response(request, raw_response)`.

The following request fields are deliberately omitted:

* `tools`, tool choice, web search, file search, and code execution;
* `previous_response_id`, conversation, and continuation state;
* `top_p` and seed;
* metadata and user identifiers;
* prompt-cache keys, cache-retention controls, and cache optimization hints;
* service-tier overrides; and
* any provider prompt, label, fixture ID, log, or general project context.

`temperature: 0` is the lowest selected randomness setting, but must not be
described as deterministic. The immutable snapshot and exact request improve
reproducibility without guaranteeing identical outputs.

## 5. Provider JSON Schema Adaptation

The source of truth is generated at runtime from:

```python
MovingServiceQuestionResponse.model_json_schema()
```

The transport would deep-copy that schema and perform only a reviewed,
deterministic provider adaptation. It must never mutate the source mapping.

| Pydantic schema element | Provider schema treatment |
| --- | --- |
| Root and nested object types | Preserve |
| Every `required` array | Preserve exactly |
| `additionalProperties: false` | Preserve on every object |
| Arrays and item schemas | Preserve |
| String enums | Preserve |
| `$defs` and local `$ref` | Preserve when accepted by the pinned endpoint |
| `const: value` | Convert to the equivalent `enum: [value]` only if required by the documented subset |
| `title` | Remove as a nonsemantic annotation |
| String and array length limits | Preserve with constraints at least as strict as the Pydantic response schema; stop if the provider cannot express them without broadening |

The adaptation must be an allowlisted tree transformation. After adaptation,
an offline invariant check must prove:

* the root is an object;
* every runtime response field and suggestion field is still present and
  required;
* no field, enum member, literal, type, object boundary, length or array limit,
  or `additionalProperties: false` rule was removed or broadened;
* no new field was added; and
* the normalized output is stable for identical input schema bytes.

OpenAI supports only a subset of JSON Schema in strict Structured Outputs.
Removing nonsemantic annotations is mechanical adaptation. Removing or
weakening a required field, type, literal, enum, extra-field prohibition,
length limit, or array limit is not approved, even though runtime Pydantic
validation remains authoritative. Any such incompatibility is a stop
condition, not permission to weaken the response contract.

The exact adapted schema is reviewed and frozen at
`docs/experiments/suggest-moving-service-questions/v1/openai-response-schema.json`
with SHA-256
`9e5a3a667a1049d150734fd16669dad98cc982c2dc7a9a18f3e0b8cb3e891afb`.
Its field review is recorded in `openai-response-schema-review.md`. No API call
is needed to test the transformation itself. If the pinned SDK or endpoint
rejects `$defs`, `$ref`,
single-value enums, or any required object rule, implementation must stop; it
must not weaken the Pydantic response schema.

## 6. Exact Token Preflight

The runner must complete all non-secret authorization, artifact, fixture,
record-path, and budget gates before credential access. The transport would
then call the official `responses.input_tokens.count` interface before
generation.

The count request must contain every input-affecting generation field:

```json
{
  "model": "gpt-4.1-mini-2025-04-14",
  "instructions": "<same exact frozen system instructions>",
  "input": "<same exact deterministic compact request JSON>",
  "text": {
    "format": {
      "type": "json_schema",
      "name": "moving_service_question_response_v1",
      "strict": true,
      "schema": "<same exact adapted schema>"
    }
  },
  "truncation": "disabled"
}
```

The official count interface does not accept generation-only controls such as
`max_output_tokens`, `temperature`, `store`, `background`, or `stream` because
they do not add model input. "Same request" therefore means byte-identical
values for all fields accepted by both interfaces, not adding unsupported
generation controls to the count call.

The returned `input_tokens` value is the provider-specific exact preflight
count. Generation is prohibited when it exceeds 3,000. GoTime must not truncate
the prompt, request, or schema. A count failure fails closed and does not become
a generation attempt or consume a formal generation sequence.

The transport implementation must build one immutable internal payload object
for shared input fields and derive both typed SDK calls from it. Offline tests
must compare the captured count and generation payloads field by field.

## 7. Timeout, Retry, and Cancellation

Token preflight and AI generation have separate bounded deadlines:

```text
token-preflight timeout: 5 seconds
AI-generation timeout: 12 seconds
automatic retries: 0
```

Total elapsed time is measured separately across both operations. Time spent
counting tokens does not reduce the formal 12-second generation allowance.

Proposed sequence:

1. Measure preflight with a monotonic clock and a five-second request timeout.
2. Stop on preflight timeout or failure; do not start generation.
3. After successful preflight and cost gates, start a new monotonic generation
   timer with a 12-second request timeout.
4. Treat generation expiry or the SDK's `APITimeoutError` as
   `AdapterTimeoutError`.
5. Record preflight, generation, and total durations independently.

The SDK client must be constructed with `max_retries=0`. Per-request options
must also preserve zero retries. No runner, adapter, transport, HTTP client, or
provider fallback may retry either request. Streaming and background execution
are disabled, so no background result may arrive after local cancellation.

A local timeout cannot prove that the provider stopped computation or billing
at the same instant. The record must retain the timeout result, and the formal
review must treat any missing provider usage as an operational limitation.

## 8. Response, Refusal, and Failure Handling

The transport accepts output only when the provider response is complete and
contains exactly one assistant output-text value for the requested schema.
That text is passed unchanged to the existing adapter parser.

The transport must reject, without repair or retry:

* provider status `failed`, `incomplete`, `cancelled`, `queued`, or
  `in_progress`;
* a refusal output item;
* missing or multiple output-text values;
* truncation, including an incomplete reason of `max_output_tokens`;
* empty output; and
* malformed JSON or a mapping that fails existing runtime validation.

Bounded generation-error translation is deliberately narrow:

| Provider/SDK condition | GoTime result |
| --- | --- |
| `APITimeoutError` or exhausted shared deadline | `AdapterTimeoutError` |
| `APIConnectionError`, HTTP 429, or HTTP 5xx | `AdapterUnavailableError` |
| HTTP 400, 401, 403, 404, or 422 | Visible configuration/authorization failure; no transient translation |
| Refusal, incomplete output, malformed JSON, or contract rejection | Existing response-validation failure path |
| Unexpected SDK or programming error | Visible failure; do not catch as provider unavailability |

Preflight failure has its own bounded classification and is not an AI-response
schema failure. It writes an audit record, preserves the sequence number, sets
`generation_attempted` and `generation_succeeded` to false, records zero
generation usage and cost, and stops the formal series without retry or
replacement.

The runner may record the existing deterministic fallback outcome after a
failed generation attempt, but the attempt remains failed. The transport and
adapter never choose fallback.

## 9. Usage, Cache, Identity, and Cost Extraction

For a completed response, the transport must extract and bound:

```text
requested AI model identifier
provider-returned AI model identifier
provider request ID
response status
finish or incomplete reason, when present
input_tokens
input_tokens_details.cached_tokens
output_tokens
output_tokens_details.reasoning_tokens, when present
total_tokens
duration_ms
```

Derive:

```text
cached_input_tokens = input_tokens_details.cached_tokens
uncached_input_tokens = input_tokens - cached_input_tokens
cache_status = hit when cached_input_tokens > 0
cache_status = miss when the detail is present and equals 0
cache_status = not_available when the provider omits the detail
```

Negative or internally inconsistent counts fail the record-validation path.
The transport must not infer cached tokens from latency or price.

Frozen planning prices for this AI model are:

```text
uncached input: $0.40 per 1,000,000 tokens
cached input: $0.10 per 1,000,000 tokens
output: $1.60 per 1,000,000 tokens
```

Actual cost is calculated from provider-reported usage categories:

```text
(uncached_input_tokens * 0.40 / 1_000_000)
+ (cached_input_tokens * 0.10 / 1_000_000)
+ (output_tokens * 1.60 / 1_000_000)
```

Preflight authorization must be conservative and assume all exact-count input
tokens are uncached plus the full 500-token output allowance. Prompt caching
is provider-managed only: GoTime sets no cache key or retention hint, does not
reorder the series, and never reuses a prior response. All attempted formal
generation calls remain in the denominator. Caching does not imply output
determinism.

The later record schema must add provider, requested and provider-returned AI
model identifiers, SDK version, provider request ID, preflight and generation
attempt/success flags, preflight/generation/total durations, separate input,
cached-input, uncached-input, and output counts, cache status, finish status,
refusal status, incomplete reason, estimated cost, and usage availability.
Records must still omit prompt text, request JSON, full response content,
trusted state, credentials, and authorization headers.

## 10. Credential Isolation and Client Construction

The only proposed credential variable remains:

```text
GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY
```

The explicit runner enablement variable remains:

```text
GOTIME_MOVING_SERVICE_EVAL_ENABLED
```

These names are design inputs, not authorization to create or read them. A
future runner—not the adapter constructor—would read the evaluation key only
after every non-secret gate succeeds. The key would be passed explicitly to a
capability-specific client instance; the SDK must not implicitly read the
conventional `OPENAI_API_KEY` variable. Backend, frontend, application startup,
and production deployment configuration must never define or inspect either
evaluation variable.

The client must not log request bodies, response bodies, headers, or SDK debug
output. Exception text stored in records must use an allowlisted local error
code, not the raw provider exception message.

## 11. Runner Gates and Call Sequence

Provider transport design does not alter the existing fail-closed runner. A
later implementation would require a new, explicit real-transport mode and all
of these gates before importing or constructing the SDK client:

1. Verify prompt bytes, digest, readiness, and runtime version compatibility.
2. Accept only the two approved synthetic fixtures from committed artifacts.
3. Reject arbitrary state and all other fixtures.
4. Verify run-series identity, sequence, output path, non-overwrite behavior,
   and committed run configuration.
5. Verify separate human authorization for transport implementation,
   credentials, and real-model execution.
6. Verify exact AI model identifier, parameters, SDK version, prices, spending
   limits, and retention assumptions against the approved run configuration.
7. Only then read the capability-specific credential and construct the client.
8. Count input tokens exactly, enforce the 3,000-token and conservative cost
   gates, then make at most one generation request within the shared deadline.
9. Validate the untrusted response through existing runtime code.
10. Write one bounded, non-overwriting record; record deterministic fallback
    metadata separately when applicable.

The fake-only concrete transport check must remain until a later implementation
milestone explicitly replaces it with an allowlist containing exactly the fake
transport and this one capability-specific OpenAI transport. No arbitrary
protocol implementation may pass the execution gate.

## 12. Offline Test Design

Implementation approval would require tests that make no network request and
read no real credential. Inject an SDK-shaped fake client and capture typed-call
arguments.

Required tests include:

* exact generation payload, field omissions, and `store: false`;
* count/generation shared-field equality;
* exact adapted schema snapshot and invariant checks;
* no semantic mutation of the Pydantic response schema;
* preflight over 3,000 tokens blocks generation;
* conservative preflight cost blocks generation when over budget;
* count failure blocks generation, preserves its planned sequence, and does not
  count as an AI-generation attempt;
* separate five-second preflight and 12-second generation deadlines and zero
  retries;
* timeout, unavailable, authentication, refusal, incomplete, and malformed
  response classifications;
* exactly one output-text item accepted;
* provider output remains subject to existing runtime validation;
* cached, uncached, output, and total token extraction and consistency checks;
* provider request ID and returned AI model identifier extraction;
* records omit all prohibited content;
* conventional provider environment variables are never read;
* backend and frontend cannot import or reach the transport; and
* source audit rejects network libraries or provider endpoints outside this
  single capability-specific transport module.

Recorded HTTP fixtures are not required and should not contain real provider
traffic. Reviewed payload snapshots must use synthetic values only.

## 13. Implementation Prerequisites and Blockers

The design is ready for human review, not implementation. Before a separate
implementation authorization, all of the following remain required:

1. Review the dependency-lock change after reconfirming the approved SDK pin's
   availability and Python compatibility.
2. Verify the frozen provider-schema snapshot against the pinned SDK's typed
   Structured Outputs interface without changing it.
3. Amend the provider request/result and local record structures to carry exact
   preflight count, cached and uncached input tokens, provider request ID,
   returned AI model identifier, response status, and usage availability.
4. Implement the approved bounded preflight-failure audit record. The failure
   preserves its planned sequence, stops the series, and is reported separately
   from AI-generation attempts and AI-response failures.
5. Verify the separate five-second preflight and 12-second AI-generation
   deadlines with offline clock and fake-client tests.
6. Preserve and verify the frozen capability-specific run configuration and
   digest before implementation work.
7. Reconfirm AI model availability, official prices, API/SDK behavior, data
   retention, and account eligibility immediately before execution approval.

None of these prerequisites authorizes SDK installation, transport code,
credential access, or execution.

## 14. Decision Requested

Human review has approved:

* the exact Responses API payload;
* the strict-schema mechanical adaptation;
* the separate five-second preflight and 12-second generation deadlines;
* the error mapping;
* usage, cache, identity, and cost extraction;
* the exact SDK pin; and
* the implementation prerequisites.

Current readiness remains:

```text
design ready for human review: no
design approved: yes
provider-transport implementation authorized: no
SDK installation authorized: no
credentials authorized: no
real-model execution authorized: no
```

## 15. Offline Implementation Status

The capability-specific transport is implemented at
`scripts/experiments/suggest_moving_service_questions/openai_transport.py`.
Its experiment dependency is pinned in `requirements-openai.txt`; the reviewed
Python 3.12 resolved set is recorded in `requirements-openai.lock`. The local
installation verified OpenAI SDK version 2.45.0 on Python 3.12.13.

The implementation constructs no SDK client, reads no environment variable or
credential, and exposes no executable entry point. It accepts only an explicitly
injected SDK-shaped client whose automatic retry count is zero. The existing
runner continues to admit only `OfflineFakeMovingServiceTransport`, so the
OpenAI transport is not reachable for network execution.

Implementation completion does not authorize credential access, an API call,
real-model execution, application exposure, or production use.

The proposed next boundary is documented in
`docs/experiments/suggest-moving-service-questions/openai-execution-boundary.md`.
It remains a design for human review and does not alter runner admission or
authorization.
