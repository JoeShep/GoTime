#!/bin/sh
set -eu
operation=$1
shift
cli=scripts/experiments/suggest_moving_service_questions/v2_sequence_4_operator_cli.py
[ -f "$cli" ] || exit 6
python -c 'from importlib.metadata import version; import pydantic; assert version("openai") == "2.45.0"; assert version("pydantic") == "2.13.4"'
exec python "$cli" "$operation" "$@"
