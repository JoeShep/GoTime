"""Offline-only preflight grant candidates with a fail-closed budget port."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Callable, Mapping

import v4_formal_evaluation_live_models as live_models
from v4_formal_evaluation_live_models import AGGREGATE_ID, digest, package_identity
from v4_formal_evaluation_live_state import format_time, parse_time

PREFLIGHT_GRANT_SCHEMA = "suggest-moving-service-questions-v4-formal-evaluation-preflight-grant-v1"
PREFLIGHT_GRANT_VERSION = 1
PREFLIGHT_GRANT_LIFETIME = timedelta(minutes=15)
PREFLIGHT_GRANT_STATES = ("prepared", "active", "consumed", "expired", "closed")


class PreflightGrantError(ValueError):
    pass


class BudgetAuthorizationUnavailable(PreflightGrantError):
    pass


def build_preflight_grant(
    case_id: str,
    envelope: Mapping[str, object],
    activated_at: datetime,
) -> dict[str, object]:
    immutable_envelope = envelope["immutable_binding"]
    if immutable_envelope["case_id"] != case_id:
        raise PreflightGrantError("grant case does not match its immutable AI envelope")
    activated = format_time(activated_at)
    expires = format_time(activated_at + PREFLIGHT_GRANT_LIFETIME)
    immutable = {
        "aggregate_id": AGGREGATE_ID,
        "aggregate_package_sha256": package_identity(),
        "case_id": case_id,
        "case_envelope_sha256": envelope["envelope_sha256"],
        "deterministic_case_input_sha256": immutable_envelope["deterministic_case_input_sha256"],
        "deterministic_request_sha256": immutable_envelope["deterministic_request_sha256"],
        "canonical_attempt_sha256": immutable_envelope["canonical_attempt_sha256"],
        "provider_fingerprint": immutable_envelope["provider_fingerprint"],
        "frozen_v4_manifest_sha256": immutable_envelope["frozen_v4_manifest_sha256"],
        "provider": immutable_envelope["provider"],
        "ai_model_identifier": immutable_envelope["ai_model_identifier"],
        "sdk": immutable_envelope["sdk"],
        "request_configuration": immutable_envelope["request_configuration"],
        "phase": "preflight",
        "conservative_operation_ceiling_usd": live_models.PER_CASE_PROVIDER_CEILING_USD,
        "per_case_provider_ceiling_usd": live_models.PER_CASE_PROVIDER_CEILING_USD,
        "maximum_attempts": 1,
        "maximum_retries": 0,
        "activated_at": activated,
        "expires_at": expires,
        "single_use": True,
    }
    identity = digest({
        "grant_schema": PREFLIGHT_GRANT_SCHEMA,
        "grant_version": PREFLIGHT_GRANT_VERSION,
        "immutable_binding": immutable,
    })
    return {
        "grant_schema": PREFLIGHT_GRANT_SCHEMA,
        "grant_version": PREFLIGHT_GRANT_VERSION,
        "grant_sha256": identity,
        "immutable_binding": immutable,
        "lifecycle": {
            "status": "prepared",
            "attempt_status": "unused",
            "budget_authorization": "unavailable_milestone_5",
            "provider_authority": False,
            "spending_authorized": False,
            "generation_authorized": False,
            "dispatch_authorized": False,
        },
    }


def validate_preflight_grant(
    grant: object,
    case_id: str,
    envelope: Mapping[str, object],
) -> None:
    if not isinstance(grant, dict):
        raise PreflightGrantError("preflight grant is malformed")
    try:
        activated = parse_time(grant["immutable_binding"]["activated_at"])
        expected = build_preflight_grant(case_id, envelope, activated)
    except (KeyError, TypeError) as error:
        raise PreflightGrantError("preflight grant is malformed") from error
    if grant != expected:
        raise PreflightGrantError("preflight grant does not match its exact frozen binding")
    if parse_time(grant["immutable_binding"]["expires_at"]) - activated != PREFLIGHT_GRANT_LIFETIME:
        raise PreflightGrantError("preflight grant lifetime is not exactly 15 minutes")


def grant_is_expired(grant: Mapping[str, object], now: datetime) -> bool:
    return now >= parse_time(grant["immutable_binding"]["expires_at"])


def deny_unimplemented_budget_authorization(_: Mapping[str, object]) -> bool:
    """Production/default Milestone 4 port: prospective accounting does not exist."""
    return False


def activate_preflight_grant(
    grant: Mapping[str, object],
    aggregate: Mapping[str, object],
    now: datetime,
) -> dict[str, object]:
    """Public runtime activation seam: unconditionally fail at Milestone 5's port."""
    return _activate_preflight_grant_synthetic(
        grant, aggregate, now, budget_authorize=deny_unimplemented_budget_authorization,
    )


def _activate_preflight_grant_synthetic(
    grant: Mapping[str, object],
    aggregate: Mapping[str, object],
    now: datetime,
    *,
    budget_authorize: Callable[[Mapping[str, object]], bool],
) -> dict[str, object]:
    """Test-only structural seam; never dispatches or persists provider authority."""
    case_id = grant["immutable_binding"]["case_id"]
    envelope = aggregate["ai_case_envelopes"].get(case_id)
    validate_preflight_grant(grant, case_id, envelope)
    if aggregate["status"] != "in_progress" or now >= parse_time(aggregate["expires_at"]):
        raise PreflightGrantError("aggregate is not active for preflight activation")
    if grant_is_expired(grant, now):
        raise PreflightGrantError("preflight grant is expired")
    if aggregate["next_case_id"] != case_id:
        raise PreflightGrantError("preflight grant no longer targets the next AI case")
    if not budget_authorize(grant):
        raise BudgetAuthorizationUnavailable(
            "prospective budget authorization is unavailable until Milestone 5"
        )
    # This result is deliberately ephemeral. Only tests may inject an approving
    # callable; no public runtime path accepts or imports one.
    activated = {**grant, "lifecycle": dict(grant["lifecycle"])}
    activated["lifecycle"].update(
        status="active_synthetic_only",
        budget_authorization="approved_synthetic_only",
        provider_authority=False,
        spending_authorized=False,
        dispatch_authorized=False,
    )
    return activated
