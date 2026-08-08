#!/bin/sh
set -eu
source_root=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
[ "$(pwd -P)" = "$source_root" ] || exit 2
command -v docker >/dev/null; command -v zsh >/dev/null
cmp -s docs/experiments/suggest-moving-service-questions/v2-pilot/execution-manifest.json docs/experiments/suggest-moving-service-questions/v2-pilot/closed-execution-manifest.json
before=$(sha256sum docs/experiments/suggest-moving-service-questions/v2-pilot/execution-manifest.json | cut -d ' ' -f1)
root=$(mktemp -d "$source_root/.v3-sequence1-preflight-rehearsal.XXXXXX")
cleanup() { rm -rf "$root"; rm -f /tmp/gotime-v3-sequence-1-preflight-authorization.toml; }
trap cleanup EXIT INT TERM HUP
repository="$root/repository"; mkdir -p "$repository"
cp -R scripts docs backend "$repository/"
state="$repository/.local/evaluations/suggest-moving-service-questions/moving-service-stage-b-v3-pilot-20260807"
commands="$root/commands.tsv"; : > "$commands"
record() { printf '%s\t%s\tpassed\n' "$1" "$2" >> "$commands"; }
field() { printf '%s\n' "$1" | sed -n "s/^$2=//p" | sed -n '1p'; }
now=$(date -u +%Y-%m-%dT%H:%M:%SZ)
approved=$(date -u -d '10 seconds ago' +%Y-%m-%dT%H:%M:%SZ)
activated=$(date -u -d '5 seconds ago' +%Y-%m-%dT%H:%M:%SZ)
expires=$(date -u -d "$activated + 900 seconds" +%Y-%m-%dT%H:%M:%SZ)
cd "$repository"
export GOTIME_V3_SEQUENCE_1_PREFLIGHT_OFFLINE_TEST=1

render_cmd=scripts/experiments/suggest_moving_service_questions/render_v3_sequence_1_preflight_authorization_docker.sh
rendered=$(sh "$render_cmd" --approver "Synthetic Approver" --approved-at "$approved" --activated-at "$activated" --expires-at "$expires" --reason "Synthetic exact-command rehearsal"); record "$render_cmd" main
artifact=$(field "$rendered" sha256)
install_cmd=scripts/experiments/suggest_moving_service_questions/install_v3_sequence_1_preflight_authorization_for_review_docker.sh
installed=$(sh "$install_cmd" --expected-sha256 "$artifact"); record "$install_cmd" main
installation=$(field "$installed" installation_record_digest)
review_cmd=scripts/experiments/suggest_moving_service_questions/review_v3_sequence_1_preflight_authorization_activation_docker.sh
reviewed=$(sh "$review_cmd" --artifact-sha256 "$artifact" --reviewer "Synthetic Reviewer" --decision approve --reviewed-at "$now" --notes "Synthetic activation approval"); record "$review_cmd" main
review=$(field "$reviewed" review_sha256)
plan_cmd=scripts/experiments/suggest_moving_service_questions/plan_v3_sequence_1_preflight_authorization_activation_docker.sh
planned=$(sh "$plan_cmd" --artifact-sha256 "$artifact" --installation-record-sha256 "$installation" --activation-review-sha256 "$review"); record "$plan_cmd" main
[ "$(field "$planned" writes_performed)" = false ]
activate_cmd=scripts/experiments/suggest_moving_service_questions/activate_v3_sequence_1_preflight_authorization_docker.sh
active=$(sh "$activate_cmd" --artifact-sha256 "$artifact" --installation-record-sha256 "$installation" --activation-review-sha256 "$review" --operator "Synthetic Operator" --operator-intent AUTHORIZE_ONE_STORAGE_UNKNOWN_V3_PREFLIGHT_ONLY); record "$activate_cmd" main
[ "$(field "$active" transaction_state)" = committed ]
verify_cmd=scripts/experiments/suggest_moving_service_questions/verify_v3_sequence_1_preflight_authorization_docker.sh
sh "$verify_cmd" >/dev/null; record "$verify_cmd" main

operator_cmd=scripts/experiments/suggest_moving_service_questions/run_v3_live_preflight_operator.zsh
launcher_cmd=scripts/experiments/suggest_moving_service_questions/run_openai_stage_b_v3_sequence_1_preflight_docker.sh
stdout="$root/operator.stdout"; stderr="$root/operator.stderr"
exec 9<<'EOF'
synthetic-v3-preflight-credential-never-print
EOF
GOTIME_V3_SEQUENCE_1_PREFLIGHT_SYNTHETIC_INPUT_FD=9 zsh "$operator_cmd" >"$stdout" 2>"$stderr"; record "$operator_cmd" main; record "$launcher_cmd" main
! grep -F 'synthetic-v3-preflight-credential-never-print' "$stdout" "$stderr" "$state"/*.json
audit="$state/001-storage_unknown-preflight.json"; evidence="$state/001-storage_unknown-preflight-evidence.json"
test -f "$audit" -a -f "$evidence"
grep -F '"preflight_request_count": 1' "$audit" >/dev/null
grep -F '"generation_request_count": 0' "$audit" >/dev/null
evidence_digest=$(sha256sum "$evidence" | cut -d ' ' -f1)
evidence_review_cmd=scripts/experiments/suggest_moving_service_questions/review_v3_sequence_1_preflight_evidence_docker.sh
reviewed_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)
evidence_review=$(sh "$evidence_review_cmd" --evidence-sha256 "$evidence_digest" --input-tokens 2300 --conservative-cost 0.0017200 --reviewer "Synthetic Evidence Reviewer" --decision approve --reviewed-at "$reviewed_at" --token-count-plausible true --cost-within-limit true --frozen-bindings-confirmed true --evidence-history-confirmed true --notes "Immediate synthetic approval"); record "$evidence_review_cmd" main
[ "$(field "$evidence_review" generation_gate_binding_eligible)" = true ]
binding_cmd=scripts/experiments/suggest_moving_service_questions/resolve_v3_sequence_4_generation_candidate_binding_docker.sh
binding=$(sh "$binding_cmd"); record "$binding_cmd" main
[ "$(field "$binding" writes_performed)" = false ] && [ "$(field "$binding" generation_authorized)" = false ]
close_cmd=scripts/experiments/suggest_moving_service_questions/close_v3_sequence_1_preflight_authorization_docker.sh
sh "$close_cmd" --reason success >/dev/null; record "$close_cmd" main
cmp -s docs/experiments/suggest-moving-service-questions/v2-pilot/execution-manifest.json docs/experiments/suggest-moving-service-questions/v2-pilot/closed-execution-manifest.json
if GOTIME_V3_SEQUENCE_1_PREFLIGHT_SYNTHETIC_INPUT_FD=9 zsh "$operator_cmd" >/dev/null 2>&1; then exit 7; fi

# Exercise fixed expired-package cleanup in a second isolated repository.
cd "$source_root"; rm -f /tmp/gotime-v3-sequence-1-preflight-authorization.toml
cleanup_repo="$root/cleanup-repository"; mkdir -p "$cleanup_repo"; cp -R scripts docs backend "$cleanup_repo/"; cd "$cleanup_repo"
export GOTIME_V3_SEQUENCE_1_PREFLIGHT_OFFLINE_TEST=1
cleanup_base="2030-01-01T00:00:10Z"; cleanup_expiry="2030-01-01T00:15:05Z"
export GOTIME_V3_SEQUENCE_1_PREFLIGHT_SYNTHETIC_NOW="$cleanup_base"
cleanup_render=$(sh "$render_cmd" --approver "Synthetic Approver" --approved-at "2030-01-01T00:00:00Z" --activated-at "2030-01-01T00:00:05Z" --expires-at "$cleanup_expiry" --reason "Synthetic expired cleanup"); cleanup_artifact=$(field "$cleanup_render" sha256)
cleanup_install=$(sh "$install_cmd" --expected-sha256 "$cleanup_artifact")
sh "$review_cmd" --artifact-sha256 "$cleanup_artifact" --reviewer "Synthetic Reviewer" --decision approve --reviewed-at "$cleanup_base" --notes "Synthetic review" >/dev/null
export GOTIME_V3_SEQUENCE_1_PREFLIGHT_SYNTHETIC_NOW="2030-01-01T00:15:06Z"
cleanup_cmd=scripts/experiments/suggest_moving_service_questions/cleanup_v3_sequence_1_expired_review_package_docker.sh
dry=$(sh "$cleanup_cmd"); [ "$(field "$dry" deleted)" = false ]
deleted=$(sh "$cleanup_cmd" --confirm-delete --operator "Synthetic Operator"); [ "$(field "$deleted" deleted)" = true ]; record "$cleanup_cmd" cleanup

cd "$source_root"
expected="$root/expected.txt"; actual="$root/actual.txt"
printf '%s\n' "$render_cmd" "$install_cmd" "$review_cmd" "$plan_cmd" "$activate_cmd" "$verify_cmd" "$operator_cmd" "$launcher_cmd" "$evidence_review_cmd" "$binding_cmd" "$close_cmd" "$cleanup_cmd" | sort -u > "$expected"
cut -f1 "$commands" | sort -u > "$actual"; cmp -s "$expected" "$actual"
test "$(cut -f1 "$actual" | wc -l)" -eq 12
test "$before" = "$(sha256sum docs/experiments/suggest-moving-service-questions/v2-pilot/execution-manifest.json | cut -d ' ' -f1)"
printf '%s\n' 'exact_public_commands_exercised=12' 'synthetic_input_tokens=2300' 'synthetic_preflight_calls=1' 'synthetic_generation_calls=0' 'automatic_retries=0' 'credential_non_disclosure=true' 'evidence_review_approved_in_time=true' 'generation_binding_dry_run=true' 'permanent_closed_restored=true' 'second_use_rejected=true' 'synthetic_cleanup_rehearsed=true'
