"""Scenario-specific assertions for the exact public sequence-4 rehearsal."""

from __future__ import annotations

import json
from pathlib import Path

PREFIX = "004-storage_unknown-generation-v4"
PROSE_CODES = [
    "irrelevant_location_reference",
    "unsupported_home_or_property_assertion",
    "storage_modality_overstatement",
    "unsupported_service_selection_language",
    "grounding_summary_mismatch",
]
ASSERTION_BACKED_SUMMARY_FIELDS = {
    "exact_public_commands_exercised",
    "synthetic_preflight_calls",
    "compliant_generation_calls",
    "prose_rejection_generation_calls",
    "structural_failure_generation_calls",
    "semantic_failure_generation_calls",
    "prompt_policy_stress_generation_calls",
    "compliant_validation_passed",
    "compliant_grounding_review",
    "prose_violation_codes_exact",
    "fallback_identity_exact",
    "structural_failure_classification",
    "semantic_failure_classification",
    "structural_semantic_distinction",
    "prompt_policy_stricter_than_validator",
    "permanent_closed_restored",
    "second_use_rejected",
}


class RehearsalAssertionError(AssertionError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RehearsalAssertionError(message)


def assert_rehearsal_scenario(*, state_root: Path, repository_root: Path,
                              scenario: str) -> dict[str, object]:
    """Assert one completed scenario solely from its emitted records."""
    audit_path = state_root / f"{PREFIX}-audit.json"
    closure_path = state_root / f"{PREFIX}-closure.json"
    transaction_path = state_root / f"{PREFIX}-activation-transaction.json"
    evidence_path = state_root / f"{PREFIX}-validated-response.json"
    review_path = state_root / f"{PREFIX}-grounding-review.json"
    deletion_path = state_root / f"{PREFIX}-evidence-deletion.json"
    active_path = state_root / f"{PREFIX}-authorization.toml"
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    closure = json.loads(closure_path.read_text(encoding="utf-8"))
    transaction = json.loads(transaction_path.read_text(encoding="utf-8"))
    _require(audit.get("sequence") == 4 and audit.get("phase") == "generation", "identity")
    _require(audit.get("preflight_attempted") is False, "preflight")
    _require(audit.get("generation_attempted") is True, "generation attempted")
    _require(audit.get("generation_request_count") == 1, "generation count")
    _require(audit.get("automatic_retries") == 0, "retries")
    _require(audit.get("authorization_consumed") is True, "consumption")
    _require(not active_path.exists(), "active authorization")
    _require(closure.get("authorization_closed") is True, "closure")
    _require(transaction.get("state") == "rolled_back", "transaction closure")
    _require((state_root / ".second-use-rejected").is_file(), "second use")
    _require((state_root / ".network-disabled").is_file(), "network isolation")
    current = repository_root / "docs/experiments/suggest-moving-service-questions/v2-pilot/execution-manifest.json"
    closed = current.with_name("closed-execution-manifest.json")
    _require(current.read_bytes() == closed.read_bytes(), "closed manifest")

    if scenario == "compliant":
        _require(audit.get("pydantic_validation_succeeded") is True, "compliant pydantic")
        _require(audit.get("semantic_validation_succeeded") is True, "compliant semantics")
        _require(audit.get("prose_validation_succeeded") is True, "compliant prose")
        _require(audit.get("prose_violation_codes") == [], "compliant prose codes")
        _require(audit.get("fallback_used") is False, "compliant fallback")
        _require(isinstance(audit.get("response_evidence_sha256"), str), "evidence digest")
        _require(review_path.is_file(), "grounding review")
        review = json.loads(review_path.read_text(encoding="utf-8"))
        _require(review.get("decision") == "approve", "grounding decision")
        _require(deletion_path.is_file(), "deletion record")
        deletion = json.loads(deletion_path.read_text(encoding="utf-8"))
        _require(deletion.get("deletion_completed") is True, "evidence deletion")
        _require(deletion.get("contains_response_content") is False, "deletion content")
        _require(set(deletion) == {
            "run_series_id", "sequence", "fixture_id", "evidence_path_identifier",
            "response_evidence_digest", "deletion_reason", "review_decision",
            "deleted_at", "deletion_completed", "contains_response_content",
        }, "bounded deletion record")
    elif scenario == "prose_rejection":
        _require(audit.get("pydantic_validation_succeeded") is True, "prose pydantic")
        _require(audit.get("semantic_validation_succeeded") is True, "prose semantics")
        _require(audit.get("prose_validation_succeeded") is False, "prose failure")
        _require(audit.get("validation_outcome") == "prose_failure", "prose classification")
        _require(audit.get("prose_violation_codes") == PROSE_CODES, "prose code order")
        _require(audit.get("complete_response_rejected") is True, "complete rejection")
        _require(audit.get("partial_salvage_used") is False, "partial salvage")
        _require(audit.get("fallback_used") is True, "fallback used")
        _require(audit.get("fallback_version") == "moving-service-fallback-v2", "fallback version")
        _require(audit.get("fallback_question_id") == "fallback-temporary-storage-v2", "fallback id")
        diagnostics = audit.get("rejected_prose_diagnostics")
        _require(isinstance(diagnostics, list) and diagnostics, "bounded prose diagnostics")
        bounded_keys = {
            "violation_code", "rule_id", "field", "start_offset", "end_offset",
            "canonical_trigger", "occurrence_count",
        }
        _require(all(isinstance(item, dict) and set(item) == bounded_keys
                     for item in diagnostics), "bounded diagnostic schema")
        _require("response" not in audit and "raw_response" not in audit,
                 "rejected prose retention")
    elif scenario == "structural_failure":
        _require(audit.get("pydantic_validation_succeeded") is False, "structural pydantic")
        _require(audit.get("semantic_validation_succeeded") is False, "structural semantics")
        _require(audit.get("prose_validation_succeeded") is False, "structural prose")
        _require(audit.get("validation_outcome") == "structural_failure", "structural classification")
        _require(audit.get("fallback_used") is True, "structural fallback")
        _require(audit.get("fallback_version") == "moving-service-fallback-v2", "structural fallback version")
        _require(audit.get("fallback_question_id") == "fallback-temporary-storage-v2", "structural fallback id")
        _require(audit.get("complete_response_rejected") is True, "structural rejection")
        _require(audit.get("partial_salvage_used") is False, "structural salvage")
    elif scenario == "semantic_failure":
        _require(audit.get("pydantic_validation_succeeded") is True, "semantic pydantic")
        _require(audit.get("semantic_validation_succeeded") is False, "semantic failure")
        _require(audit.get("prose_validation_succeeded") is False, "semantic prose")
        _require(audit.get("validation_outcome") == "semantic_failure", "semantic classification")
        _require(audit.get("fallback_used") is True, "semantic fallback")
        _require(audit.get("fallback_version") == "moving-service-fallback-v2", "semantic fallback version")
        _require(audit.get("fallback_question_id") == "fallback-temporary-storage-v2", "semantic fallback id")
        _require(audit.get("complete_response_rejected") is True, "semantic rejection")
        _require(audit.get("partial_salvage_used") is False, "semantic salvage")
    elif scenario == "prompt_policy_stress":
        _require(audit.get("pydantic_validation_succeeded") is True, "stress pydantic")
        _require(audit.get("semantic_validation_succeeded") is True, "stress semantics")
        _require(audit.get("prose_validation_succeeded") is True, "stress lexical result")
        _require(audit.get("prose_violation_codes") == [], "stress lexical codes")
        _require(review_path.is_file(), "stress grounding review")
        review = json.loads(review_path.read_text(encoding="utf-8"))
        _require(review.get("decision") == "request_changes", "stress policy decision")
        _require(deletion_path.is_file(), "stress deletion")
    else:
        raise RehearsalAssertionError("unknown scenario")
    _require(not evidence_path.exists(), "unexpected response evidence")
    return {"scenario": scenario, "assertions_passed": True}
