#!/bin/sh
set -eu
export PYTHONPATH=/workspace/backend:/workspace/scripts/experiments/suggest_moving_service_questions
exec python scripts/experiments/suggest_moving_service_questions/v4_sequence_1_preflight_cli.py "$@"
