"""Typed, fixed-path cleanup for an expired unactivated sequence-2 review package."""
from __future__ import annotations

import hashlib
import json
import os
import tomllib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

from run_openai_stage_b_v2_pilot import DEFAULT_OUTPUT_ROOT, prepare_frozen_v2_pilot
from run_openai_stage_b_v2_two_gate import frozen_binding_identity, phase_paths
from v2_phase_authorization_candidates import UMBRELLA_DIGEST
from v2_preflight_authorization_activation import REPOSITORY_ROOT, activation_paths
from v2_preflight_authorization_installation import (
    INSTALLATION_FIELDS,
    REVIEW_FIELDS,
    _load_installed,
)
from v2_sequence_2_preflight_authorization import (
    CANDIDATE_DIGEST,
    CANDIDATE_MANIFEST_DIGEST,
    _options,
)
from v2_two_gate_authorization import V2TwoGateAuthorizationError, validate_phase_authorization

CAPABILITY = "suggest_moving_service_questions"
RUN_SERIES = "moving-service-stage-b-v2-pilot-20260802"
SEQUENCE = 2
FIXTURE = "storage_unknown"
PREFIX = "002-storage_unknown"
REASON = "expired_unactivated_review_package"
SOURCE_PATH = Path("/tmp/gotime-v2-sequence-2-preflight-authorization.toml")
CLEANUP_NAME = f"{PREFIX}-expired-review-package-cleanup.json"


class CleanupError(ValueError):
    """Expired review package is not eligible for fixed cleanup."""


@dataclass(frozen=True)
class VerifiedExpiredReviewPackage:
    paths: tuple[Path, Path, Path, Path]
    digests: tuple[str, str, str, str]
    expires_at: str
    cleanup_record: Path


def _digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _digest(path: Path) -> str:
    return _digest_bytes(path.read_bytes())


def _stamp(value: datetime) -> str:
    if value.tzinfo is None:
        raise CleanupError("cleanup timestamp must be timezone-aware")
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _utc(value: object) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise CleanupError("authorization expiration is invalid")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as error:
        raise CleanupError("authorization expiration is invalid") from error
    if parsed.microsecond:
        raise CleanupError("authorization expiration is invalid")
    return parsed


def _secure_bytes(path: Path, expected: Path) -> bytes:
    if path != expected or path.is_symlink() or not path.is_file():
        raise CleanupError("cleanup path is missing, substituted, or unsafe")
    if path.resolve(strict=True) != expected:
        raise CleanupError("cleanup path resolved outside its fixed location")
    return path.read_bytes()


def _paths(output_root: Path, source_path: Path) -> tuple[tuple[Path, Path, Path, Path], Path]:
    base = output_root / RUN_SERIES
    review = base / "authorization-review"
    files = (
        source_path,
        review / f"{PREFIX}-preflight-rendered.toml",
        review / f"{PREFIX}-preflight-installation.json",
        review / f"{PREFIX}-preflight-activation-review.json",
    )
    return files, base / CLEANUP_NAME


def _verify_closed_and_unused(repository_root: Path, output_root: Path) -> None:
    activation = activation_paths(repository_root=repository_root, output_root=output_root, sequence=SEQUENCE)
    if activation.execution_manifest.read_bytes() != activation.closed_manifest.read_bytes():
        raise CleanupError("execution manifest is not permanently closed")
    conflicts = (activation.active, activation.activation, activation.journal, activation.closure)
    attempts = phase_paths(output_root, SEQUENCE)
    conflicts += tuple(attempts[key] for key in (
        "preflight_audit", "preflight_evidence", "preflight_review",
        "preflight_consumption", "preflight_closure",
    ))
    cancellation = output_root / RUN_SERIES / f"{PREFIX}-preflight-cancellation.json"
    if any(path.exists() for path in conflicts + (cancellation,)):
        raise CleanupError("sequence 2 is active, activated, consumed, or otherwise used")


def verify_expired_sequence_2_review_package(
    *, artifact_sha256: str, installation_record_sha256: str,
    activation_review_sha256: str, now: datetime,
    repository_root: Path = REPOSITORY_ROOT, output_root: Path = DEFAULT_OUTPUT_ROOT,
    source_path: Path = SOURCE_PATH,
) -> VerifiedExpiredReviewPackage:
    """Verify exact expired bytes using the reviewed typed phase validator."""
    files, cleanup_record = _paths(output_root, source_path)
    if cleanup_record.exists():
        raise CleanupError("cleanup record already exists")
    values = tuple(_secure_bytes(path, path) for path in files)
    digests = tuple(_digest_bytes(value) for value in values)
    if digests != (
        artifact_sha256, artifact_sha256,
        installation_record_sha256, activation_review_sha256,
    ):
        raise CleanupError("expired review package digest mismatch")
    if values[0] != values[1]:
        raise CleanupError("rendered source and installed bytes differ")
    try:
        artifact = tomllib.loads(values[1].decode("utf-8"))
        installation = json.loads(values[2])
        review = json.loads(values[3])
    except (UnicodeDecodeError, tomllib.TOMLDecodeError, json.JSONDecodeError) as error:
        raise CleanupError("expired review package is malformed") from error
    approval = artifact.get("approval", {})
    activated_at = _utc(approval.get("activated_at"))
    expires_at = _utc(approval.get("expires_at"))
    if now.astimezone(timezone.utc) < expires_at:
        raise CleanupError("review authorization is not expired")

    # This is the authoritative schema check. Phase identity is metadata.phase;
    # permission booleans and request counts are validated by the same typed
    # lifecycle validator used during rendering, installation, and activation.
    binding = frozen_binding_identity(prepare_frozen_v2_pilot())
    validation_time = activated_at
    try:
        verified = validate_phase_authorization(
            artifact, digest=artifact_sha256, phase="preflight",
            now=validation_time, expected_bindings=binding, expected_sequence=SEQUENCE,
        )
    except V2TwoGateAuthorizationError as error:
        raise CleanupError("rendered authorization failed typed preflight validation") from error
    if verified.phase != "preflight":
        raise CleanupError("rendered authorization phase is not preflight")

    # Reuse the installed-package loader at its reviewed in-window instant. It
    # verifies candidate, manifest, frozen bindings, record schema, and exact bytes.
    try:
        _, loaded_installation, loaded_paths, actual_installation_digest = _load_installed(
            output_root=output_root, artifact_sha256=artifact_sha256,
            now=validation_time, sequence=SEQUENCE, **_options(),
        )
    except (OSError, ValueError) as error:
        raise CleanupError("installed review package failed lifecycle validation") from error
    if loaded_installation != installation or actual_installation_digest != installation_record_sha256:
        raise CleanupError("installation record binding drifted")
    if set(installation) != INSTALLATION_FIELDS or installation.get("authoritative") is not False or installation.get("activation_status") != "not_activated":
        raise CleanupError("installation record is authoritative or activated")
    if set(review) != REVIEW_FIELDS or any((
        review.get("capability") != CAPABILITY,
        review.get("phase") != "preflight",
        review.get("run_series_id") != RUN_SERIES,
        review.get("sequence") != SEQUENCE,
        review.get("fixture_id") != FIXTURE,
        review.get("installed_artifact_path") != str(loaded_paths["installed"].resolve()),
        review.get("installed_artifact_digest") != artifact_sha256,
        review.get("installation_record_digest") != installation_record_sha256,
        review.get("candidate_digest") != CANDIDATE_DIGEST,
        review.get("authoritative") is not False,
        review.get("activated") is not False,
    )):
        raise CleanupError("activation-review record drifted or indicates activation")
    if review.get("frozen_v2_manifest_digest") != binding["frozen_v2_manifest_digest"]:
        raise CleanupError("activation-review frozen binding drifted")
    _verify_closed_and_unused(repository_root, output_root)
    return VerifiedExpiredReviewPackage(files, digests, str(approval["expires_at"]), cleanup_record)


def _json_bytes(value: Mapping[str, object]) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _exclusive(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.parent.chmod(0o700)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(value)
        stream.flush()
        os.fsync(stream.fileno())


def _replace_record(path: Path, value: bytes) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    _exclusive(temporary, value)
    os.replace(temporary, path)


def cleanup_expired_sequence_2_review_package(
    *, artifact_sha256: str, installation_record_sha256: str,
    activation_review_sha256: str, now: datetime, operator: str = "",
    repository_root: Path = REPOSITORY_ROOT, output_root: Path = DEFAULT_OUTPUT_ROOT,
    source_path: Path = SOURCE_PATH,
) -> Mapping[str, object]:
    verified = verify_expired_sequence_2_review_package(
        artifact_sha256=artifact_sha256,
        installation_record_sha256=installation_record_sha256,
        activation_review_sha256=activation_review_sha256, now=now,
        repository_root=repository_root, output_root=output_root, source_path=source_path,
    )
    record = {
        "capability": CAPABILITY, "run_series_id": RUN_SERIES,
        "sequence": SEQUENCE, "fixture_id": FIXTURE, "reason": REASON,
        "paths": [str(path.resolve()) for path in verified.paths],
        "pre_deletion_digests": list(verified.digests),
        "expired_at": verified.expires_at, "cleanup_timestamp": _stamp(now),
        "execution_manifest_closed": True, "active_authorization_absent": True,
        "activation_record_absent": True, "transaction_journal_absent": True,
        "authoritative": False, "activated": False,
        "operator": operator.strip() or "not_supplied",
        "status": "cleanup_prepared",
        "deleted": False,
        "deletion_results": [False, False, False, False],
        "credential_or_provider_operation_occurred": False,
        "sequence_consumed": False,
    }
    _exclusive(verified.cleanup_record, _json_bytes(record))
    try:
        for index, path in enumerate(verified.paths):
            path.unlink()
            record["deletion_results"][index] = True
            _replace_record(verified.cleanup_record, _json_bytes(record))
    except OSError as error:
        raise CleanupError("exact-file deletion failed; cleanup review required") from error
    if any(path.exists() for path in verified.paths):
        raise CleanupError("one or more exact cleanup files remain")
    _verify_closed_and_unused(repository_root, output_root)
    record["status"] = "expired_unactivated_review_package_deleted"
    record["deleted"] = True
    _replace_record(verified.cleanup_record, _json_bytes(record))
    return {
        "cleanup_record": str(verified.cleanup_record.resolve()),
        "cleanup_record_sha256": _digest(verified.cleanup_record),
        "deleted": True, "sequence_2_unused": True,
        "execution_manifest_closed": True,
    }
