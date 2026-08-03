"""Offline-only loaders and renderers for the two v2 phase candidates."""

from __future__ import annotations

import hashlib
import json
import os
import tomllib
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Mapping

from run_openai_stage_b_v2_pilot import prepare_frozen_v2_pilot
from run_openai_stage_b_v2_two_gate import frozen_binding_identity
from v2_authorization_candidate import load_inactive_candidate_package
from v2_two_gate_authorization import validate_phase_authorization

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = REPOSITORY_ROOT / (
    "docs/experiments/suggest-moving-service-questions/v2-pilot/"
    "authorization-review/phase-candidates"
)
MANIFEST_PATH = PACKAGE_ROOT / "phase-candidate-manifest.json"
PHASE_PATHS = {
    "preflight": PACKAGE_ROOT / "inactive-preflight-authorization-candidate.toml",
    "generation": PACKAGE_ROOT / "inactive-generation-authorization-candidate.toml",
}
UMBRELLA_DIGEST = "cee4cdb826452906ea677785b1b76cf43745d28237a791d4c129175a0447062a"
SHARED_PLACEHOLDERS = frozenset({
    "APPROVER_ID_REQUIRED", "APPROVED_AT_UTC_REQUIRED", "ACTIVATED_AT_UTC_REQUIRED",
    "EXPIRES_AT_UTC_REQUIRED", "AUTHORIZATION_REASON_REQUIRED",
})
GENERATION_PLACEHOLDERS = frozenset({
    "PREFLIGHT_EVIDENCE_DIGEST_REQUIRED", "PREFLIGHT_REVIEW_RECORD_DIGEST_REQUIRED",
    "PREFLIGHT_INPUT_TOKEN_COUNT_REQUIRED", "PREFLIGHT_CONSERVATIVE_COST_REQUIRED",
    "PREFLIGHT_REQUEST_DIGEST_REQUIRED", "PREFLIGHT_CANONICAL_ATTEMPT_DIGEST_REQUIRED",
    "PREFLIGHT_PROVIDER_FINGERPRINT_REQUIRED", "PREFLIGHT_REVIEWER_ID_REQUIRED",
    "PREFLIGHT_REVIEWED_AT_UTC_REQUIRED",
})


class V2PhaseCandidateError(ValueError):
    """A phase candidate or dry-run rendering failed closed."""


@dataclass(frozen=True)
class VerifiedPhaseCandidate:
    phase: str
    path: Path
    digest: str
    artifact: Mapping[str, object]
    unresolved_placeholders: tuple[str, ...]


@dataclass(frozen=True)
class RenderedPhaseAuthorization:
    phase: str
    path: Path
    digest: str
    artifact: Mapping[str, object]


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_regular(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise V2PhaseCandidateError("Phase-candidate path must be a regular file.")
    return path.read_bytes()


def _parse_utc(value: object, field: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise V2PhaseCandidateError(f"{field} must be whole-second UTC.")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as error:
        raise V2PhaseCandidateError(f"{field} is invalid.") from error
    if parsed.microsecond or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise V2PhaseCandidateError(f"{field} must be whole-second UTC.")
    return parsed


def _validate_timing(
    *, approved_at: str, activated_at: str, expires_at: str, now: datetime,
    reviewed_at: datetime | None = None,
) -> tuple[datetime, datetime, datetime]:
    if now.tzinfo is None:
        raise V2PhaseCandidateError("Injected clock must include a timezone.")
    approved = _parse_utc(approved_at, "approved_at")
    activated = _parse_utc(activated_at, "activated_at")
    expires = _parse_utc(expires_at, "expires_at")
    if approved > now.astimezone(timezone.utc):
        raise V2PhaseCandidateError("Approval timestamp is in the future.")
    if not approved <= activated < expires:
        raise V2PhaseCandidateError("Authorization timestamps are out of order.")
    if (expires - activated).total_seconds() > 900:
        raise V2PhaseCandidateError("Authorization window exceeds 900 seconds.")
    if not activated <= now.astimezone(timezone.utc) < expires:
        raise V2PhaseCandidateError("Authorization is expired or not active.")
    if reviewed_at is not None and (approved < reviewed_at or activated < reviewed_at):
        raise V2PhaseCandidateError("Generation authorization predates preflight review.")
    return approved, activated, expires


def _expected_candidate_metadata(phase: str) -> dict[str, object]:
    return {
        "capability": "suggest_moving_service_questions",
        "candidate_version": f"moving-service-openai-v2-{phase}-candidate-v1",
        "candidate_status": "inactive_non_authoritative", "phase": phase,
        "active_repository_authority": False, "valid_for_execution": False,
        "placeholder_bound": True, "requires_separate_human_approval": True,
        "requires_separate_active_rendering": True,
        "may_replace_permanent_closed_authorization": False,
    }


def _expected_permissions(phase: str, *, proposed: bool) -> dict[str, bool]:
    return {
        "credential_access_authorized": proposed,
        "token_preflight_authorized": proposed and phase == "preflight",
        "ai_generation_authorized": proposed and phase == "generation",
        "formal_evaluation_authorized": False, "stage_c_authorized": False,
        "production_use_authorized": False, "fastapi_exposure_authorized": False,
        "frontend_exposure_authorized": False, "recurring_execution_authorized": False,
        "background_execution_authorized": False,
    }


def _expected_scope(phase: str) -> dict[str, object]:
    return {
        "run_series_id": "moving-service-stage-b-v2-pilot-20260802", "sequence": 1,
        "fixture_id": "storage_unknown",
        "credential_environment_variable": "GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY",
        "operator_enablement_variable": "GOTIME_MOVING_SERVICE_EVAL_ENABLED",
        "required_operator_enablement_value": "1",
        "operator_intent": f"AUTHORIZE_ONE_STORAGE_UNKNOWN_V2_{phase.upper()}_ONLY",
        "maximum_credential_reads": 1, "maximum_client_constructions": 1,
        "maximum_token_preflight_requests": 1 if phase == "preflight" else 0,
        "maximum_ai_generation_requests": 0 if phase == "preflight" else 1,
        "automatic_retries": 0, "token_preflight_timeout_seconds": 5,
        "ai_generation_timeout_seconds": 12, "maximum_output_tokens": 500,
        "maximum_total_spend_usd": "0.03", "human_grounding_review_required": True,
        "single_use": True,
    }


def _expected_consumption(phase: str) -> dict[str, object]:
    phase_stage = "token_preflight_attempt" if phase == "preflight" else "preflight_evidence_consumption"
    later_stage = [] if phase == "preflight" else ["ai_generation_attempt"]
    return {
        "consumed_at_earliest_attempt_stage": True,
        "consumption_stages": [
            "credential_lookup_attempt", "client_construction_attempt", phase_stage,
            *later_stage, "expiration", "operator_cancellation_after_activation",
            "bounded_failure_after_activation",
        ],
        "reuse_after_consumption": False, "return_to_unused_active_state": False,
        "closure_restores_permanent_closed_authorization": True,
    }


def _verify_candidate_bindings(bindings: Mapping[str, object]) -> None:
    umbrella = load_inactive_candidate_package()
    expected = dict(umbrella.artifact["bindings"])
    expected.update({
        "umbrella_candidate_path": str(umbrella.path.relative_to(REPOSITORY_ROOT)),
        "umbrella_candidate_digest": UMBRELLA_DIGEST,
    })
    if bindings != expected or umbrella.digest != UMBRELLA_DIGEST:
        raise V2PhaseCandidateError("Phase candidate broadened or drifted frozen bindings.")


def validate_inactive_phase_candidate(
    artifact: Mapping[str, object], *, phase: str,
) -> tuple[str, ...]:
    if phase not in PHASE_PATHS or set(artifact) != {
        "metadata", "bindings", "authorization", "proposed_authorization", "scope",
        "approval", "evidence_binding", "consumption",
    }:
        raise V2PhaseCandidateError("Phase-candidate shape drifted.")
    if artifact["metadata"] != _expected_candidate_metadata(phase):
        raise V2PhaseCandidateError("Candidate is not inactive and phase-specific.")
    if artifact["authorization"] != _expected_permissions(phase, proposed=False):
        raise V2PhaseCandidateError("Inactive candidate grants authority.")
    if artifact["proposed_authorization"] != _expected_permissions(phase, proposed=True):
        raise V2PhaseCandidateError("Proposed phase permissions overlap or broadened.")
    if artifact["scope"] != _expected_scope(phase):
        raise V2PhaseCandidateError("Candidate phase scope drifted.")
    if artifact["consumption"] != _expected_consumption(phase):
        raise V2PhaseCandidateError("Candidate single-use policy drifted.")
    _verify_candidate_bindings(artifact["bindings"])
    approval = artifact["approval"]
    expected_approval = {
        "approval_status": "unresolved_inactive_candidate", "approver": "APPROVER_ID_REQUIRED",
        "approved_at": "APPROVED_AT_UTC_REQUIRED", "activated_at": "ACTIVATED_AT_UTC_REQUIRED",
        "expires_at": "EXPIRES_AT_UTC_REQUIRED", "maximum_authorization_duration_seconds": 900,
        "authorization_reason": "AUTHORIZATION_REASON_REQUIRED",
    }
    if approval != expected_approval:
        raise V2PhaseCandidateError("Candidate approval placeholders drifted.")
    evidence = artifact["evidence_binding"]
    if phase == "preflight":
        expected_evidence = {
            "preflight_evidence_digest": "not_applicable", "preflight_review_digest": "not_applicable",
            "input_tokens": 0, "conservative_cost": "0.00", "request_digest": "not_applicable",
            "canonical_attempt_digest": "not_applicable", "provider_fingerprint": "not_applicable",
            "preflight_reviewer": "not_applicable", "preflight_reviewed_at": "not_applicable",
        }
        if evidence != expected_evidence:
            raise V2PhaseCandidateError("Preflight candidate contains generation evidence.")
        return tuple(sorted(SHARED_PLACEHOLDERS))
    expected_generation = {
        "preflight_evidence_digest": "PREFLIGHT_EVIDENCE_DIGEST_REQUIRED",
        "preflight_review_digest": "PREFLIGHT_REVIEW_RECORD_DIGEST_REQUIRED",
        "input_tokens": "PREFLIGHT_INPUT_TOKEN_COUNT_REQUIRED",
        "conservative_cost": "PREFLIGHT_CONSERVATIVE_COST_REQUIRED",
        "request_digest": "PREFLIGHT_REQUEST_DIGEST_REQUIRED",
        "canonical_attempt_digest": "PREFLIGHT_CANONICAL_ATTEMPT_DIGEST_REQUIRED",
        "provider_fingerprint": "PREFLIGHT_PROVIDER_FINGERPRINT_REQUIRED",
        "preflight_reviewer": "PREFLIGHT_REVIEWER_ID_REQUIRED",
        "preflight_reviewed_at": "PREFLIGHT_REVIEWED_AT_UTC_REQUIRED",
    }
    if evidence != expected_generation:
        raise V2PhaseCandidateError("Generation evidence placeholders drifted.")
    return tuple(sorted(SHARED_PLACEHOLDERS | GENERATION_PLACEHOLDERS))


def load_inactive_phase_candidate(phase: str) -> VerifiedPhaseCandidate:
    if phase not in PHASE_PATHS:
        raise V2PhaseCandidateError("Unknown authorization phase.")
    manifest_bytes = _read_regular(MANIFEST_PATH)
    manifest = json.loads(manifest_bytes)
    expected_keys = {
        "capability", "package_version", "package_status", "digest_algorithm",
        "umbrella_candidate_path", "umbrella_candidate_digest", "preflight_candidate_path",
        "preflight_candidate_digest", "generation_candidate_path", "generation_candidate_digest",
        "active_repository_authority", "valid_for_execution", "separate_human_approval_required",
        "separate_active_rendering_required", "credential_access_authorized",
        "token_preflight_authorized", "ai_generation_authorized", "formal_evaluation_authorized",
        "stage_c_authorized", "production_use_authorized",
    }
    if set(manifest) != expected_keys or manifest["package_status"] != "inactive_non_authoritative":
        raise V2PhaseCandidateError("Phase-candidate manifest drifted.")
    if {
        "capability": manifest["capability"], "package_version": manifest["package_version"],
        "digest_algorithm": manifest["digest_algorithm"],
        "separate_human_approval_required": manifest["separate_human_approval_required"],
        "separate_active_rendering_required": manifest["separate_active_rendering_required"],
    } != {
        "capability": "suggest_moving_service_questions",
        "package_version": "moving-service-openai-v2-phase-candidates-v1",
        "digest_algorithm": "sha256", "separate_human_approval_required": True,
        "separate_active_rendering_required": True,
    }:
        raise V2PhaseCandidateError("Phase-candidate package identity drifted.")
    if any(manifest[key] is not False for key in (
        "active_repository_authority", "valid_for_execution", "credential_access_authorized",
        "token_preflight_authorized", "ai_generation_authorized", "formal_evaluation_authorized",
        "stage_c_authorized", "production_use_authorized",
    )):
        raise V2PhaseCandidateError("Phase-candidate manifest grants authority.")
    if manifest["umbrella_candidate_digest"] != UMBRELLA_DIGEST:
        raise V2PhaseCandidateError("Umbrella candidate digest drifted.")
    candidate = PHASE_PATHS[phase]
    manifest_path = (REPOSITORY_ROOT / str(manifest[f"{phase}_candidate_path"])).resolve()
    if manifest_path != candidate.resolve():
        raise V2PhaseCandidateError("Phase-candidate path substitution rejected.")
    content = _read_regular(candidate)
    digest = hashlib.sha256(content).hexdigest()
    if digest != manifest[f"{phase}_candidate_digest"]:
        raise V2PhaseCandidateError("Phase-candidate digest drifted.")
    artifact = tomllib.loads(content.decode("utf-8"))
    blockers = validate_inactive_phase_candidate(artifact, phase=phase)
    return VerifiedPhaseCandidate(phase, candidate, digest, artifact, blockers)


def _toml_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        return json.dumps(value)
    raise V2PhaseCandidateError("Active artifact contains unsupported TOML value.")


def _serialize_toml(artifact: Mapping[str, object]) -> bytes:
    lines: list[str] = []
    for section, values in artifact.items():
        lines.append(f"[{section}]")
        for key, value in values.items():  # type: ignore[union-attr]
            lines.append(f"{key} = {_toml_value(value)}")
        lines.append("")
    return ("\n".join(lines).rstrip() + "\n").encode("utf-8")


def _safe_output(path: Path) -> Path:
    resolved = path.resolve()
    if not resolved.is_relative_to(Path("/tmp").resolve()) or path.exists():
        raise V2PhaseCandidateError("Dry-run output must be a new file under /tmp.")
    return resolved


def _active_artifact(
    *, phase: str, approver: str, approved_at: str, activated_at: str,
    expires_at: str, authorization_reason: str, evidence_binding: Mapping[str, object],
) -> dict[str, object]:
    prepared = prepare_frozen_v2_pilot()
    return {
        "metadata": {
            "capability": "suggest_moving_service_questions",
            "authorization_version": "moving-service-openai-v2-two-gate-authorization-v1",
            "authorization_status": f"approved_v2_{phase}", "phase": phase,
            "evaluation_only": True, "active_repository_authority": True,
        },
        "bindings": frozen_binding_identity(prepared),
        "authorization": {
            "credential_access_authorized": True,
            "token_preflight_authorized": phase == "preflight",
            "ai_generation_authorized": phase == "generation",
            "formal_evaluation_authorized": False, "stage_c_authorized": False,
            "production_use_authorized": False,
        },
        "scope": {
            "run_series_id": "moving-service-stage-b-v2-pilot-20260802", "sequence": 1,
            "fixture_id": "storage_unknown", "maximum_credential_reads": 1,
            "maximum_client_constructions": 1,
            "maximum_token_preflight_requests": 1 if phase == "preflight" else 0,
            "maximum_ai_generation_requests": 0 if phase == "preflight" else 1,
            "automatic_retries": 0, "maximum_total_spend_usd": "0.03", "single_use": True,
        },
        "approval": {
            "approver": approver, "approved_at": approved_at, "activated_at": activated_at,
            "expires_at": expires_at, "maximum_duration_seconds": 900,
            "authorization_reason": authorization_reason,
        },
        "evidence_binding": dict(evidence_binding),
    }


def _render(
    *, phase: str, output_path: Path, approver: str, approved_at: str,
    activated_at: str, expires_at: str, authorization_reason: str, now: datetime,
    evidence_binding: Mapping[str, object], reviewed_at: datetime | None = None,
) -> RenderedPhaseAuthorization:
    load_inactive_phase_candidate(phase)
    if not approver.strip() or approver in SHARED_PLACEHOLDERS:
        raise V2PhaseCandidateError("Exact approver identity is required.")
    if not authorization_reason.strip() or authorization_reason in SHARED_PLACEHOLDERS:
        raise V2PhaseCandidateError("Exact authorization reason is required.")
    _validate_timing(
        approved_at=approved_at, activated_at=activated_at, expires_at=expires_at,
        now=now, reviewed_at=reviewed_at,
    )
    artifact = _active_artifact(
        phase=phase, approver=approver, approved_at=approved_at, activated_at=activated_at,
        expires_at=expires_at, authorization_reason=authorization_reason,
        evidence_binding=evidence_binding,
    )
    content = _serialize_toml(artifact)
    digest = hashlib.sha256(content).hexdigest()
    validate_phase_authorization(
        artifact, digest=digest, phase=phase, now=now,
        expected_bindings=frozen_binding_identity(prepare_frozen_v2_pilot()),
    )
    destination = _safe_output(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(content)
    return RenderedPhaseAuthorization(phase, destination, digest, artifact)


def render_preflight_candidate(
    *, output_path: Path, approver: str, approved_at: str, activated_at: str,
    expires_at: str, authorization_reason: str, now: datetime,
) -> RenderedPhaseAuthorization:
    return _render(
        phase="preflight", output_path=output_path, approver=approver,
        approved_at=approved_at, activated_at=activated_at, expires_at=expires_at,
        authorization_reason=authorization_reason, now=now,
        evidence_binding={
            "preflight_evidence_digest": "not_applicable",
            "preflight_review_digest": "not_applicable", "input_tokens": 0,
            "conservative_cost": "0.00", "request_digest": "not_applicable",
            "canonical_attempt_digest": "not_applicable", "provider_fingerprint": "not_applicable",
            "preflight_reviewer": "not_applicable", "preflight_reviewed_at": "not_applicable",
        },
    )


def render_generation_candidate(
    *, output_path: Path, evidence_path: Path, review_path: Path, approver: str,
    approved_at: str, activated_at: str, expires_at: str, authorization_reason: str,
    now: datetime,
) -> RenderedPhaseAuthorization:
    load_inactive_phase_candidate("generation")
    evidence_bytes = _read_regular(evidence_path)
    review_bytes = _read_regular(review_path)
    evidence = json.loads(evidence_bytes)
    review = json.loads(review_bytes)
    evidence_digest = hashlib.sha256(evidence_bytes).hexdigest()
    review_digest = hashlib.sha256(review_bytes).hexdigest()
    if review.get("review_status") != "approved" or review.get("preflight_evidence_digest") != evidence_digest:
        raise V2PhaseCandidateError("Approved preflight review is required.")
    if evidence.get("consumed") is not False or evidence.get("human_review_status") != "pending":
        raise V2PhaseCandidateError("Preflight evidence is rejected, cancelled, or consumed.")
    reviewed_at = _parse_utc(review.get("reviewed_at"), "preflight_reviewed_at")
    deadline = _parse_utc(evidence.get("review_deadline"), "review_deadline")
    if now.astimezone(timezone.utc) >= deadline:
        raise V2PhaseCandidateError("Preflight evidence is expired.")
    prepared = prepare_frozen_v2_pilot()
    expected = {
        **frozen_binding_identity(prepared), "run_series_id": "moving-service-stage-b-v2-pilot-20260802",
        "sequence": 1, "fixture_id": "storage_unknown", "phase": "preflight",
    }
    if any(evidence.get(key) != value for key, value in expected.items()):
        raise V2PhaseCandidateError("Preflight evidence frozen binding drifted.")
    required_review_flags = (
        "token_count_plausible", "spend_within_ceiling", "frozen_bindings_match",
        "evidence_fresh_and_unused",
    )
    if not all(review.get(key) is True for key in required_review_flags):
        raise V2PhaseCandidateError("Preflight review did not approve every bounded check.")
    if any(review.get(key) != value for key, value in {
        "run_series_id": "moving-service-stage-b-v2-pilot-20260802", "sequence": 1,
        "fixture_id": "storage_unknown", "phase": "preflight_review",
    }.items()):
        raise V2PhaseCandidateError("Preflight review run identity drifted.")
    input_tokens = evidence.get("input_tokens")
    if not isinstance(input_tokens, int) or input_tokens <= 0:
        raise V2PhaseCandidateError("Preflight token count is invalid.")
    try:
        cost = Decimal(str(evidence.get("conservative_maximum_generation_cost")))
    except InvalidOperation as error:
        raise V2PhaseCandidateError("Preflight cost is invalid.") from error
    if cost < 0 or cost > Decimal("0.03"):
        raise V2PhaseCandidateError("Preflight cost exceeds the ceiling.")
    evidence_binding = {
        "preflight_evidence_digest": evidence_digest, "preflight_review_digest": review_digest,
        "input_tokens": input_tokens, "conservative_cost": str(cost),
        "request_digest": evidence.get("deterministic_request_digest"),
        "canonical_attempt_digest": evidence.get("canonical_attempt_digest"),
        "provider_fingerprint": evidence.get("provider_preflight_fingerprint"),
        "preflight_reviewer": review.get("reviewer"), "preflight_reviewed_at": review.get("reviewed_at"),
    }
    for key in ("request_digest", "canonical_attempt_digest", "provider_fingerprint"):
        if not isinstance(evidence_binding[key], str) or len(evidence_binding[key]) != 64:
            raise V2PhaseCandidateError(f"Preflight {key} is invalid.")
    return _render(
        phase="generation", output_path=output_path, approver=approver,
        approved_at=approved_at, activated_at=activated_at, expires_at=expires_at,
        authorization_reason=authorization_reason, now=now,
        evidence_binding=evidence_binding, reviewed_at=reviewed_at,
    )
