"""Offline freeze, policy, preparation, and isolation tests for prompt v4."""

from __future__ import annotations

import hashlib
import json
import tomllib
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.moving_service_questions import STORAGE_KNOWLEDGE
from freeze_prompt_v4_artifacts import finalized_prompt_text, schema_diff_record
from freeze_prompt_v4_artifacts import (
    CANONICAL_ATTEMPT_DIGEST, DETERMINISTIC_REQUEST_DIGEST, PROVIDER_FINGERPRINT,
)
from moving_service_questions_v2 import (
    FALLBACK_VERSION_V2, MovingServiceQuestionResponseV2,
    _contains_selection_language, _contains_storage_modality_overstatement,
    validate_response_v2,
)
from moving_service_questions_v3 import MovingServiceQuestionRequestV3, MovingServiceQuestionResponseV3
from moving_service_questions_v4 import (
    PROMPT_VERSION_V4, SCHEMA_VERSION_V4, MovingServiceQuestionRequestV4,
    MovingServiceQuestionResponseV4, adapt_response_schema_for_openai_v4,
)
from openai_transport_v4 import make_v4_openai_transport
from rejected_prose_diagnostics import RULE_ID, collect_prose_violation_diagnostics
from run_openai_stage_b_v2_pilot import prepare_frozen_v2_pilot
from run_openai_stage_b_v3_pilot import prepare_frozen_v3_pilot
from run_openai_stage_b_v4_pilot import (
    CLOSED_GROUNDING_TRIGGERS, FROZEN_V4_MANIFEST_DIGEST, ProhibitedGroundingSourceError,
    canonical_attempt, canonical_attempt_digest, deterministic_request_digest,
    grounding_source_triggers, prepare_frozen_v4_pilot, validate_grounding_source,
)
from test_openai_stage_b_v2_pilot import valid_response

ROOT = Path(__file__).resolve().parents[3]
CAPABILITY = ROOT / "docs/experiments/suggest-moving-service-questions"
V4 = CAPABILITY / "v4"
VALIDATOR = ROOT / "scripts/experiments/suggest_moving_service_questions/moving_service_questions_v2.py"
REQUEST_IDENTITY = V4 / "request-identity.json"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _downgrade(response: MovingServiceQuestionResponseV4) -> MovingServiceQuestionResponseV2:
    value = response.model_dump(mode="json")
    value["prompt_version"] = "moving-service-questions-prompt-v2"
    value["schema_version"] = "moving-service-questions-schema-v2"
    return MovingServiceQuestionResponseV2.model_validate(value)


def _validate_request_identity(value: dict[str, object]) -> None:
    expected = {
        "deterministic_request_sha256": DETERMINISTIC_REQUEST_DIGEST,
        "canonical_attempt_sha256": CANONICAL_ATTEMPT_DIGEST,
        "provider_fingerprint": PROVIDER_FINGERPRINT,
    }
    for key, exact in expected.items():
        if value.get(key) != exact:
            raise ValueError(f"frozen v4 request identity drifted: {key}")


def test_manifest_binds_every_exact_artifact_and_design() -> None:
    manifest = json.loads((V4 / "manifest.json").read_text())
    assert _sha(V4 / "manifest.json") == FROZEN_V4_MANIFEST_DIGEST
    assert manifest["source_design_memo_digest"] == "5f4d171adfbc9213714b85c7fe0e9421d87b44847c1fdf3f744c093d024ae09d"
    assert manifest["source_frozen_v3_manifest_digest"] == "44da0c5005515784c2c13737ca12a4382c084f1aa56fea5b4a4d40e66fb8659c"
    for name, expected in manifest["artifact_digests"].items():
        assert _sha(V4 / name) == expected
    assert manifest["artifact_digests"]["request-identity.json"] == _sha(REQUEST_IDENTITY)
    assert manifest["fallback_version"] == FALLBACK_VERSION_V2
    assert manifest["fallback_question_id"] == "fallback-temporary-storage-v2"
    assert all(manifest[key] is False for key in (
        "live_generation_authorized", "credential_access_authorized", "token_preflight_authorized",
        "formal_evaluation_authorized", "stage_c_authorized", "production_use_authorized",
        "fastapi_exposure_authorized", "frontend_exposure_authorized",
    ))


def test_frozen_prompt_is_exact_minimal_generator_output() -> None:
    assert (V4 / "real-model-prompt.toml").read_text() == finalized_prompt_text()
    prompt = tomllib.loads((V4 / "real-model-prompt.toml").read_text())
    text = prompt["system_instructions"]
    assert prompt["metadata"]["prompt_version"] == PROMPT_VERSION_V4
    assert prompt["metadata"]["compatible_request_schema_version"] == SCHEMA_VERSION_V4
    assert "Treat curated knowledge as evidence, not as a writing style" in text
    assert "Closed runtime lexical rule" in text
    assert "Before returning JSON, inspect every generated value" in text
    assert "Never rewrite `grounding_summary`" in text
    assert prompt["examples"]["positive_examples_included"] is False


def test_v4_schema_is_literal_and_title_only() -> None:
    record = schema_diff_record(MovingServiceQuestionResponseV3.model_json_schema(),
                                MovingServiceQuestionResponseV4.model_json_schema())
    assert record["normalized_schemas_equal"] is True
    assert record["fields_changed"] == []
    assert all(record[key] is False for key in (
        "required_lists_changed", "types_changed", "enums_changed", "constraints_changed",
        "nested_structures_changed", "additional_properties_behavior_changed",
    ))
    assert json.loads((V4 / "schema-v3-v4-diff.json").read_text()) == record
    v3_request = MovingServiceQuestionRequestV3.model_json_schema()
    v4_request = MovingServiceQuestionRequestV4.model_json_schema()
    serialized = json.dumps(v4_request).replace(PROMPT_VERSION_V4, "moving-service-questions-prompt-v3").replace(
        SCHEMA_VERSION_V4, "moving-service-questions-schema-v3").replace(
        "MovingServiceQuestionRequestV4", "MovingServiceQuestionRequestV3")
    assert json.loads(serialized) == v3_request


def test_provider_schema_is_unchanged_strict_adaptation() -> None:
    expected = adapt_response_schema_for_openai_v4(MovingServiceQuestionResponseV4.model_json_schema())
    assert json.loads((V4 / "openai-response-schema.json").read_text()) == expected
    encoded = json.dumps(expected)
    assert '"title"' not in encoded
    assert '"additionalProperties": false' in encoded
    assert expected["properties"]["prompt_version"]["const"] == PROMPT_VERSION_V4


@pytest.mark.parametrize("statement,trigger", [
    ("Storage is required.", "required"), ("Storage is a REQUIREMENT.", "requirement"),
    ("Storage MuSt wait.", "must"), ("Storage WILL\n NEED review.", "will need"),
    ("Required storage must wait and will need review.", "required"),
])
def test_grounding_closed_triggers_fail_before_provider_request(statement: str, trigger: str) -> None:
    calls = []
    with pytest.raises(ProhibitedGroundingSourceError) as error:
        prepare_frozen_v4_pilot(grounding_statement=statement,
                                provider_request_constructor=lambda **kwargs: calls.append(kwargs))
    assert error.value.classification == "prohibited_grounding_source"
    assert trigger in grounding_source_triggers(statement)
    assert calls == []


@pytest.mark.parametrize("statement", [
    "Storage may be needed.", "Storage might be needed.", "Storage could be needed.",
    "Storage and mustard.", "A requirementful storage note.",
])
def test_harmless_grounding_forms_pass_lexical_precheck(statement: str) -> None:
    assert grounding_source_triggers(statement) == ()
    validate_grounding_source(statement)


def test_exact_approved_grounding_passes_and_is_byte_exact() -> None:
    validate_grounding_source(STORAGE_KNOWLEDGE.statement)
    prepared = prepare_frozen_v4_pilot()
    assert prepared.request.curated_knowledge_items[0].statement == STORAGE_KNOWLEDGE.statement
    fixtures = json.loads((V4 / "response-fixtures.json").read_text())["cases"]
    valid = next(case for case in fixtures if case["expected_valid"] and case["response"]["suggestions"])
    assert valid["response"]["suggestions"][0]["grounding_summary"] == STORAGE_KNOWLEDGE.statement


def test_all_fifteen_policy_cases_separate_prompt_and_runtime_expectations() -> None:
    artifact = json.loads((V4 / "adversarial-policy-cases.json").read_text())
    expected = json.loads((V4 / "expected-policy-results.json").read_text())
    assert len(artifact["cases"]) == 15
    for case in artifact["cases"]:
        runtime = (_contains_storage_modality_overstatement(case["text"])
                   or _contains_selection_language(case["text"]))
        assert runtime is case["runtime_validator_rejected"], case["id"]
        assert expected["case_expectations"][case["id"]] == {
            "prompt_policy": case["prompt_policy"],
            "runtime_validator_rejected": case["runtime_validator_rejected"],
        }


def test_v4_fixtures_reuse_unchanged_semantics_and_validator() -> None:
    prepared = prepare_frozen_v2_pilot()
    for case in json.loads((V4 / "response-fixtures.json").read_text())["cases"]:
        response = MovingServiceQuestionResponseV4.model_validate(case["response"])
        value = _downgrade(response).model_dump(mode="json")
        if case["expected_valid"]:
            assert validate_response_v2(prepared.request, value)
        else:
            with pytest.raises(Exception):
                validate_response_v2(prepared.request, value)


def test_rejected_prose_diagnostics_are_version_compatible_and_bounded() -> None:
    raw = valid_response()
    raw["prompt_version"] = PROMPT_VERSION_V4
    raw["schema_version"] = SCHEMA_VERSION_V4
    raw["suggestions"][0]["question"] = "PRIVATE PREFIX storage WILL\n NEED review PRIVATE SUFFIX"
    response = MovingServiceQuestionResponseV4.model_validate(raw)
    diagnostics = collect_prose_violation_diagnostics(prepare_frozen_v2_pilot().request,
                                                       _downgrade(response))
    assert [(item.violation_code, item.rule_id, item.field, item.canonical_trigger) for item in diagnostics] == [
        ("storage_modality_overstatement", RULE_ID, "question", "will need")
    ]
    encoded = json.dumps([item.as_dict() for item in diagnostics])
    assert "PRIVATE PREFIX" not in encoded and "PRIVATE SUFFIX" not in encoded


def test_request_construction_and_gate_architecture_rebind_without_structural_change() -> None:
    v3 = prepare_frozen_v3_pilot()
    v4 = prepare_frozen_v4_pilot()
    config = json.loads((V4 / "offline-pilot-request-config.json").read_text())
    assert v4.request.prompt_version == PROMPT_VERSION_V4
    assert v4.request.schema_version == SCHEMA_VERSION_V4
    assert v4.provider_request.model_identifier == v3.provider_request.model_identifier == config["model"]
    assert v4.provider_request.model_parameters == v3.provider_request.model_parameters == {"temperature": 0}
    assert v4.provider_request.maximum_output_tokens == v3.provider_request.maximum_output_tokens == 500
    assert v4.provider_request.timeout_seconds == v3.provider_request.timeout_seconds == 12
    assert v4.provider_request.retry_count == v3.provider_request.retry_count == 0
    assert config["top_p"] == "omitted" and config["seed"] == "omitted"
    assert config["truncation"] == "disabled" and config["token_preflight_timeout_seconds"] == 5
    assert config["maximum_total_spend_usd"] == "0.03"
    identity = json.loads(REQUEST_IDENTITY.read_text())
    _validate_request_identity(identity)
    assert identity["prompt_version"] == PROMPT_VERSION_V4
    assert identity["schema_version"] == SCHEMA_VERSION_V4
    assert identity["fixture"] == config["fixture"] == "storage_unknown"
    assert identity["category"] == config["category"] == "temporary_storage_need"
    assert identity["provider"] == config["provider"] == "OpenAI"
    assert identity["ai_model_identifier"] == config["model"] == "gpt-4.1-mini-2025-04-14"
    assert identity["sdk"] == config["sdk"] == "openai==2.45.0"
    assert deterministic_request_digest(v4) == identity["deterministic_request_sha256"] == DETERMINISTIC_REQUEST_DIGEST
    assert canonical_attempt_digest(v4) == identity["canonical_attempt_sha256"] == CANONICAL_ATTEMPT_DIGEST
    assert deterministic_request_digest(v4) != deterministic_request_digest(v3)
    assert canonical_attempt_digest(v4) != canonical_attempt_digest(v3)
    attempt = canonical_attempt(v4)
    assert attempt["store"] is False and attempt["stream"] is False and attempt["background"] is False
    assert "tools" not in attempt and config["tools"] == []
    fingerprint = make_v4_openai_transport(
        client=SimpleNamespace(max_retries=0), prepared=v4
    ).request_fingerprint(v4.provider_request)
    assert fingerprint == identity["provider_fingerprint"] == PROVIDER_FINGERPRINT


@pytest.mark.parametrize("key", [
    "deterministic_request_sha256", "canonical_attempt_sha256", "provider_fingerprint",
])
def test_each_frozen_request_identity_mutation_fails_validation(key: str) -> None:
    identity = json.loads(REQUEST_IDENTITY.read_text())
    identity[key] = "0" * 64
    with pytest.raises(ValueError, match=rf"request identity drifted: {key}"):
        _validate_request_identity(identity)
    mutated_bytes = (json.dumps(identity, indent=2, sort_keys=True) + "\n").encode()
    manifest = json.loads((V4 / "manifest.json").read_text())
    assert hashlib.sha256(mutated_bytes).hexdigest() != manifest["artifact_digests"]["request-identity.json"]


def test_cross_version_identity_isolation_and_no_runtime_reachability() -> None:
    v3 = prepare_frozen_v3_pilot().request.model_dump(mode="json")
    v4 = prepare_frozen_v4_pilot().request.model_dump(mode="json")
    with pytest.raises(ValidationError):
        MovingServiceQuestionRequestV4.model_validate(v3)
    with pytest.raises(ValidationError):
        MovingServiceQuestionRequestV3.model_validate(v4)
    assert not any(PROMPT_VERSION_V4 in path.read_text(errors="ignore")
                   for root in (ROOT / "backend", ROOT / "frontend/src")
                   for path in root.rglob("*") if path.is_file())


def test_immutable_validator_and_frozen_v3_are_exact() -> None:
    assert _sha(VALIDATOR) == "8b00becd2a6491ec5c2fbc267732fbe685cacf509899994480fc4052baf8af33"
    assert _sha(CAPABILITY / "v3/manifest.json") == "44da0c5005515784c2c13737ca12a4382c084f1aa56fea5b4a4d40e66fb8659c"
    assert CLOSED_GROUNDING_TRIGGERS == ("required", "requirement", "must", "will need")
