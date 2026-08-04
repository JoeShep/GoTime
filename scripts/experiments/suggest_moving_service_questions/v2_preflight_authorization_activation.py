"""Atomic, fail-closed activation for one reviewed v2 preflight authorization."""

from __future__ import annotations

import hashlib
import json
import os
import tomllib
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Mapping

from run_openai_stage_b_v2_pilot import DEFAULT_OUTPUT_ROOT, prepare_frozen_v2_pilot
from run_openai_stage_b_v2_two_gate import frozen_binding_identity, phase_paths
from v2_preflight_authorization_installation import (
    CLOSED_EXECUTION_MANIFEST,
    EXECUTION_MANIFEST,
    PERMANENT_CLOSED_AUTHORIZATION,
    REPOSITORY_ROOT,
    ActivationPrerequisiteError,
    ClosedStateError as InstallationClosedStateError,
    ConflictingStateError as InstallationConflictingStateError,
    PackageIntegrityError,
    ReviewValidationError,
    SourceIntegrityError,
    ValidityWindowError as InstallationValidityWindowError,
    plan_preflight_activation,
    review_paths,
)
from v2_two_gate_authorization import (
    V2TwoGateAuthorizationError,
    VerifiedV2PhaseAuthorization,
    validate_phase_authorization,
)

CAPABILITY = "suggest_moving_service_questions"
PHASE = "preflight"
RUN_SERIES_ID = "moving-service-stage-b-v2-pilot-20260802"
SEQUENCE = 1
FIXTURE_ID = "storage_unknown"
OPERATOR_INTENT = "activate exactly one v2 moving-service preflight authorization"
PREFIX = "001-storage_unknown"
TRANSACTION_STATES = frozenset({
    "prepared", "authorization_installed", "manifest_activated",
    "activation_recorded", "committed", "rollback_required", "rolled_back",
})
FAILPOINTS = frozenset({
    "after_prepared", "after_authorization_installed", "after_manifest_activated",
    "after_activation_recorded", "before_commit",
})


class ActivationError(ValueError):
    """Base bounded activation failure."""


class InputIntegrityError(ActivationError):
    pass


class ActivationReviewError(ActivationError):
    pass


class ActivationValidityError(ActivationError):
    pass


class ActivationClosedStateError(ActivationError):
    pass


class ActivationConflictError(ActivationError):
    pass


class TransactionPreparationError(ActivationError):
    pass


class ActiveAuthorizationWriteError(ActivationError):
    pass


class ManifestTransitionError(ActivationError):
    pass


class ActivationRecordWriteError(ActivationError):
    pass


class TransactionCommitError(ActivationError):
    pass


class RecoveryRequiredError(ActivationError):
    pass


class ActiveAuthorizationValidationError(ActivationError):
    pass


@dataclass(frozen=True)
class ActivationPaths:
    execution_manifest: Path
    closed_manifest: Path
    permanent_authorization: Path
    installed: Path
    installation: Path
    review: Path
    active: Path
    activation: Path
    journal: Path
    closure: Path


@dataclass(frozen=True)
class VerifiedActivePreflight:
    authorization: VerifiedV2PhaseAuthorization
    transaction_id: str
    manifest_digest: str
    activation_digest: str


def activation_paths(
    *, repository_root: Path = REPOSITORY_ROOT, output_root: Path = DEFAULT_OUTPUT_ROOT,
    sequence: int = SEQUENCE,
) -> ActivationPaths:
    repository_root = repository_root.resolve()
    repository_docs = repository_root / "docs/experiments/suggest-moving-service-questions/v2-pilot"
    review = review_paths(output_root, sequence=sequence)
    base = output_root / RUN_SERIES_ID
    prefix = f"{sequence:03d}-{FIXTURE_ID}"
    return ActivationPaths(
        execution_manifest=repository_docs / "execution-manifest.json",
        closed_manifest=repository_docs / "closed-execution-manifest.json",
        permanent_authorization=repository_docs / "openai-execution-authorization.toml",
        installed=review["installed"], installation=review["installation"],
        review=review["activation_review"], active=base / f"{prefix}-preflight-authorization.toml",
        activation=base / f"{prefix}-preflight-activation.json",
        journal=base / f"{prefix}-preflight-activation-transaction.json",
        closure=base / f"{prefix}-preflight-closure.json",
    )


def _digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _digest(path: Path) -> str:
    return _digest_bytes(path.read_bytes())


def _json_bytes(value: Mapping[str, object]) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _stamp(value: datetime) -> str:
    if value.tzinfo is None:
        raise ActivationValidityError("activation time must be timezone-aware")
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _utc(value: object, field: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ActivationValidityError(f"{field} must be whole-second UTC")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as error:
        raise ActivationValidityError(f"{field} is invalid") from error
    if parsed.microsecond:
        raise ActivationValidityError(f"{field} must be whole-second UTC")
    return parsed


def _secure_regular(path: Path, label: str) -> bytes:
    current = Path(path.anchor)
    for component in path.absolute().parts[1:-1]:
        current /= component
        if current.is_symlink():
            raise InputIntegrityError(f"{label} path contains a symlink")
    if not path.is_file() or path.is_symlink():
        raise InputIntegrityError(f"{label} is missing or unsafe")
    descriptor = os.open(path, os.O_RDONLY | (getattr(os, "O_NOFOLLOW", 0)))
    try:
        return os.read(descriptor, path.stat(follow_symlinks=False).st_size + 1)
    finally:
        os.close(descriptor)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _secure_directory(path: Path) -> None:
    path.mkdir(parents=True, mode=0o700, exist_ok=True)
    if path.is_symlink() or path.resolve(strict=True) != path.absolute():
        raise TransactionPreparationError("activation directory is unsafe")
    path.chmod(0o700)


def _exclusive(path: Path, value: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        _fsync_directory(path.parent)
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def _atomic_replace(path: Path, value: bytes, suffix: str) -> None:
    temporary = path.with_name(f".{path.name}.{suffix}.tmp")
    _exclusive(temporary, value)
    os.replace(temporary, path)
    _fsync_directory(path.parent)


def _closed_state(paths: ActivationPaths) -> tuple[bytes, str, str]:
    closed = _secure_regular(paths.closed_manifest, "closed execution manifest")
    current = _secure_regular(paths.execution_manifest, "execution manifest")
    if current != closed:
        raise ActivationClosedStateError("execution manifest is not the exact closed template")
    manifest = json.loads(closed)
    authorization = _secure_regular(paths.permanent_authorization, "permanent authorization")
    authorization_digest = _digest_bytes(authorization)
    if (
        manifest.get("status") != "closed_no_execution_authorized"
        or manifest.get("authorization_digest") != authorization_digest
        or any(manifest.get(field) is not False for field in (
            "credential_access_authorized", "token_preflight_authorized",
            "ai_generation_authorized", "formal_evaluation_authorized",
            "stage_c_authorized", "production_use_authorized",
        ))
    ):
        raise ActivationClosedStateError("permanent closed binding drifted")
    return closed, _digest_bytes(closed), authorization_digest


def _attempt_conflicts(output_root: Path, *, sequence: int = SEQUENCE) -> bool:
    attempts = phase_paths(output_root, sequence)
    return any(attempts[key].exists() for key in (
        "preflight_audit", "preflight_evidence", "preflight_review",
        "preflight_consumption", "preflight_closure",
    ))


def _load_inputs(
    *, paths: ActivationPaths, artifact_sha256: str, installation_record_sha256: str,
    activation_review_sha256: str, output_root: Path, now: datetime,
    sequence: int = SEQUENCE, installation_options: Mapping[str, object] | None = None,
) -> tuple[bytes, dict[str, object], dict[str, object], dict[str, object]]:
    # Reuse the reviewed package validator first; it performs no environment or provider work.
    try:
        plan_preflight_activation(
            artifact_sha256=artifact_sha256,
            installation_record_sha256=installation_record_sha256,
            activation_review_sha256=activation_review_sha256,
            output_root=output_root, now=now, sequence=sequence,
            **dict(installation_options or {}),
        )
    except InstallationValidityWindowError as error:
        raise ActivationValidityError("reviewed authorization is outside its valid window") from error
    except InstallationClosedStateError as error:
        raise ActivationClosedStateError("reviewed activation requires permanent closed state") from error
    except InstallationConflictingStateError as error:
        raise ActivationConflictError("reviewed activation has conflicting local state") from error
    except (ActivationPrerequisiteError, ReviewValidationError) as error:
        raise ActivationReviewError("reviewed activation prerequisites failed") from error
    except (PackageIntegrityError, SourceIntegrityError, OSError) as error:
        raise InputIntegrityError("reviewed activation input integrity failed") from error
    installed = _secure_regular(paths.installed, "installed authorization")
    installation_bytes = _secure_regular(paths.installation, "installation record")
    review_bytes = _secure_regular(paths.review, "activation review")
    if _digest_bytes(installed) != artifact_sha256:
        raise InputIntegrityError("installed authorization digest mismatch")
    if _digest_bytes(installation_bytes) != installation_record_sha256:
        raise InputIntegrityError("installation record digest mismatch")
    if _digest_bytes(review_bytes) != activation_review_sha256:
        raise InputIntegrityError("activation review digest mismatch")
    artifact = tomllib.loads(installed.decode("utf-8"))
    installation = json.loads(installation_bytes)
    review = json.loads(review_bytes)
    if (
        review.get("decision") != "approve"
        or review.get("activation_eligible") is not True
        or review.get("authoritative") is not False
        or review.get("activated") is not False
        or not str(review.get("reviewer", "")).strip()
    ):
        raise ActivationReviewError("activation review is not an eligible approval")
    approved = _utc(artifact["approval"]["approved_at"], "approved_at")
    activated = _utc(artifact["approval"]["activated_at"], "activated_at")
    expires = _utc(artifact["approval"]["expires_at"], "expires_at")
    installed_at = _utc(installation["installed_at"], "installed_at")
    reviewed_at = _utc(review["reviewed_at"], "reviewed_at")
    deadline = _utc(review["activation_deadline"], "activation_deadline")
    current = now.astimezone(timezone.utc)
    if not approved <= activated <= installed_at <= reviewed_at <= current < expires or deadline != expires:
        raise ActivationValidityError("activation lifecycle timestamps are invalid or expired")
    if (expires - activated).total_seconds() > 900:
        raise ActivationValidityError("activation window exceeds 900 seconds")
    if _attempt_conflicts(output_root, sequence=sequence):
        raise ActivationConflictError("preflight sequence is already used")
    return installed, artifact, installation, review


def _active_manifest(
    *, artifact: Mapping[str, object], artifact_digest: str, review_digest: str,
    active_path: Path, transaction_id: str, sequence: int = SEQUENCE,
) -> dict[str, object]:
    binding = frozen_binding_identity(prepare_frozen_v2_pilot())
    approval = artifact["approval"]
    return {
        "capability": CAPABILITY, "status": "active_preflight_authorized",
        "phase": PHASE, "run_series_id": RUN_SERIES_ID, "sequence": sequence,
        "fixture_id": FIXTURE_ID, "provider": binding["provider"],
        "ai_model_identifier": binding["ai_model_identifier"], "sdk_pin": binding["sdk_pin"],
        "frozen_v2_manifest_path": "docs/experiments/suggest-moving-service-questions/v2/manifest.json",
        "frozen_v2_manifest_digest": binding["frozen_v2_manifest_digest"],
        "prompt_digest": binding["prompt_digest"],
        "provider_schema_digest": binding["provider_schema_digest"],
        "pilot_configuration_digest": binding["pilot_configuration_digest"],
        "authorization_path": str(active_path.resolve()),
        "authorization_digest_algorithm": "sha256", "authorization_digest": artifact_digest,
        "activation_review_digest": review_digest,
        "activated_at": approval["activated_at"], "expires_at": approval["expires_at"],
        "transaction_id": transaction_id, "single_use_state": "unused",
        "credential_access_authorized": True, "maximum_credential_reads": 1,
        "maximum_client_constructions": 1, "token_preflight_authorized": True,
        "maximum_token_preflight_requests": 1, "ai_generation_authorized": False,
        "maximum_ai_generation_requests": 0, "automatic_retries": 0,
        "token_preflight_timeout_seconds": 5, "maximum_output_tokens": 500,
        "maximum_total_spend_usd": "0.03", "formal_evaluation_authorized": False,
        "stage_c_authorized": False, "production_use_authorized": False,
        "fastapi_exposure_authorized": False, "frontend_exposure_authorized": False,
        "recurring_execution_authorized": False, "background_execution_authorized": False,
    }


def _journal_record(
    *, transaction_id: str, state: str, artifact_digest: str,
    installation_digest: str, review_digest: str, now: datetime, sequence: int = SEQUENCE,
) -> dict[str, object]:
    return {
        "capability": CAPABILITY, "phase": PHASE, "run_series_id": RUN_SERIES_ID,
        "sequence": sequence, "fixture_id": FIXTURE_ID, "transaction_id": transaction_id,
        "transaction_state": state, "installed_artifact_digest": artifact_digest,
        "installation_record_digest": installation_digest,
        "activation_review_digest": review_digest, "updated_at": _stamp(now),
        "generation_authorized": False, "closure_required": state != "rolled_back",
    }


def _update_journal(path: Path, record: Mapping[str, object], state: str) -> None:
    if state not in TRANSACTION_STATES:
        raise TransactionCommitError("unknown transaction state")
    updated = dict(record)
    updated["transaction_state"] = state
    _atomic_replace(path, _json_bytes(updated), state)


def _fail(failpoint: str | None, expected: str) -> None:
    if failpoint == expected:
        raise RecoveryRequiredError(f"synthetic interruption at {expected}")


def activate_preflight_authorization(
    *, artifact_sha256: str, installation_record_sha256: str,
    activation_review_sha256: str, operator: str, operator_intent: str,
    now: datetime, repository_root: Path = REPOSITORY_ROOT,
    output_root: Path = DEFAULT_OUTPUT_ROOT, failpoint: str | None = None,
    transaction_id_factory: Callable[[], str] = lambda: uuid.uuid4().hex,
    sequence: int = SEQUENCE, installation_options: Mapping[str, object] | None = None,
) -> Mapping[str, object]:
    """Atomically activate synthetic or future reviewed state; never touches credentials."""
    if not operator.strip() or operator_intent != OPERATOR_INTENT:
        raise ActivationReviewError("operator identity or exact intent is invalid")
    if failpoint is not None and failpoint not in FAILPOINTS:
        raise ActivationError("unknown synthetic failpoint")
    paths = activation_paths(repository_root=repository_root, output_root=output_root, sequence=sequence)
    if any(path.exists() for path in (paths.active, paths.activation, paths.journal)):
        raise ActivationConflictError("active authorization, evidence, or journal already exists")
    installed, artifact, installation, review = _load_inputs(
        paths=paths, artifact_sha256=artifact_sha256,
        installation_record_sha256=installation_record_sha256,
        activation_review_sha256=activation_review_sha256,
        output_root=output_root, now=now, sequence=sequence,
        installation_options=installation_options,
    )
    closed_bytes, closed_digest, permanent_digest = _closed_state(paths)
    if installation.get("closed_execution_manifest_digest") != _digest(EXECUTION_MANIFEST):
        # The installation record binds the reviewed real closed template; synthetic roots
        # separately prove byte identity below.
        raise ActivationClosedStateError("installation closed-manifest binding drifted")
    if _digest_bytes(closed_bytes) != installation.get("closed_execution_manifest_digest"):
        raise ActivationClosedStateError("synthetic closed manifest differs from reviewed closed state")
    if permanent_digest != installation.get("permanent_closed_authorization_digest"):
        raise ActivationClosedStateError("permanent authorization differs from reviewed closed state")
    _secure_directory(paths.active.parent)
    transaction_id = transaction_id_factory()
    if not transaction_id or len(transaction_id) > 64 or not transaction_id.isalnum():
        raise TransactionPreparationError("transaction identifier is invalid")
    journal = _journal_record(
        transaction_id=transaction_id, state="prepared", artifact_digest=artifact_sha256,
        installation_digest=installation_record_sha256, review_digest=activation_review_sha256,
        now=now, sequence=sequence,
    )
    try:
        _exclusive(paths.journal, _json_bytes(journal))
    except OSError as error:
        raise TransactionPreparationError("transaction journal creation failed") from error
    _fail(failpoint, "after_prepared")
    try:
        _exclusive(paths.active, installed)
        if _digest(paths.active) != artifact_sha256:
            raise ActiveAuthorizationWriteError("active authorization verification failed")
        _update_journal(paths.journal, journal, "authorization_installed")
    except RecoveryRequiredError:
        raise
    except BaseException as error:
        raise RecoveryRequiredError("active authorization installation requires recovery") from error
    _fail(failpoint, "after_authorization_installed")
    manifest = _active_manifest(
        artifact=artifact, artifact_digest=artifact_sha256,
        review_digest=activation_review_sha256, active_path=paths.active,
        transaction_id=transaction_id, sequence=sequence,
    )
    manifest_bytes = _json_bytes(manifest)
    manifest_digest = _digest_bytes(manifest_bytes)
    try:
        _atomic_replace(paths.execution_manifest, manifest_bytes, transaction_id)
        _update_journal(paths.journal, journal, "manifest_activated")
    except BaseException as error:
        raise RecoveryRequiredError("manifest transition requires recovery") from error
    _fail(failpoint, "after_manifest_activated")
    binding = frozen_binding_identity(prepare_frozen_v2_pilot())
    activation_record = {
        "capability": CAPABILITY, "phase": PHASE, "run_series_id": RUN_SERIES_ID,
        "sequence": sequence, "fixture_id": FIXTURE_ID,
        "installed_artifact_digest": artifact_sha256,
        "installation_record_digest": installation_record_sha256,
        "activation_review_digest": activation_review_sha256,
        "active_authorization_path": str(paths.active.resolve()),
        "active_authorization_digest": artifact_sha256,
        "prior_closed_manifest_digest": closed_digest,
        "active_execution_manifest_digest": manifest_digest,
        "candidate_digest": installation["candidate_digest"],
        "umbrella_candidate_digest": installation["umbrella_candidate_digest"],
        "frozen_v2_manifest_digest": binding["frozen_v2_manifest_digest"],
        "prompt_digest": binding["prompt_digest"],
        "provider_schema_digest": binding["provider_schema_digest"],
        "pilot_configuration_digest": binding["pilot_configuration_digest"],
        "provider": binding["provider"], "ai_model_identifier": binding["ai_model_identifier"],
        "sdk_pin": binding["sdk_pin"], "operator": operator,
        "operator_intent_confirmed": True, "activation_timestamp": _stamp(now),
        "expires_at": artifact["approval"]["expires_at"],
        "transaction_id": transaction_id, "transaction_state": "committed",
        "authoritative": True, "phase_authorized": PHASE,
        "generation_authorized": False, "closure_required": True,
    }
    try:
        _exclusive(paths.activation, _json_bytes(activation_record))
        _update_journal(paths.journal, journal, "activation_recorded")
    except BaseException as error:
        raise RecoveryRequiredError("activation evidence write requires recovery") from error
    _fail(failpoint, "after_activation_recorded")
    _fail(failpoint, "before_commit")
    try:
        _update_journal(paths.journal, journal, "committed")
    except BaseException as error:
        raise RecoveryRequiredError("transaction commit requires recovery") from error
    return {
        "active_authorization": str(paths.active.resolve()),
        "active_authorization_sha256": artifact_sha256,
        "execution_manifest_sha256": manifest_digest,
        "activation_record": str(paths.activation.resolve()),
        "activation_record_sha256": _digest(paths.activation),
        "transaction_id": transaction_id, "transaction_state": "committed",
        "phase": PHASE, "generation_authorized": False,
    }


def load_active_preflight_authorization(
    *, repository_root: Path = REPOSITORY_ROOT, output_root: Path = DEFAULT_OUTPUT_ROOT,
    now: datetime, expected_sequence: int = SEQUENCE,
) -> VerifiedActivePreflight:
    """Require the complete dual-bound, committed activation state."""
    paths = activation_paths(repository_root=repository_root, output_root=output_root, sequence=expected_sequence)
    try:
        authorization_bytes = _secure_regular(paths.active, "active authorization")
        manifest_bytes = _secure_regular(paths.execution_manifest, "execution manifest")
        activation_bytes = _secure_regular(paths.activation, "activation evidence")
        journal_bytes = _secure_regular(paths.journal, "activation journal")
        artifact = tomllib.loads(authorization_bytes.decode("utf-8"))
        manifest = json.loads(manifest_bytes)
        activation = json.loads(activation_bytes)
        journal = json.loads(journal_bytes)
    except (OSError, ValueError, json.JSONDecodeError, tomllib.TOMLDecodeError) as error:
        raise ActiveAuthorizationValidationError("complete active state is missing or malformed") from error
    authorization_digest = _digest_bytes(authorization_bytes)
    manifest_digest = _digest_bytes(manifest_bytes)
    activation_digest = _digest_bytes(activation_bytes)
    if journal.get("transaction_state") != "committed":
        raise ActiveAuthorizationValidationError("activation transaction is not committed")
    if (
        manifest.get("status") != "active_preflight_authorized"
        or manifest.get("phase") != PHASE
        or manifest.get("sequence") != expected_sequence
        or manifest.get("authorization_path") != str(paths.active.resolve())
        or manifest.get("authorization_digest") != authorization_digest
        or manifest.get("transaction_id") != journal.get("transaction_id")
        or manifest.get("single_use_state") != "unused"
        or manifest.get("token_preflight_authorized") is not True
        or manifest.get("ai_generation_authorized") is not False
        or manifest.get("maximum_token_preflight_requests") != 1
        or manifest.get("maximum_ai_generation_requests") != 0
        or manifest.get("formal_evaluation_authorized") is not False
        or manifest.get("stage_c_authorized") is not False
        or manifest.get("production_use_authorized") is not False
    ):
        raise ActiveAuthorizationValidationError("active manifest is not exact preflight-only authority")
    if (
        activation.get("transaction_state") != "committed"
        or activation.get("transaction_id") != journal.get("transaction_id")
        or activation.get("active_authorization_digest") != authorization_digest
        or activation.get("active_execution_manifest_digest") != manifest_digest
        or activation.get("activation_review_digest") != manifest.get("activation_review_digest")
        or activation.get("generation_authorized") is not False
        or activation.get("authoritative") is not True
    ):
        raise ActiveAuthorizationValidationError("activation evidence binding drifted")
    prepared = prepare_frozen_v2_pilot()
    try:
        verified = validate_phase_authorization(
            artifact, digest=authorization_digest, phase="preflight", now=now,
            expected_bindings=frozen_binding_identity(prepared),
            expected_sequence=expected_sequence,
        )
    except V2TwoGateAuthorizationError as error:
        raise ActiveAuthorizationValidationError("active authorization is invalid or expired") from error
    if manifest.get("frozen_v2_manifest_digest") != frozen_binding_identity(prepared)["frozen_v2_manifest_digest"]:
        raise ActiveAuthorizationValidationError("frozen v2 binding drifted")
    return VerifiedActivePreflight(verified, str(journal["transaction_id"]), manifest_digest, activation_digest)


def recover_preflight_activation(
    *, reason: str, now: datetime, repository_root: Path = REPOSITORY_ROOT,
    output_root: Path = DEFAULT_OUTPUT_ROOT, sequence: int = SEQUENCE,
) -> Mapping[str, object]:
    """Idempotently restore exact closed bytes after any activation transaction state."""
    if reason not in {"success", "activation_recovery", "operator_cancellation", "expiration", "bounded_failure"}:
        raise ActivationError("closure reason is invalid")
    paths = activation_paths(repository_root=repository_root, output_root=output_root, sequence=sequence)
    if paths.closure.exists():
        record = json.loads(_secure_regular(paths.closure, "closure evidence"))
        if record.get("authorization_closed") is not True:
            raise RecoveryRequiredError("existing closure evidence is invalid")
        return record
    closed_bytes = _secure_regular(paths.closed_manifest, "closed execution manifest")
    closed_manifest = json.loads(closed_bytes)
    permanent_digest = _digest(paths.permanent_authorization)
    if closed_manifest.get("authorization_digest") != permanent_digest:
        raise RecoveryRequiredError("permanent closed authorization drifted")
    prior_state = "absent"
    transaction_id = "none"
    journal: dict[str, object] | None = None
    if paths.journal.exists():
        journal = json.loads(_secure_regular(paths.journal, "activation journal"))
        prior_state = str(journal.get("transaction_state"))
        transaction_id = str(journal.get("transaction_id"))
        if prior_state not in TRANSACTION_STATES:
            raise RecoveryRequiredError("transaction journal state is invalid")
        if prior_state != "rolled_back":
            _update_journal(paths.journal, journal, "rollback_required")
    _atomic_replace(paths.execution_manifest, closed_bytes, "restore-closed")
    if _digest(paths.execution_manifest) != _digest_bytes(closed_bytes):
        raise RecoveryRequiredError("closed manifest restoration failed")
    paths.active.unlink(missing_ok=True)
    for temporary in paths.execution_manifest.parent.glob(f".{paths.execution_manifest.name}.*.tmp"):
        temporary.unlink(missing_ok=True)
    for temporary in paths.active.parent.glob(".*.tmp"):
        temporary.unlink(missing_ok=True)
    _fsync_directory(paths.execution_manifest.parent)
    _fsync_directory(paths.active.parent)
    if journal is not None:
        _update_journal(paths.journal, journal, "rolled_back")
    closure = {
        "capability": CAPABILITY, "phase": PHASE, "run_series_id": RUN_SERIES_ID,
        "sequence": sequence, "fixture_id": FIXTURE_ID, "closure_reason": reason,
        "closed_at": _stamp(now), "transaction_id": transaction_id,
        "prior_transaction_state": prior_state, "transaction_state": "rolled_back",
        "closed_execution_manifest_digest": _digest_bytes(closed_bytes),
        "permanent_closed_authorization_digest": permanent_digest,
        "active_authorization_removed": not paths.active.exists(),
        "authorization_closed": True, "credential_access_authorized": False,
        "token_preflight_authorized": False, "ai_generation_authorized": False,
        "formal_evaluation_authorized": False, "stage_c_authorized": False,
        "production_use_authorized": False,
    }
    _exclusive(paths.closure, _json_bytes(closure))
    return closure
