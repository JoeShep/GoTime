"""Fail-closed Stage B single-generation pilot runner."""

from __future__ import annotations

import hashlib
import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Callable, Mapping

from pydantic import ValidationError

SCRIPT_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = REPOSITORY_ROOT / "backend"
for item in (SCRIPT_ROOT, BACKEND_ROOT):
    if str(item) not in sys.path:
        sys.path.insert(0, str(item))

from app.moving_service_questions import (  # noqa: E402
    CAPABILITY,
    ExperimentFixture,
    MovingServiceQuestionResponse,
    ResponseValidationError,
    build_trusted_fixture,
    construct_request,
    normalize_question_text,
    validate_response,
)
from openai_client_factory import (  # noqa: E402
    REQUIRED_NON_SECRET_GATE_ORDER,
    CredentialBoundaryError,
    CredentialAccessNotAuthorizedError,
    EvaluationCredentialError,
    MovingServiceOpenAIClient,
    OpenAIClientConstructionError,
    build_stage_b_moving_service_openai_client_with_pinned_sdk,
)
from openai_transport import (  # noqa: E402
    OPENAI_MODEL_IDENTIFIER,
    OPENAI_RESPONSE_SCHEMA_DIGEST,
    OPENAI_RUN_CONFIGURATION_DIGEST,
    OpenAIMovingServiceEvaluationTransport,
    OpenAIBudgetGateError,
    OpenAIIncompleteResponseError,
    OpenAIPreflightGateError,
    OpenAIPreflightResult,
    OpenAIProviderSchemaError,
    OpenAIRefusalError,
)
from real_model_adapter import (  # noqa: E402
    DEFAULT_TIMEOUT_SECONDS,
    FROZEN_PROMPT_DIGEST,
    MovingServiceProviderRequest,
    RealModelMovingServiceQuestionAdapter,
    parse_untrusted_response,
)
from run_real_model_evaluation import DEFAULT_MANIFEST_PATH, DEFAULT_OUTPUT_ROOT, OfflineRunnerGateError, _validate_output_root  # noqa: E402
from stage_b_authorization import (  # noqa: E402
    AUTHORIZATION_VERSION,
    FIXTURE_ID,
    RUN_SERIES_ID,
    SEQUENCE,
    StageBAuthorizationError,
    VerifiedStageBAuthorization,
    load_manifest_bound_stage_b_authorization,
)

OPERATOR_INTENT = "AUTHORIZE_ONE_STORAGE_UNKNOWN_STAGE_B_PREFLIGHT_AND_GENERATION"
ENABLEMENT_ENVIRONMENT_NAME = "GOTIME_MOVING_SERVICE_EVAL_ENABLED"
MAXIMUM_SPEND = Decimal("0.03")
_EVIDENCE_TOKEN = object()


class StageBPilotError(RuntimeError):
    def __init__(self, classification: str, record_path: Path) -> None:
        super().__init__(f"Stage B failed with {classification}; see audit record.")
        self.classification = classification
        self.record_path = record_path


class StageBPreflightEvidence:
    """Nonserializable, same-attempt, single-use authorization for generation."""

    __slots__ = ("authorization_digest", "run_series_id", "sequence", "fixture_id", "request_fingerprint", "prompt_digest", "run_configuration_digest", "provider_schema_digest", "ai_model_identifier", "model_parameters", "audit_record_path", "attempt_token", "approved_at", "expires_at", "preflight", "_consumed")

    def __init__(self, *, construction_token: object, authorization: VerifiedStageBAuthorization, request: MovingServiceProviderRequest, preflight: OpenAIPreflightResult, audit_record_path: Path, attempt_token: object) -> None:
        if construction_token is not _EVIDENCE_TOKEN:
            raise TypeError("Stage B evidence is runner-created only.")
        self.authorization_digest = authorization.digest
        self.run_series_id = RUN_SERIES_ID
        self.sequence = SEQUENCE
        self.fixture_id = FIXTURE_ID
        self.request_fingerprint = preflight.request_fingerprint
        self.prompt_digest = FROZEN_PROMPT_DIGEST
        self.run_configuration_digest = OPENAI_RUN_CONFIGURATION_DIGEST
        self.provider_schema_digest = OPENAI_RESPONSE_SCHEMA_DIGEST
        self.ai_model_identifier = request.model_identifier
        self.model_parameters = tuple(sorted(request.model_parameters.items()))
        self.audit_record_path = audit_record_path
        self.attempt_token = attempt_token
        self.approved_at = authorization.approved_at
        self.expires_at = authorization.expires_at
        self.preflight = preflight
        self._consumed = False

    def __reduce__(self) -> object:
        raise TypeError("Stage B preflight evidence cannot be serialized.")

    def consume(self, *, authorization: VerifiedStageBAuthorization, request: MovingServiceProviderRequest, audit_record_path: Path, attempt_token: object, now: datetime) -> OpenAIPreflightResult:
        expected = (
            authorization.digest, RUN_SERIES_ID, SEQUENCE, FIXTURE_ID,
            FROZEN_PROMPT_DIGEST, OPENAI_RUN_CONFIGURATION_DIGEST,
            OPENAI_RESPONSE_SCHEMA_DIGEST, request.model_identifier,
            tuple(sorted(request.model_parameters.items())), audit_record_path,
            attempt_token, authorization.approved_at, authorization.expires_at,
        )
        actual = (
            self.authorization_digest, self.run_series_id, self.sequence,
            self.fixture_id, self.prompt_digest, self.run_configuration_digest,
            self.provider_schema_digest, self.ai_model_identifier,
            self.model_parameters, self.audit_record_path, self.attempt_token,
            self.approved_at, self.expires_at,
        )
        if self._consumed or actual != expected or not self.preflight.succeeded or not authorization.approved_at <= now < authorization.expires_at:
            raise OpenAIPreflightGateError("Stage B evidence is consumed, stale, failed, or mismatched.")
        self._consumed = True
        return self.preflight


@dataclass(frozen=True)
class StageBAuditRecord:
    run_series_id: str
    run_sequence: int
    fixture_id: str
    capability: str
    authorization_version: str
    authorization_digest: str
    prompt_version: str
    prompt_digest: str
    request_schema_version: str
    response_schema_version: str
    knowledge_fixture_version: str
    run_configuration_digest: str
    provider_schema_digest: str
    provider: str
    ai_model_identifier: str
    provider_reported_model_identifier: str | None
    sdk_version: str
    operator_intent_confirmed: bool
    credential_lookup_attempted: bool
    credential_value_obtained: bool
    client_construction_attempted: bool
    client_construction_succeeded: bool
    preflight_attempted: bool
    preflight_succeeded: bool
    conservative_preflight_cost: str | None
    input_tokens: int | None
    generation_attempted: bool
    generation_succeeded: bool
    output_tokens: int | None
    cached_input_tokens: int | None
    uncached_input_tokens: int | None
    preflight_duration_ms: float
    generation_duration_ms: float
    total_duration_ms: float
    estimated_cost: str | None
    cache_status: str
    provider_request_id: str | None
    finish_status: str | None
    refusal_status: str | None
    incomplete_reason: str | None
    pydantic_validation_succeeded: bool
    semantic_validation_succeeded: bool
    bounded_failure_classification: str | None
    failure_stage: str | None
    normalized_question_text: str | None
    referenced_knowledge_ids: tuple[str, ...]
    response_evidence_path: str | None
    response_evidence_sha256: str | None
    response_evidence_delete_by: str | None
    response_evidence_deleted: bool
    response_evidence_deletion_recorded_at: str | None
    authorization_closed: bool
    closure_status: str
    closure_record_path: str
    fallback_used: bool
    human_review_status: str
    grounding_supported: bool | None
    invented_user_fact_present: bool | None
    scope_overstatement_present: bool | None
    provider_or_service_recommendation_present: bool | None
    storage_required_claim_present: bool | None
    clarity_score: int | None
    usefulness_score: int | None
    fallback_comparison: str | None
    reviewer: str | None
    reviewed_at: str | None
    bounded_review_notes: str | None


def _paths(output_root: Path) -> tuple[Path, Path]:
    directory = output_root / RUN_SERIES_ID
    return directory / "001-storage_unknown-generation-pilot.json", directory / "001-storage_unknown-reviewed-response.json"


def _provider_request() -> tuple[object, MovingServiceProviderRequest]:
    request = construct_request(build_trusted_fixture(ExperimentFixture.STORAGE_UNKNOWN))
    adapter = RealModelMovingServiceQuestionAdapter(
        model_identifier=OPENAI_MODEL_IDENTIFIER,
        model_parameters={"temperature": 0},
        transport=object(),
        prompt_artifact_path=REPOSITORY_ROOT / "docs/experiments/suggest-moving-service-questions/v1/real-model-prompt.toml",
        expected_prompt_digest=FROZEN_PROMPT_DIGEST,
        timeout_seconds=DEFAULT_TIMEOUT_SECONDS,
    )
    return request, adapter.prepare_request(request)


def _write_json_exclusive(path: Path, value: Mapping[str, object], mode: int = 0o600) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    with os.fdopen(descriptor, "w", encoding="utf-8") as output:
        json.dump(value, output, indent=2, sort_keys=True)
        output.write("\n")


def _require_exact_enablement(environment: Mapping[str, str]) -> None:
    """Treat exact operator enablement as intent, never repository authority."""
    if environment.get(ENABLEMENT_ENVIRONMENT_NAME) != "1":
        raise OfflineRunnerGateError("Stage B enablement must be the exact string 1.")


def _execute_stage_b(*, authorization: VerifiedStageBAuthorization, manifest_path: Path, environment: Mapping[str, str], output_root: Path, client_builder: Callable[..., MovingServiceOpenAIClient], now: Callable[[], datetime] = lambda: datetime.now(timezone.utc)) -> StageBAuditRecord:
    request, provider_request = _provider_request()
    audit_path, evidence_path = _paths(output_root)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    # Reserve before the environment can be touched.
    descriptor = os.open(audit_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    output = os.fdopen(descriptor, "w", encoding="utf-8")
    attempt_token = object()
    closure_path = audit_path.with_name("001-storage_unknown-generation-pilot-closure.json")
    state: dict[str, object] = {
        "operator_intent_confirmed": True,
        "credential_lookup_attempted": False,
        "credential_value_obtained": False,
        "client_construction_attempted": False,
        "client_construction_succeeded": False,
        "preflight_attempted": False,
        "preflight_succeeded": False,
        "conservative_preflight_cost": None,
        "input_tokens": None,
        "generation_attempted": False,
        "generation_succeeded": False,
        "output_tokens": None,
        "cached_input_tokens": None,
        "uncached_input_tokens": None,
        "preflight_duration_ms": 0.0,
        "generation_duration_ms": 0.0,
        "total_duration_ms": 0.0,
        "estimated_cost": None,
        "cache_status": "not_available",
        "provider_request_id": None,
        "provider_reported_model_identifier": None,
        "finish_status": None,
        "refusal_status": None,
        "incomplete_reason": None,
        "pydantic_validation_succeeded": False,
        "semantic_validation_succeeded": False,
        "normalized_question_text": None,
        "referenced_knowledge_ids": (),
        "response_evidence_path": None,
        "response_evidence_sha256": None,
        "response_evidence_delete_by": None,
        "response_evidence_deleted": False,
        "response_evidence_deletion_recorded_at": None,
        "authorization_closed": False,
        "closure_status": "pending",
        "closure_record_path": str(closure_path),
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
    }
    classification: str | None = None
    failure_stage: str | None = None
    try:
        state["credential_lookup_attempted"] = True
        state["client_construction_attempted"] = True
        with client_builder(environment, completed_non_secret_gates=REQUIRED_NON_SECRET_GATE_ORDER, operator_intent_confirmed=True, manifest_path=manifest_path, authorization_path=authorization.path, expected_authorization_digest=authorization.digest) as owned:
            state["credential_value_obtained"] = True
            state["client_construction_succeeded"] = True
            transport = OpenAIMovingServiceEvaluationTransport(client=owned.client)
            state["preflight_attempted"] = True
            preflight = transport.preflight(provider_request)
            state.update(preflight_succeeded=preflight.succeeded, input_tokens=preflight.input_tokens, preflight_duration_ms=preflight.duration_ms, conservative_preflight_cost=str(preflight.conservative_cost) if preflight.conservative_cost is not None else None)
            if not preflight.succeeded:
                classification = f"preflight_{preflight.error_classification.value}"
                failure_stage = "token_preflight"
                raise StageBPilotError(classification, audit_path)
            if preflight.conservative_cost is None or preflight.conservative_cost > MAXIMUM_SPEND:
                classification = "budget_rejection"
                failure_stage = "preflight_budget"
                raise StageBPilotError(classification, audit_path)
            evidence = StageBPreflightEvidence(construction_token=_EVIDENCE_TOKEN, authorization=authorization, request=provider_request, preflight=preflight, audit_record_path=audit_path, attempt_token=attempt_token)
            consumed = evidence.consume(authorization=authorization, request=provider_request, audit_record_path=audit_path, attempt_token=attempt_token, now=now())
            state["generation_attempted"] = True
            result = transport.generate(provider_request, consumed)
            state.update(generation_duration_ms=result.generation_duration_ms, total_duration_ms=result.duration_ms, input_tokens=result.input_tokens, output_tokens=result.output_tokens, cached_input_tokens=result.cached_input_tokens, uncached_input_tokens=result.uncached_input_tokens, estimated_cost=result.estimated_cost, cache_status=result.cache_status, provider_request_id=result.provider_request_id, provider_reported_model_identifier=result.provider_model_identifier, finish_status=result.finish_status, refusal_status=result.refusal_status, incomplete_reason=result.incomplete_reason)
            if result.error_classification is not None:
                classification = f"generation_{result.error_classification.value}"
                failure_stage = "generation"
                raise StageBPilotError(classification, audit_path)
            if result.provider_model_identifier not in {None, OPENAI_MODEL_IDENTIFIER}:
                classification = "provider_schema_failure"
                failure_stage = "provider_response"
                raise StageBPilotError(classification, audit_path)
            if Decimal(result.estimated_cost.removeprefix("$")) > MAXIMUM_SPEND:
                classification = "budget_rejection"
                failure_stage = "generation_budget"
                raise StageBPilotError(classification, audit_path)
            raw = parse_untrusted_response(result.response_content)
            try:
                response = MovingServiceQuestionResponse.model_validate(raw)
            except ValidationError as error:
                classification = "pydantic_validation_failure"
                failure_stage = "pydantic_validation"
                raise StageBPilotError(classification, audit_path) from error
            state["pydantic_validation_succeeded"] = True
            try:
                validated = validate_response(request, raw)
            except ResponseValidationError as error:
                classification = "semantic_validation_failure"
                failure_stage = "semantic_validation"
                raise StageBPilotError(classification, audit_path) from error
            state["semantic_validation_succeeded"] = True
            state["generation_succeeded"] = True
            evidence_data = validated.model_dump(mode="json")
            _write_json_exclusive(evidence_path, evidence_data)
            evidence_bytes = evidence_path.read_bytes()
            state["response_evidence_path"] = str(evidence_path)
            state["response_evidence_sha256"] = hashlib.sha256(evidence_bytes).hexdigest()
            state["response_evidence_delete_by"] = (now() + timedelta(days=30)).replace(microsecond=0).isoformat().replace("+00:00", "Z")
            state["normalized_question_text"] = normalize_question_text(validated.suggestions[0].question) if validated.suggestions else None
            state["referenced_knowledge_ids"] = tuple(sorted({knowledge_id for suggestion in validated.suggestions for knowledge_id in suggestion.relevant_knowledge_ids}))
    except StageBPilotError:
        raise
    except CredentialBoundaryError as error:
        classification = (
            "client_construction_failure"
            if isinstance(error, OpenAIClientConstructionError)
            else "credential_failure"
            if isinstance(error, EvaluationCredentialError)
            else "authorization_failure"
            if isinstance(error, CredentialAccessNotAuthorizedError)
            else "credential_boundary_failure"
        )
        failure_stage = "client_construction" if isinstance(error, OpenAIClientConstructionError) else "credential_lookup"
        if isinstance(error, OpenAIClientConstructionError):
            state["credential_value_obtained"] = True
        raise StageBPilotError(classification, audit_path) from error
    except OpenAIBudgetGateError as error:
        classification = "budget_rejection"
        failure_stage = "preflight_budget"
        raise StageBPilotError(classification, audit_path) from error
    except OpenAIPreflightGateError as error:
        classification = "preflight_evidence_or_budget_failure"
        failure_stage = "preflight_evidence"
        raise StageBPilotError(classification, audit_path) from error
    except ResponseValidationError as error:
        classification = (
            "refusal" if isinstance(error, OpenAIRefusalError)
            else "incomplete_output" if isinstance(error, OpenAIIncompleteResponseError)
            else "provider_schema_failure" if isinstance(error, OpenAIProviderSchemaError)
            else "malformed_json"
        )
        failure_stage = "provider_response"
        raise StageBPilotError(classification, audit_path) from error
    except Exception as error:
        classification = "unexpected_post_reservation_failure"
        failure_stage = "unexpected"
        raise StageBPilotError(classification, audit_path) from error
    finally:
        record = StageBAuditRecord(run_series_id=RUN_SERIES_ID, run_sequence=SEQUENCE, fixture_id=FIXTURE_ID, capability=CAPABILITY, authorization_version=AUTHORIZATION_VERSION, authorization_digest=authorization.digest, prompt_version="moving-service-questions-prompt-v1", prompt_digest=FROZEN_PROMPT_DIGEST, request_schema_version="moving-service-questions-schema-v1", response_schema_version="moving-service-questions-schema-v1", knowledge_fixture_version="moving-service-storage-fixture-v2", run_configuration_digest=OPENAI_RUN_CONFIGURATION_DIGEST, provider_schema_digest=OPENAI_RESPONSE_SCHEMA_DIGEST, provider="OpenAI", ai_model_identifier=OPENAI_MODEL_IDENTIFIER, sdk_version="2.45.0", bounded_failure_classification=classification, failure_stage=failure_stage, fallback_used=False, **state)
        json.dump(asdict(record), output, indent=2, sort_keys=True)
        output.write("\n")
        output.close()
    return record


def run_stage_b_generation_pilot(*, environment: Mapping[str, str], operator_intent: str, run_series_id: str = RUN_SERIES_ID, sequence: int = SEQUENCE, fixture_id: str = FIXTURE_ID, output_root: Path = DEFAULT_OUTPUT_ROOT, manifest_path: Path = DEFAULT_MANIFEST_PATH) -> StageBAuditRecord:
    """Public path; the committed closed manifest rejects before environment access."""
    if manifest_path.resolve() != DEFAULT_MANIFEST_PATH.resolve():
        raise OfflineRunnerGateError("Stage B requires the repository manifest.")
    try:
        authorization = load_manifest_bound_stage_b_authorization(manifest_path, repository_root=REPOSITORY_ROOT)
    except StageBAuthorizationError as error:
        raise OfflineRunnerGateError(str(error)) from error
    if (run_series_id, sequence, fixture_id) != (RUN_SERIES_ID, SEQUENCE, FIXTURE_ID):
        raise OfflineRunnerGateError("Stage B accepts only the exact approved slot.")
    resolved = _validate_output_root(output_root, allow_temporary_test_output=False)
    audit, evidence = _paths(resolved)
    if audit.exists() or evidence.exists():
        raise FileExistsError("The Stage B slot or evidence already exists.")
    if operator_intent != OPERATOR_INTENT:
        raise OfflineRunnerGateError("Stage B operator intent is not confirmed.")
    _require_exact_enablement(environment)
    return _execute_stage_b(authorization=authorization, manifest_path=manifest_path, environment=environment, output_root=resolved, client_builder=build_stage_b_moving_service_openai_client_with_pinned_sdk)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the one authorized moving-service Stage B pilot.")
    parser.add_argument("--run-series", required=True, choices=[RUN_SERIES_ID])
    parser.add_argument("--sequence", required=True, type=int, choices=[SEQUENCE])
    parser.add_argument("--fixture", required=True, choices=[FIXTURE_ID])
    parser.add_argument("--operator-intent", required=True, choices=[OPERATOR_INTENT])
    arguments = parser.parse_args()
    run_stage_b_generation_pilot(environment=os.environ, operator_intent=arguments.operator_intent, run_series_id=arguments.run_series, sequence=arguments.sequence, fixture_id=arguments.fixture)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
