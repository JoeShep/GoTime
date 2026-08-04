"""Offline validation shapes for separate v2 preflight and generation authority."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Mapping

from v2_follow_up_authorization import FIXTURE_ID, RUN_SERIES_ID, SEQUENCE

PHASES = frozenset({"preflight", "generation"})


class V2TwoGateAuthorizationError(ValueError):
    pass


@dataclass(frozen=True)
class VerifiedV2PhaseAuthorization:
    phase: str
    digest: str
    approved_at: datetime
    expires_at: datetime
    evidence_digest: str | None = None
    review_digest: str | None = None
    input_tokens: int | None = None
    conservative_cost: Decimal | None = None
    request_digest: str | None = None
    canonical_attempt_digest: str | None = None
    provider_fingerprint: str | None = None


def _utc(value: object, field: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise V2TwoGateAuthorizationError(f"{field} must be exact UTC.")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as error:
        raise V2TwoGateAuthorizationError(f"{field} is invalid.") from error
    if parsed.microsecond:
        raise V2TwoGateAuthorizationError(f"{field} must use whole seconds.")
    return parsed


def validate_phase_authorization(
    artifact: Mapping[str, object], *, digest: str, phase: str, now: datetime,
    expected_bindings: Mapping[str, object], expected_sequence: int = SEQUENCE,
) -> VerifiedV2PhaseAuthorization:
    """Validate one exact temporary artifact without reading repository state."""
    if phase not in PHASES or set(artifact) != {
        "metadata", "bindings", "authorization", "scope", "approval", "evidence_binding"
    }:
        raise V2TwoGateAuthorizationError("Two-gate authorization shape drifted.")
    metadata = artifact["metadata"]
    if metadata != {
        "capability": "suggest_moving_service_questions",
        "authorization_version": "moving-service-openai-v2-two-gate-authorization-v1",
        "authorization_status": f"approved_v2_{phase}",
        "phase": phase,
        "evaluation_only": True,
        "active_repository_authority": True,
    }:
        raise V2TwoGateAuthorizationError("Two-gate metadata drifted.")
    bindings = artifact["bindings"]
    if bindings != dict(expected_bindings):
        raise V2TwoGateAuthorizationError("Frozen two-gate bindings drifted.")
    expected_permissions = {
        "credential_access_authorized": True,
        "token_preflight_authorized": phase == "preflight",
        "ai_generation_authorized": phase == "generation",
        "formal_evaluation_authorized": False,
        "stage_c_authorized": False,
        "production_use_authorized": False,
    }
    if artifact["authorization"] != expected_permissions:
        raise V2TwoGateAuthorizationError("Phase permissions overlap or broadened.")
    expected_scope = {
        "run_series_id": RUN_SERIES_ID,
        "sequence": expected_sequence,
        "fixture_id": FIXTURE_ID,
        "maximum_credential_reads": 1,
        "maximum_client_constructions": 1,
        "maximum_token_preflight_requests": 1 if phase == "preflight" else 0,
        "maximum_ai_generation_requests": 0 if phase == "preflight" else 1,
        "automatic_retries": 0,
        "maximum_total_spend_usd": "0.03",
        "single_use": True,
    }
    if artifact["scope"] != expected_scope:
        raise V2TwoGateAuthorizationError("Two-gate scope drifted.")
    approval = artifact["approval"]
    if set(approval) != {
        "approver", "approved_at", "activated_at", "expires_at",
        "maximum_duration_seconds", "authorization_reason",
    }:
        raise V2TwoGateAuthorizationError("Approval fields drifted.")
    if not isinstance(approval["approver"], str) or not approval["approver"].strip():
        raise V2TwoGateAuthorizationError("Approver is required.")
    if not isinstance(approval["authorization_reason"], str) or not approval["authorization_reason"].strip():
        raise V2TwoGateAuthorizationError("Authorization reason is required.")
    approved = _utc(approval["approved_at"], "approved_at")
    activated = _utc(approval["activated_at"], "activated_at")
    expires = _utc(approval["expires_at"], "expires_at")
    if (
        approval["maximum_duration_seconds"] != 900
        or (expires - activated).total_seconds() > 900
        or not approved <= activated < expires
    ):
        raise V2TwoGateAuthorizationError("Authorization window exceeds 900 seconds.")
    if not activated <= now < expires:
        raise V2TwoGateAuthorizationError("Authorization is expired or not active.")
    evidence = artifact["evidence_binding"]
    if phase == "preflight":
        if evidence != {
            "preflight_evidence_digest": "not_applicable",
            "preflight_review_digest": "not_applicable",
            "input_tokens": 0,
            "conservative_cost": "0.00",
            "request_digest": "not_applicable",
            "canonical_attempt_digest": "not_applicable",
            "provider_fingerprint": "not_applicable",
            "preflight_reviewer": "not_applicable",
            "preflight_reviewed_at": "not_applicable",
        }:
            raise V2TwoGateAuthorizationError("Preflight authority cannot bind generation evidence.")
        return VerifiedV2PhaseAuthorization(phase, digest, approved, expires)
    if set(evidence) != {
        "preflight_evidence_digest", "preflight_review_digest", "input_tokens",
        "conservative_cost", "request_digest", "canonical_attempt_digest",
        "provider_fingerprint", "preflight_reviewer", "preflight_reviewed_at",
    }:
        raise V2TwoGateAuthorizationError("Generation evidence binding drifted.")
    if not all(isinstance(evidence[key], str) and len(evidence[key]) == 64 for key in (
        "preflight_evidence_digest", "preflight_review_digest"
    )):
        raise V2TwoGateAuthorizationError("Generation evidence digests are invalid.")
    if not isinstance(evidence["input_tokens"], int) or evidence["input_tokens"] <= 0:
        raise V2TwoGateAuthorizationError("Generation input-token binding is invalid.")
    cost = Decimal(str(evidence["conservative_cost"]))
    if cost < 0 or cost > Decimal("0.03"):
        raise V2TwoGateAuthorizationError("Generation cost binding is invalid.")
    for key in ("request_digest", "canonical_attempt_digest", "provider_fingerprint"):
        if not isinstance(evidence[key], str) or len(evidence[key]) != 64:
            raise V2TwoGateAuthorizationError("Generation attempt binding is invalid.")
    if not isinstance(evidence["preflight_reviewer"], str) or not evidence["preflight_reviewer"].strip():
        raise V2TwoGateAuthorizationError("Preflight reviewer binding is invalid.")
    reviewed_at = _utc(evidence["preflight_reviewed_at"], "preflight_reviewed_at")
    if approved < reviewed_at or activated < reviewed_at:
        raise V2TwoGateAuthorizationError("Generation authority predates preflight review.")
    return VerifiedV2PhaseAuthorization(
        phase, digest, approved, expires,
        str(evidence["preflight_evidence_digest"]), str(evidence["preflight_review_digest"]),
        int(evidence["input_tokens"]), cost, str(evidence["request_digest"]),
        str(evidence["canonical_attempt_digest"]), str(evidence["provider_fingerprint"]),
    )
