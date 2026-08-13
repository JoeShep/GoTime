"""Milestone 9B bounded generation-result validation and evidence models."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import re
from typing import Mapping

from app.moving_service_questions import MAXIMUM_RESPONSE_CHARACTERS
from freeze_v4_formal_evaluation_set import _request_for_case, source_cases
from moving_service_questions_v2 import (
    FALLBACK_VERSION_V2, HOME_OR_PROPERTY_PHRASES, PROSE_FIELDS,
    PROSE_VIOLATION_CODE_ORDER, SELECTION_ADJECTIVES, SELECTION_NOUN_PATTERNS,
    STORAGE_MODALITY_FIELDS, select_fallback_v2,
)
from rejected_prose_diagnostics import RULE_ID, STORAGE_MODALITY_TRIGGERS
from v4_formal_evaluation_runner import _v2_request, validate_case_response
from v4_formal_evaluation_live_models import AGGREGATE_ID, MAX_RETRIES, digest, package_identity
from v4_formal_evaluation_live_state import format_time, parse_time

RESULT_SCHEMA = "suggest-moving-service-questions-v4-formal-evaluation-generation-result-v1"
RESULT_VERSION = 1
EVIDENCE_SCHEMA = "suggest-moving-service-questions-v4-formal-evaluation-generation-result-evidence-v1"
EVIDENCE_VERSION = 1
CLOSURE_SCHEMA = "suggest-moving-service-questions-v4-formal-evaluation-generation-phase-closure-v1"
CLOSURE_VERSION = 1
PROVIDER_FAILURES = ("timeout", "transport_error", "provider_error", "outcome_unknown")
CONTENT_FAILURES = ("structural_failure", "semantic_failure", "prose_failure")


class GenerationResultError(ValueError):
    pass


def _valid_selection_trigger(trigger: str) -> bool:
    if trigger != " ".join(trigger.casefold().split()) or "-" in trigger:
        return False
    adjective, separator, noun = trigger.partition(" ")
    return bool(
        separator and adjective in SELECTION_ADJECTIVES
        and any(re.fullmatch(pattern, noun) for pattern in SELECTION_NOUN_PATTERNS)
    )


def _validate_prose_diagnostics(case_id: str, codes: object, diagnostics: object) -> None:
    required = {
        "violation_code", "rule_id", "field", "start_offset", "end_offset",
        "canonical_trigger", "occurrence_count",
    }
    order = {code: index for index, code in enumerate(PROSE_VIOLATION_CODE_ORDER)}
    if not isinstance(codes, list) or not codes or any(type(code) is not str for code in codes):
        raise GenerationResultError("prose failure requires canonical violation codes")
    if not isinstance(diagnostics, list) or not diagnostics:
        raise GenerationResultError("prose failure requires bounded canonical diagnostics")
    for item in diagnostics:
        if not isinstance(item, dict) or set(item) != required:
            raise GenerationResultError("prose failure diagnostics are not exact")
        code, rule, field = item["violation_code"], item["rule_id"], item["field"]
        start, end = item["start_offset"], item["end_offset"]
        trigger, count = item["canonical_trigger"], item["occurrence_count"]
        if (type(code) is not str or code not in order or type(rule) is not str
                or rule != RULE_ID or type(field) is not str or type(trigger) is not str
                or not trigger or len(trigger) > MAXIMUM_RESPONSE_CHARACTERS
                or type(start) is not int or type(end) is not int or type(count) is not int
                or start < 0 or end < start or end > MAXIMUM_RESPONSE_CHARACTERS
                or count < 1 or count > MAXIMUM_RESPONSE_CHARACTERS):
            raise GenerationResultError("prose failure diagnostic value is not canonical and bounded")
        if code == "irrelevant_location_reference":
            request = _case_request(case_id)
            locations = {
                "supplied_origin_region": " ".join(request.trusted_state.origin_region.casefold().split()),
                "supplied_destination_region": " ".join(request.trusted_state.destination_region.casefold().split()),
            }
            phrase = locations.get(trigger, "")
            valid = field in PROSE_FIELDS and bool(phrase) and end - start >= len(phrase)
        elif code == "unsupported_home_or_property_assertion":
            valid = (
                field in PROSE_FIELDS and trigger in HOME_OR_PROPERTY_PHRASES
                and end - start >= len(trigger)
            )
        elif code == "storage_modality_overstatement":
            valid = (
                field in STORAGE_MODALITY_FIELDS and trigger in STORAGE_MODALITY_TRIGGERS
                and end - start >= len(trigger)
            )
        elif code == "unsupported_service_selection_language":
            valid = (
                field in PROSE_FIELDS and _valid_selection_trigger(trigger)
                and end - start >= len(trigger)
            )
        else:
            valid = (
                start == end == 0 and count == 1
                and (field, trigger) in {
                    ("relevant_knowledge_ids", "knowledge_id_mismatch"),
                    ("grounding_summary", "exact_grounding_summary_mismatch"),
                }
            )
        if not valid:
            raise GenerationResultError("prose failure diagnostic rule binding is not canonical")
    expected_order = sorted(
        diagnostics,
        key=lambda item: (
            order[item["violation_code"]], item["field"],
            item["start_offset"], item["canonical_trigger"],
        ),
    )
    if diagnostics != expected_order:
        raise GenerationResultError("prose failure diagnostics are not canonically ordered")
    diagnostic_codes = [
        code for code in PROSE_VIOLATION_CODE_ORDER
        if any(item["violation_code"] == code for item in diagnostics)
    ]
    if codes != diagnostic_codes:
        raise GenerationResultError("prose failure codes do not match canonical diagnostics")


def provider_failure(classification: str) -> dict[str, object]:
    if classification not in PROVIDER_FAILURES:
        raise GenerationResultError("generation provider failure classification is unavailable")
    return {
        "classification": classification, "validated_response": None,
        "ordered_prose_violation_codes": [], "bounded_rejected_prose_diagnostics": [],
        "fallback_selected": False, "fallback_version": None, "fallback_question_id": None,
    }


def _case_request(case_id: str):
    case = next((item for item in source_cases() if item["case_id"] == case_id), None)
    if case is None:
        raise GenerationResultError("generation result case is unavailable")
    return _request_for_case(case)


def _base(case_id: str, envelope: Mapping[str, object], grant: Mapping[str, object],
          reservation: Mapping[str, object], dispatch_sha256: str) -> dict[str, object]:
    binding = envelope["immutable_binding"]
    return {
        "aggregate_id": AGGREGATE_ID, "aggregate_package_sha256": package_identity(),
        "case_id": case_id, "phase": "generation",
        "case_envelope_sha256": envelope["envelope_sha256"],
        "generation_grant_sha256": grant["grant_sha256"],
        "generation_reservation_sha256": reservation["reservation_sha256"],
        "provider_dispatch_started_sha256": dispatch_sha256,
        "deterministic_request_sha256": binding["deterministic_request_sha256"],
        "canonical_attempt_sha256": binding["canonical_attempt_sha256"],
        "provider_fingerprint": binding["provider_fingerprint"],
        "provider": binding["provider"], "ai_model_identifier": binding["ai_model_identifier"],
        "sdk": binding["sdk"], "automatic_retries": MAX_RETRIES,
    }


def classify_generation(case_id: str, raw: object) -> dict[str, object]:
    classification, value, diagnostics = validate_case_response(_case_request(case_id), raw)
    fallback = select_fallback_v2(_v2_request(_case_request(case_id))) if classification != "validated" else None
    return {
        "classification": classification,
        "validated_response": value.model_dump(mode="json") if classification == "validated" else None,
        "ordered_prose_violation_codes": list(value) if classification == "prose_failure" else [],
        "bounded_rejected_prose_diagnostics": list(diagnostics),
        "fallback_selected": fallback is not None,
        "fallback_version": FALLBACK_VERSION_V2 if fallback is not None else None,
        "fallback_question_id": fallback.question_id if fallback is not None else None,
    }


def build_result(case_id: str, envelope: Mapping[str, object], grant: Mapping[str, object],
                 reservation: Mapping[str, object], dispatch_sha256: str,
                 outcome: Mapping[str, object], recorded_at: datetime) -> dict[str, object]:
    classification = outcome.get("classification")
    if classification not in ("validated", *CONTENT_FAILURES, *PROVIDER_FAILURES):
        raise GenerationResultError("generation result classification is unavailable")
    validated = outcome.get("validated_response")
    if (classification == "validated") != (isinstance(validated, dict)):
        raise GenerationResultError("validated generation result requires exact structured response")
    immutable = {
        **_base(case_id, envelope, grant, reservation, dispatch_sha256),
        "classification": classification,
        "validated_response": deepcopy(validated) if classification == "validated" else None,
        "ordered_prose_violation_codes": outcome.get("ordered_prose_violation_codes", []),
        "bounded_rejected_prose_diagnostics": outcome.get("bounded_rejected_prose_diagnostics", []),
        "fallback_selected": outcome.get("fallback_selected", False),
        "fallback_version": outcome.get("fallback_version"),
        "fallback_question_id": outcome.get("fallback_question_id"),
        "recorded_at": format_time(recorded_at),
    }
    identity = {"result_schema": RESULT_SCHEMA, "result_version": RESULT_VERSION,
                "immutable_binding": immutable}
    return {**identity, "result_sha256": digest(identity)}


def build_evidence(result: Mapping[str, object], created_at: datetime) -> dict[str, object]:
    binding = result["immutable_binding"]
    if binding["classification"] != "validated":
        raise GenerationResultError("only validated generation result creates evidence")
    immutable = {
        **{key: binding[key] for key in (
            "aggregate_id", "aggregate_package_sha256", "case_id", "phase",
            "case_envelope_sha256", "generation_grant_sha256",
            "generation_reservation_sha256", "provider_dispatch_started_sha256",
            "deterministic_request_sha256", "canonical_attempt_sha256", "provider_fingerprint",
            "provider", "ai_model_identifier", "sdk",
        )},
        "generation_result_sha256": result["result_sha256"],
        "validated_response": deepcopy(binding["validated_response"]),
        "evidence_created_at": format_time(created_at),
        "generation_evidence_review_status": "pending",
    }
    identity = {"evidence_schema": EVIDENCE_SCHEMA, "evidence_version": EVIDENCE_VERSION,
                "immutable_binding": immutable}
    return {**identity, "evidence_sha256": digest(identity)}


def build_closure(result: Mapping[str, object], evidence: Mapping[str, object] | None,
                  closed_at: datetime) -> dict[str, object]:
    binding = result["immutable_binding"]
    classification = binding["classification"]
    status = "awaiting_generation_evidence_review" if classification == "validated" else (
        "provider_failed" if classification in PROVIDER_FAILURES else "automated_rejected")
    immutable = {
        "aggregate_id": binding["aggregate_id"], "case_id": binding["case_id"],
        "phase": "generation", "generation_result_sha256": result["result_sha256"],
        "generation_evidence_sha256": evidence["evidence_sha256"] if evidence else None,
        "result_classification": classification, "status": status,
        "attempt_consumed": True, "release_authorized": False, "retry_authorized": False,
        "closed_at": format_time(closed_at),
    }
    identity = {"closure_schema": CLOSURE_SCHEMA, "closure_version": CLOSURE_VERSION,
                "immutable_binding": immutable}
    return {**identity, "closure_sha256": digest(identity)}


def validate_bundle(result: object, evidence: object | None, closure: object,
                    envelope: Mapping[str, object], grant: Mapping[str, object],
                    reservation: Mapping[str, object]) -> None:
    if not isinstance(result, dict) or not isinstance(closure, dict):
        raise GenerationResultError("generation result lifecycle is malformed")
    binding = result.get("immutable_binding", {})
    recorded = parse_time(binding.get("recorded_at", ""))
    classification = binding.get("classification")
    if classification == "validated":
        canonical_outcome = classify_generation(binding.get("case_id"), binding.get("validated_response"))
        if canonical_outcome["classification"] != "validated":
            raise GenerationResultError("stored generation response is not canonically valid")
    elif classification in CONTENT_FAILURES:
        fallback = select_fallback_v2(_v2_request(_case_request(binding.get("case_id"))))
        codes = binding.get("ordered_prose_violation_codes")
        diagnostics = binding.get("bounded_rejected_prose_diagnostics")
        if classification != "prose_failure" and (codes != [] or diagnostics != []):
            raise GenerationResultError("non-prose generation failure cannot retain prose diagnostics")
        if classification == "prose_failure":
            _validate_prose_diagnostics(binding.get("case_id"), codes, diagnostics)
        canonical_outcome = {
            "classification": classification, "validated_response": None,
            "ordered_prose_violation_codes": codes,
            "bounded_rejected_prose_diagnostics": diagnostics,
            "fallback_selected": True, "fallback_version": FALLBACK_VERSION_V2,
            "fallback_question_id": fallback.question_id,
        }
    else:
        if classification not in PROVIDER_FAILURES:
            raise GenerationResultError("generation result classification is unavailable")
        canonical_outcome = provider_failure(classification)
    expected = build_result(
        binding.get("case_id"), envelope, grant, reservation,
        binding.get("provider_dispatch_started_sha256"), canonical_outcome, recorded,
    )
    if result != expected:
        raise GenerationResultError("generation result does not match its canonical validation binding")
    if (classification == "validated") != (evidence is not None):
        raise GenerationResultError("validated generation result and evidence must be atomic")
    if evidence is not None:
        created = parse_time(evidence["immutable_binding"]["evidence_created_at"])
        if evidence != build_evidence(result, created):
            raise GenerationResultError("generation evidence does not match its exact result binding")
    closed = parse_time(closure["immutable_binding"]["closed_at"])
    if closure != build_closure(result, evidence, closed):
        raise GenerationResultError("generation phase closure does not match its exact result")


def lifecycle_status(state: Mapping[str, object], case_id: str) -> str:
    """Return the fail-closed post-dispatch generation lifecycle status."""
    key = f"{case_id}:generation"
    reservation = state.get("provider_budget_reservations", {}).get(key)
    result = state.get("generation_results", {}).get(case_id)
    if result is not None:
        return state["generation_phase_closures"][case_id]["immutable_binding"]["status"]
    if reservation is not None and reservation["lifecycle"]["status"] == "consumed":
        return "dispatch_consumed_result_missing"
    return "not_dispatched"
