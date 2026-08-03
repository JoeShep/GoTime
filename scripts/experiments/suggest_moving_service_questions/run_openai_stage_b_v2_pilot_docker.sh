#!/bin/sh
set -eu

repository_root=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
if [ "$(pwd -P)" != "$repository_root" ]; then
    echo "Run this command from the GoTime repository root." >&2
    exit 2
fi
if [ -z "${GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY:-}" ]; then
    echo "The v2 pilot credential must be exported and nonempty." >&2
    exit 3
fi

network_mode=none
if [ "${GOTIME_V2_PILOT_LAUNCHER_OFFLINE_TEST:-}" != "1" ]; then
    echo "The committed v2 launcher is offline-only and repository authorization is closed." >&2
    exit 4
fi

exec docker run --rm \
    --network "$network_mode" \
    --user "$(id -u):$(id -g)" \
    --read-only \
    --tmpfs /tmp:rw,nosuid,nodev,noexec,size=64m \
    --volume "$repository_root:/workspace:ro" \
    --workdir /workspace \
    --env GOTIME_MOVING_SERVICE_EVAL_ENABLED=1 \
    --env GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY \
    --env GOTIME_V2_PILOT_LAUNCHER_OFFLINE_TEST=1 \
    gotime-moving-service-stage-b:openai-2.45.0 \
    sh scripts/experiments/suggest_moving_service_questions/run_openai_stage_b_v2_pilot_container.sh
