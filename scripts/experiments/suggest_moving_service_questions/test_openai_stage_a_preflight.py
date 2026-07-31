"""Offline proof for the inactive, preflight-only Stage A path."""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import replace
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
from run_openai_stage_a_preflight import (  # noqa: E402
    STAGE_A_CANDIDATE_DIGEST,
    STAGE_A_OPERATOR_INTENT,
    _execute_verified_stage_a_preflight,
    _load_stage_a_candidate,
    run_stage_a_token_preflight,
)
from run_real_model_evaluation import OfflineRunnerGateError  # noqa: E402


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


class FakeHttpClient:
    def __init__(self, **_: object) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


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
    with pytest.raises(OfflineRunnerGateError, match="not active"):
        run_stage_a_token_preflight(
            environment=EnvironmentThatMustNotBeRead(),
            operator_intent=STAGE_A_OPERATOR_INTENT,
        )


def test_candidate_cannot_be_passed_directly_to_credential_factory() -> None:
    candidate = _load_stage_a_candidate()
    with pytest.raises(CredentialAccessNotAuthorizedError, match="not active"):
        build_moving_service_openai_client_from_environment(
            EnvironmentThatMustNotBeRead(),
            completed_non_secret_gates=REQUIRED_NON_SECRET_GATE_ORDER,
            operator_intent_confirmed=True,
            authorization_path=candidate.path,
            expected_authorization_digest=candidate.digest,
            client_constructor=lambda **_: pytest.fail("client constructed"),
            http_client_constructor=lambda **_: pytest.fail("HTTP client constructed"),
        )


def test_offline_preflight_path_cannot_reach_generation(tmp_path: Path) -> None:
    candidate = _load_stage_a_candidate()
    approved_at = datetime.now(timezone.utc) - timedelta(seconds=10)
    expires_at = approved_at + timedelta(minutes=5)
    active_text = candidate.path.read_text().replace(
        'authorization_status = "candidate_pending_explicit_approval"',
        'authorization_status = "approved_stage_a_token_preflight"',
    ).replace(
        "active_repository_authority = false",
        "active_repository_authority = true",
    ).replace(
        'approval_status = "pending_explicit_human_approval"',
        'approval_status = "approved"',
    ).replace(
        'approved_at = "pending"',
        f'approved_at = "{approved_at.isoformat()}"',
    ).replace(
        'expires_at = "pending"',
        f'expires_at = "{expires_at.isoformat()}"',
    ).replace(
        'approved_by = "pending"',
        'approved_by = "offline-test-reviewer"',
    )
    active_path = tmp_path / "synthetic-active-stage-a.toml"
    active_path.write_text(active_text)
    synthetic_candidate = replace(
        candidate,
        path=active_path,
        digest=hashlib.sha256(active_path.read_bytes()).hexdigest(),
    )
    created_clients: list[FakeClient] = []

    def make_client(**kwargs: object) -> FakeClient:
        client = FakeClient(**kwargs)
        created_clients.append(client)
        return client

    def fake_builder(
        environment: dict[str, str], **kwargs: object
    ) -> object:
        return build_moving_service_openai_client_from_environment(
            environment,
            completed_non_secret_gates=kwargs["completed_non_secret_gates"],
            operator_intent_confirmed=kwargs["operator_intent_confirmed"],
            authorization_path=kwargs["authorization_path"],
            expected_authorization_digest=kwargs["expected_authorization_digest"],
            client_constructor=make_client,
            http_client_constructor=FakeHttpClient,
        )

    result = _execute_verified_stage_a_preflight(
        candidate=synthetic_candidate,
        environment={EVALUATION_CREDENTIAL_NAME: "synthetic-not-a-real-key"},
        output_root=tmp_path / "records",
        client_builder=fake_builder,  # type: ignore[arg-type]
    )

    fake_client = created_clients[0]
    assert len(fake_client.responses.input_tokens.calls) == 1
    assert fake_client.responses.generation_calls == 0
    assert fake_client.closed is True
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


def test_stage_a_module_contains_no_generation_operation() -> None:
    source = (SCRIPT_ROOT / "run_openai_stage_a_preflight.py").read_text()

    assert ".generate(" not in source
    assert ".responses.create(" not in source
    assert "maximum_ai_generation_requests = 0" not in source
