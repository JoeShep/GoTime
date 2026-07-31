# OpenAI Credential and Execution Boundary — Suggest Moving-Service Questions

## 1. Status and Scope

```text
capability: suggest_moving_service_questions
design date: 2026-07-31
credential-boundary implementation: offline tested
real-client construction boundary: offline tested with fake constructors
credential access authorized: false
network preflight authorized: false
AI-generation execution authorized: false
production use authorized: false
```

This document defines the boundary around the existing script-only OpenAI
transport. The capability-specific credential wrapper, validator, and client
factory now exist, but the only public environment-to-client entry point first
verifies the exact repository authorization artifact. Because that artifact
denies credential access, the entry point stops before inspecting its supplied
environment or invoking a constructor. No runner admission or network request
is enabled.

The current runner remains network-incapable and admits only
`OfflineFakeMovingServiceTransport`. The implemented OpenAI transport accepts
an injected client. The new client boundary is not imported by the runner,
backend, or frontend. Its internal credential and constructor seams are tested
only with explicit synthetic mappings and fake constructors; no SDK resource
method is invoked.

The separate `run_openai_control_path_dry_run.py` harness connects those seams
end to end without changing runner admission. It first proves that the exact
repository authorization is closed, then uses only its own fixed synthetic
environment, concrete in-memory client constructors, and fake Responses API
resources. This is simulation evidence, not credential, token-preflight,
generation, or formal-evaluation authority. The harness has no command-line
entry point and rejects subclasses or caller-provided environment mappings and
constructors.

## 2. Frozen Inputs

Any future integration must verify these exact artifacts before credential
access:

```text
prompt path: docs/experiments/suggest-moving-service-questions/v1/real-model-prompt.toml
prompt SHA-256: 583a4bdf59c4c4ac67c82928415710c3d5c21ac9912ebd4888a026b8fd4acbf2
run configuration path: docs/experiments/suggest-moving-service-questions/v1/openai-run-configuration.toml
run configuration SHA-256: e665e04b56d8aeaa01f4c9df2fd2f5f4eed37150802fdba869cba54d1e5bc782
provider schema path: docs/experiments/suggest-moving-service-questions/v1/openai-response-schema.json
provider schema SHA-256: 9e5a3a667a1049d150734fd16669dad98cc982c2dc7a9a18f3e0b8cb3e891afb
OpenAI SDK: openai==2.45.0
AI model identifier: gpt-4.1-mini-2025-04-14
```

The frozen prompt, Pydantic request schema, Pydantic response schema, provider
schema snapshot, model parameters, prices, fixture order, and fallback behavior
must not be changed by credential or client integration.

## 3. Authorization Layers

Authorization must be additive and explicit. Passing one layer does not imply
the next.

| Layer | Current state | Permits |
| --- | --- | --- |
| Offline artifacts and fake-client tests | Complete | Local validation only |
| Credential-boundary implementation | Not authorized | Code that can read one evaluation credential |
| Credential availability | Not authorized | Reading the evaluation credential for one approved run |
| Token-preflight network request | Not authorized | One exact input-token count request |
| AI-generation request | Not authorized | One bounded Responses API generation |
| Formal 20-slot series | Not authorized | The reviewed fixed run series |
| Application or production integration | Prohibited | Nothing in this evaluation may enable it |

Neither an environment variable nor a command-line option may grant authority
by itself. A future runner must require a reviewed repository authorization
record in addition to explicit operator intent. Credential access and network
execution require separate approvals because exact token counting is itself an
authenticated network operation.

## 4. Credential Boundary

The only permitted API credential name is:

```text
GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY
```

The only permitted operator enablement name is:

```text
GOTIME_MOVING_SERVICE_EVAL_ENABLED
```

The enablement value is intent, not authority. It must be ignored unless all
committed authorization and artifact gates pass.

The capability-specific credential reader:

1. Live under `scripts/experiments/suggest_moving_service_questions/`.
2. Be imported lazily only after every non-secret gate passes.
3. Read exactly one named key from an explicitly supplied environment mapping.
4. Reject a missing, blank, multiline, or unreasonably long value.
5. Return a non-serializable, redacted credential wrapper whose representation
   never contains the value.
6. Never write, hash, compare, print, log, persist, or include the value in an
   exception.
7. Never place the value in a dataclass converted with `asdict`, an evaluation
   record, request payload snapshot, test fixture, or command-line argument.
8. Keep the value in memory only for client construction and release references
   when the run process exits.

The normal backend, frontend, Docker Compose services, production deployment,
tests, and application startup must never define or inspect this name.

### Conventional OpenAI environment variables

Pinned SDK source confirms that omitting constructor arguments can trigger
implicit reads of conventional OpenAI variables, including `OPENAI_API_KEY`,
`OPENAI_ADMIN_KEY`, `OPENAI_ORG_ID`, `OPENAI_PROJECT_ID`, and
`OPENAI_WEBHOOK_SECRET`. The pinned source also checks `OPENAI_BASE_URL`.

The future runner must fail closed if any of those names is present. It must
not use them, copy them, unset them temporarily, or allow the SDK to infer
configuration from them. This protects the evaluation from accidentally using
another developer or application credential.

No credential-presence check is allowed during the current dry-run milestone.

## 5. Real-Client Factory Boundary

The capability-specific client factory lives beside the transport at:

```text
scripts/experiments/suggest_moving_service_questions/openai_client_factory.py
```

Its public entry point is deliberately stricter than a bare constructor: it
requires the runner's exact ordered non-secret gate result and explicit
operator-intent result, then independently verifies repository authorization
before it reads the explicitly supplied environment mapping. The internal
construction seam is equivalent to:

```python
def build_moving_service_openai_client(
    credential: MovingServiceEvaluationCredential,
) -> OpenAI:
    ...
```

After a future authorization revision, the factory can construct the
synchronous pinned SDK client with:

```python
OpenAI(
    api_key=credential.reveal_for_client_construction(),
    base_url="https://api.openai.com/v1",
    max_retries=0,
    http_client=DefaultHttpxClient(trust_env=False),
)
```

The secret wrapper is redacted, lacks an instance dictionary, rejects pickle
serialization, and exposes its value only to the module's internal construction
seam.

The factory must:

* verify `openai.__version__ == "2.45.0"` before construction;
* pass the evaluation credential explicitly, never rely on SDK inference;
* set `max_retries=0` explicitly;
* create a synchronous client only;
* use the explicit official API base URL shown above without accepting a
  configurable URL;
* create and own the reviewed `DefaultHttpxClient(trust_env=False)` so ambient
  proxy, certificate, or other HTTP-client environment configuration cannot
  redirect or alter the evaluation;
* accept no caller-provided proxy, provider object, HTTP client, transport,
  default headers, default query, organization, project, admin key, workload
  identity, or webhook key;
* add no logging hooks, telemetry hooks, middleware, or response persistence;
* return the client only to the capability-specific transport; and
* close the OpenAI client and factory-owned HTTP client in a `finally` block
  after the bounded run operation.

Per-request timeouts remain authoritative: five seconds for token preflight and
12 seconds for AI generation. Client construction must not change these values.

Client construction is not a model call, but it is prohibited until credential
integration is separately authorized. The first SDK method invocation is the
network boundary.

## 6. Runner Gate Sequence

The runner must use phases so no secret or network-capable object exists during
ordinary validation.

### Phase A — Non-secret, offline gates

Run all of these before importing the credential reader or client factory:

1. Confirm the runner was invoked through the capability-specific script.
2. Confirm the repository authorization record permits the requested phase.
3. Verify prompt, run-configuration, and provider-schema bytes and digests.
4. Verify prompt, request, response, knowledge, scenario, fallback, and protocol
   versions.
5. Verify the SDK requirement and lock identify exactly 2.45.0 and the reviewed
   Python version.
6. Accept only `storage_unknown` or `complete` from committed fixtures.
7. Reject arbitrary state, fixture paths, prompt paths, schema paths, model
   identifiers, parameters, prices, run order, and output roots.
8. Verify the planned sequence matches the frozen alternating 20-slot order.
9. Verify the ignored local output directory, run-series ID, sequence number,
   and exclusive non-overwrite record path.
10. Verify the monthly, series, and per-call budget configuration.
11. Construct and validate the Pydantic request.
12. Construct the provider request and compare it with reviewed offline payload
    expectations without invoking an SDK method.

Any failure exits before credential access.

### Phase B — Explicit operator intent

After Phase A, require all of:

* an exact command-line execution mode that is not the default;
* `GOTIME_MOVING_SERVICE_EVAL_ENABLED` set to the single reviewed literal;
* the run-series ID and next sequence matching the reviewed authorization;
* a clean, non-overwriting output slot; and
* an interactive confirmation unless a separately reviewed noninteractive
  formal-run procedure explicitly replaces it.

No `--force`, wildcard fixture, arbitrary model, arbitrary endpoint, or skip-
gate option is permitted.

### Phase C — Credential access and client construction

Only after Phases A and B pass may the future runner:

1. Reject all conventional OpenAI environment names.
2. Read the one GoTime-specific evaluation credential.
3. Construct the pinned client through the capability-specific factory.
4. Recheck `max_retries == 0` on the constructed client.

Failure writes no prompt, request, response, or credential data.

### Phase D — Exact token preflight

The authenticated `/v1/responses/input_tokens` request is the first network
operation. Before it, generation must still be impossible.

The runner must record:

```text
preflight_attempted: true
preflight_succeeded: true | false
generation_attempted: false
preflight_duration
bounded failure classification, when applicable
```

On failure, timeout, invalid count, more than 3,000 input tokens, or excessive
conservative cost, write the bounded preflight record exclusively, preserve the
planned sequence, stop the series, close the client, and do not generate or
retry.

### Phase E — One AI generation

Only a successful Phase D may enable one generation request. The transport
must use the already reviewed payload, 12-second timeout, zero retries, and no
tools, streaming, background execution, provider prompt-cache controls, or
response reuse.

After the attempt, close the client, validate the untrusted response through
the existing runtime validator, write one bounded record, and stop immediately
on any hard gate failure.

## 7. Authorization Record Decision

The frozen run configuration and manifest currently state that real-model
execution is unauthorized. The runner must not reinterpret those fields or let
an environment variable override them.

The initial versioned authorization artifact is:

```text
path: docs/experiments/suggest-moving-service-questions/v1/openai-execution-authorization.toml
version: moving-service-openai-execution-authorization-v1
SHA-256: 6e3ca9cb4488764f012703ab77daae4f4b952895100f7d935935aeb6a0978be5
status: closed_no_execution_authorized
credential access: false
token preflight: false
AI generation: false
formal evaluation: false
```

The manifest records the artifact path, version, digest, and closed status.
This initial artifact supplies repository-level default denial; it cannot be
used to enable any later phase.

The runner must validate this authority before evaluating operator intent or
approaching a secret boundary. It reads the exact bytes, verifies the manifest
path and SHA-256, rejects unknown or missing TOML sections and fields, and then
compares every binding with the frozen prompt, run-configuration, and provider-
schema paths, versions, and digests. It also requires an empty scope, zero
authorized spend, and all four authorization flags to be false. Environment
values, command-line flags, and operator intent cannot override those results.
Any mismatch stops before credential access, client construction, token
preflight, or generation.

Before credential integration or execution, human review must select one of
these approaches:

1. Create a new versioned run configuration and digest whose authorization
   fields explicitly match the approved phase; or
2. Keep the frozen run configuration immutable and add a separate, versioned,
   narrowly scoped execution-authorization artifact referenced by the manifest.

The second approach is now represented by the initial closed artifact because
it separates experiment inputs from time-bounded operational authority. A
future authorizing revision should identify
the run configuration digest, allowed phase, run-series ID, allowed sequences,
maximum spend, approval date, expiration date, and approving human. It must not
contain a credential.

Until an authorizing revision is explicitly approved, the public factory must
remain unreachable through the runner and the runner must remain fake-only.

## 8. Pre-Execution Dry-Run Plan

The dry run has no credential phase and no network phase.

### Dry run 1 — Artifact and dependency verification

* Parse and verify every frozen artifact and digest.
* Verify the exact SDK and resolved lock versions without constructing a client.
* Regenerate and compare the Pydantic and provider schemas.
* Verify all authorization fields remain closed.

### Dry run 2 — Fixture and sequence matrix

For all 20 planned slots:

* load only the expected committed fixture;
* construct and validate the Pydantic request;
* verify deterministic compact JSON and input field order;
* verify the fixed alternating order; and
* prove exclusive record paths without retaining records after the test.

### Dry run 3 — Captured payload verification

Using only the injected fake SDK client:

* capture the exact token-count and generation keyword arguments;
* compare all shared input fields;
* verify 5-second and 12-second timeouts;
* verify `store: false`, zero retries, strict schema, and prohibited-field
  omissions;
* test exact-count, budget, timeout, unavailable, refusal, incomplete, malformed,
  cache-reporting, and usage-consistency paths; and
* prove no fake call occurs when a prior gate fails.

The implemented control-path harness additionally exercises the frozen fixture
order through request construction, synthetic credential validation, fake
client construction, the OpenAI-specific transport, exact fake token preflight,
fake generation, runtime response validation, cost accounting, exclusive
bounded records, and stop-on-first-failure behavior. Every record states that
all repository authorization flags remain false and that credential access and
client construction were simulated. It excludes system instructions,
serialized requests, full responses, trusted state, credentials, and
authorization headers.

### Dry run 4 — Credential and network negative tests

Without inspecting the real process environment:

* pass synthetic mappings to a future credential-reader unit test;
* verify missing, blank, multiline, oversized, and conventional-name cases fail;
* verify exception text and representations never contain synthetic secrets;
* monkeypatch client construction to fail if reached during offline mode;
* monkeypatch SDK methods to fail if reached before authorization; and
* scan backend, frontend, runner defaults, Compose, and production configuration
  for credential names or transport reachability.

### Dry-run evidence

The reviewed dry-run report should contain only:

```text
artifact versions and digests
SDK and Python versions
test commit identifier
run-configuration identity
provider-schema identity
20-slot fixture and sequence verification result
payload-structure verification result
negative credential/network test result
test counts
authorization state: closed
```

It must not contain prompt text, serialized requests, response bodies, trusted
state, environment values, credentials, or authorization headers.

## 9. Exit Criteria for an Execution-Authorization Review

Before asking to authorize any credential or network request:

* credential-boundary and client-factory code has separate approval;
* all dry runs pass from a clean checkout using the frozen dependency lock;
* a reviewed authorization-artifact approach is implemented;
* the runner remains fail-closed by default;
* conventional OpenAI variables cannot activate or influence the client;
* a preflight failure record is implemented and tested;
* record fields, retention, and deletion procedure are approved;
* provider account, project, spend limit, and data-retention settings are
  reviewed outside the repository;
* the prompt is explicitly frozen for execution;
* real-model execution is explicitly authorized; and
* no application, browser, frontend, FastAPI, production, scheduled, or
  background path can reach the runner.

## 10. Current Decision

```text
credential boundary ready for human review: yes
real-client integration ready for human review: yes
runner-gate design ready for human review: yes
pre-execution dry-run plan ready for human review: yes
credential access authorized: false
network preflight authorized: false
AI-generation execution authorized: false
```

No credential was read, checked, created, or configured while producing this
design. No SDK client was constructed and no network request was made.
