# Frozen-v3 sequence-4 generation operator runbook

Status: **offline resolved and rehearsed; generation remains unauthorized**.

The frozen-v2 preflight cannot bind this request. The approved frozen-v3
sequence-1 preflight supplied 2,542 input tokens, conservative maximum cost
`$0.0018168`, evidence digest `0de37564...`, and review digest `5e61e2a7...`.
The separate resolved candidate binds those exact bytes while remaining
inactive, non-authoritative, placeholder-bound, and invalid for execution.
No live timestamp package is currently valid.

Resolved candidate SHA-256: `197c87a6fd56717d7abba4ac342a87d825e6770bb10efbe42d56b5b15a32217b`.
Resolved manifest SHA-256: `380fd2d0bd3a1968cd0300a4f9ef805363f36403af0f31bfe018b8c48a8cb13e`.

Fixed identity: sequence 4, fixture `storage_unknown`, prompt
`moving-service-questions-prompt-v3`, schema
`moving-service-questions-schema-v3`, fallback
`moving-service-fallback-v2`, OpenAI `gpt-4.1-mini-2025-04-14`,
`openai==2.45.0`, zero generation preflights, one generation, zero retries.

## Offline readiness

```sh
sh scripts/experiments/suggest_moving_service_questions/verify_v3_sequence_4_generation_operator_inventory.sh
sh scripts/experiments/suggest_moving_service_questions/verify_v3_sequence_4_generation_readiness_docker.sh
sh scripts/experiments/suggest_moving_service_questions/rehearse_v3_sequence_4_generation_workflow_docker.sh
```

Readiness validates the exact approved live v3 evidence and review. The
rehearsal uses synthetic v3 preflight evidence in isolated state and Docker
networking is disabled. It exercises every operational command below.

## Non-authoritative preparation

```sh
sh scripts/experiments/suggest_moving_service_questions/render_v3_sequence_4_generation_authorization_candidate_docker.sh --output /tmp/gotime-v3-sequence-4-generation-authorization.toml --approver "<APPROVER>" --approved-at "<UTC_Z>" --activated-at "<UTC_Z>" --expires-at "<UTC_Z>" --reason "<REASON>"
sh scripts/experiments/suggest_moving_service_questions/install_v3_sequence_4_generation_authorization_for_review_docker.sh --source /tmp/gotime-v3-sequence-4-generation-authorization.toml --expected-sha256 "<ARTIFACT_SHA256>"
sh scripts/experiments/suggest_moving_service_questions/review_v3_sequence_4_generation_authorization_activation_docker.sh --artifact-sha256 "<ARTIFACT_SHA256>" --reviewer "<REVIEWER>" --decision "<approve|reject|request_changes>" --reviewed-at "<UTC_Z>" --notes "<NOTES>"
sh scripts/experiments/suggest_moving_service_questions/plan_v3_sequence_4_generation_authorization_activation_docker.sh --artifact-sha256 "<ARTIFACT_SHA256>" --installation-record-sha256 "<INSTALL_SHA256>" --activation-review-sha256 "<REVIEW_SHA256>"
```

## Atomic activation and verification

```sh
sh scripts/experiments/suggest_moving_service_questions/activate_v3_sequence_4_generation_authorization_docker.sh --artifact-sha256 "<ARTIFACT_SHA256>" --installation-record-sha256 "<INSTALL_SHA256>" --activation-review-sha256 "<REVIEW_SHA256>" --operator "<OPERATOR>" --operator-intent "AUTHORIZE_ONE_STORAGE_UNKNOWN_V3_GENERATION_ONLY"
sh scripts/experiments/suggest_moving_service_questions/verify_v3_sequence_4_generation_authorization_docker.sh
```

## Human same-shell generation

Only the human operator runs:

```zsh
zsh scripts/experiments/suggest_moving_service_questions/run_v3_sequence_4_live_generation_operator.zsh
```

The script silently prompts, exports only within its process tree, performs no
token preflight, invokes one generation, verifies closure, and unsets all
controls on every exit path. Codex must not launch it during a future live run.

## Grounding review, deletion, and closure

```sh
sh scripts/experiments/suggest_moving_service_questions/review_v3_sequence_4_generation_response_docker.sh --evidence-sha256 "<EVIDENCE_SHA256>" --reviewer "<REVIEWER>" --decision "<approve|reject|request_changes>" --reviewed-at "<UTC_Z>" --grounding-accuracy "<true|false>" --invented-user-fact "<true|false>" --irrelevant-detail "<true|false>" --modality-overstatement "<true|false>" --service-selection-overstatement "<true|false>" --clarity-score "<1-5>" --usefulness-score "<1-5>" --fallback-comparison "<materially_better|slightly_better|equivalent|slightly_worse|materially_worse>" --notes "<NOTES>"
sh scripts/experiments/suggest_moving_service_questions/delete_v3_sequence_4_generation_response_evidence_docker.sh
sh scripts/experiments/suggest_moving_service_questions/close_v3_sequence_4_generation_authorization_docker.sh --reason "<success|bounded_failure|expiration|operator_cancellation|activation_recovery>"
```

For an expired, never-activated review package, first run the fixed command as
a dry-run. A later explicit human deletion approval adds `--confirm-delete`
and `--operator`; no wildcard or recursive deletion is used.

```sh
sh scripts/experiments/suggest_moving_service_questions/cleanup_v3_sequence_4_expired_generation_review_package_docker.sh --artifact-sha256 "<ARTIFACT_SHA256>" --installation-record-sha256 "<INSTALL_SHA256>" --activation-review-sha256 "<REVIEW_SHA256>"
```

V3 is stricter than unchanged lexical
validators in five documented cases; the stress rehearsal records that a
human review must catch those phrases when lexical validation accepts them.
Grounding review is never pre-approved: generation, automated validation, and
closure precede human review, followed by immediate evidence deletion after
sign-off. Bounded rejected-response diagnostics remain a separate milestone.
