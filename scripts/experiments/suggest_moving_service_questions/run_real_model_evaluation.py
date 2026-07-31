"""Script-only offline runner for suggest_moving_service_questions.

Milestone 1 accepts only OfflineFakeMovingServiceTransport and cannot contact a
provider or read credentials.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import tomllib
from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path
from time import perf_counter
from typing import Mapping

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = REPOSITORY_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.moving_service_questions import (  # noqa: E402
    CAPABILITY,
    KNOWLEDGE_VERSION,
    PROMPT_VERSION,
    SCHEMA_VERSION,
    AdapterTimeoutError,
    AdapterUnavailableError,
    ExperimentFixture,
    ResponseValidationError,
    build_trusted_fixture,
    construct_request,
    normalize_question_text,
    select_fallback,
    validate_response,
)

from real_model_adapter import (  # noqa: E402
    FROZEN_PROMPT_DIGEST,
    OfflineFakeMovingServiceTransport,
    RealModelMovingServiceQuestionAdapter,
)

DEFAULT_PROMPT_PATH = (
    REPOSITORY_ROOT
    / "docs/experiments/suggest-moving-service-questions/v1/real-model-prompt.toml"
)
DEFAULT_MANIFEST_PATH = (
    REPOSITORY_ROOT
    / "docs/experiments/suggest-moving-service-questions/v1/manifest.json"
)
DEFAULT_EXECUTION_AUTHORIZATION_PATH = (
    REPOSITORY_ROOT
    / "docs/experiments/suggest-moving-service-questions/v1/"
    "openai-execution-authorization.toml"
)
FROZEN_EXECUTION_AUTHORIZATION_DIGEST = (
    "6e3ca9cb4488764f012703ab77daae4f4b952895100f7d935935aeb6a0978be5"
)
FROZEN_RUN_CONFIGURATION_DIGEST = (
    "e665e04b56d8aeaa01f4c9df2fd2f5f4eed37150802fdba869cba54d1e5bc782"
)
FROZEN_PROVIDER_SCHEMA_DIGEST = (
    "9e5a3a667a1049d150734fd16669dad98cc982c2dc7a9a18f3e0b8cb3e891afb"
)
DEFAULT_OUTPUT_ROOT = (
    REPOSITORY_ROOT
    / ".local/evaluations/suggest-moving-service-questions"
)
OFFLINE_MODEL_IDENTIFIER = "offline-test-model"
ALLOWED_FIXTURES = frozenset(
    {ExperimentFixture.STORAGE_UNKNOWN, ExperimentFixture.COMPLETE}
)
RUN_SERIES_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
MAXIMUM_RUN_SEQUENCE = 20


class OfflineRunnerGateError(ValueError):
    pass


class ExecutionStage(StrEnum):
    TOKEN_PREFLIGHT = "token_preflight"
    AI_GENERATION = "ai_generation"
    FORMAL_EVALUATION = "formal_evaluation"


def require_execution_stage_authorized(
    authorization: Mapping[str, object],
    stage: ExecutionStage,
) -> None:
    """Require the exact, minimally scoped permission pattern for one stage."""
    permissions = authorization.get("authorization")
    if not isinstance(permissions, Mapping):
        raise OfflineRunnerGateError("Execution authorization is missing permissions.")
    expected_fields = {
        "credential_access_authorized",
        "token_preflight_authorized",
        "ai_generation_authorized",
        "formal_evaluation_authorized",
    }
    if set(permissions) != expected_fields:
        raise OfflineRunnerGateError("Execution permission fields are incompatible.")
    expected_by_stage = {
        ExecutionStage.TOKEN_PREFLIGHT: {
            "credential_access_authorized": True,
            "token_preflight_authorized": True,
            "ai_generation_authorized": False,
            "formal_evaluation_authorized": False,
        },
        ExecutionStage.AI_GENERATION: {
            "credential_access_authorized": True,
            "token_preflight_authorized": True,
            "ai_generation_authorized": True,
            "formal_evaluation_authorized": False,
        },
        ExecutionStage.FORMAL_EVALUATION: {
            "credential_access_authorized": True,
            "token_preflight_authorized": True,
            "ai_generation_authorized": True,
            "formal_evaluation_authorized": True,
        },
    }
    if dict(permissions) != expected_by_stage[stage]:
        raise OfflineRunnerGateError(
            f"Repository authorization does not permit {stage.value}."
        )


@dataclass(frozen=True)
class OfflineRunnerAuthorization:
    adapter_implementation_authorized: bool
    real_model_execution_authorized: bool = False


@dataclass(frozen=True)
class OfflineEvaluationRecord:
    run_series_id: str
    run_sequence: int
    fixture_id: str
    capability: str
    prompt_version: str
    prompt_artifact_digest: str
    schema_version: str
    knowledge_version: str
    scenario_version: str
    fallback_version: str
    model_identifier: str
    model_parameters: Mapping[str, object]
    input_tokens: int | None
    output_tokens: int | None
    estimated_cost: str
    duration_ms: float
    schema_valid: bool | None
    validation_error_code: str | None
    referenced_knowledge_ids: tuple[str, ...]
    fallback_used: bool
    fallback_reason: str | None
    normalized_question_text: str | None
    cache_status: str
    hard_gate_results: tuple[str, ...]
    human_review_scores: None = None
    human_review_notes: None = None

    def as_json_data(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class OfflineRunResult:
    record: OfflineEvaluationRecord
    record_path: Path


def _load_verified_manifest(path: Path) -> dict[str, object]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    expected = {
        "capability": CAPABILITY,
        "prompt_version": PROMPT_VERSION,
        "schema_version": SCHEMA_VERSION,
        "knowledge_fixture_version": KNOWLEDGE_VERSION,
        "prompt_artifact_path": (
            "docs/experiments/suggest-moving-service-questions/v1/"
            "real-model-prompt.toml"
        ),
        "prompt_artifact_digest_algorithm": "sha256",
        "prompt_artifact_digest": FROZEN_PROMPT_DIGEST,
        "prompt_artifact_reviewed": True,
        "prompt_artifact_frozen_for_adapter_implementation": True,
        "openai_run_configuration_path": (
            "docs/experiments/suggest-moving-service-questions/v1/"
            "openai-run-configuration.toml"
        ),
        "openai_run_configuration_digest_algorithm": "sha256",
        "openai_run_configuration_digest": FROZEN_RUN_CONFIGURATION_DIGEST,
        "openai_response_schema_path": (
            "docs/experiments/suggest-moving-service-questions/v1/"
            "openai-response-schema.json"
        ),
        "openai_response_schema_digest_algorithm": "sha256",
        "openai_response_schema_digest": FROZEN_PROVIDER_SCHEMA_DIGEST,
        "openai_execution_authorization_path": (
            "docs/experiments/suggest-moving-service-questions/v1/"
            "openai-execution-authorization.toml"
        ),
        "openai_execution_authorization_version": (
            "moving-service-openai-execution-authorization-v1"
        ),
        "openai_execution_authorization_digest_algorithm": "sha256",
        "openai_execution_authorization_digest": (
            FROZEN_EXECUTION_AUTHORIZATION_DIGEST
        ),
        "openai_execution_authorization_status": (
            "closed_no_execution_authorized"
        ),
        "contract_artifacts_ready": True,
        "adapter_implementation_authorized": False,
        "real_model_execution_authorized": False,
        "real_model_evaluation_eligible": False,
    }
    for field, expected_value in expected.items():
        if manifest.get(field) != expected_value:
            raise OfflineRunnerGateError(f"Manifest field {field} is incompatible.")
    return manifest


def _load_verified_execution_authorization(
    path: Path,
    manifest: Mapping[str, object],
) -> dict[str, object]:
    """Verify the repository authority before any secret or network boundary."""
    artifact_bytes = path.read_bytes()
    digest = hashlib.sha256(artifact_bytes).hexdigest()
    if digest != FROZEN_EXECUTION_AUTHORIZATION_DIGEST:
        raise OfflineRunnerGateError("Execution-authorization digest is incompatible.")
    if digest != manifest["openai_execution_authorization_digest"]:
        raise OfflineRunnerGateError("Manifest authorization digest is incompatible.")

    artifact = tomllib.loads(artifact_bytes.decode("utf-8"))
    expected_sections = {
        "metadata", "bindings", "authorization", "scope", "policy", "validation"
    }
    if set(artifact) != expected_sections:
        raise OfflineRunnerGateError("Execution-authorization sections are incompatible.")

    metadata = artifact["metadata"]
    if metadata != {
        "capability": CAPABILITY,
        "authorization_version": "moving-service-openai-execution-authorization-v1",
        "authorization_status": "closed_no_execution_authorized",
        "created_date": "2026-07-31",
        "evaluation_only": True,
        "default_deny": True,
    }:
        raise OfflineRunnerGateError("Execution-authorization metadata is incompatible.")

    bindings = artifact["bindings"]
    expected_bindings = {
        "prompt_artifact_path": manifest["prompt_artifact_path"],
        "prompt_version": PROMPT_VERSION,
        "prompt_digest_algorithm": "sha256",
        "prompt_digest": FROZEN_PROMPT_DIGEST,
        "run_configuration_path": manifest["openai_run_configuration_path"],
        "run_configuration_digest_algorithm": "sha256",
        "run_configuration_digest": FROZEN_RUN_CONFIGURATION_DIGEST,
        "provider_schema_path": manifest["openai_response_schema_path"],
        "provider_schema_digest_algorithm": "sha256",
        "provider_schema_digest": FROZEN_PROVIDER_SCHEMA_DIGEST,
        "request_schema_version": SCHEMA_VERSION,
        "response_schema_version": SCHEMA_VERSION,
        "knowledge_fixture_version": KNOWLEDGE_VERSION,
        "provider": "OpenAI",
        "ai_model_identifier": "gpt-4.1-mini-2025-04-14",
        "sdk_pin": "openai==2.45.0",
    }
    if bindings != expected_bindings:
        raise OfflineRunnerGateError("Execution-authorization bindings are incompatible.")
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
                "Execution-authorization binding escapes the repository."
            ) from error
        bound_digest = hashlib.sha256(bound_path.read_bytes()).hexdigest()
        if bound_digest != bindings[digest_field]:
            raise OfflineRunnerGateError(
                f"Bound artifact {path_field} digest is incompatible."
            )

    authorization = artifact["authorization"]
    if authorization != {
        "credential_access_authorized": False,
        "token_preflight_authorized": False,
        "ai_generation_authorized": False,
        "formal_evaluation_authorized": False,
    }:
        raise OfflineRunnerGateError("Execution authorization is not closed.")
    if artifact["scope"] != {
        "authorized_run_series_id": "",
        "authorized_sequence_numbers": [],
        "authorized_fixture_ids": [],
        "maximum_authorized_spend": "0.00",
        "approval_date": "not_authorized",
        "expiration_date": "not_authorized",
        "approved_by": "none",
    }:
        raise OfflineRunnerGateError("Execution-authorization scope is not closed.")

    policy = artifact["policy"]
    false_policy = {
        "operator_intent_is_authority",
        "environment_values_may_override_authorization",
        "command_line_flags_may_override_authorization",
    }
    true_policy = {
        "missing_or_unknown_fields_fail_closed",
        "authorization_changes_require_human_review",
        "authorization_changes_require_new_digest",
        "authorization_changes_require_manifest_update",
        "credential_access_requires_all_non_secret_gates",
        "token_preflight_requires_credential_access_authorization",
        "ai_generation_requires_successful_token_preflight",
        "formal_evaluation_requires_ai_generation_authorization",
    }
    if set(policy) != false_policy | true_policy or any(policy[key] for key in false_policy):
        raise OfflineRunnerGateError("Execution-authorization override policy is unsafe.")
    if not all(policy[key] is True for key in true_policy):
        raise OfflineRunnerGateError("Execution-authorization prerequisites are incomplete.")
    if artifact["validation"] != {
        "non_secret_gate_order": [
            "artifact_integrity",
            "repository_authorization",
            "fixture_and_sequence_validation",
            "output_path_checks",
            "budget_checks",
            "operator_intent_check",
        ],
        "first_secret_stage": "credential_access",
        "first_network_stage": "token_preflight",
        "generation_stage": "possible_generation",
    }:
        raise OfflineRunnerGateError("Execution-authorization gate order is incompatible.")
    return artifact


def _validate_fixture(fixture_id: str) -> ExperimentFixture:
    try:
        fixture = ExperimentFixture(fixture_id)
    except ValueError as error:
        raise OfflineRunnerGateError("Fixture is not recognized.") from error
    if fixture not in ALLOWED_FIXTURES:
        raise OfflineRunnerGateError("Fixture is not model-quality allowlisted.")
    return fixture


def _validate_run_identity(run_series_id: str, run_sequence: int) -> None:
    if not RUN_SERIES_PATTERN.fullmatch(run_series_id):
        raise OfflineRunnerGateError("Run-series ID is invalid.")
    if not 1 <= run_sequence <= MAXIMUM_RUN_SEQUENCE:
        raise OfflineRunnerGateError("Run sequence is outside the frozen range.")


def _validate_output_root(
    output_root: Path,
    *,
    allow_temporary_test_output: bool,
) -> Path:
    resolved = output_root.resolve()
    approved = DEFAULT_OUTPUT_ROOT.resolve()
    if not allow_temporary_test_output:
        try:
            resolved.relative_to(approved)
        except ValueError as error:
            raise OfflineRunnerGateError(
                "Output directory is outside the approved ignored path."
            ) from error
        ignored_entry = ".local/evaluations/"
        ignore_lines = {
            line.strip()
            for line in (REPOSITORY_ROOT / ".gitignore").read_text().splitlines()
        }
        if ignored_entry not in ignore_lines:
            raise OfflineRunnerGateError("Approved output directory is not ignored.")
    return resolved


def _estimated_input_tokens(system_instructions: str, request_json: str) -> int:
    return (len(system_instructions) + len(request_json) + 3) // 4


def write_record_exclusively(
    record: OfflineEvaluationRecord,
    output_root: Path,
) -> Path:
    series_directory = output_root / record.run_series_id
    series_directory.mkdir(parents=True, exist_ok=True)
    record_path = (
        series_directory
        / f"{record.run_sequence:03d}-{record.fixture_id}.json"
    )
    with record_path.open("x", encoding="utf-8") as output:
        json.dump(record.as_json_data(), output, indent=2, sort_keys=True)
        output.write("\n")
    return record_path


def _record_path(
    output_root: Path,
    run_series_id: str,
    run_sequence: int,
    fixture_id: str,
) -> Path:
    return (
        output_root
        / run_series_id
        / f"{run_sequence:03d}-{fixture_id}.json"
    )


def run_offline_evaluation(
    *,
    fixture_id: str,
    run_series_id: str,
    run_sequence: int,
    adapter: RealModelMovingServiceQuestionAdapter,
    authorization: OfflineRunnerAuthorization,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
    execution_authorization_path: Path = DEFAULT_EXECUTION_AUTHORIZATION_PATH,
    allow_temporary_test_output: bool = False,
) -> OfflineRunResult:
    """Run one network-incapable fake invocation and write a bounded record."""
    manifest = _load_verified_manifest(manifest_path)
    _load_verified_execution_authorization(execution_authorization_path, manifest)

    if authorization.adapter_implementation_authorized is not True:
        raise OfflineRunnerGateError("Offline adapter implementation is not authorized.")
    if authorization.real_model_execution_authorized is not False:
        raise OfflineRunnerGateError("Real-model execution must remain unauthorized.")
    if type(adapter.transport) is not OfflineFakeMovingServiceTransport:
        raise OfflineRunnerGateError("Milestone 1 permits only the offline fake transport.")
    if adapter.model_identifier != OFFLINE_MODEL_IDENTIFIER:
        raise OfflineRunnerGateError("Milestone 1 permits only the offline model label.")
    if adapter.model_parameters:
        raise OfflineRunnerGateError("Milestone 1 model parameters must be empty.")
    if adapter.prompt_artifact_path.resolve() != DEFAULT_PROMPT_PATH.resolve():
        raise OfflineRunnerGateError("Only the frozen prompt path is permitted.")

    fixture = _validate_fixture(fixture_id)
    _validate_run_identity(run_series_id, run_sequence)
    resolved_output_root = _validate_output_root(
        output_root,
        allow_temporary_test_output=allow_temporary_test_output,
    )
    if _record_path(
        resolved_output_root,
        run_series_id,
        run_sequence,
        fixture.value,
    ).exists():
        raise FileExistsError("The offline evaluation record already exists.")

    request = construct_request(build_trusted_fixture(fixture))
    provider_request = adapter.prepare_request(request)
    estimated_input_tokens = _estimated_input_tokens(
        provider_request.system_instructions,
        provider_request.deterministic_request_json,
    )
    if estimated_input_tokens > 3_000:
        raise OfflineRunnerGateError("Estimated input exceeds 3,000 tokens.")

    started_at = perf_counter()
    schema_valid: bool | None = None
    validation_error_code: str | None = None
    fallback_reason: str | None = None
    response = None
    transport_result = None
    try:
        invocation = adapter.invoke_prepared(provider_request)
        transport_result = invocation.transport_result
        response = validate_response(request, invocation.raw_response)
        schema_valid = True
    except AdapterUnavailableError:
        validation_error_code = "adapter_unavailable"
        fallback_reason = "adapter_unavailable"
    except AdapterTimeoutError:
        validation_error_code = "adapter_timeout"
        fallback_reason = "adapter_timeout"
    except ResponseValidationError:
        schema_valid = False
        validation_error_code = "invalid_adapter_response"
        fallback_reason = "invalid_adapter_response"

    fallback = select_fallback(request) if response is None else None
    fallback_used = fallback is not None
    referenced_knowledge_ids: tuple[str, ...] = ()
    normalized_question: str | None = None
    if response is not None and response.suggestions:
        referenced_knowledge_ids = tuple(
            knowledge_id
            for suggestion in response.suggestions
            for knowledge_id in suggestion.relevant_knowledge_ids
        )
        normalized_question = normalize_question_text(response.suggestions[0].question)
    elif fallback is not None:
        referenced_knowledge_ids = fallback.relevant_knowledge_ids

    record = OfflineEvaluationRecord(
        run_series_id=run_series_id,
        run_sequence=run_sequence,
        fixture_id=fixture.value,
        capability=CAPABILITY,
        prompt_version=PROMPT_VERSION,
        prompt_artifact_digest=FROZEN_PROMPT_DIGEST,
        schema_version=SCHEMA_VERSION,
        knowledge_version=KNOWLEDGE_VERSION,
        scenario_version=str(manifest["scenario_version"]),
        fallback_version=str(manifest["fallback_version"]),
        model_identifier=adapter.model_identifier,
        model_parameters=adapter.model_parameters,
        input_tokens=(
            transport_result.input_tokens if transport_result is not None else None
        ),
        output_tokens=(
            transport_result.output_tokens if transport_result is not None else None
        ),
        estimated_cost="$0.00",
        duration_ms=round((perf_counter() - started_at) * 1_000, 3),
        schema_valid=schema_valid,
        validation_error_code=validation_error_code,
        referenced_knowledge_ids=referenced_knowledge_ids,
        fallback_used=fallback_used,
        fallback_reason=fallback_reason,
        normalized_question_text=normalized_question,
        cache_status=(
            transport_result.cache_status
            if transport_result is not None
            else "not_available"
        ),
        hard_gate_results=(
            "execution_authorization_verified_closed",
            "offline_authorization_passed",
            "real_model_execution_unauthorized",
            "frozen_prompt_verified",
            "fixture_allowlisted",
            "input_size_passed",
            "offline_fake_transport_only",
        ),
    )
    record_path = write_record_exclusively(record, resolved_output_root)
    return OfflineRunResult(record=record, record_path=record_path)
