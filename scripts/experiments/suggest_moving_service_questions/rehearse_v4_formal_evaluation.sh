#!/usr/bin/env bash
set -euo pipefail
exec "$(dirname "$0")/v4_formal_evaluation_offline.sh" rehearse "$@"
