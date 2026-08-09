"""Offline-only frozen-v4 request preparation; no credential or transport access."""

from __future__ import annotations

import hashlib
import json
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping

from app.moving_service_questions import ExperimentFixture, STORAGE_KNOWLEDGE, build_trusted_fixture
from moving_service_questions_v2 import construct_request_v2
from moving_service_questions_v4 import PROMPT_VERSION_V4, SCHEMA_VERSION_V4, MovingServiceQuestionRequestV4
from real_model_adapter import MovingServiceProviderRequest
from run_openai_stage_b_v2_pilot import PreparedV2Pilot

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
V4_ROOT = REPOSITORY_ROOT / "docs/experiments/suggest-moving-service-questions/v4"
V2_PILOT_PATH = REPOSITORY_ROOT / "docs/experiments/suggest-moving-service-questions/v2/openai-follow-up-pilot.toml"
V2_PILOT_CONFIGURATION_DIGEST = "08d1d6781cae9150c059736ea92e119226234c8e53c798766f2901f010499ad3"
FROZEN_V4_MANIFEST_DIGEST = "3cdbd2bf3606191aa52108d8284c8ab300d58a511f313f78a06be51d95fac649"
CLOSED_GROUNDING_TRIGGERS = ("required", "requirement", "must", "will need")


class V4PilotError(ValueError):
    pass


class ProhibitedGroundingSourceError(V4PilotError):
    """Fail before request construction when exact grounding cannot be safely copied."""

    classification = "prohibited_grounding_source"


@dataclass(frozen=True)
class FrozenV4ProviderMetadata:
    """Validated frozen metadata that carries no constructed provider request."""

    manifest: Mapping[str, object]
    pilot_configuration: Mapping[str, object]
    system_instructions: str
    response_json_schema: Mapping[str, object]


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def grounding_source_triggers(statement: str) -> tuple[str, ...]:
    normalized = " ".join(statement.casefold().split())
    return tuple(trigger for trigger in CLOSED_GROUNDING_TRIGGERS
                 if re.search(rf"\b{re.escape(trigger)}\b", normalized))


def validate_grounding_source(statement: str) -> None:
    triggers = grounding_source_triggers(statement)
    if triggers:
        raise ProhibitedGroundingSourceError(
            "approved grounding source contains a closed runtime lexical trigger"
        )


def prepare_frozen_v4_provider_metadata(
    *, grounding_statement: str = STORAGE_KNOWLEDGE.statement,
) -> FrozenV4ProviderMetadata:
    """Load exact frozen-v4 provider metadata without constructing a request."""
    validate_grounding_source(grounding_statement)
    manifest_path = V4_ROOT / "manifest.json"
    if _digest(manifest_path) != FROZEN_V4_MANIFEST_DIGEST:
        raise V4PilotError("frozen v4 manifest drifted")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for name, expected in manifest["artifact_digests"].items():
        if _digest(V4_ROOT / name) != expected:
            raise V4PilotError(f"frozen v4 artifact drifted: {name}")
    if _digest(V2_PILOT_PATH) != V2_PILOT_CONFIGURATION_DIGEST:
        raise V4PilotError("unchanged transport configuration drifted")
    if grounding_statement != STORAGE_KNOWLEDGE.statement:
        raise V4PilotError("grounding source differs from the approved exact statement")

    prompt = tomllib.loads((V4_ROOT / "real-model-prompt.toml").read_text())
    schema = json.loads((V4_ROOT / "openai-response-schema.json").read_text())
    pilot = tomllib.loads(V2_PILOT_PATH.read_text())
    pilot["contracts"] = {
        **pilot["contracts"],
        "prompt_path": str(V4_ROOT.relative_to(REPOSITORY_ROOT) / "real-model-prompt.toml"),
        "prompt_version": PROMPT_VERSION_V4,
        "prompt_digest": manifest["artifact_digests"]["real-model-prompt.toml"],
        "request_schema_version": SCHEMA_VERSION_V4,
        "response_schema_version": SCHEMA_VERSION_V4,
        "provider_schema_path": str(V4_ROOT.relative_to(REPOSITORY_ROOT) / "openai-response-schema.json"),
        "provider_schema_digest": manifest["artifact_digests"]["openai-response-schema.json"],
    }
    return FrozenV4ProviderMetadata(
        manifest=manifest,
        pilot_configuration=pilot,
        system_instructions=prompt["system_instructions"],
        response_json_schema=schema,
    )


def construct_frozen_v4_provider_request(
    metadata: FrozenV4ProviderMetadata,
    request: MovingServiceQuestionRequestV4,
    provider_request_constructor: Callable[..., MovingServiceProviderRequest] = MovingServiceProviderRequest,
) -> MovingServiceProviderRequest:
    """Construct the provider request only after deterministic eligibility succeeds."""
    pilot = metadata.pilot_configuration
    return provider_request_constructor(
        model_identifier=pilot["identity"]["ai_model_identifier"],
        model_parameters={"temperature": pilot["model_parameters"]["temperature"]},
        system_instructions=metadata.system_instructions,
        deterministic_request_json=request.model_dump_json(exclude_none=False, exclude_defaults=False),
        response_json_schema=metadata.response_json_schema,
        maximum_output_tokens=pilot["model_parameters"]["maximum_output_tokens"],
        timeout_seconds=float(pilot["transport"]["ai_generation_timeout_seconds"]),
        retry_count=pilot["transport"]["automatic_retries"],
    )


def prepare_frozen_v4_pilot(
    *, grounding_statement: str = STORAGE_KNOWLEDGE.statement,
    provider_request_constructor: Callable[..., MovingServiceProviderRequest] = MovingServiceProviderRequest,
) -> PreparedV2Pilot:
    """Validate grounding first, then construct the exact offline v4 request."""
    metadata = prepare_frozen_v4_provider_metadata(grounding_statement=grounding_statement)
    v2_request = construct_request_v2(build_trusted_fixture(ExperimentFixture.STORAGE_UNKNOWN))
    document = v2_request.model_dump(mode="python")
    document["prompt_version"] = PROMPT_VERSION_V4
    document["schema_version"] = SCHEMA_VERSION_V4
    request = MovingServiceQuestionRequestV4.model_validate(document)
    provider_request = construct_frozen_v4_provider_request(
        metadata, request, provider_request_constructor
    )
    return PreparedV2Pilot(
        request, provider_request, metadata.manifest, metadata.pilot_configuration
    )


def deterministic_request_digest(prepared: PreparedV2Pilot) -> str:
    return hashlib.sha256(prepared.provider_request.deterministic_request_json.encode()).hexdigest()


def canonical_attempt(prepared: PreparedV2Pilot) -> dict[str, object]:
    return {
        "common_input": {
            "model": prepared.provider_request.model_identifier,
            "instructions": prepared.provider_request.system_instructions,
            "input": prepared.provider_request.deterministic_request_json,
            "text": {"format": {"type": "json_schema", "name": "moving_service_question_response_v4",
                                "strict": True, "schema": prepared.provider_request.response_json_schema}},
            "truncation": "disabled",
        },
        "maximum_output_tokens": prepared.provider_request.maximum_output_tokens,
        "temperature": 0, "store": False, "background": False, "stream": False,
        "generation_timeout_seconds": prepared.provider_request.timeout_seconds,
        "retry_count": prepared.provider_request.retry_count,
    }


def canonical_attempt_digest(prepared: PreparedV2Pilot) -> str:
    encoded = json.dumps(canonical_attempt(prepared), ensure_ascii=False,
                         separators=(",", ":"), sort_keys=True).encode()
    return hashlib.sha256(encoded).hexdigest()
