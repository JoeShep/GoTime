"""Offline tests for the closed OpenAI credential and client boundary."""

from __future__ import annotations

import hashlib
import pickle
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

SCRIPT_ROOT = Path(__file__).resolve().parent
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from openai_client_factory import (  # noqa: E402
    EVALUATION_CREDENTIAL_NAME,
    OPENAI_API_BASE_URL,
    REQUIRED_NON_SECRET_GATE_ORDER,
    CredentialAccessNotAuthorizedError,
    EvaluationCredentialError,
    OpenAIClientConstructionError,
    _construct_openai_client,
    _read_evaluation_credential,
    build_moving_service_openai_client_from_environment,
)


SYNTHETIC_SECRET = "synthetic-test-secret-not-a-real-key"


class EnvironmentThatMustNotBeRead(dict[str, str]):
    def __contains__(self, key: object) -> bool:
        raise AssertionError(f"environment membership read: {key}")

    def get(self, key: str, default: object = None) -> object:
        raise AssertionError(f"environment value read: {key}")


class FakeHttpClient:
    def __init__(self, **kwargs: object) -> None:
        self.arguments = kwargs
        self.closed = False

    def close(self) -> None:
        self.closed = True


class FakeOpenAIClient:
    def __init__(self, **kwargs: object) -> None:
        self.arguments = kwargs
        self.max_retries = int(kwargs["max_retries"])
        self.closed = False

    def close(self) -> None:
        self.closed = True


def test_closed_repository_authorization_prevents_environment_access() -> None:
    client_calls: list[dict[str, object]] = []
    http_calls: list[dict[str, object]] = []

    with pytest.raises(CredentialAccessNotAuthorizedError, match="does not permit"):
        build_moving_service_openai_client_from_environment(
            EnvironmentThatMustNotBeRead(),
            completed_non_secret_gates=REQUIRED_NON_SECRET_GATE_ORDER,
            operator_intent_confirmed=True,
            client_constructor=lambda **kwargs: client_calls.append(kwargs),
            http_client_constructor=lambda **kwargs: http_calls.append(kwargs),
        )

    assert client_calls == []
    assert http_calls == []


def test_active_stage_a_window_permits_only_client_construction(
    tmp_path: Path,
) -> None:
    candidate_path = (
        SCRIPT_ROOT.parents[2]
        / "docs/experiments/suggest-moving-service-questions/v1/"
        "openai-stage-a-authorization-candidate.toml"
    )
    approved_at = datetime.now(timezone.utc) - timedelta(seconds=10)
    expires_at = approved_at + timedelta(minutes=5)
    active_text = candidate_path.read_text().replace(
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
    active_path = tmp_path / "active-stage-a.toml"
    active_path.write_text(active_text)
    active_digest = hashlib.sha256(active_path.read_bytes()).hexdigest()
    created_clients: list[FakeOpenAIClient] = []

    def make_client(**kwargs: object) -> FakeOpenAIClient:
        client = FakeOpenAIClient(**kwargs)
        created_clients.append(client)
        return client

    owned = build_moving_service_openai_client_from_environment(
        {EVALUATION_CREDENTIAL_NAME: SYNTHETIC_SECRET},
        completed_non_secret_gates=REQUIRED_NON_SECRET_GATE_ORDER,
        operator_intent_confirmed=True,
        authorization_path=active_path,
        expected_authorization_digest=active_digest,
        client_constructor=make_client,
        http_client_constructor=FakeHttpClient,
    )

    assert len(created_clients) == 1
    assert not hasattr(created_clients[0], "responses")
    owned.close()


def test_incomplete_runner_gates_fail_before_artifact_or_environment_access(
    tmp_path: Path,
) -> None:
    with pytest.raises(CredentialAccessNotAuthorizedError, match="gates"):
        build_moving_service_openai_client_from_environment(
            EnvironmentThatMustNotBeRead(),
            completed_non_secret_gates=(),
            operator_intent_confirmed=True,
            authorization_path=tmp_path / "must-not-be-read.toml",
            client_constructor=lambda **_: pytest.fail("client constructed"),
            http_client_constructor=lambda **_: pytest.fail("HTTP client constructed"),
        )


@pytest.mark.parametrize(
    ("environment", "message"),
    (
        ({}, "missing"),
        ({EVALUATION_CREDENTIAL_NAME: ""}, "blank"),
        ({EVALUATION_CREDENTIAL_NAME: "   "}, "blank"),
        ({EVALUATION_CREDENTIAL_NAME: "line1\nline2"}, "multiline"),
        ({EVALUATION_CREDENTIAL_NAME: "x" * 4_097}, "too long"),
        ({EVALUATION_CREDENTIAL_NAME: SYNTHETIC_SECRET, "OPENAI_API_KEY": "x"},
         "Conventional"),
    ),
)
def test_synthetic_credential_validation_fails_closed(
    environment: dict[str, str],
    message: str,
) -> None:
    with pytest.raises(EvaluationCredentialError, match=message) as caught:
        _read_evaluation_credential(environment)

    assert SYNTHETIC_SECRET not in str(caught.value)


def test_credential_is_redacted_and_not_serializable() -> None:
    credential = _read_evaluation_credential(
        {EVALUATION_CREDENTIAL_NAME: SYNTHETIC_SECRET}
    )

    assert SYNTHETIC_SECRET not in repr(credential)
    assert SYNTHETIC_SECRET not in str(credential)
    assert not hasattr(credential, "__dict__")
    with pytest.raises(TypeError, match="cannot be serialized"):
        pickle.dumps(credential)


def test_client_construction_is_explicit_and_calls_no_sdk_resource() -> None:
    credential = _read_evaluation_credential(
        {EVALUATION_CREDENTIAL_NAME: SYNTHETIC_SECRET}
    )
    created_http_clients: list[FakeHttpClient] = []
    created_clients: list[FakeOpenAIClient] = []

    def make_http_client(**kwargs: object) -> FakeHttpClient:
        client = FakeHttpClient(**kwargs)
        created_http_clients.append(client)
        return client

    def make_client(**kwargs: object) -> FakeOpenAIClient:
        client = FakeOpenAIClient(**kwargs)
        created_clients.append(client)
        return client

    owned_client = _construct_openai_client(
        credential,
        sdk_version="2.45.0",
        client_constructor=make_client,
        http_client_constructor=make_http_client,
    )

    assert created_http_clients[0].arguments == {"trust_env": False}
    assert created_clients[0].arguments == {
        "api_key": SYNTHETIC_SECRET,
        "base_url": OPENAI_API_BASE_URL,
        "max_retries": 0,
        "http_client": created_http_clients[0],
    }
    assert not hasattr(created_clients[0], "responses")
    owned_client.close()
    assert created_clients[0].closed is True
    assert created_http_clients[0].closed is True


def test_wrong_sdk_version_fails_before_any_constructor() -> None:
    calls: list[str] = []

    with pytest.raises(OpenAIClientConstructionError, match="SDK version"):
        _construct_openai_client(
            _read_evaluation_credential(
                {EVALUATION_CREDENTIAL_NAME: SYNTHETIC_SECRET}
            ),
            sdk_version="wrong",
            client_constructor=lambda **_: calls.append("client"),
            http_client_constructor=lambda **_: calls.append("http"),
        )

    assert calls == []


def test_constructor_failure_is_redacted_and_closes_http_client() -> None:
    http_client = FakeHttpClient()

    def fail_with_secret(**_: object) -> FakeOpenAIClient:
        raise RuntimeError(SYNTHETIC_SECRET)

    with pytest.raises(OpenAIClientConstructionError) as caught:
        _construct_openai_client(
            _read_evaluation_credential(
                {EVALUATION_CREDENTIAL_NAME: SYNTHETIC_SECRET}
            ),
            sdk_version="2.45.0",
            client_constructor=fail_with_secret,
            http_client_constructor=lambda **_: http_client,
        )

    assert SYNTHETIC_SECRET not in str(caught.value)
    assert http_client.closed is True


def test_factory_is_unreachable_from_runner_backend_and_frontend() -> None:
    factory_name = "openai_client_factory"
    runner_source = (SCRIPT_ROOT / "run_real_model_evaluation.py").read_text()
    assert factory_name not in runner_source

    for root_name in ("backend", "frontend"):
        root = SCRIPT_ROOT.parents[2] / root_name
        for path in root.rglob("*"):
            if path.is_file() and path.suffix in {".py", ".ts", ".tsx", ".js"}:
                assert factory_name not in path.read_text(errors="ignore")


def test_factory_module_contains_no_network_operation() -> None:
    source = (SCRIPT_ROOT / "openai_client_factory.py").read_text()

    for prohibited in (
        ".responses.",
        ".input_tokens.",
        ".create(",
        ".request(",
        ".send(",
    ):
        assert prohibited not in source
