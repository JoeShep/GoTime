#!/bin/sh
set -eu
export PYTHONPATH=/workspace/backend:/workspace/scripts/experiments/suggest_moving_service_questions
if [ "${GOTIME_V3_SEQUENCE_1_PREFLIGHT_OFFLINE_TEST:-}" = "1" ]; then
  exec python scripts/experiments/suggest_moving_service_questions/run_openai_stage_b_v3_sequence_1_preflight_synthetic.py
fi
exec python scripts/experiments/suggest_moving_service_questions/run_openai_stage_b_v3_sequence_1_preflight_live.py
