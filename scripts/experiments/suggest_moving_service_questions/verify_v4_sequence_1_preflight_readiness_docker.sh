#!/bin/sh
set -eu
exec sh scripts/experiments/suggest_moving_service_questions/v4_sequence_1_preflight_docker.sh readiness "$@"
