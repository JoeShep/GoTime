"""Milestone 9A bounded preflight result, evidence, review, and closure models."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Mapping

from v4_formal_evaluation_live_generation import conservative_generation_exposure
from v4_formal_evaluation_live_models import (
    AGGREGATE_ID, FROZEN_V4_MANIFEST_SHA256, MAX_RETRIES,
    REQUEST_IDENTITIES_SHA256, digest, package_identity, validate_human_label,
)
from v4_formal_evaluation_live_state import format_time, parse_time

RESULT_SCHEMA = "suggest-moving-service-questions-v4-formal-evaluation-preflight-result-v1"
RESULT_VERSION = 1
EVIDENCE_SCHEMA = "suggest-moving-service-questions-v4-formal-evaluation-preflight-result-evidence-v1"
EVIDENCE_VERSION = 1
REVIEW_SCHEMA = "suggest-moving-service-questions-v4-formal-evaluation-preflight-evidence-review-v1"
REVIEW_VERSION = 1
CLOSURE_SCHEMA = "suggest-moving-service-questions-v4-formal-evaluation-preflight-phase-closure-v1"
CLOSURE_VERSION = 1
REVIEW_LIFETIME = timedelta(minutes=15)
REVIEW_DECISIONS = ("approve", "reject", "request_changes")
FAILURE_CLASSIFICATIONS = (
    "timeout", "transport_error", "provider_error", "outcome_unknown", "invalid_result",
)
CONFIRMATION_FIELDS = (
    "token_count_plausible", "cost_within_limit",
    "frozen_bindings_confirmed", "evidence_history_confirmed",
)


class PreflightResultError(ValueError):
    pass


def lifecycle_status(state: Mapping[str, object], case_id: str) -> str:
    """Derive the fail-closed status; projection never fabricates a missing result."""
    result = state["preflight_results"].get(case_id)
    if result is not None:
        return state["preflight_phase_closures"][case_id]["immutable_binding"]["status"]
    reservation = state["provider_budget_reservations"].get(case_id)
    if reservation and reservation["lifecycle"]["attempt_consumed"] is True:
        return "dispatch_consumed_result_missing"
    return "not_dispatched"


def _base(case_id: str, envelope: Mapping[str, object], grant: Mapping[str, object],
          reservation: Mapping[str, object], dispatch_event_sha256: str) -> dict[str, object]:
    binding = envelope["immutable_binding"]
    return {
        "aggregate_id": AGGREGATE_ID,
        "aggregate_package_sha256": package_identity(),
        "case_id": case_id,
        "phase": "preflight",
        "case_envelope_sha256": envelope["envelope_sha256"],
        "preflight_grant_sha256": grant["grant_sha256"],
        "preflight_reservation_sha256": reservation["reservation_sha256"],
        "provider_dispatch_started_sha256": dispatch_event_sha256,
        "deterministic_case_input_sha256": binding["deterministic_case_input_sha256"],
        "deterministic_request_sha256": binding["deterministic_request_sha256"],
        "canonical_attempt_sha256": binding["canonical_attempt_sha256"],
        "provider_fingerprint": binding["provider_fingerprint"],
        "frozen_v4_manifest_sha256": FROZEN_V4_MANIFEST_SHA256,
        "request_identities_sha256": REQUEST_IDENTITIES_SHA256,
        "provider": binding["provider"],
        "ai_model_identifier": binding["ai_model_identifier"],
        "sdk": binding["sdk"],
    }


def build_validated_result(case_id: str, envelope: Mapping[str, object],
                           grant: Mapping[str, object], reservation: Mapping[str, object],
                           dispatch_event_sha256: str, input_tokens: int,
                           recorded_at: datetime) -> dict[str, object]:
    if not isinstance(input_tokens, int) or isinstance(input_tokens, bool) or input_tokens <= 0:
        raise PreflightResultError("preflight token-count result must be a positive integer")
    if case_id == "eval-v4-01" and input_tokens != 2852:
        raise PreflightResultError("case-01 preflight token-count result must equal 2852")
    immutable = {
        **_base(case_id, envelope, grant, reservation, dispatch_event_sha256),
        "classification": "validated",
        "input_tokens": input_tokens,
        "conservative_generation_exposure_usd": conservative_generation_exposure(
            input_tokens, envelope["immutable_binding"]["request_configuration"]),
        "recorded_at": format_time(recorded_at),
        "automatic_retries": MAX_RETRIES,
    }
    identity = {"result_schema": RESULT_SCHEMA, "result_version": RESULT_VERSION,
                "immutable_binding": immutable}
    return {**identity, "result_sha256": digest(identity)}


def build_provider_failure(case_id: str, envelope: Mapping[str, object],
                           grant: Mapping[str, object], reservation: Mapping[str, object],
                           dispatch_event_sha256: str, classification: str,
                           recorded_at: datetime) -> dict[str, object]:
    if classification not in FAILURE_CLASSIFICATIONS:
        raise PreflightResultError("preflight provider failure classification is unavailable")
    immutable = {
        **_base(case_id, envelope, grant, reservation, dispatch_event_sha256),
        "classification": classification, "recorded_at": format_time(recorded_at),
        "automatic_retries": MAX_RETRIES,
    }
    identity = {"result_schema": RESULT_SCHEMA, "result_version": RESULT_VERSION,
                "immutable_binding": immutable}
    return {**identity, "result_sha256": digest(identity)}


def build_evidence(result: Mapping[str, object], envelope: Mapping[str, object],
                   created_at: datetime) -> dict[str, object]:
    binding = result["immutable_binding"]
    if binding.get("classification") != "validated":
        raise PreflightResultError("provider failure cannot create reviewable preflight evidence")
    immutable = {
        **{key: binding[key] for key in _base(
            binding["case_id"], envelope,
            {"grant_sha256": binding["preflight_grant_sha256"]},
            {"reservation_sha256": binding["preflight_reservation_sha256"]},
            binding["provider_dispatch_started_sha256"],
        )},
        "preflight_result_sha256": result["result_sha256"],
        "input_tokens": binding["input_tokens"],
        "conservative_generation_exposure_usd": binding["conservative_generation_exposure_usd"],
        "evidence_created_at": format_time(created_at),
        "review_deadline": format_time(created_at + REVIEW_LIFETIME),
        "generation_gate_binding_eligible": False,
    }
    identity = {"evidence_schema": EVIDENCE_SCHEMA, "evidence_version": EVIDENCE_VERSION,
                "immutable_binding": immutable}
    return {**identity, "evidence_sha256": digest(identity)}


def build_review(evidence: Mapping[str, object], *, reviewer: str, decision: str,
                 reviewed_at: datetime, token_count_plausible: bool,
                 cost_within_limit: bool, frozen_bindings_confirmed: bool,
                 evidence_history_confirmed: bool, notes: str, now: datetime) -> dict[str, object]:
    validate_human_label(reviewer, "reviewer")
    if decision not in REVIEW_DECISIONS:
        raise PreflightResultError("preflight evidence review decision is unavailable")
    if not isinstance(notes, str) or not notes.strip() or len(notes) > 500:
        raise PreflightResultError("preflight evidence review notes must be nonempty and bounded")
    confirmations = {
        "token_count_plausible": token_count_plausible,
        "cost_within_limit": cost_within_limit,
        "frozen_bindings_confirmed": frozen_bindings_confirmed,
        "evidence_history_confirmed": evidence_history_confirmed,
    }
    if any(not isinstance(value, bool) for value in confirmations.values()):
        raise PreflightResultError("preflight evidence review confirmations must be explicit booleans")
    binding = evidence["immutable_binding"]
    created = parse_time(binding["evidence_created_at"])
    deadline = parse_time(binding["review_deadline"])
    if reviewed_at < created or reviewed_at > now:
        raise PreflightResultError("preflight evidence review timestamp is invalid")
    if decision == "approve" and (reviewed_at >= deadline or now >= deadline):
        raise PreflightResultError("preflight evidence approval is late")
    if decision == "approve" and not all(confirmations.values()):
        raise PreflightResultError("preflight evidence approval requires every confirmation")
    immutable = {
        "aggregate_id": binding["aggregate_id"], "case_id": binding["case_id"],
        "phase": "preflight_review", "preflight_evidence_sha256": evidence["evidence_sha256"],
        "preflight_result_sha256": binding["preflight_result_sha256"],
        "case_envelope_sha256": binding["case_envelope_sha256"],
        "preflight_grant_sha256": binding["preflight_grant_sha256"],
        "preflight_reservation_sha256": binding["preflight_reservation_sha256"],
        "provider_dispatch_started_sha256": binding["provider_dispatch_started_sha256"],
        "deterministic_request_sha256": binding["deterministic_request_sha256"],
        "canonical_attempt_sha256": binding["canonical_attempt_sha256"],
        "provider_fingerprint": binding["provider_fingerprint"],
        "provider": binding["provider"], "ai_model_identifier": binding["ai_model_identifier"],
        "sdk": binding["sdk"], "input_tokens": binding["input_tokens"],
        "conservative_generation_exposure_usd": binding["conservative_generation_exposure_usd"],
        "evidence_created_at": binding["evidence_created_at"],
        "review_deadline": binding["review_deadline"], "reviewer": reviewer,
        "decision": decision, "reviewed_at": format_time(reviewed_at),
        **confirmations, "bounded_notes": notes,
        "generation_gate_binding_eligible": decision == "approve",
    }
    identity = {"review_schema": REVIEW_SCHEMA, "review_version": REVIEW_VERSION,
                "immutable_binding": immutable}
    return {**identity, "review_sha256": digest(identity)}


def build_closure(case_id: str, result: Mapping[str, object], evidence: Mapping[str, object] | None,
                  review: Mapping[str, object] | None, closed_at: datetime) -> dict[str, object]:
    classification = result["immutable_binding"]["classification"]
    status = "review_pending" if evidence is not None and review is None else "review_approved" if review and review["immutable_binding"]["decision"] == "approve" else "review_rejected" if review and review["immutable_binding"]["decision"] == "reject" else "review_changes_requested" if review else "provider_failed"
    immutable = {
        "aggregate_id": AGGREGATE_ID, "case_id": case_id, "phase": "preflight",
        "preflight_result_sha256": result["result_sha256"],
        "preflight_evidence_sha256": evidence["evidence_sha256"] if evidence else None,
        "preflight_review_sha256": review["review_sha256"] if review else None,
        "result_classification": classification, "status": status,
        "attempt_consumed": True, "release_authorized": False,
        "retry_authorized": False, "generation_gate_binding_eligible": status == "review_approved",
        "closed_at": format_time(closed_at),
    }
    identity = {"closure_schema": CLOSURE_SCHEMA, "closure_version": CLOSURE_VERSION,
                "immutable_binding": immutable}
    return {**identity, "closure_sha256": digest(identity)}


def validate_bundle(result: object, evidence: object | None, review: object | None,
                    closure: object, envelope: Mapping[str, object], grant: Mapping[str, object],
                    reservation: Mapping[str, object]) -> None:
    if not isinstance(result, dict) or not isinstance(closure, dict):
        raise PreflightResultError("preflight result lifecycle is malformed")
    binding = result.get("immutable_binding", {})
    recorded = parse_time(binding.get("recorded_at", ""))
    expected = (build_validated_result(binding.get("case_id"), envelope, grant, reservation,
                binding.get("provider_dispatch_started_sha256"), binding.get("input_tokens"), recorded)
                if binding.get("classification") == "validated" else
                build_provider_failure(binding.get("case_id"), envelope, grant, reservation,
                binding.get("provider_dispatch_started_sha256"), binding.get("classification"), recorded))
    if result != expected:
        raise PreflightResultError("preflight result does not match its exact dispatch binding")
    if binding.get("classification") == "validated" and evidence is None:
        raise PreflightResultError("validated preflight result requires exact matching evidence")
    if binding.get("classification") != "validated" and evidence is not None:
        raise PreflightResultError("provider failure cannot retain preflight evidence")
    if evidence is not None:
        created = parse_time(evidence["immutable_binding"]["evidence_created_at"])
        if evidence != build_evidence(result, envelope, created):
            raise PreflightResultError("preflight evidence does not match its exact result binding")
    if review is not None:
        if evidence is None or review["immutable_binding"]["preflight_evidence_sha256"] != evidence["evidence_sha256"]:
            raise PreflightResultError("preflight review does not match its exact evidence binding")
        review_binding = review["immutable_binding"]
        reviewed_at = parse_time(review_binding["reviewed_at"])
        expected_review = build_review(
            evidence, reviewer=review_binding["reviewer"], decision=review_binding["decision"],
            reviewed_at=reviewed_at,
            token_count_plausible=review_binding["token_count_plausible"],
            cost_within_limit=review_binding["cost_within_limit"],
            frozen_bindings_confirmed=review_binding["frozen_bindings_confirmed"],
            evidence_history_confirmed=review_binding["evidence_history_confirmed"],
            notes=review_binding["bounded_notes"], now=reviewed_at,
        )
        if review != expected_review:
            raise PreflightResultError("preflight review does not match the canonical review contract")
    closed = parse_time(closure["immutable_binding"]["closed_at"])
    if closure != build_closure(binding["case_id"], result, evidence, review, closed):
        raise PreflightResultError("preflight phase closure does not match its result/review lifecycle")
