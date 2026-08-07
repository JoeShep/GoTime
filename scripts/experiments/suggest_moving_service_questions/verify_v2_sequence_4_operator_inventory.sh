#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
[ "$(pwd -P)" = "$root" ] || { echo "Run from the GoTime repository root." >&2; exit 2; }

runbook=docs/experiments/suggest-moving-service-questions/v2-pilot/sequence-4-operator-runbook.md
candidate=docs/experiments/suggest-moving-service-questions/v2-pilot/authorization-review/phase-candidates/sequence-4/inactive-sequence-4-preflight-authorization-candidate.toml
manifest=docs/experiments/suggest-moving-service-questions/v2-pilot/authorization-review/phase-candidates/sequence-4/sequence-4-candidate-manifest.json

[ "$(sha256sum "$candidate" | cut -d' ' -f1)" = "a9a20f8933adfd63c0e6959795284c7287f4c1227cf976a4ac19e443c3b39f2c" ]
[ "$(sha256sum "$manifest" | cut -d' ' -f1)" = "a6ce4574ce8c787fb8cff511a264fa9f0e5a265c608e2496cf6ed42a701da125" ]
grep -F 'sequence `4`' "$runbook" >/dev/null
grep -F '`004-storage_unknown`' "$runbook" >/dev/null

for script in \
  render_v2_sequence_4_preflight_authorization_candidate_docker.sh \
  install_v2_sequence_4_preflight_authorization_for_review_docker.sh \
  review_v2_sequence_4_preflight_authorization_activation_docker.sh \
  plan_v2_sequence_4_preflight_authorization_activation_docker.sh \
  activate_v2_sequence_4_preflight_authorization_docker.sh \
  verify_v2_sequence_4_preflight_authorization_docker.sh \
  run_v2_sequence_4_live_preflight_operator.zsh \
  close_v2_sequence_4_preflight_authorization_docker.sh \
  review_v2_sequence_4_preflight_evidence_docker.sh
do
  path="scripts/experiments/suggest_moving_service_questions/$script"
  [ -f "$path" ]
  [ -x "$path" ]
  grep -F "$path" "$runbook" >/dev/null
done

if grep -F 'local status=' scripts/experiments/suggest_moving_service_questions/run_v2_sequence_4_live_preflight_operator.zsh >/dev/null; then
  exit 3
fi
grep -F 'local exit_code=$?' scripts/experiments/suggest_moving_service_questions/run_v2_sequence_4_live_preflight_operator.zsh >/dev/null

echo 'command_inventory=passed'
echo 'public_commands=9'
echo 'sequence=4'
echo 'audit_prefix=004-storage_unknown'
echo 'authoritative=false'
