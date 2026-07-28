"""Bounded fake-adapter experiment for moving-service question suggestions."""

from __future__ import annotations

import json
import logging
from enum import StrEnum
from time import perf_counter
from typing import Literal, Mapping, Protocol

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator


CAPABILITY = "suggest_moving_service_questions"
PROMPT_VERSION = "moving-service-questions-prompt-v1"
SCHEMA_VERSION = "moving-service-questions-schema-v1"
KNOWLEDGE_VERSION = "moving-service-storage-fixture-v1"
FALLBACK_VERSION = "moving-service-fallback-v1"
ADAPTER_IDENTIFIER = "fake-moving-service-question-adapter-v1"
MAXIMUM_QUESTIONS = 3
MAXIMUM_OUTPUT_TOKENS = 500
MAXIMUM_RESPONSE_CHARACTERS = 8_000
MOVING_SERVICE_DECISION_ID = "moving-service-model"

logger = logging.getLogger(__name__)


class ExperimentModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ExperimentFixture(StrEnum):
    """Temporary fixture selector for the experiment-only HTTP endpoint."""

    STORAGE_UNKNOWN = "storage_unknown"
    COMPLETE = "complete"
    INVALID_AI_RESPONSE = "invalid_ai_response"
    ADAPTER_UNAVAILABLE = "adapter_unavailable"
    ADAPTER_TIMEOUT = "adapter_timeout"
    BUDGET_UNAVAILABLE = "budget_unavailable"
    AI_DISABLED = "ai_disabled"


class SuggestionSource(StrEnum):
    FAKE_AI_ADAPTER = "fake_ai_adapter"
    DETERMINISTIC_FALLBACK = "deterministic_fallback"
    NONE = "none"


class AnswerType(StrEnum):
    BOOLEAN = "boolean"
    ENUM = "enum"


class InformationStatus(StrEnum):
    KNOWN = "known"
    MISSING = "missing"
    NOT_APPLICABLE = "not_applicable"


class MissingInformationCategory(StrEnum):
    TEMPORARY_STORAGE_NEED = "temporary_storage_need"
    WILLING_TO_DRIVE_RENTAL_TRUCK = "willing_to_drive_rental_truck"
    COST_VS_CONVENIENCE_PREFERENCE = "cost_vs_convenience_preference"
    PACKING_PREFERENCE = "packing_preference"
    SPECIALTY_ITEM_NEEDS = "specialty_item_needs"


class InformationValue(ExperimentModel):
    status: InformationStatus
    value: bool | str | None = None

    @model_validator(mode="after")
    def validate_status_and_value(self) -> "InformationValue":
        if self.status is InformationStatus.KNOWN and self.value is None:
            raise ValueError("Known information requires a value.")
        if self.status is not InformationStatus.KNOWN and self.value is not None:
            raise ValueError("Only known information may contain a value.")
        return self


class MovingServiceTrustedState(ExperimentModel):
    goal_summary: str = Field(max_length=160)
    move_type: Literal["interstate"]
    origin_region: str = Field(max_length=80)
    destination_region: str = Field(max_length=80)
    target_move_window: str = Field(max_length=80)
    household_size: InformationValue
    temporary_storage_need: InformationValue
    packing_preference: InformationValue
    willing_to_drive_rental_truck: InformationValue
    cost_vs_convenience_preference: InformationValue
    specialty_item_needs: InformationValue
    known_constraints: tuple[str, ...] = Field(max_length=8)


class MissingInformationItem(ExperimentModel):
    category_id: MissingInformationCategory
    state_field: MissingInformationCategory
    answer_type: AnswerType
    allowed_enum_values: tuple[str, ...] | None = Field(default=None, max_length=8)
    reason_missing: str = Field(max_length=200)

    @model_validator(mode="after")
    def validate_deterministic_mapping(self) -> "MissingInformationItem":
        if self.category_id is not self.state_field:
            raise ValueError("Category and state-field mapping must match the allowlist.")
        if self.answer_type is AnswerType.BOOLEAN and self.allowed_enum_values is not None:
            raise ValueError("Boolean information cannot define enum values.")
        if self.answer_type is AnswerType.ENUM and not self.allowed_enum_values:
            raise ValueError("Enum information requires allowed values.")
        return self


class MovingServiceDecisionContext(ExperimentModel):
    decision_id: Literal["moving-service-model"]
    status: Literal["unresolved"]
    title: str = Field(max_length=120)


class DeterministicContext(ExperimentModel):
    open_decision: MovingServiceDecisionContext
    current_recommendation: str = Field(max_length=240)
    research_stage: Literal["moving_service_research"]
    applicable_known_constraints: tuple[str, ...] = Field(max_length=8)


class CuratedKnowledgeItem(ExperimentModel):
    knowledge_id: str = Field(max_length=120)
    service_model: str = Field(max_length=80)
    statement: str = Field(max_length=400)
    tradeoff_category: str = Field(max_length=80)
    applicable_conditions: tuple[str, ...] = Field(max_length=8)
    source: str = Field(max_length=200)
    reviewed_at: str = Field(max_length=32)
    freshness_guidance: str = Field(max_length=160)
    version: str = Field(max_length=32)


class RequestedOutput(ExperimentModel):
    prefer_one_question: Literal[True] = True
    permit_zero_questions: Literal[True] = True
    prohibit_service_model_selection: Literal[True] = True
    prohibit_provider_selection: Literal[True] = True
    prohibit_state_mutation: Literal[True] = True


class MovingServiceQuestionRequest(ExperimentModel):
    capability: Literal["suggest_moving_service_questions"]
    trusted_state: MovingServiceTrustedState
    missing_information: tuple[MissingInformationItem, ...] = Field(max_length=5)
    deterministic_context: DeterministicContext
    curated_knowledge_items: tuple[CuratedKnowledgeItem, ...] = Field(max_length=4)
    requested_output: RequestedOutput
    prompt_version: Literal["moving-service-questions-prompt-v1"]
    schema_version: Literal["moving-service-questions-schema-v1"]
    knowledge_fixture_version: Literal["moving-service-storage-fixture-v1"]
    maximum_questions: Literal[3]
    maximum_output_tokens: Literal[500]


class MovingServiceQuestionSuggestion(ExperimentModel):
    question_id: str = Field(min_length=1, max_length=120)
    question: str = Field(min_length=1, max_length=240)
    why_it_matters: str = Field(min_length=1, max_length=400)
    information_it_would_clarify: str = Field(min_length=1, max_length=160)
    affected_decision_id: str = Field(min_length=1, max_length=120)
    selected_missing_information_category: MissingInformationCategory
    relevant_knowledge_ids: tuple[str, ...] = Field(min_length=1, max_length=4)
    grounding_summary: str = Field(min_length=1, max_length=500)
    reason_not_deterministic: str = Field(min_length=1, max_length=300)
    uncertainties: tuple[str, ...] = Field(max_length=5)
    suggested_answer_type: AnswerType
    requires_user_confirmation: Literal[True]


class MovingServiceQuestionResponse(ExperimentModel):
    capability: Literal["suggest_moving_service_questions"]
    prompt_version: Literal["moving-service-questions-prompt-v1"]
    schema_version: Literal["moving-service-questions-schema-v1"]
    suggestions: tuple[MovingServiceQuestionSuggestion, ...] = Field(max_length=3)
    fallback_recommended: bool
    warnings: tuple[str, ...] = Field(max_length=5)


class DisplaySuggestion(ExperimentModel):
    question_id: str
    question: str
    why_it_matters: str
    answer_type: AnswerType
    allowed_enum_values: tuple[str, ...] | None
    requires_user_confirmation: Literal[True]
    grounding_details: tuple[str, ...]


class ExperimentObservability(ExperimentModel):
    capability: Literal["suggest_moving_service_questions"]
    prompt_version: str
    schema_version: str
    fixture_id: ExperimentFixture
    adapter_identifier: str
    knowledge_version: str
    referenced_knowledge_ids: tuple[str, ...]
    schema_valid: bool | None
    fallback_used: bool
    fallback_reason: str | None
    suggestion_count: int
    duration_ms: float
    estimated_cost: Literal["$0.00"]
    user_disposition: None = None


class MovingServiceQuestionExperimentResult(ExperimentModel):
    suggestion: DisplaySuggestion | None
    source: SuggestionSource
    no_question_reason: str | None
    observability: ExperimentObservability


class MovingServiceQuestionSuggestionAdapter(Protocol):
    """Capability-specific adapter boundary for the fake experiment."""

    def suggest(
        self,
        request: MovingServiceQuestionRequest,
    ) -> Mapping[str, object]:
        ...


class AdapterUnavailableError(RuntimeError):
    pass


class AdapterTimeoutError(TimeoutError):
    pass


STORAGE_KNOWLEDGE = CuratedKnowledgeItem(
    knowledge_id="moving-service.storage-question.fixture.v1",
    service_model="multiple_moving_service_models",
    statement=(
        "A need for temporary storage can affect which moving-service models are "
        "practical to investigate."
    ),
    tradeoff_category="temporary_storage",
    applicable_conditions=("temporary_storage_need_is_unknown",),
    source=(
        "GoTime implementation experiment fixture; not approved for real-model use."
    ),
    reviewed_at="2026-07-27",
    freshness_guidance=(
        "Fixture-only statement; review and source approval are required before "
        "real-model evaluation."
    ),
    version="1.0.0",
)


ANSWER_TYPES = {
    MissingInformationCategory.TEMPORARY_STORAGE_NEED: (AnswerType.BOOLEAN, None),
    MissingInformationCategory.WILLING_TO_DRIVE_RENTAL_TRUCK: (
        AnswerType.BOOLEAN,
        None,
    ),
    MissingInformationCategory.COST_VS_CONVENIENCE_PREFERENCE: (
        AnswerType.ENUM,
        ("minimize_cost", "balance", "minimize_hands_on_work"),
    ),
    MissingInformationCategory.PACKING_PREFERENCE: (
        AnswerType.ENUM,
        ("self_pack", "partial_help", "full_packing"),
    ),
    MissingInformationCategory.SPECIALTY_ITEM_NEEDS: (AnswerType.BOOLEAN, None),
}


class FallbackQuestion(ExperimentModel):
    question_id: str
    category_id: MissingInformationCategory
    priority: int
    question: str
    why_it_matters: str
    relevant_knowledge_ids: tuple[str, ...]


FALLBACK_QUESTIONS = (
    FallbackQuestion(
        question_id="fallback-temporary-storage-v1",
        category_id=MissingInformationCategory.TEMPORARY_STORAGE_NEED,
        priority=10,
        question="Will you need temporary storage between homes?",
        why_it_matters=(
            "Storage needs can change which moving-service models are practical "
            "to investigate."
        ),
        relevant_knowledge_ids=(STORAGE_KNOWLEDGE.knowledge_id,),
    ),
    FallbackQuestion(
        question_id="fallback-rental-truck-driving-v1",
        category_id=MissingInformationCategory.WILLING_TO_DRIVE_RENTAL_TRUCK,
        priority=20,
        question="Would someone in your household be willing to drive a rental truck?",
        why_it_matters=(
            "Driving willingness determines whether self-drive approaches are "
            "practical to investigate."
        ),
        relevant_knowledge_ids=(),
    ),
    FallbackQuestion(
        question_id="fallback-cost-convenience-v1",
        category_id=MissingInformationCategory.COST_VS_CONVENIENCE_PREFERENCE,
        priority=30,
        question=(
            "Would you rather minimize cost, balance cost and effort, or minimize "
            "hands-on work?"
        ),
        why_it_matters=(
            "This tradeoff helps focus later moving-service research on approaches "
            "that fit your priorities."
        ),
        relevant_knowledge_ids=(),
    ),
    FallbackQuestion(
        question_id="fallback-packing-preference-v1",
        category_id=MissingInformationCategory.PACKING_PREFERENCE,
        priority=40,
        question="How much packing help would you want from a moving service?",
        why_it_matters=(
            "Packing responsibility can affect which moving-service approaches "
            "deserve investigation."
        ),
        relevant_knowledge_ids=(),
    ),
    FallbackQuestion(
        question_id="fallback-specialty-items-v1",
        category_id=MissingInformationCategory.SPECIALTY_ITEM_NEEDS,
        priority=50,
        question="Are there specialty items that require special handling?",
        why_it_matters=(
            "Special handling needs can affect which moving-service approaches are "
            "practical."
        ),
        relevant_knowledge_ids=(),
    ),
)


def _information(
    status: InformationStatus, value: bool | str | None = None
) -> InformationValue:
    return InformationValue(status=status, value=value)


def build_trusted_fixture(fixture: ExperimentFixture) -> MovingServiceTrustedState:
    """Build narrow trusted state; the HTTP fixture value never reaches the adapter."""
    complete = fixture is ExperimentFixture.COMPLETE
    return MovingServiceTrustedState(
        goal_summary="Relocate the household from Tennessee to Northern California.",
        move_type="interstate",
        origin_region="Tennessee",
        destination_region="Northern California",
        target_move_window="explicitly_unknown",
        household_size=_information(InformationStatus.KNOWN, "household"),
        temporary_storage_need=_information(
            InformationStatus.KNOWN if complete else InformationStatus.MISSING,
            False if complete else None,
        ),
        packing_preference=_information(
            InformationStatus.KNOWN,
            "self_pack" if complete else "full_packing",
        ),
        willing_to_drive_rental_truck=_information(
            InformationStatus.KNOWN, False
        ),
        cost_vs_convenience_preference=_information(
            InformationStatus.KNOWN, "balance"
        ),
        specialty_item_needs=_information(InformationStatus.KNOWN, False),
        known_constraints=("The household is unwilling to drive a rental truck.",),
    )


def construct_request(
    trusted_state: MovingServiceTrustedState,
) -> MovingServiceQuestionRequest:
    """Construct the bounded adapter request from trusted experiment state."""
    missing_information = []
    for category in MissingInformationCategory:
        state = getattr(trusted_state, category.value)
        if state.status is not InformationStatus.MISSING:
            continue
        answer_type, allowed_values = ANSWER_TYPES[category]
        missing_information.append(
            MissingInformationItem(
                category_id=category,
                state_field=category,
                answer_type=answer_type,
                allowed_enum_values=allowed_values,
                reason_missing=f"{category.value} has not been confirmed.",
            )
        )

    return MovingServiceQuestionRequest(
        capability=CAPABILITY,
        trusted_state=trusted_state,
        missing_information=tuple(missing_information),
        deterministic_context=DeterministicContext(
            open_decision=MovingServiceDecisionContext(
                decision_id=MOVING_SERVICE_DECISION_ID,
                status="unresolved",
                title="Determine which moving-service models deserve investigation",
            ),
            current_recommendation=(
                "Clarify unresolved moving-service needs before investigating "
                "service models."
            ),
            research_stage="moving_service_research",
            applicable_known_constraints=trusted_state.known_constraints,
        ),
        curated_knowledge_items=(STORAGE_KNOWLEDGE,),
        requested_output=RequestedOutput(),
        prompt_version=PROMPT_VERSION,
        schema_version=SCHEMA_VERSION,
        knowledge_fixture_version=KNOWLEDGE_VERSION,
        maximum_questions=MAXIMUM_QUESTIONS,
        maximum_output_tokens=MAXIMUM_OUTPUT_TOKENS,
    )


def _valid_storage_response() -> dict[str, object]:
    return {
        "capability": CAPABILITY,
        "prompt_version": PROMPT_VERSION,
        "schema_version": SCHEMA_VERSION,
        "suggestions": [
            {
                "question_id": "ai-temporary-storage-v1",
                "question": "Will you need temporary storage between homes?",
                "why_it_matters": (
                    "Storage needs can change which moving-service models are "
                    "practical to investigate."
                ),
                "information_it_would_clarify": "Temporary storage need",
                "affected_decision_id": MOVING_SERVICE_DECISION_ID,
                "selected_missing_information_category": "temporary_storage_need",
                "relevant_knowledge_ids": [STORAGE_KNOWLEDGE.knowledge_id],
                "grounding_summary": (
                    "The supplied state marks temporary storage as missing, and "
                    f"{STORAGE_KNOWLEDGE.knowledge_id} explains why it matters."
                ),
                "reason_not_deterministic": (
                    "The experiment is testing grounded question prioritization; "
                    "the deterministic fallback remains available."
                ),
                "uncertainties": ["The user has not confirmed a storage need."],
                "suggested_answer_type": "boolean",
                "requires_user_confirmation": True,
            }
        ],
        "fallback_recommended": False,
        "warnings": [],
    }


class FakeMovingServiceQuestionSuggestionAdapter:
    """Return predefined responses for the temporary experiment fixtures."""

    def __init__(self, fixture: ExperimentFixture):
        self.fixture = fixture

    def suggest(
        self,
        request: MovingServiceQuestionRequest,
    ) -> Mapping[str, object]:
        if self.fixture is ExperimentFixture.ADAPTER_UNAVAILABLE:
            raise AdapterUnavailableError("The fake adapter is unavailable.")
        if self.fixture is ExperimentFixture.ADAPTER_TIMEOUT:
            raise AdapterTimeoutError("The fake adapter timed out.")
        if self.fixture is ExperimentFixture.COMPLETE:
            return {
                "capability": CAPABILITY,
                "prompt_version": PROMPT_VERSION,
                "schema_version": SCHEMA_VERSION,
                "suggestions": [],
                "fallback_recommended": False,
                "warnings": [],
            }
        response = _valid_storage_response()
        if self.fixture is ExperimentFixture.INVALID_AI_RESPONSE:
            response["suggestions"][0]["relevant_knowledge_ids"] = [  # type: ignore[index]
                "unknown-knowledge-id"
            ]
        return response


class ResponseValidationError(ValueError):
    pass


def normalize_question_text(value: str) -> str:
    return " ".join(
        "".join(character.lower() for character in value if character.isalnum() or character.isspace()).split()
    )


def validate_response(
    request: MovingServiceQuestionRequest,
    raw_response: Mapping[str, object],
) -> MovingServiceQuestionResponse:
    """Validate the complete response; no individual suggestion is retained on failure."""
    try:
        if len(json.dumps(raw_response, separators=(",", ":"))) > MAXIMUM_RESPONSE_CHARACTERS:
            raise ResponseValidationError("The response exceeds the output limit.")
        response = MovingServiceQuestionResponse.model_validate(raw_response)
    except (TypeError, ValidationError) as error:
        raise ResponseValidationError("The response does not match the schema.") from error

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

    return response


def select_fallback(
    request: MovingServiceQuestionRequest,
) -> FallbackQuestion | None:
    """Select one frozen fallback question from currently missing information."""
    missing_categories = {item.category_id for item in request.missing_information}
    candidates = [
        question
        for question in FALLBACK_QUESTIONS
        if question.category_id in missing_categories
    ]
    return min(candidates, key=lambda question: question.priority) if candidates else None


def _display_from_ai(
    request: MovingServiceQuestionRequest,
    suggestion: MovingServiceQuestionSuggestion,
) -> DisplaySuggestion:
    missing_item = next(
        item
        for item in request.missing_information
        if item.category_id is suggestion.selected_missing_information_category
    )
    knowledge_by_id = {
        item.knowledge_id: item for item in request.curated_knowledge_items
    }
    return DisplaySuggestion(
        question_id=suggestion.question_id,
        question=suggestion.question,
        why_it_matters=suggestion.why_it_matters,
        answer_type=suggestion.suggested_answer_type,
        allowed_enum_values=missing_item.allowed_enum_values,
        requires_user_confirmation=True,
        grounding_details=tuple(
            knowledge_by_id[knowledge_id].statement
            for knowledge_id in suggestion.relevant_knowledge_ids
        ),
    )


def _display_from_fallback(
    request: MovingServiceQuestionRequest,
    question: FallbackQuestion,
) -> DisplaySuggestion:
    missing_item = next(
        item
        for item in request.missing_information
        if item.category_id is question.category_id
    )
    knowledge_by_id = {
        item.knowledge_id: item for item in request.curated_knowledge_items
    }
    return DisplaySuggestion(
        question_id=question.question_id,
        question=question.question,
        why_it_matters=question.why_it_matters,
        answer_type=missing_item.answer_type,
        allowed_enum_values=missing_item.allowed_enum_values,
        requires_user_confirmation=True,
        grounding_details=tuple(
            knowledge_by_id[knowledge_id].statement
            for knowledge_id in question.relevant_knowledge_ids
            if knowledge_id in knowledge_by_id
        ),
    )


def run_experiment(
    fixture: ExperimentFixture,
    adapter: MovingServiceQuestionSuggestionAdapter | None = None,
) -> MovingServiceQuestionExperimentResult:
    """Run one explicit fake-adapter experiment invocation."""
    started_at = perf_counter()
    trusted_state = build_trusted_fixture(fixture)
    request = construct_request(trusted_state)
    selected_adapter = adapter or FakeMovingServiceQuestionSuggestionAdapter(fixture)
    schema_valid: bool | None = None
    fallback_reason: str | None = None
    response: MovingServiceQuestionResponse | None = None

    if fixture is ExperimentFixture.BUDGET_UNAVAILABLE:
        fallback_reason = "experimental_budget_unavailable"
    elif fixture is ExperimentFixture.AI_DISABLED:
        fallback_reason = "ai_assistance_disabled"
    else:
        try:
            raw_response = selected_adapter.suggest(request)
            response = validate_response(request, raw_response)
            schema_valid = True
        except AdapterUnavailableError:
            fallback_reason = "adapter_unavailable"
        except AdapterTimeoutError:
            fallback_reason = "adapter_timeout"
        except ResponseValidationError:
            schema_valid = False
            fallback_reason = "invalid_adapter_response"

    source = SuggestionSource.NONE
    display_suggestion = None
    referenced_knowledge_ids: tuple[str, ...] = ()
    suggestion_count = len(response.suggestions) if response is not None else 0

    if response is not None and response.suggestions:
        selected_suggestion = response.suggestions[0]
        display_suggestion = _display_from_ai(request, selected_suggestion)
        source = SuggestionSource.FAKE_AI_ADAPTER
        referenced_knowledge_ids = selected_suggestion.relevant_knowledge_ids
    elif response is None:
        fallback = select_fallback(request)
        if fallback is not None:
            display_suggestion = _display_from_fallback(request, fallback)
            source = SuggestionSource.DETERMINISTIC_FALLBACK
            referenced_knowledge_ids = fallback.relevant_knowledge_ids
    elif response.fallback_recommended:
        fallback = select_fallback(request)
        if fallback is not None:
            display_suggestion = _display_from_fallback(request, fallback)
            source = SuggestionSource.DETERMINISTIC_FALLBACK
            fallback_reason = "adapter_recommended_fallback"
            referenced_knowledge_ids = fallback.relevant_knowledge_ids

    no_question_reason = (
        None
        if display_suggestion is not None
        else "No supported moving-service information gap remains."
    )
    fallback_used = source is SuggestionSource.DETERMINISTIC_FALLBACK
    observability = ExperimentObservability(
        capability=CAPABILITY,
        prompt_version=PROMPT_VERSION,
        schema_version=SCHEMA_VERSION,
        fixture_id=fixture,
        adapter_identifier=ADAPTER_IDENTIFIER,
        knowledge_version=KNOWLEDGE_VERSION,
        referenced_knowledge_ids=referenced_knowledge_ids,
        schema_valid=schema_valid,
        fallback_used=fallback_used,
        fallback_reason=fallback_reason,
        suggestion_count=suggestion_count,
        duration_ms=round((perf_counter() - started_at) * 1_000, 3),
        estimated_cost="$0.00",
    )
    logger.info("moving_service_question_experiment", extra={"experiment": observability.model_dump()})
    return MovingServiceQuestionExperimentResult(
        suggestion=display_suggestion,
        source=source,
        no_question_reason=no_question_reason,
        observability=observability,
    )
