#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
[ "$(pwd -P)" = "$root" ] || exit 2
state="$root/.local/evaluations/suggest-moving-service-questions"
mkdir -p "$state"
exec docker run --rm --network none --user "$(id -u):$(id -g)" --read-only \
  --tmpfs /tmp:rw,nosuid,nodev,noexec,size=16m \
  --volume "$root:/workspace:ro" \
  --volume "$state:/workspace/.local/evaluations/suggest-moving-service-questions:rw" \
  --workdir /workspace --env PYTHONDONTWRITEBYTECODE=1 \
  --env PYTHONPATH=/workspace/backend:/workspace/scripts/experiments/suggest_moving_service_questions \
  gotime-moving-service-stage-b:openai-2.45.0 python \
  scripts/experiments/suggest_moving_service_questions/review_v4_formal_evaluation_live_preflight_evidence.py "$@"
