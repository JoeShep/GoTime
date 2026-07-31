"""Offline end-to-end tests for the closed OpenAI control-path harness."""

from __future__ import annotations

import json
import sys
from decimal import Decimal
from pathlib import Path

import pytest

SCRIPT_ROOT = Path(__file__).resolve().parent
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from run_openai_control_path_dry_run import (  # noqa: E402
    OFFLINE_SYNTHETIC_CREDENTIAL,
    OfflineControlPathError,
    OfflineFakeHttpClientConstructor,
    OfflineFakeOpenAIClientConstructor,
    OfflineOpenAIScenario,
    OfflineSyntheticEnvironment,
    run_offline_openai_control_path_series,
)


def storage_response() -> dict[str, object]:
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


def complete_response() -> dict[str, object]:
    return {
        "capability": "suggest_moving_service_questions",
        "prompt_version": "moving-service-questions-prompt-v1",
        "schema_version": "moving-service-questions-schema-v1",
        "suggestions": [],
        "fallback_recommended": False,
        "warnings": [],
    }


def run_series(
    tmp_path: Path,
    scenarios: tuple[OfflineOpenAIScenario, ...],
    *,
    fixture_ids: tuple[str, ...] = ("storage_unknown", "complete"),
):
    environment = OfflineSyntheticEnvironment()
    client_constructor = OfflineFakeOpenAIClientConstructor(scenarios)
    http_constructor = OfflineFakeHttpClientConstructor()
    result = run_offline_openai_control_path_series(
        fixture_ids=fixture_ids,
        run_series_id="offline-openai-control-path",
        first_sequence=1,
        environment=environment,
        client_constructor=client_constructor,
        http_client_constructor=http_constructor,
        output_root=tmp_path,
        allow_temporary_test_output=True,
    )
    return result, client_constructor, http_constructor


def test_complete_closed_control_path_and_budget_accounting(tmp_path: Path) -> None:
    result, client_constructor, http_constructor = run_series(
        tmp_path,
        (
            OfflineOpenAIScenario(
                storage_response(),
                cached_input_tokens=20,
            ),
            OfflineOpenAIScenario(
                complete_response(),
                cached_input_tokens=20,
            ),
        ),
    )

    assert result.stopped is False
    assert result.cumulative_cost == Decimal("0.00016400")
    assert len(result.records) == 2
    assert len(client_constructor.calls) == 2
    assert all(client.closed for client in client_constructor.clients)
    assert all(client.closed for client in http_constructor.clients)
    for record in result.records:
        assert record.repository_authorization_closed is True
        assert record.credential_access_authorized is False
        assert record.token_preflight_authorized is False
        assert record.ai_generation_authorized is False
        assert record.formal_evaluation_authorized is False
        assert record.credential_access_simulated is True
        assert record.client_construction_simulated is True
        assert record.preflight_succeeded is True
        assert record.generation_succeeded is True
        assert record.response_schema_valid is True
        assert record.estimated_cost == "$0.00008200"
        assert record.input_tokens == 100
        assert record.cached_input_tokens == 20
        assert record.uncached_input_tokens == 80
        assert record.output_tokens == 30


def test_preflight_failure_writes_record_and_stops_series(tmp_path: Path) -> None:
    result, client_constructor, _ = run_series(
        tmp_path,
        (
            OfflineOpenAIScenario(storage_response(), exact_input_tokens=3_001),
            OfflineOpenAIScenario(complete_response()),
        ),
    )

    assert result.stopped is True
    assert result.stop_reason == "preflight_gate_rejected"
    assert len(result.records) == 1
    assert len(client_constructor.calls) == 1
    record = result.records[0]
    assert record.preflight_attempted is True
    assert record.preflight_succeeded is False
    assert record.generation_attempted is False
    assert record.generation_succeeded is False
    assert record.estimated_cost == "$0.00000000"
    assert record.series_stopped is True


def test_invalid_response_writes_record_and_stops_series(tmp_path: Path) -> None:
    invalid = storage_response()
    invalid["extra"] = "not allowed"
    result, client_constructor, _ = run_series(
        tmp_path,
        (
            OfflineOpenAIScenario(invalid),
            OfflineOpenAIScenario(complete_response()),
        ),
    )

    assert result.stopped is True
    assert result.stop_reason == "invalid_ai_response"
    assert len(client_constructor.calls) == 1
    record = result.records[0]
    assert record.preflight_succeeded is True
    assert record.generation_attempted is True
    assert record.generation_succeeded is False
    assert record.response_schema_valid is False


def test_records_are_bounded_and_exclusive(tmp_path: Path) -> None:
    result, _, _ = run_series(
        tmp_path,
        (
            OfflineOpenAIScenario(storage_response()),
            OfflineOpenAIScenario(complete_response()),
        ),
    )
    serialized = "\n".join(path.read_text() for path in result.record_paths).lower()
    for prohibited in (
        OFFLINE_SYNTHETIC_CREDENTIAL,
        "api_key",
        "authorization_header",
        "system_instructions",
        "deterministic_request_json",
        "trusted_state",
        "full_response",
    ):
        assert prohibited.lower() not in serialized

    with pytest.raises(FileExistsError):
        run_series(
            tmp_path,
            (
                OfflineOpenAIScenario(storage_response()),
                OfflineOpenAIScenario(complete_response()),
            ),
        )


def test_arbitrary_environment_and_fixture_order_are_rejected(tmp_path: Path) -> None:
    constructor = OfflineFakeOpenAIClientConstructor(
        (OfflineOpenAIScenario(storage_response()),)
    )
    http_constructor = OfflineFakeHttpClientConstructor()
    with pytest.raises(OfflineControlPathError, match="synthetic environment"):
        run_offline_openai_control_path_series(
            fixture_ids=("storage_unknown",),
            run_series_id="offline-openai-control-path",
            first_sequence=1,
            environment={"key": "value"},  # type: ignore[arg-type]
            client_constructor=constructor,
            http_client_constructor=http_constructor,
            output_root=tmp_path,
            allow_temporary_test_output=True,
        )
    with pytest.raises(OfflineControlPathError, match="frozen order"):
        run_offline_openai_control_path_series(
            fixture_ids=("complete",),
            run_series_id="offline-openai-control-path",
            first_sequence=1,
            environment=OfflineSyntheticEnvironment(),
            client_constructor=constructor,
            http_client_constructor=http_constructor,
            output_root=tmp_path,
            allow_temporary_test_output=True,
        )


def test_existing_runner_remains_incapable_of_openai_reachability() -> None:
    runner_source = (SCRIPT_ROOT / "run_real_model_evaluation.py").read_text()

    assert "run_openai_control_path_dry_run" not in runner_source
    assert "openai_client_factory" not in runner_source
    assert "OpenAIMovingServiceEvaluationTransport" not in runner_source
    assert "type(adapter.transport) is not OfflineFakeMovingServiceTransport" in (
        runner_source
    )
