"""Sequence-3 candidate, inventory, and same-shell credential-boundary tests."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "scripts/experiments/suggest_moving_service_questions"
RUNBOOK = ROOT / "docs/experiments/suggest-moving-service-questions/v2-pilot/sequence-3-operator-runbook.md"
OPERATOR = SCRIPTS / "run_v2_sequence_3_live_preflight_operator.zsh"


def test_candidate_and_fixed_paths() -> None:
    candidate = (ROOT / "docs/experiments/suggest-moving-service-questions/v2-pilot/authorization-review/phase-candidates/sequence-3/inactive-sequence-3-preflight-authorization-candidate.toml").read_text()
    manifest = (ROOT / "docs/experiments/suggest-moving-service-questions/v2-pilot/authorization-review/phase-candidates/sequence-3/sequence-3-candidate-manifest.json").read_text()
    assert "sequence = 3" in candidate and '"sequence": 3' in manifest
    assert "003-storage_unknown" in manifest
    assert "maximum_ai_generation_requests = 0" in candidate
    assert "ai_generation_authorized = false" in candidate
    assert "--sequence" not in RUNBOOK.read_text()


def test_runbook_paths_exist_are_executable_and_fixed() -> None:
    paths = set(re.findall(r"scripts/experiments/suggest_moving_service_questions/([\w.-]+\.(?:sh|zsh))", RUNBOOK.read_text()))
    assert "run_v2_sequence_3_live_preflight_operator.zsh" in paths
    for name in paths:
        path = SCRIPTS / name
        assert path.is_file() and os.access(path, os.X_OK)
        assert "sequence_2" not in name


def _stubbed_operator(*, launcher_status: int = 0, interrupt: bool = False):
    if shutil.which("zsh") is None:
        import pytest
        pytest.skip("zsh is required for same-shell process tests")
    with tempfile.TemporaryDirectory(prefix="gotime-sequence3-shell-") as directory:
        root = Path(directory)
        script_path = root / "scripts/experiments/suggest_moving_service_questions/run_v2_sequence_3_live_preflight_operator.zsh"
        script_path.parent.mkdir(parents=True)
        script_path.write_bytes(OPERATOR.read_bytes()); script_path.chmod(0o755)
        (root / "docs").mkdir()
        bin_path = root / "bin"; bin_path.mkdir()
        stub = bin_path / "sh"
        action = "kill -TERM $PPID; exit 143" if interrupt else f"exit {launcher_status}"
        stub.write_text("#!/bin/sh\ncase \"$*\" in\n*verify*) exit 0;;\n*run_openai*) " + action + ";;\n*close*) printf 'closed=true\\n'; exit 0;;\nesac\nexit 0\n")
        stub.chmod(0o755)
        read_fd, write_fd = os.pipe()
        os.write(write_fd, b"synthetic-secret-never-print\n"); os.close(write_fd)
        environment = os.environ.copy()
        environment.update({"PATH": f"{bin_path}:{environment['PATH']}", "GOTIME_V2_SEQUENCE_3_OFFLINE_TEST": "1",
                            "GOTIME_V2_SEQUENCE_3_SYNTHETIC_INPUT_FD": str(read_fd)})
        result = subprocess.run(["zsh", str(script_path)], cwd=root, env=environment,
            pass_fds=(read_fd,), text=True, capture_output=True, timeout=20)
        os.close(read_fd)
        return result


def test_same_shell_success_does_not_disclose_credential() -> None:
    result = _stubbed_operator()
    assert result.returncode == 0
    assert "synthetic-secret-never-print" not in result.stdout + result.stderr


def test_failure_and_interruption_close_without_disclosure() -> None:
    for result in (_stubbed_operator(launcher_status=9), _stubbed_operator(interrupt=True)):
        assert result.returncode != 0
        assert "synthetic-secret-never-print" not in result.stdout + result.stderr


def test_public_script_uses_exact_prompt_and_unsets_every_variable() -> None:
    text = OPERATOR.read_text()
    assert 'read -s "GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY?OpenAI evaluation key: "' in text
    for name in ("GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY", "GOTIME_MOVING_SERVICE_EVAL_ENABLED", "GOTIME_MOVING_SERVICE_EVAL_OPERATOR_INTENT"):
        assert f"unset {name}" in text
    assert "read -p" not in text and "--api-key" not in text


def _fields(output: str) -> dict[str, str]:
    return dict(line.split("=", 1) for line in output.splitlines() if "=" in line)


def _public(root: Path, name: str, *arguments: str):
    result = subprocess.run(["sh", str(root / "scripts/experiments/suggest_moving_service_questions" / name), *arguments],
        cwd=root, text=True, capture_output=True, timeout=120)
    assert result.returncode == 0, result.stderr
    return _fields(result.stdout)


def test_exact_public_sequence_3_synthetic_rehearsal() -> None:
    if shutil.which("docker") is None or shutil.which("zsh") is None:
        return
    with tempfile.TemporaryDirectory(prefix="gotime-v2-sequence3-rehearsal-") as directory:
        root = Path(directory) / "repository"
        for name in ("scripts", "docs", "backend"):
            shutil.copytree(ROOT / name, root / name)
        now = datetime.now(timezone.utc).replace(microsecond=0)
        approved = now - timedelta(seconds=10); activated = now - timedelta(seconds=5)
        expires = activated + timedelta(seconds=900)
        rendered_path = Path("/tmp") / f"gotime-sequence3-rehearsal-{os.getpid()}.toml"
        rendered_path.unlink(missing_ok=True)
        try:
            rendered = _public(root, "render_v2_sequence_3_preflight_authorization_candidate_docker.sh",
                "--output", str(rendered_path), "--approver", "Synthetic Approver",
                "--approved-at", approved.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "--activated-at", activated.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "--expires-at", expires.strftime("%Y-%m-%dT%H:%M:%SZ"), "--reason", "Synthetic rehearsal")
            installed = _public(root, "install_v2_sequence_3_preflight_authorization_for_review_docker.sh",
                "--source", str(rendered_path), "--expected-sha256", rendered["sha256"])
            reviewed = _public(root, "review_v2_sequence_3_preflight_authorization_activation_docker.sh",
                "--artifact-sha256", installed["sha256"], "--reviewer", "Synthetic Reviewer", "--decision", "approve",
                "--reviewed-at", datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "--notes", "Synthetic approval")
            plan = _public(root, "plan_v2_sequence_3_preflight_authorization_activation_docker.sh",
                "--artifact-sha256", installed["sha256"], "--installation-record-sha256", installed["installation_record_sha256"],
                "--activation-review-sha256", reviewed["review_sha256"])
            assert "003-storage_unknown" in plan["future_active_destination"] and plan["writes_performed"] == "false"
            activated_result = _public(root, "activate_v2_sequence_3_preflight_authorization_docker.sh",
                "--artifact-sha256", installed["sha256"], "--installation-record-sha256", installed["installation_record_sha256"],
                "--activation-review-sha256", reviewed["review_sha256"], "--operator", "Synthetic Operator",
                "--operator-intent", "AUTHORIZE_ONE_STORAGE_UNKNOWN_V2_PREFLIGHT_ONLY")
            assert activated_result["transaction_state"] == "committed"
            read_fd, write_fd = os.pipe(); os.write(write_fd, b"synthetic-not-a-real-key\n"); os.close(write_fd)
            environment = os.environ.copy()
            environment.update({"GOTIME_V2_SEQUENCE_3_OFFLINE_TEST": "1", "GOTIME_V2_SEQUENCE_3_SYNTHETIC_INPUT_FD": str(read_fd)})
            result = subprocess.run(["zsh", "scripts/experiments/suggest_moving_service_questions/run_v2_sequence_3_live_preflight_operator.zsh"],
                cwd=root, env=environment, pass_fds=(read_fd,), text=True, capture_output=True, timeout=120)
            os.close(read_fd)
            assert result.returncode == 0, result.stderr
            assert "synthetic-not-a-real-key" not in result.stdout + result.stderr
            run_state = root / ".local/evaluations/suggest-moving-service-questions/moving-service-stage-b-v2-pilot-20260802"
            pilot = root / "docs/experiments/suggest-moving-service-questions/v2-pilot"
            assert (run_state / "003-storage_unknown-preflight.json").is_file()
            assert (run_state / "003-storage_unknown-preflight-evidence.json").is_file()
            assert (run_state / "003-storage_unknown-preflight-closure.json").is_file()
            assert not (run_state / "003-storage_unknown-preflight-authorization.toml").exists()
            assert (pilot / "execution-manifest.json").read_bytes() == (pilot / "closed-execution-manifest.json").read_bytes()
            second = subprocess.run(["zsh", "scripts/experiments/suggest_moving_service_questions/run_v2_sequence_3_live_preflight_operator.zsh"],
                cwd=root, env=environment, text=True, capture_output=True, timeout=120)
            assert second.returncode != 0
        finally:
            rendered_path.unlink(missing_ok=True)


if __name__ == "__main__":
    test_candidate_and_fixed_paths(); test_runbook_paths_exist_are_executable_and_fixed()
    test_same_shell_success_does_not_disclose_credential(); test_failure_and_interruption_close_without_disclosure()
    test_public_script_uses_exact_prompt_and_unsets_every_variable()
    test_exact_public_sequence_3_synthetic_rehearsal()
    print("sequence_3_single_shell_tests=passed")
