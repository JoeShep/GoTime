# Frozen-v3 sequence-1 preflight operator runbook

Status: offline-only until this workflow is committed and receives final human
review. Fixed identity is run series
`moving-service-stage-b-v3-pilot-20260807`, sequence `1`, fixture
`storage_unknown`, prefix `001-storage_unknown`. Generation is unauthorized.

## Phase 0: offline readiness

Run from the repository root:

```sh
sh scripts/experiments/suggest_moving_service_questions/verify_v3_sequence_1_preflight_operator_inventory.sh
sh scripts/experiments/suggest_moving_service_questions/verify_v3_sequence_1_preflight_readiness_docker.sh
sh scripts/experiments/suggest_moving_service_questions/rehearse_v3_sequence_1_preflight_workflow_docker.sh
```

## Render, install, activation review, and plan

```sh
sh scripts/experiments/suggest_moving_service_questions/render_v3_sequence_1_preflight_authorization_docker.sh --approver "<APPROVER>" --approved-at "<UTC_Z>" --activated-at "<UTC_Z>" --expires-at "<UTC_Z>" --reason "<REASON>"
sh scripts/experiments/suggest_moving_service_questions/install_v3_sequence_1_preflight_authorization_for_review_docker.sh --expected-sha256 "<ARTIFACT_SHA256>"
sh scripts/experiments/suggest_moving_service_questions/review_v3_sequence_1_preflight_authorization_activation_docker.sh --artifact-sha256 "<ARTIFACT_SHA256>" --reviewer "<REVIEWER>" --decision "<approve|reject|request_changes>" --reviewed-at "<UTC_Z>" --notes "<NOTES>"
sh scripts/experiments/suggest_moving_service_questions/plan_v3_sequence_1_preflight_authorization_activation_docker.sh --artifact-sha256 "<ARTIFACT_SHA256>" --installation-record-sha256 "<INSTALL_SHA256>" --activation-review-sha256 "<REVIEW_SHA256>"
```

## Atomic activation and verification

```sh
sh scripts/experiments/suggest_moving_service_questions/activate_v3_sequence_1_preflight_authorization_docker.sh --artifact-sha256 "<ARTIFACT_SHA256>" --installation-record-sha256 "<INSTALL_SHA256>" --activation-review-sha256 "<REVIEW_SHA256>" --operator "<OPERATOR>" --operator-intent "AUTHORIZE_ONE_STORAGE_UNKNOWN_V3_PREFLIGHT_ONLY"
sh scripts/experiments/suggest_moving_service_questions/verify_v3_sequence_1_preflight_authorization_docker.sh
```

## Human same-shell preflight

Only the human operator runs this command directly in zsh:

```zsh
zsh scripts/experiments/suggest_moving_service_questions/run_v3_live_preflight_operator.zsh
```

The fixed child launcher is
`scripts/experiments/suggest_moving_service_questions/run_openai_stage_b_v3_sequence_1_preflight_docker.sh`.
It receives the evaluation credential by environment-variable name only. Codex
must not run the human credential-bearing command.

## Immediate evidence review and generation binding

Complete evidence review in the same session, before its deadline:

```sh
sh scripts/experiments/suggest_moving_service_questions/review_v3_sequence_1_preflight_evidence_docker.sh --evidence-sha256 "<EVIDENCE_SHA256>" --input-tokens "<COUNT>" --conservative-cost "<COST>" --reviewer "<REVIEWER>" --decision "<approve|reject|request_changes>" --reviewed-at "<UTC_Z>" --token-count-plausible "<true|false>" --cost-within-limit "<true|false>" --frozen-bindings-confirmed "<true|false>" --evidence-history-confirmed "<true|false>" --notes "<NOTES>"
sh scripts/experiments/suggest_moving_service_questions/resolve_v3_sequence_4_generation_candidate_binding_docker.sh
```

The binding command is dry-run-only, writes nothing, and does not authorize
generation. A later reviewed milestone must version the resolved generation
candidate.

## Closure/recovery and expired review cleanup

```sh
sh scripts/experiments/suggest_moving_service_questions/close_v3_sequence_1_preflight_authorization_docker.sh --reason "<success|bounded_failure|expiration|operator_cancellation|activation_recovery>"
sh scripts/experiments/suggest_moving_service_questions/cleanup_v3_sequence_1_expired_review_package_docker.sh
sh scripts/experiments/suggest_moving_service_questions/cleanup_v3_sequence_1_expired_review_package_docker.sh --confirm-delete --operator "<OPERATOR>"
```

Cleanup is fixed to the rendered `/tmp` artifact and three review files. It
uses no wildcard or recursive deletion and is valid only for an expired,
never-activated package.
