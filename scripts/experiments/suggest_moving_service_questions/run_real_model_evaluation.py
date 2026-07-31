"""Script-only offline runner for suggest_moving_service_questions.

Milestone 1 accepts only OfflineFakeMovingServiceTransport and cannot contact a
provider or read credentials.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import asdict, dataclass
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
        "contract_artifacts_ready": True,
        "adapter_implementation_authorized": False,
        "real_model_execution_authorized": False,
        "real_model_evaluation_eligible": False,
    }
    for field, expected_value in expected.items():
        if manifest.get(field) != expected_value:
            raise OfflineRunnerGateError(f"Manifest field {field} is incompatible.")
    return manifest


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
    allow_temporary_test_output: bool = False,
) -> OfflineRunResult:
    """Run one network-incapable fake invocation and write a bounded record."""
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

    manifest = _load_verified_manifest(manifest_path)
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
