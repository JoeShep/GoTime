# Sequence-4 generation operator runbook

Generation remains unauthorized in committed state. Every command is fixed to
run series `moving-service-stage-b-v2-pilot-20260802`, sequence `4`, fixture
`storage_unknown`, OpenAI model `gpt-4.1-mini-2025-04-14`, SDK
`openai==2.45.0`, zero preflights, one generation, zero retries, and `$0.03`.

## Offline readiness

```sh
sh scripts/experiments/suggest_moving_service_questions/verify_v2_sequence_4_generation_operator_inventory.sh
sh scripts/experiments/suggest_moving_service_questions/verify_v2_sequence_4_generation_readiness_docker.sh
sh scripts/experiments/suggest_moving_service_questions/rehearse_v2_sequence_4_generation_workflow_docker.sh
```

Both use the pinned image with `--network none`. No credential is forwarded.

## Non-authoritative preparation

```sh
sh scripts/experiments/suggest_moving_service_questions/render_v2_sequence_4_generation_authorization_candidate_docker.sh --output /tmp/gotime-v2-sequence-4-generation-authorization.toml --approver "<APPROVER>" --approved-at "<UTC_Z>" --activated-at "<UTC_Z>" --expires-at "<UTC_Z>" --reason "<REASON>"
sh scripts/experiments/suggest_moving_service_questions/install_v2_sequence_4_generation_authorization_for_review_docker.sh --source /tmp/gotime-v2-sequence-4-generation-authorization.toml --expected-sha256 "<ARTIFACT_SHA256>"
sh scripts/experiments/suggest_moving_service_questions/review_v2_sequence_4_generation_authorization_activation_docker.sh --artifact-sha256 "<ARTIFACT_SHA256>" --reviewer "<REVIEWER>" --decision "<approve|reject|request_changes>" --reviewed-at "<UTC_Z>" --notes "<NOTES>"
sh scripts/experiments/suggest_moving_service_questions/plan_v2_sequence_4_generation_authorization_activation_docker.sh --artifact-sha256 "<ARTIFACT_SHA256>" --installation-record-sha256 "<INSTALL_SHA256>" --activation-review-sha256 "<REVIEW_SHA256>"
```

## Atomic activation

```sh
sh scripts/experiments/suggest_moving_service_questions/activate_v2_sequence_4_generation_authorization_docker.sh --artifact-sha256 "<ARTIFACT_SHA256>" --installation-record-sha256 "<INSTALL_SHA256>" --activation-review-sha256 "<REVIEW_SHA256>" --operator "<OPERATOR>" --operator-intent "AUTHORIZE_ONE_STORAGE_UNKNOWN_V2_GENERATION_ONLY"
sh scripts/experiments/suggest_moving_service_questions/verify_v2_sequence_4_generation_authorization_docker.sh
```

## One live generation

After separate approval, the human operator—not Codex—runs exactly:

```zsh
zsh scripts/experiments/suggest_moving_service_questions/run_v2_sequence_4_live_generation_operator.zsh
```

The script prompts silently and launches generation in the same process tree.
It never performs a token preflight and unsets all controls on every exit path.

## Immediate grounding review and evidence deletion

```sh
sh scripts/experiments/suggest_moving_service_questions/review_v2_sequence_4_generation_response_docker.sh --evidence-sha256 "<EVIDENCE_SHA256>" --reviewer "<REVIEWER>" --decision "<approve|reject|request_changes>" --reviewed-at "<UTC_Z>" --grounding-accuracy "<true|false>" --invented-user-fact "<true|false>" --irrelevant-detail "<true|false>" --modality-overstatement "<true|false>" --service-selection-overstatement "<true|false>" --clarity-score "<1-5>" --usefulness-score "<1-5>" --fallback-comparison "<materially_better|slightly_better|equivalent|slightly_worse|materially_worse>" --notes "<NOTES>"
sh scripts/experiments/suggest_moving_service_questions/delete_v2_sequence_4_generation_response_evidence_docker.sh
```

Grounding review deletes validated response evidence immediately and writes a
content-free deletion record. Rejected automated output has no response evidence.

## Closure/recovery

```sh
sh scripts/experiments/suggest_moving_service_questions/close_v2_sequence_4_generation_authorization_docker.sh --reason "<success|bounded_failure|expiration|operator_cancellation|activation_recovery>"
```

Formal evaluation, Stage C, production use, FastAPI, and frontend exposure are
always false. No command authorizes another preflight or a second generation.
