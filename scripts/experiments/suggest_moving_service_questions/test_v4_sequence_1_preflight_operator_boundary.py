"""Dependency-free zsh process-boundary tests for frozen-v4 preflight."""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from unittest import SkipTest

ROOT = Path(__file__).resolve().parents[3]
OPERATOR = ROOT / "scripts/experiments/suggest_moving_service_questions/run_v4_live_preflight_operator.zsh"
INTENT = "AUTHORIZE_ONE_STORAGE_UNKNOWN_V4_PREFLIGHT_ONLY"


def _run(*, launcher_status=0, signal_name=None, closure_status=0):
    if shutil.which("zsh") is None: raise SkipTest("zsh is required")
    with tempfile.TemporaryDirectory(prefix="gotime-v4-preflight-shell-") as directory:
        root = Path(directory); copied = root / "scripts/experiments/suggest_moving_service_questions" / OPERATOR.name
        copied.parent.mkdir(parents=True); copied.write_bytes(OPERATOR.read_bytes()); copied.chmod(0o755)
        bin_path = root / "bin"; bin_path.mkdir(); log = root / "calls.log"
        action = f"kill -{signal_name} $PPID; exit 99" if signal_name else ('test "$GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY" = synthetic-v4-secret || exit 88; test "$GOTIME_MOVING_SERVICE_EVAL_ENABLED" = 1 || exit 88; ' + f'test "$GOTIME_MOVING_SERVICE_EVAL_OPERATOR_INTENT" = {INTENT} || exit 88; exit {launcher_status}')
        stub = bin_path / "sh"; stub.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$v4_CALL_LOG"\ncase "$*" in\n*verify*) exit 0;;\n*run_openai*) ' + action + f';;\n*close*) exit {closure_status};;\nesac\nexit 0\n'); stub.chmod(0o755)
        read_fd, write_fd = os.pipe(); os.write(write_fd, b"synthetic-v4-secret\n"); os.close(write_fd)
        environment = os.environ.copy(); environment.update({"PATH": f"{bin_path}:{environment['PATH']}", "GOTIME_V4_SEQUENCE_1_PREFLIGHT_OFFLINE_TEST": "1", "GOTIME_V4_SEQUENCE_1_PREFLIGHT_SYNTHETIC_INPUT_FD": str(read_fd), "v4_CALL_LOG": str(log)})
        result = subprocess.run(["zsh", str(copied)], cwd=root, env=environment, pass_fds=(read_fd,), text=True, capture_output=True, timeout=20); os.close(read_fd)
        return result, log.read_text()


def test_success_failure_signals_and_closure_failure() -> None:
    result, calls = _run(); assert result.returncode == 0; assert "synthetic-v4-secret" not in result.stdout + result.stderr; assert "--reason success" in calls
    result, calls = _run(launcher_status=9); assert result.returncode == 9; assert "bounded_failure" in calls
    for signal, code in (("INT", 130), ("TERM", 143), ("HUP", 129)):
        result, calls = _run(signal_name=signal); assert result.returncode == code; assert "bounded_failure" in calls; assert "synthetic-v4-secret" not in result.stdout + result.stderr
    result, calls = _run(closure_status=17); assert result.returncode == 17; assert "--reason success" in calls and "bounded_failure" in calls
