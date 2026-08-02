#!/bin/sh
set -eu

repository_root=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
if [ "$(pwd -P)" != "$repository_root" ]; then
    echo "Run this command from the GoTime repository root." >&2
    exit 2
fi

if [ -z "${GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY:-}" ]; then
    echo "The Stage B evaluation credential must be exported and nonempty." >&2
    exit 3
fi

exec docker run --rm \
    --network bridge \
    --user "$(id -u):$(id -g)" \
    --read-only \
    --tmpfs /tmp:rw,nosuid,nodev,noexec,size=64m \
    --volume "$repository_root:/workspace" \
    --workdir /workspace \
    --env GOTIME_MOVING_SERVICE_EVAL_ENABLED=1 \
    --env GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY \
    gotime-moving-service-stage-b:openai-2.45.0 \
    sh scripts/experiments/suggest_moving_service_questions/run_openai_stage_b_pilot_container.sh
