#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
[ "$(pwd -P)" = "$root" ] || { echo "Run from the GoTime repository root." >&2; exit 2; }
command -v docker >/dev/null
command -v zsh >/dev/null

closed_manifest="$root/docs/experiments/suggest-moving-service-questions/v2-pilot/closed-execution-manifest.json"
execution_manifest="$root/docs/experiments/suggest-moving-service-questions/v2-pilot/execution-manifest.json"
cmp -s "$execution_manifest" "$closed_manifest"
before_manifest=$(sha256sum "$execution_manifest" | cut -d' ' -f1)
real_state="$root/.local/evaluations/suggest-moving-service-questions/moving-service-stage-b-v2-pilot-20260802"
[ -z "$(find "$real_state" -maxdepth 2 -name '004-storage_unknown*' -print 2>/dev/null)" ]

sandbox=$(mktemp -d "$root/.sequence4-readiness-rehearsal.XXXXXX")
rendered="/tmp/gotime-v2-sequence-4-readiness-rehearsal-$$.toml"
operator_output="/tmp/gotime-sequence4-rehearsal-output-$$"
operator_error="/tmp/gotime-sequence4-rehearsal-error-$$"
cleanup() {
  rm -f "$rendered"
  rm -f "$operator_output" "$operator_error"
  case "$sandbox" in "$root"/.sequence4-readiness-rehearsal.*) rm -rf "$sandbox";; esac
}
trap cleanup EXIT INT TERM HUP

cp -R "$root/scripts" "$sandbox/scripts"
cp -R "$root/docs" "$sandbox/docs"
cp -R "$root/backend" "$sandbox/backend"

field() {
  printf '%s\n' "$1" | sed -n "s/^$2=//p" | sed -n '1p'
}

approved=$(date -u -d '10 seconds ago' '+%Y-%m-%dT%H:%M:%SZ')
activated=$(date -u -d '5 seconds ago' '+%Y-%m-%dT%H:%M:%SZ')
expires=$(date -u -d "$activated + 900 seconds" '+%Y-%m-%dT%H:%M:%SZ')

cd "$sandbox"
render_output=$(sh scripts/experiments/suggest_moving_service_questions/render_v2_sequence_4_preflight_authorization_candidate_docker.sh \
  --output "$rendered" --approver "Synthetic Approver" --approved-at "$approved" \
  --activated-at "$activated" --expires-at "$expires" --reason "Synthetic readiness rehearsal")
artifact_digest=$(field "$render_output" sha256)
[ -n "$artifact_digest" ]

install_output=$(sh scripts/experiments/suggest_moving_service_questions/install_v2_sequence_4_preflight_authorization_for_review_docker.sh \
  --source "$rendered" --expected-sha256 "$artifact_digest")
installed_digest=$(field "$install_output" sha256)
installation_digest=$(field "$install_output" installation_record_sha256)
[ "$installed_digest" = "$artifact_digest" ]
[ -n "$installation_digest" ]

reviewed_at=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
review_output=$(sh scripts/experiments/suggest_moving_service_questions/review_v2_sequence_4_preflight_authorization_activation_docker.sh \
  --artifact-sha256 "$installed_digest" --reviewer "Synthetic Reviewer" --decision approve \
  --reviewed-at "$reviewed_at" --notes "Synthetic activation approval")
activation_review_digest=$(field "$review_output" review_sha256)
[ -n "$activation_review_digest" ]

plan_output=$(sh scripts/experiments/suggest_moving_service_questions/plan_v2_sequence_4_preflight_authorization_activation_docker.sh \
  --artifact-sha256 "$installed_digest" --installation-record-sha256 "$installation_digest" \
  --activation-review-sha256 "$activation_review_digest")
[ "$(field "$plan_output" writes_performed)" = false ]
printf '%s\n' "$plan_output" | grep -F '004-storage_unknown-preflight-authorization.toml' >/dev/null

activation_output=$(sh scripts/experiments/suggest_moving_service_questions/activate_v2_sequence_4_preflight_authorization_docker.sh \
  --artifact-sha256 "$installed_digest" --installation-record-sha256 "$installation_digest" \
  --activation-review-sha256 "$activation_review_digest" --operator "Synthetic Operator" \
  --operator-intent "AUTHORIZE_ONE_STORAGE_UNKNOWN_V2_PREFLIGHT_ONLY")
[ "$(field "$activation_output" transaction_state)" = committed ]

exec 9<<'SYNTHETIC_CREDENTIAL'
synthetic-readiness-credential-never-print
SYNTHETIC_CREDENTIAL
GOTIME_V2_SEQUENCE_4_OFFLINE_TEST=1 GOTIME_V2_SEQUENCE_4_SYNTHETIC_INPUT_FD=9 \
  zsh scripts/experiments/suggest_moving_service_questions/run_v2_sequence_4_live_preflight_operator.zsh >"$operator_output" 2>"$operator_error"
if grep -F 'synthetic-readiness-credential-never-print' "$operator_output" "$operator_error" >/dev/null; then
  exit 7
fi
rm -f "$operator_output" "$operator_error"

run_state="$sandbox/.local/evaluations/suggest-moving-service-questions/moving-service-stage-b-v2-pilot-20260802"
audit="$run_state/004-storage_unknown-preflight.json"
evidence="$run_state/004-storage_unknown-preflight-evidence.json"
closure="$run_state/004-storage_unknown-preflight-closure.json"
[ -f "$audit" ] && [ -f "$evidence" ] && [ -f "$closure" ]
grep -F '"preflight_attempted": true' "$audit" >/dev/null
grep -F '"preflight_succeeded": true' "$audit" >/dev/null
grep -F '"generation_attempted": false' "$audit" >/dev/null
grep -F '"authorization_consumed": true' "$audit" >/dev/null
cmp -s "$sandbox/docs/experiments/suggest-moving-service-questions/v2-pilot/execution-manifest.json" \
  "$sandbox/docs/experiments/suggest-moving-service-questions/v2-pilot/closed-execution-manifest.json"
[ ! -e "$run_state/004-storage_unknown-preflight-authorization.toml" ]

evidence_digest=$(sha256sum "$evidence" | cut -d' ' -f1)
input_tokens=$(sed -n 's/^[[:space:]]*"input_tokens": \([0-9][0-9]*\),*$/\1/p' "$evidence")
conservative_cost=$(sed -n 's/^[[:space:]]*"conservative_maximum_generation_cost": "\([0-9.][0-9.]*\)",*$/\1/p' "$evidence")
[ -n "$input_tokens" ] && [ -n "$conservative_cost" ]
evidence_review_output=$(sh scripts/experiments/suggest_moving_service_questions/review_v2_sequence_4_preflight_evidence_docker.sh \
  --evidence-sha256 "$evidence_digest" --input-tokens "$input_tokens" --conservative-cost "$conservative_cost" \
  --reviewer "Synthetic Evidence Reviewer" --decision approve --reviewed-at "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" \
  --token-count-plausible true --cost-within-limit true --frozen-bindings-confirmed true \
  --evidence-history-confirmed true --notes "Immediate synthetic evidence approval")
[ "$(field "$evidence_review_output" generation_gate_binding_eligible)" = true ]
[ -f "$run_state/004-storage_unknown-preflight-review.json" ]

if GOTIME_V2_SEQUENCE_4_OFFLINE_TEST=1 zsh scripts/experiments/suggest_moving_service_questions/run_v2_sequence_4_live_preflight_operator.zsh </dev/null >/dev/null 2>&1; then
  exit 8
fi

cd "$root"
cmp -s "$execution_manifest" "$closed_manifest"
[ "$(sha256sum "$execution_manifest" | cut -d' ' -f1)" = "$before_manifest" ]
[ -z "$(find "$real_state" -maxdepth 2 -name '004-storage_unknown*' -print 2>/dev/null)" ]

echo 'synthetic_rehearsal=passed'
echo 'fake_preflight_requests=1'
echo 'generation_requests=0'
echo 'evidence_review=approved'
echo 'authorization_closed=true'
echo 'second_use_rejected=true'
