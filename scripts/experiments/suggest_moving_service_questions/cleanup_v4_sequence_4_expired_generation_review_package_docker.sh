#!/bin/sh
set -eu
exec sh scripts/experiments/suggest_moving_service_questions/v4_sequence_4_generation_operator_docker.sh cleanup-expired-review "$@"
