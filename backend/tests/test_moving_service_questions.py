import copy
import json

import pytest

from app.moving_service_questions import (
    CAPABILITY,
    KNOWLEDGE_VERSION,
    MAXIMUM_INPUT_TOKENS,
    PROMPT_VERSION,
    SCHEMA_VERSION,
    STORAGE_KNOWLEDGE,
    ExperimentFixture,
    FakeMovingServiceQuestionSuggestionAdapter,
    InformationStatus,
    AnswerType,
    MissingInformationItem,
    MissingInformationCategory,
    ResponseValidationError,
    SuggestionSource,
    build_trusted_fixture,
    construct_request,
    run_experiment,
    select_fallback,
    validate_response,
)


APPROVED_REQUEST_FIELDS = {
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
}

APPROVED_TRUSTED_STATE_FIELDS = {
    "goal_summary",
    "move_type",
    "origin_region",
    "destination_region",
    "target_move_window",
    "household_size",
    "temporary_storage_need",
    "packing_preference",
    "willing_to_drive_rental_truck",
    "cost_vs_convenience_preference",
    "specialty_item_needs",
    "known_constraints",
}


def storage_request():
    return construct_request(
        build_trusted_fixture(ExperimentFixture.STORAGE_UNKNOWN)
    )


def valid_response():
    request = storage_request()
    return FakeMovingServiceQuestionSuggestionAdapter(
        ExperimentFixture.STORAGE_UNKNOWN
    ).suggest(request)


def assert_response_rejected(mutate) -> None:
    request = storage_request()
    response = copy.deepcopy(valid_response())
    mutate(response)

    with pytest.raises(ResponseValidationError):
        validate_response(request, response)


def test_request_construction_is_bounded_to_approved_fields() -> None:
    request = storage_request()
    serialized = request.model_dump()

    assert set(serialized) == APPROVED_REQUEST_FIELDS
    assert set(serialized["trusted_state"]) == APPROVED_TRUSTED_STATE_FIELDS
    assert serialized["capability"] == CAPABILITY
    assert serialized["prompt_version"] == PROMPT_VERSION
    assert serialized["schema_version"] == SCHEMA_VERSION
    assert serialized["knowledge_fixture_version"] == KNOWLEDGE_VERSION
    assert serialized["maximum_questions"] == 3
    assert serialized["maximum_output_tokens"] == 500
    assert "current_state" not in serialized["trusted_state"]
    assert "assumptions" not in serialized["trusted_state"]
    assert "conversation" not in str(serialized).lower()
    assert "application_logs" not in str(serialized).lower()


def test_storage_request_uses_reviewed_knowledge_within_input_budget() -> None:
    request = storage_request()
    serialized = json.dumps(
        request.model_dump(mode="json"), separators=(",", ":")
    ).encode("utf-8")

    assert len(serialized) < MAXIMUM_INPUT_TOKENS
    assert request.curated_knowledge_items == (STORAGE_KNOWLEDGE,)
    assert STORAGE_KNOWLEDGE.knowledge_id == (
        "moving-service.temporary-storage-planning.fmcsa.v1"
    )
    assert STORAGE_KNOWLEDGE.service_model == "interstate_household_goods_mover"
    assert "fmcsa.dot.gov" in STORAGE_KNOWLEDGE.source
    assert "fixture" not in STORAGE_KNOWLEDGE.source.lower()
    assert STORAGE_KNOWLEDGE.version == "2.0.0"


def test_request_maps_only_the_storage_gap_to_an_allowlisted_boolean_field() -> None:
    request = storage_request()

    assert len(request.missing_information) == 1
    missing = request.missing_information[0]
    assert missing.category_id is MissingInformationCategory.TEMPORARY_STORAGE_NEED
    assert missing.state_field is MissingInformationCategory.TEMPORARY_STORAGE_NEED
    assert missing.answer_type == "boolean"
    assert missing.allowed_enum_values is None
    assert (
        request.trusted_state.willing_to_drive_rental_truck.status
        is InformationStatus.KNOWN
    )
    assert request.trusted_state.willing_to_drive_rental_truck.value is False


def test_storage_unknown_fixture_produces_a_grounded_storage_question() -> None:
    result = run_experiment(ExperimentFixture.STORAGE_UNKNOWN)

    assert result.source is SuggestionSource.FAKE_AI_ADAPTER
    assert result.suggestion is not None
    assert result.suggestion.question == (
        "Will you need temporary storage between homes?"
    )
    assert result.suggestion.answer_type == "boolean"
    assert result.suggestion.requires_user_confirmation is True
    assert result.suggestion.grounding_details == (
        "For an interstate move handled by a household-goods mover, a possible "
        "need for temporary storage before final delivery is relevant when "
        "identifying the services to request.",
    )
    assert "drive" not in result.suggestion.question.lower()


def test_complete_fixture_returns_a_valid_no_question_result() -> None:
    result = run_experiment(ExperimentFixture.COMPLETE)

    assert result.source is SuggestionSource.NONE
    assert result.suggestion is None
    assert result.no_question_reason == (
        "No supported moving-service information gap remains."
    )
    assert result.observability.schema_valid is True
    assert result.observability.fallback_used is False
    assert result.observability.suggestion_count == 0


def test_invalid_fake_response_is_rejected_completely_and_uses_fallback() -> None:
    result = run_experiment(ExperimentFixture.INVALID_AI_RESPONSE)

    assert result.source is SuggestionSource.DETERMINISTIC_FALLBACK
    assert result.suggestion is not None
    assert result.suggestion.question_id == "fallback-temporary-storage-v1"
    assert result.suggestion.question == (
        "Will you need temporary storage between homes?"
    )
    assert result.observability.schema_valid is False
    assert result.observability.fallback_used is True
    assert result.observability.fallback_reason == "invalid_adapter_response"
    assert result.observability.suggestion_count == 0


def test_unknown_knowledge_id_rejects_the_complete_response() -> None:
    assert_response_rejected(
        lambda response: response["suggestions"][0].update(  # type: ignore[index,union-attr]
            relevant_knowledge_ids=["not-supplied"]
        )
    )


def test_requires_user_confirmation_false_rejects_the_complete_response() -> None:
    assert_response_rejected(
        lambda response: response["suggestions"][0].update(  # type: ignore[index,union-attr]
            requires_user_confirmation=False
        )
    )


def test_known_category_rejects_the_complete_response() -> None:
    def target_known_category(response) -> None:
        suggestion = response["suggestions"][0]
        suggestion["selected_missing_information_category"] = (
            "willing_to_drive_rental_truck"
        )
        suggestion["suggested_answer_type"] = "boolean"

    assert_response_rejected(target_known_category)


def test_duplicate_question_id_rejects_the_complete_response() -> None:
    def duplicate(response) -> None:
        response["suggestions"].append(copy.deepcopy(response["suggestions"][0]))

    assert_response_rejected(duplicate)


def test_duplicate_category_rejects_the_complete_response() -> None:
    def duplicate(response) -> None:
        second = copy.deepcopy(response["suggestions"][0])
        second["question_id"] = "different-question-id"
        second["question"] = "Is temporary storage part of this move?"
        response["suggestions"].append(second)

    assert_response_rejected(duplicate)


def test_duplicate_normalized_question_text_rejects_the_complete_response() -> None:
    request = storage_request().model_copy(
        update={
            "missing_information": (
                *storage_request().missing_information,
                MissingInformationItem(
                    category_id=MissingInformationCategory.SPECIALTY_ITEM_NEEDS,
                    state_field=MissingInformationCategory.SPECIALTY_ITEM_NEEDS,
                    answer_type=AnswerType.BOOLEAN,
                    allowed_enum_values=None,
                    reason_missing=(
                        "Specialty-item needs have not been confirmed."
                    ),
                ),
            )
        }
    )
    response = copy.deepcopy(valid_response())
    second = copy.deepcopy(response["suggestions"][0])
    second["question_id"] = "different-question-id"
    second["selected_missing_information_category"] = "specialty_item_needs"
    second["question"] = " WILL you need temporary storage between homes "
    response["suggestions"].append(second)

    with pytest.raises(ResponseValidationError, match="text must be unique"):
        validate_response(request, response)


def test_unexpected_state_mutation_field_rejects_the_complete_response() -> None:
    assert_response_rejected(
        lambda response: response["suggestions"][0].update(  # type: ignore[index,union-attr]
            state_mutation={"temporary_storage_need": True}
        )
    )


@pytest.mark.parametrize(
    ("fixture", "reason"),
    (
        (ExperimentFixture.ADAPTER_UNAVAILABLE, "adapter_unavailable"),
        (ExperimentFixture.ADAPTER_TIMEOUT, "adapter_timeout"),
        (
            ExperimentFixture.BUDGET_UNAVAILABLE,
            "experimental_budget_unavailable",
        ),
        (ExperimentFixture.AI_DISABLED, "ai_assistance_disabled"),
    ),
)
def test_non_ai_paths_use_the_same_deterministic_fallback(
    fixture: ExperimentFixture, reason: str
) -> None:
    result = run_experiment(fixture)

    assert result.source is SuggestionSource.DETERMINISTIC_FALLBACK
    assert result.suggestion is not None
    assert result.suggestion.question_id == "fallback-temporary-storage-v1"
    assert result.observability.fallback_used is True
    assert result.observability.fallback_reason == reason
    assert result.observability.schema_valid is None


def test_fallback_uses_fixed_priority_and_returns_none_without_a_gap() -> None:
    storage = storage_request()
    complete = construct_request(build_trusted_fixture(ExperimentFixture.COMPLETE))

    assert select_fallback(storage).category_id == "temporary_storage_need"
    assert select_fallback(complete) is None


def test_suggestion_does_not_mutate_trusted_fixture_or_goal_state() -> None:
    trusted_state = build_trusted_fixture(ExperimentFixture.STORAGE_UNKNOWN)
    before = trusted_state.model_dump()

    result = run_experiment(ExperimentFixture.STORAGE_UNKNOWN)

    assert trusted_state.model_dump() == before
    assert trusted_state.temporary_storage_need.status is InformationStatus.MISSING
    assert result.suggestion is not None
    assert not hasattr(result.suggestion, "state_field")
    assert not hasattr(result.suggestion, "proposed_state_field")


def test_observability_is_bounded_and_records_zero_fake_cost() -> None:
    result = run_experiment(ExperimentFixture.STORAGE_UNKNOWN)
    metadata = result.observability.model_dump()

    assert metadata == {
        "capability": CAPABILITY,
        "prompt_version": PROMPT_VERSION,
        "schema_version": SCHEMA_VERSION,
        "fixture_id": ExperimentFixture.STORAGE_UNKNOWN,
        "adapter_identifier": "fake-moving-service-question-adapter-v1",
        "knowledge_version": KNOWLEDGE_VERSION,
        "referenced_knowledge_ids": (
            "moving-service.temporary-storage-planning.fmcsa.v1",
        ),
        "schema_valid": True,
        "fallback_used": False,
        "fallback_reason": None,
        "suggestion_count": 1,
        "duration_ms": metadata["duration_ms"],
        "estimated_cost": "$0.00",
        "user_disposition": None,
    }
    assert "trusted_state" not in metadata
    assert "prompt" not in metadata
    assert "answer" not in metadata
