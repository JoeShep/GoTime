"""Immutable, non-authoritative AI case envelopes for Architecture A."""

from __future__ import annotations

from typing import Mapping

from run_openai_stage_b_v4_pilot import prepare_frozen_v4_provider_metadata
from v4_formal_evaluation_live_models import (
    AGGREGATE_ID, AGGREGATE_VERSION, AI_CASE_ORDER, EVALUATION_SET_ID,
    EVALUATION_MANIFEST_SHA256, FROZEN_V4_MANIFEST_SHA256,
    PER_CASE_PROVIDER_CEILING_USD, canonical_json, digest, immutable_package,
    package_identity,
)

ENVELOPE_SCHEMA = "suggest-moving-service-questions-v4-formal-evaluation-ai-case-envelope-v1"
ENVELOPE_VERSION = 1


class AiCaseEnvelopeError(ValueError):
    pass


def _frozen_provider_metadata() -> dict[str, object]:
    metadata = prepare_frozen_v4_provider_metadata()
    pilot = metadata.pilot_configuration
    contracts = pilot["contracts"]
    return {
        "frozen_v4_manifest_sha256": FROZEN_V4_MANIFEST_SHA256,
        "prompt_version": contracts["prompt_version"],
        "prompt_sha256": contracts["prompt_digest"],
        "request_schema_version": contracts["request_schema_version"],
        "response_schema_version": contracts["response_schema_version"],
        "provider_schema_sha256": contracts["provider_schema_digest"],
        "provider": pilot["identity"]["provider"],
        "ai_model_identifier": pilot["identity"]["ai_model_identifier"],
        "sdk": pilot["identity"]["sdk_pin"],
        "request_configuration": {
            "model_parameters": pilot["model_parameters"],
            "structured_output_mode": pilot["transport"]["structured_output_mode"],
            "token_preflight_timeout_seconds": pilot["transport"]["token_preflight_timeout_seconds"],
            "generation_timeout_seconds": pilot["transport"]["ai_generation_timeout_seconds"],
            "automatic_retries": pilot["transport"]["automatic_retries"],
        },
    }


def _build_ai_case_envelope(
    case_id: str, binding: Mapping[str, object], provider: Mapping[str, object],
) -> dict[str, object]:
    if (
        binding["provider_request_expected"] is not True
        or binding["provider"] != provider["provider"]
        or binding["ai_model_identifier"] != provider["ai_model_identifier"]
        or binding["sdk"] != provider["sdk"]
        or not all(binding[key] for key in (
            "deterministic_request_sha256", "canonical_attempt_sha256",
            "provider_fingerprint",
        ))
    ):
        raise AiCaseEnvelopeError("frozen AI request identity binding is incomplete")
    immutable = {
        "aggregate_id": AGGREGATE_ID,
        "aggregate_version": AGGREGATE_VERSION,
        "aggregate_package_sha256": package_identity(),
        "evaluation_set_id": EVALUATION_SET_ID,
        "evaluation_manifest_sha256": EVALUATION_MANIFEST_SHA256,
        "case_id": case_id,
        "deterministic_case_input_sha256": binding["deterministic_case_input_sha256"],
        "deterministic_request_sha256": binding["deterministic_request_sha256"],
        "canonical_attempt_sha256": binding["canonical_attempt_sha256"],
        "provider_fingerprint": binding["provider_fingerprint"],
        **provider,
        "case_budget_policy": {
            "maximum_token_preflights": 1,
            "maximum_generations": 1,
            "maximum_retries": 0,
            "provider_ceiling_usd": PER_CASE_PROVIDER_CEILING_USD,
            "spending_authorized": False,
        },
        "provider_authority": False,
    }
    identity = digest({
        "envelope_schema": ENVELOPE_SCHEMA,
        "envelope_version": ENVELOPE_VERSION,
        "immutable_binding": immutable,
    })
    return {
        "envelope_schema": ENVELOPE_SCHEMA,
        "envelope_version": ENVELOPE_VERSION,
        "envelope_sha256": identity,
        "immutable_binding": immutable,
        "phase_lifecycle": {
            "preflight_status": "not_authorized",
            "generation_status": "not_authorized",
            "provider_attempts_consumed": 0,
            "terminal": False,
            "review_status": "not_started",
            "evidence_deletion_status": "not_applicable",
            "closure_status": "open",
        },
    }


def build_ai_case_envelope(case_id: str) -> dict[str, object]:
    if case_id not in AI_CASE_ORDER:
        raise AiCaseEnvelopeError("AI envelope target is not a frozen AI case")
    binding = {
        item["case_id"]: item for item in immutable_package()["case_bindings"]
    }[case_id]
    return _build_ai_case_envelope(case_id, binding, _frozen_provider_metadata())


def build_all_ai_case_envelopes() -> dict[str, object]:
    bindings = {item["case_id"]: item for item in immutable_package()["case_bindings"]}
    provider = _frozen_provider_metadata()
    envelopes = {
        case_id: _build_ai_case_envelope(case_id, bindings[case_id], provider)
        for case_id in AI_CASE_ORDER
    }
    identities = [item["envelope_sha256"] for item in envelopes.values()]
    if len(set(identities)) != len(AI_CASE_ORDER):
        raise AiCaseEnvelopeError("AI envelope identities are not unique")
    return envelopes


def validate_ai_case_envelopes(value: object, *, allow_unbound: bool) -> None:
    if value == {} and allow_unbound:
        return
    expected = build_all_ai_case_envelopes()
    if not isinstance(value, dict) or tuple(value) != AI_CASE_ORDER or value != expected:
        raise AiCaseEnvelopeError("AI case envelopes do not match the frozen bindings")


def envelope_digest_map(envelopes: Mapping[str, object]) -> dict[str, str]:
    validate_ai_case_envelopes(envelopes, allow_unbound=False)
    return {case_id: envelopes[case_id]["envelope_sha256"] for case_id in AI_CASE_ORDER}


def canonical_envelopes_json() -> str:
    """Stable representation used only for offline review and reproducibility."""
    return canonical_json(build_all_ai_case_envelopes())
