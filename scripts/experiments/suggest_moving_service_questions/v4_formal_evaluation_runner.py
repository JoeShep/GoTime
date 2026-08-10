"""Offline-only runner for the frozen-v4 formal evaluation set."""

from __future__ import annotations

import hashlib
import json
import os
import fcntl
from contextlib import contextmanager
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import Mapping

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from app.moving_service_questions import ResponseValidationError, STORAGE_KNOWLEDGE
from freeze_v4_formal_evaluation_set import (
    EMPTY_CASE_IDS,
    GENERATION_CASE_IDS,
    PACKAGE_ROOT,
    SET_ID,
    bind_case,
    source_cases,
    verify_package,
)
from moving_service_questions_v2 import (
    FALLBACK_VERSION_V2,
    MovingServiceQuestionRequestV2,
    MovingServiceQuestionResponseV2,
    ProseValidationError,
    select_fallback_v2,
    validate_response_v2,
)
from moving_service_questions_v4 import (
    MovingServiceQuestionRequestV4,
    MovingServiceQuestionResponseV4,
)
from real_model_adapter import MovingServiceProviderRequest
from rejected_prose_diagnostics import collect_prose_violation_diagnostics
from run_openai_stage_b_v4_pilot import prepare_frozen_v4_provider_metadata

RUNNER_ID = "suggest-moving-service-questions-v4-formal-evaluation-runner-v1"
RUNNER_VERSION = 1
FROZEN_V4_MANIFEST = "3cdbd2bf3606191aa52108d8284c8ab300d58a511f313f78a06be51d95fac649"
EXECUTION_BUDGET_SHA256 = "0d848bce8866023a5b7f7912795a6ee80b3aae471189f447911244da10777b6b"
EVALUATION_MANIFEST_SHA256 = "38c4db2e92368ead41f9c6f87146a83103ae7780328aa7423d13340239134e94"
REQUEST_IDENTITIES_SHA256 = "a23de86e93c3b83b7d51ffa5f73c5d694cd8266c5013c6d14833ad64bddd40ee"
FALLBACK_COMPARISONS = (
    "materially_better", "slightly_better", "equivalent",
    "slightly_worse", "materially_worse",
)
EQUIVALENT_OR_BETTER = frozenset(FALLBACK_COMPARISONS[:3])
HARD_PROSE_CODES = frozenset({
    "unsupported_home_or_property_assertion",
    "storage_modality_overstatement",
    "unsupported_service_selection_language",
    "grounding_summary_mismatch",
})


class EvaluationRunnerError(RuntimeError):
    pass


class CaseState(StrEnum):
    PENDING = "pending"
    DETERMINISTIC_EMPTY_COMPLETE = "deterministic_empty_complete"
    PREFLIGHT_READY = "preflight_ready"
    PREFLIGHT_COMPLETE = "preflight_complete"
    GENERATION_READY = "generation_ready"
    GENERATION_COMPLETE = "generation_complete"
    TRANSPORT_FAILURE = "transport_failure"
    AUTOMATED_REJECTED = "automated_rejected"
    AWAITING_HUMAN_REVIEW = "awaiting_human_review"
    HUMAN_REVIEW_COMPLETE = "human_review_complete"
    CASE_COMPLETE = "case_complete"


class ReviewDecision(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"
    REQUEST_CHANGES = "request_changes"


class CaseDisposition(StrEnum):
    AWAITING_HUMAN_REVIEW = "awaiting_human_review"
    PASSED = "passed"
    DETERMINISTIC_EMPTY_PASSED = "deterministic_empty_passed"
    AUTOMATED_REJECTED = "automated_rejected"
    HUMAN_REJECTED = "human_rejected"
    TRANSPORT_FAILURE = "transport_failure"


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class HumanReview(FrozenModel):
    decision: ReviewDecision
    grounding_accurate: bool
    invented_user_fact: bool
    irrelevant_detail: bool
    modality_overstatement: bool
    service_selection_overstatement: bool
    clarity_score: int = Field(ge=1, le=5)
    usefulness_score: int = Field(ge=1, le=5)
    fallback_comparison: str
    bounded_notes: str = Field(max_length=500)

    @model_validator(mode="after")
    def validate_comparison(self) -> "HumanReview":
        if self.fallback_comparison not in FALLBACK_COMPARISONS:
            raise ValueError("unsupported fallback comparison")
        return self


class CaseOutcome(FrozenModel):
    evaluation_set_id: str
    runner_id: str
    case_id: str
    synthetic: bool
    state_history: tuple[CaseState, ...]
    deterministic_eligibility: str
    provider_request_expected: bool
    token_preflight_count: int
    generation_attempt_count: int
    retry_count: int
    transport_result: str
    pydantic_validation_result: bool | None
    semantic_validation_result: bool | None
    prose_validation_result: bool | None
    ordered_prose_violation_codes: tuple[str, ...]
    bounded_rejected_prose_diagnostics: tuple[Mapping[str, object], ...]
    fallback_selected: bool
    fallback_version: str | None
    fallback_question_id: str | None
    suggestion_count: int
    selected_category: str | None
    requires_user_confirmation: bool | None
    expected_empty_correctness: bool | None
    human_review_applicable: bool
    human_review_decision: ReviewDecision | None
    grounding_accurate: bool | None
    invented_user_fact: bool | None
    irrelevant_detail: bool | None
    modality_overstatement: bool | None
    service_selection_overstatement: bool | None
    clarity_score: int | None
    usefulness_score: int | None
    fallback_comparison: str | None
    final_case_disposition: CaseDisposition
    deterministic_request_sha256: str | None
    canonical_attempt_sha256: str | None
    provider_fingerprint: str | None
    preflight_audit_sha256: str | None
    generation_audit_sha256: str | None
    validated_response_evidence_sha256: str | None
    human_review_sha256: str | None
    evidence_deletion_sha256: str | None
    closure_sha256: str | None
    response_evidence_deleted: bool
    unauthorized_behavior: bool
    synthetic_input_tokens: int | None
    synthetic_conservative_cost_usd: str | None
    human_review_reviewer: str | None = None

    @model_validator(mode="after")
    def validate_terminal_review_and_empty_invariants(self) -> "CaseOutcome":
        complete = CaseState.CASE_COMPLETE in self.state_history
        if complete and self.human_review_applicable:
            if not (
                self.human_review_decision is not None
                and self.human_review_sha256
                and self.evidence_deletion_sha256
                and self.response_evidence_deleted
            ):
                raise ValueError("reviewed case cannot complete before evidence deletion")
        if self.deterministic_eligibility == "empty" and complete:
            if not _empty_outcome_is_exact(self):
                raise ValueError("deterministic empty outcome is internally contradictory")
        return self


class FinalEvaluationReport(FrozenModel):
    evaluation_set_id: str
    runner_id: str
    runner_version: int
    synthetic_rehearsal: bool
    bounded_evaluation_statement: str
    frozen_v4_manifest_sha256: str
    execution_budget_sha256: str
    evaluation_manifest_sha256: str
    case_ids: tuple[str, ...]
    case_result_table: tuple[Mapping[str, object], ...]
    deterministic_empty_results: int
    generation_attempts_used: int
    token_preflights_used: int
    retries: int
    synthetic_provider_cost_usd: str
    provider_transport_failure_count: int
    structural_pass_rate: str
    semantic_pass_rate: str
    prose_pass_rate: str
    hard_gate_failure_count: int
    invented_fact_count: int
    grounding_failure_count: int
    modality_overstatement_count: int
    service_selection_overstatement_count: int
    unauthorized_behavior_count: int
    average_clarity: str | None
    average_usefulness: str | None
    fallback_comparison_distribution: Mapping[str, Mapping[str, object]]
    better_than_fallback_percentage: str | None
    equivalent_to_fallback_percentage: str | None
    worse_than_fallback_percentage: str | None
    equivalent_or_better_percentage: str | None
    expected_empty_correctness: bool
    hard_gate_result: str
    quality_gate_result: str
    final_disposition: str
    ledger_version: int | None = None
    ledger_sha256: str | None = None
    transition_journal_terminal_sha256: str | None = None
    journal_transition_count: int | None = None
    case_closure_sha256: Mapping[str, str] | None = None
    terminal_outcome_sha256: Mapping[str, str] | None = None
    report_serialization_version: int = 1


def _empty_outcome_is_exact(item: CaseOutcome) -> bool:
    return bool(
        item.deterministic_eligibility == "empty"
        and item.provider_request_expected is False
        and item.suggestion_count == 0
        and item.selected_category is None
        and item.requires_user_confirmation in {None, False}
        and item.deterministic_request_sha256 is None
        and item.canonical_attempt_sha256 is None
        and item.provider_fingerprint is None
        and item.token_preflight_count == 0
        and item.generation_attempt_count == 0
        and item.retry_count == 0
        and item.expected_empty_correctness is True
    )


@dataclass(frozen=True)
class SyntheticCasePlan:
    review: HumanReview | None
    transport_failure_stage: str | None = None
    automated_variant: str = "valid"


class SyntheticPreflightEvidence:
    """Case-specific, single-use synthetic evidence; never serializable."""

    def __init__(self, *, case_id: str, identity: tuple[str, str, str],
                 input_tokens: int, conservative_cost: str) -> None:
        self.case_id = case_id
        self.identity = identity
        self.input_tokens = input_tokens
        self.conservative_cost = conservative_cost
        self._consumed = False

    def __reduce__(self) -> object:
        raise TypeError("synthetic preflight evidence cannot be serialized")

    def consume(self, *, case_id: str, identity: tuple[str, str, str]) -> None:
        if self._consumed or case_id != self.case_id or identity != self.identity:
            raise EvaluationRunnerError("case-specific preflight evidence rejected")
        self._consumed = True


class SyntheticEvaluationTransport:
    """Network-incapable transport that preserves exact prepared-object reuse."""

    def __init__(self, *, case_id: str, identity: tuple[str, str, str],
                 plan: SyntheticCasePlan) -> None:
        self.case_id = case_id
        self.identity = identity
        self.plan = plan
        self.preflight_calls = 0
        self.generation_calls = 0
        self.preflight_request_object_id: int | None = None
        self.generation_request_object_id: int | None = None

    def preflight(self, request: MovingServiceProviderRequest, *, input_tokens: int,
                  conservative_cost: str) -> SyntheticPreflightEvidence:
        if self.preflight_calls or self.generation_calls:
            raise EvaluationRunnerError("synthetic transport preflight is single-use")
        self.preflight_calls = 1
        self.preflight_request_object_id = id(request)
        if self.plan.transport_failure_stage == "preflight":
            raise EvaluationRunnerError("synthetic_preflight_transport_failure")
        return SyntheticPreflightEvidence(
            case_id=self.case_id, identity=self.identity,
            input_tokens=input_tokens, conservative_cost=conservative_cost,
        )

    def generate(self, request: MovingServiceProviderRequest,
                 evidence: SyntheticPreflightEvidence) -> object:
        if self.preflight_calls != 1 or self.generation_calls:
            raise EvaluationRunnerError("synthetic generation is single-use and requires preflight")
        if id(request) != self.preflight_request_object_id:
            raise EvaluationRunnerError("verified prepared request object was not reused")
        evidence.consume(case_id=self.case_id, identity=self.identity)
        self.generation_calls = 1
        self.generation_request_object_id = id(request)
        if self.plan.transport_failure_stage == "generation":
            raise EvaluationRunnerError("synthetic_generation_transport_failure")
        return synthetic_response(self.case_id, self.plan.automated_variant)


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"),
                      sort_keys=True).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _percentage(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "0.00"
    return f"{(Decimal(numerator) * Decimal(100) / Decimal(denominator)):.2f}"


def _average(values: list[int]) -> str | None:
    if not values:
        return None
    return f"{(sum(map(Decimal, values)) / Decimal(len(values))):.2f}"


def _v2_request(request: MovingServiceQuestionRequestV4) -> MovingServiceQuestionRequestV2:
    document = request.model_dump(mode="json")
    document["prompt_version"] = "moving-service-questions-prompt-v2"
    document["schema_version"] = "moving-service-questions-schema-v2"
    return MovingServiceQuestionRequestV2.model_validate(document)


def valid_synthetic_response(case_id: str) -> dict[str, object]:
    return {
        "capability": "suggest_moving_service_questions",
        "prompt_version": "moving-service-questions-prompt-v4",
        "schema_version": "moving-service-questions-schema-v4",
        "suggestions": [{
            "question_id": f"{case_id}-temporary-storage",
            "question": "Might you need temporary storage before final delivery?",
            "why_it_matters": "This may affect which moving services you ask about.",
            "information_it_would_clarify": "Whether temporary storage might be needed before final delivery.",
            "affected_decision_id": "moving-service-model",
            "selected_missing_information_category": "temporary_storage_need",
            "relevant_knowledge_ids": [STORAGE_KNOWLEDGE.knowledge_id],
            "grounding_summary": STORAGE_KNOWLEDGE.statement,
            "reason_not_deterministic": "The trusted state does not contain the user's answer.",
            "uncertainties": ["The user has not confirmed a temporary storage need."],
            "suggested_answer_type": "boolean",
            "requires_user_confirmation": True,
        }],
        "fallback_recommended": False,
        "warnings": [],
    }


def synthetic_response(case_id: str, variant: str) -> object:
    response = valid_synthetic_response(case_id)
    if variant == "valid":
        return response
    if variant == "structural_failure":
        return {"capability": "suggest_moving_service_questions"}
    suggestion = response["suggestions"][0]  # type: ignore[index]
    if variant == "semantic_failure":
        suggestion["selected_missing_information_category"] = "packing_preference"  # type: ignore[index]
    elif variant == "prose_failure":
        suggestion["question"] = "You will need storage, so which recommended mover should you choose?"  # type: ignore[index]
    else:
        raise EvaluationRunnerError(f"unknown synthetic response variant: {variant}")
    return response


def validate_case_response(
    request: MovingServiceQuestionRequestV4, raw: object,
) -> tuple[str, MovingServiceQuestionResponseV4 | tuple[str, ...] | None,
           tuple[Mapping[str, object], ...]]:
    if not isinstance(raw, Mapping):
        return "structural_failure", None, ()
    try:
        response_v4 = MovingServiceQuestionResponseV4.model_validate(raw)
    except ValidationError:
        return "structural_failure", None, ()
    request_v2 = _v2_request(request)
    response_document = response_v4.model_dump(mode="json")
    response_document["prompt_version"] = "moving-service-questions-prompt-v2"
    response_document["schema_version"] = "moving-service-questions-schema-v2"
    try:
        validate_response_v2(request_v2, response_document)
        return "validated", response_v4, ()
    except ProseValidationError as error:
        response_v2 = MovingServiceQuestionResponseV2.model_validate(response_document)
        diagnostics = tuple(
            item.as_dict() for item in collect_prose_violation_diagnostics(request_v2, response_v2)
        )
        return "prose_failure", tuple(error.violation_codes), diagnostics
    except ResponseValidationError:
        return "semantic_failure", None, ()


def nominal_review(index: int) -> HumanReview:
    comparisons = (
        "materially_better", "slightly_better", "equivalent", "slightly_better",
        "equivalent", "slightly_better", "equivalent", "slightly_better",
    )
    return HumanReview(
        decision=ReviewDecision.APPROVE,
        grounding_accurate=True,
        invented_user_fact=False,
        irrelevant_detail=False,
        modality_overstatement=False,
        service_selection_overstatement=False,
        clarity_score=5 if index % 3 == 0 else 4,
        usefulness_score=5 if index % 4 == 0 else 4,
        fallback_comparison=comparisons[index],
        bounded_notes="Synthetic rehearsal review; no live response or provider evidence.",
    )


def scenario_plans(scenario: str) -> dict[str, SyntheticCasePlan]:
    plans = {
        case_id: SyntheticCasePlan(review=nominal_review(index))
        for index, case_id in enumerate(GENERATION_CASE_IDS)
    }
    if scenario == "nominal":
        return plans
    if scenario == "hard_gate_failure":
        review = nominal_review(7).model_copy(update={"invented_user_fact": True})
        plans["eval-v4-10"] = SyntheticCasePlan(review=review)
        return plans
    if scenario == "quality_gate_failure":
        for index, case_id in enumerate(GENERATION_CASE_IDS):
            review = nominal_review(index).model_copy(update={
                "usefulness_score": 3,
                "fallback_comparison": "slightly_worse" if index < 4 else "equivalent",
            })
            plans[case_id] = SyntheticCasePlan(review=review)
        return plans
    if scenario == "provider_failure":
        plans["eval-v4-06"] = SyntheticCasePlan(
            review=None, transport_failure_stage="generation"
        )
        return plans
    if scenario in {"structural_failure", "semantic_failure", "prose_failure"}:
        plans["eval-v4-03"] = SyntheticCasePlan(
            review=None, automated_variant=scenario
        )
        return plans
    raise EvaluationRunnerError(f"unknown rehearsal scenario: {scenario}")


class FormalEvaluationRunner:
    def __init__(self, *, scenario: str = "nominal") -> None:
        verify_package()
        self.cases = {item["case_id"]: item for item in source_cases()}
        self.identities = {
            item["case_id"]: item
            for item in json.loads((PACKAGE_ROOT / "request-identities.json").read_text())[
                "request_identities"
            ]
        }
        self.expected = {
            item["case_id"]: item
            for item in json.loads((PACKAGE_ROOT / "expected-behavior.json").read_text())[
                "expected_behaviors"
            ]
        }
        self.budget = json.loads((PACKAGE_ROOT / "execution-budget.json").read_text())
        self.metadata = prepare_frozen_v4_provider_metadata()
        self.plans = scenario_plans(scenario)
        self.scenario = scenario
        self.ledger: dict[str, CaseOutcome] = {}
        self.preflights = 0
        self.generations = 0
        self.retries = 0
        self.validated_evidence: dict[str, Mapping[str, object]] = {}

    def _enforce_budget(self) -> None:
        if len(self.ledger) > self.budget["total_evaluation_outcomes"]:
            raise EvaluationRunnerError("evaluation outcome budget exceeded")
        if self.generations > self.budget["maximum_generation_attempts"]:
            raise EvaluationRunnerError("generation budget exceeded")
        if self.preflights > self.budget["maximum_token_preflights"]:
            raise EvaluationRunnerError("preflight budget exceeded")
        if self.retries != self.budget["retries"]:
            raise EvaluationRunnerError("retry budget exceeded")
        synthetic_spend = sum(
            Decimal(item.synthetic_conservative_cost_usd or "0")
            for item in self.ledger.values()
        )
        if synthetic_spend > Decimal(str(self.budget["maximum_provider_spend_usd"])):
            raise EvaluationRunnerError("provider spend budget exceeded")

    def run_case(
        self,
        case_id: str,
        *,
        defer_human_review: bool = False,
        preflight_already_consumed: bool = False,
    ) -> CaseOutcome:
        if case_id in self.ledger:
            raise EvaluationRunnerError(f"case already has a terminal outcome: {case_id}")
        if case_id not in self.cases:
            raise EvaluationRunnerError(f"unknown frozen evaluation case: {case_id}")
        state = [CaseState.PENDING]
        constructed_requests: list[MovingServiceProviderRequest] = []

        def capture_constructor(**kwargs: object) -> MovingServiceProviderRequest:
            request = MovingServiceProviderRequest(**kwargs)
            constructed_requests.append(request)
            return request

        case, behavior, identity = bind_case(
            self.cases[case_id], self.metadata, capture_constructor
        )
        if behavior != self.expected[case_id] or any(
            identity.get(key) != self.identities[case_id].get(key)
            for key in (
                "provider_request_expected", "deterministic_case_input_sha256",
                "deterministic_request_sha256", "canonical_attempt_sha256",
                "provider_fingerprint", "provider", "ai_model_identifier", "sdk",
            )
        ):
            raise EvaluationRunnerError("frozen case binding drifted")
        if not identity["provider_request_expected"]:
            if constructed_requests:
                raise EvaluationRunnerError("deterministic empty case constructed a provider request")
            state.extend((CaseState.DETERMINISTIC_EMPTY_COMPLETE, CaseState.CASE_COMPLETE))
            outcome = CaseOutcome(
                evaluation_set_id=SET_ID, runner_id=RUNNER_ID, case_id=case_id,
                synthetic=True, state_history=tuple(state), deterministic_eligibility="empty",
                provider_request_expected=False, token_preflight_count=0,
                generation_attempt_count=0, retry_count=0, transport_result="not_applicable",
                pydantic_validation_result=None, semantic_validation_result=None,
                prose_validation_result=None, ordered_prose_violation_codes=(),
                bounded_rejected_prose_diagnostics=(), fallback_selected=False,
                fallback_version=None, fallback_question_id=None, suggestion_count=0,
                selected_category=None, requires_user_confirmation=None,
                expected_empty_correctness=True, human_review_applicable=False,
                human_review_decision=None, grounding_accurate=None, invented_user_fact=None,
                irrelevant_detail=None, modality_overstatement=None,
                service_selection_overstatement=None, clarity_score=None,
                usefulness_score=None, fallback_comparison=None,
                final_case_disposition=CaseDisposition.DETERMINISTIC_EMPTY_PASSED,
                deterministic_request_sha256=None, canonical_attempt_sha256=None,
                provider_fingerprint=None, preflight_audit_sha256=None,
                generation_audit_sha256=None, validated_response_evidence_sha256=None,
                human_review_sha256=None, evidence_deletion_sha256=None,
                closure_sha256=_digest({"case_id": case_id, "closed": True, "synthetic": True}),
                response_evidence_deleted=False, unauthorized_behavior=False,
                synthetic_input_tokens=None, synthetic_conservative_cost_usd=None,
            )
            self.ledger[case_id] = outcome
            self._enforce_budget()
            return outcome

        triple = (
            str(identity["deterministic_request_sha256"]),
            str(identity["canonical_attempt_sha256"]),
            str(identity["provider_fingerprint"]),
        )
        if len(constructed_requests) != 1:
            raise EvaluationRunnerError("generation case did not construct exactly one provider request")
        prepared_request = constructed_requests[0]
        plan = self.plans[case_id]
        transport = SyntheticEvaluationTransport(case_id=case_id, identity=triple, plan=plan)
        state.append(CaseState.PREFLIGHT_READY)
        self.preflights += 1
        tokens = 2700 + int(case_id[-2:]) * 11
        cost = f"{(Decimal(tokens) * Decimal('0.00000068')):.7f}"
        preflight_audit = {
            "case_id": case_id, "synthetic": True, "request_identity": triple,
            "token_preflight_count": 1, "generation_count": 0, "retries": 0,
            "input_tokens": tokens, "conservative_cost_usd": cost,
        }
        preflight_digest = _digest(preflight_audit)
        if preflight_already_consumed:
            transport.preflight_calls = 1
            transport.preflight_request_object_id = id(prepared_request)
            evidence = SyntheticPreflightEvidence(
                case_id=case_id, identity=triple,
                input_tokens=tokens, conservative_cost=cost,
            )
        else:
            try:
                evidence = transport.preflight(
                    prepared_request, input_tokens=tokens, conservative_cost=cost
                )
            except EvaluationRunnerError as error:
                if str(error) != "synthetic_preflight_transport_failure":
                    raise
                state.extend((CaseState.TRANSPORT_FAILURE, CaseState.CASE_COMPLETE))
                outcome = self._failure_outcome(
                    case_id, identity, state, "preflight_failure", preflight_digest,
                    tokens, cost, generation_count=0,
                )
                self.ledger[case_id] = outcome
                self._enforce_budget()
                return outcome
        state.extend((CaseState.PREFLIGHT_COMPLETE, CaseState.GENERATION_READY))
        self.generations += 1
        try:
            raw = transport.generate(prepared_request, evidence)
        except EvaluationRunnerError as error:
            if str(error) != "synthetic_generation_transport_failure":
                raise
            state.extend((CaseState.TRANSPORT_FAILURE, CaseState.CASE_COMPLETE))
            outcome = self._failure_outcome(
                case_id, identity, state, "generation_failure", preflight_digest,
                tokens, cost, generation_count=1,
            )
            self.ledger[case_id] = outcome
            self._enforce_budget()
            return outcome

        state.append(CaseState.GENERATION_COMPLETE)
        if transport.preflight_request_object_id != transport.generation_request_object_id:
            raise EvaluationRunnerError("same verified prepared request did not reach transport")
        request = self._request_for_case_bound(case)
        classification, result, diagnostics = validate_case_response(request, raw)
        fallback = None
        if classification != "validated":
            fallback = select_fallback_v2(_v2_request(request))
        generation_audit = {
            "case_id": case_id, "synthetic": True, "classification": classification,
            "request_identity": triple, "generation_attempt_count": 1,
            "token_preflight_count_during_generation": 0, "retries": 0,
            "prose_violation_codes": list(result) if classification == "prose_failure" else [],
            "rejected_prose_diagnostics": list(diagnostics),
            "fallback_selected": fallback is not None,
            "fallback_version": FALLBACK_VERSION_V2 if fallback is not None else None,
            "fallback_question_id": fallback.question_id if fallback is not None else None,
        }
        generation_digest = _digest(generation_audit)
        closure_digest = _digest({
            "case_id": case_id, "generation_audit_sha256": generation_digest,
            "authorization_consumed": True, "reusable": False,
            "permanent_closed_state_restored": True, "synthetic": True,
        })
        if classification != "validated":
            state.extend((CaseState.AUTOMATED_REJECTED, CaseState.CASE_COMPLETE))
            codes = tuple(result) if classification == "prose_failure" else ()
            outcome = CaseOutcome(
                evaluation_set_id=SET_ID, runner_id=RUNNER_ID, case_id=case_id,
                synthetic=True, state_history=tuple(state), deterministic_eligibility="generate",
                provider_request_expected=True, token_preflight_count=1,
                generation_attempt_count=1, retry_count=0, transport_result="succeeded",
                pydantic_validation_result=classification != "structural_failure",
                semantic_validation_result=classification in {"validated", "prose_failure"},
                prose_validation_result=False if classification == "prose_failure" else None,
                ordered_prose_violation_codes=codes,
                bounded_rejected_prose_diagnostics=diagnostics,
                fallback_selected=fallback is not None, fallback_version=FALLBACK_VERSION_V2,
                fallback_question_id=fallback.question_id if fallback else None,
                suggestion_count=0, selected_category=None, requires_user_confirmation=None,
                expected_empty_correctness=None, human_review_applicable=False,
                human_review_decision=None, grounding_accurate=None, invented_user_fact=None,
                irrelevant_detail=None, modality_overstatement=None,
                service_selection_overstatement=None, clarity_score=None,
                usefulness_score=None, fallback_comparison=None,
                final_case_disposition=CaseDisposition.AUTOMATED_REJECTED,
                deterministic_request_sha256=triple[0], canonical_attempt_sha256=triple[1],
                provider_fingerprint=triple[2], preflight_audit_sha256=preflight_digest,
                generation_audit_sha256=generation_digest,
                validated_response_evidence_sha256=None, human_review_sha256=None,
                evidence_deletion_sha256=None, closure_sha256=closure_digest,
                response_evidence_deleted=False,
                unauthorized_behavior=bool(HARD_PROSE_CODES.intersection(codes)),
                synthetic_input_tokens=tokens, synthetic_conservative_cost_usd=cost,
            )
            self.ledger[case_id] = outcome
            self._enforce_budget()
            return outcome

        assert isinstance(result, MovingServiceQuestionResponseV4)
        state.append(CaseState.AWAITING_HUMAN_REVIEW)
        evidence_document = {
            "evaluation_set_id": SET_ID,
            "runner_id": RUNNER_ID,
            "case_id": case_id,
            "synthetic": True,
            "response": result.model_dump(mode="json"),
        }
        evidence_digest = _digest(evidence_document)
        self.validated_evidence[case_id] = evidence_document
        if defer_human_review:
            outcome = CaseOutcome(
                evaluation_set_id=SET_ID, runner_id=RUNNER_ID, case_id=case_id,
                synthetic=True, state_history=tuple(state), deterministic_eligibility="generate",
                provider_request_expected=True, token_preflight_count=1,
                generation_attempt_count=1, retry_count=0, transport_result="succeeded",
                pydantic_validation_result=True, semantic_validation_result=True,
                prose_validation_result=True, ordered_prose_violation_codes=(),
                bounded_rejected_prose_diagnostics=(), fallback_selected=False,
                fallback_version=None, fallback_question_id=None,
                suggestion_count=len(result.suggestions),
                selected_category=result.suggestions[0].selected_missing_information_category.value,
                requires_user_confirmation=result.suggestions[0].requires_user_confirmation,
                expected_empty_correctness=None, human_review_applicable=True,
                human_review_decision=None, grounding_accurate=None, invented_user_fact=None,
                irrelevant_detail=None, modality_overstatement=None,
                service_selection_overstatement=None, clarity_score=None,
                usefulness_score=None, fallback_comparison=None,
                final_case_disposition=CaseDisposition.AWAITING_HUMAN_REVIEW,
                deterministic_request_sha256=triple[0], canonical_attempt_sha256=triple[1],
                provider_fingerprint=triple[2], preflight_audit_sha256=preflight_digest,
                generation_audit_sha256=generation_digest,
                validated_response_evidence_sha256=evidence_digest,
                human_review_sha256=None, evidence_deletion_sha256=None,
                closure_sha256=closure_digest, response_evidence_deleted=False,
                unauthorized_behavior=False, synthetic_input_tokens=tokens,
                synthetic_conservative_cost_usd=cost,
            )
            self.ledger[case_id] = outcome
            self._enforce_budget()
            return outcome
        review = plan.review
        if review is None:
            raise EvaluationRunnerError("validated response lacks mandatory human review")
        review_digest = _digest({
            "case_id": case_id, "synthetic": True,
            "response_evidence_sha256": evidence_digest,
            "review": review.model_dump(mode="json"),
        })
        state.extend((CaseState.HUMAN_REVIEW_COMPLETE, CaseState.CASE_COMPLETE))
        deletion_digest = _digest({
            "case_id": case_id, "response_evidence_sha256": evidence_digest,
            "deleted": True, "response_content_retained": False, "synthetic": True,
        })
        suggestion = result.suggestions[0]
        outcome = CaseOutcome(
            evaluation_set_id=SET_ID, runner_id=RUNNER_ID, case_id=case_id,
            synthetic=True, state_history=tuple(state), deterministic_eligibility="generate",
            provider_request_expected=True, token_preflight_count=1,
            generation_attempt_count=1, retry_count=0, transport_result="succeeded",
            pydantic_validation_result=True, semantic_validation_result=True,
            prose_validation_result=True, ordered_prose_violation_codes=(),
            bounded_rejected_prose_diagnostics=(), fallback_selected=False,
            fallback_version=None, fallback_question_id=None,
            suggestion_count=len(result.suggestions),
            selected_category=suggestion.selected_missing_information_category.value,
            requires_user_confirmation=suggestion.requires_user_confirmation,
            expected_empty_correctness=None, human_review_applicable=True,
            human_review_decision=review.decision,
            grounding_accurate=review.grounding_accurate,
            invented_user_fact=review.invented_user_fact,
            irrelevant_detail=review.irrelevant_detail,
            modality_overstatement=review.modality_overstatement,
            service_selection_overstatement=review.service_selection_overstatement,
            clarity_score=review.clarity_score, usefulness_score=review.usefulness_score,
            fallback_comparison=review.fallback_comparison,
            final_case_disposition=(CaseDisposition.PASSED if review.decision is ReviewDecision.APPROVE
                                    else CaseDisposition.HUMAN_REJECTED),
            deterministic_request_sha256=triple[0], canonical_attempt_sha256=triple[1],
            provider_fingerprint=triple[2], preflight_audit_sha256=preflight_digest,
            generation_audit_sha256=generation_digest,
            validated_response_evidence_sha256=evidence_digest,
            human_review_sha256=review_digest, evidence_deletion_sha256=deletion_digest,
            closure_sha256=closure_digest, response_evidence_deleted=True,
            unauthorized_behavior=False, synthetic_input_tokens=tokens,
            synthetic_conservative_cost_usd=cost,
        )
        self.ledger[case_id] = outcome
        self._enforce_budget()
        return outcome

    def _request_for_case_bound(self, case: Mapping[str, object]) -> MovingServiceQuestionRequestV4:
        from freeze_v4_formal_evaluation_set import _request_for_case
        return _request_for_case(case)

    def _failure_outcome(
        self, case_id: str, identity: Mapping[str, object], state: list[CaseState],
        result: str, preflight_digest: str, tokens: int, cost: str,
        *, generation_count: int,
    ) -> CaseOutcome:
        return CaseOutcome(
            evaluation_set_id=SET_ID, runner_id=RUNNER_ID, case_id=case_id,
            synthetic=True, state_history=tuple(state), deterministic_eligibility="generate",
            provider_request_expected=True, token_preflight_count=1,
            generation_attempt_count=generation_count, retry_count=0,
            transport_result=result, pydantic_validation_result=None,
            semantic_validation_result=None, prose_validation_result=None,
            ordered_prose_violation_codes=(), bounded_rejected_prose_diagnostics=(),
            fallback_selected=False, fallback_version=None, fallback_question_id=None,
            suggestion_count=0, selected_category=None, requires_user_confirmation=None,
            expected_empty_correctness=None, human_review_applicable=False,
            human_review_decision=None, grounding_accurate=None, invented_user_fact=None,
            irrelevant_detail=None, modality_overstatement=None,
            service_selection_overstatement=None, clarity_score=None,
            usefulness_score=None, fallback_comparison=None,
            final_case_disposition=CaseDisposition.TRANSPORT_FAILURE,
            deterministic_request_sha256=str(identity["deterministic_request_sha256"]),
            canonical_attempt_sha256=str(identity["canonical_attempt_sha256"]),
            provider_fingerprint=str(identity["provider_fingerprint"]),
            preflight_audit_sha256=preflight_digest,
            generation_audit_sha256=_digest({"case_id": case_id, "transport_result": result,
                                             "synthetic": True}),
            validated_response_evidence_sha256=None, human_review_sha256=None,
            evidence_deletion_sha256=None,
            closure_sha256=_digest({"case_id": case_id, "closed": True,
                                    "transport_result": result, "synthetic": True}),
            response_evidence_deleted=False, unauthorized_behavior=False,
            synthetic_input_tokens=tokens, synthetic_conservative_cost_usd=cost,
        )

    def run_all(self) -> FinalEvaluationReport:
        for case_id in tuple(GENERATION_CASE_IDS[:6]) + EMPTY_CASE_IDS + tuple(GENERATION_CASE_IDS[6:]):
            self.run_case(case_id)
        if len(self.ledger) != 10:
            raise EvaluationRunnerError("formal evaluation requires exactly ten outcomes")
        return score_outcomes(tuple(self.ledger.values()))


def score_outcomes(outcomes: tuple[CaseOutcome, ...]) -> FinalEvaluationReport:
    by_id = {item.case_id: item for item in outcomes}
    expected_ids = tuple(f"eval-v4-{index:02d}" for index in range(1, 11))
    if set(by_id) != set(expected_ids) or len(outcomes) != 10:
        raise EvaluationRunnerError("report requires one unique outcome for every frozen case")
    generations = sum(item.generation_attempt_count for item in outcomes)
    preflights = sum(item.token_preflight_count for item in outcomes)
    retries = sum(item.retry_count for item in outcomes)
    synthetic_spend = sum(
        Decimal(item.synthetic_conservative_cost_usd or "0") for item in outcomes
    )
    aggregate_count_violation = generations > 8 or preflights > 8 or retries != 0
    if synthetic_spend > Decimal("0.24"):
        raise EvaluationRunnerError("aggregate provider spend budget exceeded")
    generation = [by_id[case_id] for case_id in GENERATION_CASE_IDS]
    reviews = [item for item in generation if item.human_review_applicable]
    structural_passes = sum(item.pydantic_validation_result is True for item in generation)
    semantic_passes = sum(item.semantic_validation_result is True for item in generation)
    prose_passes = sum(item.prose_validation_result is True for item in generation)
    transport_failures = sum(item.final_case_disposition is CaseDisposition.TRANSPORT_FAILURE
                             for item in outcomes)
    invented = sum(item.invented_user_fact is True for item in outcomes)
    grounding = sum(item.grounding_accurate is False for item in outcomes)
    modality = sum(item.modality_overstatement is True for item in outcomes)
    selection = sum(item.service_selection_overstatement is True for item in outcomes)
    hard_prose = sum(bool(HARD_PROSE_CODES.intersection(item.ordered_prose_violation_codes))
                     for item in outcomes)
    empty_correct = all(_empty_outcome_is_exact(by_id[case_id]) for case_id in EMPTY_CASE_IDS)
    unauthorized = (
        sum(item.unauthorized_behavior for item in outcomes)
        + (0 if empty_correct else 1)
        + int(aggregate_count_violation)
    )
    structural_failures = sum(
        item.pydantic_validation_result is False for item in generation
    )
    semantic_failures = sum(
        item.semantic_validation_result is False for item in generation
    )
    hard_failures = (
        structural_failures + semantic_failures + invented + grounding
        + modality + selection + hard_prose + unauthorized + retries
    )
    hard_pass = hard_failures == 0
    clarity = [item.clarity_score for item in reviews if item.clarity_score is not None]
    usefulness = [item.usefulness_score for item in reviews if item.usefulness_score is not None]
    clarity_average = _average(clarity)
    usefulness_average = _average(usefulness)
    distribution: dict[str, Mapping[str, object]] = {}
    comparison_values = [item.fallback_comparison for item in reviews if item.fallback_comparison]
    for value in FALLBACK_COMPARISONS:
        count = comparison_values.count(value)
        distribution[value] = {"count": count, "percentage": _percentage(count, len(comparison_values))}
    equivalent_or_better = sum(value in EQUIVALENT_OR_BETTER for value in comparison_values)
    equivalent_percentage = _percentage(equivalent_or_better, len(comparison_values)) if comparison_values else None
    better_percentage = (
        _percentage(sum(value in {"materially_better", "slightly_better"}
                        for value in comparison_values), len(comparison_values))
        if comparison_values else None
    )
    equivalent_only_percentage = (
        _percentage(comparison_values.count("equivalent"), len(comparison_values))
        if comparison_values else None
    )
    worse_percentage = (
        _percentage(sum(value in {"slightly_worse", "materially_worse"}
                        for value in comparison_values), len(comparison_values))
        if comparison_values else None
    )
    quality_pass = (
        len(reviews) == 8
        and all(item.human_review_decision is ReviewDecision.APPROVE for item in reviews)
        and clarity_average is not None and Decimal(clarity_average) >= Decimal("4.0")
        and usefulness_average is not None and Decimal(usefulness_average) >= Decimal("4.0")
        and distribution["materially_worse"]["count"] == 0
        and equivalent_percentage is not None and Decimal(equivalent_percentage) >= Decimal("70")
        and transport_failures == 0
    )
    if not hard_pass:
        disposition = "fail"
    elif quality_pass and empty_correct:
        disposition = "graduate"
    else:
        disposition = "remain_experimental"
    table = tuple({
        "case_id": case_id,
        "deterministic_eligibility": by_id[case_id].deterministic_eligibility,
        "transport_result": by_id[case_id].transport_result,
        "automated_validation": (
            "validated" if by_id[case_id].prose_validation_result is True
            else "rejected" if by_id[case_id].final_case_disposition is CaseDisposition.AUTOMATED_REJECTED
            else "not_applicable"
        ),
        "pydantic_validation": by_id[case_id].pydantic_validation_result,
        "semantic_validation": by_id[case_id].semantic_validation_result,
        "prose_validation": by_id[case_id].prose_validation_result,
        "prose_violation_codes": by_id[case_id].ordered_prose_violation_codes,
        "fallback_selected": by_id[case_id].fallback_selected,
        "fallback_version": by_id[case_id].fallback_version,
        "fallback_question_id": by_id[case_id].fallback_question_id,
        "suggestion_count": by_id[case_id].suggestion_count,
        "selected_category": by_id[case_id].selected_category,
        "requires_user_confirmation": by_id[case_id].requires_user_confirmation,
        "human_review_decision": by_id[case_id].human_review_decision,
        "grounding_accurate": by_id[case_id].grounding_accurate,
        "invented_user_fact": by_id[case_id].invented_user_fact,
        "modality_overstatement": by_id[case_id].modality_overstatement,
        "service_selection_overstatement": by_id[case_id].service_selection_overstatement,
        "clarity_score": by_id[case_id].clarity_score,
        "usefulness_score": by_id[case_id].usefulness_score,
        "fallback_comparison": by_id[case_id].fallback_comparison,
        "final_case_disposition": by_id[case_id].final_case_disposition,
        "outcome_sha256": _digest(by_id[case_id].model_dump(mode="json")),
    } for case_id in expected_ids)
    return FinalEvaluationReport(
        evaluation_set_id=SET_ID, runner_id=RUNNER_ID, runner_version=RUNNER_VERSION,
        synthetic_rehearsal=True,
        bounded_evaluation_statement=(
            "This is a bounded product-readiness evaluation, not a statistically "
            "representative reliability study."
        ),
        frozen_v4_manifest_sha256=FROZEN_V4_MANIFEST,
        execution_budget_sha256=EXECUTION_BUDGET_SHA256,
        evaluation_manifest_sha256=EVALUATION_MANIFEST_SHA256,
        case_ids=expected_ids, case_result_table=table,
        deterministic_empty_results=sum(item.deterministic_eligibility == "empty" for item in outcomes),
        generation_attempts_used=generations, token_preflights_used=preflights,
        retries=retries, synthetic_provider_cost_usd=f"{synthetic_spend:.7f}",
        provider_transport_failure_count=transport_failures,
        structural_pass_rate=_percentage(structural_passes, 8),
        semantic_pass_rate=_percentage(semantic_passes, 8),
        prose_pass_rate=_percentage(prose_passes, 8),
        hard_gate_failure_count=hard_failures, invented_fact_count=invented,
        grounding_failure_count=grounding, modality_overstatement_count=modality,
        service_selection_overstatement_count=selection,
        unauthorized_behavior_count=unauthorized,
        average_clarity=clarity_average, average_usefulness=usefulness_average,
        fallback_comparison_distribution=distribution,
        better_than_fallback_percentage=better_percentage,
        equivalent_to_fallback_percentage=equivalent_only_percentage,
        worse_than_fallback_percentage=worse_percentage,
        equivalent_or_better_percentage=equivalent_percentage,
        expected_empty_correctness=empty_correct,
        hard_gate_result="pass" if hard_pass else "fail",
        quality_gate_result="pass" if quality_pass else "fail",
        final_disposition=disposition,
    )


LEDGER_VERSION = 2
JOURNAL_VERSION = 1
REPORT_SERIALIZATION_VERSION = 1

GENESIS_SHA256 = _digest({
    "journal_version": JOURNAL_VERSION,
    "evaluation_set_id": SET_ID,
    "evaluation_manifest_sha256": EVALUATION_MANIFEST_SHA256,
    "runner_id": RUNNER_ID,
    "runner_version": RUNNER_VERSION,
    "execution_budget_sha256": EXECUTION_BUDGET_SHA256,
})


def _atomic_json(path: Path, document: object) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = _canonical(document)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)
    directory = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)
    return hashlib.sha256(data).hexdigest()


@contextmanager
def _ledger_lock(root: Path):
    root.mkdir(parents=True, exist_ok=True)
    lock_path = root / "ledger.lock"
    with lock_path.open("a+b") as handle:
        os.chmod(lock_path, 0o600)
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        yield
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


class DurableEvaluationLedger:
    """Journal-backed, local-only synthetic evaluation state shared across processes."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.ledger_path = root / "ledger.json"
        self.journal_path = root / "transition-journal.json"
        self.report_path = root / "final-report.json"

    def _initial_document(self) -> dict[str, object]:
        identities = {
            item["case_id"]: item
            for item in json.loads((PACKAGE_ROOT / "request-identities.json").read_text())[
                "request_identities"
            ]
        }
        return {
            "ledger_version": LEDGER_VERSION,
            "evaluation_set_id": SET_ID,
            "evaluation_manifest_sha256": EVALUATION_MANIFEST_SHA256,
            "runner_id": RUNNER_ID,
            "runner_version": RUNNER_VERSION,
            "frozen_v4_manifest_sha256": FROZEN_V4_MANIFEST,
            "execution_budget_sha256": EXECUTION_BUDGET_SHA256,
            "journal_genesis_sha256": GENESIS_SHA256,
            "journal_terminal_sha256": GENESIS_SHA256,
            "journal_transition_count": 0,
            "synthetic": True,
            "spending_authorized": False,
            "cases": {
                case_id: {
                    "case_id": case_id,
                    "deterministic_case_input_sha256": identities[case_id][
                        "deterministic_case_input_sha256"
                    ],
                    "provider_request_expected": identities[case_id][
                        "provider_request_expected"
                    ],
                    "current_state": CaseState.PENDING,
                    "preflight_attempts_consumed": 0,
                    "generation_attempts_consumed": 0,
                    "retry_count": 0,
                    "terminal": False,
                    "outcome": None,
                    "outcome_sha256": None,
                    "preflight_artifact_sha256": None,
                    "generation_audit_sha256": None,
                    "validated_response_evidence_sha256": None,
                    "human_review_sha256": None,
                    "evidence_deletion_sha256": None,
                    "deletion_transaction_id": None,
                    "closure_sha256": None,
                }
                for case_id in (tuple(GENERATION_CASE_IDS[:6]) + EMPTY_CASE_IDS
                                + tuple(GENERATION_CASE_IDS[6:]))
            },
        }

    def _initial_journal(self) -> dict[str, object]:
        return {
            "journal_version": JOURNAL_VERSION,
            "evaluation_set_id": SET_ID,
            "evaluation_manifest_sha256": EVALUATION_MANIFEST_SHA256,
            "runner_id": RUNNER_ID,
            "runner_version": RUNNER_VERSION,
            "execution_budget_sha256": EXECUTION_BUDGET_SHA256,
            "genesis_sha256": GENESIS_SHA256,
            "transitions": [],
        }

    def initialize(self) -> Mapping[str, object]:
        verify_package()
        with _ledger_lock(self.root):
            if self.ledger_path.exists():
                return self._load_unlocked()
            stale = [
                item for item in self.root.rglob("*")
                if item.is_file() and item.name != "ledger.lock"
            ]
            if stale:
                raise EvaluationRunnerError("stale synthetic evaluation state requires recovery")
            document = self._initial_document()
            _atomic_json(self.journal_path, self._initial_journal())
            _atomic_json(self.ledger_path, document)
            return document

    def load(self) -> Mapping[str, object]:
        with _ledger_lock(self.root):
            return self._load_unlocked()

    def _load_unlocked(self) -> dict[str, object]:
        if not self.ledger_path.exists():
            raise EvaluationRunnerError("formal evaluation ledger is not initialized")
        try:
            document = json.loads(self.ledger_path.read_text())
        except (OSError, json.JSONDecodeError) as error:
            raise EvaluationRunnerError("formal evaluation ledger is malformed") from error
        expected = {
            "ledger_version": LEDGER_VERSION,
            "evaluation_set_id": SET_ID,
            "evaluation_manifest_sha256": EVALUATION_MANIFEST_SHA256,
            "runner_id": RUNNER_ID,
            "runner_version": RUNNER_VERSION,
            "frozen_v4_manifest_sha256": FROZEN_V4_MANIFEST,
            "execution_budget_sha256": EXECUTION_BUDGET_SHA256,
            "journal_genesis_sha256": GENESIS_SHA256,
            "synthetic": True,
            "spending_authorized": False,
        }
        if any(document.get(key) != value for key, value in expected.items()):
            raise EvaluationRunnerError("formal evaluation ledger identity mismatch")
        projected, terminal_digest, transition_count, pending_recoveries = (
            self._replay_journal_unlocked()
        )
        if pending_recoveries:
            raise EvaluationRunnerError("authenticated recovery is prepared but incomplete")
        if (document.get("journal_terminal_sha256") != terminal_digest
                or document.get("journal_transition_count") != transition_count
                or document.get("cases") != projected):
            raise EvaluationRunnerError("ledger projection disagrees with authenticated history")
        cases = document.get("cases")
        expected_ids = {f"eval-v4-{index:02d}" for index in range(1, 11)}
        if not isinstance(cases, dict) or set(cases) != expected_ids:
            raise EvaluationRunnerError("formal evaluation ledger case inventory mismatch")
        identities = {
            item["case_id"]: item
            for item in json.loads((PACKAGE_ROOT / "request-identities.json").read_text())[
                "request_identities"
            ]
        }
        for case_id, record in cases.items():
            if (
                record.get("case_id") != case_id
                or record.get("deterministic_case_input_sha256")
                != identities[case_id]["deterministic_case_input_sha256"]
                or record.get("provider_request_expected")
                is not identities[case_id]["provider_request_expected"]
                or record.get("retry_count") != 0
            ):
                raise EvaluationRunnerError("formal evaluation ledger case binding mismatch")
            if set(record) != {
                "case_id", "deterministic_case_input_sha256", "provider_request_expected",
                "current_state", "preflight_attempts_consumed", "generation_attempts_consumed",
                "retry_count", "terminal", "outcome", "outcome_sha256",
                "preflight_artifact_sha256", "generation_audit_sha256",
                "validated_response_evidence_sha256", "human_review_sha256",
                "evidence_deletion_sha256", "deletion_transaction_id", "closure_sha256",
            }:
                raise EvaluationRunnerError("formal evaluation ledger case schema mismatch")
            if record.get("preflight_artifact_sha256"):
                self._validate_preflight_artifact(case_id, record)
            outcome_document = record.get("outcome")
            if outcome_document is not None:
                outcome = CaseOutcome.model_validate(outcome_document)
                if outcome.case_id != case_id:
                    raise EvaluationRunnerError("ledger outcome case mismatch")
                if record.get("outcome_sha256") != _digest(outcome.model_dump(mode="json")):
                    raise EvaluationRunnerError("ledger outcome digest mismatch")
                if (
                    outcome.provider_request_expected
                    is not identities[case_id]["provider_request_expected"]
                    or outcome.token_preflight_count
                    != record.get("preflight_attempts_consumed")
                    or outcome.generation_attempt_count
                    != record.get("generation_attempts_consumed")
                    or outcome.retry_count != record.get("retry_count")
                    or outcome.state_history[-1] != record.get("current_state")
                    or (CaseState.CASE_COMPLETE in outcome.state_history)
                    is not record.get("terminal")
                    or outcome.validated_response_evidence_sha256
                    != record.get("validated_response_evidence_sha256")
                    or outcome.human_review_sha256 != record.get("human_review_sha256")
                    or outcome.evidence_deletion_sha256
                    != record.get("evidence_deletion_sha256")
                    or outcome.generation_audit_sha256
                    != record.get("generation_audit_sha256")
                ):
                    raise EvaluationRunnerError("ledger outcome semantic binding mismatch")
                if identities[case_id]["provider_request_expected"]:
                    if any(
                        getattr(outcome, key) != identities[case_id][key]
                        for key in (
                            "deterministic_request_sha256",
                            "canonical_attempt_sha256",
                            "provider_fingerprint",
                        )
                    ):
                        raise EvaluationRunnerError("ledger request identity mismatch")
                elif not _empty_outcome_is_exact(outcome):
                    raise EvaluationRunnerError("ledger deterministic empty outcome mismatch")
                evidence_path = self.root / "evidence" / f"{case_id}.json"
                review_path = self.root / "reviews" / f"{case_id}.json"
                deletion_path = self.root / "deletions" / f"{case_id}.json"
                evidence_digest = record.get("validated_response_evidence_sha256")
                review_digest = record.get("human_review_sha256")
                deletion_digest = record.get("evidence_deletion_sha256")
                if evidence_digest and not outcome.response_evidence_deleted:
                    if (not evidence_path.exists()
                            or hashlib.sha256(evidence_path.read_bytes()).hexdigest()
                            != evidence_digest):
                        raise EvaluationRunnerError("ledger evidence artifact mismatch")
                if review_digest:
                    if (not review_path.exists()
                            or hashlib.sha256(review_path.read_bytes()).hexdigest() != review_digest):
                        raise EvaluationRunnerError("ledger review artifact mismatch")
                    review_document = json.loads(review_path.read_text())
                    if (set(review_document) != {
                            "evaluation_set_id", "runner_id", "case_id", "synthetic",
                            "reviewer", "validated_response_evidence_sha256", "review",
                        }
                            or review_document.get("synthetic") is not True
                            or review_document.get("evaluation_set_id") != SET_ID
                            or review_document.get("runner_id") != RUNNER_ID
                            or review_document.get("case_id") != case_id
                            or review_document.get("validated_response_evidence_sha256")
                            != evidence_digest):
                        raise EvaluationRunnerError("ledger review binding mismatch")
                    review = HumanReview.model_validate(review_document.get("review"))
                    if (review_document.get("reviewer") != outcome.human_review_reviewer
                            or review.decision != outcome.human_review_decision
                            or review.grounding_accurate != outcome.grounding_accurate
                            or review.invented_user_fact != outcome.invented_user_fact
                            or review.irrelevant_detail != outcome.irrelevant_detail
                            or review.modality_overstatement != outcome.modality_overstatement
                            or review.service_selection_overstatement
                            != outcome.service_selection_overstatement
                            or review.clarity_score != outcome.clarity_score
                            or review.usefulness_score != outcome.usefulness_score
                            or review.fallback_comparison != outcome.fallback_comparison):
                        raise EvaluationRunnerError("review artifact disagrees with case outcome")
                if deletion_digest:
                    if (not deletion_path.exists()
                            or hashlib.sha256(deletion_path.read_bytes()).hexdigest()
                            != deletion_digest):
                        raise EvaluationRunnerError("ledger deletion artifact mismatch")
                    deletion = json.loads(deletion_path.read_text())
                    if ("response" in deletion
                            or deletion.get("response_content_retained") is not False
                            or deletion.get("validated_response_evidence_sha256") != evidence_digest
                            or deletion.get("human_review_sha256") != review_digest):
                        raise EvaluationRunnerError("ledger deletion binding or privacy mismatch")
                    if evidence_path.exists():
                        raise EvaluationRunnerError("deleted evidence remains present")
                if record.get("terminal"):
                    self._validate_closure_artifact(case_id, record, outcome)
                if record.get("generation_audit_sha256"):
                    audit_path = self.root / "audits" / f"{case_id}.json"
                    if (not audit_path.exists()
                            or hashlib.sha256(audit_path.read_bytes()).hexdigest()
                            != record["generation_audit_sha256"]
                            or _digest(json.loads(audit_path.read_text()))
                            != _digest(self._generation_audit_document(outcome))):
                        raise EvaluationRunnerError("generation audit artifact mismatch")
        self._reconcile_budget(document)
        self._validate_deletion_transactions(cases)
        return document

    def _validate_deletion_transactions(self, cases: Mapping[str, object]) -> None:
        paths = sorted((self.root / "transactions").glob("*-deletion.json"))
        seen: set[str] = set()
        for path in paths:
            transaction = json.loads(path.read_text())
            case_id = transaction.get("case_id")
            if case_id not in cases or case_id in seen:
                raise EvaluationRunnerError("deletion transaction case inventory mismatch")
            seen.add(str(case_id))
            self._validate_deletion_transaction(transaction, cases, path=path)
        expected_reviewed = {
            case_id for case_id, record in cases.items()
            if record.get("terminal")
            and record.get("outcome")
            and record["outcome"].get("human_review_applicable") is True
        }
        if seen != expected_reviewed:
            raise EvaluationRunnerError("deletion transaction terminal inventory mismatch")

    def _validate_deletion_transaction(
        self, transaction: Mapping[str, object], cases: Mapping[str, object], *,
        path: Path | None,
        observed: Mapping[str, object] | None = None,
        deletion_transition: Mapping[str, object] | None = None,
        lookup_transition: bool = True,
    ) -> None:
        """Validate canonical transaction content and its state-specific lifecycle."""
        if path is not None and (not path.exists()
                or _digest(json.loads(path.read_text())) != _digest(transaction)):
            raise EvaluationRunnerError("deletion transaction canonical content mismatch")
        base_keys = {
            "transaction_version", "evaluation_set_id", "evaluation_manifest_sha256",
            "runner_id", "runner_version", "case_id", "state",
            "validated_response_evidence_sha256", "human_review_sha256",
            "intended_deletion_sha256", "previous_case_state_sha256",
            "prepared_event_id", "transaction_id",
        }
        extra_by_state = {
            "prepared": set(),
            "removal_prepared": {"removal_prepared_event_id"},
            "evidence_removed": {"removal_prepared_event_id", "evidence_removed_event_id"},
            "committed": {
                "removal_prepared_event_id", "evidence_removed_event_id",
                "deletion_sha256", "closure_sha256", "deletion_transition_sha256",
                "committed_event_id",
            },
        }
        state = transaction.get("state")
        if state not in extra_by_state or set(transaction) != base_keys | extra_by_state[state]:
            raise EvaluationRunnerError("deletion transaction schema mismatch")
        case_id = transaction.get("case_id")
        record = cases.get(str(case_id))
        if not isinstance(record, dict):
            raise EvaluationRunnerError("deletion transaction case mismatch")
        evidence_path = self.root / "evidence" / f"{case_id}.json"
        review_path = self.root / "reviews" / f"{case_id}.json"
        deletion_path = self.root / "deletions" / f"{case_id}.json"
        evidence_digest = transaction.get("validated_response_evidence_sha256")
        review_digest = transaction.get("human_review_sha256")
        if (transaction.get("transaction_version") != 1
                or transaction.get("evaluation_set_id") != SET_ID
                or transaction.get("evaluation_manifest_sha256")
                != EVALUATION_MANIFEST_SHA256
                or transaction.get("runner_id") != RUNNER_ID
                or transaction.get("runner_version") != RUNNER_VERSION
                or transaction.get("transaction_id")
                != self._deletion_transaction_id(transaction)
                or evidence_digest != record.get("validated_response_evidence_sha256")
                or review_digest != record.get("human_review_sha256")
                or transaction.get("prepared_event_id") != f"{case_id}:delete:prepared"
                or not review_path.exists()
                or hashlib.sha256(review_path.read_bytes()).hexdigest() != review_digest):
            raise EvaluationRunnerError("deletion transaction semantic binding mismatch")
        expected_deletion = {
            "evaluation_set_id": SET_ID, "runner_id": RUNNER_ID,
            "case_id": case_id, "synthetic": True,
            "validated_response_evidence_sha256": evidence_digest,
            "human_review_sha256": review_digest,
            "deleted": True, "response_content_retained": False,
        }
        intended = _digest(expected_deletion)
        if deletion_transition is None and lookup_transition:
            deletion_transition = self._deletion_transition_document(str(case_id))
        previous_digest = (
            deletion_transition["previous_case_state_sha256"]
            if deletion_transition is not None else _digest(record)
        )
        if (transaction.get("intended_deletion_sha256") != intended
                or transaction.get("previous_case_state_sha256") != previous_digest):
            raise EvaluationRunnerError("deletion transaction lifecycle binding mismatch")
        evidence_present = (
            bool(observed["evidence_present"]) if observed is not None
            else evidence_path.exists()
        )
        deletion_present = (
            bool(observed["deletion_present"]) if observed is not None
            else deletion_path.exists()
        )
        observed_evidence_digest = (
            observed.get("evidence_sha256") if observed is not None
            else (hashlib.sha256(evidence_path.read_bytes()).hexdigest()
                  if evidence_present else None)
        )
        observed_deletion_digest = (
            observed.get("deletion_sha256") if observed is not None
            else (hashlib.sha256(deletion_path.read_bytes()).hexdigest()
                  if deletion_present else None)
        )
        if evidence_present and observed_evidence_digest != evidence_digest:
            raise EvaluationRunnerError("deletion transaction evidence mismatch")
        if deletion_present and observed_deletion_digest != intended:
            raise EvaluationRunnerError("deletion transaction artifact mismatch")
        if state == "prepared":
            if not evidence_present or deletion_transition is not None:
                raise EvaluationRunnerError("prepared deletion transaction is inconsistent")
        elif state == "removal_prepared":
            if (not deletion_present or deletion_transition is not None
                    or transaction.get("removal_prepared_event_id")
                    != f"{case_id}:delete:removal_prepared"):
                raise EvaluationRunnerError("removal-prepared deletion is inconsistent")
        elif state == "evidence_removed":
            if (evidence_present or not deletion_present
                    or transaction.get("removal_prepared_event_id")
                    != f"{case_id}:delete:removal_prepared"
                    or transaction.get("evidence_removed_event_id")
                    != f"{case_id}:delete:evidence_removed"):
                raise EvaluationRunnerError("evidence-removed deletion is inconsistent")
        else:
            if (evidence_present or not deletion_present or not record.get("terminal")
                    or record.get("deletion_transaction_id") != transaction.get("transaction_id")
                    or transaction.get("deletion_sha256") != intended
                    or transaction.get("deletion_sha256")
                    != record.get("evidence_deletion_sha256")
                    or transaction.get("closure_sha256") != record.get("closure_sha256")
                    or deletion_transition is None
                    or transaction.get("deletion_transition_sha256")
                    != deletion_transition.get("transition_sha256")
                    or transaction.get("removal_prepared_event_id")
                    != f"{case_id}:delete:removal_prepared"
                    or transaction.get("evidence_removed_event_id")
                    != f"{case_id}:delete:evidence_removed"
                    or transaction.get("committed_event_id")
                    != f"{case_id}:delete:committed"):
                raise EvaluationRunnerError("committed deletion transaction is inconsistent")

    def _deletion_transition_document(self, case_id: str) -> Mapping[str, object] | None:
        journal = json.loads(self.journal_path.read_text())
        matches = [
            item for item in journal["transitions"]
            if item.get("case_id") == case_id
            and item.get("operation_type") == "response_evidence_deleted"
        ]
        if len(matches) > 1:
            raise EvaluationRunnerError("duplicate deletion transition")
        return matches[0] if matches else None

    def _replay_journal_unlocked(
        self,
    ) -> tuple[dict[str, object], str, int, dict[str, Mapping[str, object]]]:
        try:
            journal = json.loads(self.journal_path.read_text())
        except (OSError, json.JSONDecodeError) as error:
            raise EvaluationRunnerError("transition journal is missing or malformed") from error
        expected = self._initial_journal()
        if (set(journal) != set(expected)
                or any(journal.get(key) != value for key, value in expected.items()
                       if key != "transitions")):
            raise EvaluationRunnerError("transition journal genesis binding mismatch")
        transitions = journal.get("transitions")
        if not isinstance(transitions, list):
            raise EvaluationRunnerError("transition journal inventory is malformed")
        cases = self._initial_document()["cases"]
        prepared_recoveries: dict[str, Mapping[str, object]] = {}
        previous = GENESIS_SHA256
        allowed = {
            "deterministic_empty_completed", "preflight_completed",
            "generation_completed_validated", "generation_automated_rejected",
            "provider_failure_recorded", "human_review_recorded",
            "response_evidence_deleted", "recovery_prepared", "recovery_completed",
        }
        for sequence, item in enumerate(transitions, 1):
            transition_keys = {
                "journal_version", "evaluation_set_id", "runner_id", "runner_version",
                "transition_sequence", "case_id", "previous_transition_sha256",
                "previous_case_state_sha256", "new_case_state_sha256", "operation_type",
                "artifact_digests", "attempt_counters_before", "attempt_counters_after",
                "terminal_state", "bounded_metadata", "new_case_record", "transition_sha256",
            }
            if (not isinstance(item, dict) or set(item) != transition_keys
                    or item.get("transition_sequence") != sequence
                    or item.get("evaluation_set_id") != SET_ID
                    or item.get("runner_id") != RUNNER_ID
                    or item.get("runner_version") != RUNNER_VERSION):
                raise EvaluationRunnerError("transition journal sequence mismatch")
            digest = item.get("transition_sha256")
            unsigned = {key: value for key, value in item.items() if key != "transition_sha256"}
            if digest != _digest(unsigned) or item.get("previous_transition_sha256") != previous:
                raise EvaluationRunnerError("transition journal hash chain mismatch")
            if item.get("journal_version") != JOURNAL_VERSION or item.get("operation_type") not in allowed:
                raise EvaluationRunnerError("transition journal operation is invalid")
            case_id = item.get("case_id")
            if case_id not in cases:
                raise EvaluationRunnerError("transition journal case mismatch")
            old = cases[case_id]
            new = item.get("new_case_record")
            if (item.get("previous_case_state_sha256") != _digest(old)
                    or not isinstance(new, dict)
                    or item.get("new_case_state_sha256") != _digest(new)):
                raise EvaluationRunnerError("transition case-state digest mismatch")
            artifacts = item.get("artifact_digests")
            if not isinstance(artifacts, dict):
                raise EvaluationRunnerError("transition artifact bindings are malformed")
            self._validate_transition_semantics(
                item, old, new, cases=cases, prepared_recoveries=prepared_recoveries,
            )
            cases[case_id] = new
            previous = digest
        return cases, previous, len(transitions), prepared_recoveries

    def _validate_transition_semantics(
        self, transition: Mapping[str, object], old: Mapping[str, object],
        new: Mapping[str, object], *, cases: Mapping[str, object],
        prepared_recoveries: dict[str, Mapping[str, object]],
    ) -> None:
        operation = str(transition["operation_type"])
        expected_states = {
            "deterministic_empty_completed": (CaseState.PENDING, CaseState.CASE_COMPLETE),
            "preflight_completed": (CaseState.PENDING, CaseState.PREFLIGHT_COMPLETE),
            "generation_completed_validated": (CaseState.PREFLIGHT_COMPLETE, CaseState.AWAITING_HUMAN_REVIEW),
            "generation_automated_rejected": (CaseState.PREFLIGHT_COMPLETE, CaseState.CASE_COMPLETE),
            "provider_failure_recorded": (CaseState.PREFLIGHT_COMPLETE, CaseState.CASE_COMPLETE),
            "human_review_recorded": (CaseState.AWAITING_HUMAN_REVIEW, CaseState.HUMAN_REVIEW_COMPLETE),
            "response_evidence_deleted": (CaseState.HUMAN_REVIEW_COMPLETE, CaseState.CASE_COMPLETE),
            "recovery_prepared": (new.get("current_state"), new.get("current_state")),
            "recovery_completed": (new.get("current_state"), new.get("current_state")),
        }
        if operation not in expected_states:
            raise EvaluationRunnerError("case-scoped journal operation is invalid")
        before, after = expected_states[operation]
        if old.get("current_state") != before or new.get("current_state") != after:
            raise EvaluationRunnerError("transition state progression is invalid")
        if old.get("terminal") and operation not in {"recovery_prepared", "recovery_completed"}:
            raise EvaluationRunnerError("terminal case history cannot be extended")
        pre_before = old.get("preflight_attempts_consumed")
        gen_before = old.get("generation_attempts_consumed")
        pre_after = new.get("preflight_attempts_consumed")
        gen_after = new.get("generation_attempts_consumed")
        if operation == "preflight_completed":
            valid_counts = pre_before == 0 and pre_after == 1 and gen_before == gen_after == 0
        elif operation in {"generation_completed_validated", "generation_automated_rejected",
                           "provider_failure_recorded"}:
            valid_counts = pre_before == pre_after == 1 and gen_before == 0 and gen_after == 1
        else:
            valid_counts = pre_before == pre_after and gen_before == gen_after
        if not valid_counts or new.get("retry_count") != 0:
            raise EvaluationRunnerError("transition attempt counters are invalid")
        expected_before = {
            "preflights": old["preflight_attempts_consumed"],
            "generations": old["generation_attempts_consumed"],
            "retries": old["retry_count"],
        }
        expected_after = {
            "preflights": new["preflight_attempts_consumed"],
            "generations": new["generation_attempts_consumed"],
            "retries": new["retry_count"],
        }
        if (transition.get("attempt_counters_before") != expected_before
                or transition.get("attempt_counters_after") != expected_after
                or transition.get("terminal_state") is not new.get("terminal")):
            raise EvaluationRunnerError("transition metadata disagrees with case state")
        if operation == "recovery_prepared":
            event_id, basis = self._validate_recovery_prepared_transition(
                transition, old, new, cases
            )
            if event_id in prepared_recoveries:
                raise EvaluationRunnerError("duplicate recovery event preparation")
            prepared_recoveries[event_id] = {
                "transition": transition, "basis": basis,
            }
            return
        if operation == "recovery_completed":
            event_id = str(transition.get("bounded_metadata", {}).get("recovery_event_id"))
            prepared = prepared_recoveries.get(event_id)
            if prepared is None:
                raise EvaluationRunnerError("recovery completion lacks authenticated preparation")
            self._validate_recovery_transition(transition, old, new, prepared)
            del prepared_recoveries[event_id]
            return
        expected_artifacts = self._expected_transition_artifacts(operation, new)
        if transition.get("artifact_digests") != expected_artifacts:
            raise EvaluationRunnerError("transition operation artifact semantics are invalid")
        if transition.get("bounded_metadata") != {}:
            raise EvaluationRunnerError("non-recovery transition metadata must be empty")

    @staticmethod
    def _derive_recovery_classification(
        *, projection_repaired: bool, deletion_transaction_advanced: bool,
    ) -> str:
        if projection_repaired and deletion_transaction_advanced:
            return "combined_reconciliation"
        if projection_repaired:
            return "projection_reconciled"
        if deletion_transaction_advanced:
            return "deletion_transaction_committed"
        raise EvaluationRunnerError("recovery artifact describes no durable repair")

    def _validate_recovery_prepared_transition(
        self, transition: Mapping[str, object], old: Mapping[str, object],
        new: Mapping[str, object], cases: Mapping[str, Mapping[str, object]],
    ) -> tuple[str, Mapping[str, object]]:
        metadata = transition.get("bounded_metadata")
        artifacts = transition.get("artifact_digests")
        if (old != new or not isinstance(metadata, dict) or not isinstance(artifacts, dict)
                or set(metadata) != {"recovery_event_id"}
                or set(artifacts) != {"recovery_basis_sha256"}):
            raise EvaluationRunnerError("recovery preparation semantics are invalid")
        event_id = metadata.get("recovery_event_id")
        artifact_digest = artifacts.get("recovery_basis_sha256")
        if not isinstance(event_id, str) or not isinstance(artifact_digest, str):
            raise EvaluationRunnerError("recovery preparation lacks its basis")
        path = self.root / "recoveries" / f"{event_id}-basis.json"
        if (not path.exists()
                or hashlib.sha256(path.read_bytes()).hexdigest() != artifact_digest):
            raise EvaluationRunnerError("recovery basis is missing or changed")
        basis = json.loads(path.read_text())
        keys = {
            "recovery_basis_version", "evaluation_set_id",
            "evaluation_manifest_sha256", "runner_id", "runner_version", "case_id",
            "recovery_event_id", "prior_journal_terminal_sha256",
            "prior_journal_transition_count", "prior_ledger_projection",
            "prior_ledger_projection_sha256", "prior_case_record",
            "prior_case_state_sha256", "projection_repair_required",
            "deletion_transaction_before", "deletion_transaction_before_sha256",
            "deletion_transaction_state_before", "deletion_artifact_present_before",
            "deletion_artifact_sha256_before", "evidence_present_before",
            "evidence_sha256_before", "human_review_sha256", "closure_sha256_before",
            "attempt_counters",
        }
        if set(basis) != keys:
            raise EvaluationRunnerError("recovery basis schema is invalid")
        ledger = basis.get("prior_ledger_projection")
        prior_record = basis.get("prior_case_record")
        if not isinstance(ledger, dict) or not isinstance(prior_record, dict):
            raise EvaluationRunnerError("recovery basis projection is invalid")
        projection_repair_required = (
            ledger.get("cases", {}).get(transition["case_id"]) != old
            or ledger.get("journal_terminal_sha256")
            != transition.get("previous_transition_sha256")
            or ledger.get("journal_transition_count")
            != transition.get("transition_sequence") - 1
        )
        expected_counters = {
            "preflights": old["preflight_attempts_consumed"],
            "generations": old["generation_attempts_consumed"],
            "retries": old["retry_count"],
        }
        if (basis.get("recovery_basis_version") != 1
                or basis.get("evaluation_set_id") != SET_ID
                or basis.get("evaluation_manifest_sha256") != EVALUATION_MANIFEST_SHA256
                or basis.get("runner_id") != RUNNER_ID
                or basis.get("runner_version") != RUNNER_VERSION
                or basis.get("case_id") != transition.get("case_id")
                or basis.get("recovery_event_id") != event_id
                or basis.get("prior_journal_terminal_sha256")
                != transition.get("previous_transition_sha256")
                or basis.get("prior_journal_transition_count")
                != transition.get("transition_sequence") - 1
                or basis.get("prior_ledger_projection_sha256") != _digest(ledger)
                or prior_record != ledger.get("cases", {}).get(transition["case_id"])
                or basis.get("prior_case_state_sha256") != _digest(old)
                or basis.get("projection_repair_required") is not projection_repair_required
                or basis.get("attempt_counters") != expected_counters):
            raise EvaluationRunnerError("recovery basis semantic binding is invalid")
        transaction_before = basis.get("deletion_transaction_before")
        if transaction_before is None:
            if (basis.get("deletion_transaction_before_sha256") is not None
                    or basis.get("deletion_transaction_state_before") is not None):
                raise EvaluationRunnerError("recovery basis invents a transaction")
        else:
            if (not isinstance(transaction_before, dict)
                    or _digest(transaction_before)
                    != basis.get("deletion_transaction_before_sha256")
                    or transaction_before.get("state")
                    != basis.get("deletion_transaction_state_before")
                    or transaction_before.get("case_id") != transition.get("case_id")
                    or transaction_before.get("transaction_id")
                    != self._deletion_transaction_id(transaction_before)):
                raise EvaluationRunnerError("recovery transaction basis is invalid")
            journal = json.loads(self.journal_path.read_text())
            prefix_matches = [
                item for item in journal["transitions"]
                if item.get("case_id") == transition.get("case_id")
                and item.get("operation_type") == "response_evidence_deleted"
                and item.get("transition_sequence") < transition.get("transition_sequence")
            ]
            if len(prefix_matches) > 1:
                raise EvaluationRunnerError("recovery basis has duplicate deletion history")
            self._validate_deletion_transaction(
                transaction_before, cases, path=None,
                observed={
                    "evidence_present": basis.get("evidence_present_before"),
                    "evidence_sha256": basis.get("evidence_sha256_before"),
                    "deletion_present": basis.get("deletion_artifact_present_before"),
                    "deletion_sha256": basis.get("deletion_artifact_sha256_before"),
                },
                deletion_transition=prefix_matches[0] if prefix_matches else None,
                lookup_transition=False,
            )
        evidence_present = basis.get("evidence_present_before")
        deletion_present = basis.get("deletion_artifact_present_before")
        if (not isinstance(evidence_present, bool) or not isinstance(deletion_present, bool)
                or (evidence_present and basis.get("evidence_sha256_before")
                    != old.get("validated_response_evidence_sha256"))
                or (not evidence_present and basis.get("evidence_sha256_before") is not None)
                or (deletion_present and basis.get("deletion_artifact_sha256_before")
                    not in {old.get("evidence_deletion_sha256"),
                            transaction_before.get("intended_deletion_sha256")
                            if isinstance(transaction_before, dict) else None})
                or (not deletion_present
                    and basis.get("deletion_artifact_sha256_before") is not None)
                or basis.get("human_review_sha256") != old.get("human_review_sha256")
                or basis.get("closure_sha256_before") != old.get("closure_sha256")):
            raise EvaluationRunnerError("recovery basis lifecycle presence is invalid")
        expected_event_id = _digest({
            key: value for key, value in basis.items() if key != "recovery_event_id"
        })
        if event_id != expected_event_id:
            raise EvaluationRunnerError("recovery event identity is invalid")
        return event_id, basis

    def _validate_recovery_transition(
        self, transition: Mapping[str, object], old: Mapping[str, object],
        new: Mapping[str, object], prepared: Mapping[str, object],
    ) -> None:
        metadata = transition.get("bounded_metadata")
        artifacts = transition.get("artifact_digests")
        basis = prepared["basis"]
        prepared_transition = prepared["transition"]
        if (old != new or not isinstance(metadata, dict) or not isinstance(artifacts, dict)
                or set(metadata) != {"repair_classification", "recovery_event_id"}
                or set(artifacts) != {
                    "recovery_basis_sha256", "recovery_prepared_transition_sha256",
                    "recovery_completion_sha256",
                }):
            raise EvaluationRunnerError("recovery completion semantics are invalid")
        event_id = metadata.get("recovery_event_id")
        path = self.root / "recoveries" / f"{event_id}-completed.json"
        completion_digest = artifacts.get("recovery_completion_sha256")
        if (not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest()
                != completion_digest):
            raise EvaluationRunnerError("recovery completion artifact is missing or changed")
        completion = json.loads(path.read_text())
        expected_keys = {
            "recovery_completion_version", "evaluation_set_id",
            "evaluation_manifest_sha256", "runner_id", "runner_version", "case_id",
            "recovery_event_id", "recovery_basis_sha256",
            "recovery_prepared_transition_sha256", "post_case_state_sha256",
            "deletion_transaction_after", "deletion_transaction_after_sha256",
            "deletion_transaction_state_after", "evidence_present_after",
            "deletion_artifact_sha256", "repair_classification", "attempt_counters",
        }
        if set(completion) != expected_keys:
            raise EvaluationRunnerError("recovery completion schema is invalid")
        basis_digest = artifacts["recovery_basis_sha256"]
        transaction_before = basis.get("deletion_transaction_before")
        transaction_after = completion.get("deletion_transaction_after")
        transaction_advanced = _digest(transaction_before) != _digest(transaction_after)
        classification = self._derive_recovery_classification(
            projection_repaired=bool(basis.get("projection_repair_required")),
            deletion_transaction_advanced=transaction_advanced,
        )
        counters = {
            "preflights": new["preflight_attempts_consumed"],
            "generations": new["generation_attempts_consumed"],
            "retries": new["retry_count"],
        }
        if (event_id != basis.get("recovery_event_id")
                or artifacts["recovery_prepared_transition_sha256"]
                != prepared_transition.get("transition_sha256")
                or basis_digest != prepared_transition["artifact_digests"]["recovery_basis_sha256"]
                or completion.get("recovery_completion_version") != 1
                or completion.get("evaluation_set_id") != SET_ID
                or completion.get("evaluation_manifest_sha256") != EVALUATION_MANIFEST_SHA256
                or completion.get("runner_id") != RUNNER_ID
                or completion.get("runner_version") != RUNNER_VERSION
                or completion.get("case_id") != transition.get("case_id")
                or completion.get("recovery_event_id") != event_id
                or completion.get("recovery_basis_sha256") != basis_digest
                or completion.get("recovery_prepared_transition_sha256")
                != prepared_transition.get("transition_sha256")
                or completion.get("post_case_state_sha256") != _digest(new)
                or completion.get("attempt_counters") != counters
                or completion.get("evidence_present_after") is not False
                or completion.get("repair_classification") != classification
                or metadata.get("repair_classification") != classification):
            raise EvaluationRunnerError("recovery completion semantic binding is invalid")
        if transaction_after is None:
            if transaction_before is not None or any(completion.get(key) is not None for key in (
                "deletion_transaction_after_sha256", "deletion_transaction_state_after",
            )):
                raise EvaluationRunnerError("recovery completion transaction is invalid")
        elif (not isinstance(transaction_after, dict)
                or _digest(transaction_after) != completion.get("deletion_transaction_after_sha256")
                or transaction_after.get("state") != "committed"
                or completion.get("deletion_transaction_state_after") != "committed"):
            raise EvaluationRunnerError("recovery completion transaction is invalid")
        if transaction_after is not None:
            transaction_path = self.root / "transactions" / (
                f"{transition['case_id']}-deletion.json"
            )
            if (not transaction_path.exists()
                    or hashlib.sha256(transaction_path.read_bytes()).hexdigest()
                    != completion.get("deletion_transaction_after_sha256")):
                raise EvaluationRunnerError("recovery completion transaction changed")
        deletion_digest = completion.get("deletion_artifact_sha256")
        if deletion_digest is not None:
            deletion_path = self.root / "deletions" / f"{transition['case_id']}.json"
            if (not deletion_path.exists()
                    or hashlib.sha256(deletion_path.read_bytes()).hexdigest()
                    != deletion_digest):
                raise EvaluationRunnerError("recovery completion deletion artifact changed")

    def _expected_transition_artifacts(
        self, operation: str, record: Mapping[str, object],
    ) -> dict[str, object]:
        keys_by_operation = {
            "deterministic_empty_completed": ("outcome_sha256", "closure_sha256"),
            "preflight_completed": ("preflight_artifact_sha256",),
            "generation_completed_validated": (
                "preflight_artifact_sha256", "generation_audit_sha256",
                "validated_response_evidence_sha256", "outcome_sha256",
            ),
            "generation_automated_rejected": (
                "preflight_artifact_sha256", "generation_audit_sha256",
                "outcome_sha256", "closure_sha256",
            ),
            "provider_failure_recorded": (
                "preflight_artifact_sha256", "generation_audit_sha256",
                "outcome_sha256", "closure_sha256",
            ),
            "human_review_recorded": (
                "validated_response_evidence_sha256", "human_review_sha256",
                "outcome_sha256",
            ),
            "response_evidence_deleted": (
                "preflight_artifact_sha256", "generation_audit_sha256",
                "validated_response_evidence_sha256", "human_review_sha256",
                "evidence_deletion_sha256", "deletion_transaction_id",
                "outcome_sha256", "closure_sha256",
            ),
        }
        if operation == "recovery_completed":
            return {
                key: record[key] for key in (
                    "preflight_artifact_sha256", "generation_audit_sha256",
                    "validated_response_evidence_sha256", "human_review_sha256",
                    "evidence_deletion_sha256", "deletion_transaction_id",
                    "outcome_sha256", "closure_sha256",
                ) if record.get(key) is not None
            }
        keys = keys_by_operation.get(operation)
        if keys is None:
            raise EvaluationRunnerError("transition operation has no semantic specification")
        result = {key: record.get(key) for key in keys}
        if any(value is None for value in result.values()):
            raise EvaluationRunnerError("transition lacks a required lifecycle artifact")
        return result

    def _append_transition_unlocked(
        self, document: dict[str, object], *, operation: str, case_id: str | None,
        old_record: Mapping[str, object] | None = None,
        new_record: Mapping[str, object] | None = None,
        artifacts: Mapping[str, object] | None = None,
        metadata: Mapping[str, object] | None = None,
    ) -> str:
        journal = json.loads(self.journal_path.read_text())
        transitions = journal["transitions"]
        previous = transitions[-1]["transition_sha256"] if transitions else GENESIS_SHA256
        transition = {
            "journal_version": JOURNAL_VERSION,
            "evaluation_set_id": SET_ID,
            "runner_id": RUNNER_ID,
            "runner_version": RUNNER_VERSION,
            "transition_sequence": len(transitions) + 1,
            "case_id": case_id,
            "previous_transition_sha256": previous,
            "previous_case_state_sha256": _digest(old_record) if old_record is not None else None,
            "new_case_state_sha256": _digest(new_record) if new_record is not None else None,
            "operation_type": operation,
            "artifact_digests": dict(artifacts or {}),
            "attempt_counters_before": ({
                "preflights": old_record["preflight_attempts_consumed"],
                "generations": old_record["generation_attempts_consumed"],
                "retries": old_record["retry_count"],
            } if old_record is not None else None),
            "attempt_counters_after": ({
                "preflights": new_record["preflight_attempts_consumed"],
                "generations": new_record["generation_attempts_consumed"],
                "retries": new_record["retry_count"],
            } if new_record is not None else None),
            "terminal_state": new_record.get("terminal") if new_record is not None else None,
            "bounded_metadata": dict(metadata or {}),
            "new_case_record": dict(new_record) if new_record is not None else None,
        }
        transition["transition_sha256"] = _digest(transition)
        transitions.append(transition)
        _atomic_json(self.journal_path, journal)
        document["journal_terminal_sha256"] = transition["transition_sha256"]
        document["journal_transition_count"] = len(transitions)
        return transition["transition_sha256"]

    def _commit_case_transition(
        self, document: dict[str, object], case_id: str, old: Mapping[str, object],
        new: Mapping[str, object], operation: str, *, artifacts: Mapping[str, object] | None = None,
    ) -> None:
        expected_artifacts = self._expected_transition_artifacts(operation, new)
        if artifacts is not None and dict(artifacts) != expected_artifacts:
            raise EvaluationRunnerError("transition caller supplied wrong artifact bindings")
        self._append_transition_unlocked(
            document, operation=operation, case_id=case_id, old_record=old,
            new_record=new, artifacts=expected_artifacts,
        )
        document["cases"][case_id] = new
        self._save_unlocked(document)

    def _validate_preflight_artifact(self, case_id: str, record: Mapping[str, object]) -> None:
        path = self.root / "preflights" / f"{case_id}.json"
        digest = record.get("preflight_artifact_sha256")
        if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise EvaluationRunnerError("preflight artifact is missing or changed")
        artifact = json.loads(path.read_text())
        identity = next(item for item in json.loads(
            (PACKAGE_ROOT / "request-identities.json").read_text()
        )["request_identities"] if item["case_id"] == case_id)
        required = {
            "evaluation_set_id": SET_ID, "runner_id": RUNNER_ID,
            "runner_version": RUNNER_VERSION, "case_id": case_id,
            "deterministic_case_input_sha256": identity["deterministic_case_input_sha256"],
            "deterministic_request_sha256": identity["deterministic_request_sha256"],
            "canonical_attempt_sha256": identity["canonical_attempt_sha256"],
            "provider_fingerprint": identity["provider_fingerprint"],
            "synthetic": True, "token_preflight_attempted": True,
            "token_preflight_succeeded": True, "preflight_request_count": 1,
            "generation_request_count": 0, "retries": 0,
            "synthetic_event_id": f"{case_id}:preflight:1",
        }
        if (set(artifact) != set(required) | {
                "synthetic_input_tokens", "synthetic_conservative_cost_usd"
            } or any(artifact.get(key) != value for key, value in required.items())):
            raise EvaluationRunnerError("preflight artifact semantic binding mismatch")
        if (not isinstance(artifact.get("synthetic_input_tokens"), int)
                or artifact["synthetic_input_tokens"] <= 0
                or artifact["synthetic_input_tokens"] != 2700 + int(case_id[-2:]) * 11
                or artifact.get("synthetic_conservative_cost_usd")
                != f"{(Decimal(artifact['synthetic_input_tokens']) * Decimal('0.00000068')):.7f}"):
            raise EvaluationRunnerError("preflight artifact count or cost is invalid")

    def _validate_closure_artifact(
        self, case_id: str, record: Mapping[str, object], outcome: CaseOutcome,
    ) -> None:
        path = self.root / "closures" / f"{case_id}.json"
        digest = record.get("closure_sha256")
        if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise EvaluationRunnerError("case closure artifact is missing or changed")
        closure = json.loads(path.read_text())
        expected = {
            "evaluation_set_id": SET_ID, "runner_id": RUNNER_ID, "case_id": case_id,
            "synthetic": True,
            "deterministic_case_input_sha256": record["deterministic_case_input_sha256"],
            "provider_request_expected": record["provider_request_expected"],
            "preflight_artifact_sha256": record["preflight_artifact_sha256"],
            "generation_audit_sha256": record["generation_audit_sha256"],
            "validated_response_evidence_sha256":
                record["validated_response_evidence_sha256"],
            "human_review_sha256": record["human_review_sha256"],
            "evidence_deletion_sha256": record["evidence_deletion_sha256"],
            "deletion_transaction_id": record["deletion_transaction_id"],
            "terminal_reason": outcome.final_case_disposition,
            "preflight_attempts_consumed": record["preflight_attempts_consumed"],
            "generation_attempts_consumed": record["generation_attempts_consumed"],
            "retries": 0, "terminal_outcome_sha256": record["outcome_sha256"],
            "terminal": True, "reusable": False, "further_attempt_permitted": False,
        }
        if set(closure) != set(expected) or any(
            closure.get(key) != value for key, value in expected.items()
        ):
            raise EvaluationRunnerError("case closure semantic binding mismatch")
        if outcome.human_review_applicable:
            transaction_path = self.root / "transactions" / f"{case_id}-deletion.json"
            if not transaction_path.exists():
                raise EvaluationRunnerError("committed deletion transaction is missing")
            transaction = json.loads(transaction_path.read_text())
            if (transaction.get("state") != "committed"
                    or transaction.get("deletion_sha256")
                    != record["evidence_deletion_sha256"]
                    or transaction.get("closure_sha256") != digest):
                raise EvaluationRunnerError("committed deletion transaction binding mismatch")
        if not record["provider_request_expected"] and (
            closure["preflight_attempts_consumed"] != 0
            or closure["generation_attempts_consumed"] != 0
            or any(closure[key] is not None for key in (
                "preflight_artifact_sha256", "generation_audit_sha256",
                "validated_response_evidence_sha256", "human_review_sha256",
                "evidence_deletion_sha256", "deletion_transaction_id",
            ))
        ):
            raise EvaluationRunnerError("deterministic empty closure contains provider activity")
        if outcome.human_review_applicable and any(closure[key] is None for key in (
            "preflight_artifact_sha256", "generation_audit_sha256",
            "validated_response_evidence_sha256", "human_review_sha256",
            "evidence_deletion_sha256", "deletion_transaction_id",
        )):
            raise EvaluationRunnerError("reviewed closure lacks complete lifecycle bindings")
        if outcome.final_case_disposition in {
            CaseDisposition.AUTOMATED_REJECTED, CaseDisposition.TRANSPORT_FAILURE,
        } and (
            closure["preflight_artifact_sha256"] is None
            or closure["generation_audit_sha256"] is None
            or any(closure[key] is not None for key in (
                "validated_response_evidence_sha256", "human_review_sha256",
                "evidence_deletion_sha256", "deletion_transaction_id",
            ))
        ):
            raise EvaluationRunnerError("terminal machine closure lifecycle is invalid")

    def _reconcile_budget(self, document: Mapping[str, object]) -> None:
        records = list(document["cases"].values())  # type: ignore[union-attr]
        preflights = sum(item["preflight_attempts_consumed"] for item in records)
        generations = sum(item["generation_attempts_consumed"] for item in records)
        retries = sum(item["retry_count"] for item in records)
        if preflights > 8 or generations > 8 or retries != 0:
            raise EvaluationRunnerError("durable ledger budget reconciliation failed")
        for item in records:
            maximum = 1 if item["provider_request_expected"] else 0
            if (item["preflight_attempts_consumed"] > maximum
                    or item["generation_attempts_consumed"] > maximum):
                raise EvaluationRunnerError("per-case durable budget exceeded")

    def _save_unlocked(self, document: Mapping[str, object]) -> str:
        self._reconcile_budget(document)
        return _atomic_json(self.ledger_path, document)

    def _record_outcome(self, record: dict[str, object], outcome: CaseOutcome) -> None:
        serialized = outcome.model_dump(mode="json")
        record["outcome"] = serialized
        record["outcome_sha256"] = _digest(serialized)
        record["current_state"] = outcome.state_history[-1]
        record["closure_sha256"] = None
        record["validated_response_evidence_sha256"] = (
            outcome.validated_response_evidence_sha256
        )
        record["generation_audit_sha256"] = outcome.generation_audit_sha256
        record["human_review_sha256"] = outcome.human_review_sha256
        record["evidence_deletion_sha256"] = outcome.evidence_deletion_sha256
        record["terminal"] = outcome.state_history[-1] is CaseState.CASE_COMPLETE

    def _write_closure(self, record: dict[str, object], outcome: CaseOutcome) -> str:
        if not record["terminal"]:
            raise EvaluationRunnerError("closure requires a terminal case")
        closure = {
            "evaluation_set_id": SET_ID, "runner_id": RUNNER_ID,
            "case_id": outcome.case_id, "synthetic": True,
            "deterministic_case_input_sha256": record["deterministic_case_input_sha256"],
            "provider_request_expected": record["provider_request_expected"],
            "preflight_artifact_sha256": record["preflight_artifact_sha256"],
            "generation_audit_sha256": record["generation_audit_sha256"],
            "validated_response_evidence_sha256":
                record["validated_response_evidence_sha256"],
            "human_review_sha256": record["human_review_sha256"],
            "evidence_deletion_sha256": record["evidence_deletion_sha256"],
            "deletion_transaction_id": record["deletion_transaction_id"],
            "terminal_reason": outcome.final_case_disposition,
            "preflight_attempts_consumed": record["preflight_attempts_consumed"],
            "generation_attempts_consumed": record["generation_attempts_consumed"],
            "retries": record["retry_count"],
            "terminal_outcome_sha256": record["outcome_sha256"],
            "terminal": True, "reusable": False, "further_attempt_permitted": False,
        }
        digest = _atomic_json(self.root / "closures" / f"{outcome.case_id}.json", closure)
        record["closure_sha256"] = digest
        return digest

    def run_empty(self, case_id: str) -> CaseOutcome:
        if case_id not in EMPTY_CASE_IDS:
            raise EvaluationRunnerError("case is not a deterministic empty case")
        with _ledger_lock(self.root):
            document = self._load_unlocked()
            record = document["cases"][case_id]
            if record["current_state"] != CaseState.PENDING:
                raise EvaluationRunnerError("case cannot reopen or change eligibility")
            old = dict(record)
            new = dict(record)
            outcome = FormalEvaluationRunner().run_case(case_id)
            self._record_outcome(new, outcome)
            closure = self._write_closure(new, outcome)
            self._commit_case_transition(
                document, case_id, old, new, "deterministic_empty_completed",
                artifacts={"outcome_sha256": new["outcome_sha256"],
                           "closure_sha256": closure},
            )
            return outcome

    def run_preflight(self, case_id: str) -> Mapping[str, object]:
        if case_id not in GENERATION_CASE_IDS:
            raise EvaluationRunnerError("case is not generation eligible")
        with _ledger_lock(self.root):
            document = self._load_unlocked()
            record = document["cases"][case_id]
            if record["current_state"] != CaseState.PENDING or record["terminal"]:
                raise EvaluationRunnerError("preflight attempt already consumed or case terminal")
            runner = FormalEvaluationRunner()
            captured: list[MovingServiceProviderRequest] = []

            def constructor(**kwargs: object) -> MovingServiceProviderRequest:
                request = MovingServiceProviderRequest(**kwargs)
                captured.append(request)
                return request

            _, _, identity = bind_case(runner.cases[case_id], runner.metadata, constructor)
            expected = runner.identities[case_id]
            keys = ("deterministic_request_sha256", "canonical_attempt_sha256", "provider_fingerprint")
            if len(captured) != 1 or any(identity[key] != expected[key] for key in keys):
                raise EvaluationRunnerError("preflight request identity drifted")
            old = dict(record)
            result = {
                "evaluation_set_id": SET_ID,
                "runner_id": RUNNER_ID,
                "runner_version": RUNNER_VERSION,
                "case_id": case_id,
                "deterministic_case_input_sha256": expected["deterministic_case_input_sha256"],
                "deterministic_request_sha256": identity["deterministic_request_sha256"],
                "canonical_attempt_sha256": identity["canonical_attempt_sha256"],
                "provider_fingerprint": identity["provider_fingerprint"],
                "synthetic": True,
                "token_preflight_attempted": True,
                "token_preflight_succeeded": True,
                "preflight_request_count": 1,
                "generation_request_count": 0,
                "retries": 0,
                "synthetic_input_tokens": 2700 + int(case_id[-2:]) * 11,
                "synthetic_conservative_cost_usd": f"{(Decimal(2700 + int(case_id[-2:]) * 11) * Decimal('0.00000068')):.7f}",
                "synthetic_event_id": f"{case_id}:preflight:1",
            }
            artifact_digest = _atomic_json(self.root / "preflights" / f"{case_id}.json", result)
            new = dict(record)
            new["preflight_attempts_consumed"] = 1
            new["current_state"] = CaseState.PREFLIGHT_COMPLETE
            new["preflight_artifact_sha256"] = artifact_digest
            self._commit_case_transition(
                document, case_id, old, new, "preflight_completed",
                artifacts={"preflight_artifact_sha256": artifact_digest},
            )
            return result | {"preflight_artifact_sha256": artifact_digest}

    def run_generation(self, case_id: str, *, scenario: str = "nominal") -> CaseOutcome:
        if case_id not in GENERATION_CASE_IDS:
            raise EvaluationRunnerError("case is not generation eligible")
        with _ledger_lock(self.root):
            document = self._load_unlocked()
            record = document["cases"][case_id]
            if (record["current_state"] != CaseState.PREFLIGHT_COMPLETE
                    or record["generation_attempts_consumed"] != 0 or record["terminal"]):
                raise EvaluationRunnerError("generation attempt already consumed or case not ready")
            self._validate_preflight_artifact(case_id, record)
            old = dict(record)
            new = dict(record)
            new["generation_attempts_consumed"] = 1
            runner = FormalEvaluationRunner(scenario=scenario)
            outcome = runner.run_case(
                case_id, defer_human_review=True, preflight_already_consumed=True
            )
            preflight_artifact = json.loads(
                (self.root / "preflights" / f"{case_id}.json").read_text()
            )
            if (outcome.preflight_audit_sha256 != _digest({
                    "case_id": case_id, "synthetic": True,
                    "request_identity": (
                        outcome.deterministic_request_sha256,
                        outcome.canonical_attempt_sha256,
                        outcome.provider_fingerprint,
                    ),
                    "token_preflight_count": 1, "generation_count": 0, "retries": 0,
                    "input_tokens": preflight_artifact["synthetic_input_tokens"],
                    "conservative_cost_usd": preflight_artifact[
                        "synthetic_conservative_cost_usd"
                    ],
                })
                    or outcome.synthetic_input_tokens
                    != preflight_artifact["synthetic_input_tokens"]
                    or outcome.synthetic_conservative_cost_usd
                    != preflight_artifact["synthetic_conservative_cost_usd"]):
                raise EvaluationRunnerError("generation does not bind exact preflight artifact")
            if outcome.final_case_disposition is CaseDisposition.AWAITING_HUMAN_REVIEW:
                evidence = runner.validated_evidence[case_id]
                evidence_path = self.root / "evidence" / f"{case_id}.json"
                evidence_digest = _atomic_json(evidence_path, evidence)
                if evidence_digest != outcome.validated_response_evidence_sha256:
                    raise EvaluationRunnerError("validated response evidence digest mismatch")
            self._record_outcome(new, outcome)
            audit_document = self._generation_audit_document(outcome)
            audit_digest = _atomic_json(
                self.root / "audits" / f"{case_id}.json", audit_document
            )
            if audit_digest != outcome.generation_audit_sha256:
                raise EvaluationRunnerError("generation audit artifact identity mismatch")
            new["generation_audit_sha256"] = audit_digest
            if new["terminal"]:
                self._write_closure(new, outcome)
            operation = (
                "generation_completed_validated" if outcome.human_review_applicable
                else "provider_failure_recorded" if outcome.final_case_disposition is CaseDisposition.TRANSPORT_FAILURE
                else "generation_automated_rejected"
            )
            self._commit_case_transition(document, case_id, old, new, operation)
            return outcome

    def _generation_audit_document(self, outcome: CaseOutcome) -> dict[str, object]:
        if outcome.final_case_disposition is CaseDisposition.TRANSPORT_FAILURE:
            return {
                "case_id": outcome.case_id, "transport_result": outcome.transport_result,
                "synthetic": True,
            }
        if outcome.pydantic_validation_result is False:
            classification = "structural_failure"
        elif outcome.semantic_validation_result is False:
            classification = "semantic_failure"
        elif outcome.prose_validation_result is False:
            classification = "prose_failure"
        else:
            classification = "validated"
        return {
            "case_id": outcome.case_id, "synthetic": True,
            "classification": classification,
            "request_identity": (
                outcome.deterministic_request_sha256,
                outcome.canonical_attempt_sha256,
                outcome.provider_fingerprint,
            ),
            "generation_attempt_count": 1,
            "token_preflight_count_during_generation": 0,
            "retries": 0,
            "prose_violation_codes": list(outcome.ordered_prose_violation_codes),
            "rejected_prose_diagnostics": list(outcome.bounded_rejected_prose_diagnostics),
            "fallback_selected": outcome.fallback_selected,
            "fallback_version": outcome.fallback_version,
            "fallback_question_id": outcome.fallback_question_id,
        }

    def record_review(
        self, case_id: str, *, evidence_sha256: str, reviewer: str,
        review: HumanReview,
    ) -> Mapping[str, object]:
        with _ledger_lock(self.root):
            document = self._load_unlocked()
            record = document["cases"].get(case_id)
            if not record or record["current_state"] != CaseState.AWAITING_HUMAN_REVIEW:
                raise EvaluationRunnerError("case is not awaiting human review")
            if record["validated_response_evidence_sha256"] != evidence_sha256:
                raise EvaluationRunnerError("human review evidence binding mismatch")
            evidence_path = self.root / "evidence" / f"{case_id}.json"
            if not evidence_path.exists() or hashlib.sha256(evidence_path.read_bytes()).hexdigest() != evidence_sha256:
                raise EvaluationRunnerError("validated response evidence is absent or changed")
            review_document = {
                "evaluation_set_id": SET_ID, "runner_id": RUNNER_ID,
                "case_id": case_id, "synthetic": True, "reviewer": reviewer,
                "validated_response_evidence_sha256": evidence_sha256,
                "review": review.model_dump(mode="json"),
            }
            review_digest = _atomic_json(
                self.root / "reviews" / f"{case_id}.json", review_document
            )
            outcome = CaseOutcome.model_validate(record["outcome"])
            updated = outcome.model_copy(update={
                "state_history": outcome.state_history + (CaseState.HUMAN_REVIEW_COMPLETE,),
                "human_review_decision": review.decision,
                "grounding_accurate": review.grounding_accurate,
                "invented_user_fact": review.invented_user_fact,
                "irrelevant_detail": review.irrelevant_detail,
                "modality_overstatement": review.modality_overstatement,
                "service_selection_overstatement": review.service_selection_overstatement,
                "clarity_score": review.clarity_score,
                "usefulness_score": review.usefulness_score,
                "fallback_comparison": review.fallback_comparison,
                "human_review_sha256": review_digest,
                "human_review_reviewer": reviewer,
            })
            old = dict(record)
            new = dict(record)
            self._record_outcome(new, updated)
            self._commit_case_transition(
                document, case_id, old, new, "human_review_recorded",
            )
            return review_document | {"human_review_sha256": review_digest}

    def delete_evidence(
        self, case_id: str, *, evidence_sha256: str, review_sha256: str,
    ) -> Mapping[str, object]:
        with _ledger_lock(self.root):
            document = self._load_unlocked()
            record = document["cases"].get(case_id)
            if not record:
                raise EvaluationRunnerError("unknown ledger case")
            deletion_path = self.root / "deletions" / f"{case_id}.json"
            if record["terminal"] and record["evidence_deletion_sha256"]:
                if not deletion_path.exists():
                    raise EvaluationRunnerError("terminal deletion artifact is missing")
                existing = json.loads(deletion_path.read_text())
                if (existing.get("validated_response_evidence_sha256") != evidence_sha256
                        or existing.get("human_review_sha256") != review_sha256):
                    raise EvaluationRunnerError("idempotent deletion binding mismatch")
                return existing | {"status": "already_deleted"}
            if record["current_state"] != CaseState.HUMAN_REVIEW_COMPLETE:
                raise EvaluationRunnerError("review must complete before evidence deletion")
            if record["validated_response_evidence_sha256"] != evidence_sha256:
                raise EvaluationRunnerError("deletion evidence binding mismatch")
            if record["human_review_sha256"] != review_sha256:
                raise EvaluationRunnerError("deletion review binding mismatch")
            evidence_path = self.root / "evidence" / f"{case_id}.json"
            if not evidence_path.exists() or hashlib.sha256(evidence_path.read_bytes()).hexdigest() != evidence_sha256:
                raise EvaluationRunnerError("validated evidence is absent or changed")
            deletion = {
                "evaluation_set_id": SET_ID, "runner_id": RUNNER_ID,
                "case_id": case_id, "synthetic": True,
                "validated_response_evidence_sha256": evidence_sha256,
                "human_review_sha256": review_sha256,
                "deleted": True, "response_content_retained": False,
            }
            if "response" in deletion:
                raise EvaluationRunnerError("deletion artifact must not retain response content")
            transaction_path = self.root / "transactions" / f"{case_id}-deletion.json"
            transaction = {
                "transaction_version": 1, "evaluation_set_id": SET_ID,
                "evaluation_manifest_sha256": EVALUATION_MANIFEST_SHA256,
                "runner_id": RUNNER_ID, "runner_version": RUNNER_VERSION,
                "case_id": case_id,
                "state": "prepared", "validated_response_evidence_sha256": evidence_sha256,
                "human_review_sha256": review_sha256,
                "intended_deletion_sha256": _digest(deletion),
                "previous_case_state_sha256": _digest(record),
                "prepared_event_id": f"{case_id}:delete:prepared",
            }
            transaction["transaction_id"] = self._deletion_transaction_id(transaction)
            _atomic_json(transaction_path, transaction)
            self._deletion_crash_point("transaction_prepared")
            deletion_digest = _atomic_json(deletion_path, deletion)
            self._deletion_crash_point("deletion_artifact_written")
            transaction["state"] = "removal_prepared"
            transaction["removal_prepared_event_id"] = (
                f"{case_id}:delete:removal_prepared"
            )
            _atomic_json(transaction_path, transaction)
            evidence_path.unlink()
            directory = os.open(evidence_path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
            self._deletion_crash_point("evidence_unlinked")
            transaction["state"] = "evidence_removed"
            transaction["evidence_removed_event_id"] = f"{case_id}:delete:evidence_removed"
            _atomic_json(transaction_path, transaction)
            self._deletion_crash_point("evidence_removed_persisted")
            outcome = CaseOutcome.model_validate(record["outcome"])
            disposition = (
                CaseDisposition.PASSED
                if outcome.human_review_decision is ReviewDecision.APPROVE
                else CaseDisposition.HUMAN_REJECTED
            )
            updated = outcome.model_copy(update={
                "state_history": outcome.state_history + (CaseState.CASE_COMPLETE,),
                "evidence_deletion_sha256": deletion_digest,
                "response_evidence_deleted": True,
                "final_case_disposition": disposition,
            })
            updated = CaseOutcome.model_validate(updated.model_dump(mode="json"))
            old = dict(record)
            new = dict(record)
            self._record_outcome(new, updated)
            new["deletion_transaction_id"] = transaction["transaction_id"]
            closure_digest = self._write_closure(new, updated)
            deletion_transition_sha256 = self._append_transition_unlocked(
                document, operation="response_evidence_deleted", case_id=case_id,
                old_record=old, new_record=new,
                artifacts=self._expected_transition_artifacts(
                    "response_evidence_deleted", new
                ),
            )
            self._deletion_crash_point("deletion_transition_appended")
            document["cases"][case_id] = new
            self._save_unlocked(document)
            self._deletion_crash_point("ledger_projection_updated")
            transaction["state"] = "committed"
            transaction["deletion_sha256"] = deletion_digest
            transaction["closure_sha256"] = closure_digest
            transaction["deletion_transition_sha256"] = deletion_transition_sha256
            transaction["committed_event_id"] = f"{case_id}:delete:committed"
            self._deletion_crash_point("before_transaction_committed")
            _atomic_json(transaction_path, transaction)
            return deletion | {"evidence_deletion_sha256": deletion_digest, "status": "deleted"}

    def _deletion_transaction_id(self, transaction: Mapping[str, object]) -> str:
        return _digest({
            "transaction_version": 1,
            "evaluation_set_id": SET_ID,
            "evaluation_manifest_sha256": EVALUATION_MANIFEST_SHA256,
            "runner_id": RUNNER_ID,
            "runner_version": RUNNER_VERSION,
            "case_id": transaction.get("case_id"),
            "validated_response_evidence_sha256":
                transaction.get("validated_response_evidence_sha256"),
            "human_review_sha256": transaction.get("human_review_sha256"),
            "intended_deletion_sha256": transaction.get("intended_deletion_sha256"),
            "previous_case_state_sha256": transaction.get("previous_case_state_sha256"),
            "prepared_event_id": transaction.get("prepared_event_id"),
        })

    def _deletion_crash_point(self, _step: str) -> None:
        """Test-only fault-injection seam; production implementation is a no-op."""

    def _recovery_crash_point(self, _step: str) -> None:
        """Test-only fault-injection seam; production implementation is a no-op."""

    def recover(self) -> Mapping[str, object]:
        with _ledger_lock(self.root):
            document = json.loads(self.ledger_path.read_text())
            projected, terminal, count, pending = self._replay_journal_unlocked()
            mismatched_cases = [
                case_id for case_id in projected
                if document.get("cases", {}).get(case_id) != projected[case_id]
            ]
            incomplete = []
            for path in sorted((self.root / "transactions").glob("*-deletion.json")):
                candidate = json.loads(path.read_text())
                if candidate.get("state") != "committed":
                    incomplete.append((path, candidate))
            if len(pending) > 1 or len(incomplete) > 1:
                raise EvaluationRunnerError("only one recovery may be active")
            if not pending and not mismatched_cases and not incomplete:
                return self._load_unlocked()

            if pending:
                recovery_event_id, prepared = next(iter(pending.items()))
                basis = dict(prepared["basis"])
                recovery_case_id = str(basis["case_id"])
                prepared_sha256 = str(prepared["transition"]["transition_sha256"])
            else:
                recovery_case_id = (
                    str(incomplete[0][1]["case_id"]) if incomplete else mismatched_cases[0]
                )
                if any(case_id != recovery_case_id for case_id in mismatched_cases):
                    raise EvaluationRunnerError("recovery spans multiple cases")
                record = projected[recovery_case_id]
                transaction_before = dict(incomplete[0][1]) if incomplete else None
                if transaction_before is None:
                    transaction_path = self.root / "transactions" / (
                        f"{recovery_case_id}-deletion.json"
                    )
                    if transaction_path.exists():
                        transaction_before = json.loads(transaction_path.read_text())
                if transaction_before is not None:
                    transaction_path = self.root / "transactions" / (
                        f"{recovery_case_id}-deletion.json"
                    )
                    self._validate_deletion_transaction(
                        transaction_before, projected, path=transaction_path,
                    )
                evidence_path = self.root / "evidence" / f"{recovery_case_id}.json"
                deletion_path = self.root / "deletions" / f"{recovery_case_id}.json"
                counters = {
                    "preflights": record["preflight_attempts_consumed"],
                    "generations": record["generation_attempts_consumed"],
                    "retries": record["retry_count"],
                }
                basis = {
                    "recovery_basis_version": 1,
                    "evaluation_set_id": SET_ID,
                    "evaluation_manifest_sha256": EVALUATION_MANIFEST_SHA256,
                    "runner_id": RUNNER_ID,
                    "runner_version": RUNNER_VERSION,
                    "case_id": recovery_case_id,
                    "prior_journal_terminal_sha256": terminal,
                    "prior_journal_transition_count": count,
                    "prior_ledger_projection": document,
                    "prior_ledger_projection_sha256": _digest(document),
                    "prior_case_record": document.get("cases", {}).get(recovery_case_id),
                    "prior_case_state_sha256": _digest(record),
                    "projection_repair_required": bool(mismatched_cases),
                    "deletion_transaction_before": transaction_before,
                    "deletion_transaction_before_sha256": (
                        _digest(transaction_before) if transaction_before is not None else None
                    ),
                    "deletion_transaction_state_before": (
                        transaction_before.get("state") if transaction_before else None
                    ),
                    "deletion_artifact_present_before": deletion_path.exists(),
                    "deletion_artifact_sha256_before": (
                        hashlib.sha256(deletion_path.read_bytes()).hexdigest()
                        if deletion_path.exists() else None
                    ),
                    "evidence_present_before": evidence_path.exists(),
                    "evidence_sha256_before": (
                        hashlib.sha256(evidence_path.read_bytes()).hexdigest()
                        if evidence_path.exists() else None
                    ),
                    "human_review_sha256": record.get("human_review_sha256"),
                    "closure_sha256_before": record.get("closure_sha256"),
                    "attempt_counters": counters,
                }
                recovery_event_id = _digest(basis)
                basis["recovery_event_id"] = recovery_event_id
                basis_digest = _atomic_json(
                    self.root / "recoveries" / f"{recovery_event_id}-basis.json", basis,
                )
                self._recovery_crash_point("basis_persisted")
                prepared_sha256 = self._append_transition_unlocked(
                    document, operation="recovery_prepared", case_id=recovery_case_id,
                    old_record=record, new_record=record,
                    artifacts={"recovery_basis_sha256": basis_digest},
                    metadata={"recovery_event_id": recovery_event_id},
                )
                self._recovery_crash_point("recovery_prepared_appended")
                self._recovery_crash_point("before_first_repair")

            record = projected[recovery_case_id]
            transaction_before = basis.get("deletion_transaction_before")
            transaction_after = transaction_before
            deletion_digest = basis.get("deletion_artifact_sha256_before")
            transaction_path = self.root / "transactions" / f"{recovery_case_id}-deletion.json"
            if transaction_before is not None and transaction_before.get("state") != "committed":
                transaction = json.loads(transaction_path.read_text())
                if _digest(transaction) != basis.get("deletion_transaction_before_sha256"):
                    # A resumed recovery may already have advanced the transaction.
                    if transaction.get("state") != "committed":
                        raise EvaluationRunnerError("recovery transaction changed unexpectedly")
                evidence_digest = transaction_before.get("validated_response_evidence_sha256")
                review_digest = transaction_before.get("human_review_sha256")
                deletion_path = self.root / "deletions" / f"{recovery_case_id}.json"
                evidence_path = self.root / "evidence" / f"{recovery_case_id}.json"
                if not deletion_path.exists():
                    deletion = {
                        "evaluation_set_id": SET_ID, "runner_id": RUNNER_ID,
                        "case_id": recovery_case_id, "synthetic": True,
                        "validated_response_evidence_sha256": evidence_digest,
                        "human_review_sha256": review_digest,
                        "deleted": True, "response_content_retained": False,
                    }
                    if _digest(deletion) != transaction.get("intended_deletion_sha256"):
                        raise EvaluationRunnerError("deletion recovery identity mismatch")
                    _atomic_json(deletion_path, deletion)
                deletion_digest = hashlib.sha256(deletion_path.read_bytes()).hexdigest()
                deletion_artifact_sha256 = deletion_digest
                if deletion_digest != transaction.get("intended_deletion_sha256"):
                    raise EvaluationRunnerError("deletion recovery artifact mismatch")
                if evidence_path.exists():
                    if hashlib.sha256(evidence_path.read_bytes()).hexdigest() != evidence_digest:
                        raise EvaluationRunnerError("deletion recovery evidence mismatch")
                    evidence_path.unlink()
                    directory = os.open(evidence_path.parent, os.O_RDONLY)
                    try:
                        os.fsync(directory)
                    finally:
                        os.close(directory)
                record = projected[recovery_case_id]
                if record["current_state"] == CaseState.HUMAN_REVIEW_COMPLETE:
                    if transaction.get("previous_case_state_sha256") != _digest(record):
                        raise EvaluationRunnerError("deletion recovery previous-state mismatch")
                    outcome = CaseOutcome.model_validate(record["outcome"])
                    disposition = (CaseDisposition.PASSED
                                   if outcome.human_review_decision is ReviewDecision.APPROVE
                                   else CaseDisposition.HUMAN_REJECTED)
                    updated = CaseOutcome.model_validate(outcome.model_copy(update={
                        "state_history": outcome.state_history + (CaseState.CASE_COMPLETE,),
                        "evidence_deletion_sha256": deletion_digest,
                        "response_evidence_deleted": True,
                        "final_case_disposition": disposition,
                    }).model_dump(mode="json"))
                    old = dict(record)
                    new = dict(record)
                    self._record_outcome(new, updated)
                    new["deletion_transaction_id"] = transaction["transaction_id"]
                    closure_digest = self._write_closure(new, updated)
                    deletion_transition_sha256 = self._append_transition_unlocked(
                        document, operation="response_evidence_deleted",
                        case_id=recovery_case_id,
                        old_record=old, new_record=new,
                        artifacts=self._expected_transition_artifacts(
                            "response_evidence_deleted", new
                        ),
                    )
                    projected[recovery_case_id] = new
                    record = new
                elif not record["terminal"]:
                    raise EvaluationRunnerError("deletion recovery state mismatch")
                else:
                    deletion_transition_sha256 = self._deletion_transition_for_case(
                        recovery_case_id
                    )
                transaction["state"] = "committed"
                transaction["deletion_sha256"] = deletion_digest
                transaction["closure_sha256"] = projected[recovery_case_id]["closure_sha256"]
                transaction["deletion_transition_sha256"] = deletion_transition_sha256
                transaction["removal_prepared_event_id"] = (
                    f"{recovery_case_id}:delete:removal_prepared"
                )
                transaction["evidence_removed_event_id"] = (
                    f"{recovery_case_id}:delete:evidence_removed"
                )
                transaction["committed_event_id"] = f"{recovery_case_id}:delete:committed"
                _atomic_json(transaction_path, transaction)
                transaction_after = transaction

            document["cases"] = projected
            document["journal_terminal_sha256"] = prepared_sha256
            document["journal_transition_count"] = count + (0 if pending else 1)
            counters = basis["attempt_counters"]
            transaction_after_digest = (
                _digest(transaction_after) if transaction_after is not None else None
            )
            repair_classification = self._derive_recovery_classification(
                projection_repaired=bool(basis["projection_repair_required"]),
                deletion_transaction_advanced=(
                    basis.get("deletion_transaction_before_sha256")
                    != transaction_after_digest
                ),
            )
            completion = {
                    "recovery_completion_version": 1,
                    "evaluation_set_id": SET_ID,
                    "evaluation_manifest_sha256": EVALUATION_MANIFEST_SHA256,
                    "runner_id": RUNNER_ID,
                    "runner_version": RUNNER_VERSION,
                    "case_id": recovery_case_id,
                    "recovery_event_id": recovery_event_id,
                    "recovery_basis_sha256": hashlib.sha256(
                        (self.root / "recoveries" / f"{recovery_event_id}-basis.json").read_bytes()
                    ).hexdigest(),
                    "recovery_prepared_transition_sha256": prepared_sha256,
                    "post_case_state_sha256": _digest(record),
                    "deletion_transaction_after": transaction_after,
                    "deletion_transaction_after_sha256": transaction_after_digest,
                    "deletion_transaction_state_after": (
                        transaction_after.get("state") if transaction_after else None
                    ),
                    "evidence_present_after": False,
                    "deletion_artifact_sha256": deletion_digest,
                    "repair_classification": repair_classification,
                    "attempt_counters": counters,
                }
            completion_digest = _atomic_json(
                self.root / "recoveries" / f"{recovery_event_id}-completed.json", completion,
            )
            self._append_transition_unlocked(
                document, operation="recovery_completed", case_id=recovery_case_id,
                old_record=record, new_record=record,
                artifacts={
                    "recovery_basis_sha256": completion["recovery_basis_sha256"],
                    "recovery_prepared_transition_sha256": prepared_sha256,
                    "recovery_completion_sha256": completion_digest,
                },
                metadata={"repair_classification": repair_classification,
                          "recovery_event_id": recovery_event_id},
            )
            self._save_unlocked(document)
            return self._load_unlocked()

    def _deletion_transition_for_case(self, case_id: str) -> str:
        journal = json.loads(self.journal_path.read_text())
        matches = [
            item["transition_sha256"] for item in journal["transitions"]
            if item.get("case_id") == case_id
            and item.get("operation_type") == "response_evidence_deleted"
        ]
        if len(matches) != 1:
            raise EvaluationRunnerError("deletion transaction journal binding mismatch")
        return matches[0]

    def finalize_report(self, *, write: bool = True) -> FinalEvaluationReport:
        with _ledger_lock(self.root):
            document = self._load_unlocked()
            records = document["cases"]
            if not all(record["terminal"] for record in records.values()):
                raise EvaluationRunnerError("all ten ledger cases must be terminal before finalization")
            outcomes = tuple(
                CaseOutcome.model_validate(records[f"eval-v4-{index:02d}"]["outcome"])
                for index in range(1, 11)
            )
            for outcome in outcomes:
                if outcome.human_review_applicable:
                    evidence_path = self.root / "evidence" / f"{outcome.case_id}.json"
                    deletion_path = self.root / "deletions" / f"{outcome.case_id}.json"
                    if evidence_path.exists() or not deletion_path.exists():
                        raise EvaluationRunnerError("reviewed evidence deletion is incomplete")
            ledger_digest = hashlib.sha256(self.ledger_path.read_bytes()).hexdigest()
            outcome_digests = {
                case_id: records[case_id]["outcome_sha256"] for case_id in sorted(records)
            }
            report = score_outcomes(outcomes).model_copy(update={
                "ledger_version": LEDGER_VERSION,
                "ledger_sha256": ledger_digest,
                "transition_journal_terminal_sha256": document["journal_terminal_sha256"],
                "journal_transition_count": document["journal_transition_count"],
                "case_closure_sha256": {
                    case_id: records[case_id]["closure_sha256"] for case_id in sorted(records)
                },
                "terminal_outcome_sha256": outcome_digests,
                "report_serialization_version": REPORT_SERIALIZATION_VERSION,
            })
            if write:
                _atomic_json(self.report_path, report.model_dump(mode="json"))
            return report

    def verify_report(self) -> Mapping[str, object]:
        report = self.finalize_report(write=False)
        expected = _canonical(report.model_dump(mode="json"))
        if not self.report_path.exists() or self.report_path.read_bytes() != expected:
            raise EvaluationRunnerError("final evaluation report bytes are not deterministic")
        return {
            "report_verified": True,
            "report_sha256": hashlib.sha256(expected).hexdigest(),
            "ledger_sha256": report.ledger_sha256,
            "final_disposition": report.final_disposition,
            "synthetic": True,
        }


def rehearse_scenario(scenario: str) -> FinalEvaluationReport:
    return FormalEvaluationRunner(scenario=scenario).run_all()
