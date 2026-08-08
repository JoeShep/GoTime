# Frozen-v3 sequence-4 generation operator runbook

Status: **offline rehearsed; live blocked pending a fresh approved v3 preflight**.

The frozen-v2 preflight cannot bind this request. Frozen v3 changes the exact
deterministic request, canonical attempt, provider fingerprint, and necessarily
requires a fresh provider token count. These commands refuse non-synthetic
preparation until a separately reviewed v3 preflight package replaces the
explicit unresolved bindings. No live timestamp package is currently valid.

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

The rehearsal uses only synthetic v3 preflight evidence in isolated state and
Docker networking is disabled. It exercises every operational command below.

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

Expired-package cleanup is not applicable while the live package is blocked
and cannot be rendered. A future resolved candidate must add and rehearse that
command before live preparation. V3 is stricter than unchanged lexical
validators in five documented cases; the stress rehearsal records that a
human review must catch those phrases when lexical validation accepts them.
Bounded rejected-response diagnostics remain a separate milestone.
