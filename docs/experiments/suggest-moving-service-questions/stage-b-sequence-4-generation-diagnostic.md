# Stage B Sequence 4 Generation Diagnostic

## Status and scope

Research date: 2026-08-01

This is an offline diagnostic for the consumed sequence 4 attempt in
`moving-service-stage-b-pilot-20260801`. Repository authorization remains
closed. No credential was read and no OpenAI request was made during this
diagnostic.

Decision: **no-go for another Stage B sequence until the bounded exception
mapping is reviewed and committed and the project key's Responses-generation
permission is reconfirmed.** The evidence does not justify changing the
12-second generation timeout.

The OpenAI Developer Docs MCP source was restored in user-level Codex
configuration, but the running session required a restart before exposing its
tools. Current claims below were therefore checked through read-only fallback
access restricted to official OpenAI documentation.

## Bounded sequence-4 evidence

The bounded audit and closure records report:

| Field | Safe recorded value |
| --- | --- |
| Credential value obtained | `true` |
| Client construction succeeded | `true` |
| Token preflight attempted / succeeded | `true` / `true` |
| Exact input tokens | `2176` |
| Preflight duration | `1573.2412109937286` ms |
| Conservative preflight cost | `0.0016704` |
| Generation attempted / succeeded | `true` / `false` |
| Generation duration | `8667.128724991926` ms |
| Failure | `generation_unavailable` at `generation` |
| Provider request ID | unavailable |
| Generation token usage | unavailable |
| Recorded generation cost | `$0.00` |
| Response evidence | not created |
| Closure | closed and verified, reason `bounded_failure` |

The records contain no credential, authorization header, system instructions,
serialized request, trusted-state payload, provider response body, or raw
exception text. Because the old classification discarded the typed exception
and safe HTTP status, the record cannot distinguish the concrete cause further.

## Exact generation request review

The pinned `openai==2.45.0` SDK signature was inspected offline. The transport
constructs this call:

```python
client.responses.create(
    model="gpt-4.1-mini-2025-04-14",
    instructions=verified_system_instructions,
    input=deterministic_compact_request_json,
    text={
        "format": {
            "type": "json_schema",
            "name": "moving_service_question_response_v1",
            "strict": True,
            "schema": frozen_provider_schema,
        }
    },
    truncation="disabled",
    max_output_tokens=500,
    temperature=0,
    store=False,
    background=False,
    stream=False,
    timeout=12.0,
)
```

Field review:

| Requirement | Construction and finding |
| --- | --- |
| AI model identifier | Exact frozen dated identifier is supplied. |
| System instructions | Exact verified TOML text is supplied through `instructions`. |
| Request JSON | Deterministic compact JSON is supplied as the single `input` string. |
| Structured output | `text.format` uses the frozen schema with `type=json_schema` and `strict=true`. |
| Temperature | Explicitly `0`. |
| Output ceiling | Explicitly `500`. |
| Storage | Explicitly `store=false`. |
| Streaming/background | Both explicitly false. |
| Tools | The `tools` argument is omitted. No tool is configured; this matches the frozen `tools_enabled=false` setting. |
| Truncation | Explicitly disabled, so an oversized input fails instead of being truncated. |
| Timeout | Per-generation SDK timeout is `12.0` seconds. |
| Retries | The separately verified client is constructed with `max_retries=0`; request code performs no retry. |

The current Responses API reference documents `instructions`, string `input`,
`text.format` JSON Schema output, `max_output_tokens`, `temperature`, `store`,
`background`, `stream`, `tools`, and `truncation`. The Structured Outputs guide
documents strict JSON Schema output, and the input-token endpoint accepts the
same model, instructions, input, text, tools, and truncation context. The
request shape therefore has no identified field-level incompatibility with the
current official API or pinned SDK. See the official [Responses input-token
reference](https://developers.openai.com/api/reference/resources/responses/subresources/input_tokens/methods/count)
and [Structured Outputs guide](https://developers.openai.com/api/docs/guides/structured-outputs).

## Exception mapping diagnosis

Before this diagnostic, the transport translated only:

| SDK failure | Old bounded result |
| --- | --- |
| `APITimeoutError` | `generation_timeout` |
| `APIConnectionError` other than timeout | `generation_unavailable` |
| `RateLimitError` / HTTP 429 | `generation_unavailable` |
| `APIStatusError` HTTP 5xx | `generation_unavailable` |

Authentication (401), permission (403), not-found/model access (404), malformed
request (400), conflict (409), and unprocessable request (422) were not
classified as unavailable; they escaped the transport and became an unexpected
post-reservation runner failure. Refusal, incomplete output, malformed JSON,
provider-envelope/schema failure, Pydantic failure, and GoTime semantic failure
already have distinct post-response paths.

The sequence-4 result therefore rules out the local timeout classifier and does
not directly indicate authentication, permission, model access, or invalid
request. Its concrete old-classification candidates are connection failure,
rate limiting/429 (including provider spend/rate categories represented as
429), or provider 5xx. OpenAI's official [API error guide](https://developers.openai.com/api/docs/guides/error-codes)
documents the corresponding Python SDK exception types and distinguishes
connection, timeout, authentication, bad request, permission, not found, rate
limit, unprocessable entity, and internal server failures.

## Narrow offline reconciliation

The capability transport now maps typed SDK errors to:

| SDK exception/status | Bounded generation classification |
| --- | --- |
| `AuthenticationError` / 401 | `generation_authentication_failed` |
| `PermissionDeniedError` / 403 | `generation_permission_denied` |
| `NotFoundError` / 404 | `generation_model_unavailable` |
| `RateLimitError` / 429 | `generation_rate_limited` |
| `BadRequestError` / 400 | `generation_invalid_request` |
| `ConflictError` / 409 | `generation_invalid_request` |
| `UnprocessableEntityError` / 422 | `generation_invalid_request` |
| `APIConnectionError` | `generation_connection_failed` |
| `InternalServerError` / 5xx | `generation_provider_unavailable` |
| `APITimeoutError` | `generation_timeout` |

The fixed endpoint and dated AI model make `model_unavailable` a useful bounded
name for a 404, but it remains an inference: a 404 proves that the requested
resource was unavailable, not why. Future failure records may retain only a
bounded HTTP status and bounded provider request ID when the typed SDK exception
supplies them. Raw exception text, bodies, headers, and request content remain
prohibited. Unknown programming errors still remain visible and become the
existing bounded unexpected-failure tombstone.

Offline fake-exception tests cover every classification, confirm zero retries,
and verify safe request-ID/status capture without retaining exception content.

## Permission finding

OpenAI documents restricted user-key permissions as resource/endpoint-specific
choices that may include None, Read, Write, or request-specific scopes; the
available choices vary by resource. See [Assign API Key Permissions](https://help.openai.com/en/articles/8867743-assign-api-key-permissions).

The successful authenticated `/v1/responses/input_tokens` call proves that the
sequence-4 key could reach that endpoint for this payload. It does **not** prove
that the same restricted key had permission to call `POST /v1/responses`.
Official public documentation does not define a portable single permission
label guaranteed to cover both operations. Before another sequence, a human
must reconfirm in the dedicated project that the restricted key has the
narrowest available Responses write/request permission covering both
`/v1/responses/input_tokens` and `/v1/responses`, while unrelated endpoint
permissions remain disabled. No repository code can verify that private
control without making a request.

## Timeout finding

The observed generation ended after about 8.67 seconds and was classified as
unavailable, not timeout. The SDK raises `APITimeoutError` separately, and the
transport checks it before its superclass `APIConnectionError`. This record
therefore provides no evidence that the 12-second generation timeout caused
sequence 4. Keep the frozen timeout unchanged. Reconsider it only after a
separately reviewed protocol decision supported by an actual timeout record or
repeatable offline timing evidence.

## Go/no-go

Current decision: **no-go** for a new live Stage B authorization package.

Repository-side prerequisites:

1. review and commit the bounded exception mapping and fake-exception tests;
2. run the full offline/backend test suite and safety checks;
3. verify closed authorization and unchanged frozen artifact digests.

Private-account prerequisite:

1. human reconfirmation that the restricted project key permits both exact
   Responses operations and that the dated AI model remains enabled.

After those checks pass, another single-use Stage B sequence may be proposed
for separate review. This diagnostic does not authorize that proposal or any
request.
