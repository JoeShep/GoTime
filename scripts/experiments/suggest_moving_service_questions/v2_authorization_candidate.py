"""Offline-only validation for the inactive v2 authorization review package."""

from __future__ import annotations

import hashlib
import json
import tomllib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

from v2_follow_up_authorization import load_verified_v2_package

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
REVIEW_ROOT = (
    REPOSITORY_ROOT
    / "docs/experiments/suggest-moving-service-questions/v2-pilot/authorization-review"
)
CANDIDATE_PATH = REVIEW_ROOT / "inactive-authorization-candidate.toml"
CANDIDATE_MANIFEST_PATH = REVIEW_ROOT / "authorization-candidate-manifest.json"
EXECUTION_MANIFEST_PATH = (
    REPOSITORY_ROOT
    / "docs/experiments/suggest-moving-service-questions/v2-pilot/execution-manifest.json"
)
CLOSED_MANIFEST_PATH = EXECUTION_MANIFEST_PATH.with_name("closed-execution-manifest.json")
PLACEHOLDERS = frozenset(
    {"APPROVER_ID_REQUIRED", "APPROVED_AT_UTC_REQUIRED", "ACTIVATED_AT_UTC_REQUIRED", "EXPIRES_AT_UTC_REQUIRED"}
)


class V2AuthorizationCandidateError(ValueError):
    """The inactive review package failed closed."""


@dataclass(frozen=True)
class VerifiedInactiveCandidate:
    path: Path
    digest: str
    artifact: Mapping[str, object]
    blockers: tuple[str, ...]


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _parse_utc(value: object, field: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise V2AuthorizationCandidateError(f"{field} must be exact UTC.")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as error:
        raise V2AuthorizationCandidateError(f"{field} is invalid.") from error
    if parsed.microsecond:
        raise V2AuthorizationCandidateError(f"{field} must use whole seconds.")
    return parsed


def validate_activation_values(
    *, approver: str, approved_at: str, activated_at: str, expires_at: str, now: datetime
) -> None:
    """Validate future rendered values without creating repository authority."""
    if not approver.strip() or approver in PLACEHOLDERS:
        raise V2AuthorizationCandidateError("Exact approver identity is required.")
    if any(value in PLACEHOLDERS for value in (approved_at, activated_at, expires_at)):
        raise V2AuthorizationCandidateError("Timestamp placeholders cannot activate.")
    approved = _parse_utc(approved_at, "approved_at")
    activated = _parse_utc(activated_at, "activated_at")
    expires = _parse_utc(expires_at, "expires_at")
    if not approved <= activated < expires:
        raise V2AuthorizationCandidateError("Authorization timestamps are out of order.")
    if (expires - activated).total_seconds() > 900:
        raise V2AuthorizationCandidateError("Authorization window exceeds 900 seconds.")
    if not activated <= now < expires:
        raise V2AuthorizationCandidateError("Rendered authorization is expired or not active.")


def validate_candidate_artifact(
    artifact: Mapping[str, object], *, repository_root: Path = REPOSITORY_ROOT
) -> tuple[str, ...]:
    if set(artifact) != {
        "metadata", "bindings", "authorization", "proposed_authorization", "scope",
        "approval", "consumption", "paths", "activation",
    }:
        raise V2AuthorizationCandidateError("Candidate sections are missing or unknown.")
    metadata = artifact["metadata"]
    if metadata != {
        "capability": "suggest_moving_service_questions",
        "authorization_version": "moving-service-openai-v2-follow-up-authorization-v1",
        "authorization_status": "inactive_review_candidate",
        "evaluation_only": True,
        "default_deny": True,
        "active_repository_authority": False,
        "valid_for_execution": False,
        "requires_separate_human_approval": True,
        "requires_separate_activation": True,
    }:
        raise V2AuthorizationCandidateError("Candidate metadata is not inactive.")
    if artifact["authorization"] != {
        "credential_access_authorized": False,
        "token_preflight_authorized": False,
        "ai_generation_authorized": False,
        "formal_evaluation_authorized": False,
        "stage_c_authorized": False,
        "production_use_authorized": False,
    }:
        raise V2AuthorizationCandidateError("Candidate itself grants authority.")
    if artifact["proposed_authorization"] != {
        "credential_access_authorized": True,
        "token_preflight_authorized": True,
        "ai_generation_authorized": True,
        "formal_evaluation_authorized": False,
        "stage_c_authorized": False,
        "production_use_authorized": False,
    }:
        raise V2AuthorizationCandidateError("Proposed permissions broadened or drifted.")
    scope = artifact["scope"]
    if scope != {
        "run_series_id": "moving-service-stage-b-v2-pilot-20260802",
        "sequence": 1,
        "fixture_id": "storage_unknown",
        "credential_environment_variable": "GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY",
        "operator_enablement_variable": "GOTIME_MOVING_SERVICE_EVAL_ENABLED",
        "required_operator_enablement_value": "1",
        "operator_intent": "AUTHORIZE_ONE_STORAGE_UNKNOWN_V2_PREFLIGHT_AND_GENERATION",
        "maximum_credential_reads": 1,
        "maximum_client_constructions": 1,
        "maximum_token_preflight_requests": 1,
        "maximum_ai_generation_requests": 1,
        "automatic_retries": 0,
        "token_preflight_timeout_seconds": 5,
        "ai_generation_timeout_seconds": 12,
        "maximum_output_tokens": 500,
        "maximum_total_spend_usd": "0.03",
        "human_grounding_review_required": True,
        "single_use": True,
    }:
        raise V2AuthorizationCandidateError("Candidate scope drifted.")
    consumption = artifact["consumption"]
    if consumption != {
        "consumed_at_earliest_attempt_stage": True,
        "consumption_stages": [
            "credential_lookup_attempt", "client_construction_attempt", "token_preflight_attempt",
            "ai_generation_attempt", "expiration", "operator_cancellation",
            "bounded_failure_after_activation",
        ],
        "reuse_after_consumption": False,
        "return_to_unused_active_state": False,
        "closure_restores_permanent_closed_authorization": True,
    }:
        raise V2AuthorizationCandidateError("Single-use policy drifted.")
    bindings = artifact["bindings"]
    required_binding_files = {
        "frozen_v2_manifest_path": "frozen_v2_manifest_digest",
        "prompt_path": "prompt_digest",
        "provider_schema_path": "provider_schema_digest",
        "provider_schema_review_path": "provider_schema_review_digest",
        "schema_adaptation_path": "schema_adaptation_digest",
        "deterministic_baseline_path": "deterministic_baseline_digest",
        "request_fixtures_path": "request_fixtures_digest",
        "response_fixtures_path": "response_fixtures_digest",
        "expected_results_path": "expected_results_digest",
        "pilot_configuration_path": "pilot_configuration_digest",
        "closed_execution_manifest_path": "closed_execution_manifest_digest",
        "permanent_closed_authorization_path": "permanent_closed_authorization_digest",
    }
    if set(bindings) != {
        *required_binding_files.keys(), *required_binding_files.values(),
        "prompt_version", "schema_version", "fallback_version", "provider",
        "ai_model_identifier", "sdk_pin",
    }:
        raise V2AuthorizationCandidateError("Candidate binding fields are missing or unknown.")
    for path_key, digest_key in required_binding_files.items():
        path = (repository_root / str(bindings.get(path_key))).resolve()
        if not path.is_relative_to(repository_root.resolve()) or _digest(path) != bindings.get(digest_key):
            raise V2AuthorizationCandidateError(f"Candidate binding drifted: {path_key}.")
    expected_identities = {
        "prompt_version": "moving-service-questions-prompt-v2",
        "schema_version": "moving-service-questions-schema-v2",
        "fallback_version": "moving-service-fallback-v2",
        "provider": "OpenAI",
        "ai_model_identifier": "gpt-4.1-mini-2025-04-14",
        "sdk_pin": "openai==2.45.0",
    }
    if any(bindings.get(key) != value for key, value in expected_identities.items()):
        raise V2AuthorizationCandidateError("Candidate frozen identity drifted.")
    approval = artifact["approval"]
    if approval != {
        "approval_status": "pending_explicit_human_approval",
        "approver": "APPROVER_ID_REQUIRED",
        "approved_at": "APPROVED_AT_UTC_REQUIRED",
        "activated_at": "ACTIVATED_AT_UTC_REQUIRED",
        "expires_at": "EXPIRES_AT_UTC_REQUIRED",
        "maximum_authorization_duration_seconds": 900,
        "authorization_reason": "One controlled v2 follow-up pilot for prompt and prose-validation review",
    }:
        raise V2AuthorizationCandidateError("Candidate approval placeholders drifted.")
    if artifact["paths"] != {
        "audit_path": ".local/evaluations/suggest-moving-service-questions/moving-service-stage-b-v2-pilot-20260802/001-storage_unknown-generation-pilot.json",
        "response_evidence_path": ".local/evaluations/suggest-moving-service-questions/moving-service-stage-b-v2-pilot-20260802/001-storage_unknown-reviewed-response.json",
        "deletion_record_path": ".local/evaluations/suggest-moving-service-questions/moving-service-stage-b-v2-pilot-20260802/001-storage_unknown-evidence-deletion.json",
        "closure_path": ".local/evaluations/suggest-moving-service-questions/moving-service-stage-b-v2-pilot-20260802/001-storage_unknown-generation-pilot-closure.json",
        "response_evidence_retention_days": 30,
        "delete_immediately_after_review_signoff": True,
    }:
        raise V2AuthorizationCandidateError("Candidate record paths drifted.")
    if artifact["activation"] != {
        "candidate_must_not_replace_closed_authorization": True,
        "candidate_digest_required": True,
        "clean_working_tree_required": True,
        "frozen_integrity_required": True,
        "closed_state_required": True,
        "unconsumed_sequence_required": True,
        "conflicting_local_records_prohibited": True,
        "separate_preflight_and_generation_approval_required": True,
    }:
        raise V2AuthorizationCandidateError("Candidate activation policy drifted.")
    return ("approver_identity", "approved_at", "activated_at", "expires_at", "human_approval", "activation")


def load_inactive_candidate_package(
    *, repository_root: Path = REPOSITORY_ROOT,
    candidate_manifest_path: Path = CANDIDATE_MANIFEST_PATH,
) -> VerifiedInactiveCandidate:
    manifest = json.loads(candidate_manifest_path.read_text(encoding="utf-8"))
    expected_keys = {
        "capability", "package_version", "package_status", "candidate_path",
        "candidate_digest_algorithm", "candidate_digest", "candidate_activated",
        "permanent_closed_execution_manifest_path", "permanent_closed_execution_manifest_digest",
        "permanent_closed_authorization_path", "permanent_closed_authorization_digest",
        "human_approval_required", "separate_activation_required", "credential_access_authorized",
        "token_preflight_authorized", "ai_generation_authorized", "formal_evaluation_authorized",
        "stage_c_authorized", "production_use_authorized",
    }
    if set(manifest) != expected_keys or manifest["package_status"] != "inactive_non_authoritative_review_candidate":
        raise V2AuthorizationCandidateError("Candidate manifest drifted.")
    if {
        "capability": manifest["capability"],
        "package_version": manifest["package_version"],
        "candidate_digest_algorithm": manifest["candidate_digest_algorithm"],
        "human_approval_required": manifest["human_approval_required"],
        "separate_activation_required": manifest["separate_activation_required"],
    } != {
        "capability": "suggest_moving_service_questions",
        "package_version": "moving-service-openai-v2-authorization-review-v1",
        "candidate_digest_algorithm": "sha256",
        "human_approval_required": True,
        "separate_activation_required": True,
    }:
        raise V2AuthorizationCandidateError("Candidate package identity drifted.")
    if any(manifest[key] is not False for key in (
        "candidate_activated", "credential_access_authorized", "token_preflight_authorized",
        "ai_generation_authorized", "formal_evaluation_authorized", "stage_c_authorized",
        "production_use_authorized",
    )):
        raise V2AuthorizationCandidateError("Candidate manifest grants authority.")
    candidate = (repository_root / manifest["candidate_path"]).resolve()
    if _digest(candidate) != manifest["candidate_digest"]:
        raise V2AuthorizationCandidateError("Candidate digest drifted.")
    closed_manifest = (
        repository_root / manifest["permanent_closed_execution_manifest_path"]
    ).resolve()
    closed_authorization = (
        repository_root / manifest["permanent_closed_authorization_path"]
    ).resolve()
    if (
        _digest(closed_manifest)
        != manifest["permanent_closed_execution_manifest_digest"]
        or _digest(closed_authorization)
        != manifest["permanent_closed_authorization_digest"]
    ):
        raise V2AuthorizationCandidateError("Permanent closed package digest drifted.")
    if EXECUTION_MANIFEST_PATH.read_bytes() != CLOSED_MANIFEST_PATH.read_bytes():
        raise V2AuthorizationCandidateError("Permanent execution manifest is not closed.")
    load_verified_v2_package(EXECUTION_MANIFEST_PATH, repository_root=repository_root)
    artifact = tomllib.loads(candidate.read_text(encoding="utf-8"))
    blockers = validate_candidate_artifact(artifact, repository_root=repository_root)
    return VerifiedInactiveCandidate(candidate, manifest["candidate_digest"], artifact, blockers)


def dry_run_activation_readiness(environment: Mapping[str, str] | None = None) -> Mapping[str, object]:
    """Report non-secret blockers without reading the supplied environment."""
    verified = load_inactive_candidate_package()
    return {
        "candidate_digest": verified.digest,
        "inactive": True,
        "active_repository_authority": False,
        "environment_inspected": False,
        "client_constructed": False,
        "network_request_made": False,
        "blockers": list(verified.blockers),
    }
