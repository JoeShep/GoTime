#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
[ "$(pwd -P)" = "$root" ] || exit 2
commands='render_v3_sequence_4_generation_authorization_candidate_docker.sh
install_v3_sequence_4_generation_authorization_for_review_docker.sh
review_v3_sequence_4_generation_authorization_activation_docker.sh
plan_v3_sequence_4_generation_authorization_activation_docker.sh
activate_v3_sequence_4_generation_authorization_docker.sh
verify_v3_sequence_4_generation_authorization_docker.sh
run_openai_stage_b_v3_sequence_4_generation_docker.sh
run_v3_sequence_4_live_generation_operator.zsh
review_v3_sequence_4_generation_response_docker.sh
delete_v3_sequence_4_generation_response_evidence_docker.sh
close_v3_sequence_4_generation_authorization_docker.sh
cleanup_v3_sequence_4_expired_generation_review_package_docker.sh'
printf '%s\n' "$commands" | while IFS= read -r name; do
  path="$root/scripts/experiments/suggest_moving_service_questions/$name"
  [ -f "$path" ] && [ -x "$path" ] || exit 4
  grep -q "scripts/experiments/suggest_moving_service_questions/$name" \
    scripts/experiments/suggest_moving_service_questions/rehearse_v3_sequence_4_generation_workflow.sh || exit 5
done
grep -q 'AUTHORIZE_ONE_STORAGE_UNKNOWN_V3_GENERATION_ONLY' \
  scripts/experiments/suggest_moving_service_questions/run_v3_sequence_4_live_generation_operator.zsh
grep -q -- '--network none' \
  scripts/experiments/suggest_moving_service_questions/v3_sequence_4_generation_operator_docker.sh
! grep -q -- '--sequence' \
  docs/experiments/suggest-moving-service-questions/v3-generation-operator-runbook.md
printf 'generation_operator_commands=12\n'
printf 'fixed_sequence=4\n'
printf 'inventory_valid=true\n'
