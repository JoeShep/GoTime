#!/usr/bin/env zsh
if [[ "${ZSH_EVAL_CONTEXT:-}" == *:file ]]; then
  return 2
fi
set -eu
[[ -n "${ZSH_VERSION:-}" ]] || exit 2
set +x
repository_root=${0:A:h:h:h:h}
[[ "$PWD:A" == "$repository_root" ]] || exit 2
# This fixed launcher intentionally fails before prompting until production
# reviewed evidence and Milestone 18 live authorization both exist.
sh scripts/experiments/suggest_moving_service_questions/run_v4_formal_evaluation_live_generation_boundary_docker.sh
