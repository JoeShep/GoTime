#!/bin/sh
set -eu
[ -n "${GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY:-}" ] || { echo "The v2 preflight credential is unavailable in the container." >&2; exit 3; }
[ "${GOTIME_V2_TWO_GATE_OFFLINE_TEST:-}" = "1" ] || { echo "Preflight execution remains closed." >&2; exit 4; }
exec python scripts/experiments/suggest_moving_service_questions/test_v2_two_gate_launcher_boundary.py preflight
