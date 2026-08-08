# Frozen-v4 sequence-1 preflight operator runbook

Status: offline-only until this workflow is committed and receives final human
review. Fixed identity is run series
`moving-service-stage-b-v4-pilot-20260808`, sequence `1`, fixture
`storage_unknown`, prefix `001-storage_unknown`. Generation is unauthorized.

The inactive candidate is bound to frozen-v4 manifest
`3cdbd2bf3606191aa52108d8284c8ab300d58a511f313f78a06be51d95fac649`,
request-identity artifact `b5125e2075779306f0a4374676d442fa3016702bdb5143bc8e3a6b7173d9dd35`,
deterministic request `f5a8c7e0...`, canonical attempt `7a3c0f7a...`, and
provider fingerprint `15caaaaa...`. V2 and v3 evidence are ineligible.

## Phase 0: offline readiness

Run from the repository root:

```sh
sh scripts/experiments/suggest_moving_service_questions/verify_v4_sequence_1_preflight_operator_inventory.sh
sh scripts/experiments/suggest_moving_service_questions/verify_v4_sequence_1_preflight_readiness_docker.sh
sh scripts/experiments/suggest_moving_service_questions/rehearse_v4_sequence_1_preflight_workflow_docker.sh
```

## Render, install, activation review, and plan

```sh
sh scripts/experiments/suggest_moving_service_questions/render_v4_sequence_1_preflight_authorization_docker.sh --approver "<APPROVER>" --approved-at "<UTC_Z>" --activated-at "<UTC_Z>" --expires-at "<UTC_Z>" --reason "<REASON>"
sh scripts/experiments/suggest_moving_service_questions/install_v4_sequence_1_preflight_authorization_for_review_docker.sh --expected-sha256 "<ARTIFACT_SHA256>"
sh scripts/experiments/suggest_moving_service_questions/review_v4_sequence_1_preflight_authorization_activation_docker.sh --artifact-sha256 "<ARTIFACT_SHA256>" --reviewer "<REVIEWER>" --decision "<approve|reject|request_changes>" --reviewed-at "<UTC_Z>" --notes "<NOTES>"
sh scripts/experiments/suggest_moving_service_questions/plan_v4_sequence_1_preflight_authorization_activation_docker.sh --artifact-sha256 "<ARTIFACT_SHA256>" --installation-record-sha256 "<INSTALL_SHA256>" --activation-review-sha256 "<REVIEW_SHA256>"
```

## Atomic activation and verification

```sh
sh scripts/experiments/suggest_moving_service_questions/activate_v4_sequence_1_preflight_authorization_docker.sh --artifact-sha256 "<ARTIFACT_SHA256>" --installation-record-sha256 "<INSTALL_SHA256>" --activation-review-sha256 "<REVIEW_SHA256>" --operator "<OPERATOR>" --operator-intent "AUTHORIZE_ONE_STORAGE_UNKNOWN_V4_PREFLIGHT_ONLY"
sh scripts/experiments/suggest_moving_service_questions/verify_v4_sequence_1_preflight_authorization_docker.sh
```

## Human same-shell preflight

Only the human operator runs this command directly in zsh:

```zsh
zsh scripts/experiments/suggest_moving_service_questions/run_v4_live_preflight_operator.zsh
```

The fixed child launcher is
`scripts/experiments/suggest_moving_service_questions/run_openai_stage_b_v4_sequence_1_preflight_docker.sh`.
It receives the evaluation credential by environment-variable name only. Codex
must not run the human credential-bearing command.

## Immediate evidence review and generation binding

Complete evidence review in the same session, before its deadline:

```sh
sh scripts/experiments/suggest_moving_service_questions/review_v4_sequence_1_preflight_evidence_docker.sh --evidence-sha256 "<EVIDENCE_SHA256>" --input-tokens "<COUNT>" --conservative-cost "<COST>" --reviewer "<REVIEWER>" --decision "<approve|reject|request_changes>" --reviewed-at "<UTC_Z>" --token-count-plausible "<true|false>" --cost-within-limit "<true|false>" --frozen-bindings-confirmed "<true|false>" --evidence-history-confirmed "<true|false>" --notes "<NOTES>"
sh scripts/experiments/suggest_moving_service_questions/preview_v4_generation_candidate_binding_docker.sh
```

The binding command is dry-run-only, writes nothing, and does not authorize
generation. A later reviewed milestone must version the resolved generation
candidate.

## Bounded evidence contract

Successful preflight evidence records the fixed run/sequence/fixture/phase,
credential and client attempt status, exactly one preflight and zero generation
requests, zero retries, exact input tokens, optional cached/uncached counts and
provider request ID, conservative cost, duration, all frozen request identities,
authorization/activation/transaction bindings, creation time, and a 15-minute
review deadline. It explicitly records `token_preflight_attempted`,
`token_preflight_succeeded`, `ai_generation_attempted`,
`authorization_consumed`, `authorization_reusable`, `closure_verified`, and
`permanent_closed_state_verified`. The compatibility fields
`preflight_attempted` and `preflight_succeeded` have exactly the same boolean
meaning as their `token_preflight_*` equivalents.

Evidence binds the exact activation, final transaction, audit, consumption,
and closure bytes by SHA-256. Evidence approval and generation-binding preview
each independently validate that fixed-path chain, permanent closed state, and
non-reuse. Optional provider fields are `null` when unavailable. Evidence never
contains credential material. Approval is non-authoritative and only makes the
exact evidence eligible for a future separately reviewed generation candidate.

Semantic history validation also requires the complete rendered candidate
bindings and scope, approved activation review, exact active-manifest identity,
committed-then-closed transaction semantics, credential/client success, and a
whole-second UTC order from approval through evidence creation. Self-consistent
records with recomputed digests still fail when any fixed semantic value differs.

The exact-command rehearsal uses the unmistakably synthetic values 4,242 input
tokens and `$0.0024242`; they are not live measurements.

## Closure/recovery and expired review cleanup

```sh
sh scripts/experiments/suggest_moving_service_questions/close_v4_sequence_1_preflight_authorization_docker.sh --reason "<success|bounded_failure|expiration|operator_cancellation|activation_recovery>"
sh scripts/experiments/suggest_moving_service_questions/cleanup_v4_sequence_1_expired_review_package_docker.sh
sh scripts/experiments/suggest_moving_service_questions/cleanup_v4_sequence_1_expired_review_package_docker.sh --confirm-delete --operator "<OPERATOR>"
```

Cleanup is fixed to the rendered `/tmp` artifact and three review files. It
uses no wildcard or recursive deletion and is valid only for an expired,
never-activated package.
