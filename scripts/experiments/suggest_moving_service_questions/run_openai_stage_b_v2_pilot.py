"""Offline-testable runner boundary for the frozen v2 follow-up pilot."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tomllib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Callable, Mapping, Protocol

from pydantic import ValidationError

SCRIPT_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = REPOSITORY_ROOT / "backend"
for import_path in (SCRIPT_ROOT, BACKEND_ROOT):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from app.moving_service_questions import (  # noqa: E402
    ExperimentFixture,
    ResponseValidationError,
    build_trusted_fixture,
)
from openai_transport import OpenAIPreflightResult  # noqa: E402
from real_model_adapter import (  # noqa: E402
    MovingServiceProviderRequest,
    MovingServiceTransportResult,
)
from moving_service_questions_v2 import (  # noqa: E402
    FALLBACK_VERSION_V2,
    PROMPT_VERSION_V2,
    SCHEMA_VERSION_V2,
    ProseValidationError,
    MovingServiceQuestionResponseV2,
    construct_request_v2,
    select_fallback_v2,
    validate_response_v2,
)
from v2_follow_up_authorization import (  # noqa: E402
    CAPABILITY,
    FIXTURE_ID,
    RUN_SERIES_ID,
    SEQUENCE,
    VerifiedV2FollowUpAuthorization,
    V2FollowUpAuthorizationError,
    load_manifest_bound_v2_authorization,
)
from openai_client_factory import CONVENTIONAL_OPENAI_ENVIRONMENT_NAMES  # noqa: E402

DEFAULT_EXECUTION_MANIFEST = (
    REPOSITORY_ROOT
    / "docs/experiments/suggest-moving-service-questions/v2-pilot/"
    "execution-manifest.json"
)
DEFAULT_OUTPUT_ROOT = REPOSITORY_ROOT / ".local/evaluations/suggest-moving-service-questions"
ENABLEMENT_NAME = "GOTIME_MOVING_SERVICE_EVAL_ENABLED"
CREDENTIAL_NAME = "GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY"
OPERATOR_INTENT = "AUTHORIZE_ONE_STORAGE_UNKNOWN_V2_PREFLIGHT_AND_GENERATION"
_EVIDENCE_TOKEN = object()


class V2FollowUpPilotError(RuntimeError):
    def __init__(self, classification: str, audit_path: Path | None = None):
        self.classification = classification
        self.audit_path = audit_path
        super().__init__(f"V2 follow-up pilot failed with {classification}.")


class V2PilotTransport(Protocol):
    def request_fingerprint(self, request: MovingServiceProviderRequest) -> str:
        ...

    def preflight(self, request: MovingServiceProviderRequest) -> OpenAIPreflightResult:
        ...

    def generate(
        self,
        request: MovingServiceProviderRequest,
        preflight: OpenAIPreflightResult,
    ) -> MovingServiceTransportResult:
        ...


class V2PreflightEvidence:
    """Runner-created, nonserializable, exact-attempt, single-use evidence."""

    __slots__ = ("_binding", "_preflight", "_consumed")

    def __init__(
        self,
        *,
        construction_token: object,
        binding: tuple[object, ...],
        preflight: OpenAIPreflightResult,
    ) -> None:
        if construction_token is not _EVIDENCE_TOKEN:
            raise TypeError("V2 preflight evidence is runner-created only.")
        self._binding = binding
        self._preflight = preflight
        self._consumed = False

    def __reduce__(self) -> object:
        raise TypeError("V2 preflight evidence cannot be serialized.")

    def consume(self, binding: tuple[object, ...]) -> OpenAIPreflightResult:
        if self._consumed or binding != self._binding or not self._preflight.succeeded:
            raise V2FollowUpPilotError("preflight_evidence_rejected")
        self._consumed = True
        return self._preflight


@dataclass(frozen=True)
class PreparedV2Pilot:
    request: object
    provider_request: MovingServiceProviderRequest
    frozen_manifest: Mapping[str, object]
    pilot_configuration: Mapping[str, object]


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _paths(output_root: Path) -> tuple[Path, Path, Path]:
    directory = output_root / RUN_SERIES_ID
    prefix = f"{SEQUENCE:03d}-{FIXTURE_ID}"
    return (
        directory / f"{prefix}-generation-pilot.json",
        directory / f"{prefix}-reviewed-response.json",
        directory / f"{prefix}-generation-pilot-closure.json",
    )


def prepare_frozen_v2_pilot() -> PreparedV2Pilot:
    root = REPOSITORY_ROOT / "docs/experiments/suggest-moving-service-questions/v2"
    frozen = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    digests = frozen["artifact_digests"]
    prompt_path = root / "real-model-prompt.toml"
    schema_path = root / "openai-response-schema.json"
    pilot_path = root / "openai-follow-up-pilot.toml"
    for path in (prompt_path, schema_path, pilot_path):
        if _digest(path) != digests[path.name]:
            raise V2FollowUpPilotError("frozen_v2_artifact_drift")
    prompt = tomllib.loads(prompt_path.read_text(encoding="utf-8"))
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    pilot = tomllib.loads(pilot_path.read_text(encoding="utf-8"))
    request = construct_request_v2(
        build_trusted_fixture(ExperimentFixture.STORAGE_UNKNOWN)
    )
    serialized = request.model_dump_json(exclude_none=False, exclude_defaults=False)
    provider_request = MovingServiceProviderRequest(
        model_identifier=pilot["identity"]["ai_model_identifier"],
        model_parameters={"temperature": pilot["model_parameters"]["temperature"]},
        system_instructions=prompt["system_instructions"],
        deterministic_request_json=serialized,
        response_json_schema=schema,
        maximum_output_tokens=pilot["model_parameters"]["maximum_output_tokens"],
        timeout_seconds=float(pilot["transport"]["ai_generation_timeout_seconds"]),
        retry_count=pilot["transport"]["automatic_retries"],
    )
    if request.prompt_version != PROMPT_VERSION_V2 or request.schema_version != SCHEMA_VERSION_V2:
        raise V2FollowUpPilotError("mixed_version_identity")
    return PreparedV2Pilot(request, provider_request, frozen, pilot)


def _fingerprint(prepared: PreparedV2Pilot) -> str:
    value = {
        "common_input": {
            "model": prepared.provider_request.model_identifier,
            "instructions": prepared.provider_request.system_instructions,
            "input": prepared.provider_request.deterministic_request_json,
            "text": {"format": {
                "type": "json_schema",
                "name": "moving_service_question_response_v2",
                "strict": True,
                "schema": prepared.provider_request.response_json_schema,
            }},
            "truncation": "disabled",
        },
        "maximum_output_tokens": prepared.provider_request.maximum_output_tokens,
        "temperature": 0,
        "store": False,
        "background": False,
        "stream": False,
        "generation_timeout_seconds": prepared.provider_request.timeout_seconds,
        "retry_count": prepared.provider_request.retry_count,
    }
    serialized = json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _binding(
    authorization: VerifiedV2FollowUpAuthorization,
    prepared: PreparedV2Pilot,
    audit_path: Path,
    attempt_token: object,
) -> tuple[object, ...]:
    digests = prepared.frozen_manifest["artifact_digests"]
    return (
        authorization.digest,
        RUN_SERIES_ID,
        SEQUENCE,
        FIXTURE_ID,
        _fingerprint(prepared),
        digests["real-model-prompt.toml"],
        digests["openai-response-schema.json"],
        digests["openai-follow-up-pilot.toml"],
        prepared.provider_request.model_identifier,
        tuple(sorted(prepared.provider_request.model_parameters.items())),
        audit_path,
        attempt_token,
        authorization.approved_at,
        authorization.expires_at,
    )


def _write_exclusive(path: Path, value: Mapping[str, object]) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as output:
        json.dump(value, output, indent=2, sort_keys=True)
        output.write("\n")


def execute_authorized_v2_pilot_offline(
    *,
    authorization: VerifiedV2FollowUpAuthorization,
    environment: Mapping[str, str],
    output_root: Path,
    client_constructor: Callable[[str], object],
    transport_factory: Callable[[object, PreparedV2Pilot], V2PilotTransport],
    closure: Callable[[], bool],
) -> dict[str, object]:
    """Exercise the complete authorized path with injected offline boundaries."""
    prepared = prepare_frozen_v2_pilot()
    audit_path, evidence_path, closure_path = _paths(output_root)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    if any(path.exists() for path in (audit_path, evidence_path, closure_path)):
        raise FileExistsError("V2 pilot output already exists.")
    descriptor = os.open(audit_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    output = os.fdopen(descriptor, "w", encoding="utf-8")
    state: dict[str, object] = {
        "run_series_id": RUN_SERIES_ID,
        "sequence": SEQUENCE,
        "fixture_id": FIXTURE_ID,
        "prompt_version": PROMPT_VERSION_V2,
        "schema_version": SCHEMA_VERSION_V2,
        "fallback_version": FALLBACK_VERSION_V2,
        "artifact_digests": prepared.frozen_manifest["artifact_digests"],
        "provider": prepared.pilot_configuration["identity"]["provider"],
        "ai_model_identifier": prepared.provider_request.model_identifier,
        "authorization_digest": authorization.digest,
        "repository_authorization_validated": True,
        "operator_intent_confirmed": True,
        "sdk_version": prepared.pilot_configuration["identity"]["sdk_pin"],
        "provider_schema_digest": prepared.frozen_manifest["artifact_digests"]["openai-response-schema.json"],
        "pilot_configuration_digest": prepared.frozen_manifest["artifact_digests"]["openai-follow-up-pilot.toml"],
        "credential_lookup_attempted": False,
        "credential_value_obtained": False,
        "client_construction_attempted": False,
        "client_construction_succeeded": False,
        "preflight_attempted": False,
        "preflight_succeeded": False,
        "generation_attempted": False,
        "generation_succeeded": False,
        "input_tokens": None,
        "conservative_preflight_cost": None,
        "preflight_duration_ms": None,
        "generation_duration_ms": None,
        "total_duration_ms": None,
        "output_tokens": None,
        "cached_input_tokens": None,
        "uncached_input_tokens": None,
        "cache_status": "not_available",
        "estimated_cost": None,
        "provider_request_id": None,
        "finish_status": None,
        "pydantic_validation_succeeded": False,
        "semantic_validation_succeeded": False,
        "prose_validation_succeeded": False,
        "prose_violation_codes": [],
        "referenced_knowledge_ids": [],
        "fallback_used": False,
        "fallback_question_id": None,
        "human_review_status": "pending",
        "grounding_supported": None,
        "invented_user_fact_present": None,
        "scope_overstatement_present": None,
        "provider_or_service_recommendation_present": None,
        "storage_required_claim_present": None,
        "clarity_score": None,
        "usefulness_score": None,
        "fallback_comparison": None,
        "reviewer": None,
        "reviewed_at": None,
        "bounded_review_notes": None,
        "response_evidence_path": None,
        "response_evidence_sha256": None,
        "response_evidence_delete_by": None,
        "response_evidence_deleted": False,
        "response_evidence_deletion_recorded_at": None,
        "authorization_closed": False,
        "closure_record_path": str(closure_path),
        "bounded_failure_classification": None,
    }
    attempt_token = object()
    try:
        state["credential_lookup_attempted"] = True
        if any(name in environment for name in CONVENTIONAL_OPENAI_ENVIRONMENT_NAMES):
            raise V2FollowUpPilotError("credential_configuration_rejected", audit_path)
        credential = environment.get(CREDENTIAL_NAME)
        if not credential:
            raise V2FollowUpPilotError("credential_failure", audit_path)
        state["credential_value_obtained"] = True
        state["client_construction_attempted"] = True
        client = client_constructor(credential)
        state["client_construction_succeeded"] = True
        transport = transport_factory(client, prepared)
        state["preflight_attempted"] = True
        preflight = transport.preflight(prepared.provider_request)
        state["preflight_succeeded"] = preflight.succeeded
        state["input_tokens"] = preflight.input_tokens
        state["preflight_duration_ms"] = preflight.duration_ms
        state["conservative_preflight_cost"] = (
            str(preflight.conservative_cost) if preflight.conservative_cost is not None else None
        )
        if (
            not preflight.succeeded
            or preflight.request_fingerprint
            != transport.request_fingerprint(prepared.provider_request)
        ):
            raise V2FollowUpPilotError("preflight_failure", audit_path)
        if preflight.conservative_cost is None or preflight.conservative_cost > Decimal("0.03"):
            raise V2FollowUpPilotError("budget_rejection", audit_path)
        binding = _binding(authorization, prepared, audit_path, attempt_token)
        evidence = V2PreflightEvidence(
            construction_token=_EVIDENCE_TOKEN,
            binding=binding,
            preflight=preflight,
        )
        consumed = evidence.consume(binding)
        state["generation_attempted"] = True
        result = transport.generate(prepared.provider_request, consumed)
        state.update(
            output_tokens=result.output_tokens,
            cached_input_tokens=result.cached_input_tokens,
            uncached_input_tokens=result.uncached_input_tokens,
            cache_status=result.cache_status,
            estimated_cost=result.estimated_cost,
            provider_request_id=result.provider_request_id,
            finish_status=result.finish_status,
            preflight_duration_ms=result.preflight_duration_ms,
            generation_duration_ms=result.generation_duration_ms,
            total_duration_ms=result.duration_ms,
        )
        if result.error_classification is not None:
            raise V2FollowUpPilotError(
                f"generation_{result.error_classification.value}", audit_path
            )
        state["generation_succeeded"] = True
        if not isinstance(result.estimated_cost, str):
            raise V2FollowUpPilotError("usage_or_cost_unavailable", audit_path)
        if Decimal(result.estimated_cost.removeprefix("$")) > Decimal("0.03"):
            raise V2FollowUpPilotError("budget_rejection", audit_path)
        if not isinstance(result.response_content, (str, Mapping)):
            raise V2FollowUpPilotError("malformed_json", audit_path)
        try:
            raw = (
                json.loads(result.response_content)
                if isinstance(result.response_content, str)
                else dict(result.response_content)
            )
        except json.JSONDecodeError as error:
            raise V2FollowUpPilotError("malformed_json", audit_path) from error
        try:
            structured = MovingServiceQuestionResponseV2.model_validate(raw)
        except ValidationError as error:
            raise V2FollowUpPilotError("pydantic_validation_failure", audit_path) from error
        state["pydantic_validation_succeeded"] = True
        state["referenced_knowledge_ids"] = sorted(
            {
                knowledge_id
                for suggestion in structured.suggestions
                for knowledge_id in suggestion.relevant_knowledge_ids
            }
        )
        try:
            validated = validate_response_v2(prepared.request, raw)
        except ProseValidationError as error:
            state["semantic_validation_succeeded"] = True
            state["prose_violation_codes"] = list(error.violation_codes)
            fallback = select_fallback_v2(prepared.request)
            state["fallback_used"] = fallback is not None
            state["fallback_question_id"] = (
                fallback.question_id if fallback is not None else None
            )
            raise V2FollowUpPilotError("prose_validation_failure", audit_path) from error
        except ResponseValidationError as error:
            raise V2FollowUpPilotError("semantic_validation_failure", audit_path) from error
        state["semantic_validation_succeeded"] = True
        state["prose_validation_succeeded"] = True
        _write_exclusive(evidence_path, validated.model_dump(mode="json"))
        os.chmod(evidence_path, 0o600)
        state["response_evidence_sha256"] = _digest(evidence_path)
        state["response_evidence_path"] = str(evidence_path)
        state["response_evidence_delete_by"] = (
            datetime.now(timezone.utc) + timedelta(days=30)
        ).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        return state
    except V2FollowUpPilotError as error:
        state["bounded_failure_classification"] = error.classification
        raise
    except Exception:
        state["bounded_failure_classification"] = "unexpected_failure"
        raise
    finally:
        active_exception = sys.exc_info()[0] is not None
        cleanup_failure: str | None = None
        close_method = getattr(locals().get("client"), "close", None)
        if callable(close_method):
            try:
                close_method()
            except Exception:
                cleanup_failure = "client_close_failure"
                state["bounded_failure_classification"] = state["bounded_failure_classification"] or cleanup_failure
        try:
            state["authorization_closed"] = closure()
        except Exception:
            state["authorization_closed"] = False
            cleanup_failure = "closure_failure"
            state["bounded_failure_classification"] = state["bounded_failure_classification"] or cleanup_failure
        if not closure_path.exists():
            _write_exclusive(
                closure_path,
                {
                    "run_series_id": RUN_SERIES_ID,
                    "sequence": SEQUENCE,
                    "authorization_closed": state["authorization_closed"],
                    "contains_response_content": False,
                },
            )
        json.dump(state, output, indent=2, sort_keys=True)
        output.write("\n")
        output.close()
        if cleanup_failure is not None and not active_exception:
            raise V2FollowUpPilotError(cleanup_failure, audit_path)


def run_v2_follow_up_pilot_with_injected_boundaries(
    *,
    execution_manifest_path: Path,
    repository_root: Path,
    environment: Mapping[str, str],
    operator_intent: str,
    run_series_id: str,
    sequence: int,
    fixture_id: str,
    output_root: Path,
    client_constructor: Callable[[str], object],
    transport_factory: Callable[[object, PreparedV2Pilot], V2PilotTransport],
    closure: Callable[[], bool],
    now: datetime,
) -> dict[str, object]:
    """Exercise exact gates with injected, network-disabled boundaries only."""
    authorization = load_manifest_bound_v2_authorization(
        execution_manifest_path,
        repository_root=repository_root,
        now=now,
    )
    if (run_series_id, sequence, fixture_id) != (RUN_SERIES_ID, SEQUENCE, FIXTURE_ID):
        raise V2FollowUpPilotError("pilot_slot_rejected")
    if operator_intent != OPERATOR_INTENT:
        raise V2FollowUpPilotError("operator_intent_rejected")
    if environment.get(ENABLEMENT_NAME) != "1":
        raise V2FollowUpPilotError("operator_enablement_rejected")
    return execute_authorized_v2_pilot_offline(
        authorization=authorization,
        environment=environment,
        output_root=output_root,
        client_constructor=client_constructor,
        transport_factory=transport_factory,
        closure=closure,
    )


def run_v2_follow_up_pilot(
    *,
    environment: Mapping[str, str],
    operator_intent: str,
    execution_manifest_path: Path = DEFAULT_EXECUTION_MANIFEST,
) -> dict[str, object]:
    """Public entry remains closed before environment or output inspection."""
    if execution_manifest_path.resolve() != DEFAULT_EXECUTION_MANIFEST.resolve():
        raise V2FollowUpPilotError("execution_manifest_path_rejected")
    try:
        load_manifest_bound_v2_authorization(
            execution_manifest_path,
            repository_root=REPOSITORY_ROOT,
        )
    except V2FollowUpAuthorizationError as error:
        raise V2FollowUpPilotError("repository_authorization_closed") from error
    if operator_intent != OPERATOR_INTENT:
        raise V2FollowUpPilotError("operator_intent_rejected")
    if environment.get(ENABLEMENT_NAME) != "1":
        raise V2FollowUpPilotError("operator_enablement_rejected")
    raise V2FollowUpPilotError("real_execution_not_implemented_or_authorized")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the exact v2 follow-up pilot slot.")
    parser.add_argument("--run-series", required=True, choices=[RUN_SERIES_ID])
    parser.add_argument("--sequence", required=True, type=int, choices=[SEQUENCE])
    parser.add_argument("--fixture", required=True, choices=[FIXTURE_ID])
    parser.add_argument("--operator-intent", required=True, choices=[OPERATOR_INTENT])
    arguments = parser.parse_args()
    run_v2_follow_up_pilot(
        environment=os.environ,
        operator_intent=arguments.operator_intent,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
