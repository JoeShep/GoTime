#!/bin/sh
set -eu

cli=scripts/experiments/suggest_moving_service_questions/cleanup_v2_sequence_2_expired_review_package.py
[ -f "$cli" ] || exit 5
python -c 'from importlib.metadata import version; import pydantic; assert version("openai") == "2.45.0"; assert version("pydantic") == "2.13.4"'
exec python "$cli" "$@"
