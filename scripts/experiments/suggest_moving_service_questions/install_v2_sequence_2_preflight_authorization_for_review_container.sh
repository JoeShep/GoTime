#!/bin/sh
set -eu

cli=scripts/experiments/suggest_moving_service_questions/install_v2_sequence_2_preflight_authorization_for_review.py
[ -f "$cli" ] || exit 5
python -c 'from importlib.metadata import version; import pydantic; assert version("openai") == "2.45.0"; assert version("pydantic") == "2.13.4"'
exec python "$cli" "$@"
