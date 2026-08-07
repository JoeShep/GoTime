#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
[ "$(pwd -P)" = "$root" ] || exit 2
[ -n "${GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY:-}" ] || exit 3
[ "${GOTIME_MOVING_SERVICE_EVAL_ENABLED:-}" = "1" ] || exit 4
[ "${GOTIME_MOVING_SERVICE_EVAL_OPERATOR_INTENT:-}" = "AUTHORIZE_ONE_STORAGE_UNKNOWN_V2_PREFLIGHT_ONLY" ] || exit 5
network_args=""
[ "${GOTIME_V2_SEQUENCE_4_OFFLINE_TEST:-}" = "1" ] && network_args="--network none"
run_state="$root/.local/evaluations/suggest-moving-service-questions/moving-service-stage-b-v2-pilot-20260802"
exec docker run --rm $network_args --user "$(id -u):$(id -g)" --read-only \
  --tmpfs /tmp:rw,nosuid,nodev,noexec,size=64m --volume "$root:/workspace:ro" \
  --volume "$root/docs/experiments/suggest-moving-service-questions/v2-pilot:/workspace/docs/experiments/suggest-moving-service-questions/v2-pilot:rw" \
  --volume "$run_state:/workspace/.local/evaluations/suggest-moving-service-questions/moving-service-stage-b-v2-pilot-20260802:rw" \
  --workdir /workspace --env GOTIME_MOVING_SERVICE_EVAL_ENABLED=1 \
  --env GOTIME_MOVING_SERVICE_EVAL_OPERATOR_INTENT=AUTHORIZE_ONE_STORAGE_UNKNOWN_V2_PREFLIGHT_ONLY \
  --env GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY \
  --env GOTIME_V2_SEQUENCE_4_OFFLINE_TEST \
  gotime-moving-service-stage-b:openai-2.45.0 sh \
  scripts/experiments/suggest_moving_service_questions/run_openai_stage_b_v2_sequence_4_preflight_container.sh
