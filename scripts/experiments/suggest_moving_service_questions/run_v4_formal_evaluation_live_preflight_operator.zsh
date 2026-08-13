#!/usr/bin/env zsh
if [[ "${ZSH_EVAL_CONTEXT:-}" == *:file ]]; then
  return 2
fi
set -eu
[[ -n "${ZSH_VERSION:-}" ]] || exit 2
set +x
repository_root=${0:A:h:h:h:h}
[[ "$PWD:A" == "$repository_root" ]] || exit 2
child_pid=""
cleanup_m8_credential() {
  local child_exit_code=$?
  trap - EXIT INT TERM HUP
  unset GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY
  return $child_exit_code
}
handle_m8_signal() {
  local signal_name=$1
  local signal_exit_code=$2
  trap - INT TERM HUP
  if [[ -n "$child_pid" ]]; then
    kill -s "$signal_name" "$child_pid" >/dev/null 2>&1 || true
    wait "$child_pid" >/dev/null 2>&1 || true
  fi
  exit "$signal_exit_code"
}
trap cleanup_m8_credential EXIT
trap 'handle_m8_signal INT 130' INT
trap 'handle_m8_signal TERM 143' TERM
trap 'handle_m8_signal HUP 129' HUP
sh scripts/experiments/suggest_moving_service_questions/run_v4_formal_evaluation_live_preflight_boundary_docker.sh check
read -s "GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY?OpenAI evaluation key: "
echo
export GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY
[[ -n "$GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY" ]] || exit 3
sh scripts/experiments/suggest_moving_service_questions/run_v4_formal_evaluation_live_preflight_boundary_docker.sh execute &
child_pid=$!
set +e
wait "$child_pid"
child_exit_code=$?
set -e
child_pid=""
exit "$child_exit_code"
