"""Offline tests for atomic v2 preflight activation and recovery."""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

SCRIPT_ROOT = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_ROOT.parents[2] / "backend"
for value in (SCRIPT_ROOT, BACKEND_ROOT):
    if str(value) not in sys.path:
        sys.path.insert(0, str(value))

from activate_v2_preflight_authorization import main as activation_main  # noqa: E402
from v2_phase_authorization_candidates import render_preflight_candidate  # noqa: E402
from v2_preflight_authorization_activation import (  # noqa: E402
    OPERATOR_INTENT, ActiveAuthorizationValidationError, ActivationClosedStateError,
    ActivationConflictError, ActivationReviewError, ActivationValidityError, RecoveryRequiredError,
    activate_preflight_authorization, activation_paths, load_active_preflight_authorization,
    recover_preflight_activation,
)
from v2_preflight_authorization_installation import (  # noqa: E402
    install_preflight_for_review, review_paths, review_preflight_activation,
)

REPOSITORY_ROOT = SCRIPT_ROOT.parents[2]
NOW = datetime(2030, 1, 1, 12, 7, tzinfo=timezone.utc)


def _repository(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    target = root / "docs/experiments/suggest-moving-service-questions/v2-pilot"
    target.mkdir(parents=True)
    source = REPOSITORY_ROOT / "docs/experiments/suggest-moving-service-questions/v2-pilot"
    for name in (
        "execution-manifest.json", "closed-execution-manifest.json",
        "openai-execution-authorization.toml",
    ):
        (target / name).write_bytes((source / name).read_bytes())
    return root


def _approved_package(tmp_path: Path, decision: str = "approve") -> dict[str, object]:
    source = tmp_path / "rendered.toml"
    rendered = render_preflight_candidate(
        output_path=source, approver="Human Approver",
        approved_at="2030-01-01T12:00:00Z", activated_at="2030-01-01T12:04:00Z",
        expires_at="2030-01-01T12:15:00Z",
        authorization_reason="One reviewed preflight", now=datetime(2030, 1, 1, 12, 5, tzinfo=timezone.utc),
    )
    output_root = tmp_path / "local"
    installation = install_preflight_for_review(
        source=source, expected_sha256=rendered.digest, output_root=output_root,
        now=datetime(2030, 1, 1, 12, 5, tzinfo=timezone.utc),
    )
    review = review_preflight_activation(
        artifact_sha256=rendered.digest, reviewer="Activation Reviewer", decision=decision,
        reviewed_at="2030-01-01T12:06:00Z", notes="Bounded approval.",
        output_root=output_root, now=datetime(2030, 1, 1, 12, 6, tzinfo=timezone.utc),
    )
    return {
        "repository_root": _repository(tmp_path), "output_root": output_root,
        "artifact": rendered.digest,
        "installation": installation["installation_record_sha256"],
        "review": review["review_sha256"], "source": source,
    }


def _activate(package: dict[str, object], **changes):
    arguments = {
        "artifact_sha256": package["artifact"],
        "installation_record_sha256": package["installation"],
        "activation_review_sha256": package["review"],
        "operator": "Test Operator", "operator_intent": OPERATOR_INTENT, "now": NOW,
        "repository_root": package["repository_root"], "output_root": package["output_root"],
        "transaction_id_factory": lambda: "synthetictransaction001",
    }
    arguments.update(changes)
    return activate_preflight_authorization(**arguments)


def test_complete_synthetic_activation_is_exact_preflight_only_and_committed(tmp_path: Path) -> None:
    package = _approved_package(tmp_path)
    installed_before = review_paths(package["output_root"])["installed"].read_bytes()
    result = _activate(package)
    paths = activation_paths(repository_root=package["repository_root"], output_root=package["output_root"])
    manifest = json.loads(paths.execution_manifest.read_text())
    evidence = json.loads(paths.activation.read_text())
    journal = json.loads(paths.journal.read_text())
    assert paths.active.read_bytes() == installed_before
    assert hashlib.sha256(paths.active.read_bytes()).hexdigest() == package["artifact"]
    assert manifest["authorization_digest"] == package["artifact"]
    assert manifest["token_preflight_authorized"] is True
    assert manifest["maximum_token_preflight_requests"] == 1
    assert manifest["ai_generation_authorized"] is False
    assert manifest["maximum_ai_generation_requests"] == 0
    assert manifest["automatic_retries"] == 0
    assert manifest["maximum_total_spend_usd"] == "0.03"
    assert evidence["active_execution_manifest_digest"] == result["execution_manifest_sha256"]
    assert evidence["generation_authorized"] is False
    assert evidence["transaction_state"] == journal["transaction_state"] == "committed"
    verified = load_active_preflight_authorization(
        repository_root=package["repository_root"], output_root=package["output_root"], now=NOW,
    )
    assert verified.authorization.phase == "preflight"


def test_activation_cli_prints_only_bounded_machine_fields(tmp_path: Path, capsys) -> None:
    package = _approved_package(tmp_path)
    code = activation_main([
        "--artifact-sha256", package["artifact"],
        "--installation-record-sha256", package["installation"],
        "--activation-review-sha256", package["review"],
        "--operator", "Test Operator", "--operator-intent", OPERATOR_INTENT,
    ], now=NOW, repository_root=package["repository_root"], output_root=package["output_root"])
    assert code == 0
    output = capsys.readouterr().out.splitlines()
    assert [line.split("=", 1)[0] for line in output] == [
        "active_authorization", "active_authorization_sha256", "execution_manifest_sha256",
        "activation_record", "activation_record_sha256", "transaction_id",
        "transaction_state", "phase", "generation_authorized",
    ]
    assert output[-3:] == [f"transaction_state=committed", "phase=preflight", "generation_authorized=false"]


@pytest.mark.parametrize("operator,intent", [("", OPERATOR_INTENT), ("Operator", "wrong")])
def test_operator_and_exact_intent_are_required(tmp_path: Path, operator: str, intent: str) -> None:
    package = _approved_package(tmp_path)
    with pytest.raises(ActivationReviewError):
        _activate(package, operator=operator, operator_intent=intent)
    paths = activation_paths(repository_root=package["repository_root"], output_root=package["output_root"])
    assert not paths.active.exists() and paths.execution_manifest.read_bytes() == paths.closed_manifest.read_bytes()


def test_nonapproved_review_cannot_activate(tmp_path: Path) -> None:
    package = _approved_package(tmp_path, decision="reject")
    with pytest.raises(ActivationReviewError):
        _activate(package)


def test_expired_reviewed_package_is_rejected_before_transaction(tmp_path: Path) -> None:
    package = _approved_package(tmp_path)
    with pytest.raises(ActivationValidityError):
        _activate(package, now=datetime(2030, 1, 1, 12, 15, 1, tzinfo=timezone.utc))
    paths = activation_paths(repository_root=package["repository_root"], output_root=package["output_root"])
    assert not paths.journal.exists() and paths.execution_manifest.read_bytes() == paths.closed_manifest.read_bytes()


@pytest.mark.parametrize("digest_name", ["artifact", "installation", "review"])
def test_wrong_input_digest_is_rejected_before_writes(tmp_path: Path, digest_name: str) -> None:
    package = _approved_package(tmp_path)
    package[digest_name] = "0" * 64
    with pytest.raises((ActivationReviewError, ActivationClosedStateError)):
        _activate(package)
    paths = activation_paths(repository_root=package["repository_root"], output_root=package["output_root"])
    assert not paths.active.exists() and not paths.journal.exists()


def test_closed_manifest_and_permanent_authorization_drift_are_rejected(tmp_path: Path) -> None:
    for filename in ("execution-manifest.json", "openai-execution-authorization.toml"):
        case = tmp_path / filename.replace(".", "-")
        case.mkdir()
        package = _approved_package(case)
        target = Path(package["repository_root"]) / "docs/experiments/suggest-moving-service-questions/v2-pilot" / filename
        target.write_bytes(target.read_bytes() + b"\n")
        with pytest.raises(ActivationClosedStateError):
            _activate(package)


@pytest.mark.parametrize(
    "failpoint",
    ["after_prepared", "after_authorization_installed", "after_manifest_activated", "after_activation_recorded", "before_commit"],
)
def test_every_interruption_fails_closed_and_recovers_exactly(tmp_path: Path, failpoint: str) -> None:
    package = _approved_package(tmp_path)
    paths = activation_paths(repository_root=package["repository_root"], output_root=package["output_root"])
    closed = paths.closed_manifest.read_bytes()
    with pytest.raises(RecoveryRequiredError):
        _activate(package, failpoint=failpoint)
    with pytest.raises(ActiveAuthorizationValidationError):
        load_active_preflight_authorization(
            repository_root=package["repository_root"], output_root=package["output_root"], now=NOW,
        )
    record = recover_preflight_activation(
        reason="activation_recovery", now=NOW, repository_root=package["repository_root"],
        output_root=package["output_root"],
    )
    assert paths.execution_manifest.read_bytes() == closed
    assert not paths.active.exists()
    assert record["authorization_closed"] is True
    assert json.loads(paths.journal.read_text())["transaction_state"] == "rolled_back"
    assert recover_preflight_activation(
        reason="activation_recovery", now=NOW, repository_root=package["repository_root"],
        output_root=package["output_root"],
    ) == record


@pytest.mark.parametrize("missing", ["active", "activation", "journal"])
def test_missing_component_of_committed_state_fails_closed(tmp_path: Path, missing: str) -> None:
    package = _approved_package(tmp_path)
    _activate(package)
    paths = activation_paths(repository_root=package["repository_root"], output_root=package["output_root"])
    getattr(paths, missing).unlink()
    with pytest.raises(ActiveAuthorizationValidationError):
        load_active_preflight_authorization(
            repository_root=package["repository_root"], output_root=package["output_root"], now=NOW,
        )


def test_active_manifest_without_file_and_digest_mismatch_fail_closed(tmp_path: Path) -> None:
    package = _approved_package(tmp_path)
    _activate(package)
    paths = activation_paths(repository_root=package["repository_root"], output_root=package["output_root"])
    manifest = json.loads(paths.execution_manifest.read_text())
    manifest["authorization_digest"] = "0" * 64
    paths.execution_manifest.write_text(json.dumps(manifest) + "\n")
    with pytest.raises(ActiveAuthorizationValidationError):
        load_active_preflight_authorization(
            repository_root=package["repository_root"], output_root=package["output_root"], now=NOW,
        )


@pytest.mark.parametrize("conflict", ["active", "activation", "journal"])
def test_conflicting_attempt_active_or_transaction_state_rejected(tmp_path: Path, conflict: str) -> None:
    package = _approved_package(tmp_path)
    paths = activation_paths(repository_root=package["repository_root"], output_root=package["output_root"])
    target = getattr(paths, conflict)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("conflict")
    with pytest.raises(ActivationConflictError):
        _activate(package)


def test_existing_preflight_audit_marks_sequence_used_before_activation(tmp_path: Path) -> None:
    package = _approved_package(tmp_path)
    base = Path(package["output_root"]) / "moving-service-stage-b-v2-pilot-20260802"
    (base / "001-storage_unknown-preflight.json").write_text("{}\n")
    with pytest.raises((ActivationReviewError, ActivationConflictError)):
        _activate(package)


def test_runtime_rejects_expired_committed_authority(tmp_path: Path) -> None:
    package = _approved_package(tmp_path)
    _activate(package)
    with pytest.raises(ActiveAuthorizationValidationError):
        load_active_preflight_authorization(
            repository_root=package["repository_root"], output_root=package["output_root"],
            now=datetime(2030, 1, 1, 12, 15, 1, tzinfo=timezone.utc),
        )


def test_completed_activation_closure_restores_exact_closed_state_and_is_idempotent(tmp_path: Path) -> None:
    package = _approved_package(tmp_path)
    _activate(package)
    paths = activation_paths(repository_root=package["repository_root"], output_root=package["output_root"])
    activation_bytes = paths.activation.read_bytes()
    result = recover_preflight_activation(
        reason="operator_cancellation", now=NOW, repository_root=package["repository_root"],
        output_root=package["output_root"],
    )
    assert paths.execution_manifest.read_bytes() == paths.closed_manifest.read_bytes()
    assert not paths.active.exists() and paths.activation.read_bytes() == activation_bytes
    assert result["authorization_closed"] is True
    assert recover_preflight_activation(
        reason="operator_cancellation", now=NOW, repository_root=package["repository_root"],
        output_root=package["output_root"],
    ) == result


def test_activation_modules_have_no_environment_client_or_network_access() -> None:
    for filename in ("v2_preflight_authorization_activation.py", "activate_v2_preflight_authorization.py"):
        source = (SCRIPT_ROOT / filename).read_text()
        for prohibited in (
            "os.environ", "getenv(", "OpenAI(", "client_constructor", "responses.create",
            "token_preflight(", "requests.", "httpx.", "urllib", "socket.",
        ):
            assert prohibited not in source


def test_real_repository_stays_exactly_closed() -> None:
    directory = REPOSITORY_ROOT / "docs/experiments/suggest-moving-service-questions/v2-pilot"
    assert (directory / "execution-manifest.json").read_bytes() == (directory / "closed-execution-manifest.json").read_bytes()
