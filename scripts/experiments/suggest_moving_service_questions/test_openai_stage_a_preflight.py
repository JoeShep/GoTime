"""Offline proof for the inactive, preflight-only Stage A path."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

SCRIPT_ROOT = Path(__file__).resolve().parent
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from openai_client_factory import (  # noqa: E402
    CredentialAccessNotAuthorizedError,
    EVALUATION_CREDENTIAL_NAME,
    REQUIRED_NON_SECRET_GATE_ORDER,
    build_moving_service_openai_client_from_environment,
)
import evaluate_baseline  # noqa: E402
from run_openai_stage_a_preflight import (  # noqa: E402
    STAGE_A_CANDIDATE_DIGEST,
    STAGE_A_OPERATOR_INTENT,
    _execute_verified_stage_a_preflight,
    _load_stage_a_candidate,
    run_stage_a_token_preflight,
)
from run_real_model_evaluation import OfflineRunnerGateError  # noqa: E402
from stage_a_authorization import (  # noqa: E402
    STAGE_A_FINAL_ARTIFACT_PATH,
    StageAAuthorizationError,
    load_manifest_bound_stage_a_authorization,
)


class EnvironmentThatMustNotBeRead(dict[str, str]):
    def __contains__(self, key: object) -> bool:
        raise AssertionError(f"environment membership read: {key}")

    def get(self, key: str, default: object = None) -> object:
        raise AssertionError(f"environment value read: {key}")


class FakeInputTokens:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def count(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        return SimpleNamespace(input_tokens=777)


class FakeResponses:
    def __init__(self) -> None:
        self.input_tokens = FakeInputTokens()
        self.generation_calls = 0

    def create(self, **_: object) -> object:
        self.generation_calls += 1
        raise AssertionError("Stage A reached AI generation")


class FakeClient:
    def __init__(self, **kwargs: object) -> None:
        self.max_retries = int(kwargs["max_retries"])
        self.responses = FakeResponses()
        self.closed = False

    def close(self) -> None:
        self.closed = True


class FakeOwnedClient:
    def __init__(self, client: FakeClient) -> None:
        self.client = client
        self.closed = False

    def __enter__(self) -> "FakeOwnedClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.closed = True


def _write_future_stage_a_package(
    root: Path,
    *,
    approved_at: datetime,
) -> tuple[Path, Path, datetime]:
    repository_root = SCRIPT_ROOT.parents[2]
    artifact_root = root / "docs/experiments/suggest-moving-service-questions/v1"
    artifact_root.mkdir(parents=True)
    for name in (
        "real-model-prompt.toml",
        "openai-run-configuration.toml",
        "openai-response-schema.json",
        "openai-stage-a-authorization-candidate.toml",
    ):
        shutil.copyfile(
            repository_root
            / "docs/experiments/suggest-moving-service-questions/v1"
            / name,
            artifact_root / name,
        )
    expires_at = approved_at + timedelta(seconds=900)
    candidate_text = (
        artifact_root / "openai-stage-a-authorization-candidate.toml"
    ).read_text()
    final_text = candidate_text.replace(
        'authorization_status = "candidate_pending_explicit_approval"',
        'authorization_status = "approved_stage_a_token_preflight"',
    ).replace(
        'created_at = "2026-07-31T22:54:07Z"',
        f'created_at = "{approved_at.strftime("%Y-%m-%dT%H:%M:%SZ")}"',
    ).replace(
        "active_repository_authority = false",
        "active_repository_authority = true",
    ).replace(
        'approval_status = "pending_explicit_human_approval"',
        'approval_status = "approved"',
    ).replace(
        'approved_at = "pending"',
        f'approved_at = "{approved_at.strftime("%Y-%m-%dT%H:%M:%SZ")}"',
    ).replace(
        'expires_at = "pending"',
        f'expires_at = "{expires_at.strftime("%Y-%m-%dT%H:%M:%SZ")}"',
    ).replace(
        'approved_by = "pending"',
        'approved_by = "Joe Shepherd"',
    )
    for obsolete in (
        "activation_requires_new_final_artifact = true\n",
        "activation_requires_new_digest = true\n",
        "activation_requires_manifest_repoint = true\n",
    ):
        final_text = final_text.replace(obsolete, "")
    final_path = root / STAGE_A_FINAL_ARTIFACT_PATH
    final_path.write_text(final_text)
    final_digest = hashlib.sha256(final_path.read_bytes()).hexdigest()
    manifest = json.loads(
        (
            repository_root
            / "docs/experiments/suggest-moving-service-questions/v1/manifest.json"
        ).read_text()
    )
    manifest.update(
        {
            "artifact_version": "1.7.0",
            "openai_execution_authorization_path": STAGE_A_FINAL_ARTIFACT_PATH,
            "openai_execution_authorization_version": (
                "moving-service-openai-stage-a-authorization-v1"
            ),
            "openai_execution_authorization_digest_algorithm": "sha256",
            "openai_execution_authorization_digest": final_digest,
            "openai_execution_authorization_status": (
                "approved_stage_a_token_preflight"
            ),
            "openai_stage_a_authorization_candidate_status": (
                "candidate_superseded_by_approved_stage_a"
            ),
            "openai_stage_a_authorization_candidate_activated": True,
            "status": "openai_stage_a_token_preflight_authorized",
        }
    )
    manifest_path = artifact_root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest_path, final_path, approved_at + timedelta(seconds=1)


def test_candidate_is_exact_and_not_active_repository_authority() -> None:
    candidate = _load_stage_a_candidate()

    assert candidate.digest == STAGE_A_CANDIDATE_DIGEST
    assert candidate.artifact["authorization"] == {
        "credential_access_authorized": True,
        "token_preflight_authorized": True,
        "ai_generation_authorized": False,
        "formal_evaluation_authorized": False,
    }
    assert candidate.artifact["metadata"]["active_repository_authority"] is False
    assert candidate.artifact["approval"]["approval_status"] == (
        "pending_explicit_human_approval"
    )


def test_public_stage_a_path_stops_before_environment_or_client() -> None:
    with pytest.raises(OfflineRunnerGateError, match="does not authorize"):
        run_stage_a_token_preflight(
            environment=EnvironmentThatMustNotBeRead(),
            operator_intent=STAGE_A_OPERATOR_INTENT,
        )


def test_candidate_cannot_be_passed_directly_to_credential_factory() -> None:
    candidate = _load_stage_a_candidate()
    with pytest.raises(
        CredentialAccessNotAuthorizedError,
        match="does not authorize",
    ):
        build_moving_service_openai_client_from_environment(
            EnvironmentThatMustNotBeRead(),
            completed_non_secret_gates=REQUIRED_NON_SECRET_GATE_ORDER,
            operator_intent_confirmed=True,
            manifest_path=(
                SCRIPT_ROOT.parents[2]
                / "docs/experiments/suggest-moving-service-questions/v1/manifest.json"
            ),
            authorization_path=candidate.path,
            expected_authorization_digest=candidate.digest,
            client_constructor=lambda **_: pytest.fail("client constructed"),
            http_client_constructor=lambda **_: pytest.fail("HTTP client constructed"),
        )


def test_public_stage_a_path_rejects_alternate_manifest(tmp_path: Path) -> None:
    alternate_manifest = tmp_path / "manifest.json"
    alternate_manifest.write_text("{}\n")

    with pytest.raises(OfflineRunnerGateError, match="active manifest"):
        run_stage_a_token_preflight(
            environment=EnvironmentThatMustNotBeRead(),
            operator_intent=STAGE_A_OPERATOR_INTENT,
            manifest_path=alternate_manifest,
        )


def test_offline_preflight_path_cannot_reach_generation(tmp_path: Path) -> None:
    manifest_path, _, now = _write_future_stage_a_package(
        tmp_path,
        approved_at=datetime(2030, 1, 1, 12, 0, tzinfo=timezone.utc),
    )
    authorization = load_manifest_bound_stage_a_authorization(
        manifest_path,
        repository_root=tmp_path,
        now=now,
    )
    artifact_validation = (
        evaluate_baseline.validate_future_manifest_bound_stage_a_authorization(
            manifest_path,
            repository_root=tmp_path,
            now=now,
        )
    )
    assert artifact_validation.digest == authorization.digest
    fake_client = FakeClient(max_retries=0)
    owned = FakeOwnedClient(fake_client)

    def fake_builder(*_: object, **__: object) -> FakeOwnedClient:
        return owned

    result = _execute_verified_stage_a_preflight(
        authorization=authorization,
        manifest_path=manifest_path,
        environment={EVALUATION_CREDENTIAL_NAME: "synthetic-not-a-real-key"},
        output_root=tmp_path / "records",
        client_builder=fake_builder,  # type: ignore[arg-type]
    )

    assert len(fake_client.responses.input_tokens.calls) == 1
    assert fake_client.responses.generation_calls == 0
    assert owned.closed is True
    assert result.record.preflight_attempted is True
    assert result.record.preflight_succeeded is True
    assert result.record.input_tokens == 777
    assert result.record.generation_attempted is False
    assert result.record.generation_spend == "0.00"
    record_data = json.loads(result.record_path.read_text())
    prohibited = {
        "system_instructions",
        "serialized_request",
        "full_response",
        "trusted_state",
        "credential",
        "authorization_header",
    }
    assert prohibited.isdisjoint(record_data)


def test_future_authorization_rejects_manifest_digest_drift(tmp_path: Path) -> None:
    manifest_path, _, now = _write_future_stage_a_package(
        tmp_path,
        approved_at=datetime(2030, 1, 1, 12, 0, tzinfo=timezone.utc),
    )
    manifest = json.loads(manifest_path.read_text())
    manifest["openai_execution_authorization_digest"] = "0" * 64
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    with pytest.raises(StageAAuthorizationError, match="digest does not match"):
        load_manifest_bound_stage_a_authorization(
            manifest_path, repository_root=tmp_path, now=now
        )


def test_future_authorization_rejects_nonexact_manifest_path(tmp_path: Path) -> None:
    manifest_path, _, now = _write_future_stage_a_package(
        tmp_path,
        approved_at=datetime(2030, 1, 1, 12, 0, tzinfo=timezone.utc),
    )
    manifest = json.loads(manifest_path.read_text())
    manifest["openai_execution_authorization_path"] = (
        "docs/experiments/suggest-moving-service-questions/v1/other.toml"
    )
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    with pytest.raises(StageAAuthorizationError, match="exact Stage A"):
        load_manifest_bound_stage_a_authorization(
            manifest_path, repository_root=tmp_path, now=now
        )


def test_future_authorization_rejects_semantic_permission_drift(
    tmp_path: Path,
) -> None:
    manifest_path, final_path, now = _write_future_stage_a_package(
        tmp_path,
        approved_at=datetime(2030, 1, 1, 12, 0, tzinfo=timezone.utc),
    )
    final_path.write_text(
        final_path.read_text().replace(
            "ai_generation_authorized = false",
            "ai_generation_authorized = true",
        )
    )
    manifest = json.loads(manifest_path.read_text())
    manifest["openai_execution_authorization_digest"] = hashlib.sha256(
        final_path.read_bytes()
    ).hexdigest()
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    with pytest.raises(StageAAuthorizationError, match="permissions"):
        load_manifest_bound_stage_a_authorization(
            manifest_path, repository_root=tmp_path, now=now
        )


def test_future_authorization_rejects_expired_window(tmp_path: Path) -> None:
    manifest_path, _, _ = _write_future_stage_a_package(
        tmp_path,
        approved_at=datetime(2030, 1, 1, 12, 0, tzinfo=timezone.utc),
    )

    with pytest.raises(StageAAuthorizationError, match="not currently active"):
        load_manifest_bound_stage_a_authorization(
            manifest_path,
            repository_root=tmp_path,
            now=datetime(2030, 1, 1, 12, 15, tzinfo=timezone.utc),
        )


def test_future_authorization_requires_exact_900_second_window(
    tmp_path: Path,
) -> None:
    manifest_path, final_path, now = _write_future_stage_a_package(
        tmp_path,
        approved_at=datetime(2030, 1, 1, 12, 0, tzinfo=timezone.utc),
    )
    final_path.write_text(
        final_path.read_text().replace(
            'expires_at = "2030-01-01T12:15:00Z"',
            'expires_at = "2030-01-01T12:14:59Z"',
        )
    )
    manifest = json.loads(manifest_path.read_text())
    manifest["openai_execution_authorization_digest"] = hashlib.sha256(
        final_path.read_bytes()
    ).hexdigest()
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    with pytest.raises(StageAAuthorizationError, match="exactly 900 seconds"):
        load_manifest_bound_stage_a_authorization(
            manifest_path, repository_root=tmp_path, now=now
        )


def test_stage_a_module_contains_no_generation_operation() -> None:
    source = (SCRIPT_ROOT / "run_openai_stage_a_preflight.py").read_text()

    assert ".generate(" not in source
    assert ".responses.create(" not in source
    assert "maximum_ai_generation_requests = 0" not in source
