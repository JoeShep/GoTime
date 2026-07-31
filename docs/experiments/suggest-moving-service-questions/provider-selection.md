# Provider Selection Research — Suggest Moving-Service Questions

## 1. Status and Scope

```text
capability: suggest_moving_service_questions
research_date: 2026-07-30
provider research complete: yes
provider selected provisionally: yes
model selected provisionally: yes
provider-transport design authorized: yes
provider-transport implementation authorized: no
credentials authorized: no
real-model execution authorized: no
production use authorized: no
```

This document records a current, first-party-source comparison for the
controlled real-model evaluation. It is capability-specific research, not a
general provider strategy. It does not authorize a transport implementation,
credential access, or a model call.

OpenAI GPT-4.1 mini is provisionally selected for provider-transport design
because it meets the contract, identity, exact-counting, cost, and bounded
implementation requirements. The evaluation protocol now permits unavoidable
provider-managed automatic prompt caching when a selected provider offers no
documented disable control. This does not permit GoTime to create or optimize
cache keys or prefixes, cache model responses, or reuse a response instead of
making one of the twenty formal calls.

Anthropic Claude Haiku 4.5 remains the fallback candidate, but it is not
currently eligible because Anthropic describes its preflight token count as an
estimate rather than exact.

## 2. Frozen Experiment Requirements

The provider must preserve these frozen constraints:

```text
prompt artifact: docs/experiments/suggest-moving-service-questions/v1/real-model-prompt.toml
prompt version: moving-service-questions-prompt-v1
prompt SHA-256: 583a4bdf59c4c4ac67c82928415710c3d5c21ac9912ebd4888a026b8fd4acbf2
request schema: moving-service-questions-schema-v1
response schema: moving-service-questions-schema-v1
knowledge fixture: moving-service-storage-fixture-v2
maximum input tokens: 3,000
maximum output tokens: 500
timeout: 12 seconds
automatic retries: 0
formal calls: 20
formal caching: no application-managed caching or response reuse;
  unavoidable provider-managed automatic prompt caching permitted
live research and tools: prohibited
```

The provider must receive the exact frozen system instructions, deterministic
compact request JSON, and a mechanically adapted schema derived from
`MovingServiceQuestionResponse.model_json_schema()`. Runtime validation remains
authoritative.

## 3. Official-Source Research Method

Only official provider documentation, official API references, official
pricing pages, official privacy documentation, and official SDK repositories
were used. The research date is 2026-07-30. No provider account, credential,
token-count request, or generation request was used.

The OpenAI Developer Docs MCP was installed at user scope from the official
endpoint `https://developers.openai.com/mcp`. It added an enabled
`openaiDeveloperDocs` streamable-HTTP entry to the user Codex configuration,
with no bearer-token environment variable or custom headers. It did not change
the repository or add a model API credential. Because newly installed MCP tools
were not exposed to the already-running session, current OpenAI documentation
was read directly from official OpenAI documentation pages.

### Source record

| Source | Provider | Relevant claim | Authoritative | Uncertainty |
| --- | --- | --- | --- | --- |
| [GPT-4.1 mini model](https://developers.openai.com/api/docs/models/gpt-4.1-mini) | OpenAI | Snapshot ID, pricing, limits, endpoints, structured output | Yes | Availability must be reconfirmed before approval |
| [Structured model outputs](https://developers.openai.com/api/docs/guides/structured-outputs) | OpenAI | Strict JSON Schema subset and refusal handling | Yes | Generated schema still needs a no-call compatibility test |
| [Counting tokens](https://developers.openai.com/api/docs/guides/token-counting) | OpenAI | Exact server-side preflight count, including request structure and schemas | Yes | Counting is a separate authenticated network request |
| [Prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching) | OpenAI | Automatic caching on GPT-4o and newer models | Yes | No GPT-4.1 disable control is documented |
| [Data controls](https://developers.openai.com/api/docs/guides/your-data) | OpenAI | No training by default; default abuse-monitoring retention up to 30 days | Yes | ZDR and modified monitoring require approval |
| [OpenAI Python SDK](https://github.com/openai/openai-python) | OpenAI | Two default retries; `max_retries=0`; configurable timeout | Yes | Exact installed-version behavior must be frozen later |
| [Claude models overview](https://platform.claude.com/docs/en/about-claude/models/overview) | Anthropic | Dated Haiku ID, pricing, context, output limit | Yes | Availability must be reconfirmed before approval |
| [Claude structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) | Anthropic | JSON Schema constraints, Pydantic support, refusal/truncation behavior | Yes | Provider adds a system prompt and grammar compilation |
| [Claude token counting](https://platform.claude.com/docs/en/build-with-claude/token-counting) | Anthropic | Free preflight endpoint; count is an estimate | Yes | Estimate can differ slightly from actual input usage |
| [Claude model deprecations](https://platform.claude.com/docs/en/about-claude/model-deprecations) | Anthropic | At least 60 days' retirement notice | Yes | A dated ID can still be retired |
| [Claude prompt caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching) | Anthropic | Caching is enabled by adding `cache_control`; prices and usage categories | Yes | Structured-output grammar caching is separate |
| [Claude API and data retention](https://platform.claude.com/docs/en/manage-claude/api-and-data-retention) | Anthropic | ZDR eligibility and structured-output schema caching | Yes | ZDR depends on the account arrangement |
| [Anthropic commercial retention](https://privacy.anthropic.com/en/articles/7996866-how-long-do-you-store-my-organization-s-data) | Anthropic | Standard API input/output deletion within 30 days | Yes | Safety/legal exceptions apply |
| [Gemini 2.5 Flash](https://ai.google.dev/gemini-api/docs/models/gemini-2.5-flash) | Google | Stable alias, limits, supported structured output | Yes | No dated immutable Gemini API ID is documented |
| [Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing) | Google | Paid-tier token prices and no training for paid use | Yes | Pricing must be frozen before a run |
| [Gemini structured outputs](https://ai.google.dev/gemini-api/docs/structured-output) | Google | Supported JSON Schema subset and Pydantic input | Yes | Generated schema needs mechanical adaptation |
| [Gemini token counting](https://ai.google.dev/gemini-api/docs/tokens) | Google | Preflight `countTokens` and response usage categories | Yes | Counting requires an API request |
| [Gemini context caching](https://ai.google.dev/gemini-api/docs/generate-content/caching) | Google | Implicit caching is automatic for Gemini 2.5 and newer | Yes | No disable control is documented |
| [Gemini logs and datasets](https://ai.google.dev/gemini-api/docs/logs-datasets) | Google | GenerateContent is not stored by default; optional logs retain 7–55 days | Yes | Project-level settings must be verified |
| [Google Gen AI Python SDK](https://github.com/googleapis/python-genai) | Google | Uses `httpx`; API version and HTTP options are configurable | Yes | Retry semantics are not sufficiently explicit for selection |

## 4. Candidate Comparison

Scores use 0 (does not meet), 1 (material concern), or 2 (meets). A high score
does not override a frozen stop condition.

| Criterion | OpenAI GPT-4.1 mini snapshot | Anthropic Claude Haiku 4.5 snapshot | Google Gemini 2.5 Flash |
| --- | ---: | ---: | ---: |
| Structured-output fit | 2 | 2 | 1 |
| Immutable identity | 2 | 2 | 0 |
| Exact preflight count | 2 | 0 | 1 |
| Lowest randomness control | 2 | 2 | 2 |
| Cost ceilings | 2 | 2 | 2 |
| 12-second timeout / zero retries | 2 | 2 | 1 |
| Usage reporting | 2 | 2 | 2 |
| Caching protocol fit | 2 | 2 | 1 |
| Clear standard data terms | 2 | 2 | 2 |
| Narrow transport simplicity | 2 | 2 | 1 |
| **Total / 20** | **20** | **18** | **13** |
| **Status** | Provisionally selected | Ineligible fallback | Not selected |

## 5. Structured-Output Compatibility

The runtime schema contains:

* a root object and one nested object;
* required fields at both levels;
* `additionalProperties: false`;
* arrays with item types and length constraints;
* string enums;
* boolean and string constants;
* local `$defs` and `$ref` references; and
* string-length and array-length constraints.

### OpenAI

GPT-4.1 mini supports Structured Outputs. OpenAI requires strict schemas to
use supported JSON Schema features and forbids extra properties. Refusal or
incomplete output remains possible and must be treated as a failed attempt.

A later transport would need a reviewed mechanical normalization step:

* retain the same object hierarchy, required fields, enums, arrays, and
  `additionalProperties: false`;
* convert unsupported `const` forms to equivalent single-value enums if the
  provider endpoint requires it;
* inline or preserve `$defs` and `$ref` according to the endpoint subset; and
* remove only provider-unsupported annotations or length keywords.

Runtime validation must continue to enforce every original constraint.
Removing a generation-only annotation is mechanical adaptation; changing a
field, type, required status, enum value, or runtime validator is semantic and
out of scope.

### Anthropic

Claude Haiku 4.5 supports `output_config.format` with `type: "json_schema"`.
Anthropic documents Pydantic helpers and constrained decoding. Refusals use
`stop_reason: "refusal"` and may violate the schema; truncation uses
`stop_reason: "max_tokens"` and may return incomplete JSON. Neither condition
may be retried in the formal series.

The same mechanical normalization review is required. Anthropic also injects
an output-format system prompt, increasing the provider-side input count, and
caches the compiled schema grammar for up to 24 hours. That grammar cache is
not prompt-content caching, but it must be disclosed in the run configuration.

### Google

Gemini supports objects, arrays, strings, booleans, nulls, enums, required
properties, and `additionalProperties`, but only a documented JSON Schema
subset. It can accept Pydantic-derived schemas through the official SDK.
Compatibility is plausible but less certain without a provider-schema
validation request. No semantic runtime change is justified.

## 6. Model-Version Reproducibility

* OpenAI offers the dated snapshot `gpt-4.1-mini-2025-04-14`; the floating
  alias is `gpt-4.1-mini`. The dated snapshot is acceptable for formal identity.
* Anthropic offers the dated Claude API ID
  `claude-haiku-4-5-20251001` and alias `claude-haiku-4-5`. Anthropic promises
  at least 60 days' notice before retirement of publicly released models.
* Google documents `gemini-2.5-flash` as the stable model code, not a dated
  immutable Gemini Developer API identifier. That is a reproducibility blocker.

Every later record must capture both the requested identifier and the model
identifier returned by the provider.

## 7. Token-Counting Comparison

| Candidate | Preflight method | Local | Exact for provider request | Cost |
| --- | --- | ---: | ---: | ---: |
| OpenAI | `POST /v1/responses/input_tokens` with the generation payload | No | Yes, per official documentation | No separate price documented |
| Anthropic | `POST /v1/messages/count_tokens` | No | No; officially an estimate | Free |
| Google | `countTokens` with request input | No | Not described as exact | No separate price documented |

OpenAI says its endpoint returns the exact count the model receives, including
request structure, role boundaries, tools, and schemas. This satisfies the
formal preflight requirement, but it is a separate authenticated network call.
It must occur after all non-secret gates and before generation. A failed count
must fail closed and must not consume a formal generation sequence.

Anthropic accepts the same structured inputs as message creation, but says the
result can differ slightly from actual usage. It also documents token counting
with structured outputs “without compilation,” while structured output adds an
injected prompt. That does not meet GoTime's current exact-count requirement.

No local tokenizer is sufficient for any candidate because provider-injected
structure and schemas contribute tokens.

## 8. Randomness and Proposed Parameters

No provider guarantees identical output for identical inputs. The formal
series is intended to measure this variation.

Provisionally selected OpenAI parameters:

```text
model: gpt-4.1-mini-2025-04-14
temperature: 0
top_p: omitted
seed: omitted
maximum output tokens: 500
streaming: false
tools: none
background execution: false
store: false
structured output: strict JSON Schema
timeout: 12 seconds
automatic retries: 0
prompt caching: provider-managed automatic behavior only
application cache keys or prefix optimization: prohibited
response reuse: prohibited
```

Conditional Anthropic fallback parameters:

```text
model: claude-haiku-4-5-20251001
anthropic-version: 2023-06-01
temperature: 0
top_p: omitted
top_k: omitted
seed: unsupported / omitted
maximum output tokens: 500
streaming: false
tools: none
thinking: omitted
cache_control: omitted
structured output: output_config.format json_schema
timeout: 12 seconds
automatic retries: 0
```

Gemini 2.5 Flash exposes temperature and seed in current generation
configuration, but this does not cure its identity and caching blockers.

## 9. Cost Calculations

Planning calculations use the latest repository estimates:

```text
storage_unknown input: 2,163 tokens
complete input: 2,113 tokens
output assumption for both: full 500-token ceiling
```

These are conservative character-based planning estimates, not acceptable
formal preflight counts. The headline calculations use uncached input pricing
to remain conservative. Formal cost records must instead separate
provider-reported cached input from uncached input.

| Candidate | Input / MTok | Cached input / MTok | Output / MTok | Storage call | Complete call | 10 storage | 10 complete | 20-call series | Hard call (3,000 + 500) | Hard 20 calls |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| OpenAI GPT-4.1 mini | $0.40 | $0.10 | $1.60 | $0.0016652 | $0.0016452 | $0.016652 | $0.016452 | $0.033104 | $0.002000 | $0.040000 |
| Anthropic Haiku 4.5 | $1.00 | $0.10 | $5.00 | $0.004663 | $0.004613 | $0.046630 | $0.046130 | $0.092760 | $0.005500 | $0.110000 |
| Gemini 2.5 Flash | $0.30 | $0.03 | $2.50 | $0.0018989 | $0.0018839 | $0.018989 | $0.018839 | $0.037828 | $0.002150 | $0.043000 |

Example OpenAI storage arithmetic:

```text
(2,163 × $0.40 / 1,000,000) + (500 × $1.60 / 1,000,000)
= $0.0008652 + $0.0008000
= $0.0016652
```

All candidates meet the $0.01 target per call, $0.03 hard per call, $0.20
target series, $0.60 hard series, and $10 monthly ceiling under these bounds.
There is no request or platform fee documented for these plain text calls.
Tools, search, batch, priority, and background processing must remain absent.

## 10. Timeout, Cancellation, and Retry Behavior

The OpenAI Python SDK defaults to two retries for connection errors, 408, 409,
429, and server errors, and defaults to a ten-minute timeout. It supports
`max_retries=0`, a float or `httpx.Timeout`, and reports
`APITimeoutError`. A later implementation would have to set both values
explicitly and use a non-streaming request.

The official Anthropic SDK follows the same Stainless client pattern and
supports explicit retry and timeout configuration, but exact behavior must be
confirmed against the frozen SDK version before implementation approval.
Provider overload and 5xx errors map to unavailable; the local 12-second
deadline maps to timeout. No provider error may trigger a replacement call.

Google's SDK exposes HTTP options, but current official material does not state
retry defaults clearly enough for selection. Direct HTTP could avoid hidden
retries, but does not solve the identity or caching blockers.

The 12-second boundary should cover DNS/connect, request write, response read,
and parsing. A local monotonic deadline remains authoritative. Cancellation is
best-effort at the HTTP layer; a timed-out request may still be processed and
billed by the provider, so the record must remain a failed attempt.

## 11. Usage and Cache Reporting

OpenAI responses report input and output usage, cached input tokens, model
identity, request identity, and completion status. Prompt caching is automatic
for eligible GPT-4o-and-newer requests and GPT-4.1 offers no documented disable
switch. Under the amended protocol, this provider-managed behavior is
permitted but not controlled or optimized by GoTime. Every record must capture
the reported cached-token count and cache status. A missing or undocumented
cache signal is an evaluation limitation, not permission to infer a hit or
miss. Caching must not be described as making output deterministic.

Anthropic reports `input_tokens`, `output_tokens`,
`cache_creation_input_tokens`, and `cache_read_input_tokens`, plus response ID,
model, and `stop_reason`. Prompt caching is opt-in through `cache_control`, so
omitting it keeps prompt-content caching off. Structured-output grammar caching
still occurs for up to 24 hours.

Gemini reports input, output, thought, cached, tool-use, and total tokens.
Implicit caching is automatically enabled for Gemini 2.5 and newer, with no
documented off switch.

## 12. Credential Isolation

For the provisionally selected OpenAI design, use:

```text
GOTIME_MOVING_SERVICE_EVAL_ENABLED
GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY
GOTIME_MOVING_SERVICE_EVAL_MODEL
```

Do not use `OPENAI_API_KEY`, because the official SDK may read that conventional
name implicitly. The runner must read the GoTime-specific key only after prompt
digest, manifest, fixture, schema, token-budget, run-series, output-path, spend,
and explicit authorization gates pass. Pass the key explicitly to the
provider-specific client. Never log it or an authorization header.

Do not define these variables in Git, `.env` files, backend/frontend startup,
Docker Compose, hosting configuration, or production configuration.

## 13. Data Handling and Retention

OpenAI states that API data is not used to train models by default unless the
customer opts in. Default abuse-monitoring logs may contain prompts and
responses and are retained for up to 30 days. Zero Data Retention and Modified
Abuse Monitoring require prior approval and additional requirements. The
planning assumption must therefore be standard retention of up to 30 days,
not ZDR.

Anthropic states that standard API inputs and outputs are deleted within 30
days, subject to safety and legal exceptions. Its structured-output feature is
ZDR-eligible, but GoTime must not assume the account has a ZDR arrangement.
Anthropic temporarily caches the JSON schema for up to 24 hours.

Google's paid tier states that prompts and responses are not used to improve
products. GenerateContent does not store requests by default; optional project
logging can retain data for 7, 14, 28, or 55 days. A later preflight would have
to verify paid-tier use and logging disabled.

All formal fixtures are synthetic. Even so, no conversation history, full goal
history, credentials, or live personal information may be sent.

## 14. SDK Versus HTTP Comparison

| Approach | Dependency | Timeout/retry control | Structured output and usage | Mocking | Hidden behavior / maintenance |
| --- | --- | --- | --- | --- | --- |
| Official Python SDK | New provider dependency | Strong when explicitly configured | Best typed support | Good behind existing seam | Default retries/env behavior must be overridden |
| Direct HTTP with an existing client | No new dependency only if already direct | Strong | Manual mapping and schema payload | Excellent | Provider contract maintenance moves into GoTime |
| Standard-library HTTP | None | Basic | Entire mapping is manual | Good | TLS, errors, cancellation, and testing burden highest |

Provisional recommendation: use the official OpenAI Python SDK in one
capability-specific transport, pinned and reviewed, with the API key passed
explicitly, `max_retries=0`, a 12-second timeout, non-streaming Responses API,
and no tools. The SDK is preferable here because it exposes the exact token
count endpoint, structured-output request types, usage fields, and typed
errors. It must remain behind the existing capability-specific seam; no
provider registry or generic client should be introduced.

This is a transport-design recommendation only. Installation and
implementation are not authorized.

## 15. Provisional Provider Selection

```text
provider: OpenAI
model: gpt-4.1-mini-2025-04-14
selection status: provisional; approved for provider-transport design only
provider-transport implementation authorized: no
real-model execution authorized: no
```

Why it is provisionally selected:

* immutable snapshot identity;
* strict structured output;
* exact preflight token count for the full Responses payload;
* cost far below every ceiling;
* explicit timeout and zero-retry controls;
* detailed usage and error reporting; and
* a small capability-specific official SDK integration path;
* provider-reported cached-token usage that can be recorded and priced.

The protocol amendment permits only OpenAI's unavoidable provider-managed
automatic caching. GoTime must not set or optimize cache keys, rearrange the
frozen prompt or request to affect cache reuse, change run order to influence
reuse, or reuse a previously generated response.

## 16. Fallback Candidate

```text
provider: Anthropic
model: claude-haiku-4-5-20251001
selection status: blocked; not selected
reason: official preflight token count is an estimate, not exact
```

Anthropic is otherwise a strong fit: immutable ID, schema-constrained output,
opt-in prompt caching, low cost, clear usage fields, and standard 30-day
retention. It becomes eligible only if Anthropic documents an exact full-payload
preflight count or GoTime explicitly revises the exact-count prerequisite in a
separately reviewed protocol change.

Gemini 2.5 Flash is not the fallback because it combines a floating stable
identifier with automatic implicit caching.

## 17. Proposed Frozen Pricing Rule

Before any implementation or run approval, create a reviewed,
capability-specific run configuration that records:

```text
provider
immutable model identifier
pricing effective date
uncached input price per 1M tokens
cached input price per 1M tokens
output price per 1M tokens
request or platform fee
token-counting fee
maximum output tokens
maximum authorized formal-series spend: $0.60
monthly evaluation ceiling: $10.00
```

For OpenAI GPT-4.1 mini, freeze:

```text
pricing effective date: 2026-07-30
uncached input: $0.40 per 1M tokens
cached input: $0.10 per 1M tokens
output: $1.60 per 1M tokens
```

Before generation, the runner must calculate the conservative worst-case call
cost from the exact provider preflight input count at the uncached rate plus
the 500-token output ceiling. After an attempted call, actual cost must use
provider-reported categories:

```text
uncached_input_tokens = input_tokens - cached_input_tokens
actual_cost =
  (uncached_input_tokens × uncached_input_price)
  + (cached_input_tokens × cached_input_price)
  + (output_tokens × output_price)
```

Current live pricing must not be fetched during the formal run. A price change
requires review of the frozen run configuration, not an automatic update.

## 18. Local Record Retention

Proposed policy:

* retain bounded local call records through human review and for 30 days after
  the evaluation decision;
* retain the reviewed aggregate report in Git;
* retain raw structured response evidence only with separate approval;
* delete expired local call records by explicitly removing the approved
  run-series directory after confirming the aggregate report is complete; and
* never retain prompts, serialized requests, credentials, authorization
  headers, full trusted state, conversation history, or raw user answers.

Deletion should be a reviewed manual step recorded in the evaluation notes.
No background cleanup job is warranted.

## 19. Known Risks and Unresolved Questions

Required before implementation approval:

1. Validate the mechanically adapted response schema without changing runtime
   semantics.
2. Confirm the selected model remains active and the exact prices remain
   current.
3. Freeze the provider API version and SDK version.
4. Verify the chosen SDK's retry, timeout, proxy, and environment-variable
   behavior from its pinned source.
5. Authorize the authenticated token-count request separately and specify how
   it is recorded without consuming a formal generation call.
6. Confirm the exact Responses API structured-output parameter names supported
   by the pinned SDK version.
7. Confirm the provider account's retention controls and organization/project
   logging settings.
8. Specify how provider-reported automatic cache usage and missing cache
   reporting map into the evaluation record.
9. Add distinct `cached_input_tokens` and `uncached_input_tokens` record fields.
10. Obtain separate approval before installing or implementing the transport.

## 20. Implementation and Execution Prerequisites

Implementation prerequisites:

* the provisional provider/model decision recorded here;
* approval of one capability-specific transport milestone;
* reviewed schema adaptation;
* frozen parameters, pricing, API version, and SDK version; and
* tests proving zero retries, 12-second timeout, explicit credential passing,
  and no application/frontend reachability.

Execution prerequisites:

* separate explicit real-model execution authorization;
* frozen-for-execution prompt and manifest state;
* approved evaluation-only credential and paid project;
* exact provider preflight count for each request;
* approved run-series identity, ordering, and spend;
* confirmed data-retention settings;
* an ignored, empty, non-overwriting record directory; and
* no unresolved protocol or contract mismatch.

## 21. Decision Record and Approval Status

```text
research conclusion: provider/model provisionally selected for transport design
provider selected provisionally: OpenAI
model selected provisionally: gpt-4.1-mini-2025-04-14
fallback candidate: Anthropic / claude-haiku-4-5-20251001
provider-transport design authorized: yes
provider-transport implementation authorized: no
credentials authorized: no
real-model execution authorized: no
production use authorized: no
```

The next milestone may design the provider-specific transport against this
selection and the amended cache-observation rule. It may not install the SDK,
implement the transport, access credentials, or call the model without
separate authorization. No frozen prompt or runtime contract change is needed.
