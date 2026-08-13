#!/bin/sh
set -eu
[ "$#" -eq 1 ] && { [ "$1" = check ] || [ "$1" = execute ]; } || exit 2
root=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
[ "$(pwd -P)" = "$root" ] || exit 2
state="$root/.local/evaluations/suggest-moving-service-questions"
mkdir -p "$state"
credential_env=""
[ "$1" = execute ] && credential_env="--env GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY"
exec docker run --rm --network none --user "$(id -u):$(id -g)" --read-only \
  --tmpfs /tmp:rw,nosuid,nodev,noexec,size=16m \
  --volume "$root:/workspace:ro" \
  --volume "$state:/workspace/.local/evaluations/suggest-moving-service-questions:rw" \
  --workdir /workspace --env PYTHONDONTWRITEBYTECODE=1 \
  --env PYTHONPATH=/workspace/backend:/workspace/scripts/experiments/suggest_moving_service_questions \
  $credential_env \
  gotime-moving-service-stage-b:openai-2.45.0 python \
  scripts/experiments/suggest_moving_service_questions/v4_formal_evaluation_live_preflight_entry.py "$1"
