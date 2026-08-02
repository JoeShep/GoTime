"""Offline-only v2 contracts and prose validation for the moving-service experiment."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Literal, Mapping

from pydantic import ValidationError

from app.moving_service_questions import (
    FALLBACK_QUESTIONS,
    MAXIMUM_RESPONSE_CHARACTERS,
    STORAGE_KNOWLEDGE,
    FallbackQuestion,
    MissingInformationCategory,
    MovingServiceQuestionRequest,
    MovingServiceQuestionResponse,
    ResponseValidationError,
    build_trusted_fixture,
    construct_request,
    normalize_question_text,
)


PROMPT_VERSION_V2 = "moving-service-questions-prompt-v2"
SCHEMA_VERSION_V2 = "moving-service-questions-schema-v2"
FALLBACK_VERSION_V2 = "moving-service-fallback-v2"

STORAGE_FALLBACK_V2 = FallbackQuestion(
    question_id="fallback-temporary-storage-v2",
    category_id=MissingInformationCategory.TEMPORARY_STORAGE_NEED,
    priority=10,
    question="Might temporary storage be needed before final delivery?",
    why_it_matters=STORAGE_KNOWLEDGE.statement,
    relevant_knowledge_ids=(STORAGE_KNOWLEDGE.knowledge_id,),
)
FALLBACK_QUESTIONS_V2 = (STORAGE_FALLBACK_V2, *FALLBACK_QUESTIONS[1:])

PROSE_VIOLATION_CODE_ORDER = (
    "irrelevant_location_reference",
    "unsupported_home_or_property_assertion",
    "storage_modality_overstatement",
    "unsupported_service_selection_language",
    "grounding_summary_mismatch",
)

PROSE_FIELDS = (
    "question",
    "information_it_would_clarify",
    "why_it_matters",
)
STORAGE_MODALITY_FIELDS = (*PROSE_FIELDS, "grounding_summary")
HOME_OR_PROPERTY_PHRASES = (
    "your new home",
    "your home",
    "your house",
    "your property",
    "your residence",
)
SELECTION_ADJECTIVES = (
    "appropriate",
    "best",
    "suitable",
    "recommended",
)
SELECTION_NOUN_PATTERNS = (
    r"moving[ -]services?",
    r"services?",
    r"movers?",
    r"providers?",
    r"moving[ -]service models?",
    r"service models?",
)


class MovingServiceQuestionRequestV2(MovingServiceQuestionRequest):
    prompt_version: Literal["moving-service-questions-prompt-v2"]
    schema_version: Literal["moving-service-questions-schema-v2"]


class MovingServiceQuestionResponseV2(MovingServiceQuestionResponse):
    prompt_version: Literal["moving-service-questions-prompt-v2"]
    schema_version: Literal["moving-service-questions-schema-v2"]


class ProseValidationError(ResponseValidationError):
    """Reject a complete v2 response and retain bounded violation codes."""

    def __init__(self, violation_codes: tuple[str, ...]):
        self.violation_codes = violation_codes
        super().__init__("The response failed capability-specific prose validation.")


@dataclass(frozen=True)
class V2ValidationResult:
    """Bounded result proving prose rejection precedes fallback selection."""

    response: MovingServiceQuestionResponseV2 | None
    prose_violation_codes: tuple[str, ...]
    fallback: FallbackQuestion | None


def construct_request_v2(trusted_state) -> MovingServiceQuestionRequestV2:
    """Build the exact v2 request from the existing bounded request construction."""
    request_v1 = construct_request(trusted_state)
    document = request_v1.model_dump(mode="python")
    document["prompt_version"] = PROMPT_VERSION_V2
    document["schema_version"] = SCHEMA_VERSION_V2
    return MovingServiceQuestionRequestV2.model_validate(document)


def _normalized_phrase_text(value: str) -> str:
    return " ".join(value.casefold().split())


def _contains_exact_phrase(value: str, phrase: str) -> bool:
    normalized_value = _normalized_phrase_text(value)
    normalized_phrase = _normalized_phrase_text(phrase)
    return bool(
        re.search(
            rf"(?<!\w){re.escape(normalized_phrase)}(?!\w)",
            normalized_value,
        )
    )


def _contains_storage_modality_overstatement(value: str) -> bool:
    normalized = _normalized_phrase_text(value)
    if not re.search(r"\bstorage\b", normalized):
        return False
    return bool(
        re.search(r"\brequired\b|\brequirement\b|\bmust\b|\bwill need\b", normalized)
    )


def _contains_selection_language(value: str) -> bool:
    normalized = _normalized_phrase_text(value)
    adjectives = "|".join(map(re.escape, SELECTION_ADJECTIVES))
    nouns = "|".join(SELECTION_NOUN_PATTERNS)
    return bool(re.search(rf"\b(?:{adjectives})\s+(?:{nouns})\b", normalized))


def _temporary_storage_knowledge_statement(
    request: MovingServiceQuestionRequestV2,
) -> tuple[str, str] | None:
    for item in request.curated_knowledge_items:
        if item.knowledge_id == STORAGE_KNOWLEDGE.knowledge_id:
            return item.knowledge_id, item.statement
    return None


def collect_prose_violation_codes(
    request: MovingServiceQuestionRequestV2,
    response: MovingServiceQuestionResponseV2,
) -> tuple[str, ...]:
    """Collect every bounded v2 violation in stable policy order."""
    detected: set[str] = set()
    knowledge = _temporary_storage_knowledge_statement(request)

    for suggestion in response.suggestions:
        if (
            suggestion.selected_missing_information_category
            is not MissingInformationCategory.TEMPORARY_STORAGE_NEED
        ):
            continue

        prose_values = tuple(getattr(suggestion, field) for field in PROSE_FIELDS)
        supplied_locations = (
            request.trusted_state.origin_region,
            request.trusted_state.destination_region,
        )
        if any(
            location.strip()
            and _contains_exact_phrase(value, location)
            for value in prose_values
            for location in supplied_locations
        ):
            detected.add("irrelevant_location_reference")

        if any(
            _contains_exact_phrase(value, phrase)
            for value in prose_values
            for phrase in HOME_OR_PROPERTY_PHRASES
        ):
            detected.add("unsupported_home_or_property_assertion")

        if any(
            _contains_storage_modality_overstatement(getattr(suggestion, field))
            for field in STORAGE_MODALITY_FIELDS
        ):
            detected.add("storage_modality_overstatement")

        if any(_contains_selection_language(value) for value in prose_values):
            detected.add("unsupported_service_selection_language")

        expected_ids_and_statement = knowledge
        if expected_ids_and_statement is None:
            detected.add("grounding_summary_mismatch")
        else:
            knowledge_id, statement = expected_ids_and_statement
            if (
                suggestion.relevant_knowledge_ids != (knowledge_id,)
                or suggestion.grounding_summary != statement
            ):
                detected.add("grounding_summary_mismatch")

    return tuple(code for code in PROSE_VIOLATION_CODE_ORDER if code in detected)


def collect_fallback_prose_violation_codes(
    request: MovingServiceQuestionRequestV2,
    fallback: FallbackQuestion,
) -> tuple[str, ...]:
    """Apply relevant user-facing checks to the deterministic fallback prose."""
    if fallback.category_id is not MissingInformationCategory.TEMPORARY_STORAGE_NEED:
        return ()

    detected: set[str] = set()
    values = (fallback.question, fallback.why_it_matters)
    for location in (
        request.trusted_state.origin_region,
        request.trusted_state.destination_region,
    ):
        if location.strip() and any(
            _contains_exact_phrase(value, location) for value in values
        ):
            detected.add("irrelevant_location_reference")
    if any(
        _contains_exact_phrase(value, phrase)
        for value in values
        for phrase in HOME_OR_PROPERTY_PHRASES
    ):
        detected.add("unsupported_home_or_property_assertion")
    if any(_contains_storage_modality_overstatement(value) for value in values):
        detected.add("storage_modality_overstatement")
    if any(_contains_selection_language(value) for value in values):
        detected.add("unsupported_service_selection_language")
    return tuple(code for code in PROSE_VIOLATION_CODE_ORDER if code in detected)


def select_fallback_v2(
    request: MovingServiceQuestionRequestV2,
) -> FallbackQuestion | None:
    """Select the versioned v2 fallback without changing v1 runtime behavior."""
    missing_categories = {item.category_id for item in request.missing_information}
    candidates = [
        question
        for question in FALLBACK_QUESTIONS_V2
        if question.category_id in missing_categories
    ]
    return min(candidates, key=lambda question: question.priority) if candidates else None


def _validate_v2_semantics(
    request: MovingServiceQuestionRequestV2,
    response: MovingServiceQuestionResponseV2,
) -> None:
    supplied_knowledge_ids = {
        item.knowledge_id for item in request.curated_knowledge_items
    }
    missing_by_category = {
        item.category_id: item for item in request.missing_information
    }
    question_ids: set[str] = set()
    categories: set[MissingInformationCategory] = set()
    normalized_questions: set[str] = set()

    for suggestion in response.suggestions:
        if suggestion.question_id in question_ids:
            raise ResponseValidationError("Question IDs must be unique.")
        question_ids.add(suggestion.question_id)

        category = suggestion.selected_missing_information_category
        if category in categories:
            raise ResponseValidationError(
                "Suggestions must target unique missing-information categories."
            )
        categories.add(category)

        normalized_question = normalize_question_text(suggestion.question)
        if normalized_question in normalized_questions:
            raise ResponseValidationError("Question text must be unique.")
        normalized_questions.add(normalized_question)

        missing_item = missing_by_category.get(category)
        if missing_item is None:
            raise ResponseValidationError(
                "A suggestion targeted information that is not currently missing."
            )
        if suggestion.suggested_answer_type is not missing_item.answer_type:
            raise ResponseValidationError("The suggested answer type is unsupported.")
        if suggestion.affected_decision_id != (
            request.deterministic_context.open_decision.decision_id
        ):
            raise ResponseValidationError("The affected Decision is not open.")
        if not set(suggestion.relevant_knowledge_ids).issubset(
            supplied_knowledge_ids
        ):
            raise ResponseValidationError(
                "A suggestion referenced knowledge that was not supplied."
            )


def validate_response_v2(
    request: MovingServiceQuestionRequestV2,
    raw_response: Mapping[str, object],
) -> MovingServiceQuestionResponseV2:
    """Validate structure, existing semantics, then all v2 prose checks."""
    try:
        if len(json.dumps(raw_response, separators=(",", ":"))) > (
            MAXIMUM_RESPONSE_CHARACTERS
        ):
            raise ResponseValidationError("The response exceeds the output limit.")
        response = MovingServiceQuestionResponseV2.model_validate(raw_response)
    except (TypeError, ValidationError) as error:
        raise ResponseValidationError("The response does not match the schema.") from error

    _validate_v2_semantics(request, response)
    violation_codes = collect_prose_violation_codes(request, response)
    if violation_codes:
        raise ProseValidationError(violation_codes)
    return response


def validate_v2_response_with_fallback(
    request: MovingServiceQuestionRequestV2,
    raw_response: Mapping[str, object],
) -> V2ValidationResult:
    """Select deterministic fallback only after complete prose rejection."""
    try:
        response = validate_response_v2(request, raw_response)
    except ProseValidationError as error:
        return V2ValidationResult(
            response=None,
            prose_violation_codes=error.violation_codes,
            fallback=select_fallback_v2(request),
        )
    return V2ValidationResult(
        response=response,
        prose_violation_codes=(),
        fallback=None,
    )


def storage_request_v2() -> MovingServiceQuestionRequestV2:
    """Build the reviewed storage fixture for offline v2 tests and artifacts."""
    from app.moving_service_questions import ExperimentFixture

    return construct_request_v2(build_trusted_fixture(ExperimentFixture.STORAGE_UNKNOWN))
