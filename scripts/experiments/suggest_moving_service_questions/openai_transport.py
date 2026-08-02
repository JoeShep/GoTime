"""Offline-testable OpenAI transport for suggest_moving_service_questions.

This module constructs no SDK client, reads no credential, and is not admitted
by the evaluation runner. A caller must inject an SDK-shaped client explicitly.
"""

from __future__ import annotations

import hashlib
import json
import sys
import tomllib
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from time import perf_counter
from typing import Callable, Mapping, Protocol

import openai
from openai import APIConnectionError, APIStatusError, APITimeoutError, RateLimitError

SCRIPT_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = REPOSITORY_ROOT / "backend"
for import_path in (SCRIPT_ROOT, BACKEND_ROOT):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from app.moving_service_questions import (  # noqa: E402
    MAXIMUM_INPUT_TOKENS,
    ResponseValidationError,
)
from real_model_adapter import (  # noqa: E402
    MovingServiceProviderRequest,
    MovingServiceTransportResult,
    TransportErrorClassification,
)

OPENAI_PROVIDER_NAME = "OpenAI"
OPENAI_MODEL_IDENTIFIER = "gpt-4.1-mini-2025-04-14"
OPENAI_SDK_VERSION = "2.45.0"
OPENAI_RUN_CONFIGURATION_DIGEST = (
    "e665e04b56d8aeaa01f4c9df2fd2f5f4eed37150802fdba869cba54d1e5bc782"
)
OPENAI_RESPONSE_SCHEMA_DIGEST = (
    "9e5a3a667a1049d150734fd16669dad98cc982c2dc7a9a18f3e0b8cb3e891afb"
)
DEFAULT_RUN_CONFIGURATION_PATH = (
    REPOSITORY_ROOT
    / "docs/experiments/suggest-moving-service-questions/v1/"
    "openai-run-configuration.toml"
)
DEFAULT_RESPONSE_SCHEMA_PATH = (
    REPOSITORY_ROOT
    / "docs/experiments/suggest-moving-service-questions/v1/"
    "openai-response-schema.json"
)


class OpenAITransportArtifactError(ValueError):
    """A frozen OpenAI transport artifact is missing or incompatible."""


class OpenAIPreflightGateError(ValueError):
    """Exact input-token or conservative cost preflight failed closed."""


class OpenAIBudgetGateError(OpenAIPreflightGateError):
    """A frozen token or cost ceiling was exceeded."""


class OpenAIRefusalError(ResponseValidationError):
    """The provider returned a refusal instead of structured output."""


class OpenAIIncompleteResponseError(ResponseValidationError):
    """The provider reported incomplete generation."""


class OpenAIProviderSchemaError(ResponseValidationError):
    """The provider envelope or usage violated the reviewed contract."""


class OpenAIInputTokenCounter(Protocol):
    def count(self, **kwargs: object) -> object:
        ...


class OpenAIResponsesResource(Protocol):
    input_tokens: OpenAIInputTokenCounter

    def create(self, **kwargs: object) -> object:
        ...


class InjectedOpenAIClient(Protocol):
    responses: OpenAIResponsesResource
    max_retries: int


@dataclass(frozen=True)
class VerifiedOpenAITransportArtifacts:
    response_schema: Mapping[str, object]
    preflight_timeout_seconds: float
    generation_timeout_seconds: float
    maximum_per_call_spend: Decimal
    uncached_input_price_per_million: Decimal
    cached_input_price_per_million: Decimal
    output_price_per_million: Decimal


@dataclass(frozen=True)
class OpenAIPreflightResult:
    """Bounded, in-memory evidence for one exact prepared provider request."""

    request_fingerprint: str
    input_tokens: int | None
    duration_ms: float
    conservative_cost: Decimal | None
    error_classification: TransportErrorClassification | None = None

    @property
    def succeeded(self) -> bool:
        return (
            self.error_classification is None
            and self.input_tokens is not None
            and self.conservative_cost is not None
        )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _without_titles(value: object) -> object:
    if isinstance(value, dict):
        return {
            key: _without_titles(item)
            for key, item in value.items()
            if key != "title"
        }
    if isinstance(value, list):
        return [_without_titles(item) for item in value]
    return value


def load_verified_openai_transport_artifacts(
    *,
    run_configuration_path: Path = DEFAULT_RUN_CONFIGURATION_PATH,
    response_schema_path: Path = DEFAULT_RESPONSE_SCHEMA_PATH,
    expected_run_configuration_digest: str = OPENAI_RUN_CONFIGURATION_DIGEST,
    expected_response_schema_digest: str = OPENAI_RESPONSE_SCHEMA_DIGEST,
) -> VerifiedOpenAITransportArtifacts:
    """Verify frozen bytes and closed authorization before any injected call."""
    if _sha256(run_configuration_path) != expected_run_configuration_digest:
        raise OpenAITransportArtifactError(
            "Frozen OpenAI run-configuration digest does not match."
        )
    if _sha256(response_schema_path) != expected_response_schema_digest:
        raise OpenAITransportArtifactError(
            "Frozen OpenAI response-schema digest does not match."
        )
    try:
        configuration = tomllib.loads(
            run_configuration_path.read_text(encoding="utf-8")
        )
        response_schema = json.loads(
            response_schema_path.read_text(encoding="utf-8")
        )
    except (tomllib.TOMLDecodeError, json.JSONDecodeError) as error:
        raise OpenAITransportArtifactError(
            "Frozen OpenAI transport artifact is not parseable."
        ) from error

    status = configuration.get("status", {})
    required_status = {
        "configuration_status": "approved_and_frozen",
        "approved": True,
        "frozen": True,
        "provider_transport_implementation_authorized": False,
        "credentials_authorized": False,
        "real_model_execution_authorized": False,
        "production_use_authorized": False,
    }
    for field, expected in required_status.items():
        if status.get(field) != expected:
            raise OpenAITransportArtifactError(
                f"Frozen OpenAI authorization field {field} is incompatible."
            )

    identity = configuration.get("identity", {})
    model_parameters = configuration.get("model_parameters", {})
    transport = configuration.get("transport", {})
    contracts = configuration.get("contracts", {})
    pricing = configuration.get("pricing", {})
    expected_values = (
        (identity.get("provider"), OPENAI_PROVIDER_NAME, "provider"),
        (
            identity.get("ai_model_identifier"),
            OPENAI_MODEL_IDENTIFIER,
            "AI model identifier",
        ),
        (identity.get("sdk_pin"), f"openai=={OPENAI_SDK_VERSION}", "SDK pin"),
        (model_parameters.get("temperature"), 0, "temperature"),
        (model_parameters.get("maximum_output_tokens"), 500, "output limit"),
        (model_parameters.get("stream"), False, "stream setting"),
        (model_parameters.get("background"), False, "background setting"),
        (model_parameters.get("store"), False, "storage setting"),
        (model_parameters.get("tools_enabled"), False, "tool setting"),
        (transport.get("automatic_retries"), 0, "retry count"),
        (
            transport.get("structured_output_mode"),
            "strict_json_schema",
            "structured-output mode",
        ),
        (
            contracts.get("provider_schema_snapshot_status"),
            "reviewed_and_frozen",
            "provider-schema status",
        ),
    )
    for actual, expected, field in expected_values:
        if actual != expected:
            raise OpenAITransportArtifactError(
                f"Frozen OpenAI {field} is incompatible."
            )
    if not isinstance(response_schema, dict):
        raise OpenAITransportArtifactError("Frozen OpenAI response schema is invalid.")

    return VerifiedOpenAITransportArtifacts(
        response_schema=response_schema,
        preflight_timeout_seconds=float(
            transport["token_preflight_timeout_seconds"]
        ),
        generation_timeout_seconds=float(transport["generation_timeout_seconds"]),
        maximum_per_call_spend=Decimal(pricing["maximum_per_call_spend"]),
        uncached_input_price_per_million=Decimal(
            pricing["uncached_input_price"]
        ),
        cached_input_price_per_million=Decimal(pricing["cached_input_price"]),
        output_price_per_million=Decimal(pricing["output_price"]),
    )


def _read_attribute(value: object, name: str, default: object = None) -> object:
    if isinstance(value, Mapping):
        return value.get(name, default)
    return getattr(value, name, default)


def _error_classification(error: Exception) -> TransportErrorClassification | None:
    if isinstance(error, APITimeoutError):
        return TransportErrorClassification.TIMEOUT
    if isinstance(error, (APIConnectionError, RateLimitError)):
        return TransportErrorClassification.UNAVAILABLE
    if isinstance(error, APIStatusError):
        status_code = error.status_code
        if status_code == 429 or status_code >= 500:
            return TransportErrorClassification.UNAVAILABLE
    return None


def _extract_one_output_text(response: object) -> tuple[str, str | None]:
    status = _read_attribute(response, "status")
    if status != "completed":
        incomplete = _read_attribute(response, "incomplete_details")
        reason = _read_attribute(incomplete, "reason")
        raise OpenAIIncompleteResponseError(
            f"OpenAI response was not complete ({reason or status})."
        )
    texts: list[str] = []
    for output_item in _read_attribute(response, "output", ()) or ():
        if _read_attribute(output_item, "type") != "message":
            raise OpenAIProviderSchemaError(
                "OpenAI response contains an unexpected output item."
            )
        for content_item in _read_attribute(output_item, "content", ()) or ():
            content_type = _read_attribute(content_item, "type")
            if content_type == "refusal":
                raise OpenAIRefusalError("OpenAI response was refused.")
            if content_type == "output_text":
                text = _read_attribute(content_item, "text")
                if isinstance(text, str):
                    texts.append(text)
                continue
            raise OpenAIProviderSchemaError(
                "OpenAI response contains an unexpected content item."
            )
    if len(texts) != 1:
        raise OpenAIProviderSchemaError(
            "OpenAI response must contain exactly one output-text value."
        )
    return texts[0], str(status)


class OpenAIMovingServiceEvaluationTransport:
    """Injected-client OpenAI transport; unreachable from the current runner."""

    def __init__(
        self,
        *,
        client: InjectedOpenAIClient,
        run_configuration_path: Path = DEFAULT_RUN_CONFIGURATION_PATH,
        response_schema_path: Path = DEFAULT_RESPONSE_SCHEMA_PATH,
        expected_run_configuration_digest: str = OPENAI_RUN_CONFIGURATION_DIGEST,
        expected_response_schema_digest: str = OPENAI_RESPONSE_SCHEMA_DIGEST,
        clock: Callable[[], float] = perf_counter,
    ) -> None:
        if openai.__version__ != OPENAI_SDK_VERSION:
            raise OpenAITransportArtifactError("Installed OpenAI SDK version drifted.")
        if getattr(client, "max_retries", None) != 0:
            raise OpenAITransportArtifactError(
                "Injected OpenAI client must disable automatic retries."
            )
        self.client = client
        self.run_configuration_path = run_configuration_path
        self.response_schema_path = response_schema_path
        self.expected_run_configuration_digest = expected_run_configuration_digest
        self.expected_response_schema_digest = expected_response_schema_digest
        self.clock = clock
        self._consumed_preflights: list[OpenAIPreflightResult] = []

    def _verified(
        self, request: MovingServiceProviderRequest
    ) -> VerifiedOpenAITransportArtifacts:
        artifacts = load_verified_openai_transport_artifacts(
            run_configuration_path=self.run_configuration_path,
            response_schema_path=self.response_schema_path,
            expected_run_configuration_digest=self.expected_run_configuration_digest,
            expected_response_schema_digest=self.expected_response_schema_digest,
        )
        if request.model_identifier != OPENAI_MODEL_IDENTIFIER:
            raise OpenAITransportArtifactError("OpenAI AI model identifier drifted.")
        if dict(request.model_parameters) != {"temperature": 0}:
            raise OpenAITransportArtifactError("OpenAI model parameters drifted.")
        if request.maximum_output_tokens != 500 or request.retry_count != 0:
            raise OpenAITransportArtifactError("OpenAI request limits drifted.")
        if request.timeout_seconds != artifacts.generation_timeout_seconds:
            raise OpenAITransportArtifactError("OpenAI generation timeout drifted.")
        if _without_titles(request.response_json_schema) != artifacts.response_schema:
            raise OpenAITransportArtifactError(
                "Runtime response schema drifted from the frozen OpenAI snapshot."
            )
        return artifacts

    def _common_input(
        self,
        request: MovingServiceProviderRequest,
        artifacts: VerifiedOpenAITransportArtifacts,
    ) -> dict[str, object]:
        text_format = {
            "format": {
                "type": "json_schema",
                "name": "moving_service_question_response_v1",
                "strict": True,
                "schema": artifacts.response_schema,
            }
        }
        return {
            "model": request.model_identifier,
            "instructions": request.system_instructions,
            "input": request.deterministic_request_json,
            "text": text_format,
            "truncation": "disabled",
        }

    def _request_fingerprint(
        self,
        request: MovingServiceProviderRequest,
        artifacts: VerifiedOpenAITransportArtifacts,
    ) -> str:
        fingerprint_data = {
            "common_input": self._common_input(request, artifacts),
            "maximum_output_tokens": request.maximum_output_tokens,
            "temperature": 0,
            "store": False,
            "background": False,
            "stream": False,
            "generation_timeout_seconds": artifacts.generation_timeout_seconds,
            "retry_count": request.retry_count,
        }
        serialized = json.dumps(
            fingerprint_data,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def preflight(
        self,
        request: MovingServiceProviderRequest,
    ) -> OpenAIPreflightResult:
        """Perform only exact input-token counting and conservative gating."""
        artifacts = self._verified(request)
        common_input = self._common_input(request, artifacts)
        request_fingerprint = self._request_fingerprint(request, artifacts)
        preflight_started = self.clock()
        try:
            count_response = self.client.responses.input_tokens.count(
                **common_input,
                timeout=artifacts.preflight_timeout_seconds,
            )
        except Exception as error:
            classification = _error_classification(error)
            if classification is None:
                raise
            preflight_ms = (self.clock() - preflight_started) * 1_000
            return OpenAIPreflightResult(
                request_fingerprint=request_fingerprint,
                input_tokens=None,
                duration_ms=preflight_ms,
                conservative_cost=None,
                error_classification=classification,
            )
        preflight_ms = (self.clock() - preflight_started) * 1_000
        input_tokens = _read_attribute(count_response, "input_tokens")
        if not isinstance(input_tokens, int) or input_tokens < 0:
            raise OpenAIPreflightGateError(
                "OpenAI preflight did not return a valid exact token count."
            )
        if input_tokens > MAXIMUM_INPUT_TOKENS:
            raise OpenAIBudgetGateError(
                "OpenAI exact input-token count exceeds the frozen ceiling."
            )
        conservative_cost = (
            Decimal(input_tokens)
            * artifacts.uncached_input_price_per_million
            / Decimal(1_000_000)
            + Decimal(request.maximum_output_tokens)
            * artifacts.output_price_per_million
            / Decimal(1_000_000)
        )
        if conservative_cost > artifacts.maximum_per_call_spend:
            raise OpenAIBudgetGateError(
                "OpenAI conservative cost exceeds the frozen per-call ceiling."
            )

        return OpenAIPreflightResult(
            request_fingerprint=request_fingerprint,
            input_tokens=input_tokens,
            duration_ms=preflight_ms,
            conservative_cost=conservative_cost,
        )

    def generate(
        self,
        request: MovingServiceProviderRequest,
        preflight: OpenAIPreflightResult,
    ) -> MovingServiceTransportResult:
        """Generate once using successful evidence for this exact request."""
        artifacts = self._verified(request)
        if not preflight.succeeded:
            raise OpenAIPreflightGateError(
                "Successful OpenAI preflight evidence is required for generation."
            )
        if preflight.request_fingerprint != self._request_fingerprint(
            request,
            artifacts,
        ):
            raise OpenAIPreflightGateError(
                "OpenAI preflight evidence does not match the generation request."
            )
        if any(item is preflight for item in self._consumed_preflights):
            raise OpenAIPreflightGateError(
                "OpenAI preflight evidence has already been consumed."
            )
        self._consumed_preflights.append(preflight)
        input_tokens = preflight.input_tokens
        if input_tokens is None:
            raise OpenAIPreflightGateError(
                "OpenAI preflight token evidence is missing."
            )
        common_input = self._common_input(request, artifacts)
        generation_started = self.clock()
        try:
            response = self.client.responses.create(
                **common_input,
                max_output_tokens=request.maximum_output_tokens,
                temperature=0,
                store=False,
                background=False,
                stream=False,
                timeout=artifacts.generation_timeout_seconds,
            )
        except Exception as error:
            classification = _error_classification(error)
            if classification is None:
                raise
            generation_ms = (self.clock() - generation_started) * 1_000
            return MovingServiceTransportResult(
                response_content=None,
                input_tokens=input_tokens,
                duration_ms=preflight.duration_ms + generation_ms,
                preflight_duration_ms=preflight.duration_ms,
                generation_duration_ms=generation_ms,
                cache_status="not_available",
                provider_name=OPENAI_PROVIDER_NAME,
                failure_phase="generation",
                error_classification=classification,
            )

        generation_ms = (self.clock() - generation_started) * 1_000
        response_text, finish_status = _extract_one_output_text(response)
        usage = _read_attribute(response, "usage")
        usage_input_tokens = _read_attribute(usage, "input_tokens")
        usage_output_tokens = _read_attribute(usage, "output_tokens")
        input_details = _read_attribute(usage, "input_tokens_details")
        cached_tokens = _read_attribute(input_details, "cached_tokens")
        if not isinstance(usage_input_tokens, int) or usage_input_tokens < 0:
            raise ResponseValidationError("OpenAI input-token usage is invalid.")
        if not isinstance(usage_output_tokens, int) or usage_output_tokens < 0:
            raise ResponseValidationError("OpenAI output-token usage is invalid.")
        if usage_input_tokens != input_tokens:
            raise ResponseValidationError(
                "OpenAI preflight and generation input-token counts differ."
            )
        cache_status = "not_available"
        if cached_tokens is None:
            cached_tokens = 0
        elif isinstance(cached_tokens, int) and 0 <= cached_tokens <= usage_input_tokens:
            cache_status = "hit" if cached_tokens else "miss"
        else:
            raise ResponseValidationError("OpenAI cached-token usage is invalid.")
        uncached_tokens = usage_input_tokens - cached_tokens
        actual_cost = (
            Decimal(uncached_tokens)
            * artifacts.uncached_input_price_per_million
            / Decimal(1_000_000)
            + Decimal(cached_tokens)
            * artifacts.cached_input_price_per_million
            / Decimal(1_000_000)
            + Decimal(usage_output_tokens)
            * artifacts.output_price_per_million
            / Decimal(1_000_000)
        )
        return MovingServiceTransportResult(
            response_content=response_text,
            input_tokens=usage_input_tokens,
            cached_input_tokens=cached_tokens,
            uncached_input_tokens=uncached_tokens,
            output_tokens=usage_output_tokens,
            duration_ms=preflight.duration_ms + generation_ms,
            preflight_duration_ms=preflight.duration_ms,
            generation_duration_ms=generation_ms,
            cache_status=cache_status,
            provider_name=OPENAI_PROVIDER_NAME,
            provider_model_identifier=(
                str(_read_attribute(response, "model"))
                if _read_attribute(response, "model") is not None
                else None
            ),
            provider_request_id=(
                str(_read_attribute(response, "_request_id"))
                if _read_attribute(response, "_request_id") is not None
                else None
            ),
            finish_status=finish_status,
            refusal_status="not_refused",
            estimated_cost=f"${actual_cost:.8f}",
        )
