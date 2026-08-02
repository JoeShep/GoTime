"""Manifest-bound authorization validation for the isolated v2 follow-up pilot."""

from __future__ import annotations

import hashlib
import json
import os
import tomllib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

CAPABILITY = "suggest_moving_service_questions"
AUTHORIZATION_VERSION = "moving-service-openai-v2-follow-up-authorization-v1"
OPEN_STATUS = "approved_v2_follow_up_pilot"
CLOSED_STATUS = "closed_no_execution_authorized"
RUN_SERIES_ID = "moving-service-stage-b-v2-pilot-20260802"
SEQUENCE = 1
FIXTURE_ID = "storage_unknown"


class V2FollowUpAuthorizationError(ValueError):
    """Repository authorization does not permit the exact v2 pilot slot."""


@dataclass(frozen=True)
class VerifiedV2FollowUpAuthorization:
    path: Path
    digest: str
    artifact: Mapping[str, object]
    approved_at: datetime
    expires_at: datetime


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _resolve(repository_root: Path, value: object) -> Path:
    if not isinstance(value, str) or not value:
        raise V2FollowUpAuthorizationError("Authorization path is invalid.")
    resolved = (repository_root / value).resolve()
    if not resolved.is_relative_to(repository_root.resolve()):
        raise V2FollowUpAuthorizationError("Authorization path escapes repository.")
    return resolved


def _utc(value: object, field: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise V2FollowUpAuthorizationError(f"{field} must be exact UTC.")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as error:
        raise V2FollowUpAuthorizationError(f"{field} is invalid.") from error
    if parsed.microsecond:
        raise V2FollowUpAuthorizationError(f"{field} must use whole seconds.")
    return parsed


def load_verified_v2_package(
    execution_manifest_path: Path,
    *,
    repository_root: Path,
) -> tuple[dict[str, object], dict[str, object]]:
    """Verify the execution manifest, frozen v2 manifest, and every bound byte."""
    try:
        execution = json.loads(execution_manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise V2FollowUpAuthorizationError("Execution manifest is invalid.") from error
    if execution.get("capability") != CAPABILITY:
        raise V2FollowUpAuthorizationError("Execution capability is incompatible.")
    frozen_path = _resolve(repository_root, execution.get("frozen_v2_manifest_path"))
    expected_manifest_digest = execution.get("frozen_v2_manifest_digest")
    if _digest(frozen_path) != expected_manifest_digest:
        raise V2FollowUpAuthorizationError("Frozen v2 manifest digest drifted.")
    try:
        frozen = json.loads(frozen_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise V2FollowUpAuthorizationError("Frozen v2 manifest is invalid.") from error
    if frozen.get("status") != "reviewed_and_frozen":
        raise V2FollowUpAuthorizationError("V2 package is not frozen.")
    digests = frozen.get("artifact_digests")
    if not isinstance(digests, dict):
        raise V2FollowUpAuthorizationError("V2 artifact digests are missing.")
    for filename, expected in digests.items():
        if not isinstance(filename, str) or not isinstance(expected, str):
            raise V2FollowUpAuthorizationError("V2 artifact digest entry is invalid.")
        if _digest(frozen_path.parent / filename) != expected:
            raise V2FollowUpAuthorizationError(f"Frozen v2 artifact drifted: {filename}")
    return execution, frozen


def load_manifest_bound_v2_authorization(
    execution_manifest_path: Path,
    *,
    repository_root: Path,
    now: datetime | None = None,
) -> VerifiedV2FollowUpAuthorization:
    """Fail closed unless one exact, current, single-use v2 slot is authorized."""
    execution, frozen = load_verified_v2_package(
        execution_manifest_path,
        repository_root=repository_root,
    )
    expected_execution_permissions = {
        "follow_up_pilot_authorized": True,
        "credential_access_authorized": True,
        "token_preflight_authorized": True,
        "ai_generation_authorized": True,
        "formal_evaluation_authorized": False,
        "stage_c_authorized": False,
        "production_use_authorized": False,
    }
    if execution.get("status") != "v2_follow_up_pilot_authorized" or any(
        execution.get(field) is not expected
        for field, expected in expected_execution_permissions.items()
    ):
        raise V2FollowUpAuthorizationError("V2 follow-up authorization is closed.")
    authorization_path = _resolve(repository_root, execution.get("authorization_path"))
    digest = _digest(authorization_path)
    if digest != execution.get("authorization_digest"):
        raise V2FollowUpAuthorizationError("Authorization digest is not manifest-bound.")
    try:
        artifact = tomllib.loads(authorization_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise V2FollowUpAuthorizationError("Authorization artifact is invalid.") from error

    metadata = artifact.get("metadata", {})
    bindings = artifact.get("bindings", {})
    permissions = artifact.get("authorization", {})
    scope = artifact.get("scope", {})
    approval = artifact.get("approval", {})
    if metadata.get("authorization_status") == CLOSED_STATUS:
        raise V2FollowUpAuthorizationError("V2 follow-up authorization is closed.")
    expected_bindings = {
        "frozen_v2_manifest_path": execution.get("frozen_v2_manifest_path"),
        "frozen_v2_manifest_digest": execution.get("frozen_v2_manifest_digest"),
        "prompt_version": frozen.get("prompt_version"),
        "schema_version": frozen.get("request_schema_version"),
        "fallback_version": frozen.get("fallback_version"),
        "pilot_configuration_path": frozen.get("follow_up_pilot_path"),
        "pilot_configuration_digest": frozen["artifact_digests"].get(
            "openai-follow-up-pilot.toml"
        ),
    }
    if metadata != {
        "capability": CAPABILITY,
        "authorization_version": AUTHORIZATION_VERSION,
        "authorization_status": OPEN_STATUS,
        "evaluation_only": True,
        "production_use_prohibited": True,
    } or bindings != expected_bindings:
        raise V2FollowUpAuthorizationError("V2 authorization identity drifted.")
    if permissions != {
        "credential_access_authorized": True,
        "token_preflight_authorized": True,
        "ai_generation_authorized": True,
        "formal_evaluation_authorized": False,
        "stage_c_authorized": False,
        "production_use_authorized": False,
    }:
        raise V2FollowUpAuthorizationError("V2 authorization permissions drifted.")
    if scope != {
        "run_series_id": RUN_SERIES_ID,
        "sequence": SEQUENCE,
        "fixture_id": FIXTURE_ID,
        "maximum_credential_reads": 1,
        "maximum_client_constructions": 1,
        "maximum_token_preflight_requests": 1,
        "maximum_ai_generation_requests": 1,
        "automatic_retries": 0,
        "maximum_total_spend_usd": "0.03",
        "single_use": True,
    }:
        raise V2FollowUpAuthorizationError("V2 authorization scope drifted.")
    approved_at = _utc(approval.get("approved_at"), "approved_at")
    expires_at = _utc(approval.get("expires_at"), "expires_at")
    current = now or datetime.now(timezone.utc)
    if approval.get("approver") in {None, "", "none_closed"}:
        raise V2FollowUpAuthorizationError("V2 authorization approver is missing.")
    if (expires_at - approved_at).total_seconds() > 900:
        raise V2FollowUpAuthorizationError("V2 authorization window is too long.")
    if not approved_at <= current < expires_at:
        raise V2FollowUpAuthorizationError("V2 authorization is not currently valid.")
    return VerifiedV2FollowUpAuthorization(
        path=authorization_path,
        digest=digest,
        artifact=artifact,
        approved_at=approved_at,
        expires_at=expires_at,
    )


def close_v2_follow_up_authorization(
    *,
    execution_manifest_path: Path,
    closed_manifest_path: Path,
    repository_root: Path,
    active_authorization_path: Path | None,
    closure_record_path: Path,
    reason: str,
    closed_at: datetime,
) -> None:
    """Restore exact closed bytes and write bounded, idempotent closure evidence."""
    if reason not in {"success", "bounded_failure", "expiration", "cancellation"}:
        raise V2FollowUpAuthorizationError("Closure reason is unsupported.")
    execution, _ = load_verified_v2_package(
        closed_manifest_path,
        repository_root=repository_root,
    )
    closed_fields = (
        "follow_up_pilot_authorized",
        "credential_access_authorized",
        "token_preflight_authorized",
        "ai_generation_authorized",
        "formal_evaluation_authorized",
        "stage_c_authorized",
        "production_use_authorized",
    )
    if execution.get("status") != CLOSED_STATUS or any(
        execution.get(field) is not False for field in closed_fields
    ):
        raise V2FollowUpAuthorizationError("Closed manifest template is not closed.")
    closed_authorization = _resolve(repository_root, execution.get("authorization_path"))
    if _digest(closed_authorization) != execution.get("authorization_digest"):
        raise V2FollowUpAuthorizationError("Permanent closed authorization drifted.")
    temporary = execution_manifest_path.with_suffix(".closing.tmp")
    temporary.write_bytes(closed_manifest_path.read_bytes())
    os.replace(temporary, execution_manifest_path)
    if (
        active_authorization_path is not None
        and active_authorization_path.resolve() != closed_authorization.resolve()
        and active_authorization_path.exists()
    ):
        active_authorization_path.unlink()
    if closure_record_path.exists():
        return
    closure_record_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        closure_record_path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        0o600,
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as output:
        json.dump(
            {
                "run_series_id": RUN_SERIES_ID,
                "sequence": SEQUENCE,
                "reason": reason,
                "closed_at": closed_at.astimezone(timezone.utc)
                .replace(microsecond=0)
                .isoformat()
                .replace("+00:00", "Z"),
                "authorization_closed": True,
                "contains_credential_or_response_content": False,
            },
            output,
            indent=2,
            sort_keys=True,
        )
        output.write("\n")
