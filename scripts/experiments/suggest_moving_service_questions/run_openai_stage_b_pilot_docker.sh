#!/bin/sh
set -eu

repository_root=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
if [ "$(pwd -P)" != "$repository_root" ]; then
    echo "Run this command from the GoTime repository root." >&2
    exit 2
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
    python scripts/experiments/suggest_moving_service_questions/run_openai_stage_b_pilot.py \
    --run-series moving-service-stage-b-pilot-20260801 \
    --sequence 3 \
    --fixture storage_unknown \
    --operator-intent AUTHORIZE_ONE_STORAGE_UNKNOWN_STAGE_B_PREFLIGHT_AND_GENERATION
