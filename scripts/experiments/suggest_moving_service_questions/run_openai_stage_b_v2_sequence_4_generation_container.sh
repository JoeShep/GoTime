#!/bin/sh
set -eu
[ -n "${GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY:-}" ] || exit 3
[ "${GOTIME_MOVING_SERVICE_EVAL_ENABLED:-}" = "1" ] || exit 4
[ "${GOTIME_MOVING_SERVICE_EVAL_OPERATOR_INTENT:-}" = "AUTHORIZE_ONE_STORAGE_UNKNOWN_V2_GENERATION_ONLY" ] || exit 5
python -c 'from importlib.metadata import version; import pydantic; assert version("openai") == "2.45.0"; assert version("pydantic") == "2.13.4"'
exec python scripts/experiments/suggest_moving_service_questions/run_openai_stage_b_v2_sequence_4_generation_live.py
