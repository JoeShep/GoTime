"""Non-activating install, review, and planning for one v2 preflight artifact."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

from run_openai_stage_b_v2_pilot import DEFAULT_OUTPUT_ROOT, prepare_frozen_v2_pilot
from run_openai_stage_b_v2_two_gate import frozen_binding_identity, phase_paths
from v2_phase_authorization_candidates import (
    MANIFEST_PATH,
    UMBRELLA_DIGEST,
    load_inactive_phase_candidate,
)
from v2_two_gate_authorization import V2TwoGateAuthorizationError, validate_phase_authorization

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
EXECUTION_MANIFEST = REPOSITORY_ROOT / (
    "docs/experiments/suggest-moving-service-questions/v2-pilot/execution-manifest.json"
)
CLOSED_EXECUTION_MANIFEST = EXECUTION_MANIFEST.with_name("closed-execution-manifest.json")
PERMANENT_CLOSED_AUTHORIZATION = EXECUTION_MANIFEST.with_name("openai-execution-authorization.toml")
RUN_SERIES_ID = "moving-service-stage-b-v2-pilot-20260802"
SEQUENCE = 1
FIXTURE_ID = "storage_unknown"
PREFIX = "001-storage_unknown"
MAX_NOTES = 500
DECISIONS = frozenset({"approve", "reject", "request_changes"})
INSTALLATION_FIELDS = frozenset({
    "capability", "phase", "run_series_id", "sequence", "fixture_id", "source_digest",
    "installed_digest", "installed_path", "candidate_digest",
    "phase_candidate_manifest_digest", "umbrella_candidate_digest",
    "frozen_v2_manifest_digest", "prompt_digest", "provider_schema_digest",
    "pilot_configuration_digest", "provider", "ai_model_identifier", "sdk_pin",
    "approver", "approved_at", "activated_at", "expires_at", "authorization_reason",
    "installed_at", "closed_execution_manifest_digest",
    "permanent_closed_authorization_digest", "permanent_closed_state_verified",
    "authoritative", "activation_status", "activation_review_status",
})
REVIEW_FIELDS = frozenset({
    "capability", "phase", "run_series_id", "sequence", "fixture_id",
    "installed_artifact_path", "installed_artifact_digest", "installation_record_digest",
    "candidate_digest", "frozen_v2_manifest_digest", "prompt_digest",
    "provider_schema_digest", "pilot_configuration_digest", "reviewer", "decision",
    "reviewed_at", "bounded_notes", "artifact_validity_confirmed",
    "preflight_only_scope_confirmed", "permanent_closed_state_confirmed",
    "conflicting_records_absent", "authoritative", "activated", "activation_eligible",
    "activation_deadline", "review_record_digest_policy",
})


class InstallationPathError(ValueError):
    pass


class SourceIntegrityError(ValueError):
    pass


class PackageIntegrityError(ValueError):
    pass


class ClosedStateError(ValueError):
    pass


class ConflictingStateError(ValueError):
    pass


class ValidityWindowError(ValueError):
    pass


class InstallationWriteError(OSError):
    pass


class ReviewValidationError(ValueError):
    pass


class ReviewWriteError(OSError):
    pass


class ActivationPrerequisiteError(ValueError):
    pass


def _digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _digest(path: Path) -> str:
    return _digest_bytes(path.read_bytes())


def _stamp(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValidityWindowError("time must be timezone-aware")
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _utc(value: object, field: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValidityWindowError(f"{field} must be whole-second UTC")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as error:
        raise ValidityWindowError(f"{field} is invalid") from error
    if parsed.microsecond:
        raise ValidityWindowError(f"{field} must be whole-second UTC")
    return parsed


def review_paths(output_root: Path = DEFAULT_OUTPUT_ROOT) -> dict[str, Path]:
    base = output_root / RUN_SERIES_ID
    review = base / "authorization-review"
    return {
        "directory": review,
        "installed": review / f"{PREFIX}-preflight-rendered.toml",
        "installation": review / f"{PREFIX}-preflight-installation.json",
        "activation_review": review / f"{PREFIX}-preflight-activation-review.json",
        "future_active": base / f"{PREFIX}-preflight-authorization.toml",
        "future_closure": base / f"{PREFIX}-preflight-closure.json",
    }


def validate_source_path(path: Path) -> Path:
    if not path.is_absolute() or ".." in path.parts:
        raise InstallationPathError("source must be an absolute traversal-free path under /tmp")
    lexical = Path(os.path.normpath(str(path)))
    if lexical == Path("/tmp") or not lexical.is_relative_to(Path("/tmp")):
        raise InstallationPathError("source must be beneath /tmp")
    current = Path("/")
    for component in lexical.parts[1:]:
        current /= component
        if current.is_symlink():
            raise InstallationPathError("source path must not contain symlinks")
    if not lexical.is_file() or lexical.is_symlink():
        raise InstallationPathError("source must be a regular non-symlink file")
    mode = stat.S_IMODE(lexical.stat(follow_symlinks=False).st_mode)
    if mode & 0o077:
        raise InstallationPathError("source permissions must be owner-only")
    return lexical


def _read_source_secure(path: Path) -> bytes:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags)
    try:
        details = os.fstat(descriptor)
        if not stat.S_ISREG(details.st_mode) or stat.S_IMODE(details.st_mode) & 0o077:
            raise InstallationPathError("source must remain an owner-only regular file")
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            return stream.read()
    finally:
        os.close(descriptor)


def _verify_closed_state() -> tuple[str, str]:
    if EXECUTION_MANIFEST.read_bytes() != CLOSED_EXECUTION_MANIFEST.read_bytes():
        raise ClosedStateError("permanent execution manifest is not closed")
    manifest = json.loads(EXECUTION_MANIFEST.read_text(encoding="utf-8"))
    authorization_digest = _digest(PERMANENT_CLOSED_AUTHORIZATION)
    if (
        manifest.get("status") != "closed_no_execution_authorized"
        or manifest.get("authorization_digest") != authorization_digest
        or any(manifest.get(key) is not False for key in (
            "credential_access_authorized", "token_preflight_authorized",
            "ai_generation_authorized", "formal_evaluation_authorized",
            "stage_c_authorized", "production_use_authorized",
        ))
    ):
        raise ClosedStateError("permanent closed authorization binding drifted")
    return _digest(EXECUTION_MANIFEST), authorization_digest


def _verify_package() -> tuple[Mapping[str, object], str, str]:
    try:
        candidate = load_inactive_phase_candidate("preflight")
        manifest_digest = _digest(MANIFEST_PATH)
        prepared = prepare_frozen_v2_pilot()
    except (OSError, ValueError) as error:
        raise PackageIntegrityError("reviewed candidate or frozen package failed verification") from error
    if candidate.digest != "a3f1000bb1b336bad4fb35e9316520f59eb1eeb96e257f19eb13e9d495504a6c":
        raise PackageIntegrityError("preflight candidate digest drifted")
    if manifest_digest != "a9e8f21c65c15d0a0fccaffdbd44902c7e2a88416b97f53c562f331ae1740979":
        raise PackageIntegrityError("phase-candidate manifest digest drifted")
    return prepared.frozen_manifest, candidate.digest, manifest_digest


def _validate_artifact(
    artifact: Mapping[str, object], *, digest: str, now: datetime,
) -> Mapping[str, object]:
    prepared = prepare_frozen_v2_pilot()
    try:
        validate_phase_authorization(
            artifact, digest=digest, phase="preflight", now=now,
            expected_bindings=frozen_binding_identity(prepared),
        )
    except V2TwoGateAuthorizationError as error:
        message = str(error)
        if "expired" in message or "window" in message or "UTC" in message:
            raise ValidityWindowError("rendered authorization validity failed") from error
        raise SourceIntegrityError("rendered authorization scope or binding failed") from error
    text = json.dumps(artifact, sort_keys=True)
    if "_REQUIRED" in text:
        raise SourceIntegrityError("rendered authorization contains unresolved placeholders")
    return artifact


def _conflicts(paths: Mapping[str, Path], output_root: Path) -> None:
    if any(paths[key].exists() for key in ("installed", "installation", "activation_review", "future_active")):
        raise ConflictingStateError("authorization review or active artifact already exists")
    attempts = phase_paths(output_root)
    if any(attempts[key].exists() for key in (
        "preflight_audit", "preflight_evidence", "preflight_review",
        "preflight_consumption", "preflight_closure",
    )):
        raise ConflictingStateError("preflight sequence has conflicting or consumed state")


def _secure_directory(path: Path) -> None:
    current = Path("/")
    for component in path.absolute().parts[1:]:
        current /= component
        if current.is_symlink():
            raise InstallationWriteError("review directory path contains a symlink")
    path.mkdir(parents=True, mode=0o700, exist_ok=True)
    if path.is_symlink() or not path.is_dir() or path.resolve(strict=True) != path.absolute():
        raise InstallationWriteError("review directory is not a real directory")
    path.chmod(0o700)


def _exclusive_bytes(path: Path, value: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def _json_bytes(value: Mapping[str, object]) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def install_preflight_for_review(
    *, source: Path, expected_sha256: str, output_root: Path = DEFAULT_OUTPUT_ROOT,
    now: datetime,
) -> Mapping[str, object]:
    source = validate_source_path(source)
    if len(expected_sha256) != 64 or any(character not in "0123456789abcdef" for character in expected_sha256):
        raise SourceIntegrityError("expected SHA-256 must be lowercase hexadecimal")
    source_bytes = _read_source_secure(source)
    source_digest = _digest_bytes(source_bytes)
    if source_digest != expected_sha256:
        raise SourceIntegrityError("rendered source digest mismatch")
    try:
        artifact = tomllib.loads(source_bytes.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        raise SourceIntegrityError("rendered source is malformed TOML") from error
    _, candidate_digest, candidate_manifest_digest = _verify_package()
    _validate_artifact(artifact, digest=source_digest, now=now)
    closed_manifest_digest, closed_authorization_digest = _verify_closed_state()
    paths = review_paths(output_root)
    _conflicts(paths, output_root)
    approval = artifact["approval"]
    bindings = artifact["bindings"]
    installation = {
        "capability": "suggest_moving_service_questions", "phase": "preflight",
        "run_series_id": RUN_SERIES_ID, "sequence": SEQUENCE, "fixture_id": FIXTURE_ID,
        "source_digest": source_digest, "installed_digest": source_digest,
        "installed_path": str(paths["installed"].resolve()),
        "candidate_digest": candidate_digest,
        "phase_candidate_manifest_digest": candidate_manifest_digest,
        "umbrella_candidate_digest": UMBRELLA_DIGEST,
        "frozen_v2_manifest_digest": frozen_binding_identity(prepare_frozen_v2_pilot())["frozen_v2_manifest_digest"],
        "prompt_digest": bindings["prompt_digest"],
        "provider_schema_digest": bindings["provider_schema_digest"],
        "pilot_configuration_digest": bindings["pilot_configuration_digest"],
        "provider": bindings["provider"], "ai_model_identifier": bindings["ai_model_identifier"],
        "sdk_pin": bindings["sdk_pin"], "approver": approval["approver"],
        "approved_at": approval["approved_at"], "activated_at": approval["activated_at"],
        "expires_at": approval["expires_at"], "authorization_reason": approval["authorization_reason"],
        "installed_at": _stamp(now), "closed_execution_manifest_digest": closed_manifest_digest,
        "permanent_closed_authorization_digest": closed_authorization_digest,
        "permanent_closed_state_verified": True, "authoritative": False,
        "activation_status": "not_activated", "activation_review_status": "pending",
    }
    _secure_directory(paths["directory"])
    try:
        _exclusive_bytes(paths["installed"], source_bytes)
        if paths["installed"].read_bytes() != source_bytes:
            raise InstallationWriteError("installed bytes differ from rendered source")
        _exclusive_bytes(paths["installation"], _json_bytes(installation))
    except BaseException as error:
        paths["installed"].unlink(missing_ok=True)
        paths["installation"].unlink(missing_ok=True)
        if isinstance(error, (ConflictingStateError, InstallationWriteError)):
            raise
        raise InstallationWriteError("exclusive installation failed") from error
    return {
        "installed_path": str(paths["installed"].resolve()), "sha256": source_digest,
        "installation_record": str(paths["installation"].resolve()),
        "installation_record_sha256": _digest(paths["installation"]), "authoritative": False,
    }


def _load_installed(
    *, output_root: Path, artifact_sha256: str, now: datetime,
) -> tuple[dict[str, object], dict[str, object], dict[str, Path], str]:
    paths = review_paths(output_root)
    if paths["future_active"].exists():
        raise ClosedStateError("active local preflight authorization exists")
    if not paths["installed"].is_file() or paths["installed"].is_symlink():
        raise ConflictingStateError("installed review artifact is missing or unsafe")
    if not paths["installation"].is_file() or paths["installation"].is_symlink():
        raise ConflictingStateError("installation record is missing or unsafe")
    installed_bytes = paths["installed"].read_bytes()
    installed_digest = _digest_bytes(installed_bytes)
    if installed_digest != artifact_sha256:
        raise ReviewValidationError("installed artifact digest mismatch")
    installation = json.loads(paths["installation"].read_text(encoding="utf-8"))
    binding = frozen_binding_identity(prepare_frozen_v2_pilot())
    if (
        set(installation) != INSTALLATION_FIELDS
        or installation.get("capability") != "suggest_moving_service_questions"
        or installation.get("phase") != "preflight"
        or installation.get("run_series_id") != RUN_SERIES_ID
        or installation.get("sequence") != SEQUENCE
        or installation.get("fixture_id") != FIXTURE_ID
        or installation.get("source_digest") != installed_digest
        or installation.get("installed_digest") != installed_digest
        or installation.get("installed_path") != str(paths["installed"].resolve())
        or installation.get("candidate_digest") != "a3f1000bb1b336bad4fb35e9316520f59eb1eeb96e257f19eb13e9d495504a6c"
        or installation.get("phase_candidate_manifest_digest") != "a9e8f21c65c15d0a0fccaffdbd44902c7e2a88416b97f53c562f331ae1740979"
        or installation.get("umbrella_candidate_digest") != UMBRELLA_DIGEST
        or installation.get("frozen_v2_manifest_digest") != binding["frozen_v2_manifest_digest"]
        or installation.get("authoritative") is not False
        or installation.get("activation_status") != "not_activated"
        or installation.get("activation_review_status") != "pending"
    ):
        raise ReviewValidationError("installation record drifted")
    artifact = tomllib.loads(installed_bytes.decode("utf-8"))
    _verify_package()
    _verify_closed_state()
    _validate_artifact(artifact, digest=installed_digest, now=now)
    approval = artifact["approval"]
    bindings = artifact["bindings"]
    if any(installation.get(key) != value for key, value in {
        "approver": approval["approver"], "approved_at": approval["approved_at"],
        "activated_at": approval["activated_at"], "expires_at": approval["expires_at"],
        "authorization_reason": approval["authorization_reason"],
        "prompt_digest": bindings["prompt_digest"],
        "provider_schema_digest": bindings["provider_schema_digest"],
        "pilot_configuration_digest": bindings["pilot_configuration_digest"],
        "provider": bindings["provider"], "ai_model_identifier": bindings["ai_model_identifier"],
        "sdk_pin": bindings["sdk_pin"],
    }.items()):
        raise ReviewValidationError("installation record does not match installed artifact")
    return artifact, installation, paths, _digest(paths["installation"])


def review_preflight_activation(
    *, artifact_sha256: str, reviewer: str, decision: str, reviewed_at: str,
    notes: str, output_root: Path = DEFAULT_OUTPUT_ROOT, now: datetime,
) -> Mapping[str, object]:
    if decision not in DECISIONS:
        raise ReviewValidationError("review decision is invalid")
    if not reviewer.strip() or not notes.strip() or len(notes) > MAX_NOTES:
        raise ReviewValidationError("reviewer and bounded notes are required")
    reviewed = _utc(reviewed_at, "reviewed_at")
    if reviewed > now.astimezone(timezone.utc):
        raise ReviewValidationError("review timestamp is in the future")
    artifact, installation, paths, installation_digest = _load_installed(
        output_root=output_root, artifact_sha256=artifact_sha256, now=now,
    )
    if paths["activation_review"].exists():
        raise ConflictingStateError("activation review already exists")
    attempts = phase_paths(output_root)
    if any(attempts[key].exists() for key in (
        "preflight_audit", "preflight_evidence", "preflight_consumption", "preflight_closure",
    )):
        raise ConflictingStateError("preflight sequence is already used")
    binding = frozen_binding_identity(prepare_frozen_v2_pilot())
    expires_at = str(artifact["approval"]["expires_at"])
    record = {
        "capability": "suggest_moving_service_questions", "phase": "preflight",
        "run_series_id": RUN_SERIES_ID, "sequence": SEQUENCE, "fixture_id": FIXTURE_ID,
        "installed_artifact_path": str(paths["installed"].resolve()),
        "installed_artifact_digest": artifact_sha256,
        "installation_record_digest": installation_digest,
        "candidate_digest": installation["candidate_digest"],
        "frozen_v2_manifest_digest": binding["frozen_v2_manifest_digest"],
        "prompt_digest": binding["prompt_digest"],
        "provider_schema_digest": binding["provider_schema_digest"],
        "pilot_configuration_digest": binding["pilot_configuration_digest"],
        "reviewer": reviewer, "decision": decision, "reviewed_at": reviewed_at,
        "bounded_notes": notes, "artifact_validity_confirmed": True,
        "preflight_only_scope_confirmed": True, "permanent_closed_state_confirmed": True,
        "conflicting_records_absent": True, "authoritative": False, "activated": False,
        "activation_eligible": decision == "approve", "activation_deadline": expires_at,
        "review_record_digest_policy": "external_sha256_of_exact_bytes",
    }
    try:
        _exclusive_bytes(paths["activation_review"], _json_bytes(record))
    except OSError as error:
        raise ReviewWriteError("exclusive activation-review write failed") from error
    return {
        "review_path": str(paths["activation_review"].resolve()),
        "review_sha256": _digest(paths["activation_review"]), "decision": decision,
        "authoritative": False, "activated": False,
    }


def plan_preflight_activation(
    *, artifact_sha256: str, installation_record_sha256: str,
    activation_review_sha256: str, output_root: Path = DEFAULT_OUTPUT_ROOT,
    now: datetime,
) -> Mapping[str, object]:
    artifact, _, paths, actual_installation_digest = _load_installed(
        output_root=output_root, artifact_sha256=artifact_sha256, now=now,
    )
    if actual_installation_digest != installation_record_sha256:
        raise ActivationPrerequisiteError("installation-record digest mismatch")
    if not paths["activation_review"].is_file() or paths["activation_review"].is_symlink():
        raise ActivationPrerequisiteError("approved activation review is missing")
    if _digest(paths["activation_review"]) != activation_review_sha256:
        raise ActivationPrerequisiteError("activation-review digest mismatch")
    review = json.loads(paths["activation_review"].read_text(encoding="utf-8"))
    if (
        set(review) != REVIEW_FIELDS
        or review.get("decision") != "approve"
        or review.get("activation_eligible") is not True
        or review.get("authoritative") is not False
        or review.get("activated") is not False
        or review.get("installed_artifact_digest") != artifact_sha256
        or review.get("installation_record_digest") != installation_record_sha256
    ):
        raise ActivationPrerequisiteError("activation review does not approve this artifact")
    _verify_closed_state()
    if paths["future_active"].exists():
        raise ActivationPrerequisiteError("future active destination already exists")
    attempts = phase_paths(output_root)
    if any(attempts[key].exists() for key in (
        "preflight_audit", "preflight_evidence", "preflight_consumption", "preflight_closure",
    )):
        raise ActivationPrerequisiteError("sequence is used or conflicting")
    return {
        "source_installed_artifact": str(paths["installed"].resolve()),
        "future_active_destination": str(paths["future_active"].resolve()),
        "expected_active_artifact_digest": artifact_sha256,
        "execution_manifest_transition_required": True,
        "execution_manifest_path": str(EXECUTION_MANIFEST),
        "closure_artifact": str(paths["future_closure"].resolve()),
        "remaining_operator_confirmations": [
            "approve_exact_atomic_manifest_transition",
            "authorize_one_live_preflight_separately",
        ],
        "authoritative": False, "activated": False, "writes_performed": False,
        "activation_deadline": artifact["approval"]["expires_at"],
    }
