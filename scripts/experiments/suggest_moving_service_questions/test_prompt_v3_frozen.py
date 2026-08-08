"""Offline integrity and isolation tests for the frozen prompt-v3 package."""

from __future__ import annotations

import hashlib
import json
import tomllib
from pathlib import Path

import pytest
from pydantic import ValidationError

from freeze_prompt_v3_artifacts import finalized_prompt_text, schema_diff_record
from moving_service_questions_v2 import (
    FALLBACK_VERSION_V2,
    PROSE_VIOLATION_CODE_ORDER,
    MovingServiceQuestionResponseV2,
    _contains_selection_language,
    _contains_storage_modality_overstatement,
    validate_response_v2,
)
from moving_service_questions_v3 import (
    PROMPT_VERSION_V3,
    SCHEMA_VERSION_V3,
    MovingServiceQuestionRequestV3,
    MovingServiceQuestionResponseV3,
    adapt_response_schema_for_openai_v3,
)
from run_openai_stage_b_v2_pilot import prepare_frozen_v2_pilot


ROOT = Path(__file__).resolve().parents[3]
CAPABILITY = ROOT / "docs/experiments/suggest-moving-service-questions"
V1 = CAPABILITY / "v1"
V2 = CAPABILITY / "v2"
V3 = CAPABILITY / "v3"
DRAFT = CAPABILITY / "v3-draft"
VALIDATOR = ROOT / "scripts/experiments/suggest_moving_service_questions/moving_service_questions_v2.py"

FROZEN_V1_MANIFEST = "6ca134ff1aad2994830eafa2aa5c17e96e798e18eeae4057c126450a3719f080"
FROZEN_V2_MANIFEST = "3fb5d63b438f7658f319b3300885cea1d27c307bec30d6c2b85fdb8ca5d7741e"
FROZEN_V2_PROMPT = "9bcc190f9c4c51fba1caed8c5d284de9d29d6fe8d675132a04f741cc9a1af7a6"
UNCHANGED_V2_VALIDATOR = "8b00becd2a6491ec5c2fbc267732fbe685cacf509899994480fc4052baf8af33"

FROZEN_V3_DIGESTS = {
    "real-model-prompt.toml": "1146474ad5112a238446a63d4fc797022ca2cd65d8e9cb6c88935d7f4f3376e8",
    "openai-response-schema.json": "333d6923902c46662243e019074b735500904bc49acbafdc1b929bceed9924e2",
    "openai-response-schema-review.md": "d06f623b1c6daa2c939961325ec92afb9e0fe97f1c5e0e7d995bcf7e4034c96f",
    "provider-schema-adaptation.json": "e7bc2a8c96527759cda4398e2d09a138dec63c64d08add9ed38af51d53148247",
    "schema-v2-v3-diff.json": "aa56116fad48eb13ee50bdf45343e64debe5836c198b9f0ae98e88f7ff8d5e48",
    "deterministic-baseline.json": "e2e185dac7411ad7bd7ea9ed049b9d7146c4e4e2ffa3d2125e67f84a72573dbc",
    "request-fixtures.json": "4edd377721d6d4e70b738508f44877f93dc6856e2eee2fc5da936f0dcce15eb9",
    "response-fixtures.json": "aca6178cbc0438edfe3646535ded2f27fab6fcf7f867793c71c5f14d9b1cf127",
    "expected-results.json": "e9c6fc8973ed05feb545721563b6f43cc3b348f5810c4bb1f7068e1a9afac67e",
    "knowledge-source-review.md": "cb752f280fe6c79c28cd80ff0d10bdb2b751e3af804ee270563b1fc6a89555d7",
    "synthetic-language-cases.json": "e138cf35d3e017441b823ccae14355102f06bc1a2bed8d30ad425d67a85bb0a1",
    "expected-language-results.json": "697f9374caf8fdc97c7979573b0560b66d80ce60bb1af346e292687f77a76a8e",
    "freeze-record.md": "337bbe553d3b459068ab5d16a1a3f7e53f3e03f0a1b29d9c474ee21570c27b55",
}
FROZEN_V3_MANIFEST = "44da0c5005515784c2c13737ca12a4382c084f1aa56fea5b4a4d40e66fb8659c"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _cases() -> list[dict[str, object]]:
    return json.loads((V3 / "synthetic-language-cases.json").read_text())["cases"]


def _validator_rejects(case: dict[str, object]) -> bool:
    values = case.get("texts", [case.get("text")])
    assert isinstance(values, list)
    if case["class"] == "storage":
        return any(_contains_storage_modality_overstatement(str(value)) for value in values)
    if case["class"] == "service":
        return any(_contains_selection_language(str(value)) for value in values)
    return any(
        _contains_storage_modality_overstatement(str(value))
        or _contains_selection_language(str(value))
        for value in values
    )


def test_frozen_v3_digests_reject_every_artifact_drift() -> None:
    manifest = json.loads((V3 / "manifest.json").read_text())
    assert manifest["artifact_digests"] == FROZEN_V3_DIGESTS
    for name, expected in FROZEN_V3_DIGESTS.items():
        assert _sha(V3 / name) == expected
    assert _sha(V3 / "manifest.json") == FROZEN_V3_MANIFEST


def test_v1_v2_and_existing_validator_remain_exact() -> None:
    assert _sha(V1 / "manifest.json") == FROZEN_V1_MANIFEST
    assert _sha(V2 / "manifest.json") == FROZEN_V2_MANIFEST
    assert _sha(V2 / "real-model-prompt.toml") == FROZEN_V2_PROMPT
    assert _sha(VALIDATOR) == UNCHANGED_V2_VALIDATOR
    assert PROSE_VIOLATION_CODE_ORDER == (
        "irrelevant_location_reference",
        "unsupported_home_or_property_assertion",
        "storage_modality_overstatement",
        "unsupported_service_selection_language",
        "grounding_summary_mismatch",
    )


def test_frozen_prompt_is_exact_generator_output_and_closed() -> None:
    assert (V3 / "real-model-prompt.toml").read_text() == finalized_prompt_text()
    prompt = tomllib.loads((V3 / "real-model-prompt.toml").read_text())
    assert prompt["metadata"]["prompt_version"] == PROMPT_VERSION_V3
    assert prompt["metadata"]["compatible_request_schema_version"] == SCHEMA_VERSION_V3
    assert prompt["metadata"]["compatible_response_schema_version"] == SCHEMA_VERSION_V3
    assert prompt["serialization"]["source_model"] == "MovingServiceQuestionRequestV3"
    assert prompt["structured_output"]["response_model"] == "MovingServiceQuestionResponseV3"
    assert prompt["examples"]["positive_examples_included"] is False
    assert prompt["readiness"]["prompt_v3_approved"] is True
    for key in (
        "follow_up_pilot_authorized",
        "credential_access_authorized",
        "token_preflight_authorized",
        "ai_generation_authorized",
        "stage_c_authorized",
        "production_use_authorized",
    ):
        assert prompt["readiness"][key] is False


def test_schema_v3_change_is_literal_and_title_only() -> None:
    v2_request = prepare_frozen_v2_pilot().request.__class__.model_json_schema()
    v3_request = MovingServiceQuestionRequestV3.model_json_schema()
    v2_response = MovingServiceQuestionResponseV2.model_json_schema()
    v3_response = MovingServiceQuestionResponseV3.model_json_schema()
    assert schema_diff_record(v2_response, v3_response)["normalized_schemas_equal"] is True

    def normalized(value: object) -> object:
        if isinstance(value, dict):
            return {key: normalized(item) for key, item in value.items() if key != "title"}
        if isinstance(value, list):
            return [normalized(item) for item in value]
        return {
            PROMPT_VERSION_V3: "moving-service-questions-prompt-v2",
            SCHEMA_VERSION_V3: "moving-service-questions-schema-v2",
        }.get(value, value)

    assert normalized(v2_request) == normalized(v3_request)
    assert normalized(v2_response) == normalized(v3_response)
    record = json.loads((V3 / "schema-v2-v3-diff.json").read_text())
    assert record["fields_changed"] == []
    assert all(
        record[key] is False
        for key in (
            "required_lists_changed",
            "types_changed",
            "enums_changed",
            "constraints_changed",
            "nested_structures_changed",
            "additional_properties_behavior_changed",
        )
    )


def test_provider_schema_is_the_title_only_adaptation() -> None:
    generated = MovingServiceQuestionResponseV3.model_json_schema()
    expected = adapt_response_schema_for_openai_v3(generated)
    assert json.loads((V3 / "openai-response-schema.json").read_text()) == expected
    serialized = json.dumps(expected)
    assert '"title"' not in serialized
    assert '"additionalProperties": false' in serialized
    assert expected["properties"]["prompt_version"]["const"] == PROMPT_VERSION_V3
    assert expected["properties"]["schema_version"]["const"] == SCHEMA_VERSION_V3


def test_v3_fixtures_validate_with_unchanged_v2_semantics() -> None:
    prepared = prepare_frozen_v2_pilot()
    cases = json.loads((V3 / "response-fixtures.json").read_text())["cases"]
    assert {case["response_fixture_id"] for case in cases} == {
        "valid_storage_suggestion_v3",
        "valid_zero_suggestions_v3",
        "invalid_multiple_prose_violations_v3",
    }
    for case in cases:
        v3_response = MovingServiceQuestionResponseV3.model_validate(case["response"])
        v2_document = v3_response.model_dump(mode="json")
        v2_document["prompt_version"] = "moving-service-questions-prompt-v2"
        v2_document["schema_version"] = "moving-service-questions-schema-v2"
        if case["expected_valid"]:
            validated = validate_response_v2(prepared.request, v2_document)
            assert len(validated.suggestions) <= 1
        else:
            from moving_service_questions_v2 import ProseValidationError

            with pytest.raises(ProseValidationError) as error:
                validate_response_v2(prepared.request, v2_document)
            assert list(error.value.violation_codes) == case["expected_violation_codes"]


def test_v3_and_v2_mixed_identities_fail_closed() -> None:
    prepared = prepare_frozen_v2_pilot()
    request_document = prepared.request.model_dump(mode="json")
    request_document["prompt_version"] = PROMPT_VERSION_V3
    request_document["schema_version"] = SCHEMA_VERSION_V3
    assert MovingServiceQuestionRequestV3.model_validate(request_document)
    with pytest.raises(ValidationError):
        MovingServiceQuestionRequestV3.model_validate(prepared.request.model_dump(mode="json"))
    with pytest.raises(ValidationError):
        prepared.request.__class__.model_validate(request_document)


def test_synthetic_policy_and_unchanged_validator_are_consistent() -> None:
    cases = _cases()
    expected = json.loads((V3 / "expected-language-results.json").read_text())
    assert len(cases) == 28
    for case in cases:
        assert _validator_rejects(case) is case["validator_rejected"], case["id"]
        if case["prompt_v3_status"] == "allowed":
            assert case["validator_rejected"] is False, case["id"]
    mismatches = {
        case["id"]
        for case in cases
        if case["prompt_v3_status"] == "prohibited" and not case["validator_rejected"]
    }
    assert mismatches == set(expected["known_mismatch_ids"])
    assert len(mismatches) == 5


def test_fallback_and_approved_scope_semantics_remain_v2() -> None:
    manifest = json.loads((V3 / "manifest.json").read_text())
    expected = json.loads((V3 / "expected-results.json").read_text())
    assert manifest["fallback_version"] == FALLBACK_VERSION_V2
    assert manifest["fallback_v2_reused"] is True
    assert expected["prose_validation"]["fallback_version"] == FALLBACK_VERSION_V2
    assert all(case["expected_suggestion_count"] in (0, 1) for case in expected["cases"])
    nonempty = [case for case in expected["cases"] if case["expected_suggestion_count"] == 1]
    assert {case["expected_category"] for case in nonempty} == {"temporary_storage_need"}


def test_v3_package_has_no_live_configuration_or_authorization() -> None:
    names = {path.name for path in V3.iterdir()}
    assert "openai-follow-up-pilot.toml" not in names
    assert not any("authorization" in name for name in names)
    manifest = json.loads((V3 / "manifest.json").read_text())
    for key in (
        "live_generation_authorized",
        "credential_access_authorized",
        "token_preflight_authorized",
        "formal_evaluation_authorized",
        "stage_c_authorized",
        "production_use_authorized",
        "fastapi_exposure_authorized",
        "frontend_exposure_authorized",
    ):
        assert manifest[key] is False


def test_prompt_v3_has_no_backend_frontend_or_authorization_reachability() -> None:
    assert not any(
        "moving-service-questions-prompt-v3" in path.read_text(errors="ignore")
        for path in (ROOT / "backend").rglob("*")
        if path.is_file()
    )
    assert not any(
        "moving-service-questions-prompt-v3" in path.read_text(errors="ignore")
        for path in (ROOT / "frontend/src").rglob("*")
        if path.is_file()
    )
    operational = [
        path
        for path in (ROOT / "scripts/experiments/suggest_moving_service_questions").glob("*.py")
        if path.name not in {
            "moving_service_questions_v3.py",
            "freeze_prompt_v3_artifacts.py",
            "openai_transport_v3.py",
            "run_openai_stage_b_v3_pilot.py",
            "run_openai_stage_b_v3_sequence_4_generation_live.py",
            "run_openai_stage_b_v3_sequence_4_generation_synthetic.py",
            "test_prompt_v3_draft.py",
            "test_prompt_v3_frozen.py",
            "test_v3_sequence_4_generation_gate.py",
            "test_v3_sequence_4_generation_operator_boundary.py",
            "v3_sequence_4_generation_gate.py",
            "v3_sequence_4_generation_operator_cli.py",
            "v3_sequence_4_generation_rehearsal_assertions.py",
        }
    ]
    assert not any(
        "moving-service-questions-prompt-v3" in path.read_text(errors="ignore")
        for path in operational
    )
