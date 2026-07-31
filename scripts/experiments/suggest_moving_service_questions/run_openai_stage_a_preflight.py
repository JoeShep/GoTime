"""Fail-closed Stage A runner for one OpenAI token-preflight request.

The committed candidate authorization is not active repository authority, so
the public entry point currently stops before credential access, client
construction, or network access. This module contains no generation call.
"""

from __future__ import annotations

import hashlib
import json
import sys
import tomllib
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path
from typing import Callable, Mapping

SCRIPT_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = REPOSITORY_ROOT / "backend"
for import_path in (SCRIPT_ROOT, BACKEND_ROOT):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from app.moving_service_questions import (  # noqa: E402
    CAPABILITY,
    ExperimentFixture,
    build_trusted_fixture,
    construct_request,
)
from openai_client_factory import (  # noqa: E402
    REQUIRED_NON_SECRET_GATE_ORDER,
    MovingServiceOpenAIClient,
    build_moving_service_openai_client_with_pinned_sdk,
)
from openai_transport import (  # noqa: E402
    OPENAI_MODEL_IDENTIFIER,
    OpenAIMovingServiceEvaluationTransport,
    OpenAIPreflightResult,
)
from real_model_adapter import (  # noqa: E402
    DEFAULT_TIMEOUT_SECONDS,
    FROZEN_PROMPT_DIGEST,
    MovingServiceProviderRequest,
    RealModelMovingServiceQuestionAdapter,
)
from run_real_model_evaluation import (  # noqa: E402
    DEFAULT_MANIFEST_PATH,
    DEFAULT_OUTPUT_ROOT,
    ExecutionStage,
    OfflineRunnerGateError,
    _validate_output_root,
    require_execution_stage_authorized,
)

STAGE_A_CANDIDATE_PATH = (
    REPOSITORY_ROOT
    / "docs/experiments/suggest-moving-service-questions/v1/"
    "openai-stage-a-authorization-candidate.toml"
)
STAGE_A_CANDIDATE_DIGEST = (
    "b523426249b9c697f0ad8fa5c7e3cdc0d965db35c5ab5f8f1a7dc66fd4655202"
)
STAGE_A_AUTHORIZATION_VERSION = "moving-service-openai-stage-a-authorization-v1"
STAGE_A_RUN_SERIES_ID = "moving-service-stage-a-20260731"
STAGE_A_SEQUENCE = 1
STAGE_A_FIXTURE_ID = "storage_unknown"
STAGE_A_OPERATOR_INTENT = "AUTHORIZE_ONE_STORAGE_UNKNOWN_TOKEN_PREFLIGHT"
STAGE_A_MAXIMUM_GENERATION_SPEND = Decimal("0.00")


@dataclass(frozen=True)
class VerifiedStageACandidate:
    path: Path
    digest: str
    artifact: Mapping[str, object]


@dataclass(frozen=True)
class StageAPreflightAuditRecord:
    run_series_id: str
    run_sequence: int
    fixture_id: str
    capability: str
    authorization_version: str
    authorization_digest: str
    prompt_digest: str
    run_configuration_digest: str
    provider_schema_digest: str
    provider: str
    ai_model_identifier: str
    sdk_version: str
    preflight_attempted: bool
    preflight_succeeded: bool
    preflight_duration_ms: float
    input_tokens: int | None
    conservative_max_generation_cost: str | None
    bounded_failure_classification: str | None
    credential_accessed: bool
    client_constructed: bool
    generation_attempted: bool
    generation_succeeded: bool
    generation_spend: str
    formal_evaluation_attempted: bool

    def as_json_data(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class StageAPreflightResult:
    record: StageAPreflightAuditRecord
    record_path: Path


def _load_stage_a_candidate(path: Path = STAGE_A_CANDIDATE_PATH) -> VerifiedStageACandidate:
    artifact_bytes = path.read_bytes()
    digest = hashlib.sha256(artifact_bytes).hexdigest()
    if digest != STAGE_A_CANDIDATE_DIGEST:
        raise OfflineRunnerGateError("Stage A candidate digest is incompatible.")
    artifact = tomllib.loads(artifact_bytes.decode("utf-8"))
    if set(artifact) != {
        "metadata",
        "bindings",
        "authorization",
        "scope",
        "approval",
        "policy",
        "validation",
    }:
        raise OfflineRunnerGateError("Stage A candidate sections are incompatible.")
    metadata = artifact["metadata"]
    if metadata != {
        "capability": CAPABILITY,
        "authorization_version": STAGE_A_AUTHORIZATION_VERSION,
        "authorization_status": "candidate_pending_explicit_approval",
        "created_at": "2026-07-31T22:54:07Z",
        "evaluation_only": True,
        "default_deny": True,
        "active_repository_authority": False,
    }:
        raise OfflineRunnerGateError("Stage A candidate metadata is incompatible.")
    bindings = artifact["bindings"]
    expected_bindings = {
        "prompt_artifact_path": (
            "docs/experiments/suggest-moving-service-questions/v1/"
            "real-model-prompt.toml"
        ),
        "prompt_version": "moving-service-questions-prompt-v1",
        "prompt_digest_algorithm": "sha256",
        "prompt_digest": FROZEN_PROMPT_DIGEST,
        "run_configuration_path": (
            "docs/experiments/suggest-moving-service-questions/v1/"
            "openai-run-configuration.toml"
        ),
        "run_configuration_digest_algorithm": "sha256",
        "run_configuration_digest": (
            "e665e04b56d8aeaa01f4c9df2fd2f5f4eed37150802fdba869cba54d1e5bc782"
        ),
        "provider_schema_path": (
            "docs/experiments/suggest-moving-service-questions/v1/"
            "openai-response-schema.json"
        ),
        "provider_schema_digest_algorithm": "sha256",
        "provider_schema_digest": (
            "9e5a3a667a1049d150734fd16669dad98cc982c2dc7a9a18f3e0b8cb3e891afb"
        ),
        "request_schema_version": "moving-service-questions-schema-v1",
        "response_schema_version": "moving-service-questions-schema-v1",
        "knowledge_fixture_version": "moving-service-storage-fixture-v2",
        "provider": "OpenAI",
        "ai_model_identifier": OPENAI_MODEL_IDENTIFIER,
        "sdk_pin": "openai==2.45.0",
    }
    if bindings != expected_bindings:
        raise OfflineRunnerGateError("Stage A candidate bindings are incompatible.")
    for path_field, digest_field in (
        ("prompt_artifact_path", "prompt_digest"),
        ("run_configuration_path", "run_configuration_digest"),
        ("provider_schema_path", "provider_schema_digest"),
    ):
        bound_path = (REPOSITORY_ROOT / str(bindings[path_field])).resolve()
        try:
            bound_path.relative_to(REPOSITORY_ROOT.resolve())
        except ValueError as error:
            raise OfflineRunnerGateError(
                "Stage A artifact binding escapes the repository."
            ) from error
        if hashlib.sha256(bound_path.read_bytes()).hexdigest() != bindings[digest_field]:
            raise OfflineRunnerGateError(
                f"Stage A bound artifact {path_field} digest is incompatible."
            )
    require_execution_stage_authorized(artifact, ExecutionStage.TOKEN_PREFLIGHT)
    if artifact["scope"] != {
        "authorized_run_series_id": STAGE_A_RUN_SERIES_ID,
        "authorized_sequence_numbers": [STAGE_A_SEQUENCE],
        "authorized_fixture_ids": [STAGE_A_FIXTURE_ID],
        "maximum_authorized_generation_spend": "0.00",
        "maximum_credential_reads": 1,
        "maximum_client_constructions": 1,
        "maximum_token_preflight_requests": 1,
        "maximum_ai_generation_requests": 0,
    }:
        raise OfflineRunnerGateError("Stage A candidate scope is incompatible.")
    approval = artifact["approval"]
    if approval != {
        "approval_status": "pending_explicit_human_approval",
        "approved_at": "pending",
        "expires_at": "pending",
        "approved_by": "pending",
        "maximum_authorization_duration_seconds": 900,
        "activation_requires_new_final_artifact": True,
        "activation_requires_new_digest": True,
        "activation_requires_manifest_repoint": True,
    }:
        raise OfflineRunnerGateError("Stage A approval policy is incompatible.")
    if artifact["policy"] != {
        "operator_intent_is_authority": False,
        "environment_values_may_override_authorization": False,
        "command_line_flags_may_override_authorization": False,
        "missing_or_unknown_fields_fail_closed": True,
        "credential_access_requires_all_non_secret_gates": True,
        "token_preflight_requires_credential_access_authorization": True,
        "ai_generation_requires_successful_token_preflight": True,
        "formal_evaluation_requires_ai_generation_authorization": True,
        "authorization_is_single_use": True,
        "failure_consumes_sequence": True,
        "generation_method_must_be_unreachable": True,
    }:
        raise OfflineRunnerGateError("Stage A candidate policy is incompatible.")
    if artifact["validation"] != {
        "non_secret_gate_order": list(REQUIRED_NON_SECRET_GATE_ORDER),
        "first_secret_stage": "credential_access",
        "first_network_stage": "token_preflight",
        "generation_stage": "prohibited",
    }:
        raise OfflineRunnerGateError("Stage A gate order is incompatible.")
    return VerifiedStageACandidate(path=path, digest=digest, artifact=artifact)


def _require_manifest_activation(
    manifest_path: Path,
    candidate: VerifiedStageACandidate,
) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    candidate_path = (
        candidate.path.resolve().relative_to(REPOSITORY_ROOT.resolve()).as_posix()
    )
    candidate_expectations = {
        "openai_stage_a_authorization_candidate_path": candidate_path,
        "openai_stage_a_authorization_candidate_version": STAGE_A_AUTHORIZATION_VERSION,
        "openai_stage_a_authorization_candidate_digest_algorithm": "sha256",
        "openai_stage_a_authorization_candidate_digest": candidate.digest,
        "openai_stage_a_authorization_candidate_status": "candidate_pending_explicit_approval",
        "openai_stage_a_authorization_candidate_activated": False,
    }
    for field, expected in candidate_expectations.items():
        if manifest.get(field) != expected:
            raise OfflineRunnerGateError(f"Manifest Stage A field {field} is incompatible.")
    if manifest.get("openai_stage_a_authorization_candidate_activated") is not True:
        raise OfflineRunnerGateError("Stage A repository authorization is not active.")
    # Activation intentionally cannot pass with the committed candidate. A later
    # milestone must create a final approved artifact and repoint the manifest.


def _validate_exact_scope(
    *, fixture_id: str, run_series_id: str, run_sequence: int
) -> None:
    if (
        fixture_id != STAGE_A_FIXTURE_ID
        or run_series_id != STAGE_A_RUN_SERIES_ID
        or run_sequence != STAGE_A_SEQUENCE
    ):
        raise OfflineRunnerGateError("Requested operation is outside Stage A scope.")


def _record_path(output_root: Path) -> Path:
    return output_root / STAGE_A_RUN_SERIES_ID / "001-storage_unknown-preflight.json"


def _write_record_exclusively(
    record: StageAPreflightAuditRecord, output_root: Path
) -> Path:
    path = _record_path(output_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as output:
        json.dump(record.as_json_data(), output, indent=2, sort_keys=True)
        output.write("\n")
    return path


def _prepare_provider_request() -> MovingServiceProviderRequest:
    request = construct_request(build_trusted_fixture(ExperimentFixture.STORAGE_UNKNOWN))
    adapter = RealModelMovingServiceQuestionAdapter(
        model_identifier=OPENAI_MODEL_IDENTIFIER,
        model_parameters={"temperature": 0},
        transport=object(),  # request preparation does not invoke the transport
        prompt_artifact_path=(
            REPOSITORY_ROOT
            / "docs/experiments/suggest-moving-service-questions/v1/real-model-prompt.toml"
        ),
        expected_prompt_digest=FROZEN_PROMPT_DIGEST,
        timeout_seconds=DEFAULT_TIMEOUT_SECONDS,
    )
    return adapter.prepare_request(request)


def _execute_verified_stage_a_preflight(
    *,
    candidate: VerifiedStageACandidate,
    environment: Mapping[str, str],
    output_root: Path,
    client_builder: Callable[..., MovingServiceOpenAIClient],
) -> StageAPreflightResult:
    provider_request = _prepare_provider_request()
    preflight: OpenAIPreflightResult | None = None
    with client_builder(
        environment,
        completed_non_secret_gates=REQUIRED_NON_SECRET_GATE_ORDER,
        operator_intent_confirmed=True,
        authorization_path=candidate.path,
        expected_authorization_digest=candidate.digest,
    ) as owned_client:
        transport = OpenAIMovingServiceEvaluationTransport(client=owned_client.client)
        preflight = transport.preflight(provider_request)

    failure = (
        preflight.error_classification.value
        if preflight.error_classification is not None
        else None
    )
    record = StageAPreflightAuditRecord(
        run_series_id=STAGE_A_RUN_SERIES_ID,
        run_sequence=STAGE_A_SEQUENCE,
        fixture_id=STAGE_A_FIXTURE_ID,
        capability=CAPABILITY,
        authorization_version=STAGE_A_AUTHORIZATION_VERSION,
        authorization_digest=candidate.digest,
        prompt_digest=str(candidate.artifact["bindings"]["prompt_digest"]),
        run_configuration_digest=str(
            candidate.artifact["bindings"]["run_configuration_digest"]
        ),
        provider_schema_digest=str(
            candidate.artifact["bindings"]["provider_schema_digest"]
        ),
        provider="OpenAI",
        ai_model_identifier=OPENAI_MODEL_IDENTIFIER,
        sdk_version="2.45.0",
        preflight_attempted=True,
        preflight_succeeded=preflight.succeeded,
        preflight_duration_ms=preflight.duration_ms,
        input_tokens=preflight.input_tokens,
        conservative_max_generation_cost=(
            str(preflight.conservative_cost)
            if preflight.conservative_cost is not None
            else None
        ),
        bounded_failure_classification=failure,
        credential_accessed=True,
        client_constructed=True,
        generation_attempted=False,
        generation_succeeded=False,
        generation_spend="0.00",
        formal_evaluation_attempted=False,
    )
    return StageAPreflightResult(
        record=record,
        record_path=_write_record_exclusively(record, output_root),
    )


def run_stage_a_token_preflight(
    *,
    environment: Mapping[str, str],
    operator_intent: str,
    fixture_id: str = STAGE_A_FIXTURE_ID,
    run_series_id: str = STAGE_A_RUN_SERIES_ID,
    run_sequence: int = STAGE_A_SEQUENCE,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
) -> StageAPreflightResult:
    """Run Stage A only after a separately approved manifest activation."""
    candidate = _load_stage_a_candidate()
    _require_manifest_activation(manifest_path, candidate)
    _validate_exact_scope(
        fixture_id=fixture_id,
        run_series_id=run_series_id,
        run_sequence=run_sequence,
    )
    resolved_output = _validate_output_root(
        output_root, allow_temporary_test_output=False
    )
    if _record_path(resolved_output).exists():
        raise FileExistsError("The Stage A preflight record already exists.")
    authorized_generation_spend = Decimal(
        str(candidate.artifact["scope"]["maximum_authorized_generation_spend"])
    )
    if authorized_generation_spend != STAGE_A_MAXIMUM_GENERATION_SPEND:
        raise OfflineRunnerGateError("Stage A generation budget is not zero.")
    if operator_intent != STAGE_A_OPERATOR_INTENT:
        raise OfflineRunnerGateError("Stage A operator intent is not confirmed.")
    return _execute_verified_stage_a_preflight(
        candidate=candidate,
        environment=environment,
        output_root=resolved_output,
        client_builder=build_moving_service_openai_client_with_pinned_sdk,
    )
