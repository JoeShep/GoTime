# Stage A Token-Preflight Go/No-Go — Suggest Moving-Service Questions

## Decision

```text
review date: 2026-07-31
candidate run-series ID: moving-service-stage-a-20260731
candidate sequence: 1
candidate fixture: storage_unknown
candidate authorization active: false
credential access active: false
token preflight active: false
AI generation authorized: false
formal evaluation authorized: false
decision for a real token-preflight call: NO-GO
```

This milestone defines and tests the exact Stage A boundary without opening it.
No credential was read, no network request was made, and no AI model was called.
The next milestone may decide whether to create and activate a final Stage A
authorization; the committed candidate is not itself activatable.

## Sequence-2 Reconciliation

Sequence `1` was later activated for one bounded attempt. That attempt stopped
at credential validation because the evaluation credential was absent. No
client was constructed and no provider request was made, but the authorization
policy states that a failure consumes the sequence. The manifest was restored
to the permanent closed authorization afterward.

The next eligible Stage A artifact must therefore authorize exactly sequence
`2` in run series `moving-service-stage-a-20260731`. The manifest-bound
validator extracts the single sequence from that artifact and rejects consumed
sequence `1`, skipped sequence `3`, multiple sequences, and non-integer values.
The runner derives its sequence from the verified artifact and rejects any
caller-supplied mismatch. Its exclusive record for the next slot is:

```text
.local/evaluations/suggest-moving-service-questions/
  moving-service-stage-a-20260731/002-storage_unknown-preflight.json
```

This reconciliation does not activate Stage A. Credential access, token
preflight, AI generation, and formal evaluation remain closed until a new,
exact sequence-2 artifact and manifest switch receive separate review.

Sequence `2` was subsequently authorized and completed its one exact token
preflight successfully. The provider reported `2176` input tokens; AI
generation was not attempted. The manifest was returned to the permanent
closed authorization and sequence `2` is now consumed. Any future Stage A
authorization must use the next contiguous sequence, `3`, and requires a new
review decision; this does not itself authorize another preflight.

## Candidate Authorization

The exact candidate is:

```text
path: docs/experiments/suggest-moving-service-questions/v1/openai-stage-a-authorization-candidate.toml
version: moving-service-openai-stage-a-authorization-v1
SHA-256: b523426249b9c697f0ad8fa5c7e3cdc0d965db35c5ab5f8f1a7dc66fd4655202
status: candidate_pending_explicit_approval
active repository authority: false
```

Its proposed operational permissions are exactly:

```toml
[authorization]
credential_access_authorized = true
token_preflight_authorized = true
ai_generation_authorized = false
formal_evaluation_authorized = false
```

Its scope permits at most one credential read, one client construction, and one
token-preflight request for sequence `1` of `storage_unknown` in run series
`moving-service-stage-a-20260731`. It permits zero AI-generation requests and
sets maximum authorized generation spend to `$0.00`.

Approval is deliberately pending. A later final authorization must record a
non-placeholder approving human, an exact UTC approval time, and an exact UTC
expiration no more than 900 seconds after approval. It must be a new artifact
with a new digest and must replace the active manifest authorization. Editing or
activating the candidate in place is prohibited.

## Fail-Closed Activation and Call Path

The Stage A public runner follows this order:

```text
candidate and frozen-artifact integrity
→ active manifest authorization
→ exact fixture/run-series/sequence scope
→ ignored output path and non-overwrite check
→ $0.00 generation-budget check
→ exact operator-intent literal
→ credential access
→ pinned OpenAI client construction
→ one token-preflight operation
→ bounded audit record
```

The manifest continues to point to the closed v1 execution authorization and
records `openai_stage_a_authorization_candidate_activated: false`. The public
runner therefore stops at repository authorization before inspecting the
supplied environment mapping. The credential factory also independently rejects
the candidate because `active_repository_authority` is false and approval is
pending.

The Stage A runner contains no AI-generation call. Its only admitted provider
operation is `OpenAIMovingServiceEvaluationTransport.preflight()`. Offline fake
resources prove that input-token counting can occur while the fake generation
method remains uncalled. The separate transport generation method is never
passed to, referenced by, or invoked from the Stage A runner.

## Bounded Preflight Audit Record

The exclusive local record is named:

```text
.local/evaluations/suggest-moving-service-questions/
  moving-service-stage-a-20260731/001-storage_unknown-preflight.json
```

It contains only:

* run-series ID, sequence, fixture, and capability;
* authorization version and digest;
* prompt, run-configuration, and provider-schema digests;
* provider, AI model identifier, and SDK version;
* preflight attempted/succeeded, duration, exact input-token count, and bounded
  failure classification;
* conservative maximum generation cost calculated during preflight;
* credential-access and client-construction booleans; and
* explicit false generation/formal-evaluation fields and `$0.00` generation
  spend.

It excludes system instructions, serialized requests, trusted state, provider
responses, credentials, authorization headers, and arbitrary error text. An
existing record cannot be overwritten.

## Provider Account, Project, Retention, and Credential Controls

Official OpenAI documentation establishes the controls that must be verified:

* API inputs and outputs are not used to train OpenAI models unless the customer
  explicitly opts in. The Responses API has 30-day abuse-monitoring retention
  under the standard policy. Zero Data Retention is a separately controlled
  account feature; it must not be assumed. [OpenAI data controls](https://developers.openai.com/api/docs/guides/your-data)
* Service accounts are project-scoped. Their keys default to broad read/write
  access, and project API-key settings support restricted permissions. The
  evaluation therefore requires a dedicated project and the narrowest available
  permissions for the Responses input-token endpoint. [OpenAI project management](https://help.openai.com/en/articles/9186755-managing-projects-in-the-api-platform)
* Project budgets are soft alert thresholds: requests continue after the budget
  is exceeded. GoTime's local `$0.00` generation gate and request-count gate are
  therefore the authoritative hard controls. [OpenAI project budgets](https://help.openai.com/en/articles/9186755-managing-projects-in-the-api-platform)
* OpenAI recommends separate project-based keys, isolated rate/spend controls,
  secure environment or secret storage, and never committing keys. [OpenAI API
  key safety](https://help.openai.com/en/articles/5008148)

No account dashboard or credential was accessed during this review. Before a
Stage A authorization can be activated, an authorized human must attest that:

1. a dedicated, non-production OpenAI project is selected;
2. the credential is project-scoped and stored only in
   `GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY` for the bounded process;
3. its effective permissions are the narrowest available for the required
   input-token operation, with unrelated endpoints disabled where supported;
4. `gpt-4.1-mini-2025-04-14` is allowed for the project;
5. project model/rate controls and a low spend alert are configured, with the
   understanding that the provider budget is not a hard cap;
6. API data sharing/training opt-in is disabled;
7. the applicable retention tier is recorded (standard 30-day abuse monitoring
   unless an approved different control is visibly enabled); and
8. the key is absent from Docker Compose, backend, frontend, production
   deployment configuration, shell profiles shared with application processes,
   logs, and repository files.

The repository scan confirms the evaluation credential name is confined to the
script-only experiment and its documentation/tests; no backend, frontend, or
Docker Compose configuration defines it. Actual provider-account settings remain
unverified and are a go-live blocker.

## Final Gate Decision

Offline implementation readiness is **GO for human review**. Authorization of a
real token-preflight request is **NO-GO** until all of the following occur in a
separate milestone:

1. an authorized human supplies the account/project-control attestation above;
2. a final Stage A artifact replaces all pending values with the approving
   identity and exact UTC approval/expiration times;
3. the final artifact is independently hashed and reviewed;
4. the manifest is deliberately repointed from the closed authorization to that
   one exact final artifact;
5. offline validation is rerun against the final bytes; and
6. the operator separately confirms the exact intent literal immediately before
   the one call.

Until then, credential access, token preflight, AI generation, formal evaluation,
and production use all remain closed.
