#!/bin/sh
set -eu

if [ -z "${GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY:-}" ]; then
    echo "The v2 pilot credential is unavailable in the container." >&2
    exit 3
fi
if [ "${GOTIME_V2_PILOT_LAUNCHER_OFFLINE_TEST:-}" = "1" ]; then
    exec python scripts/experiments/suggest_moving_service_questions/test_v2_launcher_credential_boundary.py
fi

exec python scripts/experiments/suggest_moving_service_questions/run_openai_stage_b_v2_pilot.py \
    --run-series moving-service-stage-b-v2-pilot-20260802 \
    --sequence 1 \
    --fixture storage_unknown \
    --operator-intent AUTHORIZE_ONE_STORAGE_UNKNOWN_V2_PREFLIGHT_AND_GENERATION
