"""Offline frozen-v3 sequence-4 generation-gate tests."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import tomllib
from dataclasses import replace
from pathlib import Path

import pytest

SCRIPT_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = SCRIPT_ROOT.parents[2]
BACKEND_ROOT = REPOSITORY_ROOT / "backend"
for value in (SCRIPT_ROOT, BACKEND_ROOT):
    if str(value) not in sys.path:
        sys.path.insert(0, str(value))

from run_openai_stage_b_v2_pilot import prepare_frozen_v2_pilot  # noqa: E402
from run_openai_stage_b_v3_pilot import (  # noqa: E402
    FROZEN_V3_MANIFEST_DIGEST,
    canonical_attempt_digest,
    deterministic_request_digest,
    prepare_frozen_v3_pilot,
)
from test_openai_stage_b_v2_pilot import rejected_stage_b_response, valid_response  # noqa: E402
from v3_sequence_4_generation_gate import (  # noqa: E402
    CANDIDATE_DIGEST,
    CANDIDATE_PATH,
    CANONICAL_ATTEMPT_DIGEST,
    MANIFEST_DIGEST,
    MANIFEST_PATH,
    OPERATOR_INTENT,
    PROVIDER_FINGERPRINT,
    REQUEST_DIGEST,
    Sequence4GenerationGateError,
    validate_generated_response,
    verify_candidate_and_preflight,
    verify_resolved_generation_candidate,
    verify_unresolved_generation_candidate,
)


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_v3_request_bindings_differ_from_v2_and_are_live_preflight_resolved() -> None:
    v2 = prepare_frozen_v2_pilot()
    v3 = prepare_frozen_v3_pilot()
    assert deterministic_request_digest(v3) == REQUEST_DIGEST
    assert canonical_attempt_digest(v3) == CANONICAL_ATTEMPT_DIGEST
    assert REQUEST_DIGEST != hashlib.sha256(
        v2.provider_request.deterministic_request_json.encode()
    ).hexdigest()
    assert v3.request.prompt_version == "moving-service-questions-prompt-v3"
    assert v3.request.schema_version == "moving-service-questions-schema-v3"
    assert v3.frozen_manifest["fallback_version"] == "moving-service-fallback-v2"
    assert v3.frozen_manifest["fallback_v2_reused"] is True
    assert verify_unresolved_generation_candidate()["binding_status"] == "fresh_v3_preflight_required"
    assert verify_resolved_generation_candidate()["binding_status"] == "approved_v3_preflight_bound"


def test_resolved_candidate_is_inactive_v3_only_and_digest_bound() -> None:
    candidate = tomllib.loads(CANDIDATE_PATH.read_text())
    manifest = json.loads(MANIFEST_PATH.read_text())
    assert _digest(CANDIDATE_PATH) == CANDIDATE_DIGEST
    assert _digest(MANIFEST_PATH) == MANIFEST_DIGEST
    assert manifest["candidate_digest"] == CANDIDATE_DIGEST
    assert candidate["metadata"]["active_repository_authority"] is False
    assert candidate["authorization"]["ai_generation_authorized"] is False
    assert candidate["required_v3_preflight"]["binding_status"] == "approved_v3_preflight_bound"
    assert candidate["required_v3_preflight"]["preflight_evidence_digest"] == "0de3756455a948472c53c34124a83815dde3ac7b89ec8b1743bbf6371b3c2360"
    assert candidate["required_v3_preflight"]["preflight_review_digest"] == "5e61e2a7eb6e1e4b054ca40dc3b7a9058cb6d10b3ba31096cde31e998f32ee20"
    assert candidate["required_v3_preflight"]["input_tokens"] == 2542
    assert candidate["required_v3_preflight"]["conservative_cost"] == "0.0018168"
    assert candidate["bindings"]["frozen_v3_manifest_digest"] == FROZEN_V3_MANIFEST_DIGEST
    assert candidate["bindings"]["prompt_version"] == "moving-service-questions-prompt-v3"
    assert candidate["bindings"]["schema_version"] == "moving-service-questions-schema-v3"
    assert candidate["scope"]["operator_intent"] == OPERATOR_INTENT
    assert candidate["scope"]["maximum_token_preflight_requests"] == 0
    assert candidate["scope"]["maximum_ai_generation_requests"] == 1
    assert candidate["scope"]["automatic_retries"] == 0


def test_exact_frozen_v3_artifact_digests() -> None:
    expected = {
        "manifest.json": "44da0c5005515784c2c13737ca12a4382c084f1aa56fea5b4a4d40e66fb8659c",
        "real-model-prompt.toml": "1146474ad5112a238446a63d4fc797022ca2cd65d8e9cb6c88935d7f4f3376e8",
        "openai-response-schema.json": "333d6923902c46662243e019074b735500904bc49acbafdc1b929bceed9924e2",
        "openai-response-schema-review.md": "d06f623b1c6daa2c939961325ec92afb9e0fe97f1c5e0e7d995bcf7e4034c96f",
        "provider-schema-adaptation.json": "e7bc2a8c96527759cda4398e2d09a138dec63c64d08add9ed38af51d53148247",
        "deterministic-baseline.json": "e2e185dac7411ad7bd7ea9ed049b9d7146c4e4e2ffa3d2125e67f84a72573dbc",
        "request-fixtures.json": "4edd377721d6d4e70b738508f44877f93dc6856e2eee2fc5da936f0dcce15eb9",
        "response-fixtures.json": "aca6178cbc0438edfe3646535ded2f27fab6fcf7f867793c71c5f14d9b1cf127",
        "expected-results.json": "e9c6fc8973ed05feb545721563b6f43cc3b348f5810c4bb1f7068e1a9afac67e",
        "synthetic-language-cases.json": "e138cf35d3e017441b823ccae14355102f06bc1a2bed8d30ad425d67a85bb0a1",
        "expected-language-results.json": "697f9374caf8fdc97c7979573b0560b66d80ce60bb1af346e292687f77a76a8e",
    }
    root = REPOSITORY_ROOT / "docs/experiments/suggest-moving-service-questions/v3"
    assert {name: _digest(root / name) for name in expected} == expected


def test_v3_validation_reuses_unchanged_semantic_prose_and_fallback_contracts() -> None:
    compliant = valid_response()
    compliant["prompt_version"] = "moving-service-questions-prompt-v3"
    compliant["schema_version"] = "moving-service-questions-schema-v3"
    assert validate_generated_response(compliant)[0] == "validated"

    rejected = rejected_stage_b_response()
    rejected["prompt_version"] = "moving-service-questions-prompt-v3"
    rejected["schema_version"] = "moving-service-questions-schema-v3"
    classification, codes = validate_generated_response(rejected)
    assert classification == "prose_failure"
    assert codes == (
        "irrelevant_location_reference",
        "unsupported_home_or_property_assertion",
        "storage_modality_overstatement",
        "unsupported_service_selection_language",
        "grounding_summary_mismatch",
    )
    assert validate_generated_response([])[0] == "structural_failure"
    semantic = valid_response()
    semantic["prompt_version"] = "moving-service-questions-prompt-v3"
    semantic["schema_version"] = "moving-service-questions-schema-v3"
    semantic["suggestions"][0]["selected_missing_information_category"] = "packing_preference"
    assert validate_generated_response(semantic)[0] == "semantic_failure"


def test_prompt_policy_stress_is_documented_as_stricter_than_lexical_validator() -> None:
    response = valid_response()
    response["prompt_version"] = "moving-service-questions-prompt-v3"
    response["schema_version"] = "moving-service-questions-schema-v3"
    response["suggestions"][0]["question"] = "Will you likely need temporary storage before final delivery?"
    response["suggestions"][0]["why_it_matters"] = "This can clarify appropriate, local moving services to discuss."
    classification, codes = validate_generated_response(response)
    assert classification == "validated"
    assert getattr(codes, "prompt_version") == "moving-service-questions-prompt-v3"


def test_cross_version_identities_and_provider_schemas_are_not_interchangeable() -> None:
    v2 = prepare_frozen_v2_pilot()
    v3 = prepare_frozen_v3_pilot()
    assert v2.request.prompt_version != v3.request.prompt_version
    assert v2.request.schema_version != v3.request.schema_version
    assert v2.provider_request.response_json_schema != v3.provider_request.response_json_schema
    with pytest.raises(Exception):
        type(v3.request).model_validate(v2.request.model_dump())
    with pytest.raises(Exception):
        type(v2.request).model_validate(v3.request.model_dump())


def test_no_v3_runtime_or_frontend_exposure() -> None:
    excluded = {SCRIPT_ROOT / "test_v3_sequence_4_generation_gate.py"}
    roots = [REPOSITORY_ROOT / "backend/app", REPOSITORY_ROOT / "frontend/src"]
    for root in roots:
        for path in root.rglob("*"):
            if path.is_file() and path not in excluded:
                assert "moving-service-questions-prompt-v3" not in path.read_text(errors="ignore")
