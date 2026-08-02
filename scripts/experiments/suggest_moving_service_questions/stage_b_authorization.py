"""Exact, manifest-bound authorization validation for the Stage B pilot."""

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
AUTHORIZATION_VERSION = "moving-service-openai-stage-b-authorization-v1"
AUTHORIZATION_STATUS = "approved_stage_b_generation_pilot"
MANIFEST_STATUS = "openai_stage_b_generation_pilot_authorized"
FINAL_ARTIFACT_PATH = (
    "docs/experiments/suggest-moving-service-questions/v1/"
    "openai-stage-b-execution-authorization.toml"
)
RUN_SERIES_ID = "moving-service-stage-b-pilot-20260801"
FIXTURE_ID = "storage_unknown"
CONSUMED_THROUGH_SEQUENCE = 4
SEQUENCE = CONSUMED_THROUGH_SEQUENCE + 1
APPROVER = "Joe Shepherd"
DURATION_SECONDS = 900
PROMPT_DIGEST = "583a4bdf59c4c4ac67c82928415710c3d5c21ac9912ebd4888a026b8fd4acbf2"
RUN_CONFIGURATION_DIGEST = "e665e04b56d8aeaa01f4c9df2fd2f5f4eed37150802fdba869cba54d1e5bc782"
PROVIDER_SCHEMA_DIGEST = "9e5a3a667a1049d150734fd16669dad98cc982c2dc7a9a18f3e0b8cb3e891afb"
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class StageBAuthorizationError(ValueError):
    """The repository does not authorize the exact Stage B pilot."""


@dataclass(frozen=True)
class VerifiedStageBAuthorization:
    path: Path
    digest: str
    artifact: Mapping[str, object]
    approved_at: datetime
    expires_at: datetime


def _utc(value: object, field: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise StageBAuthorizationError(f"Stage B {field} must be exact UTC.")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as error:
        raise StageBAuthorizationError(f"Stage B {field} is invalid.") from error
    if parsed.microsecond:
        raise StageBAuthorizationError(f"Stage B {field} must use whole seconds.")
    return parsed


def _expected_bindings() -> dict[str, object]:
    return {
        "prompt_artifact_path": "docs/experiments/suggest-moving-service-questions/v1/real-model-prompt.toml",
        "prompt_version": "moving-service-questions-prompt-v1",
        "prompt_digest_algorithm": "sha256",
        "prompt_digest": PROMPT_DIGEST,
        "run_configuration_path": "docs/experiments/suggest-moving-service-questions/v1/openai-run-configuration.toml",
        "run_configuration_digest_algorithm": "sha256",
        "run_configuration_digest": RUN_CONFIGURATION_DIGEST,
        "provider_schema_path": "docs/experiments/suggest-moving-service-questions/v1/openai-response-schema.json",
        "provider_schema_digest_algorithm": "sha256",
        "provider_schema_digest": PROVIDER_SCHEMA_DIGEST,
        "request_schema_version": "moving-service-questions-schema-v1",
        "response_schema_version": "moving-service-questions-schema-v1",
        "knowledge_fixture_version": "moving-service-storage-fixture-v2",
        "provider": "OpenAI",
        "ai_model_identifier": "gpt-4.1-mini-2025-04-14",
        "sdk_pin": "openai==2.45.0",
    }


def load_manifest_bound_stage_b_authorization(
    manifest_path: Path, *, repository_root: Path, now: datetime | None = None
) -> VerifiedStageBAuthorization:
    """Accept only a future exact, short-lived, manifest-bound Stage B artifact."""
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise StageBAuthorizationError("Stage B manifest is unreadable.") from error
    required_manifest = {
        "capability": CAPABILITY,
        "openai_execution_authorization_path": FINAL_ARTIFACT_PATH,
        "openai_execution_authorization_version": AUTHORIZATION_VERSION,
        "openai_execution_authorization_digest_algorithm": "sha256",
        "openai_execution_authorization_status": AUTHORIZATION_STATUS,
        "status": MANIFEST_STATUS,
        "adapter_implementation_authorized": False,
        "real_model_execution_authorized": False,
        "real_model_evaluation_eligible": False,
    }
    if not isinstance(manifest, dict) or any(
        manifest.get(key) != value for key, value in required_manifest.items()
    ):
        raise StageBAuthorizationError("Manifest does not authorize exact Stage B.")
    digest = manifest.get("openai_execution_authorization_digest")
    if not isinstance(digest, str) or not _SHA256.fullmatch(digest):
        raise StageBAuthorizationError("Manifest Stage B digest is invalid.")
    path = (repository_root / FINAL_ARTIFACT_PATH).resolve()
    try:
        path.relative_to(repository_root.resolve())
        data = path.read_bytes()
    except (ValueError, OSError) as error:
        raise StageBAuthorizationError("Stage B artifact is unavailable.") from error
    if hashlib.sha256(data).hexdigest() != digest:
        raise StageBAuthorizationError("Stage B artifact digest does not match.")
    try:
        artifact = tomllib.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        raise StageBAuthorizationError("Stage B artifact is invalid TOML.") from error
    if set(artifact) != {"metadata", "bindings", "authorization", "scope", "approval", "policy", "validation"}:
        raise StageBAuthorizationError("Stage B artifact sections drifted.")
    metadata = artifact["metadata"]
    if metadata != {
        "capability": CAPABILITY,
        "authorization_version": AUTHORIZATION_VERSION,
        "authorization_status": AUTHORIZATION_STATUS,
        "evaluation_only": True,
        "default_deny": True,
        "active_repository_authority": True,
    }:
        raise StageBAuthorizationError("Stage B metadata drifted.")
    if artifact["bindings"] != _expected_bindings():
        raise StageBAuthorizationError("Stage B artifact bindings drifted.")
    for path_field, digest_field in (("prompt_artifact_path", "prompt_digest"), ("run_configuration_path", "run_configuration_digest"), ("provider_schema_path", "provider_schema_digest")):
        bound = (repository_root / str(artifact["bindings"][path_field])).resolve()
        if hashlib.sha256(bound.read_bytes()).hexdigest() != artifact["bindings"][digest_field]:
            raise StageBAuthorizationError(f"Stage B {path_field} digest drifted.")
    if artifact["authorization"] != {
        "credential_access_authorized": True,
        "token_preflight_authorized": True,
        "ai_generation_authorized": True,
        "formal_evaluation_authorized": False,
        "production_use_authorized": False,
    }:
        raise StageBAuthorizationError("Stage B permission pattern drifted.")
    scope = artifact["scope"]
    authorized_sequences = scope.get("authorized_sequence_numbers", [])
    if not isinstance(authorized_sequences, list) or any(
        not isinstance(value, int) or isinstance(value, bool)
        for value in authorized_sequences
    ):
        raise StageBAuthorizationError("Stage B authorized sequence is invalid.")
    if any(value <= CONSUMED_THROUGH_SEQUENCE for value in authorized_sequences):
        raise StageBAuthorizationError("Stage B sequence has already been consumed.")
    if scope != {
        "authorized_run_series_id": RUN_SERIES_ID,
        "authorized_sequence_numbers": [SEQUENCE],
        "authorized_fixture_ids": [FIXTURE_ID],
        "maximum_authorized_spend": "0.03",
        "maximum_credential_reads": 1,
        "maximum_client_constructions": 1,
        "maximum_token_preflight_requests": 1,
        "maximum_ai_generation_requests": 1,
    }:
        raise StageBAuthorizationError("Stage B scope drifted.")
    approval = artifact["approval"]
    if set(approval) != {"approval_status", "approved_at", "expires_at", "approved_by", "maximum_authorization_duration_seconds"} or approval.get("approval_status") != "approved" or approval.get("approved_by") != APPROVER or approval.get("maximum_authorization_duration_seconds") != DURATION_SECONDS:
        raise StageBAuthorizationError("Stage B approval fields drifted.")
    approved_at = _utc(approval.get("approved_at"), "approved_at")
    expires_at = _utc(approval.get("expires_at"), "expires_at")
    current = now or datetime.now(timezone.utc)
    if expires_at <= approved_at or (expires_at - approved_at).total_seconds() > DURATION_SECONDS or not approved_at <= current < expires_at:
        raise StageBAuthorizationError("Stage B authorization is outside its window.")
    if artifact["policy"] != {
        "authorization_is_single_use": True,
        "failure_consumes_sequence": True,
        "preflight_must_be_fresh_and_same_attempt": True,
        "preflight_evidence_must_be_consumed_before_generation": True,
        "environment_values_may_override_authorization": False,
        "operator_intent_is_authority": False,
        "response_reuse_prohibited": True,
    }:
        raise StageBAuthorizationError("Stage B policy drifted.")
    if artifact["validation"] != {
        "token_preflight_timeout_seconds": 5,
        "generation_timeout_seconds": 12,
        "maximum_input_tokens": 3000,
        "maximum_output_tokens": 500,
        "automatic_retries": 0,
        "operator_intent_literal": "AUTHORIZE_ONE_STORAGE_UNKNOWN_STAGE_B_PREFLIGHT_AND_GENERATION",
    }:
        raise StageBAuthorizationError("Stage B validation settings drifted.")
    return VerifiedStageBAuthorization(path, digest, artifact, approved_at, expires_at)
