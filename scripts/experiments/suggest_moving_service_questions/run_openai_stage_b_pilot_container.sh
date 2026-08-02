#!/bin/sh
set -eu

if [ -z "${GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY:-}" ]; then
    echo "The Stage B evaluation credential is unavailable in the container." >&2
    exit 3
fi

exec python scripts/experiments/suggest_moving_service_questions/run_openai_stage_b_pilot.py \
    --run-series moving-service-stage-b-pilot-20260801 \
    --sequence 4 \
    --fixture storage_unknown \
    --operator-intent AUTHORIZE_ONE_STORAGE_UNKNOWN_STAGE_B_PREFLIGHT_AND_GENERATION
