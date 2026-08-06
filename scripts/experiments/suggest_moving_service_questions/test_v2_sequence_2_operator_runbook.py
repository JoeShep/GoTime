"""Inventory and exact-command synthetic rehearsal for the sequence-2 runbook."""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT_DIR = Path(__file__).resolve().parent
RUNBOOK = ROOT / "docs/experiments/suggest-moving-service-questions/v2-pilot/sequence-2-operator-runbook.md"
PUBLIC = {
    "render_v2_sequence_2_preflight_authorization_candidate_docker.sh",
    "install_v2_sequence_2_preflight_authorization_for_review_docker.sh",
    "review_v2_sequence_2_preflight_authorization_activation_docker.sh",
    "plan_v2_sequence_2_preflight_authorization_activation_docker.sh",
    "activate_v2_sequence_2_preflight_authorization_docker.sh",
    "run_openai_stage_b_v2_preflight_docker.sh",
    "close_v2_sequence_2_preflight_authorization_docker.sh",
    "cleanup_v2_sequence_2_expired_review_package_docker.sh",
}


def _fields(output: str) -> dict[str, str]:
    return dict(line.split("=", 1) for line in output.splitlines() if "=" in line)


def _run(root: Path, script: str, *arguments: str, environment=None, success=True):
    result = subprocess.run(
        ["sh", str(root / "scripts/experiments/suggest_moving_service_questions" / script), *arguments],
        cwd=root, env=environment, text=True, capture_output=True, timeout=120,
    )
    if success:
        assert result.returncode == 0, result.stderr
    else:
        assert result.returncode != 0
    return _fields(result.stdout)


def test_runbook_references_only_existing_executable_rehearsed_commands() -> None:
    paths = set(re.findall(r"scripts/experiments/suggest_moving_service_questions/([\w.-]+\.sh)", RUNBOOK.read_text()))
    docker_paths = {name for name in paths if name.endswith("_docker.sh")}
    assert docker_paths == PUBLIC
    for name in paths:
        path = SCRIPT_DIR / name
        assert path.is_file() and os.access(path, os.X_OK)
    for name in PUBLIC:
        path = SCRIPT_DIR / name
        text = path.read_text()
        if name != "run_openai_stage_b_v2_preflight_docker.sh":
            assert "--network none" in text
        assert "gotime-moving-service-stage-b:openai-2.45.0" in text
        assert "--sequence" not in text and "--provider" not in text and "--model" not in text
    for name in paths - PUBLIC:
        text = (SCRIPT_DIR / name).read_text()
        assert 'version("openai") == "2.45.0"' in text
        assert 'version("pydantic") == "2.13.4"' in text


def test_exact_public_commands_complete_network_disabled_synthetic_rehearsal() -> None:
    if shutil.which("docker") is None:
        import pytest
        pytest.skip("Docker is required for exact operator rehearsal")
    with tempfile.TemporaryDirectory(prefix="gotime-v2-sequence2-rehearsal-") as directory:
        root = Path(directory) / "repository"
        for name in ("scripts", "docs", "backend"):
            shutil.copytree(ROOT / name, root / name)
        run_state = root / ".local/evaluations/suggest-moving-service-questions/moving-service-stage-b-v2-pilot-20260802"
        review_state = run_state / "authorization-review"
        review_state.mkdir(parents=True, mode=0o700)
        now = datetime.now(timezone.utc).replace(microsecond=0)
        approved = now - timedelta(seconds=10)
        activated = now - timedelta(seconds=5)
        expires = activated + timedelta(seconds=900)
        rendered_path = Path("/tmp") / f"gotime-v2-sequence2-rehearsal-{os.getpid()}.toml"
        rendered_path.unlink(missing_ok=True)
        try:
            rendered = _run(root, "render_v2_sequence_2_preflight_authorization_candidate_docker.sh",
                "--output", str(rendered_path), "--approver", "Synthetic Approver",
                "--approved-at", approved.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "--activated-at", activated.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "--expires-at", expires.strftime("%Y-%m-%dT%H:%M:%SZ"), "--reason", "Synthetic rehearsal only")
            installed = _run(root, "install_v2_sequence_2_preflight_authorization_for_review_docker.sh",
                "--source", str(rendered_path), "--expected-sha256", rendered["sha256"])
            reviewed_at = datetime.now(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
            reviewed = _run(root, "review_v2_sequence_2_preflight_authorization_activation_docker.sh",
                "--artifact-sha256", installed["sha256"], "--reviewer", "Synthetic Reviewer",
                "--decision", "approve", "--reviewed-at", reviewed_at, "--notes", "Synthetic approval only")
            plan = _run(root, "plan_v2_sequence_2_preflight_authorization_activation_docker.sh",
                "--artifact-sha256", installed["sha256"],
                "--installation-record-sha256", installed["installation_record_sha256"],
                "--activation-review-sha256", reviewed["review_sha256"])
            assert plan["writes_performed"] == "false" and "002-storage_unknown" in plan["future_active_destination"]
            activated_result = _run(root, "activate_v2_sequence_2_preflight_authorization_docker.sh",
                "--artifact-sha256", installed["sha256"],
                "--installation-record-sha256", installed["installation_record_sha256"],
                "--activation-review-sha256", reviewed["review_sha256"],
                "--operator", "Synthetic Operator", "--operator-intent", "AUTHORIZE_ONE_STORAGE_UNKNOWN_V2_PREFLIGHT_ONLY")
            assert activated_result["transaction_state"] == "committed"
            environment = os.environ.copy()
            environment.update({
                "GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY": "synthetic-not-a-real-key",
                "GOTIME_MOVING_SERVICE_EVAL_ENABLED": "1",
                "GOTIME_MOVING_SERVICE_EVAL_OPERATOR_INTENT": "AUTHORIZE_ONE_STORAGE_UNKNOWN_V2_PREFLIGHT_ONLY",
                "GOTIME_V2_TWO_GATE_OFFLINE_TEST": "1",
            })
            preflight = _run(root, "run_openai_stage_b_v2_preflight_docker.sh", environment=environment)
            assert preflight["preflight_succeeded"] == "true" and preflight["generation_attempted"] == "false"
            closed = _run(root, "close_v2_sequence_2_preflight_authorization_docker.sh", "--reason", "success")
            assert closed["authorization_closed"] == "true"
            pilot = root / "docs/experiments/suggest-moving-service-questions/v2-pilot"
            assert (pilot / "execution-manifest.json").read_bytes() == (pilot / "closed-execution-manifest.json").read_bytes()
            assert not (run_state / "002-storage_unknown-preflight-authorization.toml").exists()
            _run(root, "run_openai_stage_b_v2_preflight_docker.sh", environment=environment, success=False)
            assert (run_state / "002-storage_unknown-preflight.json").is_file()
            assert (run_state / "002-storage_unknown-preflight-evidence.json").is_file()
            assert (run_state / "002-storage_unknown-preflight-closure.json").is_file()
        finally:
            rendered_path.unlink(missing_ok=True)


if __name__ == "__main__":
    test_runbook_references_only_existing_executable_rehearsed_commands()
    test_exact_public_commands_complete_network_disabled_synthetic_rehearsal()
    print("sequence_2_operator_rehearsal=passed")
