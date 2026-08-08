"""Offline-only frozen-v3 request construction for generation-gate rehearsal."""

from __future__ import annotations

import hashlib
import json
import tomllib
from pathlib import Path

from app.moving_service_questions import ExperimentFixture, build_trusted_fixture
from moving_service_questions_v2 import construct_request_v2
from moving_service_questions_v3 import (
    PROMPT_VERSION_V3,
    SCHEMA_VERSION_V3,
    MovingServiceQuestionRequestV3,
)
from real_model_adapter import MovingServiceProviderRequest
from run_openai_stage_b_v2_pilot import PreparedV2Pilot


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
V3_ROOT = REPOSITORY_ROOT / "docs/experiments/suggest-moving-service-questions/v3"
V2_PILOT_PATH = (
    REPOSITORY_ROOT
    / "docs/experiments/suggest-moving-service-questions/v2/openai-follow-up-pilot.toml"
)
FROZEN_V3_MANIFEST_DIGEST = "44da0c5005515784c2c13737ca12a4382c084f1aa56fea5b4a4d40e66fb8659c"
V2_PILOT_CONFIGURATION_DIGEST = "08d1d6781cae9150c059736ea92e119226234c8e53c798766f2901f010499ad3"


class V3PilotError(ValueError):
    pass


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare_frozen_v3_pilot() -> PreparedV2Pilot:
    """Build the v3 request while reusing unchanged frozen transport parameters."""
    if _digest(V3_ROOT / "manifest.json") != FROZEN_V3_MANIFEST_DIGEST:
        raise V3PilotError("frozen v3 manifest drifted")
    manifest = json.loads((V3_ROOT / "manifest.json").read_text(encoding="utf-8"))
    for name, expected in manifest["artifact_digests"].items():
        if _digest(V3_ROOT / name) != expected:
            raise V3PilotError(f"frozen v3 artifact drifted: {name}")
    if _digest(V2_PILOT_PATH) != V2_PILOT_CONFIGURATION_DIGEST:
        raise V3PilotError("unchanged transport configuration drifted")

    prompt = tomllib.loads((V3_ROOT / "real-model-prompt.toml").read_text())
    schema = json.loads((V3_ROOT / "openai-response-schema.json").read_text())
    pilot = tomllib.loads(V2_PILOT_PATH.read_text())
    pilot["contracts"] = {
        **pilot["contracts"],
        "prompt_path": str(V3_ROOT.relative_to(REPOSITORY_ROOT) / "real-model-prompt.toml"),
        "prompt_version": PROMPT_VERSION_V3,
        "prompt_digest": manifest["artifact_digests"]["real-model-prompt.toml"],
        "request_schema_version": SCHEMA_VERSION_V3,
        "response_schema_version": SCHEMA_VERSION_V3,
        "provider_schema_path": str(V3_ROOT.relative_to(REPOSITORY_ROOT) / "openai-response-schema.json"),
        "provider_schema_digest": manifest["artifact_digests"]["openai-response-schema.json"],
    }
    v2_request = construct_request_v2(
        build_trusted_fixture(ExperimentFixture.STORAGE_UNKNOWN)
    )
    document = v2_request.model_dump(mode="python")
    document["prompt_version"] = PROMPT_VERSION_V3
    document["schema_version"] = SCHEMA_VERSION_V3
    request = MovingServiceQuestionRequestV3.model_validate(document)
    provider_request = MovingServiceProviderRequest(
        model_identifier=pilot["identity"]["ai_model_identifier"],
        model_parameters={"temperature": pilot["model_parameters"]["temperature"]},
        system_instructions=prompt["system_instructions"],
        deterministic_request_json=request.model_dump_json(
            exclude_none=False, exclude_defaults=False
        ),
        response_json_schema=schema,
        maximum_output_tokens=pilot["model_parameters"]["maximum_output_tokens"],
        timeout_seconds=float(pilot["transport"]["ai_generation_timeout_seconds"]),
        retry_count=pilot["transport"]["automatic_retries"],
    )
    return PreparedV2Pilot(request, provider_request, manifest, pilot)


def deterministic_request_digest(prepared: PreparedV2Pilot) -> str:
    return hashlib.sha256(
        prepared.provider_request.deterministic_request_json.encode("utf-8")
    ).hexdigest()


def canonical_attempt(prepared: PreparedV2Pilot) -> dict[str, object]:
    return {
        "common_input": {
            "model": prepared.provider_request.model_identifier,
            "instructions": prepared.provider_request.system_instructions,
            "input": prepared.provider_request.deterministic_request_json,
            "text": {"format": {
                "type": "json_schema",
                "name": "moving_service_question_response_v3",
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


def canonical_attempt_digest(prepared: PreparedV2Pilot) -> str:
    serialized = json.dumps(
        canonical_attempt(prepared), ensure_ascii=False, separators=(",", ":"), sort_keys=True
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
