#!/bin/sh
set -eu
[ -n "${GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY:-}" ] || { echo "The v2 preflight credential is unavailable in the container." >&2; exit 3; }
[ "${GOTIME_MOVING_SERVICE_EVAL_ENABLED:-}" = "1" ] || { echo "Exact v2 operator enablement is unavailable in the container." >&2; exit 4; }
[ "${GOTIME_MOVING_SERVICE_EVAL_OPERATOR_INTENT:-}" = "AUTHORIZE_ONE_STORAGE_UNKNOWN_V2_PREFLIGHT_ONLY" ] || { echo "Exact v2 preflight operator intent is unavailable in the container." >&2; exit 5; }
if [ "${GOTIME_V2_TWO_GATE_OFFLINE_TEST:-}" = "1" ]; then
  exec python scripts/experiments/suggest_moving_service_questions/test_v2_two_gate_launcher_boundary.py preflight
fi
exec python scripts/experiments/suggest_moving_service_questions/run_openai_stage_b_v2_preflight_live.py
