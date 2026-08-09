"""Inactive frozen-v4 sequence-4 generation gate bound to reviewed preflight."""

from __future__ import annotations

import hashlib
import json
import os
import tomllib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Mapping

from app.moving_service_questions import ResponseValidationError
from moving_service_questions_v2 import (
    FALLBACK_VERSION_V2,
    MovingServiceQuestionResponseV2,
    ProseValidationError,
    select_fallback_v2,
    validate_response_v2,
)
from rejected_prose_diagnostics import collect_prose_violation_diagnostics
from moving_service_questions_v4 import MovingServiceQuestionResponseV4
from run_openai_stage_b_v2_pilot import PreparedV2Pilot, prepare_frozen_v2_pilot
from run_openai_stage_b_v4_pilot import (
    FROZEN_V4_MANIFEST_DIGEST,
    canonical_attempt_digest,
    deterministic_request_digest,
    prepare_frozen_v4_pilot,
)
from openai_transport import OpenAIPreflightResult
from openai_transport_v4 import make_v4_openai_transport
from v4_sequence_1_preflight import (
    generation_binding_dry_run as preview_v4_preflight_binding,
    verify_completed_lifecycle_history as verify_completed_v4_preflight_history,
    verify_lifecycle_history as verify_v4_preflight_history,
)

RUN_SERIES_ID = "moving-service-stage-b-v4-pilot-20260808"
SEQUENCE = 4
FIXTURE_ID = "storage_unknown"
PREFIX = "004-storage_unknown-generation-v4"
OPERATOR_INTENT = "AUTHORIZE_ONE_STORAGE_UNKNOWN_V4_GENERATION_ONLY"
CANDIDATE_DIGEST = "b9518a4770a7cd225d57fb3cd2564764a9ef840446ac2dd705cd5aee7b37e8df"
MANIFEST_DIGEST = "3cce967e358355b20f143fcc4b9c45284fa1275303548842545a9072f06b8676"
UNRESOLVED_CANDIDATE_DIGEST = "b4cf11ee55e8110a6805bfa30408298b84c3d96e4e56f5f2ed4de426763941a4"
UNRESOLVED_MANIFEST_DIGEST = "f18e2a03e6ef1627c930e07c8392f1aa2ccfb7849b0cad40d80499ddeb48b1e4"
PREFLIGHT_EVIDENCE_DIGEST = "f1f995231fc4986c25625f673bc878a82564adb9d6992ad9e62b1fdbccafe62c"
PREFLIGHT_REVIEW_DIGEST = "12b71c109aadf82a8d4e471f165bc3b7d450a84cc229ad6eb696e0f17e9d6bd2"
PREFLIGHT_BINDING_PREVIEW_DIGEST = "c4fd31f42019a5b8f461d57411e4696a3ccaea98f2abd4ecb67827f6002a0c94"
REQUEST_DIGEST = "f5a8c7e06d2ad9e133a5b0b92c322f09ed67205feb25314c5114fa1849fcdd0a"
CANONICAL_ATTEMPT_DIGEST = "7a3c0f7ace4ee4289f4149224fc001b215e71d4cc168edea604516fd133f450d"
PROVIDER_FINGERPRINT = "15caaaaa6a3b43860c426c7555be7f4c7a6bf50d658c92c3c8564c1d43cb5656"
INPUT_TOKENS = 2852
CONSERVATIVE_COST = "0.0019408"
PREFLIGHT_RUN_SERIES_ID = "moving-service-stage-b-v4-pilot-20260808"
PREFLIGHT_PREFIX = "001-storage_unknown-preflight"

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = REPOSITORY_ROOT / "docs/experiments/suggest-moving-service-questions/v4-pilot/authorization-review/phase-candidates/sequence-4-generation"
UNRESOLVED_CANDIDATE_PATH = PACKAGE_ROOT / "inactive-sequence-4-v4-generation-authorization-candidate.toml"
UNRESOLVED_MANIFEST_PATH = PACKAGE_ROOT / "sequence-4-v4-generation-candidate-manifest.json"
RESOLVED_PACKAGE_ROOT = PACKAGE_ROOT / "resolved-live-preflight"
CANDIDATE_PATH = RESOLVED_PACKAGE_ROOT / "inactive-sequence-4-v4-generation-authorization-candidate.toml"
MANIFEST_PATH = RESOLVED_PACKAGE_ROOT / "sequence-4-v4-generation-candidate-manifest.json"


def _verify_v4_candidate_bindings(candidate: Mapping[str, object], repository_root: Path) -> None:
    bindings = candidate.get("bindings")
    if not isinstance(bindings, Mapping):
        raise Sequence4GenerationGateError("generation candidate bindings are absent")
    expected = {
        "frozen_v4_manifest_digest": FROZEN_V4_MANIFEST_DIGEST,
        "prompt_version": "moving-service-questions-prompt-v4",
        "prompt_digest": "78b77f31e8cdc68528c08c106fec947123838813d9bdd82978c32a3b011ffb26",
        "schema_version": "moving-service-questions-schema-v4",
        "request_identity_digest": "b5125e2075779306f0a4374676d442fa3016702bdb5143bc8e3a6b7173d9dd35",
        "provider_schema_digest": "4119a12b673b693c958aa623ff8d9377e3d27f5fd1ca6655671c65716363269d",
        "pilot_configuration_digest": "9459094de6b42de7827179fae1f4523712cad1432c4bbc6a3f2a679a6703d82a",
        "deterministic_request_digest": REQUEST_DIGEST,
        "canonical_attempt_digest": CANONICAL_ATTEMPT_DIGEST,
        "provider_fingerprint": PROVIDER_FINGERPRINT,
        "provider": "OpenAI",
        "ai_model_identifier": "gpt-4.1-mini-2025-04-14",
        "sdk_pin": "openai==2.45.0",
        "fallback_version": "moving-service-fallback-v2",
        "closed_execution_manifest_digest": "18a22d62a3e368f5a021649be56a211af959fed7b0305eab61d063022b1387fa",
    }
    if any(bindings.get(key) != value for key, value in expected.items()):
        raise Sequence4GenerationGateError("generation candidate frozen-v4 binding drifted")
    paths = {
        "frozen_v4_manifest_path": "frozen_v4_manifest_digest",
        "prompt_path": "prompt_digest",
        "request_identity_path": "request_identity_digest",
        "provider_schema_path": "provider_schema_digest",
    }
    for path_key, digest_key in paths.items():
        path = repository_root / str(bindings.get(path_key, ""))
        if not path.is_file() or _digest(path) != bindings[digest_key]:
            raise Sequence4GenerationGateError("generation candidate artifact binding drifted")
    pilot_path = repository_root / "docs/experiments/suggest-moving-service-questions/v4/offline-pilot-request-config.json"
    if _digest(pilot_path) != bindings["pilot_configuration_digest"]:
        raise Sequence4GenerationGateError("generation candidate pilot configuration drifted")


class Sequence4GenerationGateError(ValueError):
    pass


def active_generation_manifest(authorization_digest: str) -> dict[str, object]:
    """Derive the only execution manifest allowed for active v4 generation."""
    return {
        "status": "active_v4_generation_only",
        "capability": "suggest_moving_service_questions",
        "run_series_id": RUN_SERIES_ID,
        "sequence": SEQUENCE,
        "fixture_id": FIXTURE_ID,
        "authorization_digest": authorization_digest,
        "credential_access_authorized": True,
        "token_preflight_authorized": False,
        "ai_generation_authorized": True,
        "formal_evaluation_authorized": False,
        "stage_c_authorized": False,
        "production_use_authorized": False,
        "fastapi_exposure_authorized": False,
        "frontend_exposure_authorized": False,
        "recurring_execution_authorized": False,
        "background_execution_authorized": False,
        "maximum_credential_reads": 1,
        "maximum_client_constructions": 1,
        "maximum_token_preflight_requests": 0,
        "maximum_ai_generation_requests": 1,
        "automatic_retries": 0,
        "ai_generation_timeout_seconds": 12,
        "maximum_output_tokens": 500,
        "maximum_total_spend_usd": "0.03",
        "human_grounding_review_required": True,
    }


def active_generation_manifest_bytes(authorization_digest: str) -> bytes:
    return (json.dumps(
        active_generation_manifest(authorization_digest), indent=2, sort_keys=True
    ) + "\n").encode()


@dataclass(frozen=True)
class VerifiedGenerationAttempt:
    """Credential-free, immutable exact request and reviewed preflight binding."""

    prepared: PreparedV2Pilot
    preflight: OpenAIPreflightResult
    deterministic_request_digest: str
    canonical_attempt_digest: str
    provider_fingerprint: str
    authorization_digest: str | None = None


def verify_exact_generation_attempt(
    *,
    output_root: Path,
    repository_root: Path = REPOSITORY_ROOT,
    prepared_builder=prepare_frozen_v4_pilot,
    provider_fingerprint_builder=None,
    history_verifier=None,
) -> VerifiedGenerationAttempt:
    """Verify the exact generation attempt before any credential boundary."""
    if history_verifier is None:
        history_verifier = verify_candidate_and_preflight_for_active_generation
    verified_history = history_verifier(
        repository_root=repository_root, output_root=output_root)
    prepared = prepared_builder()
    digests = prepared.frozen_manifest["artifact_digests"]
    frozen = {
        "frozen_v4_manifest_digest": FROZEN_V4_MANIFEST_DIGEST,
        "prompt_version": prepared.request.prompt_version,
        "prompt_digest": digests["real-model-prompt.toml"],
        "schema_version": prepared.request.schema_version,
        "provider_schema_digest": digests["openai-response-schema.json"],
        "pilot_configuration_digest": "9459094de6b42de7827179fae1f4523712cad1432c4bbc6a3f2a679a6703d82a",
        "provider": prepared.pilot_configuration["identity"]["provider"],
        "ai_model_identifier": prepared.provider_request.model_identifier,
        "sdk_pin": prepared.pilot_configuration["identity"]["sdk_pin"],
    }
    request_digest = deterministic_request_digest(prepared)
    canonical_digest = canonical_attempt_digest(prepared)
    if provider_fingerprint_builder is None:
        provider_fingerprint_builder = lambda value: make_v4_openai_transport(
            SimpleNamespace(max_retries=0), value
        ).request_fingerprint(value.provider_request)
    provider_fingerprint = provider_fingerprint_builder(prepared)
    expected_frozen = {
        "frozen_v4_manifest_digest": FROZEN_V4_MANIFEST_DIGEST,
        "prompt_version": "moving-service-questions-prompt-v4",
        "prompt_digest": "78b77f31e8cdc68528c08c106fec947123838813d9bdd82978c32a3b011ffb26",
        "schema_version": "moving-service-questions-schema-v4",
        "provider_schema_digest": "4119a12b673b693c958aa623ff8d9377e3d27f5fd1ca6655671c65716363269d",
        "pilot_configuration_digest": "9459094de6b42de7827179fae1f4523712cad1432c4bbc6a3f2a679a6703d82a",
        "provider": "OpenAI",
        "ai_model_identifier": "gpt-4.1-mini-2025-04-14",
        "sdk_pin": "openai==2.45.0",
    }
    if any(frozen.get(key) != value for key, value in expected_frozen.items()):
        raise Sequence4GenerationGateError("frozen generation request binding drifted")
    actual_parameters = {
        "temperature": prepared.provider_request.model_parameters.get("temperature"),
        "maximum_output_tokens": prepared.provider_request.maximum_output_tokens,
        "store": False,
        "stream": False,
        "background": False,
        "truncation": "disabled",
        "tools": [],
        "automatic_retries": prepared.provider_request.retry_count,
        "ai_generation_timeout_seconds": int(prepared.provider_request.timeout_seconds),
    }
    expected_parameters = {
        "temperature": 0,
        "maximum_output_tokens": 500,
        "store": False,
        "stream": False,
        "background": False,
        "truncation": "disabled",
        "tools": [],
        "automatic_retries": 0,
        "ai_generation_timeout_seconds": 12,
    }
    if actual_parameters != expected_parameters:
        raise Sequence4GenerationGateError("generation request parameters drifted")
    if (
        request_digest != REQUEST_DIGEST
        or canonical_digest != CANONICAL_ATTEMPT_DIGEST
        or provider_fingerprint != PROVIDER_FINGERPRINT
        or verified_history["input_tokens"] is None
        or verified_history["conservative_maximum_generation_cost"] is None
    ):
        raise Sequence4GenerationGateError("exact generation attempt drifted")
    return VerifiedGenerationAttempt(
        prepared=prepared,
        preflight=OpenAIPreflightResult(
            PROVIDER_FINGERPRINT,
            int(verified_history["input_tokens"]),
            0.0,
            Decimal(str(verified_history["conservative_maximum_generation_cost"])),
        ),
        deterministic_request_digest=request_digest,
        canonical_attempt_digest=canonical_digest,
        provider_fingerprint=provider_fingerprint,
    )


def verify_live_generation_precredential(
    *, output_root: Path, repository_root: Path = REPOSITORY_ROOT,
    now: datetime, prepared_builder=prepare_frozen_v4_pilot,
    provider_fingerprint_builder=None, history_verifier=None,
) -> VerifiedGenerationAttempt:
    """Verify active state, completed history, and exact request in live order."""
    active = verify_active_generation_state(
        repository_root=repository_root, output_root=output_root, now=now)
    verified = verify_exact_generation_attempt(
        output_root=output_root, repository_root=repository_root,
        prepared_builder=prepared_builder,
        provider_fingerprint_builder=provider_fingerprint_builder,
        history_verifier=history_verifier)
    return VerifiedGenerationAttempt(
        prepared=verified.prepared, preflight=verified.preflight,
        deterministic_request_digest=verified.deterministic_request_digest,
        canonical_attempt_digest=verified.canonical_attempt_digest,
        provider_fingerprint=verified.provider_fingerprint,
        authorization_digest=str(active["authorization_digest"]),
    )


@dataclass(frozen=True)
class GenerationPaths:
    review_rendered: Path
    installation: Path
    activation_review: Path
    active: Path
    activation: Path
    transaction: Path
    audit: Path
    preflight_consumption: Path
    response_evidence: Path
    grounding_review: Path
    deletion: Path
    closure: Path
    cleanup: Path


def activate_generation_authority(*, repository_root: Path, output_root: Path,
                                  artifact_sha256: str, installation_sha256: str,
                                  review_sha256: str, operator: str,
                                  operator_intent: str, now: datetime,
                                  failpoint: str | None = None) -> Mapping[str, object]:
    """Atomically install one reviewed generation-only authority."""
    if operator_intent != OPERATOR_INTENT or not operator.strip():
        raise Sequence4GenerationGateError("generation operator intent is invalid")
    paths = generation_paths(output_root)
    docs = repository_root / "docs/experiments/suggest-moving-service-questions/v2-pilot"
    execution = docs / "execution-manifest.json"
    closed = docs / "closed-execution-manifest.json"
    if execution.read_bytes() != closed.read_bytes():
        raise Sequence4GenerationGateError("execution manifest is not closed")
    if any(path.exists() for path in (paths.active, paths.activation, paths.transaction, paths.audit, paths.closure)):
        raise Sequence4GenerationGateError("generation state already exists")
    if (_digest(paths.review_rendered) != artifact_sha256 or _digest(paths.installation) != installation_sha256
            or _digest(paths.activation_review) != review_sha256):
        raise Sequence4GenerationGateError("reviewed generation package digest mismatch")
    review = json.loads(paths.activation_review.read_text())
    if review.get("decision") != "approve" or review.get("activation_eligible") is not True:
        raise Sequence4GenerationGateError("generation activation review is not approved")
    artifact = tomllib.loads(paths.review_rendered.read_text())
    validate_rendered_generation_artifact(artifact, now=now)
    if (artifact.get("metadata", {}).get("phase") != "generation"
            or artifact.get("scope", {}).get("sequence") != 4
            or artifact.get("scope", {}).get("maximum_token_preflight_requests") != 0
            or artifact.get("scope", {}).get("maximum_ai_generation_requests") != 1
            or artifact.get("authorization", {}).get("ai_generation_authorized") is not True):
        raise Sequence4GenerationGateError("generation-only artifact scope drifted")
    expires = datetime.fromisoformat(str(artifact["approval"]["expires_at"]).replace("Z", "+00:00"))
    if not now < expires:
        raise Sequence4GenerationGateError("generation authorization is expired")
    transaction_id = hashlib.sha256(f"{artifact_sha256}:{_stamp(now)}".encode()).hexdigest()[:32]
    journal = {"transaction_id": transaction_id, "state": "prepared", "phase": "generation", "sequence": 4,
               "run_series_id": RUN_SERIES_ID, "fixture_id": FIXTURE_ID,
               "artifact_digest": artifact_sha256, "closed_manifest_digest": _digest(closed),
               "prepared_at": _stamp(now)}
    _exclusive(paths.transaction, journal)
    try:
        if failpoint == "after_prepared":
            raise OSError("synthetic interruption")
        _exclusive_bytes(paths.active, paths.review_rendered.read_bytes())
        if failpoint == "after_authorization_installed":
            raise OSError("synthetic interruption")
        _atomic_replace(execution, active_generation_manifest_bytes(artifact_sha256))
        if failpoint == "after_manifest_transition":
            raise OSError("synthetic interruption")
        activation = {"transaction_id": transaction_id, "run_series_id": RUN_SERIES_ID,
                      "fixture_id": FIXTURE_ID, "phase": "generation", "sequence": 4,
                      "authorization_digest": artifact_sha256, "active_manifest_digest": _digest(execution),
                      "installation_record_digest": installation_sha256,
                      "activation_review_digest": review_sha256,
                      "candidate_digest": CANDIDATE_DIGEST, "candidate_manifest_digest": MANIFEST_DIGEST,
                      "operator": operator, "operator_intent": operator_intent, "activated_at": _stamp(now),
                      "generation_only": True, "token_preflight_authorized": False}
        activation_digest = _exclusive(paths.activation, activation)
        if failpoint == "after_activation_record":
            raise OSError("synthetic interruption")
        journal["state"] = "committed"
        journal["activation_record_digest"] = activation_digest
        journal["committed_at"] = _stamp(now)
        _atomic_replace(paths.transaction, (json.dumps(journal, indent=2, sort_keys=True) + "\n").encode())
    except BaseException:
        close_generation_authority(repository_root=repository_root, output_root=output_root,
                                   reason="activation_recovery", now=now)
        raise
    return {"active_authorization": paths.active, "active_manifest_digest": _digest(execution),
            "activation_record_digest": activation_digest, "transaction_id": transaction_id,
            "transaction_state": "committed"}


def close_generation_authority(*, repository_root: Path, output_root: Path,
                               reason: str, now: datetime) -> Mapping[str, object]:
    paths = generation_paths(output_root)
    docs = repository_root / "docs/experiments/suggest-moving-service-questions/v2-pilot"
    execution = docs / "execution-manifest.json"
    closed = docs / "closed-execution-manifest.json"
    _atomic_replace(execution, closed.read_bytes())
    paths.active.unlink(missing_ok=True)
    transaction_id = None
    if paths.transaction.exists():
        journal = json.loads(paths.transaction.read_text())
        transaction_id = journal.get("transaction_id")
        journal["state"] = "rolled_back"
        _atomic_replace(paths.transaction, (json.dumps(journal, indent=2, sort_keys=True) + "\n").encode())
    if not paths.closure.exists():
        _exclusive(paths.closure, {"transaction_id": transaction_id, "phase": "generation", "sequence": 4,
                                  "reason": reason, "closed_at": _stamp(now), "authorization_closed": True,
                                  "ai_generation_authorized": False, "token_preflight_authorized": False})
    return {"transaction_id": transaction_id, "transaction_state": "rolled_back",
            "authorization_closed": execution.read_bytes() == closed.read_bytes(),
            "active_authorization_absent": not paths.active.exists()}


def generation_paths(output_root: Path) -> GenerationPaths:
    base = output_root / RUN_SERIES_ID
    review = base / "authorization-review"
    return GenerationPaths(
        review / f"{PREFIX}-rendered.toml",
        review / f"{PREFIX}-installation.json",
        review / f"{PREFIX}-activation-review.json",
        base / f"{PREFIX}-authorization.toml",
        base / f"{PREFIX}-activation.json",
        base / f"{PREFIX}-activation-transaction.json",
        base / f"{PREFIX}-audit.json",
        base / f"{PREFIX}-preflight-evidence-consumption.json",
        base / f"{PREFIX}-validated-response.json",
        base / f"{PREFIX}-grounding-review.json",
        base / f"{PREFIX}-evidence-deletion.json",
        base / f"{PREFIX}-closure.json",
        base / f"{PREFIX}-expired-review-package-cleanup.json",
    )


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _exclusive(path: Path, value: Mapping[str, object]) -> str:
    path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    path.parent.chmod(0o700)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")
    return _digest(path)


def _exclusive_bytes(path: Path, value: bytes) -> str:
    path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(value)
    return _digest(path)


def _atomic_replace(path: Path, value: bytes) -> None:
    temporary = path.with_name(f".{path.name}.sequence4-v4-generation.tmp")
    descriptor = os.open(
        temporary,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
        0o600,
    )
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(value)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    directory = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def _stamp(now: datetime) -> str:
    if now.tzinfo is None:
        raise Sequence4GenerationGateError("time must be timezone aware")
    return now.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def validate_rendered_generation_artifact(artifact: Mapping[str, object], *, now: datetime) -> None:
    candidate = tomllib.loads(CANDIDATE_PATH.read_text(encoding="utf-8"))
    if artifact.get("metadata") != {
        "capability": "suggest_moving_service_questions",
        "authorization_version": "moving-service-openai-v4-generation-sequence-4-v1",
        "authorization_status": "approved_v4_generation", "phase": "generation",
        "active_repository_authority": True,
    }:
        raise Sequence4GenerationGateError("rendered generation metadata drifted")
    if (artifact.get("bindings") != candidate["bindings"]
            or artifact.get("required_v4_preflight") != candidate["required_v4_preflight"]):
        raise Sequence4GenerationGateError("rendered generation bindings drifted")
    if artifact.get("authorization") != candidate["proposed_authorization"] or artifact.get("scope") != candidate["scope"]:
        raise Sequence4GenerationGateError("rendered generation scope drifted")
    approval = artifact.get("approval")
    if not isinstance(approval, Mapping) or set(approval) != {
        "approver", "approved_at", "activated_at", "expires_at",
        "maximum_duration_seconds", "authorization_reason",
    }:
        raise Sequence4GenerationGateError("rendered generation approval drifted")
    try:
        approved = datetime.fromisoformat(str(approval["approved_at"]).replace("Z", "+00:00"))
        activated = datetime.fromisoformat(str(approval["activated_at"]).replace("Z", "+00:00"))
        expires = datetime.fromisoformat(str(approval["expires_at"]).replace("Z", "+00:00"))
    except ValueError as error:
        raise Sequence4GenerationGateError("rendered generation time is invalid") from error
    if (approval["maximum_duration_seconds"] != 900 or not approved <= activated < expires
            or (expires - activated).total_seconds() > 900 or not activated <= now < expires
            or not str(approval["approver"]).strip() or not str(approval["authorization_reason"]).strip()):
        raise Sequence4GenerationGateError("rendered generation authorization is not currently valid")


def _strict_utc_second(value: object) -> datetime:
    try:
        parsed = datetime.strptime(str(value), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as error:
        raise Sequence4GenerationGateError("generation lifecycle timestamp is invalid") from error
    return parsed


def verify_active_generation_state(
    *, repository_root: Path = REPOSITORY_ROOT, output_root: Path, now: datetime,
) -> Mapping[str, object]:
    """Validate the exact active authorization, records, and derived manifest."""
    verify_resolved_generation_candidate(
        repository_root=repository_root, require_closed_repository=False)
    paths = generation_paths(output_root)
    required_paths = (
        paths.review_rendered, paths.installation, paths.activation_review,
        paths.active, paths.activation, paths.transaction,
    )
    if (not all(path.is_file() and not path.is_symlink() for path in required_paths)
            or any(path.exists() for path in (
                paths.audit, paths.preflight_consumption, paths.response_evidence,
                paths.grounding_review, paths.deletion, paths.closure,
            ))):
        raise Sequence4GenerationGateError("active generation lifecycle is incomplete or consumed")
    try:
        artifact = tomllib.loads(paths.active.read_text(encoding="utf-8"))
        installed = tomllib.loads(paths.review_rendered.read_text(encoding="utf-8"))
        installation = json.loads(paths.installation.read_text(encoding="utf-8"))
        review = json.loads(paths.activation_review.read_text(encoding="utf-8"))
        activation = json.loads(paths.activation.read_text(encoding="utf-8"))
        transaction = json.loads(paths.transaction.read_text(encoding="utf-8"))
    except (ValueError, TypeError, tomllib.TOMLDecodeError) as error:
        raise Sequence4GenerationGateError("active generation lifecycle is malformed") from error
    validate_rendered_generation_artifact(artifact, now=now)
    if artifact != installed:
        raise Sequence4GenerationGateError("active authorization differs from reviewed bytes")
    authorization_digest = _digest(paths.active)
    installation_digest = _digest(paths.installation)
    review_digest = _digest(paths.activation_review)
    activation_digest = _digest(paths.activation)
    closed_path = repository_root / "docs/experiments/suggest-moving-service-questions/v2-pilot/closed-execution-manifest.json"
    execution_path = closed_path.with_name("execution-manifest.json")
    expected_installation = {
        "phase": "generation", "sequence": SEQUENCE, "fixture_id": FIXTURE_ID,
        "installed_digest": authorization_digest, "candidate_digest": CANDIDATE_DIGEST,
        "candidate_manifest_digest": MANIFEST_DIGEST, "authoritative": False,
        "activation_status": "not_activated", "activation_review_status": "pending",
    }
    if installation != expected_installation:
        raise Sequence4GenerationGateError("generation installation record drifted")
    expected_review_fields = {
        "phase", "sequence", "fixture_id", "installed_artifact_digest",
        "installation_record_digest", "reviewer", "decision", "reviewed_at",
        "bounded_notes", "activation_eligible", "authoritative", "activated",
    }
    if (set(review) != expected_review_fields
            or review.get("phase") != "generation_activation_review"
            or review.get("sequence") != SEQUENCE or review.get("fixture_id") != FIXTURE_ID
            or review.get("installed_artifact_digest") != authorization_digest
            or review.get("installation_record_digest") != installation_digest
            or review.get("decision") != "approve" or review.get("activation_eligible") is not True
            or review.get("authoritative") is not False or review.get("activated") is not False
            or not str(review.get("reviewer", "")).strip()
            or not str(review.get("bounded_notes", "")).strip()):
        raise Sequence4GenerationGateError("generation activation review drifted")
    transaction_id = transaction.get("transaction_id")
    expected_manifest_bytes = active_generation_manifest_bytes(authorization_digest)
    if execution_path.read_bytes() != expected_manifest_bytes:
        raise Sequence4GenerationGateError("active generation execution manifest drifted")
    active_manifest_digest = hashlib.sha256(expected_manifest_bytes).hexdigest()
    expected_activation = {
        "transaction_id": transaction_id, "run_series_id": RUN_SERIES_ID,
        "sequence": SEQUENCE, "fixture_id": FIXTURE_ID, "phase": "generation",
        "authorization_digest": authorization_digest,
        "active_manifest_digest": active_manifest_digest,
        "installation_record_digest": installation_digest,
        "activation_review_digest": review_digest,
        "candidate_digest": CANDIDATE_DIGEST, "candidate_manifest_digest": MANIFEST_DIGEST,
        "operator": activation.get("operator"), "operator_intent": OPERATOR_INTENT,
        "activated_at": activation.get("activated_at"), "generation_only": True,
        "token_preflight_authorized": False,
    }
    if (activation != expected_activation
            or not str(activation.get("operator", "")).strip()
            or transaction_id != hashlib.sha256(
                f"{authorization_digest}:{activation.get('activated_at')}".encode()
            ).hexdigest()[:32]):
        raise Sequence4GenerationGateError("generation activation record drifted")
    expected_transaction = {
        "transaction_id": transaction_id, "state": "committed", "phase": "generation",
        "sequence": SEQUENCE, "run_series_id": RUN_SERIES_ID, "fixture_id": FIXTURE_ID,
        "artifact_digest": authorization_digest,
        "closed_manifest_digest": "18a22d62a3e368f5a021649be56a211af959fed7b0305eab61d063022b1387fa",
        "prepared_at": transaction.get("prepared_at"),
        "activation_record_digest": activation_digest,
        "committed_at": transaction.get("committed_at"),
    }
    if transaction != expected_transaction or _digest(closed_path) != expected_transaction["closed_manifest_digest"]:
        raise Sequence4GenerationGateError("generation transaction journal drifted")
    approval = artifact["approval"]
    approved_at = _strict_utc_second(approval["approved_at"])
    eligible_at = _strict_utc_second(approval["activated_at"])
    reviewed_at = _strict_utc_second(review["reviewed_at"])
    activated_at = _strict_utc_second(activation["activated_at"])
    prepared_at = _strict_utc_second(transaction["prepared_at"])
    committed_at = _strict_utc_second(transaction["committed_at"])
    expires_at = _strict_utc_second(approval["expires_at"])
    if not (approved_at <= eligible_at <= reviewed_at <= activated_at
            and activated_at == prepared_at == committed_at < expires_at
            and activated_at <= now and now + timedelta(seconds=180) <= expires_at):
        raise Sequence4GenerationGateError("generation lifecycle timestamp order drifted")
    return {
        "authorization_digest": authorization_digest,
        "installation_record_digest": installation_digest,
        "activation_review_digest": review_digest,
        "activation_record_digest": activation_digest,
        "transaction_id": transaction_id,
        "active_manifest_digest": active_manifest_digest,
        "artifact": artifact,
    }


def _verify_candidate_and_preflight(*, repository_root: Path,
                                    output_root: Path,
                                    current_state: str) -> Mapping[str, object]:
    if current_state not in {"permanent_closed", "active_generation"}:
        raise Sequence4GenerationGateError("unknown generation verification state")
    candidate_status = verify_resolved_generation_candidate(
        repository_root=repository_root,
        require_closed_repository=current_state == "permanent_closed",
    )
    synthetic = os.environ.get("GOTIME_V4_SEQUENCE_4_GENERATION_OFFLINE_TEST") == "1"
    if synthetic:
        evidence_path = output_root / PREFLIGHT_RUN_SERIES_ID / f"{PREFLIGHT_PREFIX}-evidence.json"
        review_path = output_root / PREFLIGHT_RUN_SERIES_ID / f"{PREFLIGHT_PREFIX}-review.json"
    else:
        evidence_path = output_root / PREFLIGHT_RUN_SERIES_ID / f"{PREFLIGHT_PREFIX}-evidence.json"
        review_path = output_root / PREFLIGHT_RUN_SERIES_ID / f"{PREFLIGHT_PREFIX}-review.json"
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    review = json.loads(review_path.read_text(encoding="utf-8"))
    expected = {
        "sequence": 1,
        "fixture_id": FIXTURE_ID,
        "deterministic_request_digest": REQUEST_DIGEST,
        "canonical_attempt_digest": CANONICAL_ATTEMPT_DIGEST,
        "provider_preflight_fingerprint": PROVIDER_FINGERPRINT,
        "frozen_v4_manifest_digest": FROZEN_V4_MANIFEST_DIGEST,
        "provider": "OpenAI",
        "ai_model_identifier": "gpt-4.1-mini-2025-04-14",
        "sdk_pin": "openai==2.45.0",
    }
    if any(evidence.get(key) != value for key, value in expected.items()):
        raise Sequence4GenerationGateError("approved preflight binding drifted")
    if (review.get("decision") != "approve"
            or review.get("generation_gate_binding_eligible") is not True
            or review.get("preflight_evidence_digest") != _digest(evidence_path)):
        raise Sequence4GenerationGateError("preflight evidence review is not approved")
    if not synthetic:
        if (_digest(evidence_path) != PREFLIGHT_EVIDENCE_DIGEST
                or _digest(review_path) != PREFLIGHT_REVIEW_DIGEST
                or evidence.get("input_tokens") != INPUT_TOKENS
                or str(evidence.get("conservative_maximum_generation_cost")) != CONSERVATIVE_COST):
            raise Sequence4GenerationGateError("approved live preflight bytes drifted")
    history_verifier = (
        verify_v4_preflight_history
        if current_state == "permanent_closed"
        else verify_completed_v4_preflight_history
    )
    history = history_verifier(
        evidence=evidence, output_root=output_root, repository_root=repository_root)
    if (any(review.get(key) != value for key, value in history.items())
            or review.get("preflight_evidence_digest") != _digest(evidence_path)
            or review.get("generation_authorized") is not False
            or review.get("authoritative") is not False):
        raise Sequence4GenerationGateError("approved live preflight history drifted")
    if current_state == "permanent_closed":
        if synthetic:
            preview = preview_v4_preflight_binding(
                output_root=output_root, repository_root=repository_root)
            if (preview.get("writes_performed") is not False
                    or preview.get("authoritative") is not False
                    or preview.get("generation_authorized") is not False):
                raise Sequence4GenerationGateError("synthetic preflight preview drifted")
        else:
            preview = preview_v4_preflight_binding(
                output_root=output_root, repository_root=repository_root)
            if (preview.get("resolved_binding_preview_digest") != PREFLIGHT_BINDING_PREVIEW_DIGEST
                    or preview.get("writes_performed") is not False
                    or preview.get("authoritative") is not False
                    or preview.get("generation_authorized") is not False):
                raise Sequence4GenerationGateError("approved live preflight preview drifted")
    return {
        **candidate_status,
        **expected,
        "input_tokens": evidence["input_tokens"],
        "conservative_maximum_generation_cost": evidence["conservative_maximum_generation_cost"],
    }


def verify_candidate_and_preflight(*, repository_root: Path = REPOSITORY_ROOT,
                                   output_root: Path) -> Mapping[str, object]:
    """Resolve the candidate only while the repository is permanently closed."""
    return _verify_candidate_and_preflight(
        repository_root=repository_root, output_root=output_root,
        current_state="permanent_closed")


def verify_candidate_and_preflight_for_active_generation(
    *, repository_root: Path = REPOSITORY_ROOT, output_root: Path,
) -> Mapping[str, object]:
    """Verify completed preflight history while exact generation is active."""
    return _verify_candidate_and_preflight(
        repository_root=repository_root, output_root=output_root,
        current_state="active_generation")


def verify_unresolved_generation_candidate(
    *, repository_root: Path = REPOSITORY_ROOT,
    require_closed_repository: bool = True,
) -> Mapping[str, object]:
    """Verify the inactive v4 candidate without claiming preflight resolution."""
    if _digest(UNRESOLVED_CANDIDATE_PATH) != UNRESOLVED_CANDIDATE_DIGEST:
        raise Sequence4GenerationGateError("unresolved generation candidate drifted")
    candidate = tomllib.loads(UNRESOLVED_CANDIDATE_PATH.read_text(encoding="utf-8"))
    manifest = json.loads(UNRESOLVED_MANIFEST_PATH.read_text(encoding="utf-8"))
    if (_digest(UNRESOLVED_MANIFEST_PATH) != UNRESOLVED_MANIFEST_DIGEST
            or manifest.get("candidate_digest") != UNRESOLVED_CANDIDATE_DIGEST
            or manifest.get("request_identity_digest") != "b5125e2075779306f0a4374676d442fa3016702bdb5143bc8e3a6b7173d9dd35"):
        raise Sequence4GenerationGateError("unresolved generation manifest drifted")
    _verify_v4_candidate_bindings(candidate, repository_root)
    scope = candidate["scope"]
    required_scope = {
        "run_series_id": RUN_SERIES_ID, "sequence": 4, "fixture_id": FIXTURE_ID,
        "operator_intent": OPERATOR_INTENT, "maximum_credential_reads": 1,
        "maximum_client_constructions": 1, "maximum_token_preflight_requests": 0,
        "maximum_ai_generation_requests": 1, "automatic_retries": 0,
        "maximum_output_tokens": 500, "maximum_total_spend_usd": "0.03",
        "human_grounding_review_required": True, "single_use": True,
    }
    if any(scope.get(key) != value for key, value in required_scope.items()):
        raise Sequence4GenerationGateError("generation-only scope drifted")
    approved = candidate["required_v4_preflight"]
    if approved.get("binding_status") != "fresh_v4_preflight_required":
        raise Sequence4GenerationGateError("candidate preflight requirement drifted")
    if candidate["authorization"]["ai_generation_authorized"] is not False:
        raise Sequence4GenerationGateError("inactive candidate grants authority")
    closed = repository_root / "docs/experiments/suggest-moving-service-questions/v2-pilot/closed-execution-manifest.json"
    current = closed.with_name("execution-manifest.json")
    if require_closed_repository and current.read_bytes() != closed.read_bytes():
        raise Sequence4GenerationGateError("repository authority is not permanently closed")
    return {
        "candidate_digest": _digest(UNRESOLVED_CANDIDATE_PATH),
        "manifest_digest": _digest(UNRESOLVED_MANIFEST_PATH),
        "binding_status": "fresh_v4_preflight_required",
        "live_generation_authorized": False,
    }


def verify_resolved_generation_candidate(
    *, repository_root: Path = REPOSITORY_ROOT,
    require_closed_repository: bool = True,
) -> Mapping[str, object]:
    """Verify the resolved candidate remains inactive and exactly preflight-bound."""
    if _digest(CANDIDATE_PATH) != CANDIDATE_DIGEST:
        raise Sequence4GenerationGateError("resolved generation candidate digest drifted")
    candidate = tomllib.loads(CANDIDATE_PATH.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if (_digest(MANIFEST_PATH) != MANIFEST_DIGEST
            or manifest.get("candidate_digest") != CANDIDATE_DIGEST
            or manifest.get("request_identity_digest") != "b5125e2075779306f0a4374676d442fa3016702bdb5143bc8e3a6b7173d9dd35"):
        raise Sequence4GenerationGateError("resolved generation manifest binding drifted")
    _verify_v4_candidate_bindings(candidate, repository_root)
    scope = candidate["scope"]
    required_scope = {
        "run_series_id": RUN_SERIES_ID, "sequence": 4, "fixture_id": FIXTURE_ID,
        "operator_intent": OPERATOR_INTENT, "maximum_credential_reads": 1,
        "maximum_client_constructions": 1, "maximum_token_preflight_requests": 0,
        "maximum_ai_generation_requests": 1, "automatic_retries": 0,
        "ai_generation_timeout_seconds": 12, "maximum_output_tokens": 500,
        "maximum_total_spend_usd": "0.03", "human_grounding_review_required": True,
        "single_use": True,
    }
    if any(scope.get(key) != value for key, value in required_scope.items()):
        raise Sequence4GenerationGateError("resolved generation-only scope drifted")
    approved = candidate["required_v4_preflight"]
    required_preflight = {
        "binding_status": "approved_v4_preflight_bound",
        "run_series_id": PREFLIGHT_RUN_SERIES_ID, "sequence": 1,
        "fixture_id": FIXTURE_ID, "preflight_evidence_digest": PREFLIGHT_EVIDENCE_DIGEST,
        "preflight_review_digest": PREFLIGHT_REVIEW_DIGEST,
        "binding_preview_digest": PREFLIGHT_BINDING_PREVIEW_DIGEST,
        "input_tokens": INPUT_TOKENS, "conservative_cost": CONSERVATIVE_COST,
        "request_digest": REQUEST_DIGEST,
        "canonical_attempt_digest": CANONICAL_ATTEMPT_DIGEST,
        "provider_fingerprint": PROVIDER_FINGERPRINT,
    }
    if any(approved.get(key) != value for key, value in required_preflight.items()):
        raise Sequence4GenerationGateError("resolved preflight binding drifted")
    if (candidate["authorization"]["ai_generation_authorized"] is not False
            or candidate["metadata"]["active_repository_authority"] is not False
            or candidate["metadata"]["valid_for_execution"] is not False):
        raise Sequence4GenerationGateError("resolved candidate grants authority")
    closed = repository_root / "docs/experiments/suggest-moving-service-questions/v2-pilot/closed-execution-manifest.json"
    current = closed.with_name("execution-manifest.json")
    if require_closed_repository and current.read_bytes() != closed.read_bytes():
        raise Sequence4GenerationGateError("repository authority is not permanently closed")
    return {
        "candidate_digest": CANDIDATE_DIGEST,
        "manifest_digest": MANIFEST_DIGEST,
        "binding_status": "approved_v4_preflight_bound",
        "live_generation_authorized": False,
    }


def _reject_duplicate_keys(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate JSON key")
        value[key] = item
    return value


def validate_generated_response(raw: object) -> tuple[str, object]:
    """Apply structural, semantic, and all prose checks without repair."""
    prepared = prepare_frozen_v4_pilot()
    if isinstance(raw, str):
        try:
            raw = json.loads(raw, object_pairs_hook=_reject_duplicate_keys)
        except (json.JSONDecodeError, ValueError):
            return "structural_failure", None
    if not isinstance(raw, Mapping):
        return "structural_failure", None
    try:
        v4_response = MovingServiceQuestionResponseV4.model_validate(raw)
    except Exception:
        return "structural_failure", None
    try:
        v2_document = v4_response.model_dump(mode="json")
        v2_document["prompt_version"] = "moving-service-questions-prompt-v2"
        v2_document["schema_version"] = "moving-service-questions-schema-v2"
        v2_prepared = prepare_frozen_v2_pilot()
        validate_response_v2(v2_prepared.request, v2_document)
        return "validated", v4_response
    except ProseValidationError as error:
        return "prose_failure", tuple(error.violation_codes)
    except ResponseValidationError:
        return "semantic_failure", None


def write_generation_outcome(*, output_root: Path, raw: object, now: datetime) -> Mapping[str, object]:
    paths = generation_paths(output_root)
    if paths.audit.exists() or paths.closure.exists():
        raise Sequence4GenerationGateError("sequence-4 generation slot is already consumed")
    classification, result = validate_generated_response(raw)
    audit: dict[str, object] = {
        "run_series_id": RUN_SERIES_ID, "sequence": 4, "fixture_id": FIXTURE_ID,
        "phase": "generation", "preflight_attempted": False,
        "credential_lookup_attempted": True, "client_construction_attempted": True,
        "generation_attempted": True, "generation_request_count": 1,
        "automatic_retries": 0, "generation_authorized": True,
        "validation_outcome": classification, "prose_violation_codes": [],
        "pydantic_validation_succeeded": classification != "structural_failure",
        "semantic_validation_succeeded": classification in {"validated", "prose_failure"},
        "prose_validation_succeeded": classification == "validated",
        "complete_response_rejected": classification != "validated",
        "partial_salvage_used": False,
        "fallback_used": classification != "validated", "fallback_version": None,
        "fallback_question_id": None,
        "response_evidence_sha256": None, "human_review_status": "pending",
        "authorization_consumed": True, "generation_closed": True,
        "generation_succeeded": classification == "validated",
    }
    if classification == "validated":
        assert isinstance(result, MovingServiceQuestionResponseV4)
        audit["response_evidence_sha256"] = _exclusive(paths.response_evidence, result.model_dump(mode="json"))
    else:
        if classification == "prose_failure":
            audit["prose_violation_codes"] = list(result)  # type: ignore[arg-type]
            diagnostic_raw = (
                json.loads(raw, object_pairs_hook=_reject_duplicate_keys)
                if isinstance(raw, str) else raw
            )
            assert isinstance(diagnostic_raw, Mapping)
            v4_response = MovingServiceQuestionResponseV4.model_validate(diagnostic_raw)
            v2_document = v4_response.model_dump(mode="json")
            v2_document["prompt_version"] = "moving-service-questions-prompt-v2"
            v2_document["schema_version"] = "moving-service-questions-schema-v2"
            v2_response = MovingServiceQuestionResponseV2.model_validate(v2_document)
            diagnostics = collect_prose_violation_diagnostics(
                prepare_frozen_v2_pilot().request, v2_response
            )
            audit["rejected_prose_diagnostics"] = [item.as_dict() for item in diagnostics]
        fallback = select_fallback_v2(prepare_frozen_v2_pilot().request)
        audit["fallback_used"] = fallback is not None
        audit["fallback_version"] = FALLBACK_VERSION_V2
        audit["fallback_question_id"] = fallback.question_id if fallback else None
    audit_digest = _exclusive(paths.audit, audit)
    closure = {
        "run_series_id": RUN_SERIES_ID, "sequence": 4, "fixture_id": FIXTURE_ID,
        "phase": "generation", "closed_at": _stamp(now), "authorization_closed": True,
        "credential_access_authorized": False, "token_preflight_authorized": False,
        "ai_generation_authorized": False, "formal_evaluation_authorized": False,
        "stage_c_authorized": False, "production_use_authorized": False,
    }
    closure_digest = _exclusive(paths.closure, closure)
    return {**audit, "audit_digest": audit_digest, "closure_digest": closure_digest}


def consume_preflight_evidence_for_generation(*, output_root: Path, authorization_digest: str,
                                              now: datetime) -> str:
    paths = generation_paths(output_root)
    return _exclusive(paths.preflight_consumption, {
        "run_series_id": RUN_SERIES_ID, "sequence": 4, "fixture_id": FIXTURE_ID,
        "phase": "generation", "preflight_evidence_digest": PREFLIGHT_EVIDENCE_DIGEST,
        "preflight_review_digest": PREFLIGHT_REVIEW_DIGEST,
        "generation_authorization_digest": authorization_digest,
        "consumed_at": _stamp(now), "consumed_before_generation": True,
        "reusable": False,
    })


def review_and_delete_response(*, output_root: Path, evidence_sha256: str, reviewer: str,
                               decision: str, reviewed_at: datetime,
                               grounding_accuracy: bool, invented_user_fact: bool,
                               irrelevant_detail: bool, modality_overstatement: bool,
                               service_selection_overstatement: bool, clarity_score: int,
                               usefulness_score: int, fallback_comparison: str,
                               notes: str) -> Mapping[str, object]:
    paths = generation_paths(output_root)
    if decision not in {"approve", "reject", "request_changes"} or not reviewer.strip() or len(notes) > 500:
        raise Sequence4GenerationGateError("grounding review is invalid")
    evidence = paths.response_evidence.read_bytes()
    if hashlib.sha256(evidence).hexdigest() != evidence_sha256:
        raise Sequence4GenerationGateError("validated response evidence drifted")
    safe = grounding_accuracy and not any((invented_user_fact, irrelevant_detail, modality_overstatement, service_selection_overstatement))
    if decision == "approve" and not safe:
        raise Sequence4GenerationGateError("approved grounding review is unsafe")
    if not (1 <= clarity_score <= 5 and 1 <= usefulness_score <= 5):
        raise Sequence4GenerationGateError("grounding scores are invalid")
    record = {
        "run_series_id": RUN_SERIES_ID, "sequence": 4, "fixture_id": FIXTURE_ID,
        "phase": "generation_grounding_review", "response_evidence_digest": evidence_sha256,
        "reviewer": reviewer, "decision": decision, "reviewed_at": _stamp(reviewed_at),
        "grounding_accuracy": grounding_accuracy, "invented_user_fact": invented_user_fact,
        "irrelevant_detail": irrelevant_detail, "modality_overstatement": modality_overstatement,
        "service_selection_overstatement": service_selection_overstatement,
        "clarity_score": clarity_score, "usefulness_score": usefulness_score,
        "fallback_comparison": fallback_comparison, "bounded_notes": notes,
        "authoritative": False, "generation_authorized": False,
    }
    review_digest = _exclusive(paths.grounding_review, record)
    paths.response_evidence.unlink()
    deletion = {
        "run_series_id": RUN_SERIES_ID, "sequence": 4, "fixture_id": FIXTURE_ID,
        "evidence_path_identifier": paths.response_evidence.name,
        "response_evidence_digest": evidence_sha256, "deletion_reason": "review_signoff",
        "review_decision": decision, "deleted_at": _stamp(reviewed_at),
        "deletion_completed": not paths.response_evidence.exists(),
        "contains_response_content": False,
    }
    deletion_digest = _exclusive(paths.deletion, deletion)
    return {"review_digest": review_digest, "deletion_digest": deletion_digest, **record}
