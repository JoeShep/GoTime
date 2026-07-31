"""Offline-only adapter scaffold for suggest_moving_service_questions."""

from __future__ import annotations

import hashlib
import json
import sys
import tomllib
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Mapping, Protocol

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = REPOSITORY_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.moving_service_questions import (  # noqa: E402
    CAPABILITY,
    KNOWLEDGE_VERSION,
    MAXIMUM_INPUT_TOKENS,
    MAXIMUM_OUTPUT_TOKENS,
    MAXIMUM_QUESTIONS,
    PROMPT_VERSION,
    SCHEMA_VERSION,
    AdapterTimeoutError,
    AdapterUnavailableError,
    MovingServiceQuestionRequest,
    MovingServiceQuestionResponse,
    ResponseValidationError,
)

FROZEN_PROMPT_DIGEST = (
    "583a4bdf59c4c4ac67c82928415710c3d5c21ac9912ebd4888a026b8fd4acbf2"
)
DEFAULT_TIMEOUT_SECONDS = 12.0
FORMAL_RETRY_COUNT = 0


class PromptArtifactError(ValueError):
    """The frozen prompt bytes or metadata do not match the approved artifact."""


class TransportErrorClassification(StrEnum):
    UNAVAILABLE = "unavailable"
    TIMEOUT = "timeout"


@dataclass(frozen=True)
class MovingServiceProviderRequest:
    """Bounded request data for a future provider-specific transport."""

    model_identifier: str
    model_parameters: Mapping[str, object]
    system_instructions: str
    deterministic_request_json: str
    response_json_schema: Mapping[str, object]
    maximum_output_tokens: int
    timeout_seconds: float
    retry_count: int

    def __post_init__(self) -> None:
        if not 1 <= len(self.model_identifier) <= 120:
            raise ValueError("Offline model identifier is outside the bounded length.")
        if self.maximum_output_tokens != MAXIMUM_OUTPUT_TOKENS:
            raise ValueError("Provider request output-token limit is incompatible.")
        if self.timeout_seconds != DEFAULT_TIMEOUT_SECONDS:
            raise ValueError("Provider request timeout is incompatible.")
        if self.retry_count != FORMAL_RETRY_COUNT:
            raise ValueError("Provider request retry count is incompatible.")


@dataclass(frozen=True)
class MovingServiceTransportResult:
    """Bounded untrusted result returned by the injected transport."""

    response_content: Mapping[str, object] | str | None
    input_tokens: int | None = None
    output_tokens: int | None = None
    duration_ms: float = 0.0
    cache_status: str = "disabled"
    error_classification: TransportErrorClassification | None = None

    def __post_init__(self) -> None:
        for field, value in (
            ("input_tokens", self.input_tokens),
            ("output_tokens", self.output_tokens),
        ):
            if value is not None and value < 0:
                raise ValueError(f"Transport {field} cannot be negative.")
        if self.duration_ms < 0:
            raise ValueError("Transport duration cannot be negative.")
        if self.cache_status not in {"disabled", "hit", "miss", "not_available"}:
            raise ValueError("Transport cache status is unsupported.")


class MovingServiceEvaluationTransport(Protocol):
    """Capability-specific transport seam; it owns no policy or orchestration."""

    def send(
        self,
        request: MovingServiceProviderRequest,
    ) -> MovingServiceTransportResult:
        ...


class OfflineFakeMovingServiceTransport:
    """The only transport implementation permitted in the offline milestone."""

    def __init__(self, result: MovingServiceTransportResult):
        self.result = result
        self.requests: list[MovingServiceProviderRequest] = []

    @property
    def call_count(self) -> int:
        return len(self.requests)

    def send(
        self,
        request: MovingServiceProviderRequest,
    ) -> MovingServiceTransportResult:
        self.requests.append(request)
        return self.result


@dataclass(frozen=True)
class VerifiedPrompt:
    system_instructions: str
    top_level_field_order: tuple[str, ...]
    maximum_input_tokens: int
    maximum_output_tokens: int


@dataclass(frozen=True)
class AdapterInvocation:
    raw_response: Mapping[str, object]
    transport_result: MovingServiceTransportResult


def _require_equal(actual: object, expected: object, field: str) -> None:
    if actual != expected:
        raise PromptArtifactError(f"Frozen prompt {field} is incompatible.")


def load_verified_prompt(
    prompt_artifact_path: Path,
    expected_prompt_digest: str,
) -> VerifiedPrompt:
    """Load and verify the exact frozen prompt before transport invocation."""
    prompt_bytes = prompt_artifact_path.read_bytes()
    actual_digest = hashlib.sha256(prompt_bytes).hexdigest()
    if actual_digest != expected_prompt_digest:
        raise PromptArtifactError("Frozen prompt SHA-256 digest does not match.")

    try:
        prompt = tomllib.loads(prompt_bytes.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        raise PromptArtifactError("Frozen prompt is not valid UTF-8 TOML.") from error

    metadata = prompt.get("metadata", {})
    readiness = prompt.get("readiness", {})
    serialization = prompt.get("serialization", {})
    _require_equal(metadata.get("capability"), CAPABILITY, "capability")
    _require_equal(metadata.get("prompt_version"), PROMPT_VERSION, "prompt version")
    _require_equal(
        metadata.get("compatible_request_schema_version"),
        SCHEMA_VERSION,
        "request schema version",
    )
    _require_equal(
        metadata.get("compatible_response_schema_version"),
        SCHEMA_VERSION,
        "response schema version",
    )
    _require_equal(
        metadata.get("compatible_knowledge_fixture_version"),
        KNOWLEDGE_VERSION,
        "knowledge fixture version",
    )
    _require_equal(metadata.get("maximum_questions"), MAXIMUM_QUESTIONS, "question limit")
    _require_equal(
        metadata.get("maximum_input_tokens"),
        MAXIMUM_INPUT_TOKENS,
        "input-token limit",
    )
    _require_equal(
        metadata.get("maximum_output_tokens"),
        MAXIMUM_OUTPUT_TOKENS,
        "output-token limit",
    )
    _require_equal(metadata.get("formal_evaluation_retries"), 0, "retry count")
    _require_equal(metadata.get("production_use_prohibited"), True, "production status")
    _require_equal(readiness.get("reviewed"), True, "review status")
    _require_equal(
        readiness.get("frozen_for_adapter_implementation"),
        True,
        "adapter freeze status",
    )
    _require_equal(
        readiness.get("frozen_for_real_model_execution"),
        False,
        "execution freeze status",
    )
    _require_equal(
        serialization.get("request_format"),
        "deterministic_compact_json",
        "request format",
    )
    system_instructions = prompt.get("system_instructions")
    if not isinstance(system_instructions, str) or not system_instructions.strip():
        raise PromptArtifactError("Frozen prompt system instructions are missing.")
    field_order = serialization.get("top_level_field_order")
    if not isinstance(field_order, list) or not all(
        isinstance(field, str) for field in field_order
    ):
        raise PromptArtifactError("Frozen prompt request field order is invalid.")

    return VerifiedPrompt(
        system_instructions=system_instructions,
        top_level_field_order=tuple(field_order),
        maximum_input_tokens=MAXIMUM_INPUT_TOKENS,
        maximum_output_tokens=MAXIMUM_OUTPUT_TOKENS,
    )


def serialize_request_deterministically(
    request: MovingServiceQuestionRequest,
    expected_field_order: tuple[str, ...],
) -> str:
    """Serialize only validated request fields in frozen declaration order."""
    serialized = request.model_dump_json(
        exclude_none=False,
        exclude_defaults=False,
    )
    decoded = json.loads(serialized)
    if list(decoded) != list(MovingServiceQuestionRequest.model_fields):
        raise PromptArtifactError("Runtime request field order has drifted.")
    if list(decoded) != list(expected_field_order):
        raise PromptArtifactError("Request field order does not match the frozen prompt.")
    return serialized


def _reject_duplicate_json_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ResponseValidationError("Transport response contains duplicate keys.")
        result[key] = value
    return result


def _parse_untrusted_response(
    content: Mapping[str, object] | str | None,
) -> Mapping[str, object]:
    if isinstance(content, Mapping):
        return dict(content)
    if not isinstance(content, str):
        raise ResponseValidationError("Transport returned no response object.")
    try:
        decoded = json.loads(content, object_pairs_hook=_reject_duplicate_json_keys)
    except (json.JSONDecodeError, ResponseValidationError) as error:
        raise ResponseValidationError(
            "Transport response is not one valid JSON object."
        ) from error
    if not isinstance(decoded, dict):
        raise ResponseValidationError("Transport response is not a JSON object.")
    return decoded


class RealModelMovingServiceQuestionAdapter:
    """Offline scaffold implementing the existing capability adapter boundary."""

    def __init__(
        self,
        *,
        model_identifier: str,
        model_parameters: Mapping[str, object],
        transport: MovingServiceEvaluationTransport,
        prompt_artifact_path: Path,
        expected_prompt_digest: str = FROZEN_PROMPT_DIGEST,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ):
        if not model_identifier.strip():
            raise ValueError("A nonblank offline model identifier is required.")
        if timeout_seconds != DEFAULT_TIMEOUT_SECONDS:
            raise ValueError("The offline scaffold requires the frozen timeout.")
        self.model_identifier = model_identifier
        self.model_parameters = dict(model_parameters)
        self.transport = transport
        self.prompt_artifact_path = prompt_artifact_path
        self.expected_prompt_digest = expected_prompt_digest
        self.timeout_seconds = timeout_seconds

    def prepare_request(
        self,
        request: MovingServiceQuestionRequest,
    ) -> MovingServiceProviderRequest:
        prompt = load_verified_prompt(
            self.prompt_artifact_path,
            self.expected_prompt_digest,
        )
        serialized = serialize_request_deterministically(
            request,
            prompt.top_level_field_order,
        )
        return MovingServiceProviderRequest(
            model_identifier=self.model_identifier,
            model_parameters=self.model_parameters,
            system_instructions=prompt.system_instructions,
            deterministic_request_json=serialized,
            response_json_schema=MovingServiceQuestionResponse.model_json_schema(),
            maximum_output_tokens=prompt.maximum_output_tokens,
            timeout_seconds=self.timeout_seconds,
            retry_count=FORMAL_RETRY_COUNT,
        )

    def invoke_prepared(
        self,
        provider_request: MovingServiceProviderRequest,
    ) -> AdapterInvocation:
        result = self.transport.send(provider_request)
        if result.error_classification is TransportErrorClassification.UNAVAILABLE:
            raise AdapterUnavailableError("The offline transport is unavailable.")
        if result.error_classification is TransportErrorClassification.TIMEOUT:
            raise AdapterTimeoutError("The offline transport timed out.")
        raw_response = _parse_untrusted_response(result.response_content)
        return AdapterInvocation(raw_response=raw_response, transport_result=result)

    def invoke(
        self,
        request: MovingServiceQuestionRequest,
    ) -> AdapterInvocation:
        return self.invoke_prepared(self.prepare_request(request))

    def suggest(
        self,
        request: MovingServiceQuestionRequest,
    ) -> Mapping[str, object]:
        return self.invoke(request).raw_response
