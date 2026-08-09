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
real_generation_state="$source_root/.local/evaluations/suggest-moving-service-questions/moving-service-stage-b-v4-pilot-20260808"
[ -z "$(find "$real_generation_state" -maxdepth 2 -name '004-storage_unknown-generation-v4*' -print 2>/dev/null)" ]

rehearsal_root=$(mktemp -d "$source_root/.sequence4-v4-generation-rehearsal.XXXXXX")
cleanup() {
  cd "$source_root" || exit 9
  case "$rehearsal_root" in
    "$source_root"/.sequence4-v4-generation-rehearsal.*) rm -rf "$rehearsal_root" ;;
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
  mkdir -p "$sandbox/backend/app"
  cp "$source_root"/backend/app/*.py "$sandbox/backend/app/"
  state="$sandbox/.local/evaluations/suggest-moving-service-questions/moving-service-stage-b-v4-pilot-20260808"
  mkdir -p "$state"
  commands="$sandbox/invoked-public-commands.txt"
  rendered="/tmp/gotime-v4-sequence-4-generation-rehearsal-$$-$scenario.toml"
  rm -f "$rendered"
  approved=$(date -u -d '10 seconds ago' '+%Y-%m-%dT%H:%M:%SZ')
  activated=$(date -u -d '5 seconds ago' '+%Y-%m-%dT%H:%M:%SZ')
  expires=$(date -u -d "$activated + 900 seconds" '+%Y-%m-%dT%H:%M:%SZ')
  cd "$sandbox"
  export GOTIME_V4_SEQUENCE_4_GENERATION_OFFLINE_TEST=1
  preflight_output=$(sh scripts/experiments/suggest_moving_service_questions/v4_sequence_4_generation_operator_docker.sh \
    prepare-realistic-synthetic-preflight)
  [ "$(field "$preflight_output" realistic_completed_preflight_history)" = true ]
  [ "$(field "$preflight_output" historical_preflight_closure_valid)" = true ]

  command_path=scripts/experiments/suggest_moving_service_questions/render_v4_sequence_4_generation_authorization_candidate_docker.sh
  record_command "$command_path" "$commands"
  render_output=$(sh "$command_path" --output "$rendered" --approver "Synthetic Approver" \
    --approved-at "$approved" --activated-at "$activated" --expires-at "$expires" \
    --reason "Synthetic exact-command rehearsal")
  artifact_digest=$(field "$render_output" sha256)

  command_path=scripts/experiments/suggest_moving_service_questions/install_v4_sequence_4_generation_authorization_for_review_docker.sh
  record_command "$command_path" "$commands"
  install_output=$(sh "$command_path" --source "$rendered" --expected-sha256 "$artifact_digest")
  installation_digest=$(field "$install_output" installation_record_digest)

  command_path=scripts/experiments/suggest_moving_service_questions/review_v4_sequence_4_generation_authorization_activation_docker.sh
  record_command "$command_path" "$commands"
  review_output=$(sh "$command_path" --artifact-sha256 "$artifact_digest" --reviewer "Synthetic Reviewer" \
    --decision approve --reviewed-at "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" --notes "Synthetic approval")
  activation_review_digest=$(field "$review_output" review_sha256)

  cleanup_rendered=/tmp/gotime-v4-sequence-4-generation-authorization.toml
  cp "$rendered" "$cleanup_rendered"
  command_path=scripts/experiments/suggest_moving_service_questions/cleanup_v4_sequence_4_expired_generation_review_package_docker.sh
  record_command "$command_path" "$commands"
  cleanup_output=$(GOTIME_V4_SEQUENCE_4_GENERATION_SYNTHETIC_NOW="$(date -u -d "$expires + 1 second" '+%Y-%m-%dT%H:%M:%SZ')" \
    sh "$command_path" --artifact-sha256 "$artifact_digest" \
    --installation-record-sha256 "$installation_digest" \
    --activation-review-sha256 "$activation_review_digest")
  [ "$(field "$cleanup_output" writes_performed)" = false ]
  rm -f "$cleanup_rendered"

  command_path=scripts/experiments/suggest_moving_service_questions/plan_v4_sequence_4_generation_authorization_activation_docker.sh
  record_command "$command_path" "$commands"
  plan_output=$(sh "$command_path" --artifact-sha256 "$artifact_digest" \
    --installation-record-sha256 "$installation_digest" --activation-review-sha256 "$activation_review_digest")
  [ "$(field "$plan_output" writes_performed)" = false ]

  command_path=scripts/experiments/suggest_moving_service_questions/activate_v4_sequence_4_generation_authorization_docker.sh
  record_command "$command_path" "$commands"
  activation_output=$(sh "$command_path" --artifact-sha256 "$artifact_digest" \
    --installation-record-sha256 "$installation_digest" --activation-review-sha256 "$activation_review_digest" \
    --operator "Synthetic Operator" --operator-intent "AUTHORIZE_ONE_STORAGE_UNKNOWN_V4_GENERATION_ONLY")
  [ "$(field "$activation_output" transaction_state)" = committed ]

  command_path=scripts/experiments/suggest_moving_service_questions/verify_v4_sequence_4_generation_authorization_docker.sh
  record_command "$command_path" "$commands"
  sh "$command_path" >/dev/null
  if [ "$scenario" = compliant ]; then
    live_boundary_output=$(sh scripts/experiments/suggest_moving_service_questions/v4_sequence_4_generation_operator_docker.sh \
      assert-live-entry-boundaries)
    printf '%s\n' "$live_boundary_output" >"$sandbox/live-boundary-output.txt"
    [ "$(field "$live_boundary_output" live_entry_positive_verified)" = true ]
    [ "$(field "$live_boundary_output" realistic_completed_preflight_history)" = true ]
    [ "$(field "$live_boundary_output" current_manifest_active_generation)" = true ]
    [ "$(field "$live_boundary_output" historical_preflight_closure_valid)" = true ]
    [ "$(field "$live_boundary_output" wrong_active_authorization_rejected_precredential)" = true ]
    [ "$(field "$live_boundary_output" wrong_active_manifest_rejected_precredential)" = true ]
  fi

  command_path=scripts/experiments/suggest_moving_service_questions/run_v4_sequence_4_live_generation_operator.zsh
  record_command "$command_path" "$commands"
  record_command scripts/experiments/suggest_moving_service_questions/run_openai_stage_b_v4_sequence_4_generation_docker.sh "$commands"
  stdout="$sandbox/operator.stdout"
  stderr="$sandbox/operator.stderr"
  exec 9<<'SYNTHETIC_CREDENTIAL'
synthetic-generation-credential-never-print
SYNTHETIC_CREDENTIAL
  if ! GOTIME_V4_SEQUENCE_4_GENERATION_OFFLINE_TEST=1 \
    GOTIME_V4_SEQUENCE_4_GENERATION_SYNTHETIC_SCENARIO="$scenario" \
    GOTIME_V4_SEQUENCE_4_GENERATION_SYNTHETIC_INPUT_FD=9 \
      zsh "$command_path" >"$stdout" 2>"$stderr"; then
    sed -n '1,20p' "$stderr" >&2
    exit 6
  fi
  if grep -F 'synthetic-generation-credential-never-print' "$stdout" "$stderr" "$state"/*.json >/dev/null 2>&1; then
    exit 7
  fi
  [ "$(field "$(cat "$stdout")" synthetic_client_constructions)" = 1 ]
  [ "$(field "$(cat "$stdout")" synthetic_generation_calls)" = 1 ]
  : >"$state/.network-disabled"
  audit="$state/004-storage_unknown-generation-v4-audit.json"
  [ -f "$audit" ]
  grep -F '"preflight_attempted": false' "$audit" >/dev/null
  grep -F '"generation_request_count": 1' "$audit" >/dev/null

  if [ "$scenario" = compliant ] || [ "$scenario" = prompt_policy_stress ]; then
    evidence="$state/004-storage_unknown-generation-v4-validated-response.json"
    evidence_digest=$(sha256sum "$evidence" | cut -d' ' -f1)
    command_path=scripts/experiments/suggest_moving_service_questions/review_v4_sequence_4_generation_response_docker.sh
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
    command_path=scripts/experiments/suggest_moving_service_questions/delete_v4_sequence_4_generation_response_evidence_docker.sh
    record_command "$command_path" "$commands"
    sh "$command_path" >/dev/null
    [ ! -e "$evidence" ]
  fi

  command_path=scripts/experiments/suggest_moving_service_questions/close_v4_sequence_4_generation_authorization_docker.sh
  record_command "$command_path" "$commands"
  sh "$command_path" --reason success >/dev/null
  cmp -s "$sandbox/docs/experiments/suggest-moving-service-questions/v2-pilot/execution-manifest.json" \
    "$sandbox/docs/experiments/suggest-moving-service-questions/v2-pilot/closed-execution-manifest.json"
  if GOTIME_V4_SEQUENCE_4_GENERATION_OFFLINE_TEST=1 zsh \
    scripts/experiments/suggest_moving_service_questions/run_v4_sequence_4_live_generation_operator.zsh \
    </dev/null >/dev/null 2>&1; then
    exit 8
  fi
  : >"$state/.second-use-rejected"
  assertion_output=$(sh scripts/experiments/suggest_moving_service_questions/v4_sequence_4_generation_operator_docker.sh \
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
scripts/experiments/suggest_moving_service_questions/activate_v4_sequence_4_generation_authorization_docker.sh
scripts/experiments/suggest_moving_service_questions/cleanup_v4_sequence_4_expired_generation_review_package_docker.sh
scripts/experiments/suggest_moving_service_questions/close_v4_sequence_4_generation_authorization_docker.sh
scripts/experiments/suggest_moving_service_questions/delete_v4_sequence_4_generation_response_evidence_docker.sh
scripts/experiments/suggest_moving_service_questions/install_v4_sequence_4_generation_authorization_for_review_docker.sh
scripts/experiments/suggest_moving_service_questions/plan_v4_sequence_4_generation_authorization_activation_docker.sh
scripts/experiments/suggest_moving_service_questions/render_v4_sequence_4_generation_authorization_candidate_docker.sh
scripts/experiments/suggest_moving_service_questions/review_v4_sequence_4_generation_authorization_activation_docker.sh
scripts/experiments/suggest_moving_service_questions/review_v4_sequence_4_generation_response_docker.sh
scripts/experiments/suggest_moving_service_questions/run_openai_stage_b_v4_sequence_4_generation_docker.sh
scripts/experiments/suggest_moving_service_questions/run_v4_sequence_4_live_generation_operator.zsh
scripts/experiments/suggest_moving_service_questions/verify_v4_sequence_4_generation_authorization_docker.sh
COMMANDS
sort -u "$rehearsal_root/compliant/invoked-public-commands.txt" >"$rehearsal_root/actual.txt"
cmp -s "$expected" "$rehearsal_root/actual.txt"
cat "$rehearsal_root"/*/command-coverage.tsv >"$rehearsal_root/command-coverage.tsv"
[ "$(awk -F '\t' '$3 == "passed" {print $1}' "$rehearsal_root/command-coverage.tsv" | sort -u | wc -l)" -eq 12 ]
[ "$(awk -F '\t' '$3 == "passed" {print $2}' "$rehearsal_root/command-coverage.tsv" | sort -u | wc -l)" -eq 5 ]
cmp -s "$real_execution" "$real_closed"
[ "$(sha256sum "$real_execution" | cut -d' ' -f1)" = "$before_manifest" ]
[ -z "$(find "$real_generation_state" -maxdepth 2 -name '004-storage_unknown-generation-v4*' -print 2>/dev/null)" ]
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
cat "$rehearsal_root/compliant/live-boundary-output.txt"
echo 'client_constructions_positive=1'
echo 'provider_generations_positive=1'
