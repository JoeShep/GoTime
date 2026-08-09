# Frozen-v4 sequence-4 generation operator runbook

Status: **offline resolved and rehearsed; generation remains unauthorized**.

Frozen-v2 and frozen-v3 preflight evidence cannot bind this request. The
approved frozen-v4 sequence-1 preflight supplied 2,852 input tokens,
conservative maximum cost
`$0.0019408`, evidence digest `f1f99523...`, and review digest `12b71c10...`.
The separate resolved candidate binds those exact bytes while remaining
inactive, non-authoritative, placeholder-bound, and invalid for execution.
No live timestamp package is currently valid.

Resolved candidate SHA-256: `b9518a4770a7cd225d57fb3cd2564764a9ef840446ac2dd705cd5aee7b37e8df`.
Resolved manifest SHA-256: `3cce967e358355b20f143fcc4b9c45284fa1275303548842545a9072f06b8676`.

Fixed identity: sequence 4, fixture `storage_unknown`, prompt
`moving-service-questions-prompt-v4`, schema
`moving-service-questions-schema-v4`, fallback
`moving-service-fallback-v2`, OpenAI `gpt-4.1-mini-2025-04-14`,
`openai==2.45.0`, zero generation preflights, one generation, zero retries.

## Offline readiness

```sh
sh scripts/experiments/suggest_moving_service_questions/verify_v4_sequence_4_generation_operator_inventory.sh
sh scripts/experiments/suggest_moving_service_questions/verify_v4_sequence_4_generation_readiness_docker.sh
sh scripts/experiments/suggest_moving_service_questions/rehearse_v4_sequence_4_generation_workflow_docker.sh
```

Readiness validates the exact approved live v4 evidence and review. The
rehearsal uses synthetic v4 preflight evidence in isolated state and Docker
networking is disabled. It exercises every operational command below.

## Non-authoritative preparation

```sh
sh scripts/experiments/suggest_moving_service_questions/render_v4_sequence_4_generation_authorization_candidate_docker.sh --output /tmp/gotime-v4-sequence-4-generation-authorization.toml --approver "<APPROVER>" --approved-at "<UTC_Z>" --activated-at "<UTC_Z>" --expires-at "<UTC_Z>" --reason "<REASON>"
sh scripts/experiments/suggest_moving_service_questions/install_v4_sequence_4_generation_authorization_for_review_docker.sh --source /tmp/gotime-v4-sequence-4-generation-authorization.toml --expected-sha256 "<ARTIFACT_SHA256>"
sh scripts/experiments/suggest_moving_service_questions/review_v4_sequence_4_generation_authorization_activation_docker.sh --artifact-sha256 "<ARTIFACT_SHA256>" --reviewer "<REVIEWER>" --decision "<approve|reject|request_changes>" --reviewed-at "<UTC_Z>" --notes "<NOTES>"
sh scripts/experiments/suggest_moving_service_questions/plan_v4_sequence_4_generation_authorization_activation_docker.sh --artifact-sha256 "<ARTIFACT_SHA256>" --installation-record-sha256 "<INSTALL_SHA256>" --activation-review-sha256 "<REVIEW_SHA256>"
```

## Atomic activation and verification

```sh
sh scripts/experiments/suggest_moving_service_questions/activate_v4_sequence_4_generation_authorization_docker.sh --artifact-sha256 "<ARTIFACT_SHA256>" --installation-record-sha256 "<INSTALL_SHA256>" --activation-review-sha256 "<REVIEW_SHA256>" --operator "<OPERATOR>" --operator-intent "AUTHORIZE_ONE_STORAGE_UNKNOWN_V4_GENERATION_ONLY"
sh scripts/experiments/suggest_moving_service_questions/verify_v4_sequence_4_generation_authorization_docker.sh
```

The verifier and live runner share one pre-credential boundary. They validate
the complete active authorization against the resolved candidate, recompute
the exact active generation manifest, and separately revalidate the completed
preflight history from its recorded permanent-closure binding. Exact request,
canonical-attempt, provider-fingerprint, activation, and transaction checks
all complete before credential lookup; the verified prepared request is the
object passed to transport.

The network-disabled rehearsal constructs the completed sequence-1 preflight
lifecycle through the real preflight lifecycle functions. While the exact
generation manifest is active, it runs the live entry boundary against that
history and separately proves that a semantically rebound wrong authorization
and a wrong active manifest are rejected before synthetic credential lookup.

## Human same-shell generation

Only the human operator runs:

```zsh
zsh scripts/experiments/suggest_moving_service_questions/run_v4_sequence_4_live_generation_operator.zsh
```

The script silently prompts, exports only within its process tree, performs no
token preflight, invokes one generation, verifies closure, and unsets all
controls on every exit path. Codex must not launch it during a future live run.
It invokes this fixed Docker child command; operators do not substitute or run
the child separately during a live attempt:

```sh
sh scripts/experiments/suggest_moving_service_questions/run_openai_stage_b_v4_sequence_4_generation_docker.sh
```

## Grounding review, deletion, and closure

```sh
sh scripts/experiments/suggest_moving_service_questions/review_v4_sequence_4_generation_response_docker.sh --evidence-sha256 "<EVIDENCE_SHA256>" --reviewer "<REVIEWER>" --decision "<approve|reject|request_changes>" --reviewed-at "<UTC_Z>" --grounding-accuracy "<true|false>" --invented-user-fact "<true|false>" --irrelevant-detail "<true|false>" --modality-overstatement "<true|false>" --service-selection-overstatement "<true|false>" --clarity-score "<1-5>" --usefulness-score "<1-5>" --fallback-comparison "<materially_better|slightly_better|equivalent|slightly_worse|materially_worse>" --notes "<NOTES>"
sh scripts/experiments/suggest_moving_service_questions/delete_v4_sequence_4_generation_response_evidence_docker.sh
sh scripts/experiments/suggest_moving_service_questions/close_v4_sequence_4_generation_authorization_docker.sh --reason "<success|bounded_failure|expiration|operator_cancellation|activation_recovery>"
```

For an expired, never-activated review package, first run the fixed command as
a dry-run. A later explicit human deletion approval adds `--confirm-delete`
and `--operator`; no wildcard or recursive deletion is used.

```sh
sh scripts/experiments/suggest_moving_service_questions/cleanup_v4_sequence_4_expired_generation_review_package_docker.sh --artifact-sha256 "<ARTIFACT_SHA256>" --installation-record-sha256 "<INSTALL_SHA256>" --activation-review-sha256 "<REVIEW_SHA256>"
```

V4 is stricter than unchanged lexical
validators in five documented cases; the stress rehearsal records that a
human review must catch those phrases when lexical validation accepts them.
Grounding review is never pre-approved: generation, automated validation, and
closure precede human review, followed by immediate evidence deletion after
sign-off. Automated prose rejection retains only bounded rule, field, offset,
canonical-trigger, and occurrence-count diagnostics; rejected prose itself is
not retained.
