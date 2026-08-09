#!/bin/sh
set -eu
python -c 'from importlib.metadata import version; import pydantic; assert version("openai") == "2.45.0"; assert version("pydantic") == "2.13.4"'
exec python scripts/experiments/suggest_moving_service_questions/v4_sequence_4_generation_operator_cli.py "$@"
