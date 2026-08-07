# Sequence-3 preflight operator runbook

Only commands in this runbook belong to the reviewed sequence-3 workflow. They are fixed to run series `moving-service-stage-b-v2-pilot-20260802`, sequence `3`, fixture `storage_unknown`, audit prefix `003-storage_unknown`, OpenAI model `gpt-4.1-mini-2025-04-14`, SDK `openai==2.45.0`, one preflight, zero retries, zero generation, and `$0.03` maximum spend.

All preparation, verification, activation, and closure commands use the pinned image `gotime-moving-service-stage-b:openai-2.45.0`. Synthetic rehearsals use `--network none`.

## Command inventory

| Phase | Verified public command | Authority effect |
| --- | --- | --- |
| Render | `scripts/experiments/suggest_moving_service_questions/render_v2_sequence_3_preflight_authorization_candidate_docker.sh` | none |
| Install | `scripts/experiments/suggest_moving_service_questions/install_v2_sequence_3_preflight_authorization_for_review_docker.sh` | none |
| Review | `scripts/experiments/suggest_moving_service_questions/review_v2_sequence_3_preflight_authorization_activation_docker.sh` | none |
| Plan | `scripts/experiments/suggest_moving_service_questions/plan_v2_sequence_3_preflight_authorization_activation_docker.sh` | none |
| Activate | `scripts/experiments/suggest_moving_service_questions/activate_v2_sequence_3_preflight_authorization_docker.sh` | atomic preflight-only authority |
| Verify active | `scripts/experiments/suggest_moving_service_questions/verify_v2_sequence_3_preflight_authorization_docker.sh` | none |
| One live preflight | `scripts/experiments/suggest_moving_service_questions/run_v2_sequence_3_live_preflight_operator.zsh` | consumes active authority |
| Close/recover | `scripts/experiments/suggest_moving_service_questions/close_v2_sequence_3_preflight_authorization_docker.sh` | restores/verifies closed state |

## Non-authoritative preparation

```sh
sh scripts/experiments/suggest_moving_service_questions/render_v2_sequence_3_preflight_authorization_candidate_docker.sh --output /tmp/gotime-v2-sequence-3-preflight-authorization.toml --approver "<APPROVER>" --approved-at "<UTC_Z>" --activated-at "<UTC_Z>" --expires-at "<UTC_Z>" --reason "<REASON>"
sh scripts/experiments/suggest_moving_service_questions/install_v2_sequence_3_preflight_authorization_for_review_docker.sh --source /tmp/gotime-v2-sequence-3-preflight-authorization.toml --expected-sha256 "<ARTIFACT_SHA256>"
sh scripts/experiments/suggest_moving_service_questions/review_v2_sequence_3_preflight_authorization_activation_docker.sh --artifact-sha256 "<ARTIFACT_SHA256>" --reviewer "<REVIEWER>" --decision approve --reviewed-at "<UTC_Z>" --notes "<NOTES>"
sh scripts/experiments/suggest_moving_service_questions/plan_v2_sequence_3_preflight_authorization_activation_docker.sh --artifact-sha256 "<ARTIFACT_SHA256>" --installation-record-sha256 "<INSTALL_SHA256>" --activation-review-sha256 "<REVIEW_SHA256>"
```

## Atomic activation

```sh
sh scripts/experiments/suggest_moving_service_questions/activate_v2_sequence_3_preflight_authorization_docker.sh --artifact-sha256 "<ARTIFACT_SHA256>" --installation-record-sha256 "<INSTALL_SHA256>" --activation-review-sha256 "<REVIEW_SHA256>" --operator "<OPERATOR>" --operator-intent "AUTHORIZE_ONE_STORAGE_UNKNOWN_V2_PREFLIGHT_ONLY"
```

## One live preflight

After separate live-call approval, the human operator runs exactly one command directly in their own interactive terminal:

```zsh
zsh scripts/experiments/suggest_moving_service_questions/run_v2_sequence_3_live_preflight_operator.zsh
```

Codex must not run this command from its own process. The script performs the silent credential prompt, exports the evaluation-specific variable only inside its process tree, sets fixed enablement and intent, invokes the sequence-3 Docker child once, verifies or recovers closure, and unsets all three variables. The credential is never an argument or file.

The EXIT handler preserves the incoming exit code in a non-reserved local
variable. Operator scripts must not assign to zsh reserved parameters such as
`status`. The INT, TERM, and HUP handlers retain their bounded exit codes, and
closure failure remains visible to the operator after recovery is attempted.

After a successful live preflight, complete the human evidence review within
its review deadline before ending the same session. Do not defer that review
to a later day.

## Closure/recovery

```sh
sh scripts/experiments/suggest_moving_service_questions/close_v2_sequence_3_preflight_authorization_docker.sh --reason "<success|activation_recovery|operator_cancellation|expiration|bounded_failure>"
```

The committed repository state remains permanently closed. Generation remains unauthorized.
