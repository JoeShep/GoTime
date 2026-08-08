#!/bin/sh
set -eu
source_root=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
[ "$(pwd -P)" = "$source_root" ] || exit 2
command -v docker >/dev/null; command -v zsh >/dev/null
cmp -s docs/experiments/suggest-moving-service-questions/v2-pilot/execution-manifest.json docs/experiments/suggest-moving-service-questions/v2-pilot/closed-execution-manifest.json
before=$(sha256sum docs/experiments/suggest-moving-service-questions/v2-pilot/execution-manifest.json | cut -d ' ' -f1)
root=$(mktemp -d "$source_root/.v4-sequence1-preflight-rehearsal.XXXXXX")
cleanup() { rm -rf "$root"; rm -f /tmp/gotime-v4-sequence-1-preflight-authorization.toml; }
trap cleanup EXIT INT TERM HUP
repository="$root/repository"; mkdir -p "$repository"
cp -R scripts docs backend "$repository/"
state="$repository/.local/evaluations/suggest-moving-service-questions/moving-service-stage-b-v4-pilot-20260808"
commands="$root/commands.tsv"; : > "$commands"
record() { printf '%s\t%s\tpassed\n' "$1" "$2" >> "$commands"; }
field() { printf '%s\n' "$1" | sed -n "s/^$2=//p" | sed -n '1p'; }
now=$(date -u +%Y-%m-%dT%H:%M:%SZ)
approved=$(date -u -d '10 seconds ago' +%Y-%m-%dT%H:%M:%SZ)
activated=$(date -u -d '5 seconds ago' +%Y-%m-%dT%H:%M:%SZ)
expires=$(date -u -d "$activated + 900 seconds" +%Y-%m-%dT%H:%M:%SZ)
cd "$repository"
export GOTIME_V4_SEQUENCE_1_PREFLIGHT_OFFLINE_TEST=1

render_cmd=scripts/experiments/suggest_moving_service_questions/render_v4_sequence_1_preflight_authorization_docker.sh
rendered=$(sh "$render_cmd" --approver "Synthetic Approver" --approved-at "$approved" --activated-at "$activated" --expires-at "$expires" --reason "Synthetic exact-command rehearsal"); record "$render_cmd" main
artifact=$(field "$rendered" sha256)
install_cmd=scripts/experiments/suggest_moving_service_questions/install_v4_sequence_1_preflight_authorization_for_review_docker.sh
installed=$(sh "$install_cmd" --expected-sha256 "$artifact"); record "$install_cmd" main
installation=$(field "$installed" installation_record_digest)
review_cmd=scripts/experiments/suggest_moving_service_questions/review_v4_sequence_1_preflight_authorization_activation_docker.sh
reviewed=$(sh "$review_cmd" --artifact-sha256 "$artifact" --reviewer "Synthetic Reviewer" --decision approve --reviewed-at "$now" --notes "Synthetic activation approval"); record "$review_cmd" main
review=$(field "$reviewed" review_sha256)
plan_cmd=scripts/experiments/suggest_moving_service_questions/plan_v4_sequence_1_preflight_authorization_activation_docker.sh
planned=$(sh "$plan_cmd" --artifact-sha256 "$artifact" --installation-record-sha256 "$installation" --activation-review-sha256 "$review"); record "$plan_cmd" main
[ "$(field "$planned" writes_performed)" = false ]
activate_cmd=scripts/experiments/suggest_moving_service_questions/activate_v4_sequence_1_preflight_authorization_docker.sh
active=$(sh "$activate_cmd" --artifact-sha256 "$artifact" --installation-record-sha256 "$installation" --activation-review-sha256 "$review" --operator "Synthetic Operator" --operator-intent AUTHORIZE_ONE_STORAGE_UNKNOWN_V4_PREFLIGHT_ONLY); record "$activate_cmd" main
[ "$(field "$active" transaction_state)" = committed ]
verify_cmd=scripts/experiments/suggest_moving_service_questions/verify_v4_sequence_1_preflight_authorization_docker.sh
sh "$verify_cmd" >/dev/null; record "$verify_cmd" main

operator_cmd=scripts/experiments/suggest_moving_service_questions/run_v4_live_preflight_operator.zsh
launcher_cmd=scripts/experiments/suggest_moving_service_questions/run_openai_stage_b_v4_sequence_1_preflight_docker.sh
stdout="$root/operator.stdout"; stderr="$root/operator.stderr"
exec 9<<'EOF'
synthetic-v4-preflight-credential-never-print
EOF
GOTIME_V4_SEQUENCE_1_PREFLIGHT_SYNTHETIC_INPUT_FD=9 zsh "$operator_cmd" >"$stdout" 2>"$stderr"; record "$operator_cmd" main; record "$launcher_cmd" main
! grep -F 'synthetic-v4-preflight-credential-never-print' "$stdout" "$stderr" "$state"/*.json
audit="$state/001-storage_unknown-preflight.json"; evidence="$state/001-storage_unknown-preflight-evidence.json"
test -f "$audit" -a -f "$evidence"
grep -F '"preflight_request_count": 1' "$audit" >/dev/null
grep -F '"generation_request_count": 0' "$audit" >/dev/null
for exact in \
  '"credential_lookup_attempted": true' \
  '"client_construction_attempted": true' \
  '"token_preflight_attempted": true' \
  '"token_preflight_succeeded": true' \
  '"ai_generation_attempted": false' \
  '"authorization_consumed": true' \
  '"authorization_reusable": false' \
  '"closure_verified": true' \
  '"permanent_closed_state_verified": true' \
  '"cached_input_tokens": null' \
  '"uncached_input_tokens": null' \
  '"provider_request_id": null' \
  '"request_identity_artifact_digest": "b5125e2075779306f0a4374676d442fa3016702bdb5143bc8e3a6b7173d9dd35"' \
  '"deterministic_request_digest": "f5a8c7e06d2ad9e133a5b0b92c322f09ed67205feb25314c5114fa1849fcdd0a"' \
  '"canonical_attempt_digest": "7a3c0f7ace4ee4289f4149224fc001b215e71d4cc168edea604516fd133f450d"' \
  '"provider_preflight_fingerprint": "15caaaaa6a3b43860c426c7555be7f4c7a6bf50d658c92c3c8564c1d43cb5656"' \
  '"frozen_v4_manifest_digest": "3cdbd2bf3606191aa52108d8284c8ab300d58a511f313f78a06be51d95fac649"' \
  '"authorization_consumed": true'; do
  grep -F "$exact" "$evidence" >/dev/null
done
grep -F '"authorization_digest":' "$evidence" >/dev/null
grep -F '"activation_record_digest":' "$evidence" >/dev/null
grep -F '"transaction_id":' "$evidence" >/dev/null
grep -F '"created_at":' "$evidence" >/dev/null
grep -F '"review_deadline":' "$evidence" >/dev/null
grep -F '"audit_sha256":' "$evidence" >/dev/null
grep -F '"consumption_record_sha256":' "$evidence" >/dev/null
grep -F '"closure_sha256":' "$evidence" >/dev/null
grep -F '"activation_record_sha256":' "$evidence" >/dev/null
grep -F '"transaction_journal_sha256":' "$evidence" >/dev/null
test -f "$state/001-storage_unknown-preflight-closure.json"
evidence_digest=$(sha256sum "$evidence" | cut -d ' ' -f1)
evidence_review_cmd=scripts/experiments/suggest_moving_service_questions/review_v4_sequence_1_preflight_evidence_docker.sh
reviewed_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)
evidence_review=$(sh "$evidence_review_cmd" --evidence-sha256 "$evidence_digest" --input-tokens 4242 --conservative-cost 0.0024242 --reviewer "Synthetic Evidence Reviewer" --decision approve --reviewed-at "$reviewed_at" --token-count-plausible true --cost-within-limit true --frozen-bindings-confirmed true --evidence-history-confirmed true --notes "Immediate synthetic approval"); record "$evidence_review_cmd" main
[ "$(field "$evidence_review" generation_gate_binding_eligible)" = true ]
binding_cmd=scripts/experiments/suggest_moving_service_questions/preview_v4_generation_candidate_binding_docker.sh
binding=$(sh "$binding_cmd"); record "$binding_cmd" main
[ "$(field "$binding" writes_performed)" = false ] && [ "$(field "$binding" generation_authorized)" = false ]
close_cmd=scripts/experiments/suggest_moving_service_questions/close_v4_sequence_1_preflight_authorization_docker.sh
sh "$close_cmd" --reason success >/dev/null; record "$close_cmd" main
cmp -s docs/experiments/suggest-moving-service-questions/v2-pilot/execution-manifest.json docs/experiments/suggest-moving-service-questions/v2-pilot/closed-execution-manifest.json
if GOTIME_V4_SEQUENCE_1_PREFLIGHT_SYNTHETIC_INPUT_FD=9 zsh "$operator_cmd" >/dev/null 2>&1; then exit 7; fi

# Exercise fixed expired-package cleanup in a second isolated repository.
cd "$source_root"; rm -f /tmp/gotime-v4-sequence-1-preflight-authorization.toml
cleanup_repo="$root/cleanup-repository"; mkdir -p "$cleanup_repo"; cp -R scripts docs backend "$cleanup_repo/"; cd "$cleanup_repo"
export GOTIME_V4_SEQUENCE_1_PREFLIGHT_OFFLINE_TEST=1
cleanup_base="2030-01-01T00:00:10Z"; cleanup_expiry="2030-01-01T00:15:05Z"
export GOTIME_V4_SEQUENCE_1_PREFLIGHT_SYNTHETIC_NOW="$cleanup_base"
cleanup_render=$(sh "$render_cmd" --approver "Synthetic Approver" --approved-at "2030-01-01T00:00:00Z" --activated-at "2030-01-01T00:00:05Z" --expires-at "$cleanup_expiry" --reason "Synthetic expired cleanup"); cleanup_artifact=$(field "$cleanup_render" sha256)
cleanup_install=$(sh "$install_cmd" --expected-sha256 "$cleanup_artifact")
sh "$review_cmd" --artifact-sha256 "$cleanup_artifact" --reviewer "Synthetic Reviewer" --decision approve --reviewed-at "$cleanup_base" --notes "Synthetic review" >/dev/null
export GOTIME_V4_SEQUENCE_1_PREFLIGHT_SYNTHETIC_NOW="2030-01-01T00:15:06Z"
cleanup_cmd=scripts/experiments/suggest_moving_service_questions/cleanup_v4_sequence_1_expired_review_package_docker.sh
dry=$(sh "$cleanup_cmd"); [ "$(field "$dry" deleted)" = false ]
deleted=$(sh "$cleanup_cmd" --confirm-delete --operator "Synthetic Operator"); [ "$(field "$deleted" deleted)" = true ]; record "$cleanup_cmd" cleanup

cd "$source_root"
expected="$root/expected.txt"; actual="$root/actual.txt"
printf '%s\n' "$render_cmd" "$install_cmd" "$review_cmd" "$plan_cmd" "$activate_cmd" "$verify_cmd" "$operator_cmd" "$launcher_cmd" "$evidence_review_cmd" "$binding_cmd" "$close_cmd" "$cleanup_cmd" | sort -u > "$expected"
cut -f1 "$commands" | sort -u > "$actual"; cmp -s "$expected" "$actual"
test "$(cut -f1 "$actual" | wc -l)" -eq 12
test "$before" = "$(sha256sum docs/experiments/suggest-moving-service-questions/v2-pilot/execution-manifest.json | cut -d ' ' -f1)"
printf '%s\n' 'exact_public_commands_exercised=12' 'synthetic_input_tokens=4242' 'synthetic_preflight_calls=1' 'synthetic_generation_calls=0' 'automatic_retries=0' 'credential_non_disclosure=true' 'evidence_review_approved_in_time=true' 'generation_binding_dry_run=true' 'permanent_closed_restored=true' 'second_use_rejected=true' 'synthetic_cleanup_rehearsed=true'
