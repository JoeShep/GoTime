"""Network-disabled two-gate v2 pilot orchestration with injected boundaries."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Callable, Mapping, Protocol

from pydantic import ValidationError

from app.moving_service_questions import ResponseValidationError
from moving_service_questions_v2 import (
    FALLBACK_VERSION_V2,
    MovingServiceQuestionResponseV2,
    ProseValidationError,
    select_fallback_v2,
    validate_response_v2,
)
from openai_client_factory import CONVENTIONAL_OPENAI_ENVIRONMENT_NAMES
from openai_transport import OpenAIPreflightResult
from real_model_adapter import MovingServiceProviderRequest, MovingServiceTransportResult
from run_openai_stage_b_v2_pilot import (
    CREDENTIAL_NAME,
    DEFAULT_EXECUTION_MANIFEST,
    DEFAULT_OUTPUT_ROOT,
    ENABLEMENT_NAME,
    PreparedV2Pilot,
    V2FollowUpPilotError,
    V2PilotTransport,
    _digest,
    _fingerprint,
    _write_exclusive,
    prepare_frozen_v2_pilot,
)
from v2_follow_up_authorization import FIXTURE_ID, RUN_SERIES_ID, SEQUENCE
from v2_two_gate_authorization import VerifiedV2PhaseAuthorization

PREFLIGHT_INTENT = "AUTHORIZE_ONE_STORAGE_UNKNOWN_V2_PREFLIGHT_ONLY"
GENERATION_INTENT = "AUTHORIZE_ONE_STORAGE_UNKNOWN_V2_GENERATION_ONLY"


def phase_paths(output_root: Path = DEFAULT_OUTPUT_ROOT) -> dict[str, Path]:
    directory = output_root / RUN_SERIES_ID
    prefix = f"{SEQUENCE:03d}-{FIXTURE_ID}"
    return {
        "preflight_audit": directory / f"{prefix}-preflight.json",
        "preflight_evidence": directory / f"{prefix}-preflight-evidence.json",
        "preflight_review": directory / f"{prefix}-preflight-review.json",
        "preflight_consumption": directory / f"{prefix}-preflight-evidence-consumption.json",
        "preflight_closure": directory / f"{prefix}-preflight-closure.json",
        "generation_audit": directory / f"{prefix}-generation-pilot.json",
        "response_evidence": directory / f"{prefix}-reviewed-response.json",
        "generation_closure": directory / f"{prefix}-generation-pilot-closure.json",
    }


def frozen_binding_identity(prepared: PreparedV2Pilot) -> dict[str, object]:
    digests = prepared.frozen_manifest["artifact_digests"]
    manifest_path = Path("docs/experiments/suggest-moving-service-questions/v2/manifest.json")
    return {
        "frozen_v2_manifest_digest": _digest(
            Path(__file__).resolve().parents[3] / manifest_path
        ),
        "prompt_version": prepared.request.prompt_version,
        "prompt_digest": digests["real-model-prompt.toml"],
        "schema_version": prepared.request.schema_version,
        "provider_schema_digest": digests["openai-response-schema.json"],
        "pilot_configuration_digest": digests["openai-follow-up-pilot.toml"],
        "fallback_version": FALLBACK_VERSION_V2,
        "provider": prepared.pilot_configuration["identity"]["provider"],
        "ai_model_identifier": prepared.provider_request.model_identifier,
        "sdk_pin": prepared.pilot_configuration["identity"]["sdk_pin"],
    }


def _stamp(now: datetime) -> str:
    if now.tzinfo is None:
        raise V2FollowUpPilotError("timestamp_rejected")
    return now.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _exact_request_digest(prepared: PreparedV2Pilot) -> str:
    return hashlib.sha256(
        prepared.provider_request.deterministic_request_json.encode("utf-8")
    ).hexdigest()


def _gate_environment(environment: Mapping[str, str], intent: str, expected: str) -> str:
    if intent != expected or environment.get(ENABLEMENT_NAME) != "1":
        raise V2FollowUpPilotError("operator_intent_rejected")
    if any(name in environment for name in CONVENTIONAL_OPENAI_ENVIRONMENT_NAMES):
        raise V2FollowUpPilotError("credential_configuration_rejected")
    credential = environment.get(CREDENTIAL_NAME)
    if not credential:
        raise V2FollowUpPilotError("credential_failure")
    return credential


def _closed_public_gate() -> None:
    state = json.loads(DEFAULT_EXECUTION_MANIFEST.read_text(encoding="utf-8"))
    if state.get("status") == "closed_no_execution_authorized":
        raise V2FollowUpPilotError("repository_authorization_closed")
    raise V2FollowUpPilotError("phase_authorization_not_implemented")


def run_v2_preflight_phase(*, environment: Mapping[str, str], operator_intent: str) -> None:
    """Committed public entry fails before environment inspection."""
    _closed_public_gate()


def load_committed_v2_preflight_authorization(*, now: datetime):
    """Load only complete atomic preflight authority; import stays side-effect free."""
    from v2_preflight_authorization_activation import load_active_preflight_authorization

    return load_active_preflight_authorization(now=now)


def run_v2_generation_phase(*, environment: Mapping[str, str], operator_intent: str) -> None:
    """Committed public entry fails before environment inspection."""
    _closed_public_gate()


def execute_v2_preflight_offline(
    *, authorization: VerifiedV2PhaseAuthorization, environment: Mapping[str, str],
    operator_intent: str, output_root: Path, client_constructor: Callable[[str], object],
    transport_factory: Callable[[object, PreparedV2Pilot], V2PilotTransport],
    closure: Callable[[], bool], now: datetime,
) -> Mapping[str, object]:
    if authorization.phase != "preflight":
        raise V2FollowUpPilotError("preflight_authorization_rejected")
    prepared = prepare_frozen_v2_pilot()
    paths = phase_paths(output_root)
    paths["preflight_audit"].parent.mkdir(parents=True, exist_ok=True)
    if any(paths[key].exists() for key in ("preflight_audit", "preflight_evidence", "preflight_closure")):
        raise FileExistsError("Preflight slot already exists.")
    state: dict[str, object] = {
        "run_series_id": RUN_SERIES_ID, "sequence": SEQUENCE, "fixture_id": FIXTURE_ID,
        "phase": "preflight", "authorization_digest": authorization.digest,
        "credential_lookup_attempted": False, "credential_value_obtained": False,
        "client_construction_attempted": False, "client_construction_succeeded": False,
        "preflight_attempted": False, "preflight_succeeded": False,
        "generation_attempted": False, "input_tokens": None,
        "conservative_maximum_generation_cost": None,
        "bounded_failure_classification": None, "authorization_closed": False,
        "authorization_consumed": False,
    }
    # Reserve before the first credential lookup.
    _write_exclusive(paths["preflight_audit"], state)
    client = None
    try:
        state["credential_lookup_attempted"] = True
        state["authorization_consumed"] = True
        credential = _gate_environment(environment, operator_intent, PREFLIGHT_INTENT)
        state["credential_value_obtained"] = True
        state["client_construction_attempted"] = True
        client = client_constructor(credential)
        state["client_construction_succeeded"] = True
        transport = transport_factory(client, prepared)
        state["preflight_attempted"] = True
        preflight = transport.preflight(prepared.provider_request)
        state["input_tokens"] = preflight.input_tokens
        state["conservative_maximum_generation_cost"] = (
            str(preflight.conservative_cost) if preflight.conservative_cost is not None else None
        )
        if not preflight.succeeded or preflight.request_fingerprint != transport.request_fingerprint(prepared.provider_request):
            raise V2FollowUpPilotError("preflight_failure")
        if preflight.conservative_cost is None or preflight.conservative_cost > Decimal("0.03"):
            raise V2FollowUpPilotError("budget_rejection")
        evidence = {
            "run_series_id": RUN_SERIES_ID, "sequence": SEQUENCE, "fixture_id": FIXTURE_ID,
            "phase": "preflight", **frozen_binding_identity(prepared),
            "deterministic_request_digest": _exact_request_digest(prepared),
            "canonical_attempt_digest": _fingerprint(prepared),
            "provider_preflight_fingerprint": preflight.request_fingerprint,
            "maximum_output_tokens": 500, "temperature": 0,
            "token_preflight_timeout_seconds": 5, "ai_generation_timeout_seconds": 12,
            "automatic_retries": 0, "store": False, "stream": False,
            "background": False, "truncation": "disabled", "tools": [],
            "input_tokens": preflight.input_tokens,
            "cached_input_tokens": None, "uncached_input_tokens": None,
            "conservative_maximum_generation_cost": str(preflight.conservative_cost),
            "preflight_request_id": None, "duration_ms": preflight.duration_ms,
            "created_at": _stamp(now),
            "review_deadline": _stamp(now + timedelta(minutes=15)),
            "authorization_digest": authorization.digest,
            "consumed": False, "human_review_status": "pending",
        }
        _write_exclusive(paths["preflight_evidence"], evidence)
        state["preflight_succeeded"] = True
        return state
    except V2FollowUpPilotError as error:
        state["bounded_failure_classification"] = error.classification
        raise
    finally:
        close = getattr(client, "close", None)
        if callable(close):
            close()
        state["authorization_closed"] = closure()
        paths["preflight_audit"].write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def review_v2_preflight_evidence(
    *, output_root: Path, approved: bool, reviewer: str, token_count_plausible: bool,
    spend_within_ceiling: bool, frozen_bindings_match: bool, evidence_fresh_and_unused: bool,
    notes: str, now: datetime,
) -> Mapping[str, object]:
    paths = phase_paths(output_root)
    if paths["preflight_review"].exists():
        raise FileExistsError("Preflight review already exists.")
    if not reviewer.strip() or len(notes) > 500:
        raise V2FollowUpPilotError("preflight_review_rejected")
    evidence_bytes = paths["preflight_evidence"].read_bytes()
    evidence = json.loads(evidence_bytes)
    deadline = datetime.fromisoformat(str(evidence["review_deadline"]).replace("Z", "+00:00"))
    safe = all((token_count_plausible, spend_within_ceiling, frozen_bindings_match, evidence_fresh_and_unused))
    if approved and (not safe or now >= deadline):
        raise V2FollowUpPilotError("preflight_review_rejected")
    review = {
        "run_series_id": RUN_SERIES_ID, "sequence": SEQUENCE, "fixture_id": FIXTURE_ID,
        "phase": "preflight_review", "review_status": "approved" if approved else "rejected",
        "reviewer": reviewer, "reviewed_at": _stamp(now),
        "token_count_plausible": token_count_plausible,
        "spend_within_ceiling": spend_within_ceiling,
        "frozen_bindings_match": frozen_bindings_match,
        "evidence_fresh_and_unused": evidence_fresh_and_unused,
        "bounded_notes": notes,
        "preflight_evidence_digest": hashlib.sha256(evidence_bytes).hexdigest(),
    }
    _write_exclusive(paths["preflight_review"], review)
    return review


def execute_v2_generation_offline(
    *, authorization: VerifiedV2PhaseAuthorization, environment: Mapping[str, str],
    operator_intent: str, output_root: Path, client_constructor: Callable[[str], object],
    transport_factory: Callable[[object, PreparedV2Pilot], V2PilotTransport],
    closure: Callable[[], bool], now: datetime,
) -> Mapping[str, object]:
    if authorization.phase != "generation":
        raise V2FollowUpPilotError("generation_authorization_rejected")
    prepared = prepare_frozen_v2_pilot()
    paths = phase_paths(output_root)
    if paths["preflight_closure"].exists():
        preflight_closure = json.loads(
            paths["preflight_closure"].read_text(encoding="utf-8")
        )
        if preflight_closure.get("closure_reason") in {
            "bounded_failure", "expiration", "cancellation"
        }:
            raise V2FollowUpPilotError("preflight_phase_permanently_closed")
    evidence_bytes = paths["preflight_evidence"].read_bytes()
    review_bytes = paths["preflight_review"].read_bytes()
    if hashlib.sha256(evidence_bytes).hexdigest() != authorization.evidence_digest:
        raise V2FollowUpPilotError("preflight_evidence_digest_mismatch")
    if hashlib.sha256(review_bytes).hexdigest() != authorization.review_digest:
        raise V2FollowUpPilotError("preflight_review_digest_mismatch")
    evidence = json.loads(evidence_bytes)
    review = json.loads(review_bytes)
    if review.get("review_status") != "approved" or review.get("preflight_evidence_digest") != authorization.evidence_digest:
        raise V2FollowUpPilotError("preflight_review_not_approved")
    if now >= datetime.fromisoformat(str(evidence["review_deadline"]).replace("Z", "+00:00")):
        raise V2FollowUpPilotError("preflight_evidence_expired")
    expected = {
        **frozen_binding_identity(prepared),
        "run_series_id": RUN_SERIES_ID, "sequence": SEQUENCE, "fixture_id": FIXTURE_ID,
        "deterministic_request_digest": _exact_request_digest(prepared),
        "canonical_attempt_digest": _fingerprint(prepared),
    }
    if any(evidence.get(key) != value for key, value in expected.items()):
        raise V2FollowUpPilotError("preflight_evidence_binding_mismatch")
    if evidence.get("input_tokens") != authorization.input_tokens or Decimal(str(evidence.get("conservative_maximum_generation_cost"))) != authorization.conservative_cost:
        raise V2FollowUpPilotError("preflight_evidence_cost_mismatch")
    if (
        evidence.get("deterministic_request_digest") != authorization.request_digest
        or evidence.get("canonical_attempt_digest") != authorization.canonical_attempt_digest
        or evidence.get("provider_preflight_fingerprint") != authorization.provider_fingerprint
    ):
        raise V2FollowUpPilotError("preflight_authorization_binding_mismatch")
    if paths["preflight_consumption"].exists():
        raise V2FollowUpPilotError("preflight_evidence_consumed")
    if any(paths[key].exists() for key in ("generation_audit", "response_evidence", "generation_closure")):
        raise FileExistsError("Generation slot already exists.")
    state: dict[str, object] = {
        "run_series_id": RUN_SERIES_ID, "sequence": SEQUENCE, "fixture_id": FIXTURE_ID,
        "phase": "generation", "authorization_digest": authorization.digest,
        "credential_lookup_attempted": False, "credential_value_obtained": False,
        "client_construction_attempted": False, "client_construction_succeeded": False,
        "preflight_attempted": False, "generation_attempted": False,
        "generation_succeeded": False, "pydantic_validation_succeeded": False,
        "semantic_validation_succeeded": False, "prose_validation_succeeded": False,
        "prose_violation_codes": [], "fallback_used": False,
        "fallback_version": None, "fallback_question_id": None,
        "human_review_status": "pending", "grounding_supported": None,
        "invented_user_fact_present": None, "scope_overstatement_present": None,
        "provider_or_service_recommendation_present": None,
        "storage_required_claim_present": None, "clarity_score": None,
        "usefulness_score": None, "fallback_comparison": None, "reviewer": None,
        "reviewed_at": None, "bounded_review_notes": None,
        "response_evidence_path": None, "response_evidence_sha256": None,
        "response_evidence_delete_by": None, "response_evidence_deleted": False,
        "response_evidence_deletion_recorded_at": None,
        "bounded_failure_classification": None,
        "input_tokens": authorization.input_tokens, "cached_input_tokens": None,
        "uncached_input_tokens": None, "output_tokens": None, "cache_status": "not_available",
        "estimated_cost": None, "provider_request_id": None,
        "authorization_closed": False,
        "authorization_consumed": False,
    }
    _write_exclusive(paths["generation_audit"], state)
    client = None
    try:
        state["credential_lookup_attempted"] = True
        state["authorization_consumed"] = True
        credential = _gate_environment(environment, operator_intent, GENERATION_INTENT)
        state["credential_value_obtained"] = True
        state["client_construction_attempted"] = True
        client = client_constructor(credential)
        state["client_construction_succeeded"] = True
        transport = transport_factory(client, prepared)
        if evidence["provider_preflight_fingerprint"] != transport.request_fingerprint(prepared.provider_request):
            raise V2FollowUpPilotError("preflight_payload_digest_mismatch")
        _write_exclusive(paths["preflight_consumption"], {
            "preflight_evidence_digest": authorization.evidence_digest,
            "generation_authorization_digest": authorization.digest,
            "consumed_at": _stamp(now), "consumed_before_generation": True,
        })
        preflight = OpenAIPreflightResult(
            str(evidence["provider_preflight_fingerprint"]), int(evidence["input_tokens"]),
            float(evidence["duration_ms"]), Decimal(str(evidence["conservative_maximum_generation_cost"])),
        )
        state["generation_attempted"] = True
        result = transport.generate(prepared.provider_request, preflight)
        if result.error_classification is not None:
            raise V2FollowUpPilotError(f"generation_{result.error_classification.value}")
        state["generation_succeeded"] = True
        state.update(
            cached_input_tokens=result.cached_input_tokens,
            uncached_input_tokens=result.uncached_input_tokens,
            output_tokens=result.output_tokens,
            cache_status=result.cache_status,
            estimated_cost=result.estimated_cost,
            provider_request_id=result.provider_request_id,
        )
        if not isinstance(result.estimated_cost, str) or Decimal(result.estimated_cost.removeprefix("$")) > Decimal("0.03"):
            raise V2FollowUpPilotError("generation_budget_rejection")
        if not isinstance(result.response_content, (str, Mapping)):
            raise V2FollowUpPilotError("malformed_json")
        try:
            raw = json.loads(result.response_content) if isinstance(result.response_content, str) else dict(result.response_content)
        except json.JSONDecodeError as error:
            raise V2FollowUpPilotError("malformed_json") from error
        try:
            MovingServiceQuestionResponseV2.model_validate(raw)
        except ValidationError as error:
            raise V2FollowUpPilotError("pydantic_validation_failure") from error
        state["pydantic_validation_succeeded"] = True
        try:
            validated = validate_response_v2(prepared.request, raw)
        except ProseValidationError as error:
            state["semantic_validation_succeeded"] = True
            state["prose_violation_codes"] = list(error.violation_codes)
            fallback = select_fallback_v2(prepared.request)
            state.update(fallback_used=fallback is not None, fallback_version=FALLBACK_VERSION_V2, fallback_question_id=fallback.question_id if fallback else None)
            raise V2FollowUpPilotError("prose_validation_failure") from error
        except ResponseValidationError as error:
            raise V2FollowUpPilotError("semantic_validation_failure") from error
        state["semantic_validation_succeeded"] = True
        state["prose_validation_succeeded"] = True
        _write_exclusive(paths["response_evidence"], validated.model_dump(mode="json"))
        os.chmod(paths["response_evidence"], 0o600)
        state["response_evidence_path"] = str(paths["response_evidence"])
        state["response_evidence_sha256"] = hashlib.sha256(
            paths["response_evidence"].read_bytes()
        ).hexdigest()
        state["response_evidence_delete_by"] = _stamp(now + timedelta(days=30))
        return state
    except V2FollowUpPilotError as error:
        state["bounded_failure_classification"] = error.classification
        raise
    finally:
        close = getattr(client, "close", None)
        if callable(close):
            close()
        state["authorization_closed"] = closure()
        paths["generation_audit"].write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def close_two_gate_phase_offline(
    *, phase: str, reason: str, output_root: Path, now: datetime
) -> Mapping[str, object]:
    """Idempotently prove the committed repository is closed for one phase."""
    if phase not in {"preflight", "generation"} or reason not in {
        "success", "bounded_failure", "expiration", "cancellation"
    }:
        raise V2FollowUpPilotError("phase_closure_rejected")
    execution = DEFAULT_EXECUTION_MANIFEST.read_bytes()
    closed = DEFAULT_EXECUTION_MANIFEST.with_name("closed-execution-manifest.json").read_bytes()
    if execution != closed:
        raise V2FollowUpPilotError("repository_not_closed")
    path = phase_paths(output_root)[f"{phase}_closure"]
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    record = {
        "run_series_id": RUN_SERIES_ID, "sequence": SEQUENCE, "fixture_id": FIXTURE_ID,
        "phase": phase, "closure_reason": reason, "closed_at": _stamp(now),
        "authorization_closed": True, "credential_access_authorized": False,
        "token_preflight_authorized": False, "ai_generation_authorized": False,
        "formal_evaluation_authorized": False, "stage_c_authorized": False,
        "production_use_authorized": False, "contains_secret_or_response_content": False,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_exclusive(path, record)
    return record
