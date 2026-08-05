#!/bin/sh
set -eu

python -c 'from importlib.metadata import version; import pydantic; assert version("openai") == "2.45.0"; assert version("pydantic") == "2.13.4"'

exec python scripts/experiments/suggest_moving_service_questions/render_v2_sequence_2_preflight_authorization_candidate.py "$@"
