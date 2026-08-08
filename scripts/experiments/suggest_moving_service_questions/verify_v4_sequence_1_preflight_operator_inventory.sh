#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
[ "$(pwd -P)" = "$root" ] || exit 2
runbook="$root/docs/experiments/suggest-moving-service-questions/v4-preflight-operator-runbook.md"
expected='render_v4_sequence_1_preflight_authorization_docker.sh
install_v4_sequence_1_preflight_authorization_for_review_docker.sh
review_v4_sequence_1_preflight_authorization_activation_docker.sh
plan_v4_sequence_1_preflight_authorization_activation_docker.sh
activate_v4_sequence_1_preflight_authorization_docker.sh
verify_v4_sequence_1_preflight_authorization_docker.sh
run_v4_live_preflight_operator.zsh
run_openai_stage_b_v4_sequence_1_preflight_docker.sh
review_v4_sequence_1_preflight_evidence_docker.sh
preview_v4_generation_candidate_binding_docker.sh
close_v4_sequence_1_preflight_authorization_docker.sh
cleanup_v4_sequence_1_expired_review_package_docker.sh'
actual=$(sed -n 's|.*scripts/experiments/suggest_moving_service_questions/\([A-Za-z0-9_.-]*\).*|\1|p' "$runbook" | sort -u)
for name in $expected; do
  printf '%s\n' "$actual" | grep -qx "$name"
  test -x "$root/scripts/experiments/suggest_moving_service_questions/$name"
done
test "$(printf '%s\n' "$expected" | wc -l)" -eq 12
! grep -Eq -- '--sequence|--version|--provider|--model|--fixture' "$runbook"
printf '%s\n' 'preflight_operator_commands=12' 'fixed_run_series=moving-service-stage-b-v4-pilot-20260808' 'fixed_sequence=1' 'inventory_valid=true'
