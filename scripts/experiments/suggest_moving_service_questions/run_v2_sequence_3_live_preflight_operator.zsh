#!/usr/bin/env zsh
set -eu

[[ -n "${ZSH_VERSION:-}" ]] || { print -u2 -- "This operator command requires zsh."; exit 2; }
repository_root=${0:A:h:h:h:h}
[[ "$PWD:A" == "$repository_root" ]] || { print -u2 -- "Run from the GoTime repository root."; exit 2; }

launcher_started=false
closure_complete=false

cleanup_operator_environment() {
  unset GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY
  unset GOTIME_MOVING_SERVICE_EVAL_ENABLED
  unset GOTIME_MOVING_SERVICE_EVAL_OPERATOR_INTENT
}

recover_if_required() {
  local exit_code=$?
  trap - EXIT INT TERM HUP
  if [[ "$launcher_started" == true && "$closure_complete" != true ]]; then
    sh scripts/experiments/suggest_moving_service_questions/close_v2_sequence_3_preflight_authorization_docker.sh \
      --reason bounded_failure >/dev/null 2>&1 || true
  fi
  cleanup_operator_environment
  return $exit_code
}

trap recover_if_required EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
trap 'exit 129' HUP

sh scripts/experiments/suggest_moving_service_questions/verify_v2_sequence_3_preflight_authorization_docker.sh

if [[ "${GOTIME_V2_SEQUENCE_3_OFFLINE_TEST:-}" == "1" && -n "${GOTIME_V2_SEQUENCE_3_SYNTHETIC_INPUT_FD:-}" ]]; then
  read -r -u "$GOTIME_V2_SEQUENCE_3_SYNTHETIC_INPUT_FD" GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY
else
  read -s "GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY?OpenAI evaluation key: "
  echo
fi
export GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY
[[ -n "$GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY" ]] || { print -u2 -- "A nonempty evaluation credential is required."; exit 3; }
export GOTIME_MOVING_SERVICE_EVAL_ENABLED=1
export GOTIME_MOVING_SERVICE_EVAL_OPERATOR_INTENT=AUTHORIZE_ONE_STORAGE_UNKNOWN_V2_PREFLIGHT_ONLY

launcher_started=true
sh scripts/experiments/suggest_moving_service_questions/run_openai_stage_b_v2_sequence_3_preflight_docker.sh
sh scripts/experiments/suggest_moving_service_questions/close_v2_sequence_3_preflight_authorization_docker.sh --reason success
closure_complete=true
cleanup_operator_environment
