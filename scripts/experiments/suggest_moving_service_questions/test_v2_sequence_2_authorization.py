"""Offline sequence-2 candidate and cross-sequence isolation tests."""

from __future__ import annotations

import hashlib
import json
import sys
import tomllib
from datetime import datetime, timezone
from pathlib import Path

import pytest

SCRIPT_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = SCRIPT_ROOT.parents[2]
for value in (SCRIPT_ROOT, REPOSITORY_ROOT / "backend"):
    if str(value) not in sys.path:
        sys.path.insert(0, str(value))

from v2_phase_authorization_candidates import (  # noqa: E402
    V2PhaseCandidateError,
    load_inactive_phase_candidate,
    render_preflight_candidate,
    render_preflight_candidate_for_sequence,
)
from v2_preflight_authorization_activation import (  # noqa: E402
    ActiveAuthorizationValidationError,
    activation_paths,
    load_active_preflight_authorization,
)
from v2_sequence_2_authorization_candidate import (  # noqa: E402
    CANDIDATE_PATH,
    MANIFEST_PATH,
    load_sequence_2_preflight_candidate,
)
from v2_sequence_2_preflight_authorization import (  # noqa: E402
    CANDIDATE_DIGEST,
    CANDIDATE_MANIFEST_DIGEST,
    OPERATOR_INTENT,
    activate_sequence_2_preflight,
    install_sequence_2_for_review,
    plan_sequence_2_activation,
    recover_sequence_2_preflight,
    review_sequence_2_activation,
    sequence_2_review_paths,
)
from v2_two_gate_authorization import V2TwoGateAuthorizationError, validate_phase_authorization  # noqa: E402
from render_v2_sequence_2_preflight_authorization_candidate import main as render_sequence_2_main  # noqa: E402
from run_openai_stage_b_v2_pilot import prepare_frozen_v2_pilot  # noqa: E402
from run_openai_stage_b_v2_two_gate import frozen_binding_identity  # noqa: E402

NOW = datetime(2030, 1, 1, 12, 7, tzinfo=timezone.utc)
SEQUENCE_1_DIGEST = "a3f1000bb1b336bad4fb35e9316520f59eb1eeb96e257f19eb13e9d495504a6c"


def _render(tmp_path: Path, *, sequence: int = 2):
    if sequence == 2:
        return render_preflight_candidate_for_sequence(
            sequence=2, candidate_loader=load_sequence_2_preflight_candidate,
            output_path=tmp_path / "sequence-2.toml", approver="Human Approver",
            approved_at="2030-01-01T12:00:00Z", activated_at="2030-01-01T12:04:00Z",
            expires_at="2030-01-01T12:15:00Z", authorization_reason="Sequence 2 only",
            now=datetime(2030, 1, 1, 12, 5, tzinfo=timezone.utc),
        )
    return render_preflight_candidate(
        output_path=tmp_path / "sequence-1.toml", approver="Human Approver",
        approved_at="2030-01-01T12:00:00Z", activated_at="2030-01-01T12:04:00Z",
        expires_at="2030-01-01T12:15:00Z", authorization_reason="Sequence 1 only",
        now=datetime(2030, 1, 1, 12, 5, tzinfo=timezone.utc),
    )


def _repository(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    target = root / "docs/experiments/suggest-moving-service-questions/v2-pilot"
    target.mkdir(parents=True)
    source = REPOSITORY_ROOT / "docs/experiments/suggest-moving-service-questions/v2-pilot"
    for name in ("execution-manifest.json", "closed-execution-manifest.json", "openai-execution-authorization.toml"):
        (target / name).write_bytes((source / name).read_bytes())
    return root


def _approved_package(tmp_path: Path):
    rendered = _render(tmp_path)
    output_root = tmp_path / "local"
    installation = install_sequence_2_for_review(
        source=rendered.path, expected_sha256=rendered.digest,
        output_root=output_root, now=datetime(2030, 1, 1, 12, 5, tzinfo=timezone.utc),
    )
    review = review_sequence_2_activation(
        artifact_sha256=rendered.digest, reviewer="Reviewer", decision="approve",
        reviewed_at="2030-01-01T12:06:00Z", notes="Sequence 2 reviewed.",
        output_root=output_root, now=datetime(2030, 1, 1, 12, 6, tzinfo=timezone.utc),
    )
    return rendered, output_root, installation, review


def test_sequence_2_candidate_is_distinct_inactive_and_digest_bound() -> None:
    candidate = load_sequence_2_preflight_candidate()
    assert candidate.digest == CANDIDATE_DIGEST == hashlib.sha256(CANDIDATE_PATH.read_bytes()).hexdigest()
    assert hashlib.sha256(MANIFEST_PATH.read_bytes()).hexdigest() == CANDIDATE_MANIFEST_DIGEST
    assert candidate.artifact["scope"]["sequence"] == 2
    assert candidate.artifact["authorization"]["credential_access_authorized"] is False
    assert candidate.artifact["proposed_authorization"]["ai_generation_authorized"] is False
    assert load_inactive_phase_candidate("preflight").digest == SEQUENCE_1_DIGEST


def test_unresolved_sequence_2_candidate_cannot_be_active() -> None:
    candidate = load_sequence_2_preflight_candidate()
    with pytest.raises(V2TwoGateAuthorizationError):
        validate_phase_authorization(
            candidate.artifact, digest=candidate.digest, phase="preflight", now=NOW,
            expected_bindings=frozen_binding_identity(prepare_frozen_v2_pilot()), expected_sequence=2,
        )


def test_fixed_sequence_2_renderer_cli_has_no_sequence_override(tmp_path: Path, capsys) -> None:
    output = tmp_path / "rendered-sequence-2.toml"
    arguments = [
        "--output", str(output), "--approver", "Approver",
        "--approved-at", "2030-01-01T12:00:00Z",
        "--activated-at", "2030-01-01T12:04:00Z",
        "--expires-at", "2030-01-01T12:15:00Z", "--reason", "Sequence 2 only",
    ]
    assert render_sequence_2_main(arguments, now=datetime(2030, 1, 1, 12, 5, tzinfo=timezone.utc)) == 0
    assert [line.split("=", 1)[0] for line in capsys.readouterr().out.splitlines()] == ["output_path", "sha256"]
    assert tomllib.loads(output.read_text())["scope"]["sequence"] == 2
    with pytest.raises(SystemExit):
        render_sequence_2_main(arguments + ["--sequence", "1"], now=NOW)


def test_sequence_2_render_and_review_paths_are_fixed_to_002(tmp_path: Path) -> None:
    rendered, output_root, installation, review = _approved_package(tmp_path)
    artifact = tomllib.loads(rendered.path.read_text())
    assert artifact["scope"]["sequence"] == 2
    assert artifact["authorization"]["ai_generation_authorized"] is False
    paths = sequence_2_review_paths(output_root)
    assert all("002-storage_unknown" in path.name for key, path in paths.items() if key != "directory")
    assert all("001-storage_unknown" not in str(path) for path in paths.values())
    plan = plan_sequence_2_activation(
        artifact_sha256=rendered.digest,
        installation_record_sha256=installation["installation_record_sha256"],
        activation_review_sha256=review["review_sha256"], output_root=output_root, now=NOW,
    )
    assert "002-storage_unknown" in plan["future_active_destination"]
    assert "002-storage_unknown" in plan["activation_record"]
    assert "002-storage_unknown" in plan["transaction_journal"]
    assert plan["authoritative"] is False and plan["writes_performed"] is False


def test_sequence_1_artifact_cannot_install_as_sequence_2(tmp_path: Path) -> None:
    rendered = _render(tmp_path, sequence=1)
    with pytest.raises(ValueError):
        install_sequence_2_for_review(
            source=rendered.path, expected_sha256=rendered.digest,
            output_root=tmp_path / "local", now=NOW,
        )


def test_sequence_2_activation_commits_only_002_and_recovers_closed(tmp_path: Path) -> None:
    rendered, output_root, installation, review = _approved_package(tmp_path)
    repository = _repository(tmp_path)
    result = activate_sequence_2_preflight(
        artifact_sha256=rendered.digest,
        installation_record_sha256=installation["installation_record_sha256"],
        activation_review_sha256=review["review_sha256"], operator="Operator",
        operator_intent=OPERATOR_INTENT, now=NOW, repository_root=repository,
        output_root=output_root, transaction_id_factory=lambda: "sequence2transaction",
    )
    paths = activation_paths(repository_root=repository, output_root=output_root, sequence=2)
    assert result["transaction_state"] == "committed"
    assert paths.active.name.startswith("002-") and paths.activation.name.startswith("002-")
    assert not any((output_root / "moving-service-stage-b-v2-pilot-20260802").glob("001-*"))
    verified = load_active_preflight_authorization(
        repository_root=repository, output_root=output_root, now=NOW, expected_sequence=2,
    )
    assert verified.authorization.phase == "preflight"
    assert json.loads(paths.execution_manifest.read_text())["sequence"] == 2
    with pytest.raises(ActiveAuthorizationValidationError):
        load_active_preflight_authorization(
            repository_root=repository, output_root=output_root, now=NOW, expected_sequence=1,
        )
    closure = recover_sequence_2_preflight(
        reason="operator_cancellation", now=NOW, repository_root=repository, output_root=output_root,
    )
    assert closure["sequence"] == 2 and closure["authorization_closed"] is True
    assert paths.execution_manifest.read_bytes() == paths.closed_manifest.read_bytes()
    assert recover_sequence_2_preflight(
        reason="operator_cancellation", now=NOW, repository_root=repository, output_root=output_root,
    ) == closure


def test_sequence_2_candidate_manifest_drift_is_rejected(monkeypatch, tmp_path: Path) -> None:
    drifted = tmp_path / "manifest.json"
    payload = json.loads(MANIFEST_PATH.read_text())
    payload["sequence"] = 1
    drifted.write_text(json.dumps(payload))
    import v2_sequence_2_authorization_candidate as module
    monkeypatch.setattr(module, "MANIFEST_PATH", drifted)
    with pytest.raises(V2PhaseCandidateError):
        module.load_sequence_2_preflight_candidate()
