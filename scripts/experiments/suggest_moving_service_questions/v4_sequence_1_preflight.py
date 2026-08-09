"""Fixed frozen-v4 sequence-1 preflight lifecycle and evidence review."""

from __future__ import annotations

import hashlib
import json
import os
import tomllib
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Mapping

from openai_client_factory import CONVENTIONAL_OPENAI_ENVIRONMENT_NAMES
from openai_transport import OpenAIPreflightResult
from openai_transport_v4 import make_v4_openai_transport
from run_openai_stage_b_v4_pilot import (
    FROZEN_V4_MANIFEST_DIGEST,
    canonical_attempt_digest,
    deterministic_request_digest,
    prepare_frozen_v4_pilot,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
RUN_SERIES = "moving-service-stage-b-v4-pilot-20260808"
SEQUENCE = 1
FIXTURE = "storage_unknown"
PREFIX = "001-storage_unknown"
OPERATOR_INTENT = "AUTHORIZE_ONE_STORAGE_UNKNOWN_V4_PREFLIGHT_ONLY"
REQUEST_DIGEST = "f5a8c7e06d2ad9e133a5b0b92c322f09ed67205feb25314c5114fa1849fcdd0a"
CANONICAL_DIGEST = "7a3c0f7ace4ee4289f4149224fc001b215e71d4cc168edea604516fd133f450d"
PROVIDER_FINGERPRINT = "15caaaaa6a3b43860c426c7555be7f4c7a6bf50d658c92c3c8564c1d43cb5656"
CANDIDATE_DIGEST = "dd312d150c39c756d23007699bf8cb5e6e00d885c4794c53ddaf98ead26d5ebc"
MANIFEST_DIGEST = "0db400f55075b87a0c1fe12ec3dd2c682c48c25c70b1f26b0b6c3664713762ec"
CLOSED_DIGEST = "18a22d62a3e368f5a021649be56a211af959fed7b0305eab61d063022b1387fa"
RENDERED_TMP = Path("/tmp/gotime-v4-sequence-1-preflight-authorization.toml")
PACKAGE = REPOSITORY_ROOT / "docs/experiments/suggest-moving-service-questions/v4-pilot/authorization-review/phase-candidates/sequence-1"
CANDIDATE = PACKAGE / "inactive-sequence-1-v4-preflight-authorization-candidate.toml"
MANIFEST = PACKAGE / "sequence-1-v4-preflight-candidate-manifest.json"
DEFAULT_OUTPUT_ROOT = REPOSITORY_ROOT / ".local/evaluations/suggest-moving-service-questions"


class V4PreflightError(ValueError):
    pass


@dataclass(frozen=True)
class Paths:
    rendered: Path
    installation: Path
    activation_review: Path
    active: Path
    activation: Path
    transaction: Path
    audit: Path
    evidence: Path
    evidence_review: Path
    consumption: Path
    closure: Path
    cleanup: Path
    execution: Path
    closed: Path


@dataclass(frozen=True)
class VerifiedV4PreflightAttempt:
    prepared: object
    deterministic_request_digest: str
    canonical_attempt_digest: str
    provider_fingerprint: str


def paths(output_root: Path = DEFAULT_OUTPUT_ROOT,
          repository_root: Path = REPOSITORY_ROOT) -> Paths:
    base = output_root / RUN_SERIES
    review = base / "authorization-review"
    docs = repository_root / "docs/experiments/suggest-moving-service-questions/v2-pilot"
    return Paths(
        review / f"{PREFIX}-preflight-rendered.toml",
        review / f"{PREFIX}-preflight-installation.json",
        review / f"{PREFIX}-preflight-activation-review.json",
        base / f"{PREFIX}-preflight-authorization.toml",
        base / f"{PREFIX}-preflight-activation.json",
        base / f"{PREFIX}-preflight-activation-transaction.json",
        base / f"{PREFIX}-preflight.json",
        base / f"{PREFIX}-preflight-evidence.json",
        base / f"{PREFIX}-preflight-review.json",
        base / f"{PREFIX}-preflight-evidence-consumption.json",
        base / f"{PREFIX}-preflight-closure.json",
        base / f"{PREFIX}-expired-review-package-cleanup.json",
        docs / "execution-manifest.json",
        docs / "closed-execution-manifest.json",
    )


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stamp(value: datetime) -> str:
    if value.tzinfo is None:
        raise V4PreflightError("clock must be timezone-aware")
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def utc(value: str) -> datetime:
    if not value.endswith("Z") or "." in value:
        raise V4PreflightError("timestamp must be whole-second UTC Z")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise V4PreflightError("timestamp is invalid") from error
    if result.utcoffset() != timedelta(0):
        raise V4PreflightError("timestamp must be UTC")
    return result


def exclusive(path: Path, data: bytes) -> str:
    path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    if path.parent != Path("/tmp"):
        path.parent.chmod(0o700)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, value: Mapping[str, object]) -> str:
    return exclusive(path, (json.dumps(value, indent=2, sort_keys=True) + "\n").encode())


def atomic(path: Path, data: bytes) -> None:
    temporary = path.with_name(f".{path.name}.v4-preflight.tmp")
    temporary.write_bytes(data); os.chmod(temporary, 0o600); os.replace(temporary, path)


def active_manifest_bytes(authorization_digest: str) -> bytes:
    manifest = {
        "status": "active_v4_preflight_only", "capability": "suggest_moving_service_questions",
        "run_series_id": RUN_SERIES, "sequence": SEQUENCE, "fixture_id": FIXTURE,
        "authorization_digest": authorization_digest, "credential_access_authorized": True,
        "token_preflight_authorized": True, "ai_generation_authorized": False,
        "formal_evaluation_authorized": False, "stage_c_authorized": False,
        "production_use_authorized": False, "automatic_retries": 0,
    }
    return (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()


def verify_static(*, repository_root: Path = REPOSITORY_ROOT) -> Mapping[str, object]:
    if digest(CANDIDATE) != CANDIDATE_DIGEST or digest(MANIFEST) != MANIFEST_DIGEST:
        raise V4PreflightError("v4 preflight candidate or manifest drifted")
    candidate = tomllib.loads(CANDIDATE.read_text())
    manifest = json.loads(MANIFEST.read_text())
    verified = verify_preflight_attempt()
    actual = {"request": verified.deterministic_request_digest,
              "canonical": verified.canonical_attempt_digest,
              "fingerprint": verified.provider_fingerprint}
    if actual != {"request": REQUEST_DIGEST, "canonical": CANONICAL_DIGEST, "fingerprint": PROVIDER_FINGERPRINT}:
        raise V4PreflightError("exact frozen-v4 request binding drifted")
    expected_manifest = {
        "candidate_digest": CANDIDATE_DIGEST,
        "frozen_v4_manifest_digest": FROZEN_V4_MANIFEST_DIGEST,
        "prompt_digest": "78b77f31e8cdc68528c08c106fec947123838813d9bdd82978c32a3b011ffb26",
        "provider_schema_digest": "4119a12b673b693c958aa623ff8d9377e3d27f5fd1ca6655671c65716363269d",
        "request_identity_artifact_digest": "b5125e2075779306f0a4374676d442fa3016702bdb5143bc8e3a6b7173d9dd35",
        "deterministic_request_digest": REQUEST_DIGEST,
        "canonical_attempt_digest": CANONICAL_DIGEST,
        "provider_fingerprint": PROVIDER_FINGERPRINT,
    }
    if any(manifest.get(key) != value for key, value in expected_manifest.items()):
        raise V4PreflightError("candidate manifest binding drifted")
    binding = candidate["bindings"]
    if (binding.get("run_series_id") != RUN_SERIES or binding.get("sequence") != 1
            or binding.get("audit_prefix") != PREFIX
            or binding.get("frozen_v4_manifest_digest") != FROZEN_V4_MANIFEST_DIGEST
            or binding.get("request_identity_artifact_digest") != expected_manifest["request_identity_artifact_digest"]
            or binding.get("deterministic_request_digest") != REQUEST_DIGEST
            or binding.get("canonical_attempt_digest") != CANONICAL_DIGEST
            or binding.get("provider_fingerprint") != PROVIDER_FINGERPRINT):
        raise V4PreflightError("v4 preflight identity drifted")
    scope = candidate["scope"]
    expected_scope = {
        "maximum_credential_lookups": 1, "maximum_client_constructions": 1,
        "maximum_token_preflight_requests": 1, "maximum_ai_generation_requests": 0,
        "automatic_retries": 0, "preflight_timeout_seconds": 5,
        "maximum_output_tokens": 500, "maximum_total_spend_usd": "0.03",
        "formal_evaluation_authorized": False, "stage_c_authorized": False,
        "production_use_authorized": False,
        "fastapi_exposure_authorized": False, "frontend_exposure_authorized": False,
        "recurring_execution_authorized": False, "background_execution_authorized": False,
    }
    if any(scope.get(key) != value for key, value in expected_scope.items()):
        raise V4PreflightError("v4 preflight scope drifted")
    closed = repository_root / "docs/experiments/suggest-moving-service-questions/v2-pilot/closed-execution-manifest.json"
    execution = closed.with_name("execution-manifest.json")
    if digest(closed) != CLOSED_DIGEST or execution.read_bytes() != closed.read_bytes():
        raise V4PreflightError("repository authority is not permanently closed")
    return {"candidate_digest": CANDIDATE_DIGEST, "manifest_digest": MANIFEST_DIGEST, **actual}


def verify_preflight_attempt() -> VerifiedV4PreflightAttempt:
    """Construct and verify the one immutable request before credential access."""
    prepared = prepare_frozen_v4_pilot()
    transport = make_v4_openai_transport(type("CredentialFreeVerifier", (), {"max_retries": 0})(), prepared)
    request_digest = deterministic_request_digest(prepared)
    attempt_digest = canonical_attempt_digest(prepared)
    fingerprint = transport.request_fingerprint(prepared.provider_request)
    if (request_digest, attempt_digest, fingerprint) != (
            REQUEST_DIGEST, CANONICAL_DIGEST, PROVIDER_FINGERPRINT):
        raise V4PreflightError("exact frozen-v4 preflight attempt drifted")
    return VerifiedV4PreflightAttempt(prepared, request_digest, attempt_digest, fingerprint)


def render(*, approver: str, approved_at: str, activated_at: str, expires_at: str,
           reason: str, now: datetime, output: Path = RENDERED_TMP) -> Mapping[str, object]:
    verify_static()
    if output != RENDERED_TMP or output.exists() or not approver.strip() or not reason.strip():
        raise V4PreflightError("render destination or human values are invalid")
    approved, activated, expires = map(utc, (approved_at, activated_at, expires_at))
    if not approved <= activated <= now < expires or (expires - activated).total_seconds() > 900:
        raise V4PreflightError("authorization window is invalid")
    candidate = tomllib.loads(CANDIDATE.read_text())
    artifact = {
        "metadata": {"capability": "suggest_moving_service_questions", "authorization_version": "moving-service-openai-v4-preflight-sequence-1-v1", "status": "approved_v4_preflight", "phase": "preflight", "active_repository_authority": True},
        "bindings": candidate["bindings"], "scope": candidate["scope"],
        "authorization": {"credential_access_authorized": True, "token_preflight_authorized": True, "ai_generation_authorized": False},
        "approval": {"approver": approver, "approved_at": approved_at, "activated_at": activated_at, "expires_at": expires_at, "maximum_duration_seconds": 900, "authorization_reason": reason},
    }
    lines = []
    for section, values in artifact.items():
        lines.append(f"[{section}]")
        for key, value in values.items():
            lines.append(f"{key} = {str(value).lower()}" if isinstance(value, bool) else f"{key} = {json.dumps(value)}")
        lines.append("")
    data = ("\n".join(lines).rstrip() + "\n").encode()
    return {"output_path": output, "sha256": exclusive(output, data)}


def validate_artifact(path: Path, *, now: datetime) -> Mapping[str, object]:
    artifact = tomllib.loads(path.read_text())
    if artifact.get("bindings") != tomllib.loads(CANDIDATE.read_text())["bindings"]:
        raise V4PreflightError("rendered bindings drifted")
    if artifact.get("authorization") != {"credential_access_authorized": True, "token_preflight_authorized": True, "ai_generation_authorized": False}:
        raise V4PreflightError("rendered authority is not preflight-only")
    approval = artifact.get("approval", {})
    if not utc(str(approval.get("activated_at"))) <= now < utc(str(approval.get("expires_at"))):
        raise V4PreflightError("rendered authorization is not currently valid")
    return artifact


def install(*, source: Path, expected_sha256: str, now: datetime,
            output_root: Path = DEFAULT_OUTPUT_ROOT) -> Mapping[str, object]:
    verify_static(); target = paths(output_root)
    if source != RENDERED_TMP or source.is_symlink() or not source.is_file() or digest(source) != expected_sha256:
        raise V4PreflightError("rendered source differs")
    validate_artifact(source, now=now)
    installed = exclusive(target.rendered, source.read_bytes())
    record = {"run_series_id": RUN_SERIES, "sequence": 1, "fixture_id": FIXTURE, "phase": "preflight_installation", "installed_digest": installed, "candidate_digest": CANDIDATE_DIGEST, "candidate_manifest_digest": MANIFEST_DIGEST, "authoritative": False, "activated": False}
    return {"installed_path": target.rendered, "installed_digest": installed, "installation_record_path": target.installation, "installation_record_digest": write_json(target.installation, record), "authoritative": False}


def activation_review(*, artifact_sha256: str, reviewer: str, decision: str,
                      reviewed_at: str, notes: str, now: datetime,
                      output_root: Path = DEFAULT_OUTPUT_ROOT) -> Mapping[str, object]:
    target = paths(output_root)
    if digest(target.rendered) != artifact_sha256 or decision not in {"approve", "reject", "request_changes"} or not reviewer.strip() or len(notes) > 500:
        raise V4PreflightError("activation review is invalid")
    reviewed = utc(reviewed_at)
    artifact = validate_artifact(target.rendered, now=now)
    if reviewed > now or reviewed < utc(artifact["approval"]["activated_at"]):
        raise V4PreflightError("activation review timestamp is invalid")
    record = {"run_series_id": RUN_SERIES, "sequence": 1, "fixture_id": FIXTURE, "phase": "preflight_activation_review", "installed_artifact_digest": artifact_sha256, "installation_record_digest": digest(target.installation), "reviewer": reviewer, "decision": decision, "reviewed_at": reviewed_at, "bounded_notes": notes, "activation_eligible": decision == "approve", "authoritative": False, "activated": False}
    return {"review_path": target.activation_review, "review_sha256": write_json(target.activation_review, record), "decision": decision, "activation_eligible": decision == "approve"}


def plan(*, artifact_sha256: str, installation_sha256: str, review_sha256: str,
         now: datetime, output_root: Path = DEFAULT_OUTPUT_ROOT) -> Mapping[str, object]:
    target = paths(output_root); validate_artifact(target.rendered, now=now)
    if (digest(target.rendered), digest(target.installation), digest(target.activation_review)) != (artifact_sha256, installation_sha256, review_sha256):
        raise V4PreflightError("activation plan digest mismatch")
    if json.loads(target.activation_review.read_text()).get("activation_eligible") is not True:
        raise V4PreflightError("activation review is not approved")
    return {"future_active": target.active, "future_activation": target.activation, "future_transaction": target.transaction, "future_closure": target.closure, "writes_performed": False}


def activate(*, artifact_sha256: str, installation_sha256: str, review_sha256: str,
             operator: str, operator_intent: str, now: datetime,
             output_root: Path = DEFAULT_OUTPUT_ROOT,
             repository_root: Path = REPOSITORY_ROOT,
             failpoint: str | None = None) -> Mapping[str, object]:
    verify_static(repository_root=repository_root)
    target = paths(output_root, repository_root)
    plan(artifact_sha256=artifact_sha256, installation_sha256=installation_sha256,
         review_sha256=review_sha256, now=now, output_root=output_root)
    if operator_intent != OPERATOR_INTENT or not operator.strip() or any(p.exists() for p in (target.active, target.activation, target.transaction, target.audit, target.closure)):
        raise V4PreflightError("activation prerequisites differ")
    transaction_id = uuid.uuid4().hex
    journal = {"transaction_id": transaction_id, "state": "prepared", "activation_state": "pending", "run_series_id": RUN_SERIES, "sequence": 1, "fixture_id": FIXTURE, "phase": "preflight", "artifact_digest": artifact_sha256, "activation_review_digest": review_sha256, "closed_manifest_digest": CLOSED_DIGEST, "prepared_at": stamp(now)}
    write_json(target.transaction, journal)
    try:
        if failpoint == "prepared": raise OSError("synthetic interruption")
        exclusive(target.active, target.rendered.read_bytes())
        atomic(target.execution, active_manifest_bytes(artifact_sha256))
        if failpoint == "manifest": raise OSError("synthetic interruption")
        activation_record = {"transaction_id": transaction_id, "run_series_id": RUN_SERIES, "sequence": 1, "fixture_id": FIXTURE, "phase": "preflight", "authorization_digest": artifact_sha256, "activation_review_digest": review_sha256, "candidate_digest": CANDIDATE_DIGEST, "candidate_manifest_digest": MANIFEST_DIGEST, "active_manifest_digest": digest(target.execution), "activated_at": stamp(now), "operator": operator, "operator_intent": operator_intent, "activation_state": "committed", "generation_authorized": False}
        activation_digest = write_json(target.activation, activation_record)
        journal["state"] = "committed"; journal["activation_state"] = "committed"
        journal["activation_record_digest"] = activation_digest; journal["committed_at"] = stamp(now)
        atomic(target.transaction, (json.dumps(journal, indent=2, sort_keys=True) + "\n").encode())
        return {"active_authorization": target.active, "active_authorization_digest": artifact_sha256, "active_manifest_digest": digest(target.execution), "activation_record_digest": activation_digest, "transaction_id": transaction_id, "transaction_state": "committed"}
    except BaseException:
        close(reason="activation_recovery", now=now, output_root=output_root, repository_root=repository_root)
        raise


def verify_active(*, now: datetime, output_root: Path = DEFAULT_OUTPUT_ROOT,
                  repository_root: Path = REPOSITORY_ROOT, minimum_seconds: int = 0) -> Mapping[str, object]:
    target = paths(output_root, repository_root)
    artifact = validate_artifact(target.active, now=now)
    manifest = json.loads(target.execution.read_text()); activation_record = json.loads(target.activation.read_text()); journal = json.loads(target.transaction.read_text())
    active_digest = digest(target.active)
    if (manifest.get("status") != "active_v4_preflight_only" or manifest.get("authorization_digest") != active_digest
            or activation_record.get("authorization_digest") != active_digest or journal.get("state") != "committed"
            or target.audit.exists() or target.evidence.exists() or artifact["authorization"]["ai_generation_authorized"] is not False):
        raise V4PreflightError("active v4 preflight state differs")
    remaining = int((utc(artifact["approval"]["expires_at"]) - now).total_seconds())
    if remaining < minimum_seconds:
        raise V4PreflightError("insufficient authorization time remains")
    return {"sequence": 1, "phase": "preflight", "transaction_state": "committed", "generation_authorized": False, "seconds_remaining": remaining}


def close(*, reason: str, now: datetime, output_root: Path = DEFAULT_OUTPUT_ROOT,
          repository_root: Path = REPOSITORY_ROOT) -> Mapping[str, object]:
    target = paths(output_root, repository_root)
    authorization_digest = digest(target.active) if target.active.exists() else None
    if authorization_digest is None and target.activation.exists():
        authorization_digest = json.loads(target.activation.read_text()).get("authorization_digest")
    if target.closed.exists(): atomic(target.execution, target.closed.read_bytes())
    target.active.unlink(missing_ok=True)
    if target.transaction.exists():
        journal = json.loads(target.transaction.read_text())
        if journal.get("state") != "rolled_back":
            journal["state"] = "rolled_back"; journal["closed_at"] = stamp(now)
            atomic(target.transaction, (json.dumps(journal, indent=2, sort_keys=True) + "\n").encode())
    if not target.closure.exists():
        activation = json.loads(target.activation.read_text()) if target.activation.exists() else {}
        transaction = json.loads(target.transaction.read_text()) if target.transaction.exists() else {}
        write_json(target.closure, {
            "run_series_id": RUN_SERIES, "sequence": 1, "fixture_id": FIXTURE,
            "phase": "preflight", "reason": reason, "closed_at": stamp(now),
            "authorization_digest": authorization_digest,
            "activation_review_digest": activation.get("activation_review_digest"),
            "activation_record_digest": digest(target.activation) if target.activation.exists() else None,
            "transaction_id": transaction.get("transaction_id") or activation.get("transaction_id"),
            "transaction_journal_digest": digest(target.transaction) if target.transaction.exists() else None,
            "audit_sha256": digest(target.audit) if target.audit.exists() else None,
            "consumption_record_sha256": digest(target.consumption) if target.consumption.exists() else None,
            "closed_manifest_digest": CLOSED_DIGEST,
            "authorization_consumed": target.consumption.exists(), "authorization_reusable": False,
            "authorization_closed": True, "active_authorization_absent": not target.active.exists(),
            "permanent_closed_state_verified": target.execution.read_bytes() == target.closed.read_bytes(),
            "credential_access_authorized": False, "token_preflight_authorized": False,
            "ai_generation_authorized": False,
        })
    return {"closure_path": target.closure, "closure_digest": digest(target.closure), "transaction_state": "rolled_back", "authorization_closed": True}


def execute_preflight(*, environment: Mapping[str, str], now: datetime,
                      client_builder, transport_factory=make_v4_openai_transport,
                      output_root: Path = DEFAULT_OUTPUT_ROOT,
                      repository_root: Path = REPOSITORY_ROOT) -> Mapping[str, object]:
    target = paths(output_root, repository_root)
    active = verify_active(now=now, output_root=output_root, repository_root=repository_root, minimum_seconds=180)
    verified = verify_preflight_attempt()
    prepared = verified.prepared
    if environment.get("GOTIME_MOVING_SERVICE_EVAL_ENABLED") != "1" or environment.get("GOTIME_MOVING_SERVICE_EVAL_OPERATOR_INTENT") != OPERATOR_INTENT:
        raise V4PreflightError("operator controls are absent")
    if any(name in environment for name in CONVENTIONAL_OPENAI_ENVIRONMENT_NAMES):
        raise V4PreflightError("conventional OpenAI environment is prohibited")
    credential = environment.get("GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY")
    if not credential or "\n" in credential or "\r" in credential:
        raise V4PreflightError("evaluation credential is invalid")
    owned = None
    try:
        owned = client_builder(credential)
        transport = transport_factory(owned.client, prepared)
        if transport.request_fingerprint(prepared.provider_request) != verified.provider_fingerprint:
            raise V4PreflightError("provider fingerprint drifted")
        preflight_started = datetime.now(timezone.utc).replace(microsecond=0)
        result: OpenAIPreflightResult = transport.preflight(prepared.provider_request)
        created = datetime.now(timezone.utc).replace(microsecond=0)
        succeeded = result.succeeded
        transaction_id = json.loads(target.transaction.read_text())["transaction_id"]
        audit = {"run_series_id": RUN_SERIES, "sequence": 1, "fixture_id": FIXTURE, "phase": "preflight", "credential_lookup_attempted": True, "credential_lookup_succeeded": True, "client_construction_attempted": True, "client_construction_succeeded": True, "preflight_attempted": True, "preflight_succeeded": succeeded, "token_preflight_attempted": True, "token_preflight_succeeded": succeeded, "preflight_request_count": 1, "generation_attempted": False, "ai_generation_attempted": False, "generation_request_count": 0, "automatic_retries": 0, "preflight_started_at": stamp(preflight_started), "audit_completed_at": stamp(created), "input_tokens": result.input_tokens, "cached_input_tokens": None, "uncached_input_tokens": None, "provider_request_id": None, "conservative_maximum_generation_cost": str(result.conservative_cost) if result.conservative_cost is not None else None, "duration_ms": result.duration_ms, "authorization_digest": digest(target.active), "activation_record_digest": digest(target.activation), "transaction_id": transaction_id, "frozen_v4_manifest_digest": FROZEN_V4_MANIFEST_DIGEST, "deterministic_request_digest": REQUEST_DIGEST, "canonical_attempt_digest": CANONICAL_DIGEST, "provider_fingerprint": PROVIDER_FINGERPRINT}
        audit_digest = write_json(target.audit, audit)
        evidence_digest = None
        if succeeded:
            consumption_digest = write_json(target.consumption, {"run_series_id": RUN_SERIES, "sequence": 1, "fixture_id": FIXTURE, "phase": "preflight", "authorization_digest": digest(target.active), "activation_record_digest": digest(target.activation), "transaction_id": transaction_id, "audit_sha256": audit_digest, "audit_completed_at": stamp(created), "consumed_at": stamp(created), "authorization_consumed": True, "reusable": False})
            closure = close(reason="success", now=created, output_root=output_root, repository_root=repository_root)
            evidence = {**audit, "authorization_consumed": True, "authorization_reusable": False, "closure_verified": True, "permanent_closed_state_verified": True, "installation_record_sha256": digest(target.installation), "activation_review_sha256": digest(target.activation_review), "activation_record_sha256": digest(target.activation), "audit_sha256": audit_digest, "consumption_record_sha256": consumption_digest, "closure_sha256": closure["closure_digest"], "transaction_journal_sha256": digest(target.transaction), "closed_manifest_digest": CLOSED_DIGEST, "provider": "OpenAI", "ai_model_identifier": "gpt-4.1-mini-2025-04-14", "sdk_pin": "openai==2.45.0", "prompt_version": "moving-service-questions-prompt-v4", "schema_version": "moving-service-questions-schema-v4", "request_identity_artifact_digest": "b5125e2075779306f0a4374676d442fa3016702bdb5143bc8e3a6b7173d9dd35", "prompt_digest": "78b77f31e8cdc68528c08c106fec947123838813d9bdd82978c32a3b011ffb26", "provider_schema_digest": "4119a12b673b693c958aa623ff8d9377e3d27f5fd1ca6655671c65716363269d", "provider_preflight_fingerprint": PROVIDER_FINGERPRINT, "maximum_output_tokens": 500, "token_preflight_timeout_seconds": 5, "store": False, "stream": False, "background": False, "truncation": "disabled", "tools": [], "created_at": stamp(created), "review_deadline": stamp(created + timedelta(minutes=15))}
            evidence_digest = write_json(target.evidence, evidence)
        return {**active, **audit, "audit_digest": audit_digest, "evidence_digest": evidence_digest}
    finally:
        if owned is not None: owned.close()
        close(reason="success", now=datetime.now(timezone.utc), output_root=output_root, repository_root=repository_root)


def verify_completed_lifecycle_history(*, evidence: Mapping[str, object],
                                       output_root: Path = DEFAULT_OUTPUT_ROOT,
                                       repository_root: Path = REPOSITORY_ROOT) -> Mapping[str, str]:
    """Verify completed preflight history without constraining later authority."""
    target = paths(output_root, repository_root)
    history_paths = (target.rendered, target.installation, target.activation_review,
                     target.activation, target.transaction, target.audit,
                     target.consumption, target.closure)
    if target.active.exists() or not all(path.is_file() and not path.is_symlink() for path in history_paths):
        raise V4PreflightError("v4 preflight lifecycle history is incomplete")
    if digest(target.closed) != CLOSED_DIGEST:
        raise V4PreflightError("v4 permanent closed manifest drifted")
    try:
        authorization = tomllib.loads(target.rendered.read_text())
        installation = json.loads(target.installation.read_text())
        activation_review_record = json.loads(target.activation_review.read_text())
        activation = json.loads(target.activation.read_text())
        transaction = json.loads(target.transaction.read_text())
        audit = json.loads(target.audit.read_text())
        consumption = json.loads(target.consumption.read_text())
        closure = json.loads(target.closure.read_text())
    except (ValueError, TypeError, tomllib.TOMLDecodeError) as error:
        raise V4PreflightError("v4 preflight lifecycle history is malformed") from error

    digests = {
        "authorization_sha256": digest(target.rendered),
        "installation_record_sha256": digest(target.installation),
        "activation_review_sha256": digest(target.activation_review),
        "activation_record_sha256": digest(target.activation),
        "transaction_journal_sha256": digest(target.transaction),
        "audit_sha256": digest(target.audit),
        "consumption_record_sha256": digest(target.consumption),
        "closure_sha256": digest(target.closure),
    }
    for key, value in digests.items():
        evidence_key = "authorization_digest" if key == "authorization_sha256" else key
        if evidence.get(evidence_key) != value:
            raise V4PreflightError(f"v4 preflight {evidence_key} binding drifted")

    authorization_digest = digests["authorization_sha256"]
    transaction_id = transaction.get("transaction_id")
    common = {"run_series_id": RUN_SERIES, "sequence": SEQUENCE, "fixture_id": FIXTURE}
    candidate = tomllib.loads(CANDIDATE.read_text())
    expected_metadata = {
        "capability": "suggest_moving_service_questions",
        "authorization_version": "moving-service-openai-v4-preflight-sequence-1-v1",
        "status": "approved_v4_preflight", "phase": "preflight",
        "active_repository_authority": True,
    }
    expected_authorization = {
                "credential_access_authorized": True,
                "token_preflight_authorized": True,
                "ai_generation_authorized": False,
    }
    approval = authorization.get("approval", {})
    if (authorization.get("metadata") != expected_metadata
            or authorization.get("bindings") != candidate["bindings"]
            or authorization.get("scope") != candidate["scope"]
            or authorization.get("authorization") != expected_authorization
            or set(authorization) != {"metadata", "bindings", "scope", "authorization", "approval"}
            or set(approval) != {"approver", "approved_at", "activated_at", "expires_at",
                                "maximum_duration_seconds", "authorization_reason"}
            or not str(approval.get("approver", "")).strip()
            or not str(approval.get("authorization_reason", "")).strip()
            or approval.get("maximum_duration_seconds") != 900):
        raise V4PreflightError("v4 preflight authorization history differs")
    if installation != {
            **common, "phase": "preflight_installation", "installed_digest": authorization_digest,
            "candidate_digest": CANDIDATE_DIGEST, "candidate_manifest_digest": MANIFEST_DIGEST,
            "authoritative": False, "activated": False}:
        raise V4PreflightError("v4 preflight installation history differs")
    expected_review_fields = {"run_series_id", "sequence", "fixture_id", "phase",
        "installed_artifact_digest", "installation_record_digest", "reviewer", "decision",
        "reviewed_at", "bounded_notes", "activation_eligible", "authoritative", "activated"}
    if (any(activation_review_record.get(key) != value for key, value in common.items())
            or set(activation_review_record) != expected_review_fields
            or activation_review_record.get("phase") != "preflight_activation_review"
            or activation_review_record.get("installed_artifact_digest") != authorization_digest
            or activation_review_record.get("installation_record_digest") != digests["installation_record_sha256"]
            or activation_review_record.get("decision") != "approve"
            or activation_review_record.get("activation_eligible") is not True
            or activation_review_record.get("authoritative") is not False
            or activation_review_record.get("activated") is not False
            or not str(activation_review_record.get("reviewer", "")).strip()):
        raise V4PreflightError("v4 preflight activation review history differs")
    expected_active_digest = hashlib.sha256(active_manifest_bytes(authorization_digest)).hexdigest()
    expected_activation_fields = {"transaction_id", "run_series_id", "sequence", "fixture_id",
        "phase", "authorization_digest", "activation_review_digest", "candidate_digest",
        "candidate_manifest_digest", "active_manifest_digest", "activated_at", "operator",
        "operator_intent", "activation_state", "generation_authorized"}
    if (any(activation.get(key) != value for key, value in common.items())
            or set(activation) != expected_activation_fields
            or activation.get("phase") != "preflight"
            or activation.get("authorization_digest") != authorization_digest
            or activation.get("activation_review_digest") != digests["activation_review_sha256"]
            or activation.get("candidate_digest") != CANDIDATE_DIGEST
            or activation.get("candidate_manifest_digest") != MANIFEST_DIGEST
            or activation.get("transaction_id") != transaction_id
            or activation.get("active_manifest_digest") != expected_active_digest
            or activation.get("activation_state") != "committed"
            or activation.get("operator_intent") != OPERATOR_INTENT
            or not str(activation.get("operator", "")).strip()
            or activation.get("generation_authorized") is not False):
        raise V4PreflightError("v4 preflight activation history differs")
    expected_transaction_fields = {"transaction_id", "state", "activation_state", "run_series_id",
        "sequence", "fixture_id", "phase", "artifact_digest", "activation_review_digest",
        "closed_manifest_digest", "prepared_at", "activation_record_digest", "committed_at", "closed_at"}
    if (set(transaction) != expected_transaction_fields
            or transaction.get("run_series_id") != RUN_SERIES
            or transaction.get("sequence") != SEQUENCE
            or transaction.get("fixture_id") != FIXTURE
            or transaction.get("phase") != "preflight"
            or transaction.get("artifact_digest") != authorization_digest
            or transaction.get("activation_review_digest") != digests["activation_review_sha256"]
            or transaction.get("activation_record_digest") != digests["activation_record_sha256"]
            or transaction.get("closed_manifest_digest") != CLOSED_DIGEST
            or transaction.get("state") != "rolled_back"
            or transaction.get("activation_state") != "committed"
            or not transaction_id):
        raise V4PreflightError("v4 preflight transaction history differs")

    try:
        approved_at = utc(str(approval["approved_at"])); eligible_at = utc(str(approval["activated_at"]))
        expires_at = utc(str(approval["expires_at"]))
        activation_reviewed_at = utc(str(activation_review_record["reviewed_at"]))
        activated_at = utc(str(activation["activated_at"])); prepared_at = utc(str(transaction["prepared_at"]))
        committed_at = utc(str(transaction["committed_at"])); transaction_closed_at = utc(str(transaction["closed_at"]))
        preflight_started_at = utc(str(audit["preflight_started_at"])); audit_completed_at = utc(str(audit["audit_completed_at"]))
        consumed_at = utc(str(consumption["consumed_at"])); closure_at = utc(str(closure["closed_at"]))
        evidence_created_at = utc(str(evidence["created_at"])); review_deadline = utc(str(evidence["review_deadline"]))
    except (KeyError, TypeError, V4PreflightError) as error:
        raise V4PreflightError("v4 preflight lifecycle timestamp is invalid") from error
    if not (approved_at <= eligible_at <= activation_reviewed_at <= activated_at
            and activated_at == prepared_at == committed_at
            and activated_at <= preflight_started_at <= audit_completed_at
            and audit_completed_at <= consumed_at <= transaction_closed_at <= closure_at <= evidence_created_at
            and evidence_created_at < expires_at
            and expires_at - eligible_at <= timedelta(seconds=900)
            and review_deadline == evidence_created_at + timedelta(minutes=15)):
        raise V4PreflightError("v4 preflight lifecycle timestamp order differs")

    exact_audit = {
        **common, "phase": "preflight",
        "frozen_v4_manifest_digest": FROZEN_V4_MANIFEST_DIGEST,
        "deterministic_request_digest": REQUEST_DIGEST,
        "canonical_attempt_digest": CANONICAL_DIGEST,
        "provider_fingerprint": PROVIDER_FINGERPRINT,
        "authorization_digest": authorization_digest,
        "activation_record_digest": digests["activation_record_sha256"],
        "transaction_id": transaction_id,
        "credential_lookup_attempted": True, "credential_lookup_succeeded": True,
        "client_construction_attempted": True, "client_construction_succeeded": True,
        "token_preflight_attempted": True, "token_preflight_succeeded": True,
        "preflight_attempted": True, "preflight_succeeded": True,
        "preflight_request_count": 1, "generation_attempted": False,
        "ai_generation_attempted": False, "generation_request_count": 0,
        "automatic_retries": 0,
    }
    expected_audit_fields = set(exact_audit) | {"preflight_started_at", "audit_completed_at",
        "input_tokens", "cached_input_tokens", "uncached_input_tokens", "provider_request_id",
        "conservative_maximum_generation_cost", "duration_ms"}
    if (set(audit) != expected_audit_fields
            or any(audit.get(key) != value for key, value in exact_audit.items())
            or audit.get("input_tokens") != evidence.get("input_tokens")
            or audit.get("conservative_maximum_generation_cost") != evidence.get("conservative_maximum_generation_cost")
            or audit.get("duration_ms") is None or audit.get("duration_ms") < 0):
        raise V4PreflightError("v4 preflight audit history differs")

    exact_consumption = {
        **common, "phase": "preflight", "authorization_digest": authorization_digest,
        "activation_record_digest": digests["activation_record_sha256"],
        "transaction_id": transaction_id, "audit_sha256": digests["audit_sha256"],
        "audit_completed_at": audit["audit_completed_at"],
        "authorization_consumed": True, "reusable": False,
    }
    if (set(consumption) != set(exact_consumption) | {"consumed_at"}
            or any(consumption.get(key) != value for key, value in exact_consumption.items())):
        raise V4PreflightError("v4 preflight consumption history differs")

    exact_closure = {
        **common, "phase": "preflight", "reason": "success",
        "authorization_digest": authorization_digest,
        "activation_review_digest": digests["activation_review_sha256"],
        "activation_record_digest": digests["activation_record_sha256"],
        "transaction_id": transaction_id,
        "transaction_journal_digest": digests["transaction_journal_sha256"],
        "audit_sha256": digests["audit_sha256"],
        "consumption_record_sha256": digests["consumption_record_sha256"],
        "closed_manifest_digest": CLOSED_DIGEST,
        "authorization_consumed": True, "authorization_reusable": False,
        "authorization_closed": True, "active_authorization_absent": True,
        "permanent_closed_state_verified": True,
        "credential_access_authorized": False, "token_preflight_authorized": False,
        "ai_generation_authorized": False,
    }
    if (set(closure) != set(exact_closure) | {"closed_at"}
            or any(closure.get(key) != value for key, value in exact_closure.items())):
        raise V4PreflightError("v4 preflight closure history differs")
    evidence_state = {
        "token_preflight_attempted": True, "token_preflight_succeeded": True,
        "preflight_request_count": 1, "ai_generation_attempted": False,
        "generation_request_count": 0, "authorization_consumed": True,
        "authorization_reusable": False, "closure_verified": True,
        "permanent_closed_state_verified": True,
    }
    if any(evidence.get(key) != value for key, value in evidence_state.items()):
        raise V4PreflightError("v4 preflight evidence lifecycle state differs")
    return digests


def verify_lifecycle_history(*, evidence: Mapping[str, object],
                             output_root: Path = DEFAULT_OUTPUT_ROOT,
                             repository_root: Path = REPOSITORY_ROOT) -> Mapping[str, str]:
    """Verify completed history and require the current repository to be closed."""
    target = paths(output_root, repository_root)
    if target.execution.read_bytes() != target.closed.read_bytes():
        raise V4PreflightError("v4 preflight lifecycle is not permanently closed")
    return verify_completed_lifecycle_history(
        evidence=evidence, output_root=output_root, repository_root=repository_root)


def review_evidence(*, evidence_sha256: str, input_tokens: int, conservative_cost: str,
                    reviewer: str, decision: str, reviewed_at: str,
                    token_count_plausible: bool, cost_within_limit: bool,
                    frozen_bindings_confirmed: bool, evidence_history_confirmed: bool,
                    notes: str, now: datetime, output_root: Path = DEFAULT_OUTPUT_ROOT,
                    repository_root: Path = REPOSITORY_ROOT) -> Mapping[str, object]:
    target = paths(output_root, repository_root)
    if target.evidence_review.exists() or digest(target.evidence) != evidence_sha256:
        raise V4PreflightError("preflight evidence is absent, changed, or already reviewed")
    evidence = json.loads(target.evidence.read_text())
    required = {"run_series_id": RUN_SERIES, "sequence": 1, "fixture_id": FIXTURE, "phase": "preflight", "frozen_v4_manifest_digest": FROZEN_V4_MANIFEST_DIGEST, "request_identity_artifact_digest": "b5125e2075779306f0a4374676d442fa3016702bdb5143bc8e3a6b7173d9dd35", "prompt_version": "moving-service-questions-prompt-v4", "schema_version": "moving-service-questions-schema-v4", "prompt_digest": "78b77f31e8cdc68528c08c106fec947123838813d9bdd82978c32a3b011ffb26", "provider_schema_digest": "4119a12b673b693c958aa623ff8d9377e3d27f5fd1ca6655671c65716363269d", "deterministic_request_digest": REQUEST_DIGEST, "canonical_attempt_digest": CANONICAL_DIGEST, "provider_preflight_fingerprint": PROVIDER_FINGERPRINT, "provider": "OpenAI", "ai_model_identifier": "gpt-4.1-mini-2025-04-14", "sdk_pin": "openai==2.45.0", "maximum_output_tokens": 500, "token_preflight_timeout_seconds": 5, "automatic_retries": 0, "preflight_request_count": 1, "generation_attempted": False, "generation_request_count": 0}
    if any(evidence.get(key) != value for key, value in required.items()):
        raise V4PreflightError("preflight evidence binding drifted")
    history = verify_lifecycle_history(
        evidence=evidence, output_root=output_root, repository_root=repository_root)
    try: cost = Decimal(conservative_cost)
    except InvalidOperation as error: raise V4PreflightError("cost is invalid") from error
    review_time = utc(reviewed_at); deadline = utc(evidence["review_deadline"])
    confirmations = all((token_count_plausible, cost_within_limit, frozen_bindings_confirmed, evidence_history_confirmed))
    if (evidence.get("input_tokens") != input_tokens or Decimal(str(evidence.get("conservative_maximum_generation_cost"))) != cost
            or decision not in {"approve", "reject", "request_changes"} or not reviewer.strip() or not notes.strip() or len(notes) > 500
            or review_time > now or review_time < utc(evidence["created_at"])
            or (decision == "approve" and (not confirmations or review_time >= deadline or now >= deadline))
            or target.active.exists() or target.execution.read_bytes() != target.closed.read_bytes()):
        raise V4PreflightError("evidence review is invalid or late")
    record = {"run_series_id": RUN_SERIES, "sequence": 1, "fixture_id": FIXTURE, "phase": "preflight_review", "preflight_evidence_digest": evidence_sha256, **history, "input_tokens": input_tokens, "conservative_maximum_generation_cost": str(cost), "deterministic_request_digest": REQUEST_DIGEST, "canonical_attempt_digest": CANONICAL_DIGEST, "provider_fingerprint": PROVIDER_FINGERPRINT, "frozen_v4_manifest_digest": FROZEN_V4_MANIFEST_DIGEST, "request_identity_artifact_digest": evidence["request_identity_artifact_digest"], "prompt_version": evidence["prompt_version"], "schema_version": evidence["schema_version"], "prompt_digest": evidence["prompt_digest"], "provider_schema_digest": evidence["provider_schema_digest"], "provider": "OpenAI", "ai_model_identifier": "gpt-4.1-mini-2025-04-14", "sdk_pin": "openai==2.45.0", "evidence_created_at": evidence["created_at"], "review_deadline": evidence["review_deadline"], "reviewer": reviewer, "decision": decision, "reviewed_at": reviewed_at, "token_count_plausible": token_count_plausible, "cost_within_limit": cost_within_limit, "frozen_bindings_confirmed": frozen_bindings_confirmed, "evidence_history_confirmed": evidence_history_confirmed, "bounded_notes": notes, "authoritative": False, "generation_authorized": False, "generation_gate_binding_eligible": decision == "approve"}
    return {"review_path": target.evidence_review, "review_digest": write_json(target.evidence_review, record), "decision": decision, "generation_gate_binding_eligible": decision == "approve"}


def generation_binding_dry_run(*, output_root: Path = DEFAULT_OUTPUT_ROOT,
                               repository_root: Path = REPOSITORY_ROOT) -> Mapping[str, object]:
    target = paths(output_root, repository_root)
    evidence = json.loads(target.evidence.read_text()); review = json.loads(target.evidence_review.read_text())
    history = verify_lifecycle_history(
        evidence=evidence, output_root=output_root, repository_root=repository_root)
    exact = {
        "run_series_id": RUN_SERIES, "sequence": 1, "fixture_id": FIXTURE,
        "frozen_v4_manifest_digest": FROZEN_V4_MANIFEST_DIGEST,
        "request_identity_artifact_digest": "b5125e2075779306f0a4374676d442fa3016702bdb5143bc8e3a6b7173d9dd35",
        "deterministic_request_digest": REQUEST_DIGEST,
        "canonical_attempt_digest": CANONICAL_DIGEST,
    }
    evidence_exact = {**exact, "phase": "preflight", "provider_preflight_fingerprint": PROVIDER_FINGERPRINT}
    review_exact = {**exact, "phase": "preflight_review", "provider_fingerprint": PROVIDER_FINGERPRINT}
    if (any(evidence.get(key) != value for key, value in evidence_exact.items())
            or any(review.get(key) != value for key, value in review_exact.items())
            or review.get("decision") != "approve"
            or review.get("preflight_evidence_digest") != digest(target.evidence)
            or review.get("generation_gate_binding_eligible") is not True
            or any(review.get(key) != value for key, value in history.items())
            or utc(review["reviewed_at"]) >= utc(evidence["review_deadline"])):
        raise V4PreflightError("approved v4 evidence cannot resolve generation candidate")
    binding = {"preflight_evidence_digest": digest(target.evidence), "preflight_review_digest": digest(target.evidence_review), "input_tokens": evidence["input_tokens"], "conservative_maximum_generation_cost": evidence["conservative_maximum_generation_cost"], "deterministic_request_digest": REQUEST_DIGEST, "canonical_attempt_digest": CANONICAL_DIGEST, "provider_fingerprint": PROVIDER_FINGERPRINT}
    preview = json.dumps(binding, separators=(",", ":"), sort_keys=True).encode()
    return {**binding, "resolved_binding_preview_digest": hashlib.sha256(preview).hexdigest(), "writes_performed": False, "authoritative": False, "generation_authorized": False}


def cleanup_review_package(*, confirm: bool, operator: str | None, now: datetime,
                           output_root: Path = DEFAULT_OUTPUT_ROOT) -> Mapping[str, object]:
    target = paths(output_root); review_files = (RENDERED_TMP, target.rendered, target.installation, target.activation_review)
    for path in review_files:
        if path.is_symlink() or not path.is_file(): raise V4PreflightError("fixed cleanup file is absent or unsafe")
    artifact = tomllib.loads(target.rendered.read_text())
    if utc(artifact["approval"]["expires_at"]) >= now or any(p.exists() for p in (target.active, target.activation, target.transaction, target.audit, target.evidence, target.closure)):
        raise V4PreflightError("review package is not eligible for cleanup")
    result = {"exact_paths": [str(p) for p in review_files], "expired": True, "authoritative": False, "activated": False, "execution_manifest_closed": target.execution.read_bytes() == target.closed.read_bytes(), "sequence_1_unused": True, "deleted": False}
    if not confirm: return result
    if not operator or not operator.strip(): raise V4PreflightError("cleanup operator is required")
    record = {"run_series_id": RUN_SERIES, "sequence": 1, "fixture_id": FIXTURE, "reason": "expired_unactivated_review_package", "exact_paths": result["exact_paths"], "pre_deletion_digests": {str(p): digest(p) for p in review_files}, "cleanup_timestamp": stamp(now), "operator": operator, "authoritative": False, "activated": False, "deleted": True}
    write_json(target.cleanup, record)
    for path in review_files: path.unlink()
    return {**result, "deleted": True, "cleanup_path": target.cleanup, "cleanup_digest": digest(target.cleanup)}
