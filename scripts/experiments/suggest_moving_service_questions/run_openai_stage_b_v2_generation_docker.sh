#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
[ "$(pwd -P)" = "$root" ] || { echo "Run from the GoTime repository root." >&2; exit 2; }
[ -n "${GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY:-}" ] || { echo "The v2 generation credential must be exported and nonempty." >&2; exit 3; }
[ "${GOTIME_V2_TWO_GATE_OFFLINE_TEST:-}" = "1" ] || { echo "The committed generation launcher is closed and offline-only." >&2; exit 4; }
exec docker run --rm --network none --user "$(id -u):$(id -g)" --read-only \
  --tmpfs /tmp:rw,nosuid,nodev,noexec,size=64m --volume "$root:/workspace:ro" \
  --workdir /workspace --env GOTIME_MOVING_SERVICE_EVAL_ENABLED=1 \
  --env GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY --env GOTIME_V2_TWO_GATE_OFFLINE_TEST=1 \
  gotime-moving-service-stage-b:openai-2.45.0 sh \
  scripts/experiments/suggest_moving_service_questions/run_openai_stage_b_v2_generation_container.sh
