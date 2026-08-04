#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
[ "$(pwd -P)" = "$root" ] || { echo "Run from the GoTime repository root." >&2; exit 2; }
[ -n "${GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY:-}" ] || { echo "The v2 preflight credential must be exported and nonempty." >&2; exit 3; }
[ "${GOTIME_MOVING_SERVICE_EVAL_ENABLED:-}" = "1" ] || { echo "Exact v2 operator enablement is required." >&2; exit 4; }
[ "${GOTIME_MOVING_SERVICE_EVAL_OPERATOR_INTENT:-}" = "AUTHORIZE_ONE_STORAGE_UNKNOWN_V2_PREFLIGHT_ONLY" ] || { echo "Exact v2 preflight operator intent is required." >&2; exit 5; }
if [ "${GOTIME_V2_TWO_GATE_OFFLINE_TEST:-}" = "1" ]; then
  exec docker run --rm --network none --user "$(id -u):$(id -g)" --read-only \
    --tmpfs /tmp:rw,nosuid,nodev,noexec,size=64m --volume "$root:/workspace:rw" \
    --workdir /workspace --env GOTIME_MOVING_SERVICE_EVAL_ENABLED=1 \
    --env GOTIME_MOVING_SERVICE_EVAL_OPERATOR_INTENT=AUTHORIZE_ONE_STORAGE_UNKNOWN_V2_PREFLIGHT_ONLY \
    --env GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY --env GOTIME_V2_TWO_GATE_OFFLINE_TEST=1 \
    gotime-moving-service-stage-b:openai-2.45.0 sh \
    scripts/experiments/suggest_moving_service_questions/run_openai_stage_b_v2_preflight_container.sh
fi
exec docker run --rm --user "$(id -u):$(id -g)" --read-only \
  --tmpfs /tmp:rw,nosuid,nodev,noexec,size=64m --volume "$root:/workspace:ro" \
  --volume "$root/.local:/workspace/.local:rw" \
  --volume "$root/docs/experiments/suggest-moving-service-questions/v2-pilot:/workspace/docs/experiments/suggest-moving-service-questions/v2-pilot:rw" \
  --workdir /workspace --env GOTIME_MOVING_SERVICE_EVAL_ENABLED=1 \
  --env GOTIME_MOVING_SERVICE_EVAL_OPERATOR_INTENT=AUTHORIZE_ONE_STORAGE_UNKNOWN_V2_PREFLIGHT_ONLY \
  --env GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY \
  gotime-moving-service-stage-b:openai-2.45.0 sh \
  scripts/experiments/suggest_moving_service_questions/run_openai_stage_b_v2_preflight_container.sh
