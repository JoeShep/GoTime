#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
[ "$(pwd -P)" = "$root" ] || { echo "Run from the GoTime repository root." >&2; exit 2; }
state="$root/.local/evaluations/suggest-moving-service-questions"
mkdir -p "$state"
exec docker run --rm --network none --user "$(id -u):$(id -g)" --read-only \
  --tmpfs /tmp/container:rw,nosuid,nodev,noexec,size=16m \
  --volume "$root:/workspace:ro" --volume /tmp:/tmp:rw \
  --volume "$state:/workspace/.local/evaluations/suggest-moving-service-questions:rw" \
  --workdir /workspace --env PYTHONDONTWRITEBYTECODE=1 \
  gotime-moving-service-stage-b:openai-2.45.0 sh \
  scripts/experiments/suggest_moving_service_questions/v2_sequence_4_generation_operator_container.sh "$@"
