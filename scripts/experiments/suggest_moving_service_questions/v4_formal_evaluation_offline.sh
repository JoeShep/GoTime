#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
evaluation_state_root="${V4_FORMAL_EVALUATION_STATE_DIR:-${repo_root}/.local/evaluations/suggest-moving-service-questions/v4-formal-evaluation-runner-v1}"
mkdir -p "${evaluation_state_root}"
exec docker run --rm --network none \
  --user "$(id -u):$(id -g)" \
  --read-only --tmpfs /tmp:rw,noexec,nosuid,size=32m \
  -v "${repo_root}:/workspace:ro" -w /workspace \
  -v "${evaluation_state_root}:/evaluation-state:rw" \
  -e PYTHONPATH=/workspace/backend:/workspace/scripts/experiments/suggest_moving_service_questions \
  gotime-moving-service-stage-b:openai-2.45.0 \
  python scripts/experiments/suggest_moving_service_questions/v4_formal_evaluation_cli.py \
  --state-dir /evaluation-state "$@"
