"""Fixed offline sequence-4 generation gate and evidence lifecycle."""

from __future__ import annotations

import hashlib
import json
import os
import tomllib
from dataclasses import dataclass
from datetime import datetime, timezone
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
from run_openai_stage_b_v2_pilot import PreparedV2Pilot, prepare_frozen_v2_pilot
from run_openai_stage_b_v2_two_gate import (
    _exact_request_digest,
    _fingerprint,
    frozen_binding_identity,
)
from openai_transport import OpenAIPreflightResult
from openai_transport_v2 import make_v2_openai_transport

RUN_SERIES_ID = "moving-service-stage-b-v2-pilot-20260802"
SEQUENCE = 4
FIXTURE_ID = "storage_unknown"
PREFIX = "004-storage_unknown-generation"
OPERATOR_INTENT = "AUTHORIZE_ONE_STORAGE_UNKNOWN_V2_GENERATION_ONLY"
CANDIDATE_DIGEST = "0eaf61f75a1026e7dc53bcf7b1cceaa8e2cec106628aba48bc14796f12ce508a"
MANIFEST_DIGEST = "c86160aaf4781efaca972507876b25579bd5b91a76bbe9eb3141ccabb3f6ff3c"
PREFLIGHT_EVIDENCE_DIGEST = "e19a7b412f6a7f1517dcef32ab6fb7c305049ced90aac252bd8e55f7b0a9a38c"
PREFLIGHT_REVIEW_DIGEST = "7846de2614f673e3afb7af9e26c20ba06b785547deb1eb3f76d3409a4168c541"
REQUEST_DIGEST = "3150794ae420dfe6671ca141b762cda0a39d5fdeb11b1dbe2d97817b9ef5bfea"
CANONICAL_ATTEMPT_DIGEST = "d1f6b54caebf3745ba0447b8644edbc71b6f95879d8c6ed64d77b0ee590118ce"
PROVIDER_FINGERPRINT = "60e29402cc77e914b36d038f04a6a2eb1a0d6fcfb8fe9fd20e6837f3b887d4ef"
INPUT_TOKENS = 2228
CONSERVATIVE_COST = Decimal("0.0016912")
FROZEN_V2_DIGEST = "3fb5d63b438f7658f319b3300885cea1d27c307bec30d6c2b85fdb8ca5d7741e"

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = REPOSITORY_ROOT / "docs/experiments/suggest-moving-service-questions/v2-pilot/authorization-review/phase-candidates/sequence-4-generation"
CANDIDATE_PATH = PACKAGE_ROOT / "inactive-sequence-4-generation-authorization-candidate.toml"
MANIFEST_PATH = PACKAGE_ROOT / "sequence-4-generation-candidate-manifest.json"


class Sequence4GenerationGateError(ValueError):
    pass


@dataclass(frozen=True)
class VerifiedGenerationAttempt:
    """Credential-free, immutable exact request and reviewed preflight binding."""

    prepared: PreparedV2Pilot
    preflight: OpenAIPreflightResult
    deterministic_request_digest: str
    canonical_attempt_digest: str
    provider_fingerprint: str


def verify_exact_generation_attempt(
    *,
    output_root: Path,
    prepared_builder=prepare_frozen_v2_pilot,
    provider_fingerprint_builder=None,
) -> VerifiedGenerationAttempt:
    """Verify the exact generation attempt before any credential boundary."""
    verified_history = verify_candidate_and_preflight(
        output_root=output_root, require_closed_repository=False
    )
    prepared = prepared_builder()
    frozen = frozen_binding_identity(prepared)
    request_digest = _exact_request_digest(prepared)
    canonical_digest = _fingerprint(prepared)
    if provider_fingerprint_builder is None:
        provider_fingerprint_builder = lambda value: make_v2_openai_transport(
            SimpleNamespace(max_retries=0), value
        ).request_fingerprint(value.provider_request)
    provider_fingerprint = provider_fingerprint_builder(prepared)
    evidence_path = output_root / RUN_SERIES_ID / "004-storage_unknown-preflight-evidence.json"
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    expected_frozen = {
        "frozen_v2_manifest_digest": FROZEN_V2_DIGEST,
        "prompt_version": "moving-service-questions-prompt-v2",
        "prompt_digest": "9bcc190f9c4c51fba1caed8c5d284de9d29d6fe8d675132a04f741cc9a1af7a6",
        "schema_version": "moving-service-questions-schema-v2",
        "provider_schema_digest": "822f23e6c0fc9845626e05bd8131fd5e30a0933f8fd268296ae688cc67ebf411",
        "pilot_configuration_digest": "08d1d6781cae9150c059736ea92e119226234c8e53c798766f2901f010499ad3",
        "provider": "OpenAI",
        "ai_model_identifier": "gpt-4.1-mini-2025-04-14",
        "sdk_pin": "openai==2.45.0",
    }
    if any(frozen.get(key) != value for key, value in expected_frozen.items()):
        raise Sequence4GenerationGateError("frozen generation request binding drifted")
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
    if any(evidence.get(key) != value for key, value in expected_parameters.items()):
        raise Sequence4GenerationGateError("generation request parameters drifted")
    if (
        request_digest != REQUEST_DIGEST
        or canonical_digest != CANONICAL_ATTEMPT_DIGEST
        or provider_fingerprint != PROVIDER_FINGERPRINT
        or verified_history["input_tokens"] != INPUT_TOKENS
        or verified_history["conservative_maximum_generation_cost"] != str(CONSERVATIVE_COST)
    ):
        raise Sequence4GenerationGateError("exact generation attempt drifted")
    return VerifiedGenerationAttempt(
        prepared=prepared,
        preflight=OpenAIPreflightResult(
            PROVIDER_FINGERPRINT, INPUT_TOKENS, 0.0, CONSERVATIVE_COST
        ),
        deterministic_request_digest=request_digest,
        canonical_attempt_digest=canonical_digest,
        provider_fingerprint=provider_fingerprint,
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
               "artifact_digest": artifact_sha256, "closed_manifest_digest": _digest(closed)}
    _exclusive(paths.transaction, journal)
    try:
        if failpoint == "after_prepared":
            raise OSError("synthetic interruption")
        _exclusive_bytes(paths.active, paths.review_rendered.read_bytes())
        if failpoint == "after_authorization_installed":
            raise OSError("synthetic interruption")
        active_manifest = {
            "status": "active_v2_generation_only", "capability": "suggest_moving_service_questions",
            "run_series_id": RUN_SERIES_ID, "sequence": 4, "fixture_id": FIXTURE_ID,
            "authorization_digest": artifact_sha256, "credential_access_authorized": True,
            "token_preflight_authorized": False, "ai_generation_authorized": True,
            "formal_evaluation_authorized": False, "stage_c_authorized": False,
            "production_use_authorized": False, "automatic_retries": 0,
        }
        _atomic_replace(execution, (json.dumps(active_manifest, indent=2, sort_keys=True) + "\n").encode())
        if failpoint == "after_manifest_transition":
            raise OSError("synthetic interruption")
        activation = {"transaction_id": transaction_id, "phase": "generation", "sequence": 4,
                      "authorization_digest": artifact_sha256, "active_manifest_digest": _digest(execution),
                      "operator": operator, "operator_intent": operator_intent, "activated_at": _stamp(now),
                      "generation_only": True, "token_preflight_authorized": False}
        activation_digest = _exclusive(paths.activation, activation)
        if failpoint == "after_activation_record":
            raise OSError("synthetic interruption")
        journal["state"] = "committed"
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
    temporary = path.with_name(f".{path.name}.sequence4-generation.tmp")
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
        "authorization_version": "moving-service-openai-v2-generation-sequence-4-v1",
        "authorization_status": "approved_v2_generation", "phase": "generation",
        "active_repository_authority": True,
    }:
        raise Sequence4GenerationGateError("rendered generation metadata drifted")
    if artifact.get("bindings") != candidate["bindings"] or artifact.get("approved_preflight") != candidate["approved_preflight"]:
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


def verify_candidate_and_preflight(*, repository_root: Path = REPOSITORY_ROOT,
                                   output_root: Path,
                                   require_closed_repository: bool = True) -> Mapping[str, object]:
    if _digest(CANDIDATE_PATH) != CANDIDATE_DIGEST:
        raise Sequence4GenerationGateError("generation candidate digest drifted")
    candidate = tomllib.loads(CANDIDATE_PATH.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if _digest(MANIFEST_PATH) != MANIFEST_DIGEST or manifest.get("candidate_digest") != CANDIDATE_DIGEST:
        raise Sequence4GenerationGateError("generation manifest binding drifted")
    evidence_path = output_root / RUN_SERIES_ID / "004-storage_unknown-preflight-evidence.json"
    review_path = output_root / RUN_SERIES_ID / "004-storage_unknown-preflight-review.json"
    if _digest(evidence_path) != PREFLIGHT_EVIDENCE_DIGEST or _digest(review_path) != PREFLIGHT_REVIEW_DIGEST:
        raise Sequence4GenerationGateError("approved preflight history drifted")
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    review = json.loads(review_path.read_text(encoding="utf-8"))
    expected = {
        "sequence": SEQUENCE,
        "fixture_id": FIXTURE_ID,
        "input_tokens": INPUT_TOKENS,
        "conservative_maximum_generation_cost": str(CONSERVATIVE_COST),
        "deterministic_request_digest": REQUEST_DIGEST,
        "canonical_attempt_digest": CANONICAL_ATTEMPT_DIGEST,
        "provider_preflight_fingerprint": PROVIDER_FINGERPRINT,
        "frozen_v2_manifest_digest": FROZEN_V2_DIGEST,
        "provider": "OpenAI",
        "ai_model_identifier": "gpt-4.1-mini-2025-04-14",
        "sdk_pin": "openai==2.45.0",
    }
    if any(evidence.get(key) != value for key, value in expected.items()):
        raise Sequence4GenerationGateError("approved preflight binding drifted")
    if review.get("decision") != "approve" or review.get("generation_gate_binding_eligible") is not True:
        raise Sequence4GenerationGateError("preflight evidence review is not approved")
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
    approved = candidate["approved_preflight"]
    if approved != {
        "preflight_evidence_digest": PREFLIGHT_EVIDENCE_DIGEST,
        "preflight_review_digest": PREFLIGHT_REVIEW_DIGEST,
        "input_tokens": INPUT_TOKENS, "conservative_cost": str(CONSERVATIVE_COST),
        "request_digest": REQUEST_DIGEST, "canonical_attempt_digest": CANONICAL_ATTEMPT_DIGEST,
        "provider_fingerprint": PROVIDER_FINGERPRINT,
    }:
        raise Sequence4GenerationGateError("candidate preflight binding drifted")
    if candidate["authorization"]["ai_generation_authorized"] is not False:
        raise Sequence4GenerationGateError("inactive candidate grants authority")
    closed = repository_root / "docs/experiments/suggest-moving-service-questions/v2-pilot/closed-execution-manifest.json"
    current = closed.with_name("execution-manifest.json")
    if require_closed_repository and current.read_bytes() != closed.read_bytes():
        raise Sequence4GenerationGateError("repository authority is not permanently closed")
    return {"candidate_digest": CANDIDATE_DIGEST, "manifest_digest": _digest(MANIFEST_PATH), **expected}


def _reject_duplicate_keys(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate JSON key")
        value[key] = item
    return value


def validate_generated_response(raw: object) -> tuple[str, object]:
    """Apply structural, semantic, and all prose checks without repair."""
    prepared = prepare_frozen_v2_pilot()
    if isinstance(raw, str):
        try:
            raw = json.loads(raw, object_pairs_hook=_reject_duplicate_keys)
        except (json.JSONDecodeError, ValueError):
            return "structural_failure", None
    if not isinstance(raw, Mapping):
        return "structural_failure", None
    try:
        MovingServiceQuestionResponseV2.model_validate(raw)
    except Exception:
        return "structural_failure", None
    try:
        return "validated", validate_response_v2(prepared.request, raw)
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
        "fallback_used": classification != "validated", "fallback_version": None,
        "response_evidence_sha256": None, "human_review_status": "pending",
        "authorization_consumed": True, "generation_closed": True,
        "generation_succeeded": classification == "validated",
    }
    if classification == "validated":
        assert isinstance(result, MovingServiceQuestionResponseV2)
        audit["response_evidence_sha256"] = _exclusive(paths.response_evidence, result.model_dump(mode="json"))
    else:
        if classification == "prose_failure":
            audit["prose_violation_codes"] = list(result)  # type: ignore[arg-type]
        fallback = select_fallback_v2(prepare_frozen_v2_pilot().request)
        audit["fallback_used"] = fallback is not None
        audit["fallback_version"] = FALLBACK_VERSION_V2
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
