import copy
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.moving_service_questions import (
    PROMPT_VERSION,
    SCHEMA_VERSION,
    STORAGE_KNOWLEDGE,
    ExperimentFixture,
    MovingServiceQuestionRequest,
    MovingServiceQuestionResponse,
    build_trusted_fixture,
    select_fallback,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT_ROOT = (
    REPOSITORY_ROOT
    / "scripts/experiments/suggest_moving_service_questions"
)
if str(EXPERIMENT_ROOT) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_ROOT))

from moving_service_questions_v2 import (  # noqa: E402
    PROSE_VIOLATION_CODE_ORDER,
    PROMPT_VERSION_V2,
    SCHEMA_VERSION_V2,
    MovingServiceQuestionRequestV2,
    MovingServiceQuestionResponseV2,
    ProseValidationError,
    collect_fallback_prose_violation_codes,
    construct_request_v2,
    select_fallback_v2,
    validate_response_v2,
    validate_v2_response_with_fallback,
)


def storage_request_v2() -> MovingServiceQuestionRequestV2:
    return construct_request_v2(
        build_trusted_fixture(ExperimentFixture.STORAGE_UNKNOWN)
    )


def valid_v2_response() -> dict[str, object]:
    return {
        "capability": "suggest_moving_service_questions",
        "prompt_version": PROMPT_VERSION_V2,
        "schema_version": SCHEMA_VERSION_V2,
        "suggestions": [
            {
                "question_id": "ai-temporary_storage_need-v2",
                "question": "Might temporary storage be needed before final delivery?",
                "why_it_matters": (
                    "A possible need for temporary storage is relevant when "
                    "identifying services to request."
                ),
                "information_it_would_clarify": (
                    "Whether temporary storage may be needed"
                ),
                "affected_decision_id": "moving-service-model",
                "selected_missing_information_category": (
                    "temporary_storage_need"
                ),
                "relevant_knowledge_ids": [STORAGE_KNOWLEDGE.knowledge_id],
                "grounding_summary": STORAGE_KNOWLEDGE.statement,
                "reason_not_deterministic": (
                    "The information is not present in trusted state and must "
                    "be confirmed by the user."
                ),
                "uncertainties": [
                    "The possible need for temporary storage is unconfirmed."
                ],
                "suggested_answer_type": "boolean",
                "requires_user_confirmation": True,
            }
        ],
        "fallback_recommended": False,
        "warnings": [],
    }


def assert_prose_codes(
    mutate,
    expected: tuple[str, ...],
) -> None:
    response = copy.deepcopy(valid_v2_response())
    mutate(response["suggestions"][0])  # type: ignore[index]
    with pytest.raises(ProseValidationError) as error:
        validate_response_v2(storage_request_v2(), response)
    assert error.value.violation_codes == expected


def test_v1_contract_literals_remain_exact() -> None:
    request_schema = MovingServiceQuestionRequest.model_json_schema()
    response_schema = MovingServiceQuestionResponse.model_json_schema()

    assert request_schema["properties"]["prompt_version"]["const"] == PROMPT_VERSION
    assert request_schema["properties"]["schema_version"]["const"] == SCHEMA_VERSION
    assert response_schema["properties"]["prompt_version"]["const"] == PROMPT_VERSION
    assert response_schema["properties"]["schema_version"]["const"] == SCHEMA_VERSION


def test_v2_contracts_preserve_fields_and_constraints_except_versions() -> None:
    request_v1 = MovingServiceQuestionRequest.model_json_schema()
    request_v2 = MovingServiceQuestionRequestV2.model_json_schema()
    response_v1 = MovingServiceQuestionResponse.model_json_schema()
    response_v2 = MovingServiceQuestionResponseV2.model_json_schema()

    assert request_v2["required"] == request_v1["required"]
    assert set(request_v2["properties"]) == set(request_v1["properties"])
    assert response_v2["required"] == response_v1["required"]
    assert set(response_v2["properties"]) == set(response_v1["properties"])
    assert request_v2["additionalProperties"] is False
    assert response_v2["additionalProperties"] is False
    assert request_v2["properties"]["prompt_version"]["const"] == PROMPT_VERSION_V2
    assert request_v2["properties"]["schema_version"]["const"] == SCHEMA_VERSION_V2
    assert response_v2["properties"]["prompt_version"]["const"] == PROMPT_VERSION_V2
    assert response_v2["properties"]["schema_version"]["const"] == SCHEMA_VERSION_V2


@pytest.mark.parametrize(
    ("request_type", "prompt_version", "schema_version"),
    (
        (MovingServiceQuestionRequestV2, PROMPT_VERSION, SCHEMA_VERSION_V2),
        (MovingServiceQuestionRequestV2, PROMPT_VERSION_V2, SCHEMA_VERSION),
    ),
)
def test_v1_and_v2_request_literals_cannot_be_mixed(
    request_type,
    prompt_version: str,
    schema_version: str,
) -> None:
    document = storage_request_v2().model_dump()
    document.update(
        prompt_version=prompt_version,
        schema_version=schema_version,
    )
    with pytest.raises(ValidationError):
        request_type.model_validate(document)


@pytest.mark.parametrize(
    ("prompt_version", "schema_version"),
    (
        (PROMPT_VERSION, SCHEMA_VERSION_V2),
        (PROMPT_VERSION_V2, SCHEMA_VERSION),
    ),
)
def test_v1_and_v2_response_literals_cannot_be_mixed(
    prompt_version: str,
    schema_version: str,
) -> None:
    response = valid_v2_response()
    response.update(
        prompt_version=prompt_version,
        schema_version=schema_version,
    )
    with pytest.raises(ValidationError):
        MovingServiceQuestionResponseV2.model_validate(response)


def test_exact_grounding_statement_and_may_be_needed_pass() -> None:
    response = validate_response_v2(storage_request_v2(), valid_v2_response())
    assert response.suggestions[0].grounding_summary == STORAGE_KNOWLEDGE.statement


@pytest.mark.parametrize(
    ("changed_grounding", "expected_codes"),
    (
        (STORAGE_KNOWLEDGE.statement[:-1], ("grounding_summary_mismatch",)),
        (
            STORAGE_KNOWLEDGE.statement.replace("mover,", "mover;"),
            ("grounding_summary_mismatch",),
        ),
        (
            STORAGE_KNOWLEDGE.statement.replace("a possible", "a  possible"),
            ("grounding_summary_mismatch",),
        ),
        (
            STORAGE_KNOWLEDGE.statement.replace("possible need", "required need"),
            (
                "storage_modality_overstatement",
                "grounding_summary_mismatch",
            ),
        ),
        (
            STORAGE_KNOWLEDGE.statement + " Additional claim.",
            ("grounding_summary_mismatch",),
        ),
    ),
)
def test_any_grounding_change_fails(
    changed_grounding: str,
    expected_codes: tuple[str, ...],
) -> None:
    assert_prose_codes(
        lambda suggestion: suggestion.update(grounding_summary=changed_grounding),
        expected_codes,
    )


@pytest.mark.parametrize("location", ("Tennessee", "Northern California"))
def test_supplied_origin_or_destination_reference_fails(location: str) -> None:
    assert_prose_codes(
        lambda suggestion: suggestion.update(
            question=f"Might temporary storage be needed in {location}?"
        ),
        ("irrelevant_location_reference",),
    )


def test_location_check_is_case_insensitive_and_absence_passes() -> None:
    assert_prose_codes(
        lambda suggestion: suggestion.update(
            why_it_matters="This matters in northern california."
        ),
        ("irrelevant_location_reference",),
    )
    validate_response_v2(storage_request_v2(), valid_v2_response())


@pytest.mark.parametrize(
    "phrase",
    ("your new home", "your home", "your house", "your property", "your residence"),
)
def test_reviewed_home_or_property_phrase_fails(phrase: str) -> None:
    assert_prose_codes(
        lambda suggestion: suggestion.update(
            information_it_would_clarify=f"Storage before delivery to {phrase}"
        ),
        ("unsupported_home_or_property_assertion",),
    )


@pytest.mark.parametrize(
    "wording",
    (
        "Whether storage will be required",
        "Temporary storage is required",
        "You must use storage",
        "You will need storage",
    ),
)
def test_storage_modality_overstatement_fails(wording: str) -> None:
    assert_prose_codes(
        lambda suggestion: suggestion.update(
            information_it_would_clarify=wording
        ),
        ("storage_modality_overstatement",),
    )


def test_required_in_confirmation_reason_does_not_fail() -> None:
    response = valid_v2_response()
    response["suggestions"][0]["reason_not_deterministic"] = (  # type: ignore[index]
        "User confirmation is required because the value is missing."
    )
    validate_response_v2(storage_request_v2(), response)


@pytest.mark.parametrize(
    "wording",
    (
        "appropriate moving services",
        "best mover",
        "suitable provider",
        "recommended service",
        "recommended service model",
    ),
)
def test_selection_oriented_combination_fails(wording: str) -> None:
    assert_prose_codes(
        lambda suggestion: suggestion.update(why_it_matters=wording),
        ("unsupported_service_selection_language",),
    )


def test_benign_unrelated_adjective_use_passes() -> None:
    response = valid_v2_response()
    response["suggestions"][0]["why_it_matters"] = (  # type: ignore[index]
        "The appropriate answer should come from the user; a possible storage "
        "need is relevant when identifying services to request."
    )
    validate_response_v2(storage_request_v2(), response)


def test_multiple_violations_are_recorded_in_stable_order() -> None:
    def mutate(suggestion) -> None:
        suggestion["question"] = (
            "Will storage be required at your new home in Northern California?"
        )
        suggestion["why_it_matters"] = "Choose appropriate moving services."
        suggestion["grounding_summary"] = "Broadened grounding."

    assert_prose_codes(mutate, PROSE_VIOLATION_CODE_ORDER)


def test_complete_response_is_rejected_before_fallback_selection() -> None:
    response = valid_v2_response()
    response["suggestions"][0]["question"] = (  # type: ignore[index]
        "Might storage be needed in Tennessee?"
    )
    result = validate_v2_response_with_fallback(storage_request_v2(), response)

    assert result.response is None
    assert result.prose_violation_codes == ("irrelevant_location_reference",)
    assert result.fallback == select_fallback_v2(storage_request_v2())


def test_reconciled_fallback_passes_user_facing_prose_checks() -> None:
    request = storage_request_v2()
    fallback = select_fallback_v2(request)
    assert fallback is not None
    assert collect_fallback_prose_violation_codes(request, fallback) == ()
    assert fallback.question == (
        "Might temporary storage be needed before final delivery?"
    )
    assert fallback.why_it_matters == STORAGE_KNOWLEDGE.statement


def test_v1_fallback_remains_historically_unchanged() -> None:
    fallback = select_fallback(storage_request_v2())
    assert fallback is not None
    assert fallback.question_id == "fallback-temporary-storage-v1"
    assert fallback.question == "Will you need temporary storage between homes?"
