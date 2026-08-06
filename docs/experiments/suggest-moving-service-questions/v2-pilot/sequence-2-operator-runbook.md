# Sequence-2 Preflight Operator Runbook

This runbook is the verified operator surface for sequence 2. Every command is
fixed to run series `moving-service-stage-b-v2-pilot-20260802`, sequence `2`,
fixture `storage_unknown`, prefix `002-storage_unknown`, OpenAI model
`gpt-4.1-mini-2025-04-14`, SDK `openai==2.45.0`, one preflight, zero retries,
zero generations, and maximum spend `$0.03`.

All Docker commands use image `gotime-moving-service-stage-b:openai-2.45.0`.
Preparation, activation, and closure commands use `--network none`. Only the
one future-live preflight command permits provider networking and forwards the
evaluation-specific credential.

## Command inventory

| Phase | Public command | Exists/executable | Pinned container wrapper | Synthetic rehearsal | Authority effect |
| --- | --- | --- | --- | --- | --- |
| Render | `scripts/experiments/suggest_moving_service_questions/render_v2_sequence_2_preflight_authorization_candidate_docker.sh` | required | `render_v2_sequence_2_preflight_authorization_candidate_container.sh` | covered | none |
| Install | `scripts/experiments/suggest_moving_service_questions/install_v2_sequence_2_preflight_authorization_for_review_docker.sh` | required | `install_v2_sequence_2_preflight_authorization_for_review_container.sh` | covered | none |
| Review | `scripts/experiments/suggest_moving_service_questions/review_v2_sequence_2_preflight_authorization_activation_docker.sh` | required | `review_v2_sequence_2_preflight_authorization_activation_container.sh` | covered | none |
| Plan | `scripts/experiments/suggest_moving_service_questions/plan_v2_sequence_2_preflight_authorization_activation_docker.sh` | required | `plan_v2_sequence_2_preflight_authorization_activation_container.sh` | covered | none |
| Activate | `scripts/experiments/suggest_moving_service_questions/activate_v2_sequence_2_preflight_authorization_docker.sh` | required | `activate_v2_sequence_2_preflight_authorization_container.sh` | covered | atomic preflight-only authority |
| Preflight | `scripts/experiments/suggest_moving_service_questions/run_openai_stage_b_v2_preflight_docker.sh` | required | `run_openai_stage_b_v2_preflight_container.sh` | covered with fake client and `--network none` | consumes one active preflight authority |
| Close/recover | `scripts/experiments/suggest_moving_service_questions/close_v2_sequence_2_preflight_authorization_docker.sh` | required | `close_v2_sequence_2_preflight_authorization_container.sh` | covered | restores or verifies permanent closure |
| Expired review cleanup | `scripts/experiments/suggest_moving_service_questions/cleanup_v2_sequence_2_expired_review_package_docker.sh` | required | `cleanup_v2_sequence_2_expired_review_package_container.sh` | covered | none; sequence remains unused |

## Non-authoritative preparation

```sh
sh scripts/experiments/suggest_moving_service_questions/render_v2_sequence_2_preflight_authorization_candidate_docker.sh \
  --output /tmp/gotime-v2-sequence-2-preflight-authorization.toml \
  --approver "<APPROVER_ID>" \
  --approved-at "<APPROVED_AT_WHOLE_SECOND_UTC_Z>" \
  --activated-at "<ACTIVATED_AT_WHOLE_SECOND_UTC_Z>" \
  --expires-at "<EXPIRES_AT_WHOLE_SECOND_UTC_Z>" \
  --reason "<AUTHORIZATION_REASON>"

sh scripts/experiments/suggest_moving_service_questions/install_v2_sequence_2_preflight_authorization_for_review_docker.sh \
  --source /tmp/gotime-v2-sequence-2-preflight-authorization.toml \
  --expected-sha256 "<RENDERED_ARTIFACT_SHA256>"

sh scripts/experiments/suggest_moving_service_questions/review_v2_sequence_2_preflight_authorization_activation_docker.sh \
  --artifact-sha256 "<INSTALLED_ARTIFACT_SHA256>" \
  --reviewer "<REVIEWER_ID>" \
  --decision "<approve|reject|request_changes>" \
  --reviewed-at "<REVIEWED_AT_WHOLE_SECOND_UTC_Z>" \
  --notes "<BOUNDED_NOTES>"

sh scripts/experiments/suggest_moving_service_questions/plan_v2_sequence_2_preflight_authorization_activation_docker.sh \
  --artifact-sha256 "<INSTALLED_ARTIFACT_SHA256>" \
  --installation-record-sha256 "<INSTALLATION_RECORD_SHA256>" \
  --activation-review-sha256 "<ACTIVATION_REVIEW_SHA256>"
```

These four commands do not activate authority.

## Expired, never-activated review cleanup

The cleanup verifier uses the same typed preflight authorization validator as
rendering, installation, and activation. Phase identity is
`metadata.phase`; permission booleans are in `authorization`, and request
limits are in `scope`. Cleanup is permitted only after expiration when active,
activation, transaction, audit, evidence, consumption, cancellation, and
closure records are all absent.

Dry-run first:

```sh
sh scripts/experiments/suggest_moving_service_questions/cleanup_v2_sequence_2_expired_review_package_docker.sh \
  --artifact-sha256 "<EXPIRED_ARTIFACT_SHA256>" \
  --installation-record-sha256 "<INSTALLATION_RECORD_SHA256>" \
  --activation-review-sha256 "<ACTIVATION_REVIEW_SHA256>"
```

After separate confirmation of that exact output, delete only the fixed `/tmp`
source and three fixed `002-storage_unknown` review files:

```sh
sh scripts/experiments/suggest_moving_service_questions/cleanup_v2_sequence_2_expired_review_package_docker.sh \
  --artifact-sha256 "<EXPIRED_ARTIFACT_SHA256>" \
  --installation-record-sha256 "<INSTALLATION_RECORD_SHA256>" \
  --activation-review-sha256 "<ACTIVATION_REVIEW_SHA256>" \
  --confirm-delete \
  --operator "<OPERATOR_ID>"
```

The confirmed command writes one ignored owner-only cleanup record and deletes
only those four exact files. It does not consume sequence 2 or activate
authority.

## Atomic activation

Run only after separate explicit human approval of the exact three digests:

```sh
sh scripts/experiments/suggest_moving_service_questions/activate_v2_sequence_2_preflight_authorization_docker.sh \
  --artifact-sha256 "<INSTALLED_ARTIFACT_SHA256>" \
  --installation-record-sha256 "<INSTALLATION_RECORD_SHA256>" \
  --activation-review-sha256 "<ACTIVATION_REVIEW_SHA256>" \
  --operator "<OPERATOR_ID>" \
  --operator-intent "AUTHORIZE_ONE_STORAGE_UNKNOWN_V2_PREFLIGHT_ONLY"
```

This is the only command here that transitions repository authority. It binds
the reviewed authorization, active execution manifest, activation evidence,
and committed transaction journal. It authorizes preflight only.

## One future-live preflight

After separate live-call approval and interactive credential entry:

```zsh
read -s "GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY?OpenAI evaluation key: "
echo
export GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY
export GOTIME_MOVING_SERVICE_EVAL_ENABLED=1
export GOTIME_MOVING_SERVICE_EVAL_OPERATOR_INTENT=AUTHORIZE_ONE_STORAGE_UNKNOWN_V2_PREFLIGHT_ONLY
sh scripts/experiments/suggest_moving_service_questions/run_openai_stage_b_v2_preflight_docker.sh
```

The runner permits one `/v1/responses/input_tokens` call and no generation. It
consumes the authorization and closes immediately after success or bounded
failure.

## Closure and recovery

Use the same fixed command for idempotent closure verification or interruption
recovery; choose only the reason matching the reviewed lifecycle state:

```sh
sh scripts/experiments/suggest_moving_service_questions/close_v2_sequence_2_preflight_authorization_docker.sh \
  --reason "<success|activation_recovery|operator_cancellation|expiration|bounded_failure>"
```

Closure restores the byte-exact permanent closed manifest, removes only the
sequence-2 active authorization and temporary transaction files, and preserves
bounded transaction and closure evidence. It performs no credential, client,
preflight, generation, or network operation.
