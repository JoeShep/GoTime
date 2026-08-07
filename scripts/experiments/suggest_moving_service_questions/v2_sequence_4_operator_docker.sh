#!/bin/sh
set -eu
operation=$1
shift
root=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
[ "$(pwd -P)" = "$root" ] || { echo "Run from the GoTime repository root." >&2; exit 2; }
run_state="$root/.local/evaluations/suggest-moving-service-questions/moving-service-stage-b-v2-pilot-20260802"
mkdir -p "$run_state/authorization-review"
exec docker run --rm --network none --user "$(id -u):$(id -g)" --read-only \
  --tmpfs /tmp/container:rw,nosuid,nodev,noexec,size=16m \
  --volume "$root:/workspace:ro" --volume /tmp:/tmp:rw \
  --volume "$root/docs/experiments/suggest-moving-service-questions/v2-pilot:/workspace/docs/experiments/suggest-moving-service-questions/v2-pilot:rw" \
  --volume "$run_state:/workspace/.local/evaluations/suggest-moving-service-questions/moving-service-stage-b-v2-pilot-20260802:rw" \
  --workdir /workspace --env PYTHONDONTWRITEBYTECODE=1 \
  gotime-moving-service-stage-b:openai-2.45.0 sh \
  scripts/experiments/suggest_moving_service_questions/v2_sequence_4_operator_container.sh "$operation" "$@"
