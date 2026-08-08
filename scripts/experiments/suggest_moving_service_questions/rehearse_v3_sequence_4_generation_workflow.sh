#!/bin/sh
set -eu

source_root=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
[ "$(pwd -P)" = "$source_root" ] || exit 2
command -v docker >/dev/null
command -v zsh >/dev/null
real_execution="$source_root/docs/experiments/suggest-moving-service-questions/v2-pilot/execution-manifest.json"
real_closed="$source_root/docs/experiments/suggest-moving-service-questions/v2-pilot/closed-execution-manifest.json"
cmp -s "$real_execution" "$real_closed"
before_manifest=$(sha256sum "$real_execution" | cut -d' ' -f1)
real_generation_state="$source_root/.local/evaluations/suggest-moving-service-questions/moving-service-stage-b-v2-pilot-20260802"
[ -z "$(find "$real_generation_state" -maxdepth 2 -name '004-storage_unknown-generation-v3*' -print 2>/dev/null)" ]

rehearsal_root=$(mktemp -d "$source_root/.sequence4-v3-generation-rehearsal.XXXXXX")
cleanup() {
  case "$rehearsal_root" in
    "$source_root"/.sequence4-v3-generation-rehearsal.*) rm -rf "$rehearsal_root" ;;
  esac
}
trap cleanup EXIT INT TERM HUP

field() {
  printf '%s\n' "$1" | sed -n "s/^$2=//p" | sed -n '1p'
}

record_command() {
  printf '%s\n' "$1" >>"$2"
}

run_scenario() {
  scenario=$1
  sandbox="$rehearsal_root/$scenario"
  mkdir -p "$sandbox"
  cp -R "$source_root/scripts" "$sandbox/scripts"
  cp -R "$source_root/docs" "$sandbox/docs"
  cp -R "$source_root/backend" "$sandbox/backend"
  state="$sandbox/.local/evaluations/suggest-moving-service-questions/moving-service-stage-b-v2-pilot-20260802"
  mkdir -p "$state"
  cat >"$state/004-storage_unknown-v3-preflight-evidence.json" <<'EVIDENCE'
{"ai_generation_timeout_seconds":12,"ai_model_identifier":"gpt-4.1-mini-2025-04-14","automatic_retries":0,"background":false,"canonical_attempt_digest":"d9d8141853b7d034ce30de8c9c2689d9738b0bfd73d812a2150b823111b3bdcf","conservative_maximum_generation_cost":"0.0017500","deterministic_request_digest":"952b8003f184de1ff9617103c8c93ab64d87e63cb4e4daee84647b7dd505ed79","fixture_id":"storage_unknown","frozen_v3_manifest_digest":"44da0c5005515784c2c13737ca12a4382c084f1aa56fea5b4a4d40e66fb8659c","input_tokens":2300,"maximum_output_tokens":500,"provider":"OpenAI","provider_preflight_fingerprint":"a5895ad53d54d6d03652152aeadbf8b71a2c672cab86640d1798a3a3680a15e4","sdk_pin":"openai==2.45.0","sequence":4,"store":false,"stream":false,"synthetic":true,"temperature":0,"tools":[],"truncation":"disabled"}
EVIDENCE
  synthetic_evidence_digest=$(sha256sum "$state/004-storage_unknown-v3-preflight-evidence.json" | cut -d' ' -f1)
  printf '{"decision":"approve","generation_gate_binding_eligible":true,"preflight_evidence_digest":"%s","synthetic":true}\n' "$synthetic_evidence_digest" >"$state/004-storage_unknown-v3-preflight-review.json"
  commands="$sandbox/invoked-public-commands.txt"
  rendered="/tmp/gotime-v3-sequence-4-generation-rehearsal-$$-$scenario.toml"
  rm -f "$rendered"
  approved=$(date -u -d '10 seconds ago' '+%Y-%m-%dT%H:%M:%SZ')
  activated=$(date -u -d '5 seconds ago' '+%Y-%m-%dT%H:%M:%SZ')
  expires=$(date -u -d "$activated + 900 seconds" '+%Y-%m-%dT%H:%M:%SZ')
  cd "$sandbox"
  export GOTIME_V3_SEQUENCE_4_GENERATION_OFFLINE_TEST=1

  command_path=scripts/experiments/suggest_moving_service_questions/render_v3_sequence_4_generation_authorization_candidate_docker.sh
  record_command "$command_path" "$commands"
  render_output=$(sh "$command_path" --output "$rendered" --approver "Synthetic Approver" \
    --approved-at "$approved" --activated-at "$activated" --expires-at "$expires" \
    --reason "Synthetic exact-command rehearsal")
  artifact_digest=$(field "$render_output" sha256)

  command_path=scripts/experiments/suggest_moving_service_questions/install_v3_sequence_4_generation_authorization_for_review_docker.sh
  record_command "$command_path" "$commands"
  install_output=$(sh "$command_path" --source "$rendered" --expected-sha256 "$artifact_digest")
  installation_digest=$(field "$install_output" installation_record_digest)

  command_path=scripts/experiments/suggest_moving_service_questions/review_v3_sequence_4_generation_authorization_activation_docker.sh
  record_command "$command_path" "$commands"
  review_output=$(sh "$command_path" --artifact-sha256 "$artifact_digest" --reviewer "Synthetic Reviewer" \
    --decision approve --reviewed-at "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" --notes "Synthetic approval")
  activation_review_digest=$(field "$review_output" review_sha256)

  cleanup_rendered=/tmp/gotime-v3-sequence-4-generation-authorization.toml
  cp "$rendered" "$cleanup_rendered"
  command_path=scripts/experiments/suggest_moving_service_questions/cleanup_v3_sequence_4_expired_generation_review_package_docker.sh
  record_command "$command_path" "$commands"
  cleanup_output=$(GOTIME_V3_SEQUENCE_4_GENERATION_SYNTHETIC_NOW="$(date -u -d "$expires + 1 second" '+%Y-%m-%dT%H:%M:%SZ')" \
    sh "$command_path" --artifact-sha256 "$artifact_digest" \
    --installation-record-sha256 "$installation_digest" \
    --activation-review-sha256 "$activation_review_digest")
  [ "$(field "$cleanup_output" writes_performed)" = false ]
  rm -f "$cleanup_rendered"

  command_path=scripts/experiments/suggest_moving_service_questions/plan_v3_sequence_4_generation_authorization_activation_docker.sh
  record_command "$command_path" "$commands"
  plan_output=$(sh "$command_path" --artifact-sha256 "$artifact_digest" \
    --installation-record-sha256 "$installation_digest" --activation-review-sha256 "$activation_review_digest")
  [ "$(field "$plan_output" writes_performed)" = false ]

  command_path=scripts/experiments/suggest_moving_service_questions/activate_v3_sequence_4_generation_authorization_docker.sh
  record_command "$command_path" "$commands"
  activation_output=$(sh "$command_path" --artifact-sha256 "$artifact_digest" \
    --installation-record-sha256 "$installation_digest" --activation-review-sha256 "$activation_review_digest" \
    --operator "Synthetic Operator" --operator-intent "AUTHORIZE_ONE_STORAGE_UNKNOWN_V3_GENERATION_ONLY")
  [ "$(field "$activation_output" transaction_state)" = committed ]

  command_path=scripts/experiments/suggest_moving_service_questions/verify_v3_sequence_4_generation_authorization_docker.sh
  record_command "$command_path" "$commands"
  sh "$command_path" >/dev/null

  command_path=scripts/experiments/suggest_moving_service_questions/run_v3_sequence_4_live_generation_operator.zsh
  record_command "$command_path" "$commands"
  record_command scripts/experiments/suggest_moving_service_questions/run_openai_stage_b_v3_sequence_4_generation_docker.sh "$commands"
  stdout="$sandbox/operator.stdout"
  stderr="$sandbox/operator.stderr"
  exec 9<<'SYNTHETIC_CREDENTIAL'
synthetic-generation-credential-never-print
SYNTHETIC_CREDENTIAL
  if ! GOTIME_V3_SEQUENCE_4_GENERATION_OFFLINE_TEST=1 \
    GOTIME_V3_SEQUENCE_4_GENERATION_SYNTHETIC_SCENARIO="$scenario" \
    GOTIME_V3_SEQUENCE_4_GENERATION_SYNTHETIC_INPUT_FD=9 \
      zsh "$command_path" >"$stdout" 2>"$stderr"; then
    sed -n '1,20p' "$stderr" >&2
    exit 6
  fi
  if grep -F 'synthetic-generation-credential-never-print' "$stdout" "$stderr" "$state"/*.json >/dev/null 2>&1; then
    exit 7
  fi
  : >"$state/.network-disabled"
  audit="$state/004-storage_unknown-generation-v3-audit.json"
  [ -f "$audit" ]
  grep -F '"preflight_attempted": false' "$audit" >/dev/null
  grep -F '"generation_request_count": 1' "$audit" >/dev/null

  if [ "$scenario" = compliant ] || [ "$scenario" = prompt_policy_stress ]; then
    evidence="$state/004-storage_unknown-generation-v3-validated-response.json"
    evidence_digest=$(sha256sum "$evidence" | cut -d' ' -f1)
    command_path=scripts/experiments/suggest_moving_service_questions/review_v3_sequence_4_generation_response_docker.sh
    record_command "$command_path" "$commands"
    review_decision=approve
    grounding_accuracy=true
    [ "$scenario" = prompt_policy_stress ] && review_decision=request_changes && grounding_accuracy=false
    sh "$command_path" --evidence-sha256 "$evidence_digest" --reviewer "Synthetic Grounding Reviewer" \
      --decision "$review_decision" --reviewed-at "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" \
      --grounding-accuracy "$grounding_accuracy" --invented-user-fact false --irrelevant-detail false \
      --modality-overstatement false --service-selection-overstatement false \
      --clarity-score 5 --usefulness-score 5 --fallback-comparison materially_better \
      --notes "Synthetic grounding approval" >/dev/null
    command_path=scripts/experiments/suggest_moving_service_questions/delete_v3_sequence_4_generation_response_evidence_docker.sh
    record_command "$command_path" "$commands"
    sh "$command_path" >/dev/null
    [ ! -e "$evidence" ]
  fi

  command_path=scripts/experiments/suggest_moving_service_questions/close_v3_sequence_4_generation_authorization_docker.sh
  record_command "$command_path" "$commands"
  sh "$command_path" --reason success >/dev/null
  cmp -s "$sandbox/docs/experiments/suggest-moving-service-questions/v2-pilot/execution-manifest.json" \
    "$sandbox/docs/experiments/suggest-moving-service-questions/v2-pilot/closed-execution-manifest.json"
  if GOTIME_V3_SEQUENCE_4_GENERATION_OFFLINE_TEST=1 zsh \
    scripts/experiments/suggest_moving_service_questions/run_v3_sequence_4_live_generation_operator.zsh \
    </dev/null >/dev/null 2>&1; then
    exit 8
  fi
  : >"$state/.second-use-rejected"
  assertion_output=$(sh scripts/experiments/suggest_moving_service_questions/v3_sequence_4_generation_operator_docker.sh \
    assert-rehearsal --scenario "$scenario")
  [ "$(field "$assertion_output" assertions_passed)" = true ]
  awk -v scenario="$scenario" '{print $0 "\t" scenario "\tpassed"}' "$commands" \
    >"$sandbox/command-coverage.tsv"
  rm -f "$rendered"
  cd "$source_root"
}

run_scenario compliant
run_scenario prose_rejection
run_scenario structural_failure
run_scenario semantic_failure
run_scenario prompt_policy_stress

expected="$rehearsal_root/expected.txt"
cat >"$expected" <<'COMMANDS'
scripts/experiments/suggest_moving_service_questions/activate_v3_sequence_4_generation_authorization_docker.sh
scripts/experiments/suggest_moving_service_questions/cleanup_v3_sequence_4_expired_generation_review_package_docker.sh
scripts/experiments/suggest_moving_service_questions/close_v3_sequence_4_generation_authorization_docker.sh
scripts/experiments/suggest_moving_service_questions/delete_v3_sequence_4_generation_response_evidence_docker.sh
scripts/experiments/suggest_moving_service_questions/install_v3_sequence_4_generation_authorization_for_review_docker.sh
scripts/experiments/suggest_moving_service_questions/plan_v3_sequence_4_generation_authorization_activation_docker.sh
scripts/experiments/suggest_moving_service_questions/render_v3_sequence_4_generation_authorization_candidate_docker.sh
scripts/experiments/suggest_moving_service_questions/review_v3_sequence_4_generation_authorization_activation_docker.sh
scripts/experiments/suggest_moving_service_questions/review_v3_sequence_4_generation_response_docker.sh
scripts/experiments/suggest_moving_service_questions/run_openai_stage_b_v3_sequence_4_generation_docker.sh
scripts/experiments/suggest_moving_service_questions/run_v3_sequence_4_live_generation_operator.zsh
scripts/experiments/suggest_moving_service_questions/verify_v3_sequence_4_generation_authorization_docker.sh
COMMANDS
sort -u "$rehearsal_root/compliant/invoked-public-commands.txt" >"$rehearsal_root/actual.txt"
cmp -s "$expected" "$rehearsal_root/actual.txt"
cat "$rehearsal_root"/*/command-coverage.tsv >"$rehearsal_root/command-coverage.tsv"
[ "$(awk -F '\t' '$3 == "passed" {print $1}' "$rehearsal_root/command-coverage.tsv" | sort -u | wc -l)" -eq 12 ]
[ "$(awk -F '\t' '$3 == "passed" {print $2}' "$rehearsal_root/command-coverage.tsv" | sort -u | wc -l)" -eq 5 ]
cmp -s "$real_execution" "$real_closed"
[ "$(sha256sum "$real_execution" | cut -d' ' -f1)" = "$before_manifest" ]
[ -z "$(find "$real_generation_state" -maxdepth 2 -name '004-storage_unknown-generation-v3*' -print 2>/dev/null)" ]
echo 'exact_public_commands_exercised=12'
echo 'synthetic_preflight_calls=0'
echo 'compliant_generation_calls=1'
echo 'prose_rejection_generation_calls=1'
echo 'structural_failure_generation_calls=1'
echo 'semantic_failure_generation_calls=1'
echo 'prompt_policy_stress_generation_calls=1'
echo 'compliant_validation_passed=true'
echo 'compliant_grounding_review=approved_and_deleted'
echo 'prose_violation_codes_exact=true'
echo 'fallback_identity_exact=true'
echo 'structural_failure_classification=passed'
echo 'semantic_failure_classification=passed'
echo 'structural_semantic_distinction=true'
echo 'prompt_policy_stricter_than_validator=true'
echo 'permanent_closed_restored=true'
echo 'second_use_rejected=true'
