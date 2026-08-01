"""Exact, manifest-bound Stage A authorization validation.

The current manifest is closed and therefore fails before any future final
artifact is read. Tests may construct a complete future package under a
temporary repository root; no dynamic or caller-selected authority is accepted.
"""

from __future__ import annotations

import hashlib
import json
import re
import tomllib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

CAPABILITY = "suggest_moving_service_questions"
STAGE_A_AUTHORIZATION_VERSION = "moving-service-openai-stage-a-authorization-v1"
STAGE_A_AUTHORIZATION_STATUS = "approved_stage_a_token_preflight"
STAGE_A_MANIFEST_STATUS = "openai_stage_a_token_preflight_authorized"
STAGE_A_FINAL_ARTIFACT_PATH = (
    "docs/experiments/suggest-moving-service-questions/v1/"
    "openai-stage-a-execution-authorization.toml"
)
STAGE_A_CANDIDATE_ARTIFACT_PATH = (
    "docs/experiments/suggest-moving-service-questions/v1/"
    "openai-stage-a-authorization-candidate.toml"
)
STAGE_A_CANDIDATE_DIGEST = (
    "b523426249b9c697f0ad8fa5c7e3cdc0d965db35c5ab5f8f1a7dc66fd4655202"
)
STAGE_A_RUN_SERIES_ID = "moving-service-stage-a-20260731"
STAGE_A_FIXTURE_ID = "storage_unknown"
STAGE_A_CANDIDATE_SEQUENCE = 1
STAGE_A_CONSUMED_THROUGH_SEQUENCE = 1
STAGE_A_NEXT_SEQUENCE = STAGE_A_CONSUMED_THROUGH_SEQUENCE + 1
STAGE_A_APPROVER = "Joe Shepherd"
STAGE_A_DURATION_SECONDS = 900
FROZEN_PROMPT_DIGEST = (
    "583a4bdf59c4c4ac67c82928415710c3d5c21ac9912ebd4888a026b8fd4acbf2"
)
FROZEN_RUN_CONFIGURATION_DIGEST = (
    "e665e04b56d8aeaa01f4c9df2fd2f5f4eed37150802fdba869cba54d1e5bc782"
)
FROZEN_PROVIDER_SCHEMA_DIGEST = (
    "9e5a3a667a1049d150734fd16669dad98cc982c2dc7a9a18f3e0b8cb3e891afb"
)
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class StageAAuthorizationError(ValueError):
    """A future Stage A authorization package failed closed."""


@dataclass(frozen=True)
class VerifiedStageAAuthorization:
    path: Path
    digest: str
    artifact: Mapping[str, object]
    approved_at: datetime
    expires_at: datetime
    authorized_sequence: int


def _parse_exact_utc(value: object, field: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise StageAAuthorizationError(f"Stage A {field} must be exact UTC.")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as error:
        raise StageAAuthorizationError(f"Stage A {field} is invalid.") from error
    if parsed.microsecond != 0:
        raise StageAAuthorizationError(
            f"Stage A {field} must use whole-second precision."
        )
    return parsed


def _expected_bindings() -> dict[str, object]:
    return {
        "prompt_artifact_path": (
            "docs/experiments/suggest-moving-service-questions/v1/"
            "real-model-prompt.toml"
        ),
        "prompt_version": "moving-service-questions-prompt-v1",
        "prompt_digest_algorithm": "sha256",
        "prompt_digest": FROZEN_PROMPT_DIGEST,
        "run_configuration_path": (
            "docs/experiments/suggest-moving-service-questions/v1/"
            "openai-run-configuration.toml"
        ),
        "run_configuration_digest_algorithm": "sha256",
        "run_configuration_digest": FROZEN_RUN_CONFIGURATION_DIGEST,
        "provider_schema_path": (
            "docs/experiments/suggest-moving-service-questions/v1/"
            "openai-response-schema.json"
        ),
        "provider_schema_digest_algorithm": "sha256",
        "provider_schema_digest": FROZEN_PROVIDER_SCHEMA_DIGEST,
        "request_schema_version": "moving-service-questions-schema-v1",
        "response_schema_version": "moving-service-questions-schema-v1",
        "knowledge_fixture_version": "moving-service-storage-fixture-v2",
        "provider": "OpenAI",
        "ai_model_identifier": "gpt-4.1-mini-2025-04-14",
        "sdk_pin": "openai==2.45.0",
    }


def _validate_manifest(manifest: Mapping[str, object]) -> tuple[str, str]:
    expected = {
        "capability": CAPABILITY,
        "artifact_version": "1.7.0",
        "openai_execution_authorization_path": STAGE_A_FINAL_ARTIFACT_PATH,
        "openai_execution_authorization_version": STAGE_A_AUTHORIZATION_VERSION,
        "openai_execution_authorization_digest_algorithm": "sha256",
        "openai_execution_authorization_status": STAGE_A_AUTHORIZATION_STATUS,
        "openai_stage_a_authorization_candidate_path": (
            STAGE_A_CANDIDATE_ARTIFACT_PATH
        ),
        "openai_stage_a_authorization_candidate_version": (
            STAGE_A_AUTHORIZATION_VERSION
        ),
        "openai_stage_a_authorization_candidate_digest_algorithm": "sha256",
        "openai_stage_a_authorization_candidate_digest": STAGE_A_CANDIDATE_DIGEST,
        "openai_stage_a_authorization_candidate_status": (
            "candidate_superseded_by_approved_stage_a"
        ),
        "openai_stage_a_authorization_candidate_activated": True,
        "status": STAGE_A_MANIFEST_STATUS,
        "adapter_implementation_authorized": False,
        "real_model_execution_authorized": False,
        "real_model_evaluation_eligible": False,
    }
    for field, expected_value in expected.items():
        if manifest.get(field) != expected_value:
            raise StageAAuthorizationError(
                f"Manifest field {field} does not authorize exact Stage A."
            )
    digest = manifest.get("openai_execution_authorization_digest")
    if not isinstance(digest, str) or not _SHA256_PATTERN.fullmatch(digest):
        raise StageAAuthorizationError("Manifest Stage A digest is invalid.")
    return STAGE_A_FINAL_ARTIFACT_PATH, digest


def load_manifest_bound_stage_a_authorization(
    manifest_path: Path,
    *,
    repository_root: Path,
    now: datetime | None = None,
) -> VerifiedStageAAuthorization:
    """Load only one exact, active, unexpired manifest-bound Stage A artifact."""
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise StageAAuthorizationError("Stage A manifest is not readable.") from error
    if not isinstance(manifest, dict):
        raise StageAAuthorizationError("Stage A manifest must be an object.")
    relative_path, expected_digest = _validate_manifest(manifest)
    candidate_path = (repository_root / STAGE_A_CANDIDATE_ARTIFACT_PATH).resolve()
    try:
        candidate_path.relative_to(repository_root.resolve())
    except ValueError as error:
        raise StageAAuthorizationError(
            "Stage A candidate path escapes the repository."
        ) from error
    if (
        hashlib.sha256(candidate_path.read_bytes()).hexdigest()
        != STAGE_A_CANDIDATE_DIGEST
    ):
        raise StageAAuthorizationError("Stage A candidate digest drifted.")
    artifact_path = (repository_root / relative_path).resolve()
    try:
        artifact_path.relative_to(repository_root.resolve())
    except ValueError as error:
        raise StageAAuthorizationError(
            "Stage A authorization path escapes the repository."
        ) from error
    artifact_bytes = artifact_path.read_bytes()
    actual_digest = hashlib.sha256(artifact_bytes).hexdigest()
    if actual_digest != expected_digest:
        raise StageAAuthorizationError(
            "Manifest Stage A digest does not match exact artifact bytes."
        )
    try:
        artifact = tomllib.loads(artifact_bytes.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        raise StageAAuthorizationError(
            "Stage A authorization is not valid UTF-8 TOML."
        ) from error
    if set(artifact) != {
        "metadata",
        "bindings",
        "authorization",
        "scope",
        "approval",
        "policy",
        "validation",
    }:
        raise StageAAuthorizationError("Stage A authorization sections drifted.")
    metadata = artifact["metadata"]
    if set(metadata) != {
        "capability",
        "authorization_version",
        "authorization_status",
        "created_at",
        "evaluation_only",
        "default_deny",
        "active_repository_authority",
    }:
        raise StageAAuthorizationError("Stage A metadata fields drifted.")
    if {
        "capability": metadata.get("capability"),
        "authorization_version": metadata.get("authorization_version"),
        "authorization_status": metadata.get("authorization_status"),
        "evaluation_only": metadata.get("evaluation_only"),
        "default_deny": metadata.get("default_deny"),
        "active_repository_authority": metadata.get("active_repository_authority"),
    } != {
        "capability": CAPABILITY,
        "authorization_version": STAGE_A_AUTHORIZATION_VERSION,
        "authorization_status": STAGE_A_AUTHORIZATION_STATUS,
        "evaluation_only": True,
        "default_deny": True,
        "active_repository_authority": True,
    }:
        raise StageAAuthorizationError("Stage A metadata is incompatible.")
    if artifact["bindings"] != _expected_bindings():
        raise StageAAuthorizationError("Stage A frozen bindings drifted.")
    for path_field, digest_field in (
        ("prompt_artifact_path", "prompt_digest"),
        ("run_configuration_path", "run_configuration_digest"),
        ("provider_schema_path", "provider_schema_digest"),
    ):
        bindings = artifact["bindings"]
        bound_path = (repository_root / str(bindings[path_field])).resolve()
        try:
            bound_path.relative_to(repository_root.resolve())
        except ValueError as error:
            raise StageAAuthorizationError(
                "Stage A frozen binding escapes the repository."
            ) from error
        if (
            hashlib.sha256(bound_path.read_bytes()).hexdigest()
            != bindings[digest_field]
        ):
            raise StageAAuthorizationError(
                f"Stage A bound artifact {path_field} digest drifted."
            )
    if artifact["authorization"] != {
        "credential_access_authorized": True,
        "token_preflight_authorized": True,
        "ai_generation_authorized": False,
        "formal_evaluation_authorized": False,
    }:
        raise StageAAuthorizationError("Stage A permissions are incompatible.")
    scope = artifact["scope"]
    if set(scope) != {
        "authorized_run_series_id",
        "authorized_sequence_numbers",
        "authorized_fixture_ids",
        "maximum_authorized_generation_spend",
        "maximum_credential_reads",
        "maximum_client_constructions",
        "maximum_token_preflight_requests",
        "maximum_ai_generation_requests",
    }:
        raise StageAAuthorizationError("Stage A scope is incompatible.")
    authorized_sequences = scope.get("authorized_sequence_numbers")
    if (
        not isinstance(authorized_sequences, list)
        or len(authorized_sequences) != 1
        or type(authorized_sequences[0]) is not int
    ):
        raise StageAAuthorizationError(
            "Stage A must authorize exactly one integer sequence."
        )
    authorized_sequence = authorized_sequences[0]
    if authorized_sequence <= STAGE_A_CONSUMED_THROUGH_SEQUENCE:
        raise StageAAuthorizationError("Stage A sequence has already been consumed.")
    if authorized_sequence != STAGE_A_NEXT_SEQUENCE:
        raise StageAAuthorizationError("Stage A sequence is not the exact next slot.")
    if {
        "authorized_run_series_id": scope.get("authorized_run_series_id"),
        "authorized_fixture_ids": scope.get("authorized_fixture_ids"),
        "maximum_authorized_generation_spend": scope.get(
            "maximum_authorized_generation_spend"
        ),
        "maximum_credential_reads": scope.get("maximum_credential_reads"),
        "maximum_client_constructions": scope.get("maximum_client_constructions"),
        "maximum_token_preflight_requests": scope.get(
            "maximum_token_preflight_requests"
        ),
        "maximum_ai_generation_requests": scope.get(
            "maximum_ai_generation_requests"
        ),
    } != {
        "authorized_run_series_id": STAGE_A_RUN_SERIES_ID,
        "authorized_fixture_ids": [STAGE_A_FIXTURE_ID],
        "maximum_authorized_generation_spend": "0.00",
        "maximum_credential_reads": 1,
        "maximum_client_constructions": 1,
        "maximum_token_preflight_requests": 1,
        "maximum_ai_generation_requests": 0,
    }:
        raise StageAAuthorizationError("Stage A scope is incompatible.")
    approval = artifact["approval"]
    if set(approval) != {
        "approval_status",
        "approved_at",
        "expires_at",
        "approved_by",
        "maximum_authorization_duration_seconds",
    }:
        raise StageAAuthorizationError("Stage A approval fields drifted.")
    if (
        approval.get("approval_status") != "approved"
        or approval.get("approved_by") != STAGE_A_APPROVER
        or approval.get("maximum_authorization_duration_seconds")
        != STAGE_A_DURATION_SECONDS
    ):
        raise StageAAuthorizationError("Stage A approval is incompatible.")
    approved_at = _parse_exact_utc(approval.get("approved_at"), "approved_at")
    expires_at = _parse_exact_utc(approval.get("expires_at"), "expires_at")
    created_at = _parse_exact_utc(metadata.get("created_at"), "created_at")
    if created_at != approved_at:
        raise StageAAuthorizationError(
            "Stage A creation time must equal its approval time."
        )
    if (expires_at - approved_at).total_seconds() != STAGE_A_DURATION_SECONDS:
        raise StageAAuthorizationError(
            "Stage A expiration must be exactly 900 seconds after approval."
        )
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None or not approved_at <= current < expires_at:
        raise StageAAuthorizationError("Stage A authorization is not currently active.")
    if artifact["policy"] != {
        "operator_intent_is_authority": False,
        "environment_values_may_override_authorization": False,
        "command_line_flags_may_override_authorization": False,
        "missing_or_unknown_fields_fail_closed": True,
        "credential_access_requires_all_non_secret_gates": True,
        "token_preflight_requires_credential_access_authorization": True,
        "ai_generation_requires_successful_token_preflight": True,
        "formal_evaluation_requires_ai_generation_authorization": True,
        "authorization_is_single_use": True,
        "failure_consumes_sequence": True,
        "generation_method_must_be_unreachable": True,
    }:
        raise StageAAuthorizationError("Stage A policy is incompatible.")
    if artifact["validation"] != {
        "non_secret_gate_order": [
            "artifact_integrity",
            "repository_authorization",
            "fixture_and_sequence_validation",
            "output_path_checks",
            "budget_checks",
            "operator_intent_check",
        ],
        "first_secret_stage": "credential_access",
        "first_network_stage": "token_preflight",
        "generation_stage": "prohibited",
    }:
        raise StageAAuthorizationError("Stage A validation policy drifted.")
    return VerifiedStageAAuthorization(
        path=artifact_path,
        digest=actual_digest,
        artifact=artifact,
        approved_at=approved_at,
        expires_at=expires_at,
        authorized_sequence=authorized_sequence,
    )
