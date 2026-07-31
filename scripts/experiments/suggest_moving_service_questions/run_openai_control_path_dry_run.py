"""End-to-end, in-memory dry run of the closed OpenAI control path.

This module has no command-line entry point. It accepts only the concrete fake
environment and fake constructors defined here. Repository authorization must
remain fully closed; all secret and external stages are simulations.
"""

from __future__ import annotations

import json
import sys
import tomllib
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Mapping

SCRIPT_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = REPOSITORY_ROOT / "backend"
for import_path in (SCRIPT_ROOT, BACKEND_ROOT):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from app.moving_service_questions import (  # noqa: E402
    CAPABILITY,
    KNOWLEDGE_VERSION,
    PROMPT_VERSION,
    SCHEMA_VERSION,
    ExperimentFixture,
    ResponseValidationError,
    build_trusted_fixture,
    construct_request,
    validate_response,
)
from openai_client_factory import (  # noqa: E402
    EVALUATION_CREDENTIAL_NAME,
    OPENAI_SDK_VERSION,
    _construct_openai_client,
    _read_evaluation_credential,
)
from openai_transport import (  # noqa: E402
    DEFAULT_RUN_CONFIGURATION_PATH,
    OPENAI_MODEL_IDENTIFIER,
    OpenAIMovingServiceEvaluationTransport,
    OpenAIPreflightGateError,
)
from real_model_adapter import (  # noqa: E402
    FROZEN_PROMPT_DIGEST,
    RealModelMovingServiceQuestionAdapter,
)
from run_real_model_evaluation import (  # noqa: E402
    DEFAULT_EXECUTION_AUTHORIZATION_PATH,
    DEFAULT_MANIFEST_PATH,
    DEFAULT_PROMPT_PATH,
    _load_verified_execution_authorization,
    _load_verified_manifest,
    _record_path,
    _validate_fixture,
    _validate_output_root,
    _validate_run_identity,
)

OFFLINE_SYNTHETIC_CREDENTIAL = "gotime-offline-synthetic-not-a-real-key"
DRY_RUN_MODE = "closed_authorization_in_memory_simulation"


class OfflineControlPathError(ValueError):
    """The offline control-path harness failed closed."""


@dataclass(frozen=True)
class OfflineOpenAIScenario:
    response: Mapping[str, object]
    exact_input_tokens: int = 100
    usage_input_tokens: int = 100
    cached_input_tokens: int = 0
    output_tokens: int = 30


class OfflineSyntheticEnvironment(dict[str, str]):
    """Fixed synthetic environment that cannot carry a caller-provided key."""

    def __init__(self) -> None:
        super().__init__({EVALUATION_CREDENTIAL_NAME: OFFLINE_SYNTHETIC_CREDENTIAL})


class OfflineFakeHttpClient:
    def __init__(self, *, trust_env: bool) -> None:
        self.trust_env = trust_env
        self.closed = False

    def close(self) -> None:
        self.closed = True


class OfflineFakeHttpClientConstructor:
    def __init__(self) -> None:
        self.clients: list[OfflineFakeHttpClient] = []

    def __call__(self, **kwargs: object) -> OfflineFakeHttpClient:
        if kwargs != {"trust_env": False}:
            raise OfflineControlPathError("Fake HTTP client arguments drifted.")
        client = OfflineFakeHttpClient(trust_env=False)
        self.clients.append(client)
        return client


class OfflineFakeInputTokens:
    def __init__(self, exact_input_tokens: int) -> None:
        self.exact_input_tokens = exact_input_tokens
        self.calls: list[dict[str, object]] = []

    def count(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        return SimpleNamespace(input_tokens=self.exact_input_tokens)


class OfflineFakeResponses:
    def __init__(self, scenario: OfflineOpenAIScenario) -> None:
        self.scenario = scenario
        self.input_tokens = OfflineFakeInputTokens(scenario.exact_input_tokens)
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        return SimpleNamespace(
            status="completed",
            output=[
                SimpleNamespace(
                    type="message",
                    content=[
                        SimpleNamespace(
                            type="output_text",
                            text=json.dumps(
                                self.scenario.response,
                                separators=(",", ":"),
                            ),
                        )
                    ],
                )
            ],
            usage=SimpleNamespace(
                input_tokens=self.scenario.usage_input_tokens,
                input_tokens_details=SimpleNamespace(
                    cached_tokens=self.scenario.cached_input_tokens
                ),
                output_tokens=self.scenario.output_tokens,
            ),
            model=OPENAI_MODEL_IDENTIFIER,
            _request_id="offline-fake-request",
            incomplete_details=None,
        )


class OfflineFakeOpenAIClient:
    def __init__(self, scenario: OfflineOpenAIScenario) -> None:
        self.max_retries = 0
        self.responses = OfflineFakeResponses(scenario)
        self.closed = False

    def close(self) -> None:
        self.closed = True


class OfflineFakeOpenAIClientConstructor:
    def __init__(self, scenarios: tuple[OfflineOpenAIScenario, ...]) -> None:
        self._scenarios = list(scenarios)
        self.calls: list[dict[str, object]] = []
        self.clients: list[OfflineFakeOpenAIClient] = []

    def __call__(self, **kwargs: object) -> OfflineFakeOpenAIClient:
        if not self._scenarios:
            raise OfflineControlPathError("No fake OpenAI scenario remains.")
        if kwargs.get("api_key") != OFFLINE_SYNTHETIC_CREDENTIAL:
            raise OfflineControlPathError("Only the synthetic credential is permitted.")
        self.calls.append(
            {key: value for key, value in kwargs.items() if key != "api_key"}
        )
        client = OfflineFakeOpenAIClient(self._scenarios.pop(0))
        self.clients.append(client)
        return client


@dataclass(frozen=True)
class OfflineControlPathRecord:
    dry_run_mode: str
    run_series_id: str
    run_sequence: int
    fixture_id: str
    capability: str
    prompt_version: str
    prompt_digest: str
    schema_version: str
    knowledge_version: str
    provider: str
    ai_model_identifier: str
    repository_authorization_closed: bool
    credential_access_authorized: bool
    token_preflight_authorized: bool
    ai_generation_authorized: bool
    formal_evaluation_authorized: bool
    credential_access_simulated: bool
    client_construction_simulated: bool
    preflight_attempted: bool
    preflight_succeeded: bool
    generation_attempted: bool
    generation_succeeded: bool
    response_schema_valid: bool
    input_tokens: int | None
    cached_input_tokens: int | None
    uncached_input_tokens: int | None
    output_tokens: int | None
    estimated_cost: str
    cumulative_series_cost: str
    cache_status: str
    provider_request_id: str | None
    failure_phase: str | None
    failure_code: str | None
    series_stopped: bool

    def as_json_data(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class OfflineControlPathSeriesResult:
    records: tuple[OfflineControlPathRecord, ...]
    record_paths: tuple[Path, ...]
    cumulative_cost: Decimal
    stopped: bool
    stop_reason: str | None


def _write_record_exclusively(record: OfflineControlPathRecord, root: Path) -> Path:
    series_directory = root / record.run_series_id
    series_directory.mkdir(parents=True, exist_ok=True)
    path = series_directory / (
        f"{record.run_sequence:03d}-{record.fixture_id}-openai-dry-run.json"
    )
    with path.open("x", encoding="utf-8") as output:
        json.dump(record.as_json_data(), output, indent=2, sort_keys=True)
        output.write("\n")
    return path


def _closed_permissions(authorization: Mapping[str, object]) -> dict[str, bool]:
    permissions = authorization["authorization"]
    if not isinstance(permissions, dict) or any(permissions.values()):
        raise OfflineControlPathError(
            "The dry run requires every repository permission to remain false."
        )
    return {key: bool(value) for key, value in permissions.items()}


def _frozen_run_order_and_budget() -> tuple[tuple[str, ...], Decimal]:
    configuration = tomllib.loads(
        DEFAULT_RUN_CONFIGURATION_PATH.read_text(encoding="utf-8")
    )
    return (
        tuple(configuration["fixtures"]["fixed_run_order"]),
        Decimal(configuration["pricing"]["maximum_formal_series_spend"]),
    )


def run_offline_openai_control_path_series(
    *,
    fixture_ids: tuple[str, ...],
    run_series_id: str,
    first_sequence: int,
    environment: OfflineSyntheticEnvironment,
    client_constructor: OfflineFakeOpenAIClientConstructor,
    http_client_constructor: OfflineFakeHttpClientConstructor,
    output_root: Path,
    allow_temporary_test_output: bool = False,
) -> OfflineControlPathSeriesResult:
    """Exercise the full external shape with only fixed in-memory fakes."""
    if type(environment) is not OfflineSyntheticEnvironment:
        raise OfflineControlPathError("Only the synthetic environment is permitted.")
    if type(client_constructor) is not OfflineFakeOpenAIClientConstructor:
        raise OfflineControlPathError("Only the fake client constructor is permitted.")
    if type(http_client_constructor) is not OfflineFakeHttpClientConstructor:
        raise OfflineControlPathError("Only the fake HTTP constructor is permitted.")
    if not fixture_ids:
        raise OfflineControlPathError("At least one dry-run slot is required.")

    manifest = _load_verified_manifest(DEFAULT_MANIFEST_PATH)
    authorization = _load_verified_execution_authorization(
        DEFAULT_EXECUTION_AUTHORIZATION_PATH,
        manifest,
    )
    permissions = _closed_permissions(authorization)
    frozen_order, maximum_series_spend = _frozen_run_order_and_budget()
    final_sequence = first_sequence + len(fixture_ids) - 1
    _validate_run_identity(run_series_id, first_sequence)
    _validate_run_identity(run_series_id, final_sequence)
    expected_fixtures = frozen_order[first_sequence - 1 : final_sequence]
    if fixture_ids != expected_fixtures:
        raise OfflineControlPathError("Dry-run fixtures do not match the frozen order.")
    fixtures = tuple(_validate_fixture(fixture_id) for fixture_id in fixture_ids)
    resolved_output_root = _validate_output_root(
        output_root,
        allow_temporary_test_output=allow_temporary_test_output,
    )

    records: list[OfflineControlPathRecord] = []
    record_paths: list[Path] = []
    cumulative_cost = Decimal("0")
    stopped = False
    stop_reason: str | None = None

    for offset, fixture in enumerate(fixtures):
        sequence = first_sequence + offset
        existing_standard_record = _record_path(
            resolved_output_root,
            run_series_id,
            sequence,
            fixture.value,
        )
        dry_record_path = resolved_output_root / run_series_id / (
            f"{sequence:03d}-{fixture.value}-openai-dry-run.json"
        )
        if existing_standard_record.exists() or dry_record_path.exists():
            raise FileExistsError("An evaluation record already occupies this slot.")
        if cumulative_cost >= maximum_series_spend:
            stopped = True
            stop_reason = "series_budget_exhausted"
            break

        request = construct_request(build_trusted_fixture(fixture))
        credential = _read_evaluation_credential(environment)
        owned_client = _construct_openai_client(
            credential,
            sdk_version=OPENAI_SDK_VERSION,
            client_constructor=client_constructor,
            http_client_constructor=http_client_constructor,
        )
        transport = OpenAIMovingServiceEvaluationTransport(client=owned_client.client)
        adapter = RealModelMovingServiceQuestionAdapter(
            model_identifier=OPENAI_MODEL_IDENTIFIER,
            model_parameters={"temperature": 0},
            transport=transport,
            prompt_artifact_path=DEFAULT_PROMPT_PATH,
        )

        transport_result = None
        preflight_attempted = False
        preflight_succeeded = False
        generation_attempted = False
        generation_succeeded = False
        response_schema_valid = False
        failure_phase: str | None = None
        failure_code: str | None = None
        try:
            prepared = adapter.prepare_request(request)
            preflight_attempted = True
            invocation = adapter.invoke_prepared(prepared)
            transport_result = invocation.transport_result
            preflight_succeeded = True
            generation_attempted = True
            validate_response(request, invocation.raw_response)
            response_schema_valid = True
            generation_succeeded = True
        except OpenAIPreflightGateError:
            failure_phase = "preflight"
            failure_code = "preflight_gate_rejected"
        except ResponseValidationError:
            preflight_succeeded = bool(
                owned_client.client.responses.input_tokens.calls
            )
            generation_attempted = bool(owned_client.client.responses.calls)
            failure_phase = "response_validation"
            failure_code = "invalid_ai_response"
        finally:
            fake_client = owned_client.client
            owned_client.close()

        if transport_result is not None:
            call_cost = Decimal(transport_result.estimated_cost.removeprefix("$"))
            cumulative_cost += call_cost
        else:
            call_cost = Decimal("0")
        if cumulative_cost > maximum_series_spend:
            failure_phase = "budget"
            failure_code = "series_budget_exceeded"
            generation_succeeded = False
            response_schema_valid = False

        record = OfflineControlPathRecord(
            dry_run_mode=DRY_RUN_MODE,
            run_series_id=run_series_id,
            run_sequence=sequence,
            fixture_id=fixture.value,
            capability=CAPABILITY,
            prompt_version=PROMPT_VERSION,
            prompt_digest=FROZEN_PROMPT_DIGEST,
            schema_version=SCHEMA_VERSION,
            knowledge_version=KNOWLEDGE_VERSION,
            provider="OpenAI",
            ai_model_identifier=OPENAI_MODEL_IDENTIFIER,
            repository_authorization_closed=True,
            credential_access_authorized=permissions[
                "credential_access_authorized"
            ],
            token_preflight_authorized=permissions["token_preflight_authorized"],
            ai_generation_authorized=permissions["ai_generation_authorized"],
            formal_evaluation_authorized=permissions[
                "formal_evaluation_authorized"
            ],
            credential_access_simulated=True,
            client_construction_simulated=True,
            preflight_attempted=preflight_attempted,
            preflight_succeeded=preflight_succeeded,
            generation_attempted=generation_attempted,
            generation_succeeded=generation_succeeded,
            response_schema_valid=response_schema_valid,
            input_tokens=(transport_result.input_tokens if transport_result else None),
            cached_input_tokens=(
                transport_result.cached_input_tokens if transport_result else None
            ),
            uncached_input_tokens=(
                transport_result.uncached_input_tokens if transport_result else None
            ),
            output_tokens=(
                transport_result.output_tokens if transport_result else None
            ),
            estimated_cost=f"${call_cost:.8f}",
            cumulative_series_cost=f"${cumulative_cost:.8f}",
            cache_status=(
                transport_result.cache_status
                if transport_result is not None
                else "not_available"
            ),
            provider_request_id=(
                transport_result.provider_request_id
                if transport_result is not None
                else None
            ),
            failure_phase=failure_phase,
            failure_code=failure_code,
            series_stopped=failure_code is not None,
        )
        records.append(record)
        record_paths.append(_write_record_exclusively(record, resolved_output_root))
        if failure_code is not None:
            stopped = True
            stop_reason = failure_code
            break
        if not fake_client.closed:
            raise OfflineControlPathError("Fake OpenAI client was not closed.")

    return OfflineControlPathSeriesResult(
        records=tuple(records),
        record_paths=tuple(record_paths),
        cumulative_cost=cumulative_cost,
        stopped=stopped,
        stop_reason=stop_reason,
    )
