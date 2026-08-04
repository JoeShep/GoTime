"""Offline tests for v2 preflight installation, review, and activation planning."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import sys
import tomllib
from datetime import datetime, timezone
from pathlib import Path

import pytest

SCRIPT_ROOT = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_ROOT.parents[2] / "backend"
for value in (SCRIPT_ROOT, BACKEND_ROOT):
    if str(value) not in sys.path:
        sys.path.insert(0, str(value))

from install_v2_preflight_authorization_for_review import main as install_main  # noqa: E402
from plan_v2_preflight_authorization_activation import main as plan_main  # noqa: E402
from render_v2_preflight_authorization_candidate import validate_output_path  # noqa: E402
from review_v2_preflight_authorization_activation import main as review_main  # noqa: E402
from v2_phase_authorization_candidates import (  # noqa: E402
    MANIFEST_PATH, PHASE_PATHS, UMBRELLA_DIGEST, render_preflight_candidate,
)
from v2_preflight_authorization_installation import (  # noqa: E402
    ActivationPrerequisiteError, ClosedStateError, ConflictingStateError,
    InstallationPathError, PackageIntegrityError, ReviewValidationError,
    SourceIntegrityError, ValidityWindowError, install_preflight_for_review,
    plan_preflight_activation, review_paths, review_preflight_activation,
    validate_source_path,
)

NOW = datetime(2030, 1, 1, 12, 5, tzinfo=timezone.utc)
APPROVED = "2030-01-01T12:00:00Z"
ACTIVATED = "2030-01-01T12:04:00Z"
EXPIRES = "2030-01-01T12:15:00Z"


def rendered_source(tmp_path: Path, **changes) -> tuple[Path, str]:
    source = tmp_path / "rendered.toml"
    rendered = render_preflight_candidate(
        output_path=source, approver="Human Approver", approved_at=APPROVED,
        activated_at=ACTIVATED, expires_at=EXPIRES,
        authorization_reason="One reviewed preflight", now=NOW,
    )
    if changes:
        artifact = tomllib.loads(source.read_text())
        for section, values in changes.items():
            artifact[section].update(values)
        # Test-only stable TOML uses the reviewed serializer indirectly unavailable;
        # alter exact scalar text for the requested single-field mutations.
        text = source.read_text()
        for section, values in changes.items():
            for field, value in values.items():
                old = tomllib.loads(text)[section][field]
                rendered_value = (
                    "true" if value is True else "false" if value is False
                    else str(value) if isinstance(value, int) else json.dumps(value)
                )
                old_value = (
                    "true" if old is True else "false" if old is False
                    else str(old) if isinstance(old, int) else json.dumps(old)
                )
                text = text.replace(f"{field} = {old_value}", f"{field} = {rendered_value}", 1)
        source.write_text(text)
        source.chmod(0o600)
        return source, hashlib.sha256(source.read_bytes()).hexdigest()
    return source, rendered.digest


def install(tmp_path: Path, **changes):
    source, digest = rendered_source(tmp_path, **changes)
    output_root = tmp_path / "local"
    result = install_preflight_for_review(
        source=source, expected_sha256=digest, output_root=output_root, now=NOW,
    )
    return source, digest, output_root, result


def approve(tmp_path: Path, decision: str = "approve"):
    source, digest, output_root, installation = install(tmp_path)
    review = review_preflight_activation(
        artifact_sha256=digest, reviewer="Activation Reviewer", decision=decision,
        reviewed_at="2030-01-01T12:06:00Z", notes="Bounded activation review.",
        output_root=output_root, now=datetime(2030, 1, 1, 12, 6, tzinfo=timezone.utc),
    )
    return source, digest, output_root, installation, review


def test_synthetic_install_preserves_bytes_and_writes_bounded_non_authoritative_record(tmp_path: Path) -> None:
    source, digest, output_root, result = install(tmp_path)
    paths = review_paths(output_root)
    assert paths["installed"].read_bytes() == source.read_bytes()
    assert hashlib.sha256(paths["installed"].read_bytes()).hexdigest() == digest == result["sha256"]
    assert paths["installed"].stat().st_mode & 0o777 == 0o600
    assert paths["directory"].stat().st_mode & 0o777 == 0o700
    record_text = paths["installation"].read_text()
    record = json.loads(record_text)
    assert record["authoritative"] is False
    assert record["activation_status"] == "not_activated"
    assert record["activation_review_status"] == "pending"
    for prohibited in ("credential", "system_instructions", "deterministic_request", "trusted_state", "authorization_header"):
        assert prohibited not in record_text.lower()
    assert not paths["future_active"].exists()


def test_install_cli_has_exact_machine_readable_output(tmp_path: Path, capsys) -> None:
    source, digest = rendered_source(tmp_path)
    output_root = tmp_path / "local"
    code = install_main(
        ["--source", str(source), "--expected-sha256", digest], now=NOW,
        output_root=output_root,
    )
    assert code == 0
    lines = capsys.readouterr().out.splitlines()
    assert [line.split("=", 1)[0] for line in lines] == [
        "installed_path", "sha256", "installation_record",
        "installation_record_sha256", "authoritative",
    ]
    assert lines[-1] == "authoritative=false"


@pytest.mark.parametrize("source", [Path("relative.toml"), Path("/etc/hosts")])
def test_source_outside_real_tmp_is_rejected(source: Path) -> None:
    with pytest.raises(InstallationPathError):
        validate_source_path(source)


def test_source_symlink_and_symlink_parent_are_rejected(tmp_path: Path) -> None:
    target = tmp_path / "target.toml"
    target.write_text("x")
    target.chmod(0o600)
    link = tmp_path / "link.toml"
    link.symlink_to(target)
    with pytest.raises(InstallationPathError):
        validate_source_path(link)
    directory = tmp_path / "directory"
    directory.mkdir()
    parent_link = tmp_path / "parent-link"
    parent_link.symlink_to(directory, target_is_directory=True)
    nested = directory / "nested.toml"
    nested.write_text("x")
    nested.chmod(0o600)
    with pytest.raises(InstallationPathError):
        validate_source_path(parent_link / "nested.toml")


def test_wrong_digest_and_broad_source_mode_are_rejected(tmp_path: Path) -> None:
    source, digest = rendered_source(tmp_path)
    with pytest.raises(SourceIntegrityError):
        install_preflight_for_review(
            source=source, expected_sha256="0" * 64, output_root=tmp_path / "local", now=NOW,
        )
    source.chmod(0o640)
    with pytest.raises(InstallationPathError):
        install_preflight_for_review(
            source=source, expected_sha256=digest, output_root=tmp_path / "local", now=NOW,
        )


@pytest.mark.parametrize(
    "changes",
    [
        {"metadata": {"phase": "generation"}},
        {"scope": {"run_series_id": "wrong"}},
        {"scope": {"maximum_token_preflight_requests": 2}},
        {"scope": {"maximum_ai_generation_requests": 1}},
        {"authorization": {"ai_generation_authorized": True}},
    ],
)
def test_wrong_phase_identity_or_broadened_scope_is_rejected(tmp_path: Path, changes) -> None:
    source, digest = rendered_source(tmp_path, **changes)
    with pytest.raises(SourceIntegrityError):
        install_preflight_for_review(
            source=source, expected_sha256=digest, output_root=tmp_path / "local", now=NOW,
        )


@pytest.mark.parametrize(
    "approval",
    [
        {"activated_at": "2030-01-01T12:06:00Z"},
        {"expires_at": "2030-01-01T12:19:01Z"},
        {"expires_at": "2030-01-01T12:04:59Z"},
    ],
)
def test_not_active_excessive_or_expired_source_is_rejected(tmp_path: Path, approval) -> None:
    source, digest = rendered_source(tmp_path, approval=approval)
    with pytest.raises(ValidityWindowError):
        install_preflight_for_review(
            source=source, expected_sha256=digest, output_root=tmp_path / "local", now=NOW,
        )


def test_unknown_field_is_rejected(tmp_path: Path) -> None:
    source, _ = rendered_source(tmp_path)
    text = source.read_text().replace("[scope]\n", "[scope]\nunknown = true\n")
    source.write_text(text)
    source.chmod(0o600)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    with pytest.raises(SourceIntegrityError):
        install_preflight_for_review(
            source=source, expected_sha256=digest, output_root=tmp_path / "local", now=NOW,
        )


def test_existing_installation_or_attempt_state_fails_closed(tmp_path: Path) -> None:
    source, digest, output_root, _ = install(tmp_path)
    with pytest.raises(ConflictingStateError):
        install_preflight_for_review(
            source=source, expected_sha256=digest,
            output_root=output_root, now=NOW,
        )


def test_existing_preflight_attempt_or_active_path_rejects_installation(tmp_path: Path) -> None:
    source, digest = rendered_source(tmp_path)
    for name in ("001-storage_unknown-preflight.json", "001-storage_unknown-preflight-authorization.toml"):
        output_root = tmp_path / name.replace(".", "-")
        base = output_root / "moving-service-stage-b-v2-pilot-20260802"
        base.mkdir(parents=True)
        (base / name).write_text("conflict\n")
        with pytest.raises(ConflictingStateError):
            install_preflight_for_review(
                source=source, expected_sha256=digest, output_root=output_root, now=NOW,
            )


@pytest.mark.parametrize("decision", ["approve", "reject", "request_changes"])
def test_activation_review_is_append_only_and_never_activates(tmp_path: Path, decision: str) -> None:
    _, digest, output_root, _, result = approve(tmp_path, decision)
    paths = review_paths(output_root)
    record = json.loads(paths["activation_review"].read_text())
    assert result["decision"] == decision
    assert record["activation_eligible"] is (decision == "approve")
    assert record["authoritative"] is False and record["activated"] is False
    assert not paths["future_active"].exists()
    with pytest.raises(ConflictingStateError):
        review_preflight_activation(
            artifact_sha256=digest, reviewer="Second", decision="approve",
            reviewed_at="2030-01-01T12:07:00Z", notes="No repeat.",
            output_root=output_root, now=datetime(2030, 1, 1, 12, 7, tzinfo=timezone.utc),
        )


def test_review_rejects_wrong_digest_drift_and_expiration(tmp_path: Path) -> None:
    _, digest, output_root, _ = install(tmp_path)
    with pytest.raises(ReviewValidationError):
        review_preflight_activation(
            artifact_sha256="0" * 64, reviewer="Reviewer", decision="approve",
            reviewed_at="2030-01-01T12:06:00Z", notes="Bounded.", output_root=output_root,
            now=datetime(2030, 1, 1, 12, 6, tzinfo=timezone.utc),
        )


def test_review_after_expiration_is_rejected(tmp_path: Path) -> None:
    _, digest, output_root, _ = install(tmp_path)
    with pytest.raises(ValidityWindowError):
        review_preflight_activation(
            artifact_sha256=digest, reviewer="Reviewer", decision="approve",
            reviewed_at="2030-01-01T12:14:59Z", notes="Bounded.", output_root=output_root,
            now=datetime(2030, 1, 1, 12, 15, 1, tzinfo=timezone.utc),
        )
    paths = review_paths(output_root)
    paths["installed"].write_bytes(paths["installed"].read_bytes() + b"\n")
    with pytest.raises(ReviewValidationError):
        review_preflight_activation(
            artifact_sha256=digest, reviewer="Reviewer", decision="approve",
            reviewed_at="2030-01-01T12:06:00Z", notes="Bounded.", output_root=output_root,
            now=datetime(2030, 1, 1, 12, 6, tzinfo=timezone.utc),
        )


def test_review_cli_output_is_bounded(tmp_path: Path, capsys) -> None:
    _, digest, output_root, _ = install(tmp_path)
    code = review_main([
        "--artifact-sha256", digest, "--reviewer", "Reviewer", "--decision", "approve",
        "--reviewed-at", "2030-01-01T12:06:00Z", "--notes", "Bounded.",
    ], now=datetime(2030, 1, 1, 12, 6, tzinfo=timezone.utc), output_root=output_root)
    assert code == 0
    assert [line.split("=", 1)[0] for line in capsys.readouterr().out.splitlines()] == [
        "review_path", "review_sha256", "decision", "authoritative", "activated",
    ]


def test_approved_review_allows_dry_run_plan_without_writes(tmp_path: Path) -> None:
    _, digest, output_root, installation, review = approve(tmp_path)
    paths = review_paths(output_root)
    execution_before = (
        SCRIPT_ROOT.parents[2] / "docs/experiments/suggest-moving-service-questions/v2-pilot/execution-manifest.json"
    ).read_bytes()
    plan = plan_preflight_activation(
        artifact_sha256=digest,
        installation_record_sha256=installation["installation_record_sha256"],
        activation_review_sha256=review["review_sha256"], output_root=output_root,
        now=datetime(2030, 1, 1, 12, 7, tzinfo=timezone.utc),
    )
    assert plan["writes_performed"] is False and plan["activated"] is False
    assert plan["future_active_destination"] == str(paths["future_active"].resolve())
    assert not paths["future_active"].exists()
    assert (
        SCRIPT_ROOT.parents[2] / "docs/experiments/suggest-moving-service-questions/v2-pilot/execution-manifest.json"
    ).read_bytes() == execution_before


@pytest.mark.parametrize("decision", ["reject", "request_changes"])
def test_nonapproval_permanently_blocks_planning(tmp_path: Path, decision: str) -> None:
    _, digest, output_root, installation, review = approve(tmp_path, decision)
    with pytest.raises(ActivationPrerequisiteError):
        plan_preflight_activation(
            artifact_sha256=digest,
            installation_record_sha256=installation["installation_record_sha256"],
            activation_review_sha256=review["review_sha256"], output_root=output_root,
            now=datetime(2030, 1, 1, 12, 7, tzinfo=timezone.utc),
        )


def test_plan_cli_outputs_bounded_fields_only(tmp_path: Path, capsys) -> None:
    _, digest, output_root, installation, review = approve(tmp_path)
    code = plan_main([
        "--artifact-sha256", digest,
        "--installation-record-sha256", installation["installation_record_sha256"],
        "--activation-review-sha256", review["review_sha256"],
    ], now=datetime(2030, 1, 1, 12, 7, tzinfo=timezone.utc), output_root=output_root)
    assert code == 0
    output = capsys.readouterr().out
    assert "writes_performed=false" in output and "activated=false" in output
    assert not review_paths(output_root)["future_active"].exists()


def test_modules_have_no_external_capability_or_environment_access() -> None:
    for name in (
        "v2_preflight_authorization_installation.py",
        "install_v2_preflight_authorization_for_review.py",
        "review_v2_preflight_authorization_activation.py",
        "plan_v2_preflight_authorization_activation.py",
    ):
        source = (SCRIPT_ROOT / name).read_text()
        for prohibited in (
            "os.environ", "OpenAI(", "client_constructor", "responses.create",
            "token_preflight(", "requests.", "httpx.", "urllib", "socket.",
        ):
            assert prohibited not in source


def test_candidates_manifest_umbrella_and_closed_state_remain_exact() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text())
    assert hashlib.sha256(PHASE_PATHS["preflight"].read_bytes()).hexdigest() == manifest["preflight_candidate_digest"]
    assert hashlib.sha256(PHASE_PATHS["generation"].read_bytes()).hexdigest() == manifest["generation_candidate_digest"]
    umbrella = SCRIPT_ROOT.parents[2] / manifest["umbrella_candidate_path"]
    assert hashlib.sha256(umbrella.read_bytes()).hexdigest() == UMBRELLA_DIGEST
    execution = SCRIPT_ROOT.parents[2] / "docs/experiments/suggest-moving-service-questions/v2-pilot/execution-manifest.json"
    assert execution.read_bytes() == execution.with_name("closed-execution-manifest.json").read_bytes()
