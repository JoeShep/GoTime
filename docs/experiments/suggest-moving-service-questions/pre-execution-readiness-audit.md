# Pre-Execution Readiness Audit — Suggest Moving-Service Questions

## 1. Decision and Scope

```text
audit date: 2026-07-31
capability: suggest_moving_service_questions
overall execution readiness: not ready
credential access authorized: false
token preflight authorized: false
AI generation authorized: false
formal evaluation authorized: false
production use authorized: false
```

This audit evaluates readiness for three later, separately approved stages:

1. one authenticated token-preflight request with no generation;
2. one bounded AI-generation pilot; and
3. the fixed 20-slot formal evaluation.

It does not change an artifact, digest, authorization flag, credential, runner,
transport, prompt, schema, or application path. No credential was read and no
network request or AI generation occurred. The authorization drafts below are
proposals, not repository authority.

## 2. Evidence Reviewed

The audit reviewed the frozen prompt, run configuration, provider-schema
snapshot, closed authorization artifact, manifest, runtime request and response
contracts, adapter, OpenAI transport, credential/client boundary, normal
offline runner, full in-memory control-path harness, evaluation protocol,
provider decision, dependency lock, records, and tests.

Current exact artifact identities are:

| Artifact | SHA-256 |
| --- | --- |
| `v1/real-model-prompt.toml` | `583a4bdf59c4c4ac67c82928415710c3d5c21ac9912ebd4888a026b8fd4acbf2` |
| `v1/openai-run-configuration.toml` | `e665e04b56d8aeaa01f4c9df2fd2f5f4eed37150802fdba869cba54d1e5bc782` |
| `v1/openai-response-schema.json` | `9e5a3a667a1049d150734fd16669dad98cc982c2dc7a9a18f3e0b8cb3e891afb` |
| `v1/openai-execution-authorization.toml` | `6e3ca9cb4488764f012703ab77daae4f4b952895100f7d935935aeb6a0978be5` |

The current authorization scope is empty, maximum authorized spend is `0.00`,
and all four operational permissions are false.

Official OpenAI documentation was rechecked on the audit date. The selected
snapshot remains listed with Responses API and Structured Outputs support and
prices of `$0.40` uncached input, `$0.10` cached input, and `$1.60` output per
million tokens. The input-token endpoint remains an authenticated request. The
Responses API remains documented as not used for training, with standard abuse-
monitoring retention of 30 days; account-level controls still require separate
verification immediately before approval.

Official references:

* [GPT-4.1 mini model](https://developers.openai.com/api/docs/models/gpt-4.1-mini)
* [Counting tokens](https://developers.openai.com/api/docs/guides/token-counting)
* [Structured model outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
* [Data controls](https://developers.openai.com/api/docs/guides/your-data)

## 3. Readiness Results

### Ready offline

* Frozen artifact hashes, capability identity, schemas, field order, knowledge
  version, model identity, token ceilings, timeouts, zero retries, strict
  structured output, `store: false`, and pricing are mechanically validated.
* The response-schema snapshot preserves the Pydantic response schema and
  runtime semantic validation remains authoritative.
* The OpenAI SDK is exactly pinned to `openai==2.45.0` with a resolved Python
  3.12 dependency lock.
* Credential validation rejects conventional OpenAI variables and invalid
  synthetic credentials, redacts failures, and uses `trust_env=False` and zero
  retries at client construction.
* The in-memory harness proves request preparation, synthetic credential and
  client boundaries, fake exact preflight, fake generation, runtime validation,
  cached and uncached cost accounting, exclusive bounded records, and stop-on-
  first-failure behavior.
* The browser, backend, frontend, application startup, and ordinary runner have
  no path to the OpenAI transport or client factory.
* `.local/evaluations/` is ignored and tests retain no evaluation records.

### Blocking implementation gaps

1. **Resolved after the audit: preflight and generation are separated.**
   `OpenAIMovingServiceEvaluationTransport` now exposes only explicit
   `preflight()` and `generate()` operations. Generation requires successful,
   matching, single-use in-memory preflight evidence. The combined `send()`
   path was removed. Offline runner tests enforce exact, mutually exclusive
   permission patterns for preflight-only, one-generation pilot, and formal
   evaluation stages. Repository authorization remains fully closed.

2. **The normal runner is deliberately fake-only.**
   It rejects every transport except the concrete offline fake and does not
   import the credential/client boundary. A capability-specific real-mode path
   still needs implementation and offline tests. It must remain unreachable
   from FastAPI and the frontend.

3. **Authorization validation is hard-coded to the closed artifact.**
   The runner, client factory, artifact validator, manifest expectations, and
   tests embed the current digest, status, and false permissions. Replace this
   with stage-specific, exact allowlists before creating an authorizing
   artifact. Do not accept arbitrary versions, fields, paths, phases, scopes,
   or digests.

4. **The client factory has no reviewed real-constructor wiring.**
   It accepts injected constructors, which is correct for offline tests. A later
   implementation must lazily bind only the pinned `OpenAI` and
   `DefaultHttpxClient` constructors after all non-secret gates and repository
   authorization pass. No generic constructor option may be exposed to the
   execution CLI.

5. **Live record orchestration is incomplete.**
   The dry-run record proves bounded fields and series stopping, while the
   ordinary runner record remains fake-oriented. The real runner must write the
   protocol-approved preflight and generation fields, durations, usage
   categories, failure phase, provider identity, cumulative spend, and
   denominator counters for both success and failure paths.

6. **The prompt is not frozen for real-model execution.**
   Its readiness metadata says `frozen_for_real_model_execution = false`, and
   the adapter and artifact tests require that value. Sending the prompt even
   to the token-count endpoint crosses the provider boundary. Human approval
   must first freeze the exact prompt bytes for provider submission while
   leaving execution authorization separate and false. This metadata-only
   change changes the prompt digest and therefore every downstream binding.

7. **Frozen implementation metadata is historical.**
   The run configuration still records pending resolved SDK/Python/lock status
   and `provider_transport_implementation_authorized = false`, although the
   separately approved implementation now exists. Reconcile these facts through
   a reviewed replacement run-configuration artifact; do not silently edit the
   frozen bytes.

### Blocking review and operational decisions

* Select exact pilot and formal run-series IDs, approval and expiration times,
  approving human, operator-intent literal, and interactive confirmation text.
* Confirm the evaluation-only OpenAI project, project-scoped key, model access,
  provider spend limit, rate limit, standard or approved modified retention,
  and absence of the key from production configuration.
* Approve the proposed 30-day local record-retention and manual deletion rule.
* Name the two formal output reviewers and at least three intended-user
  reviewers, or explicitly defer intended-user review without weakening the
  contract evaluation.
* Reconcile the evaluation protocol's historical generic credential variable
  names with the approved single name
  `GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY`.
* Remove or label stale protocol prerequisites that still say no prompt or
  real-token observability artifacts exist.
* Reconfirm snapshot availability, prices, input-token semantics, provider
  retention, account settings, and SDK pin immediately before each approval.

## 4. Required Gate Order

Every future stage must preserve this order:

```text
artifact integrity
→ repository authorization for the exact requested phase
→ fixture and sequence validation
→ output-path and non-overwrite checks
→ per-call, series, and monthly budget checks
→ explicit operator-intent check
→ credential access
→ pinned client construction
→ token preflight, if authorized
→ AI generation, if separately authorized and preflight succeeded
→ runtime response validation
→ bounded record and series decision
```

An environment value, credential presence, CLI flag, or operator confirmation
is never repository authority. A later-stage permission cannot imply an earlier
permission. Unknown or missing authorization fields must fail closed.

## 5. Artifact Lifecycle for Every Stage

Do not edit the current closed artifact in place. For each stage:

1. finish and review all blocking implementation work;
2. create a new versioned execution-authorization artifact at a new path;
3. bind exact prompt, run-configuration, provider-schema, model, SDK, and
   protocol identities and digests;
4. set only the minimum stage permissions and exact scope;
5. record a non-placeholder approver, approval time, expiration time, run-
   series ID, fixture, sequence, and maximum spend;
6. compute SHA-256 over the final exact bytes and independently verify it;
7. update the manifest to exactly one active authorization artifact and digest;
8. update stage-specific validator allowlists and negative tests;
9. run the full offline suite from a clean checkout;
10. approve one stage only; and
11. after the attempt or expiration, replace it with a new closed authorization
    artifact rather than reusing or widening it.

Any semantic authorization change requires a new authorization version,
artifact, digest, manifest review, and offline verification. Any byte-level
change after approval requires review.

## 6. Stage A — One Token-Preflight Call

This stage is not ready until the capability-specific real runner and remaining
review gates are complete. Mechanical preflight/generation separation and
offline proof that preflight-only cannot generate are complete.

Minimum proposed permissions:

```toml
[authorization]
credential_access_authorized = true
token_preflight_authorized = true
ai_generation_authorized = false
formal_evaluation_authorized = false
```

Minimum proposed scope:

```toml
[scope]
authorized_run_series_id = "<approved-preflight-series-id>"
authorized_sequence_numbers = [1]
authorized_fixture_ids = ["storage_unknown"]
maximum_authorized_spend = "0.00"
approval_date = "<approved-UTC-timestamp>"
expiration_date = "<short-approved-UTC-expiration>"
approved_by = "<reviewed-human-identity>"
```

The final artifact may not contain placeholders. It authorizes one credential
read, one client construction, and one `/v1/responses/input_tokens` request for
the exact prepared `storage_unknown` payload. It authorizes no generation,
retry, alternate fixture, alternate sequence, or formal denominator entry.

The result record must contain the exact count, duration, requested AI model
identifier, prompt and run-configuration digests, success or bounded failure,
`generation_attempted: false`, and zero generation cost. It must preserve the
sequence and close the client. Any failure ends the pilot.

## 7. Stage B — One AI-Generation Pilot

The safest pilot performs a fresh exact preflight immediately before the one
generation. Therefore Stage B authorizes one additional token-preflight request
and one generation request; it does not reuse Stage A's count. Reusing Stage A
would require a separately reviewed, digest-bound preflight-evidence contract
and is not the minimum safe implementation.

Minimum proposed permissions:

```toml
[authorization]
credential_access_authorized = true
token_preflight_authorized = true
ai_generation_authorized = true
formal_evaluation_authorized = false
```

Minimum proposed scope:

```toml
[scope]
authorized_run_series_id = "<approved-generation-pilot-series-id>"
authorized_sequence_numbers = [1]
authorized_fixture_ids = ["storage_unknown"]
maximum_authorized_spend = "0.03"
approval_date = "<approved-UTC-timestamp>"
expiration_date = "<short-approved-UTC-expiration>"
approved_by = "<reviewed-human-identity>"
```

The final artifact may not contain placeholders. A successful exact preflight
at or below 3,000 tokens and conservative cost at or below `$0.03` is required
before generation becomes reachable. The generation uses the frozen 12-second
timeout, 500-token output limit, strict provider schema, temperature zero,
`store: false`, zero retries, no tools, no streaming, and no background mode.

The runner writes exactly one bounded record whether preflight, transport,
response parsing, schema validation, grounding review, or a hard gate fails.
The pilot is not part of the formal 20-slot denominator and cannot be promoted
into it after the fact.

## 8. Stage C — Fixed 20-Slot Formal Evaluation

This stage requires separate human approval after reviewing the Stage B record.
It cannot reuse the Stage B output as a formal result.

Minimum proposed permissions:

```toml
[authorization]
credential_access_authorized = true
token_preflight_authorized = true
ai_generation_authorized = true
formal_evaluation_authorized = true
```

Minimum proposed scope:

```toml
[scope]
authorized_run_series_id = "<approved-formal-series-id>"
authorized_sequence_numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10,
  11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
authorized_fixture_ids = ["storage_unknown", "complete"]
maximum_authorized_spend = "0.60"
approval_date = "<approved-UTC-timestamp>"
expiration_date = "<approved-UTC-expiration>"
approved_by = "<reviewed-human-identity>"
```

The final artifact may not contain placeholders. The runner enforces the exact
alternating fixture order from the frozen run configuration, not merely set
membership. It performs one fresh exact preflight before each possible
generation, never retries or replaces a slot, writes one exclusive record for
every attempted slot, and stops the series on preflight failure, hard budget
failure, authorization expiry, artifact drift, output collision, or another
protocol hard stop.

Reports distinguish 20 planned slots, preflight failures, actual AI-generation
attempts, and AI-response failures. Every attempted generation remains in its
denominator. Provider-managed cache usage is recorded but cannot alter order,
denominators, validation, or safety review.

## 9. Cost Envelope

Frozen worst-case arithmetic remains:

```text
per generated call:
  (3,000 × $0.40 / 1,000,000)
  + (500 × $1.60 / 1,000,000)
  = $0.002000

20 generated calls at that ceiling:
  20 × $0.002000 = $0.040000
```

This is below the `$0.03` per-call and `$0.60` formal-series hard limits. The
larger authorization ceilings remain defense-in-depth, not spending targets.
Formal records use provider-reported cached, uncached, and output-token
categories. No live price lookup occurs during a run.

## 10. Final Readiness Decision

```text
offline artifact and contract integrity: pass
offline full-path simulation: pass
current model snapshot and frozen prices rechecked: pass
one token-preflight call ready for authorization: no
one AI-generation pilot ready for authorization: no
20-slot formal evaluation ready for authorization: no
```

The minimum next implementation milestone is to add the capability-specific
real-mode runner, real-constructor wiring, and complete bounded record path while
remaining offline-testable and default closed. No authorization artifact should
be widened until that milestone and the other blockers in this audit are
reviewed.
