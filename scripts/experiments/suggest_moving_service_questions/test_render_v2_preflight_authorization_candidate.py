"""Offline tests for the fixed v2 preflight-candidate rendering CLI."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tomllib
from argparse import Namespace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

SCRIPT_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = SCRIPT_ROOT.parents[2]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from render_v2_preflight_authorization_candidate import (  # noqa: E402
    EXIT_CANDIDATE_INTEGRITY_ERROR, EXIT_PATH_POLICY_ERROR, EXIT_VALIDATION_ERROR,
    OutputPathPolicyError, main, validate_output_path,
)
from v2_phase_authorization_candidates import (  # noqa: E402
    MANIFEST_PATH, PHASE_PATHS, UMBRELLA_DIGEST, V2PhaseCandidateError,
)

NOW = datetime(2030, 1, 1, 12, 5, tzinfo=timezone.utc)
VALID = [
    "--approver", "Human Reviewer", "--approved-at", "2030-01-01T12:00:00Z",
    "--activated-at", "2030-01-01T12:04:00Z", "--expires-at", "2030-01-01T12:15:00Z",
    "--reason", "One reviewed preflight rendering",
]


def arguments(output: Path, replacements: dict[str, str] | None = None) -> list[str]:
    values = ["--output", str(output), *VALID]
    for option, value in (replacements or {}).items():
        values[values.index(option) + 1] = value
    return values


def test_exact_supported_command_renders_machine_readable_result(tmp_path: Path) -> None:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    approved = now - timedelta(seconds=1)
    expires = now + timedelta(seconds=899)
    output = tmp_path / "gotime-v2-preflight-authorization.toml"
    command = [
        sys.executable, str(SCRIPT_ROOT / "render_v2_preflight_authorization_candidate.py"),
        "--output", str(output), "--approver", "Human Reviewer",
        "--approved-at", approved.isoformat().replace("+00:00", "Z"),
        "--activated-at", now.isoformat().replace("+00:00", "Z"),
        "--expires-at", expires.isoformat().replace("+00:00", "Z"),
        "--reason", "One reviewed preflight rendering",
    ]
    completed = subprocess.run(
        command, cwd=REPOSITORY_ROOT, text=True, capture_output=True, check=False,
        env={"PATH": os.environ["PATH"], "PYTHONPATH": str(SCRIPT_ROOT)},
    )
    assert completed.returncode == 0 and completed.stderr == ""
    lines = completed.stdout.splitlines()
    assert lines == [f"output_path={output}", f"sha256={hashlib.sha256(output.read_bytes()).hexdigest()}"]
    assert output.stat().st_mode & 0o777 == 0o600
    artifact = tomllib.loads(output.read_text())
    assert artifact["metadata"]["phase"] == "preflight"
    assert artifact["authorization"]["token_preflight_authorized"] is True
    assert artifact["authorization"]["ai_generation_authorized"] is False
    assert artifact["scope"]["maximum_ai_generation_requests"] == 0
    assert not any("REQUIRED" in str(value) for section in artifact.values() for value in section.values())


@pytest.mark.parametrize(
    "value",
    [
        "relative.toml",
        str(REPOSITORY_ROOT / "candidate.toml"),
        str(REPOSITORY_ROOT / ".local/evaluations/candidate.toml"),
        "/tmp-prefix-confusion/candidate.toml",
        "/tmp/../tmp/candidate.toml",
        "/tmp",
    ],
)
def test_output_path_policy_rejects_non_tmp_or_ambiguous_paths(value: str) -> None:
    with pytest.raises(OutputPathPolicyError):
        validate_output_path(value)


def test_existing_file_symlink_file_and_symlink_parent_are_rejected(tmp_path: Path) -> None:
    existing = tmp_path / "existing.toml"
    existing.write_text("existing\n")
    with pytest.raises(OutputPathPolicyError):
        validate_output_path(str(existing))
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "link"
    link.symlink_to(target, target_is_directory=True)
    with pytest.raises(OutputPathPolicyError, match="symlink"):
        validate_output_path(str(link / "candidate.toml"))
    file_link = tmp_path / "file-link.toml"
    file_link.symlink_to(existing)
    with pytest.raises(OutputPathPolicyError, match="symlink"):
        validate_output_path(str(file_link))


def test_missing_parent_is_rejected_without_partial_output(tmp_path: Path) -> None:
    output = tmp_path / "missing" / "candidate.toml"
    assert main(arguments(output), now=NOW) == EXIT_PATH_POLICY_ERROR
    assert not output.exists() and not output.parent.exists()


@pytest.mark.parametrize("missing", ["--output", "--approver", "--approved-at", "--activated-at", "--expires-at", "--reason"])
def test_required_argument_is_enforced(missing: str, tmp_path: Path) -> None:
    values = arguments(tmp_path / "candidate.toml")
    index = values.index(missing)
    del values[index:index + 2]
    with pytest.raises(SystemExit) as error:
        main(values, now=NOW)
    assert error.value.code == 2


def test_unknown_argument_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as error:
        main([*arguments(tmp_path / "candidate.toml"), "--phase", "generation"], now=NOW)
    assert error.value.code == 2


@pytest.mark.parametrize(
    ("replacements", "exit_code"),
    [
        ({"--approver": "   "}, EXIT_VALIDATION_ERROR),
        ({"--reason": "   "}, EXIT_VALIDATION_ERROR),
        ({"--approved-at": "not-a-time"}, EXIT_VALIDATION_ERROR),
        ({"--activated-at": "2030-01-01T12:04:00.1Z"}, EXIT_VALIDATION_ERROR),
        ({"--approved-at": "2030-01-01T12:05:00Z", "--activated-at": "2030-01-01T12:04:00Z"}, EXIT_VALIDATION_ERROR),
        ({"--activated-at": "2030-01-01T11:40:00Z", "--expires-at": "2030-01-01T11:55:00Z"}, EXIT_VALIDATION_ERROR),
        ({"--expires-at": "2030-01-01T12:19:01Z"}, EXIT_VALIDATION_ERROR),
    ],
)
def test_validation_failures_are_bounded_and_leave_no_file(
    tmp_path: Path, replacements: dict[str, str], exit_code: int,
) -> None:
    output = tmp_path / "candidate.toml"
    assert main(arguments(output, replacements), now=NOW) == exit_code
    assert not output.exists()


@pytest.mark.parametrize("kind", ["candidate", "manifest", "umbrella", "frozen"])
def test_integrity_failure_has_stable_exit_and_no_output(tmp_path: Path, kind: str) -> None:
    output = tmp_path / "candidate.toml"

    def failed_loader(phase: str) -> object:
        assert phase == "preflight"
        raise V2PhaseCandidateError(f"{kind} drift")

    assert main(arguments(output), now=NOW, loader=failed_loader) == EXIT_CANDIDATE_INTEGRITY_ERROR
    assert not output.exists()


def test_renderer_is_preflight_only_and_cli_has_no_generation_or_external_side_effect_hooks() -> None:
    source = (SCRIPT_ROOT / "render_v2_preflight_authorization_candidate.py").read_text()
    assert "render_generation_candidate" not in source
    assert "os.environ" not in source
    for prohibited in (
        "OpenAI(", "client_constructor", "token_preflight", "responses.create",
        "execution-manifest.json", "GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY",
    ):
        assert prohibited not in source


def test_reviewed_inputs_and_closed_repository_remain_unchanged() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text())
    assert hashlib.sha256(PHASE_PATHS["preflight"].read_bytes()).hexdigest() == manifest["preflight_candidate_digest"]
    assert hashlib.sha256(PHASE_PATHS["generation"].read_bytes()).hexdigest() == manifest["generation_candidate_digest"]
    umbrella = REPOSITORY_ROOT / manifest["umbrella_candidate_path"]
    assert hashlib.sha256(umbrella.read_bytes()).hexdigest() == UMBRELLA_DIGEST
    execution = REPOSITORY_ROOT / "docs/experiments/suggest-moving-service-questions/v2-pilot/execution-manifest.json"
    closed = execution.with_name("closed-execution-manifest.json")
    assert execution.read_bytes() == closed.read_bytes()
