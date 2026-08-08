"""Fixed frozen-v3 sequence-1 preflight lifecycle and evidence review."""

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
from openai_transport_v3 import make_v3_openai_transport
from run_openai_stage_b_v3_pilot import (
    FROZEN_V3_MANIFEST_DIGEST,
    canonical_attempt_digest,
    deterministic_request_digest,
    prepare_frozen_v3_pilot,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
RUN_SERIES = "moving-service-stage-b-v3-pilot-20260807"
SEQUENCE = 1
FIXTURE = "storage_unknown"
PREFIX = "001-storage_unknown"
OPERATOR_INTENT = "AUTHORIZE_ONE_STORAGE_UNKNOWN_V3_PREFLIGHT_ONLY"
REQUEST_DIGEST = "952b8003f184de1ff9617103c8c93ab64d87e63cb4e4daee84647b7dd505ed79"
CANONICAL_DIGEST = "d9d8141853b7d034ce30de8c9c2689d9738b0bfd73d812a2150b823111b3bdcf"
PROVIDER_FINGERPRINT = "a5895ad53d54d6d03652152aeadbf8b71a2c672cab86640d1798a3a3680a15e4"
CANDIDATE_DIGEST = "62e341e0519b292c9802f6f2ff734bd3b5a31c4484acdcb7e200d2542898a4f7"
MANIFEST_DIGEST = "ff042074c6aeb6d8bdd1fc2f8c70721b5305bb1f763886cb453c2407a819d828"
CLOSED_DIGEST = "18a22d62a3e368f5a021649be56a211af959fed7b0305eab61d063022b1387fa"
RENDERED_TMP = Path("/tmp/gotime-v3-sequence-1-preflight-authorization.toml")
PACKAGE = REPOSITORY_ROOT / "docs/experiments/suggest-moving-service-questions/v3-pilot/authorization-review/phase-candidates/sequence-1"
CANDIDATE = PACKAGE / "inactive-sequence-1-v3-preflight-authorization-candidate.toml"
MANIFEST = PACKAGE / "sequence-1-v3-preflight-candidate-manifest.json"
DEFAULT_OUTPUT_ROOT = REPOSITORY_ROOT / ".local/evaluations/suggest-moving-service-questions"


class V3PreflightError(ValueError):
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
        raise V3PreflightError("clock must be timezone-aware")
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def utc(value: str) -> datetime:
    if not value.endswith("Z") or "." in value:
        raise V3PreflightError("timestamp must be whole-second UTC Z")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise V3PreflightError("timestamp is invalid") from error
    if result.utcoffset() != timedelta(0):
        raise V3PreflightError("timestamp must be UTC")
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
    temporary = path.with_name(f".{path.name}.v3-preflight.tmp")
    temporary.write_bytes(data); os.chmod(temporary, 0o600); os.replace(temporary, path)


def verify_static(*, repository_root: Path = REPOSITORY_ROOT) -> Mapping[str, object]:
    if digest(CANDIDATE) != CANDIDATE_DIGEST or digest(MANIFEST) != MANIFEST_DIGEST:
        raise V3PreflightError("v3 preflight candidate or manifest drifted")
    candidate = tomllib.loads(CANDIDATE.read_text())
    manifest = json.loads(MANIFEST.read_text())
    prepared = prepare_frozen_v3_pilot()
    transport = make_v3_openai_transport(type("Client", (), {"max_retries": 0})(), prepared)
    actual = {
        "request": deterministic_request_digest(prepared),
        "canonical": canonical_attempt_digest(prepared),
        "fingerprint": transport.request_fingerprint(prepared.provider_request),
    }
    if actual != {"request": REQUEST_DIGEST, "canonical": CANONICAL_DIGEST, "fingerprint": PROVIDER_FINGERPRINT}:
        raise V3PreflightError("exact frozen-v3 request binding drifted")
    if manifest.get("candidate_digest") != CANDIDATE_DIGEST:
        raise V3PreflightError("candidate manifest binding drifted")
    binding = candidate["bindings"]
    if (binding.get("run_series_id") != RUN_SERIES or binding.get("sequence") != 1
            or binding.get("audit_prefix") != PREFIX
            or binding.get("frozen_v3_manifest_digest") != FROZEN_V3_MANIFEST_DIGEST):
        raise V3PreflightError("v3 preflight identity drifted")
    scope = candidate["scope"]
    expected_scope = {
        "maximum_credential_lookups": 1, "maximum_client_constructions": 1,
        "maximum_token_preflight_requests": 1, "maximum_ai_generation_requests": 0,
        "automatic_retries": 0, "preflight_timeout_seconds": 5,
        "maximum_output_tokens": 500, "maximum_total_spend_usd": "0.03",
        "formal_evaluation_authorized": False, "stage_c_authorized": False,
        "production_use_authorized": False,
    }
    if any(scope.get(key) != value for key, value in expected_scope.items()):
        raise V3PreflightError("v3 preflight scope drifted")
    closed = repository_root / "docs/experiments/suggest-moving-service-questions/v2-pilot/closed-execution-manifest.json"
    execution = closed.with_name("execution-manifest.json")
    if digest(closed) != CLOSED_DIGEST or execution.read_bytes() != closed.read_bytes():
        raise V3PreflightError("repository authority is not permanently closed")
    return {"candidate_digest": CANDIDATE_DIGEST, "manifest_digest": MANIFEST_DIGEST, **actual}


def render(*, approver: str, approved_at: str, activated_at: str, expires_at: str,
           reason: str, now: datetime, output: Path = RENDERED_TMP) -> Mapping[str, object]:
    verify_static()
    if output != RENDERED_TMP or output.exists() or not approver.strip() or not reason.strip():
        raise V3PreflightError("render destination or human values are invalid")
    approved, activated, expires = map(utc, (approved_at, activated_at, expires_at))
    if not approved <= activated <= now < expires or (expires - activated).total_seconds() > 900:
        raise V3PreflightError("authorization window is invalid")
    candidate = tomllib.loads(CANDIDATE.read_text())
    artifact = {
        "metadata": {"capability": "suggest_moving_service_questions", "authorization_version": "moving-service-openai-v3-preflight-sequence-1-v1", "status": "approved_v3_preflight", "phase": "preflight", "active_repository_authority": True},
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
        raise V3PreflightError("rendered bindings drifted")
    if artifact.get("authorization") != {"credential_access_authorized": True, "token_preflight_authorized": True, "ai_generation_authorized": False}:
        raise V3PreflightError("rendered authority is not preflight-only")
    approval = artifact.get("approval", {})
    if not utc(str(approval.get("activated_at"))) <= now < utc(str(approval.get("expires_at"))):
        raise V3PreflightError("rendered authorization is not currently valid")
    return artifact


def install(*, source: Path, expected_sha256: str, now: datetime,
            output_root: Path = DEFAULT_OUTPUT_ROOT) -> Mapping[str, object]:
    verify_static(); target = paths(output_root)
    if source != RENDERED_TMP or source.is_symlink() or not source.is_file() or digest(source) != expected_sha256:
        raise V3PreflightError("rendered source differs")
    validate_artifact(source, now=now)
    installed = exclusive(target.rendered, source.read_bytes())
    record = {"run_series_id": RUN_SERIES, "sequence": 1, "fixture_id": FIXTURE, "phase": "preflight_installation", "installed_digest": installed, "candidate_digest": CANDIDATE_DIGEST, "candidate_manifest_digest": MANIFEST_DIGEST, "authoritative": False, "activated": False}
    return {"installed_path": target.rendered, "installed_digest": installed, "installation_record_path": target.installation, "installation_record_digest": write_json(target.installation, record), "authoritative": False}


def activation_review(*, artifact_sha256: str, reviewer: str, decision: str,
                      reviewed_at: str, notes: str, now: datetime,
                      output_root: Path = DEFAULT_OUTPUT_ROOT) -> Mapping[str, object]:
    target = paths(output_root)
    if digest(target.rendered) != artifact_sha256 or decision not in {"approve", "reject", "request_changes"} or not reviewer.strip() or len(notes) > 500:
        raise V3PreflightError("activation review is invalid")
    reviewed = utc(reviewed_at)
    artifact = validate_artifact(target.rendered, now=now)
    if reviewed > now or reviewed < utc(artifact["approval"]["activated_at"]):
        raise V3PreflightError("activation review timestamp is invalid")
    record = {"run_series_id": RUN_SERIES, "sequence": 1, "fixture_id": FIXTURE, "phase": "preflight_activation_review", "installed_artifact_digest": artifact_sha256, "installation_record_digest": digest(target.installation), "reviewer": reviewer, "decision": decision, "reviewed_at": reviewed_at, "bounded_notes": notes, "activation_eligible": decision == "approve", "authoritative": False, "activated": False}
    return {"review_path": target.activation_review, "review_sha256": write_json(target.activation_review, record), "decision": decision, "activation_eligible": decision == "approve"}


def plan(*, artifact_sha256: str, installation_sha256: str, review_sha256: str,
         now: datetime, output_root: Path = DEFAULT_OUTPUT_ROOT) -> Mapping[str, object]:
    target = paths(output_root); validate_artifact(target.rendered, now=now)
    if (digest(target.rendered), digest(target.installation), digest(target.activation_review)) != (artifact_sha256, installation_sha256, review_sha256):
        raise V3PreflightError("activation plan digest mismatch")
    if json.loads(target.activation_review.read_text()).get("activation_eligible") is not True:
        raise V3PreflightError("activation review is not approved")
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
        raise V3PreflightError("activation prerequisites differ")
    transaction_id = uuid.uuid4().hex
    journal = {"transaction_id": transaction_id, "state": "prepared", "run_series_id": RUN_SERIES, "sequence": 1, "phase": "preflight", "artifact_digest": artifact_sha256, "closed_manifest_digest": CLOSED_DIGEST}
    write_json(target.transaction, journal)
    try:
        if failpoint == "prepared": raise OSError("synthetic interruption")
        exclusive(target.active, target.rendered.read_bytes())
        active_manifest = {"status": "active_v3_preflight_only", "capability": "suggest_moving_service_questions", "run_series_id": RUN_SERIES, "sequence": 1, "fixture_id": FIXTURE, "authorization_digest": artifact_sha256, "credential_access_authorized": True, "token_preflight_authorized": True, "ai_generation_authorized": False, "formal_evaluation_authorized": False, "stage_c_authorized": False, "production_use_authorized": False, "automatic_retries": 0}
        atomic(target.execution, (json.dumps(active_manifest, indent=2, sort_keys=True) + "\n").encode())
        if failpoint == "manifest": raise OSError("synthetic interruption")
        activation_record = {"transaction_id": transaction_id, "run_series_id": RUN_SERIES, "sequence": 1, "phase": "preflight", "authorization_digest": artifact_sha256, "active_manifest_digest": digest(target.execution), "activated_at": stamp(now), "operator": operator, "generation_authorized": False}
        activation_digest = write_json(target.activation, activation_record)
        journal["state"] = "committed"; atomic(target.transaction, (json.dumps(journal, indent=2, sort_keys=True) + "\n").encode())
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
    if (manifest.get("status") != "active_v3_preflight_only" or manifest.get("authorization_digest") != active_digest
            or activation_record.get("authorization_digest") != active_digest or journal.get("state") != "committed"
            or target.audit.exists() or target.evidence.exists() or artifact["authorization"]["ai_generation_authorized"] is not False):
        raise V3PreflightError("active v3 preflight state differs")
    remaining = int((utc(artifact["approval"]["expires_at"]) - now).total_seconds())
    if remaining < minimum_seconds:
        raise V3PreflightError("insufficient authorization time remains")
    return {"sequence": 1, "phase": "preflight", "transaction_state": "committed", "generation_authorized": False, "seconds_remaining": remaining}


def close(*, reason: str, now: datetime, output_root: Path = DEFAULT_OUTPUT_ROOT,
          repository_root: Path = REPOSITORY_ROOT) -> Mapping[str, object]:
    target = paths(output_root, repository_root)
    if target.closed.exists(): atomic(target.execution, target.closed.read_bytes())
    target.active.unlink(missing_ok=True)
    if target.transaction.exists():
        journal = json.loads(target.transaction.read_text()); journal["state"] = "rolled_back"; journal["closed_at"] = stamp(now); atomic(target.transaction, (json.dumps(journal, indent=2, sort_keys=True) + "\n").encode())
    if not target.closure.exists():
        write_json(target.closure, {"run_series_id": RUN_SERIES, "sequence": 1, "fixture_id": FIXTURE, "phase": "preflight", "reason": reason, "closed_at": stamp(now), "authorization_closed": True, "credential_access_authorized": False, "token_preflight_authorized": False, "ai_generation_authorized": False})
    return {"closure_path": target.closure, "closure_digest": digest(target.closure), "transaction_state": "rolled_back", "authorization_closed": True}


def execute_preflight(*, environment: Mapping[str, str], now: datetime,
                      client_builder, transport_factory=make_v3_openai_transport,
                      output_root: Path = DEFAULT_OUTPUT_ROOT,
                      repository_root: Path = REPOSITORY_ROOT) -> Mapping[str, object]:
    target = paths(output_root, repository_root)
    active = verify_active(now=now, output_root=output_root, repository_root=repository_root, minimum_seconds=180)
    prepared = prepare_frozen_v3_pilot()
    if deterministic_request_digest(prepared) != REQUEST_DIGEST or canonical_attempt_digest(prepared) != CANONICAL_DIGEST:
        raise V3PreflightError("request drifted before credential lookup")
    if environment.get("GOTIME_MOVING_SERVICE_EVAL_ENABLED") != "1" or environment.get("GOTIME_MOVING_SERVICE_EVAL_OPERATOR_INTENT") != OPERATOR_INTENT:
        raise V3PreflightError("operator controls are absent")
    if any(name in environment for name in CONVENTIONAL_OPENAI_ENVIRONMENT_NAMES):
        raise V3PreflightError("conventional OpenAI environment is prohibited")
    credential = environment.get("GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY")
    if not credential or "\n" in credential or "\r" in credential:
        raise V3PreflightError("evaluation credential is invalid")
    owned = None
    try:
        owned = client_builder(credential)
        transport = transport_factory(owned.client, prepared)
        if transport.request_fingerprint(prepared.provider_request) != PROVIDER_FINGERPRINT:
            raise V3PreflightError("provider fingerprint drifted")
        result: OpenAIPreflightResult = transport.preflight(prepared.provider_request)
        created = datetime.now(timezone.utc).replace(microsecond=0)
        succeeded = result.succeeded
        audit = {"run_series_id": RUN_SERIES, "sequence": 1, "fixture_id": FIXTURE, "phase": "preflight", "credential_lookup_attempted": True, "credential_lookup_succeeded": True, "client_construction_attempted": True, "client_construction_succeeded": True, "preflight_attempted": True, "preflight_succeeded": succeeded, "preflight_request_count": 1, "generation_attempted": False, "generation_request_count": 0, "automatic_retries": 0, "input_tokens": result.input_tokens, "conservative_maximum_generation_cost": str(result.conservative_cost) if result.conservative_cost is not None else None, "duration_ms": result.duration_ms, "authorization_consumed": True}
        audit_digest = write_json(target.audit, audit)
        evidence_digest = None
        if succeeded:
            evidence = {**audit, "provider": "OpenAI", "ai_model_identifier": "gpt-4.1-mini-2025-04-14", "sdk_pin": "openai==2.45.0", "prompt_version": "moving-service-questions-prompt-v3", "schema_version": "moving-service-questions-schema-v3", "frozen_v3_manifest_digest": FROZEN_V3_MANIFEST_DIGEST, "prompt_digest": "1146474ad5112a238446a63d4fc797022ca2cd65d8e9cb6c88935d7f4f3376e8", "provider_schema_digest": "333d6923902c46662243e019074b735500904bc49acbafdc1b929bceed9924e2", "deterministic_request_digest": REQUEST_DIGEST, "canonical_attempt_digest": CANONICAL_DIGEST, "provider_preflight_fingerprint": PROVIDER_FINGERPRINT, "maximum_output_tokens": 500, "token_preflight_timeout_seconds": 5, "store": False, "stream": False, "background": False, "truncation": "disabled", "tools": [], "created_at": stamp(created), "review_deadline": stamp(created + timedelta(minutes=15))}
            evidence_digest = write_json(target.evidence, evidence)
        write_json(target.consumption, {"run_series_id": RUN_SERIES, "sequence": 1, "phase": "preflight", "authorization_digest": digest(target.active), "consumed_at": stamp(created), "reusable": False})
        return {**active, **audit, "audit_digest": audit_digest, "evidence_digest": evidence_digest}
    finally:
        if owned is not None: owned.close()
        close(reason="success", now=datetime.now(timezone.utc), output_root=output_root, repository_root=repository_root)


def review_evidence(*, evidence_sha256: str, input_tokens: int, conservative_cost: str,
                    reviewer: str, decision: str, reviewed_at: str,
                    token_count_plausible: bool, cost_within_limit: bool,
                    frozen_bindings_confirmed: bool, evidence_history_confirmed: bool,
                    notes: str, now: datetime, output_root: Path = DEFAULT_OUTPUT_ROOT,
                    repository_root: Path = REPOSITORY_ROOT) -> Mapping[str, object]:
    target = paths(output_root, repository_root)
    if target.evidence_review.exists() or digest(target.evidence) != evidence_sha256:
        raise V3PreflightError("preflight evidence is absent, changed, or already reviewed")
    evidence = json.loads(target.evidence.read_text())
    required = {"run_series_id": RUN_SERIES, "sequence": 1, "fixture_id": FIXTURE, "phase": "preflight", "frozen_v3_manifest_digest": FROZEN_V3_MANIFEST_DIGEST, "prompt_version": "moving-service-questions-prompt-v3", "schema_version": "moving-service-questions-schema-v3", "prompt_digest": "1146474ad5112a238446a63d4fc797022ca2cd65d8e9cb6c88935d7f4f3376e8", "provider_schema_digest": "333d6923902c46662243e019074b735500904bc49acbafdc1b929bceed9924e2", "deterministic_request_digest": REQUEST_DIGEST, "canonical_attempt_digest": CANONICAL_DIGEST, "provider_preflight_fingerprint": PROVIDER_FINGERPRINT, "provider": "OpenAI", "ai_model_identifier": "gpt-4.1-mini-2025-04-14", "sdk_pin": "openai==2.45.0", "maximum_output_tokens": 500, "token_preflight_timeout_seconds": 5, "automatic_retries": 0, "generation_attempted": False}
    if any(evidence.get(key) != value for key, value in required.items()):
        raise V3PreflightError("preflight evidence binding drifted")
    try: cost = Decimal(conservative_cost)
    except InvalidOperation as error: raise V3PreflightError("cost is invalid") from error
    review_time = utc(reviewed_at); deadline = utc(evidence["review_deadline"])
    confirmations = all((token_count_plausible, cost_within_limit, frozen_bindings_confirmed, evidence_history_confirmed))
    if (evidence.get("input_tokens") != input_tokens or Decimal(str(evidence.get("conservative_maximum_generation_cost"))) != cost
            or decision not in {"approve", "reject", "request_changes"} or not reviewer.strip() or not notes.strip() or len(notes) > 500
            or review_time > now or review_time < utc(evidence["created_at"])
            or (decision == "approve" and (not confirmations or review_time >= deadline or now >= deadline))
            or target.active.exists() or target.execution.read_bytes() != target.closed.read_bytes()):
        raise V3PreflightError("evidence review is invalid or late")
    if not all(path.is_file() for path in (target.audit, target.consumption, target.closure)):
        raise V3PreflightError("preflight evidence history is incomplete")
    record = {"run_series_id": RUN_SERIES, "sequence": 1, "fixture_id": FIXTURE, "phase": "preflight_review", "preflight_evidence_digest": evidence_sha256, "input_tokens": input_tokens, "conservative_maximum_generation_cost": str(cost), "deterministic_request_digest": REQUEST_DIGEST, "canonical_attempt_digest": CANONICAL_DIGEST, "provider_fingerprint": PROVIDER_FINGERPRINT, "frozen_v3_manifest_digest": FROZEN_V3_MANIFEST_DIGEST, "prompt_version": evidence["prompt_version"], "schema_version": evidence["schema_version"], "prompt_digest": evidence["prompt_digest"], "provider_schema_digest": evidence["provider_schema_digest"], "provider": "OpenAI", "ai_model_identifier": "gpt-4.1-mini-2025-04-14", "sdk_pin": "openai==2.45.0", "evidence_created_at": evidence["created_at"], "review_deadline": evidence["review_deadline"], "reviewer": reviewer, "decision": decision, "reviewed_at": reviewed_at, "token_count_plausible": token_count_plausible, "cost_within_limit": cost_within_limit, "frozen_bindings_confirmed": frozen_bindings_confirmed, "evidence_history_confirmed": evidence_history_confirmed, "bounded_notes": notes, "authoritative": False, "generation_authorized": False, "generation_gate_binding_eligible": decision == "approve"}
    return {"review_path": target.evidence_review, "review_digest": write_json(target.evidence_review, record), "decision": decision, "generation_gate_binding_eligible": decision == "approve"}


def generation_binding_dry_run(*, output_root: Path = DEFAULT_OUTPUT_ROOT) -> Mapping[str, object]:
    target = paths(output_root)
    evidence = json.loads(target.evidence.read_text()); review = json.loads(target.evidence_review.read_text())
    if review.get("decision") != "approve" or review.get("preflight_evidence_digest") != digest(target.evidence) or review.get("generation_gate_binding_eligible") is not True:
        raise V3PreflightError("approved v3 evidence cannot resolve generation candidate")
    binding = {"preflight_evidence_digest": digest(target.evidence), "preflight_review_digest": digest(target.evidence_review), "input_tokens": evidence["input_tokens"], "conservative_maximum_generation_cost": evidence["conservative_maximum_generation_cost"], "deterministic_request_digest": REQUEST_DIGEST, "canonical_attempt_digest": CANONICAL_DIGEST, "provider_fingerprint": PROVIDER_FINGERPRINT}
    preview = json.dumps(binding, separators=(",", ":"), sort_keys=True).encode()
    return {**binding, "resolved_binding_preview_digest": hashlib.sha256(preview).hexdigest(), "writes_performed": False, "authoritative": False, "generation_authorized": False}


def cleanup_review_package(*, confirm: bool, operator: str | None, now: datetime,
                           output_root: Path = DEFAULT_OUTPUT_ROOT) -> Mapping[str, object]:
    target = paths(output_root); review_files = (RENDERED_TMP, target.rendered, target.installation, target.activation_review)
    for path in review_files:
        if path.is_symlink() or not path.is_file(): raise V3PreflightError("fixed cleanup file is absent or unsafe")
    artifact = tomllib.loads(target.rendered.read_text())
    if utc(artifact["approval"]["expires_at"]) >= now or any(p.exists() for p in (target.active, target.activation, target.transaction, target.audit, target.evidence, target.closure)):
        raise V3PreflightError("review package is not eligible for cleanup")
    result = {"exact_paths": [str(p) for p in review_files], "expired": True, "authoritative": False, "activated": False, "execution_manifest_closed": target.execution.read_bytes() == target.closed.read_bytes(), "sequence_1_unused": True, "deleted": False}
    if not confirm: return result
    if not operator or not operator.strip(): raise V3PreflightError("cleanup operator is required")
    record = {"run_series_id": RUN_SERIES, "sequence": 1, "fixture_id": FIXTURE, "reason": "expired_unactivated_review_package", "exact_paths": result["exact_paths"], "pre_deletion_digests": {str(p): digest(p) for p in review_files}, "cleanup_timestamp": stamp(now), "operator": operator, "authoritative": False, "activated": False, "deleted": True}
    write_json(target.cleanup, record)
    for path in review_files: path.unlink()
    return {**result, "deleted": True, "cleanup_path": target.cleanup, "cleanup_digest": digest(target.cleanup)}
