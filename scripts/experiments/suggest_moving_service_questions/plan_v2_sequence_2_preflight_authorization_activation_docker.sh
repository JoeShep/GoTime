#!/bin/sh
set -eu

repository_root=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
run_state="$repository_root/.local/evaluations/suggest-moving-service-questions/moving-service-stage-b-v2-pilot-20260802"

[ "$(pwd -P)" = "$repository_root" ] || { echo "Run from the GoTime repository root." >&2; exit 2; }
[ -d "$run_state" ] || { echo "Sequence-2 review state directory is missing." >&2; exit 7; }

exec docker run --rm --network none \
  --user "$(id -u):$(id -g)" \
  --read-only \
  --volume "$repository_root:/workspace:ro" \
  --volume "$run_state:/workspace/.local/evaluations/suggest-moving-service-questions/moving-service-stage-b-v2-pilot-20260802:ro" \
  --workdir /workspace \
  --env PYTHONDONTWRITEBYTECODE=1 \
  gotime-moving-service-stage-b:openai-2.45.0 \
  sh scripts/experiments/suggest_moving_service_questions/plan_v2_sequence_2_preflight_authorization_activation_container.sh \
  "$@"
