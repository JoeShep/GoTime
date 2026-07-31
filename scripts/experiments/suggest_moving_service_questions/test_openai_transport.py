"""Offline-only tests for the capability-specific OpenAI transport."""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import httpx
import openai
import pytest
from openai import APIConnectionError, APITimeoutError

SCRIPT_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = REPOSITORY_ROOT / "backend"
for import_path in (SCRIPT_ROOT, BACKEND_ROOT):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from app.moving_service_questions import (  # noqa: E402
    ExperimentFixture,
    ResponseValidationError,
    build_trusted_fixture,
    construct_request,
    validate_response,
)
from openai_transport import (  # noqa: E402
    DEFAULT_RESPONSE_SCHEMA_PATH,
    DEFAULT_RUN_CONFIGURATION_PATH,
    OPENAI_MODEL_IDENTIFIER,
    OPENAI_RUN_CONFIGURATION_DIGEST,
    OPENAI_SDK_VERSION,
    OpenAIMovingServiceEvaluationTransport,
    OpenAIPreflightGateError,
    OpenAITransportArtifactError,
    load_verified_openai_transport_artifacts,
)
from real_model_adapter import (  # noqa: E402
    RealModelMovingServiceQuestionAdapter,
    TransportErrorClassification,
    parse_untrusted_response,
)
from run_real_model_evaluation import (  # noqa: E402
    OfflineRunnerAuthorization,
    OfflineRunnerGateError,
    run_offline_evaluation,
)


def valid_storage_response() -> dict[str, object]:
    return {
        "capability": "suggest_moving_service_questions",
        "prompt_version": "moving-service-questions-prompt-v1",
        "schema_version": "moving-service-questions-schema-v1",
        "suggestions": [
            {
                "question_id": "ai-temporary_storage_need-v1",
                "question": "Might you need temporary storage before final delivery?",
                "why_it_matters": (
                    "For an interstate move handled by a household-goods mover, "
                    "a possible storage need is relevant when identifying "
                    "services to request."
                ),
                "information_it_would_clarify": "Temporary storage need",
                "affected_decision_id": "moving-service-model",
                "selected_missing_information_category": "temporary_storage_need",
                "relevant_knowledge_ids": [
                    "moving-service.temporary-storage-planning.fmcsa.v1"
                ],
                "grounding_summary": (
                    "The supplied state leaves temporary storage unknown, and "
                    "the supplied knowledge identifies it as relevant."
                ),
                "reason_not_deterministic": (
                    "The information is absent and must be confirmed by the user."
                ),
                "uncertainties": [],
                "suggested_answer_type": "boolean",
                "requires_user_confirmation": True,
            }
        ],
        "fallback_recommended": False,
        "warnings": [],
    }


def completed_response(
    content: dict[str, object] | None = None,
    *,
    cached_tokens: int = 20,
) -> SimpleNamespace:
    return SimpleNamespace(
        status="completed",
        output=[
            SimpleNamespace(
                type="message",
                content=[
                    SimpleNamespace(
                        type="output_text",
                        text=json.dumps(content or valid_storage_response()),
                    )
                ],
            )
        ],
        usage=SimpleNamespace(
            input_tokens=100,
            input_tokens_details=SimpleNamespace(cached_tokens=cached_tokens),
            output_tokens=30,
            total_tokens=130,
        ),
        model=OPENAI_MODEL_IDENTIFIER,
        _request_id="req_offline_test",
        incomplete_details=None,
    )


class FakeInputTokens:
    def __init__(self, result: object | None = None, error: Exception | None = None):
        self.result = result or SimpleNamespace(input_tokens=100)
        self.error = error
        self.calls: list[dict[str, object]] = []

    def count(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return self.result


class FakeResponses:
    def __init__(
        self,
        response: object | None = None,
        *,
        count_result: object | None = None,
        count_error: Exception | None = None,
        generation_error: Exception | None = None,
    ) -> None:
        self.input_tokens = FakeInputTokens(count_result, count_error)
        self.response = response or completed_response()
        self.generation_error = generation_error
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        if self.generation_error:
            raise self.generation_error
        return self.response


class FakeOpenAIClient:
    def __init__(self, responses: FakeResponses | None = None) -> None:
        self.responses = responses or FakeResponses()
        self.max_retries = 0


def provider_request(client: FakeOpenAIClient):
    adapter = RealModelMovingServiceQuestionAdapter(
        model_identifier=OPENAI_MODEL_IDENTIFIER,
        model_parameters={"temperature": 0},
        transport=OpenAIMovingServiceEvaluationTransport(client=client),
        prompt_artifact_path=(
            REPOSITORY_ROOT
            / "docs/experiments/suggest-moving-service-questions/v1/"
            "real-model-prompt.toml"
        ),
    )
    request = construct_request(
        build_trusted_fixture(ExperimentFixture.STORAGE_UNKNOWN)
    )
    return adapter, request, adapter.prepare_request(request)


def test_pinned_sdk_and_frozen_transport_artifacts_are_accepted() -> None:
    assert openai.__version__ == OPENAI_SDK_VERSION == "2.45.0"
    artifacts = load_verified_openai_transport_artifacts()

    assert artifacts.preflight_timeout_seconds == 5
    assert artifacts.generation_timeout_seconds == 12
    assert artifacts.response_schema["additionalProperties"] is False


def test_client_with_retries_is_rejected() -> None:
    client = FakeOpenAIClient()
    client.max_retries = 2

    with pytest.raises(OpenAITransportArtifactError, match="retries"):
        OpenAIMovingServiceEvaluationTransport(client=client)


def test_transport_sends_exact_count_and_generation_payloads() -> None:
    client = FakeOpenAIClient()
    adapter, request, prepared = provider_request(client)

    transport = OpenAIMovingServiceEvaluationTransport(client=client)
    preflight = transport.preflight(prepared)
    result = transport.generate(prepared, preflight)
    validated = validate_response(
        request,
        parse_untrusted_response(result.response_content),
    )

    assert len(validated.suggestions) == 1
    assert len(client.responses.input_tokens.calls) == 1
    assert len(client.responses.calls) == 1
    count_payload = client.responses.input_tokens.calls[0]
    generation_payload = client.responses.calls[0]
    for field in ("model", "instructions", "input", "text", "truncation"):
        assert count_payload[field] == generation_payload[field]
    assert count_payload["timeout"] == 5
    assert set(count_payload) == {
        "model",
        "instructions",
        "input",
        "text",
        "truncation",
        "timeout",
    }
    assert generation_payload["max_output_tokens"] == 500
    assert generation_payload["temperature"] == 0
    assert generation_payload["store"] is False
    assert generation_payload["background"] is False
    assert generation_payload["stream"] is False
    assert generation_payload["timeout"] == 12
    assert "tools" not in generation_payload
    assert "prompt_cache_key" not in generation_payload
    assert generation_payload["text"]["format"]["strict"] is True


def test_preflight_is_independently_invocable_without_generation() -> None:
    client = FakeOpenAIClient()
    _, _, prepared = provider_request(client)
    transport = OpenAIMovingServiceEvaluationTransport(client=client)

    preflight = transport.preflight(prepared)

    assert not hasattr(transport, "send")
    assert preflight.succeeded is True
    assert preflight.input_tokens == 100
    assert len(client.responses.input_tokens.calls) == 1
    assert client.responses.calls == []


def test_generation_rejects_missing_mismatched_and_consumed_preflight() -> None:
    client = FakeOpenAIClient()
    _, _, prepared = provider_request(client)
    transport = OpenAIMovingServiceEvaluationTransport(client=client)
    preflight = transport.preflight(prepared)
    mismatched = replace(
        prepared,
        deterministic_request_json=prepared.deterministic_request_json + " ",
    )

    with pytest.raises(OpenAIPreflightGateError, match="does not match"):
        transport.generate(mismatched, preflight)
    assert client.responses.calls == []

    result = transport.generate(prepared, preflight)
    assert result.finish_status == "completed"
    assert len(client.responses.calls) == 1

    with pytest.raises(OpenAIPreflightGateError, match="already been consumed"):
        transport.generate(prepared, preflight)
    assert len(client.responses.calls) == 1


def test_generation_rejects_failed_preflight_evidence() -> None:
    client = FakeOpenAIClient(
        FakeResponses(
            count_error=APITimeoutError(
                httpx.Request("POST", "https://offline.invalid")
            )
        )
    )
    _, _, prepared = provider_request(client)
    transport = OpenAIMovingServiceEvaluationTransport(client=client)

    preflight = transport.preflight(prepared)
    assert preflight.succeeded is False
    with pytest.raises(OpenAIPreflightGateError, match="Successful"):
        transport.generate(prepared, preflight)
    assert client.responses.calls == []


def test_usage_cache_identity_and_cost_are_extracted() -> None:
    client = FakeOpenAIClient()
    _, _, prepared = provider_request(client)

    transport = OpenAIMovingServiceEvaluationTransport(client=client)
    result = transport.generate(prepared, transport.preflight(prepared))

    assert result.input_tokens == 100
    assert result.cached_input_tokens == 20
    assert result.uncached_input_tokens == 80
    assert result.output_tokens == 30
    assert result.cache_status == "hit"
    assert result.provider_name == "OpenAI"
    assert result.provider_model_identifier == OPENAI_MODEL_IDENTIFIER
    assert result.provider_request_id == "req_offline_test"
    assert result.finish_status == "completed"
    assert result.refusal_status == "not_refused"
    assert result.estimated_cost == "$0.00008200"
    assert result.preflight_duration_ms >= 0
    assert result.generation_duration_ms >= 0


def test_missing_cache_detail_is_not_inferred() -> None:
    response = completed_response()
    response.usage.input_tokens_details = None
    client = FakeOpenAIClient(FakeResponses(response=response))
    _, _, prepared = provider_request(client)

    transport = OpenAIMovingServiceEvaluationTransport(client=client)
    result = transport.generate(prepared, transport.preflight(prepared))

    assert result.cache_status == "not_available"
    assert result.cached_input_tokens == 0
    assert result.uncached_input_tokens == 100
    assert result.estimated_cost == "$0.00008800"


def test_modified_frozen_artifact_is_rejected_before_fake_sdk_call(
    tmp_path: Path,
) -> None:
    modified = tmp_path / "run.toml"
    modified.write_bytes(DEFAULT_RUN_CONFIGURATION_PATH.read_bytes() + b"\n")
    client = FakeOpenAIClient()
    _, _, prepared = provider_request(client)
    transport = OpenAIMovingServiceEvaluationTransport(
        client=client,
        run_configuration_path=modified,
    )

    with pytest.raises(OpenAITransportArtifactError, match="digest"):
        transport.preflight(prepared)

    assert client.responses.input_tokens.calls == []
    assert client.responses.calls == []


def test_runtime_schema_drift_is_rejected_before_fake_sdk_call() -> None:
    client = FakeOpenAIClient()
    _, _, prepared = provider_request(client)
    drifted = prepared.response_json_schema | {"title": "Still removed"}
    drifted["properties"] = dict(drifted["properties"])
    del drifted["properties"]["capability"]
    prepared = prepared.__class__(
        **{**prepared.__dict__, "response_json_schema": drifted}
    )

    with pytest.raises(OpenAITransportArtifactError, match="schema drifted"):
        OpenAIMovingServiceEvaluationTransport(client=client).preflight(prepared)

    assert client.responses.input_tokens.calls == []


def test_oversized_exact_preflight_blocks_generation() -> None:
    responses = FakeResponses(
        count_result=SimpleNamespace(input_tokens=3001),
    )
    client = FakeOpenAIClient(responses)
    _, _, prepared = provider_request(client)

    with pytest.raises(OpenAIPreflightGateError, match="token count"):
        OpenAIMovingServiceEvaluationTransport(client=client).preflight(prepared)

    assert len(responses.input_tokens.calls) == 1
    assert responses.calls == []


@pytest.mark.parametrize(
    ("phase", "error", "expected"),
    (
        (
            "preflight",
            APITimeoutError(httpx.Request("POST", "https://offline.invalid")),
            TransportErrorClassification.TIMEOUT,
        ),
        (
            "generation",
            APIConnectionError(
                request=httpx.Request("POST", "https://offline.invalid")
            ),
            TransportErrorClassification.UNAVAILABLE,
        ),
    ),
)
def test_bounded_sdk_errors_are_translated_without_retry(
    phase: str,
    error: Exception,
    expected: TransportErrorClassification,
) -> None:
    responses = FakeResponses(
        count_error=error if phase == "preflight" else None,
        generation_error=error if phase == "generation" else None,
    )
    client = FakeOpenAIClient(responses)
    _, _, prepared = provider_request(client)

    transport = OpenAIMovingServiceEvaluationTransport(client=client)
    preflight = transport.preflight(prepared)
    if phase == "preflight":
        assert preflight.error_classification is expected
    else:
        result = transport.generate(prepared, preflight)
        assert result.error_classification is expected
        assert result.failure_phase == phase
    assert len(responses.input_tokens.calls) == 1
    assert len(responses.calls) == (1 if phase == "generation" else 0)


def test_unexpected_sdk_error_remains_visible() -> None:
    responses = FakeResponses(generation_error=RuntimeError("offline bug"))
    client = FakeOpenAIClient(responses)
    _, _, prepared = provider_request(client)

    with pytest.raises(RuntimeError, match="offline bug"):
        transport = OpenAIMovingServiceEvaluationTransport(client=client)
        transport.generate(prepared, transport.preflight(prepared))

    assert len(responses.input_tokens.calls) == 1
    assert len(responses.calls) == 1


@pytest.mark.parametrize(
    "response",
    (
        SimpleNamespace(
            status="incomplete",
            incomplete_details=SimpleNamespace(reason="max_output_tokens"),
            output=[],
        ),
        SimpleNamespace(
            status="completed",
            incomplete_details=None,
            output=[
                SimpleNamespace(
                    content=[SimpleNamespace(type="refusal", refusal="no")]
                )
            ],
        ),
        SimpleNamespace(status="completed", incomplete_details=None, output=[]),
    ),
)
def test_incomplete_refusal_and_missing_text_are_rejected(response: object) -> None:
    client = FakeOpenAIClient(FakeResponses(response=response))
    _, _, prepared = provider_request(client)

    with pytest.raises(ResponseValidationError):
        transport = OpenAIMovingServiceEvaluationTransport(client=client)
        transport.generate(prepared, transport.preflight(prepared))


def test_runner_remains_fake_only_and_transport_reads_no_credentials() -> None:
    transport_source = (SCRIPT_ROOT / "openai_transport.py").read_text().lower()
    runner_source = (SCRIPT_ROOT / "run_real_model_evaluation.py").read_text()

    for prohibited in ("getenv", "environ", "openai(", "api_key"):
        assert prohibited not in transport_source
    assert "OpenAIMovingServiceEvaluationTransport" not in runner_source
    assert "type(adapter.transport) is not OfflineFakeMovingServiceTransport" in (
        runner_source
    )


def test_runner_rejects_openai_transport_before_any_sdk_call(tmp_path: Path) -> None:
    client = FakeOpenAIClient()
    adapter, _, _ = provider_request(client)

    with pytest.raises(OfflineRunnerGateError, match="offline fake transport"):
        run_offline_evaluation(
            fixture_id="storage_unknown",
            run_series_id="offline-openai-rejected",
            run_sequence=1,
            adapter=adapter,
            authorization=OfflineRunnerAuthorization(
                adapter_implementation_authorized=True,
                real_model_execution_authorized=False,
            ),
            output_root=tmp_path,
            allow_temporary_test_output=True,
        )

    assert client.responses.input_tokens.calls == []
    assert client.responses.calls == []


def test_requirement_is_exactly_pinned() -> None:
    requirement = (SCRIPT_ROOT / "requirements-openai.txt").read_text()
    lock = (SCRIPT_ROOT / "requirements-openai.lock").read_text()

    assert requirement == "openai==2.45.0\n"
    assert "# Experiment-specific resolved dependency set for Python 3.12.\n" in lock
    assert "openai==2.45.0\n" in lock
    assert hashlib.sha256(DEFAULT_RESPONSE_SCHEMA_PATH.read_bytes()).hexdigest() == (
        "9e5a3a667a1049d150734fd16669dad98cc982c2dc7a9a18f3e0b8cb3e891afb"
    )
    assert OPENAI_RUN_CONFIGURATION_DIGEST == (
        "e665e04b56d8aeaa01f4c9df2fd2f5f4eed37150802fdba869cba54d1e5bc782"
    )
