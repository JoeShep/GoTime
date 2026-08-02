# Stage B Generation Pilot Go/No-Go — Suggest Moving-Service Questions

## 1. Decision

```text
review date: 2026-08-01 America/Chicago / 2026-08-02 UTC
repository-side decision: GO for a fresh activation-package review
live execution decision: NO-GO until private account attestation and later approvals
Stage B implementation review complete: yes
Stage B repository activation authorized: false
credential access authorized: false
token preflight authorized: false
AI generation authorized: false
formal evaluation authorized: false
production use authorized: false
```

The offline Stage B boundary and lifecycle are implemented and their
closed-state tests pass. A fresh activation package may be prepared only after
the remaining private account controls are reconfirmed. This review does not
change the manifest, create repository authority, inspect an environment,
construct an OpenAI client, or make a network request.

The historical inactive final-shape proposal from the earlier no-go review was
outside the repository at:

```text
/tmp/gotime-stage-b-authorization-candidate-20260802T025938Z.toml
```

It was manifest-unbound, had no authority, and expired at
`2026-08-02T03:14:38Z`. It must not be reused. This gap-resolution milestone
does not generate a replacement.

## 2. Exact Authorization Shape

The Stage B validator accepts exactly seven TOML sections:

```text
metadata
bindings
authorization
scope
approval
policy
validation
```

The proposal binds the frozen prompt, run configuration, provider schema,
request and response schema versions, knowledge version, OpenAI provider,
`gpt-4.1-mini-2025-04-14`, and `openai==2.45.0`. It permits exactly one
`storage_unknown` attempt at sequence `2` in
`moving-service-stage-b-pilot-20260801`, with one credential read, one client
construction, one input-token preflight, one generation, zero retries, and a
maximum total pilot spend of `$0.03`. Formal evaluation and production use
remain false.

Unknown, missing, broadened, or changed fields fail closed. The artifact alone
is not authority: the repository manifest must reference its exact path,
version, status, and SHA-256 digest, and the artifact must be unexpired.

Candidate identity:

```text
approved_at: 2026-08-02T02:59:38Z
expires_at: 2026-08-02T03:14:38Z
duration: 900 seconds
approver: Joe Shepherd
SHA-256: f2e958930ab35698393ac6b53b3bb43eb396d0282b243aa943bc4c3744e19615
```

## 3. Human-Review Fields

The current audit record supplies these exact nullable placeholders:

```text
grounding_supported
invented_user_facts
scope_overstatement
provider_or_service_recommendation
storage_required_claim
clarity
usefulness
fallback_comparison
reviewer
review_timestamp
bounded_notes
```

The intended `fallback_comparison` values are `materially_better`,
`slightly_better`, `equivalent`, `slightly_worse`, and `materially_worse`.

The capability-specific review operation now validates an exact field set,
boolean safety findings, scores from `1` through `5`, the bounded comparison
enum, a nonblank reviewer of at most 100 characters, and notes of at most 500
characters. It records `human_review_status` as `approved` or `rejected`, uses
an internally generated UTC review timestamp, never changes provider evidence,
and triggers immediate evidence deletion after sign-off.

## 4. Response Evidence and Deletion

The validated response evidence path is exactly:

```text
.local/evaluations/suggest-moving-service-questions/
moving-service-stage-b-pilot-20260801/
002-storage_unknown-reviewed-response.json
```

It is Git-ignored, exclusively created with owner-only mode `0600`, and contains
only the validated Pydantic response object. The bounded audit record stores
its SHA-256 and a deletion deadline set to generation time plus 30 days.

The approved retention rule is deletion immediately after human review sign-off
and aggregate capture, or no later than the recorded 30-day deadline, whichever
comes first. The procedure must be:

1. Complete and validate the bounded human-review fields.
2. Create the reviewed aggregate outcome without copying the full response.
3. Verify the evidence digest one final time.
4. Delete the exact reviewed-response file and the local raw pilot audit record.
5. Confirm neither path exists and record deletion in the reviewed aggregate.

The explicit review command uses only bounded values:

```sh
python scripts/experiments/suggest_moving_service_questions/manage_openai_stage_b_lifecycle.py \
  review \
  --status <approved|rejected> \
  --grounding-supported <true|false> \
  --invented-user-fact-present <true|false> \
  --scope-overstatement-present <true|false> \
  --provider-or-service-recommendation-present <true|false> \
  --storage-required-claim-present <true|false> \
  --clarity-score <1-5> \
  --usefulness-score <1-5> \
  --fallback-comparison <approved-comparison-value> \
  --reviewer <stable-reviewer-label> \
  --notes <bounded-notes>
```

If review has not occurred, deadline deletion is explicit:

```sh
python scripts/experiments/suggest_moving_service_questions/manage_openai_stage_b_lifecycle.py \
  delete-expired-evidence
```

Deletion is now mechanical and audited. Review sign-off deletes immediately;
the separate `delete-expired-evidence` command refuses early deletion and acts
only at or after the recorded deadline. Missing evidence is recorded
explicitly, repeated calls are idempotent, and no response content enters the
deletion record.

## 5. Exact Live Command

Build the capability-specific image from the project root before activation:

```sh
docker build \
  --file scripts/experiments/suggest_moving_service_questions/Dockerfile.stage-b-evaluation \
  --tag gotime-moving-service-stage-b:openai-2.45.0 \
  .
```

The exact future launch command from the project root is:

```sh
sh scripts/experiments/suggest_moving_service_questions/run_openai_stage_b_pilot_docker.sh
```

The credential value is intentionally omitted. Docker receives exactly
`--env GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY`, which forwards that one
host variable by name into the container without placing its value in the
command line. The launch path also supplies exact enablement, fixed sequence
`2`, the repository mount, the caller's UID/GID, a read-only container root,
and the frozen evaluation image. The key must already exist only in the bounded
host process environment under its separately approved name. The CLI
accepts no provider, AI model identifier, artifact, endpoint, timeout, retry,
budget, count, or output-path override. Missing enablement or any value other
than exact string `1` fails after non-secret gates and before credential
lookup. Enablement and flags express operator intent only and cannot override
closed repository authority.

## 6. Account and Credential Controls

The repository boundary requires:

* a dedicated non-production OpenAI project;
* one project-scoped credential with only input-token counting and Responses
  generation permissions needed by this pilot, with unrelated permissions
  disabled where available;
* `gpt-4.1-mini-2025-04-14` enabled for that project;
* low project spend controls or alerts and an appropriate model rate limit;
* API data sharing and training opt-in disabled;
* accepted standard abuse-monitoring retention of up to 30 days;
* the key present only as
  `GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY` in the bounded process; and
* `OPENAI_API_KEY`, `OPENAI_PROJECT_ID`, `OPENAI_ORG_ID`, and all other
  conventional OpenAI configuration absent.

Joe Shepherd previously attested to the dedicated project, project-scoped key,
model access, spend/rate controls, training opt-out, conventional-variable
exclusion, and accepted 30-day retention for Stage A. That attestation covered
the narrowest token-count permission and does not prove that the credential
now has the Responses-generation permission required for Stage B. Repository
inspection also cannot verify current provider-side settings. Immediate human
reconfirmation of all items above is required before a fresh proposal.

## 7. Audit Path and Budget Gate

The pilot audit path is exactly:

```text
.local/evaluations/suggest-moving-service-questions/
moving-service-stage-b-pilot-20260801/
002-storage_unknown-generation-pilot.json
```

It is reserved exclusively with mode `0600` before environment access. An
existing audit or evidence file stops the attempt. Every post-reservation
failure writes a bounded tombstone and consumes the sequence.

Budget enforcement occurs twice:

1. Fresh exact preflight tokens plus the full 500-token output allowance must
   have conservative cost no greater than `$0.03`.
2. Provider-reported cached input, uncached input, and output usage must produce
   actual estimated cost no greater than `$0.03`.

Missing core token usage, inconsistent preflight/generation input counts,
invalid cached-token categories, or unparseable cost data fail closed. There
is one preflight, one generation, zero retry, and no formal-series budget.

The audit now includes credential lookup/value and client-construction states,
preflight and generation states, conservative and actual cost, cache status,
referenced knowledge IDs, failure stage/code, evidence retention state,
human-review state, closure state/path, and the permanent closed digest through
the bounded closure record. Unavailable provider metadata is explicit; missing
core usage required for validation or cost still fails closed.

## 8. Closure After Success or Failure

Closure must occur after every outcome, including expiration or an unexpected
failure:

1. Preserve consumed sequence `1`; do not retry or replace sequence `2` after
   any attempt begins.
2. Remove `GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY` from the bounded process
   environment and terminate that process.
3. Restore `v1/manifest.json` to the committed permanent closed binding.
4. Remove only
   `v1/openai-stage-b-execution-authorization.toml`.
5. Verify the permanent closed artifact SHA-256 is
   `6e3ca9cb4488764f012703ab77daae4f4b952895100f7d935935aeb6a0978be5`.
6. Verify the manifest references that exact path and digest and all credential,
   preflight, generation, and formal-evaluation permissions are false.
7. Run focused authorization/artifact tests and `git diff --check`.
8. Preserve the bounded local evidence only through human review, then apply
   the deletion procedure above.
9. Commit only the closed-state reviewed outcome; never commit active authority.

Closure is implemented by the capability-specific lifecycle command:

```sh
python scripts/experiments/suggest_moving_service_questions/manage_openai_stage_b_lifecycle.py \
  close --reason <success|bounded_failure|expiration|operator_cancellation>
```

It verifies the permanent closed artifact and digest, atomically restores the
closed manifest fields, removes only the temporary Stage B artifact, writes an
exclusive bounded closure record, and updates the audit closure fields. It
does not inspect the environment and is safe to rerun.

## 9. Proposed Manifest Diff — Not Applied

The candidate would require this exact conceptual manifest switch after a new,
unexpired candidate is generated and separately approved:

```diff
-  "artifact_version": "1.6.0",
+  "artifact_version": "1.8.0",
-  "openai_execution_authorization_path": "docs/experiments/suggest-moving-service-questions/v1/openai-execution-authorization.toml",
-  "openai_execution_authorization_version": "moving-service-openai-execution-authorization-v1",
+  "openai_execution_authorization_path": "docs/experiments/suggest-moving-service-questions/v1/openai-stage-b-execution-authorization.toml",
+  "openai_execution_authorization_version": "moving-service-openai-stage-b-authorization-v1",
   "openai_execution_authorization_digest_algorithm": "sha256",
-  "openai_execution_authorization_digest": "6e3ca9cb4488764f012703ab77daae4f4b952895100f7d935935aeb6a0978be5",
-  "openai_execution_authorization_status": "closed_no_execution_authorized",
+  "openai_execution_authorization_digest": "f2e958930ab35698393ac6b53b3bb43eb396d0282b243aa943bc4c3744e19615",
+  "openai_execution_authorization_status": "approved_stage_b_generation_pilot",
-  "status": "openai_execution_authorization_closed",
+  "status": "openai_stage_b_generation_pilot_authorized",
```

All application-level authorization fields remain false:

```json
"adapter_implementation_authorized": false,
"real_model_execution_authorized": false,
"real_model_evaluation_eligible": false
```

This diff is not applied. Because the candidate is already expiring, a later
activation review must generate new timestamps, new bytes, a new digest, and a
corresponding new exact diff.

## 10. Final Go/No-Go Checklist

Ready:

* exact Stage B validator and one-attempt scope;
* frozen artifact bindings;
* same-attempt, nonserializable, single-use preflight evidence;
* exclusive audit/evidence paths;
* layered provider/Pydantic/semantic validation;
* two-stage `$0.03` budget gate;
* closed active repository authority;
* fake-client and network-disabled offline tests.

Remaining before a live proposal can be approved:

* immediately reconfirm project, credential, generation permission, model,
  spending/rate, training, and retention controls.

Decision: **repository-side GO for a newly generated activation-package
review; live execution remains NO-GO** until private account attestation, a
fresh unexpired artifact, exact manifest-diff approval, and separate one-call
execution authorization. No candidate is generated by this milestone.
