#!/bin/sh
set -eu

repository_root=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
if [ "$(pwd -P)" != "$repository_root" ]; then
  echo "Run from the GoTime repository root." >&2
  exit 2
fi

exec docker run --rm --network none \
  --user "$(id -u):$(id -g)" \
  --read-only \
  --volume "$repository_root:/workspace:ro" \
  --volume /tmp:/tmp:rw \
  --workdir /workspace \
  --env PYTHONDONTWRITEBYTECODE=1 \
  gotime-moving-service-stage-b:openai-2.45.0 \
  sh scripts/experiments/suggest_moving_service_questions/render_v2_sequence_2_preflight_authorization_candidate_container.sh \
  "$@"
