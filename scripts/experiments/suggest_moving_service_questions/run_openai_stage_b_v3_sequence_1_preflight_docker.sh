#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
[ "$(pwd -P)" = "$root" ] || exit 2
state="$root/.local/evaluations/suggest-moving-service-questions"; mkdir -p "$state"
network_args=""
[ "${GOTIME_V3_SEQUENCE_1_PREFLIGHT_OFFLINE_TEST:-}" = "1" ] && network_args="--network none"
exec docker run --rm $network_args --user "$(id -u):$(id -g)" --read-only \
  --tmpfs /tmp/container:rw,nosuid,nodev,noexec,size=16m \
  --volume "$root:/workspace:ro" \
  --volume "$root/docs/experiments/suggest-moving-service-questions/v2-pilot:/workspace/docs/experiments/suggest-moving-service-questions/v2-pilot:rw" \
  --volume "$state:/workspace/.local/evaluations/suggest-moving-service-questions:rw" \
  --workdir /workspace --env PYTHONDONTWRITEBYTECODE=1 \
  --env GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY \
  --env GOTIME_MOVING_SERVICE_EVAL_ENABLED \
  --env GOTIME_MOVING_SERVICE_EVAL_OPERATOR_INTENT \
  --env GOTIME_V3_SEQUENCE_1_PREFLIGHT_OFFLINE_TEST \
  gotime-moving-service-stage-b:openai-2.45.0 sh \
  scripts/experiments/suggest_moving_service_questions/run_openai_stage_b_v3_sequence_1_preflight_container.sh
