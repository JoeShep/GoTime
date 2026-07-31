"""Offline tests for the moving-service real-model adapter scaffold."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

import pytest

SCRIPT_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = REPOSITORY_ROOT / "backend"
for path in (SCRIPT_ROOT, BACKEND_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from app.moving_service_questions import (  # noqa: E402
    CAPABILITY,
    KNOWLEDGE_VERSION,
    PROMPT_VERSION,
    SCHEMA_VERSION,
    AnswerType,
    ExperimentFixture,
    MissingInformationCategory,
    MissingInformationItem,
    ResponseValidationError,
    build_trusted_fixture,
    construct_request,
    validate_response,
)
from real_model_adapter import (  # noqa: E402
    DEFAULT_TIMEOUT_SECONDS,
    FORMAL_RETRY_COUNT,
    FROZEN_PROMPT_DIGEST,
    OfflineFakeMovingServiceTransport,
    PromptArtifactError,
    RealModelMovingServiceQuestionAdapter,
    TransportErrorClassification,
    MovingServiceTransportResult,
)
from run_real_model_evaluation import (  # noqa: E402
    DEFAULT_PROMPT_PATH,
    OFFLINE_MODEL_IDENTIFIER,
    OfflineRunnerAuthorization,
    OfflineRunnerGateError,
    run_offline_evaluation,
)


def storage_request():
    return construct_request(
        build_trusted_fixture(ExperimentFixture.STORAGE_UNKNOWN)
    )


def complete_request():
    return construct_request(build_trusted_fixture(ExperimentFixture.COMPLETE))


def valid_storage_response() -> dict[str, object]:
    return {
        "capability": CAPABILITY,
        "prompt_version": PROMPT_VERSION,
        "schema_version": SCHEMA_VERSION,
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
                    "the supplied knowledge identifies it as relevant to "
                    "services requested from a household-goods mover."
                ),
                "reason_not_deterministic": (
                    "The information is not present in trusted state and must "
                    "be confirmed by the user."
                ),
                "uncertainties": [],
                "suggested_answer_type": "boolean",
                "requires_user_confirmation": True,
            }
        ],
        "fallback_recommended": False,
        "warnings": [],
    }


def valid_complete_response() -> dict[str, object]:
    return {
        "capability": CAPABILITY,
        "prompt_version": PROMPT_VERSION,
        "schema_version": SCHEMA_VERSION,
        "suggestions": [],
        "fallback_recommended": False,
        "warnings": [],
    }


def fake_transport(
    response: dict[str, object] | str | None,
    *,
    error: TransportErrorClassification | None = None,
) -> OfflineFakeMovingServiceTransport:
    return OfflineFakeMovingServiceTransport(
        MovingServiceTransportResult(
            response_content=response,
            input_tokens=123,
            output_tokens=45,
            duration_ms=1.5,
            cache_status="disabled",
            error_classification=error,
        )
    )


def adapter_for(
    transport: OfflineFakeMovingServiceTransport,
    *,
    prompt_path: Path = DEFAULT_PROMPT_PATH,
    digest: str = FROZEN_PROMPT_DIGEST,
) -> RealModelMovingServiceQuestionAdapter:
    return RealModelMovingServiceQuestionAdapter(
        model_identifier=OFFLINE_MODEL_IDENTIFIER,
        model_parameters={},
        transport=transport,
        prompt_artifact_path=prompt_path,
        expected_prompt_digest=digest,
    )


def write_modified_prompt(
    tmp_path: Path,
    old: str,
    new: str,
) -> tuple[Path, str]:
    content = DEFAULT_PROMPT_PATH.read_text()
    assert old in content
    modified = content.replace(old, new, 1)
    path = tmp_path / "prompt.toml"
    path.write_text(modified)
    return path, hashlib.sha256(path.read_bytes()).hexdigest()


def run_fake(
    tmp_path: Path,
    response: dict[str, object] | str | None,
    *,
    fixture_id: str = "storage_unknown",
    run_sequence: int = 1,
    error: TransportErrorClassification | None = None,
):
    transport = fake_transport(response, error=error)
    result = run_offline_evaluation(
        fixture_id=fixture_id,
        run_series_id="offline-test-series",
        run_sequence=run_sequence,
        adapter=adapter_for(transport),
        authorization=OfflineRunnerAuthorization(
            adapter_implementation_authorized=True
        ),
        output_root=tmp_path,
        allow_temporary_test_output=True,
    )
    return result, transport


def test_frozen_prompt_digest_is_accepted_and_schema_is_supplied() -> None:
    transport = fake_transport(valid_storage_response())
    adapter = adapter_for(transport)

    raw_response = adapter.suggest(storage_request())

    assert raw_response == valid_storage_response()
    assert transport.call_count == 1
    provider_request = transport.requests[0]
    assert provider_request.response_json_schema["title"] == (
        "MovingServiceQuestionResponse"
    )
    assert provider_request.maximum_output_tokens == 500
    assert provider_request.timeout_seconds == DEFAULT_TIMEOUT_SECONDS == 12.0
    assert provider_request.retry_count == FORMAL_RETRY_COUNT == 0


def test_modified_prompt_bytes_are_rejected_before_transport(tmp_path: Path) -> None:
    path = tmp_path / "prompt.toml"
    path.write_bytes(DEFAULT_PROMPT_PATH.read_bytes() + b"\n")
    transport = fake_transport(valid_storage_response())

    with pytest.raises(PromptArtifactError, match="digest"):
        adapter_for(transport, prompt_path=path).suggest(storage_request())

    assert transport.call_count == 0


@pytest.mark.parametrize(
    ("old", "new"),
    (
        (
            'prompt_version = "moving-service-questions-prompt-v1"',
            'prompt_version = "wrong-prompt-version"',
        ),
        (
            'compatible_request_schema_version = "moving-service-questions-schema-v1"',
            'compatible_request_schema_version = "wrong-schema-version"',
        ),
        (
            'compatible_knowledge_fixture_version = "moving-service-storage-fixture-v2"',
            'compatible_knowledge_fixture_version = "wrong-knowledge-version"',
        ),
        ("reviewed = true", "reviewed = false"),
        (
            "frozen_for_adapter_implementation = true",
            "frozen_for_adapter_implementation = false",
        ),
    ),
)
def test_incompatible_prompt_metadata_is_rejected_before_transport(
    tmp_path: Path,
    old: str,
    new: str,
) -> None:
    path, digest = write_modified_prompt(tmp_path, old, new)
    transport = fake_transport(valid_storage_response())

    with pytest.raises(PromptArtifactError):
        adapter_for(transport, prompt_path=path, digest=digest).suggest(
            storage_request()
        )

    assert transport.call_count == 0


def test_real_model_execution_remains_unauthorized(tmp_path: Path) -> None:
    transport = fake_transport(valid_storage_response())

    with pytest.raises(OfflineRunnerGateError, match="unauthorized"):
        run_offline_evaluation(
            fixture_id="storage_unknown",
            run_series_id="offline-test-series",
            run_sequence=1,
            adapter=adapter_for(transport),
            authorization=OfflineRunnerAuthorization(
                adapter_implementation_authorized=True,
                real_model_execution_authorized=True,
            ),
            output_root=tmp_path,
            allow_temporary_test_output=True,
        )

    assert transport.call_count == 0


def test_transport_not_called_without_offline_authorization(tmp_path: Path) -> None:
    transport = fake_transport(valid_storage_response())

    with pytest.raises(OfflineRunnerGateError, match="not authorized"):
        run_offline_evaluation(
            fixture_id="storage_unknown",
            run_series_id="offline-test-series",
            run_sequence=1,
            adapter=adapter_for(transport),
            authorization=OfflineRunnerAuthorization(
                adapter_implementation_authorized=False
            ),
            output_root=tmp_path,
            allow_temporary_test_output=True,
        )

    assert transport.call_count == 0


def test_deterministic_request_serialization_matches_frozen_order() -> None:
    transport = fake_transport(valid_storage_response())
    provider_request = adapter_for(transport).prepare_request(storage_request())
    decoded = json.loads(provider_request.deterministic_request_json)

    assert list(decoded) == list(type(storage_request()).model_fields)
    assert list(decoded) == [
        "capability",
        "trusted_state",
        "missing_information",
        "deterministic_context",
        "curated_knowledge_items",
        "requested_output",
        "prompt_version",
        "schema_version",
        "knowledge_fixture_version",
        "maximum_questions",
        "maximum_output_tokens",
    ]
    assert provider_request.deterministic_request_json == (
        storage_request().model_dump_json(
            exclude_none=False,
            exclude_defaults=False,
        )
    )
    serialized = provider_request.deterministic_request_json.lower()
    assert "storage_unknown" not in serialized
    assert "fixture_id" not in serialized
    assert not serialized.startswith("request:")


def test_valid_storage_response_passes_runtime_validation(tmp_path: Path) -> None:
    result, transport = run_fake(tmp_path, valid_storage_response())

    assert result.record.schema_valid is True
    assert result.record.fallback_used is False
    assert result.record.referenced_knowledge_ids == (
        "moving-service.temporary-storage-planning.fmcsa.v1",
    )
    assert transport.call_count == 1


def test_empty_no_gap_response_passes_runtime_validation(tmp_path: Path) -> None:
    result, _ = run_fake(
        tmp_path,
        valid_complete_response(),
        fixture_id="complete",
    )

    assert result.record.schema_valid is True
    assert result.record.fallback_used is False
    assert result.record.normalized_question_text is None


def test_malformed_json_is_rejected_without_repair_and_runner_records_fallback(
    tmp_path: Path,
) -> None:
    result, _ = run_fake(tmp_path, '{"capability":')

    assert result.record.schema_valid is False
    assert result.record.validation_error_code == "invalid_adapter_response"
    assert result.record.fallback_used is True
    assert result.record.fallback_reason == "invalid_adapter_response"


@pytest.mark.parametrize(
    "mutate",
    (
        lambda response: response.update(extra_field=True),
        lambda response: response["suggestions"][0].update(  # type: ignore[index,union-attr]
            relevant_knowledge_ids=["unknown"]
        ),
        lambda response: response["suggestions"][0].update(  # type: ignore[index,union-attr]
            selected_missing_information_category="willing_to_drive_rental_truck"
        ),
        lambda response: response["suggestions"][0].update(  # type: ignore[index,union-attr]
            requires_user_confirmation=False
        ),
    ),
)
def test_invalid_response_is_rejected_and_runner_owns_fallback(
    tmp_path: Path,
    mutate,
) -> None:
    response = copy.deepcopy(valid_storage_response())
    mutate(response)

    result, _ = run_fake(tmp_path, response)

    assert result.record.schema_valid is False
    assert result.record.fallback_used is True
    assert result.record.fallback_reason == "invalid_adapter_response"


def test_duplicate_question_id_and_category_are_rejected() -> None:
    response = copy.deepcopy(valid_storage_response())
    response["suggestions"].append(copy.deepcopy(response["suggestions"][0]))  # type: ignore[union-attr]

    with pytest.raises(ResponseValidationError, match="Question IDs"):
        validate_response(storage_request(), response)

    response = copy.deepcopy(valid_storage_response())
    duplicate = copy.deepcopy(response["suggestions"][0])  # type: ignore[index]
    duplicate["question_id"] = "ai-temporary_storage_need-second-v1"
    duplicate["question"] = "Could temporary storage be needed?"
    response["suggestions"].append(duplicate)  # type: ignore[union-attr]
    with pytest.raises(ResponseValidationError, match="unique missing"):
        validate_response(storage_request(), response)


def test_duplicate_normalized_question_is_rejected() -> None:
    request = storage_request().model_copy(
        update={
            "missing_information": (
                *storage_request().missing_information,
                MissingInformationItem(
                    category_id=MissingInformationCategory.SPECIALTY_ITEM_NEEDS,
                    state_field=MissingInformationCategory.SPECIALTY_ITEM_NEEDS,
                    answer_type=AnswerType.BOOLEAN,
                    reason_missing="Specialty-item needs are missing.",
                ),
            )
        }
    )
    response = copy.deepcopy(valid_storage_response())
    duplicate = copy.deepcopy(response["suggestions"][0])  # type: ignore[index]
    duplicate["question_id"] = "ai-specialty_item_needs-v1"
    duplicate["selected_missing_information_category"] = "specialty_item_needs"
    duplicate["question"] = " MIGHT you need temporary storage before final delivery "
    response["suggestions"].append(duplicate)  # type: ignore[union-attr]

    with pytest.raises(ResponseValidationError, match="text must be unique"):
        validate_response(request, response)


@pytest.mark.parametrize(
    ("error", "reason"),
    (
        (TransportErrorClassification.UNAVAILABLE, "adapter_unavailable"),
        (TransportErrorClassification.TIMEOUT, "adapter_timeout"),
    ),
)
def test_bounded_transport_failures_record_deterministic_fallback(
    tmp_path: Path,
    error: TransportErrorClassification,
    reason: str,
) -> None:
    result, _ = run_fake(tmp_path, None, error=error)

    assert result.record.schema_valid is None
    assert result.record.fallback_used is True
    assert result.record.fallback_reason == reason


@pytest.mark.parametrize(
    "fixture_id",
    (
        "validation_multiple_gaps",
        "invalid_ai_response",
        "adapter_unavailable",
        "unknown",
    ),
)
def test_non_model_quality_fixtures_are_rejected_before_transport(
    tmp_path: Path,
    fixture_id: str,
) -> None:
    transport = fake_transport(valid_storage_response())

    with pytest.raises(OfflineRunnerGateError):
        run_offline_evaluation(
            fixture_id=fixture_id,
            run_series_id="offline-test-series",
            run_sequence=1,
            adapter=adapter_for(transport),
            authorization=OfflineRunnerAuthorization(
                adapter_implementation_authorized=True
            ),
            output_root=tmp_path,
            allow_temporary_test_output=True,
        )

    assert transport.call_count == 0


def test_record_is_bounded_and_existing_record_cannot_be_overwritten(
    tmp_path: Path,
) -> None:
    result, transport = run_fake(tmp_path, valid_storage_response())
    record_data = json.loads(result.record_path.read_text())
    serialized = json.dumps(record_data).lower()

    for excluded in (
        "system_instructions",
        "deterministic_request_json",
        "full_response",
        "trusted_state",
        "conversation_history",
        "credentials",
        "authorization_headers",
    ):
        assert excluded not in serialized

    with pytest.raises(FileExistsError):
        run_offline_evaluation(
            fixture_id="storage_unknown",
            run_series_id="offline-test-series",
            run_sequence=1,
            adapter=adapter_for(transport),
            authorization=OfflineRunnerAuthorization(
                adapter_implementation_authorized=True
            ),
            output_root=tmp_path,
            allow_temporary_test_output=True,
        )
    assert transport.call_count == 1


def test_adapter_contains_no_fallback_selection() -> None:
    source = (SCRIPT_ROOT / "real_model_adapter.py").read_text()

    assert "select_fallback" not in source


def test_scaffold_contains_no_network_or_credential_implementation() -> None:
    source = "\n".join(
        (SCRIPT_ROOT / filename).read_text()
        for filename in (
            "real_model_adapter.py",
            "run_real_model_evaluation.py",
        )
    ).lower()

    for prohibited in (
        "import requests",
        "import httpx",
        "import urllib",
        "import socket",
        "http://",
        "https://",
        "api_key",
        "getenv",
        "environ",
    ):
        assert prohibited not in source


def test_backend_and_frontend_do_not_reference_offline_scaffold() -> None:
    for root in (REPOSITORY_ROOT / "backend", REPOSITORY_ROOT / "frontend"):
        for path in root.rglob("*"):
            if not path.is_file() or "node_modules" in path.parts:
                continue
            if path.suffix not in {".py", ".ts", ".tsx"}:
                continue
            source = path.read_text(errors="ignore")
            assert "real_model_adapter" not in source
            assert "run_real_model_evaluation" not in source
