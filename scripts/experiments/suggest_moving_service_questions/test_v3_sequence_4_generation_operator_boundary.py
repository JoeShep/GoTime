"""Static boundaries for the fixed frozen-v3 generation workflow."""

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from unittest import SkipTest

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "scripts/experiments/suggest_moving_service_questions"
PUBLIC = (
    "render_v3_sequence_4_generation_authorization_candidate_docker.sh",
    "install_v3_sequence_4_generation_authorization_for_review_docker.sh",
    "review_v3_sequence_4_generation_authorization_activation_docker.sh",
    "plan_v3_sequence_4_generation_authorization_activation_docker.sh",
    "activate_v3_sequence_4_generation_authorization_docker.sh",
    "verify_v3_sequence_4_generation_authorization_docker.sh",
    "run_openai_stage_b_v3_sequence_4_generation_docker.sh",
    "run_v3_sequence_4_live_generation_operator.zsh",
    "review_v3_sequence_4_generation_response_docker.sh",
    "delete_v3_sequence_4_generation_response_evidence_docker.sh",
    "close_v3_sequence_4_generation_authorization_docker.sh",
)


def test_public_commands_exist_are_executable_and_fixed() -> None:
    for name in PUBLIC:
        path = SCRIPTS / name
        assert path.is_file() and path.stat().st_mode & 0o111
        text = path.read_text()
        assert "--sequence" not in text
        assert "--version" not in text
        assert "--api-key" not in text


def test_same_shell_credential_boundary_and_traps() -> None:
    text = (SCRIPTS / "run_v3_sequence_4_live_generation_operator.zsh").read_text()
    assert 'read -s "GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY?OpenAI evaluation key: "' in text
    assert "AUTHORIZE_ONE_STORAGE_UNKNOWN_V3_GENERATION_ONLY" in text
    assert "trap cleanup_generation_environment EXIT" in text
    assert "trap 'exit 130' INT" in text
    assert "trap 'exit 143' TERM" in text
    assert "trap 'exit 129' HUP" in text
    assert "local exit_code=$?" in text
    assert "local status=" not in text
    assert text.count("unset GOTIME_MOVING_SERVICE_EVAL_") == 3


def test_live_generation_has_no_preflight_and_credential_is_not_an_argument() -> None:
    runner = (SCRIPTS / "run_openai_stage_b_v3_sequence_4_generation_live.py").read_text()
    launcher = (SCRIPTS / "run_openai_stage_b_v3_sequence_4_generation_docker.sh").read_text()
    assert ".preflight(" not in runner
    assert "--env GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY" in launcher
    assert "${GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY}" not in launcher
    assert 'network_args="--network none"' in launcher


def test_rehearsal_covers_all_public_commands_and_five_scenarios() -> None:
    rehearsal = (SCRIPTS / "rehearse_v3_sequence_4_generation_workflow.sh").read_text()
    for name in PUBLIC:
        assert f"scripts/experiments/suggest_moving_service_questions/{name}" in rehearsal
    for scenario in (
        "compliant", "prose_rejection", "structural_failure",
        "semantic_failure", "prompt_policy_stress",
    ):
        assert f"run_scenario {scenario}" in rehearsal
    assert 'cmp -s "$expected" "$rehearsal_root/actual.txt"' in rehearsal
    assert "GOTIME_V3_SEQUENCE_4_GENERATION_SYNTHETIC_INPUT_FD" in rehearsal


def test_every_runbook_script_exists_and_is_executable() -> None:
    runbook = (ROOT / "docs/experiments/suggest-moving-service-questions/v3-generation-operator-runbook.md").read_text()
    referenced = set(re.findall(
        r"scripts/experiments/suggest_moving_service_questions/[A-Za-z0-9_.-]+",
        runbook,
    ))
    assert referenced
    for relative in referenced:
        path = ROOT / relative
        assert path.is_file(), relative
        assert path.stat().st_mode & 0o111, relative


def _stubbed_operator(*, launcher_status: int = 0, signal_name: str | None = None,
                      closure_status: int = 0):
    if shutil.which("zsh") is None:
        raise SkipTest("zsh is required for same-shell process tests")
    operator = SCRIPTS / "run_v3_sequence_4_live_generation_operator.zsh"
    with tempfile.TemporaryDirectory(prefix="gotime-v3-sequence4-shell-") as directory:
        root = Path(directory)
        script = root / "scripts/experiments/suggest_moving_service_questions" / operator.name
        script.parent.mkdir(parents=True)
        script.write_bytes(operator.read_bytes())
        script.chmod(0o755)
        bin_path = root / "bin"
        bin_path.mkdir()
        call_log = root / "calls.log"
        action = (
            f"kill -{signal_name} $PPID; exit 99"
            if signal_name else
            'test "$GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY" = "synthetic-secret-never-print" || exit 88; '
            'test "$GOTIME_MOVING_SERVICE_EVAL_ENABLED" = 1 || exit 88; '
            'test "$GOTIME_MOVING_SERVICE_EVAL_OPERATOR_INTENT" = AUTHORIZE_ONE_STORAGE_UNKNOWN_V3_GENERATION_ONLY || exit 88; '
            f"exit {launcher_status}"
        )
        stub = bin_path / "sh"
        stub.write_text(
            '#!/bin/sh\nprintf "%s\\n" "$*" >> "$GOTIME_V3_CALL_LOG"\n'
            'case "$*" in\n*verify*) exit 0;;\n*run_openai*) ' + action + ";;\n"
            f"*close*) exit {closure_status};;\nesac\nexit 0\n"
        )
        stub.chmod(0o755)
        read_fd, write_fd = os.pipe()
        os.write(write_fd, b"synthetic-secret-never-print\n")
        os.close(write_fd)
        environment = os.environ.copy()
        environment.update({
            "PATH": f"{bin_path}:{environment['PATH']}",
            "GOTIME_V3_SEQUENCE_4_GENERATION_OFFLINE_TEST": "1",
            "GOTIME_V3_SEQUENCE_4_GENERATION_SYNTHETIC_INPUT_FD": str(read_fd),
            "GOTIME_V3_CALL_LOG": str(call_log),
        })
        result = subprocess.run(
            ["zsh", str(script)], cwd=root, env=environment, pass_fds=(read_fd,),
            text=True, capture_output=True, timeout=20,
        )
        os.close(read_fd)
        return result, call_log.read_text()


def test_same_shell_success_and_failure_preserve_boundary_and_exit_codes() -> None:
    success, success_calls = _stubbed_operator()
    assert success.returncode == 0
    assert "synthetic-secret-never-print" not in success.stdout + success.stderr
    assert success_calls.count("run_openai_stage_b_v3_sequence_4_generation_docker.sh") == 1
    assert "close_v3_sequence_4_generation_authorization_docker.sh --reason success" in success_calls

    failure, failure_calls = _stubbed_operator(launcher_status=9)
    assert failure.returncode == 9
    assert "bounded_failure" in failure_calls
    assert "synthetic-secret-never-print" not in failure.stdout + failure.stderr


def test_same_shell_signals_and_closure_failure_remain_detectable() -> None:
    for signal_name, expected in (("INT", 130), ("TERM", 143), ("HUP", 129)):
        result, calls = _stubbed_operator(signal_name=signal_name)
        assert result.returncode == expected
        assert "bounded_failure" in calls
        assert "read-only variable" not in result.stderr
        assert "synthetic-secret-never-print" not in result.stdout + result.stderr
    closure_failure, calls = _stubbed_operator(closure_status=17)
    assert closure_failure.returncode == 17
    assert "--reason success" in calls and "--reason bounded_failure" in calls
