import hashlib
import json
import sys
import tomllib
from pathlib import Path

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT_ROOT = (
    REPOSITORY_ROOT
    / "scripts/experiments/suggest_moving_service_questions"
)
V1_ROOT = (
    REPOSITORY_ROOT
    / "docs/experiments/suggest-moving-service-questions/v1"
)
V2_ROOT = (
    REPOSITORY_ROOT
    / "docs/experiments/suggest-moving-service-questions/v2"
)
if str(EXPERIMENT_ROOT) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_ROOT))

from app.moving_service_questions import (  # noqa: E402
    STORAGE_KNOWLEDGE,
    ExperimentFixture,
    MovingServiceQuestionRequest,
    MovingServiceQuestionResponse,
    build_trusted_fixture,
)
from moving_service_questions_v2 import (  # noqa: E402
    FALLBACK_QUESTIONS_V2,
    FALLBACK_VERSION_V2,
    PROSE_VIOLATION_CODE_ORDER,
    PROMPT_VERSION_V2,
    SCHEMA_VERSION_V2,
    MovingServiceQuestionRequestV2,
    MovingServiceQuestionResponseV2,
    ProseValidationError,
    adapt_response_schema_for_openai_v2,
    construct_request_v2,
    select_fallback_v2,
    validate_response_v2,
)


FROZEN_V1_DIGESTS = {
    "real-model-prompt.toml": (
        "583a4bdf59c4c4ac67c82928415710c3d5c21ac9912ebd4888a026b8fd4acbf2"
    ),
    "openai-run-configuration.toml": (
        "e665e04b56d8aeaa01f4c9df2fd2f5f4eed37150802fdba869cba54d1e5bc782"
    ),
    "openai-response-schema.json": (
        "9e5a3a667a1049d150734fd16669dad98cc982c2dc7a9a18f3e0b8cb3e891afb"
    ),
    "openai-execution-authorization.toml": (
        "6e3ca9cb4488764f012703ab77daae4f4b952895100f7d935935aeb6a0978be5"
    ),
}
HISTORICAL_V1_PACKAGE_DIGESTS = {
    "deterministic-baseline.json": (
        "2db6ccaecdc3e933513293318818666196ac9ff813b82aa8af19b1c675c47e9a"
    ),
    "expected-results.json": (
        "b5333a2675f4008e9b5bd1f251fba1e0f59c03d8a0e517d311d6446f5eaf1cc9"
    ),
    "knowledge-source-review.md": (
        "108c9e1639461ec25d1be11cd24642bca4b2072cd73790e21ee440b4f1251dda"
    ),
    "manifest.json": (
        "6ca134ff1aad2994830eafa2aa5c17e96e798e18eeae4057c126450a3719f080"
    ),
    "response-fixtures.json": (
        "fc9d1ce9e88bbe57d7490e3cb843d4aa170a5b3b34419d912f58d6ba6c3f07b0"
    ),
}
FROZEN_V2_ARTIFACT_DIGESTS = {
    "real-model-prompt.toml": (
        "9bcc190f9c4c51fba1caed8c5d284de9d29d6fe8d675132a04f741cc9a1af7a6"
    ),
    "openai-response-schema.json": (
        "822f23e6c0fc9845626e05bd8131fd5e30a0933f8fd268296ae688cc67ebf411"
    ),
    "openai-response-schema-review.md": (
        "af49358cd9b390009dede7e29f38fbc3dfed0d9bc6f5a8117f3a88ea7e38bff5"
    ),
    "provider-schema-adaptation.json": (
        "65739b0adc523aaef2af53617a2541cc6f94e0cc450b4a35b39794667fe785b1"
    ),
    "deterministic-baseline.json": (
        "daf72f467845adc1e5f73bdaa51179584c5765d5f4f959e6b0c50500a7c668d7"
    ),
    "request-fixtures.json": (
        "4027cd31286244f45af409653ba13115cc25aa19f23a5bbeff2c7e482281b18e"
    ),
    "response-fixtures.json": (
        "42c494dbbb9dba4874e40ff459578a8b68829cb507d76ddaacbf315c7f1b7115"
    ),
    "expected-results.json": (
        "72eb888f789ac90c6ea5ea7dc6d9fa3d384e740d46065772d0d936aa1dcd2c1e"
    ),
    "openai-follow-up-pilot.toml": (
        "08d1d6781cae9150c059736ea92e119226234c8e53c798766f2901f010499ad3"
    ),
}
FROZEN_V2_MANIFEST_DIGEST = (
    "3fb5d63b438f7658f319b3300885cea1d27c307bec30d6c2b85fdb8ca5d7741e"
)


def test_frozen_v1_artifact_digests_remain_unchanged() -> None:
    for filename, expected in FROZEN_V1_DIGESTS.items():
        digest = hashlib.sha256((V1_ROOT / filename).read_bytes()).hexdigest()
        assert digest == expected


def test_historical_v1_package_bytes_remain_unchanged() -> None:
    for filename, expected in HISTORICAL_V1_PACKAGE_DIGESTS.items():
        digest = hashlib.sha256((V1_ROOT / filename).read_bytes()).hexdigest()
        assert digest == expected


def test_frozen_v2_artifact_and_manifest_digests_reject_drift() -> None:
    manifest = json.loads((V2_ROOT / "manifest.json").read_text())
    assert manifest["artifact_digests"] == FROZEN_V2_ARTIFACT_DIGESTS
    for filename, expected in FROZEN_V2_ARTIFACT_DIGESTS.items():
        digest = hashlib.sha256((V2_ROOT / filename).read_bytes()).hexdigest()
        assert digest == expected
    digest = hashlib.sha256((V2_ROOT / "manifest.json").read_bytes()).hexdigest()
    assert digest == FROZEN_V2_MANIFEST_DIGEST


def _normalized_versioned_schema(
    schema: dict,
    *,
    prompt_version: str,
    schema_version: str,
) -> dict:
    normalized = json.loads(json.dumps(schema))
    normalized.pop("title", None)
    normalized["properties"]["prompt_version"]["const"] = "<prompt-version>"
    normalized["properties"]["schema_version"]["const"] = "<schema-version>"
    normalized["properties"]["prompt_version"].pop("title", None)
    normalized["properties"]["schema_version"].pop("title", None)
    assert schema["properties"]["prompt_version"]["const"] == prompt_version
    assert schema["properties"]["schema_version"]["const"] == schema_version
    return normalized


def test_v2_schemas_change_only_identity_literals() -> None:
    assert _normalized_versioned_schema(
        MovingServiceQuestionRequest.model_json_schema(),
        prompt_version="moving-service-questions-prompt-v1",
        schema_version="moving-service-questions-schema-v1",
    ) == _normalized_versioned_schema(
        MovingServiceQuestionRequestV2.model_json_schema(),
        prompt_version=PROMPT_VERSION_V2,
        schema_version=SCHEMA_VERSION_V2,
    )
    assert _normalized_versioned_schema(
        MovingServiceQuestionResponse.model_json_schema(),
        prompt_version="moving-service-questions-prompt-v1",
        schema_version="moving-service-questions-schema-v1",
    ) == _normalized_versioned_schema(
        MovingServiceQuestionResponseV2.model_json_schema(),
        prompt_version=PROMPT_VERSION_V2,
        schema_version=SCHEMA_VERSION_V2,
    )


def test_v2_prompt_is_parseable_frozen_and_without_examples() -> None:
    prompt = tomllib.loads((V2_ROOT / "real-model-prompt.toml").read_text())

    assert prompt["metadata"] == {
        "capability": "suggest_moving_service_questions",
        "prompt_version": PROMPT_VERSION_V2,
        "compatible_request_schema_version": SCHEMA_VERSION_V2,
        "compatible_response_schema_version": SCHEMA_VERSION_V2,
        "compatible_knowledge_fixture_version": (
            "moving-service-storage-fixture-v2"
        ),
        "maximum_questions": 3,
        "preferred_questions": 1,
        "maximum_input_tokens": 3000,
        "maximum_output_tokens": 500,
        "formal_evaluation_retries": 0,
        "evaluation_only": True,
        "production_use_prohibited": True,
        "live_research_prohibited": True,
        "prompt_status": "approved_and_frozen",
        "prompt_artifact_digest_status": "authoritative_digest_in_v2_manifest",
    }
    assert prompt["examples"]["positive_examples_included"] is False
    assert prompt["structured_output"]["human_grounding_review_required"] is True
    assert (
        "For prompt v2, `temporary_storage_need` is the only supported nonempty\n"
        "missing-information category. Do not suggest a question for any other\n"
        "category."
    ) in prompt["system_instructions"]
    assert prompt["readiness"] == {
        "draft": False,
        "reviewed": True,
        "ready_for_human_review": False,
        "prompt_v2_approved": True,
        "frozen_for_adapter_implementation": True,
        "frozen_for_real_model_execution": False,
        "prose_checks_implemented": True,
        "follow_up_pilot_authorized": False,
        "credential_access_authorized": False,
        "token_preflight_authorized": False,
        "ai_generation_authorized": False,
        "stage_c_authorized": False,
        "production_use_authorized": False,
    }


def test_v2_request_and_response_fixtures_validate() -> None:
    request_fixtures = json.loads((V2_ROOT / "request-fixtures.json").read_text())
    response_fixtures = json.loads((V2_ROOT / "response-fixtures.json").read_text())
    assert request_fixtures["status"] == "reviewed_and_frozen"
    assert response_fixtures["status"] == "reviewed_and_frozen"
    requests = {}

    for fixture in request_fixtures["fixtures"]:
        trusted = build_trusted_fixture(ExperimentFixture(fixture["trusted_fixture"]))
        request = construct_request_v2(trusted)
        requests[fixture["fixture_id"]] = request
        assert request.prompt_version == PROMPT_VERSION_V2
        assert request.schema_version == SCHEMA_VERSION_V2
        assert [item.category_id.value for item in request.missing_information] == (
            fixture["expected_missing_categories"]
        )
        assert [item.knowledge_id for item in request.curated_knowledge_items] == (
            fixture["expected_knowledge_ids"]
        )

    for case in response_fixtures["cases"]:
        request = requests[case["request_fixture_id"]]
        if case["expected_valid"]:
            validated = validate_response_v2(request, case["response"])
            assert bool(validated.suggestions) == (
                case["response_fixture_id"] == "valid_storage_suggestion_v2"
            )
            continue
        with pytest.raises(ProseValidationError) as error:
            validate_response_v2(request, case["response"])
        assert list(error.value.violation_codes) == case["expected_violation_codes"]
        fallback = select_fallback_v2(request)
        assert fallback is not None
        assert fallback.question_id == case["expected_fallback_question_id"]


def test_v2_deterministic_baseline_matches_v2_runtime_fallbacks() -> None:
    baseline = json.loads((V2_ROOT / "deterministic-baseline.json").read_text())
    assert baseline["fallback_version"] == FALLBACK_VERSION_V2
    assert baseline["status"] == "reviewed_and_frozen"
    assert baseline["questions"] == [
        question.model_dump(mode="json") for question in FALLBACK_QUESTIONS_V2
    ]


def test_v2_knowledge_review_references_without_replacing_v1() -> None:
    review = (V2_ROOT / "knowledge-source-review.md").read_text()
    normalized_review = " ".join(review.replace("\n> ", " ").split())
    assert "v1/knowledge-source-review.md" in review
    assert STORAGE_KNOWLEDGE.statement in normalized_review
    assert "does not modify the historical v1 review" in review


def test_v2_manifest_and_pilot_structure_remain_closed() -> None:
    manifest = json.loads((V2_ROOT / "manifest.json").read_text())
    pilot = tomllib.loads((V2_ROOT / "openai-follow-up-pilot.toml").read_text())
    expected_true = (
        "prompt_v2_approved",
        "prompt_v2_frozen",
        "schema_v2_approved",
        "schema_v2_frozen",
        "fallback_v2_approved",
        "provider_schema_reviewed",
        "provider_schema_frozen",
        "follow_up_pilot_configuration_approved",
        "follow_up_pilot_configuration_frozen",
        "prose_checks_implemented",
    )
    expected_false = (
        "follow_up_pilot_authorized",
        "credential_access_authorized",
        "token_preflight_authorized",
        "ai_generation_authorized",
        "formal_evaluation_authorized",
        "stage_c_authorized",
        "production_use_authorized",
    )
    assert all(manifest[field] is True for field in expected_true)
    assert all(manifest[field] is False for field in expected_false)
    assert manifest["status"] == "reviewed_and_frozen"
    assert manifest["fallback_version"] == FALLBACK_VERSION_V2
    assert manifest["deterministic_baseline_path"].endswith(
        "/v2/deterministic-baseline.json"
    )
    assert pilot["identity"] == {
        "capability": "suggest_moving_service_questions",
        "run_series_id": "moving-service-stage-b-v2-pilot-20260802",
        "sequence": 1,
        "fixture_id": "storage_unknown",
        "provider": "OpenAI",
        "ai_model_identifier": "gpt-4.1-mini-2025-04-14",
        "sdk_package": "openai",
        "sdk_pin": "openai==2.45.0",
    }
    assert pilot["status"]["approved"] is True
    assert pilot["status"]["frozen"] is True
    assert all(
        value is False
        for field, value in pilot["status"].items()
        if field.endswith("authorized")
    )
    assert pilot["limits"]["maximum_token_preflight_requests"] == 1
    assert pilot["limits"]["maximum_ai_generation_requests"] == 1
    assert pilot["limits"]["automatic_retries"] == 0
    assert pilot["limits"]["maximum_total_spend_usd"] == "0.03"
    assert pilot["contracts"]["fallback_version"] == FALLBACK_VERSION_V2
    assert pilot["contracts"]["prompt_digest"] == FROZEN_V2_ARTIFACT_DIGESTS[
        "real-model-prompt.toml"
    ]
    assert pilot["contracts"]["provider_schema_digest"] == (
        FROZEN_V2_ARTIFACT_DIGESTS["openai-response-schema.json"]
    )
    assert pilot["comparison"] == {
        "changed_elements": [
            "prompt",
            "request_and_response_schema_literals",
            "deterministic_fallback",
            "capability_specific_prose_validation",
        ],
        "provider_transport_unchanged": True,
        "ai_generation_parameters_unchanged": True,
    }
    assert pilot["transport"] == {
        "token_preflight_endpoint": "/v1/responses/input_tokens",
        "token_preflight_timeout_seconds": 5,
        "generation_endpoint": "/v1/responses",
        "ai_generation_timeout_seconds": 12,
        "automatic_retries": 0,
        "structured_output_mode": "strict_json_schema",
        "exact_provider_token_preflight_required": True,
        "fresh_preflight_for_exact_generation_request_required": True,
    }
    assert pilot["model_parameters"] == {
        "temperature": 0,
        "top_p": "omitted",
        "seed": "omitted",
        "maximum_output_tokens": 500,
        "store": False,
        "stream": False,
        "background": False,
        "truncation": "disabled",
        "tools": [],
    }


def test_v2_openai_schema_is_exact_mechanical_adaptation() -> None:
    snapshot = json.loads((V2_ROOT / "openai-response-schema.json").read_text())
    generated = MovingServiceQuestionResponseV2.model_json_schema()
    assert adapt_response_schema_for_openai_v2(generated) == snapshot

    def require_closed_objects(value: object) -> None:
        if isinstance(value, dict):
            if value.get("type") == "object":
                assert value.get("additionalProperties") is False
            for item in value.values():
                require_closed_objects(item)
        elif isinstance(value, list):
            for item in value:
                require_closed_objects(item)

    require_closed_objects(snapshot)

    adaptation = json.loads(
        (V2_ROOT / "provider-schema-adaptation.json").read_text()
    )
    assert adaptation["status"] == "reviewed_and_frozen"
    assert adaptation["provider_snapshot_created"] is True
    assert adaptation["provider_snapshot_reviewed"] is True
    assert adaptation["provider_snapshot_frozen"] is True
    assert adaptation["runtime_pydantic_validation_authoritative"] is True


def test_v2_manifest_references_only_v2_package_artifacts() -> None:
    manifest = json.loads((V2_ROOT / "manifest.json").read_text())
    for field, value in manifest.items():
        if field.endswith("_path"):
            assert "/v2/" in value, field


def test_expected_results_record_stable_codes_and_human_review() -> None:
    expected = json.loads((V2_ROOT / "expected-results.json").read_text())
    assert expected["status"] == "reviewed_and_frozen"
    prose = expected["prose_validation"]
    assert tuple(prose["violation_code_order"]) == PROSE_VIOLATION_CODE_ORDER
    assert prose["complete_response_rejection"] is True
    assert prose["record_all_violation_codes"] is True
    assert prose["human_grounding_review_required"] is True


def test_grounding_equality_uses_supplied_request_statement() -> None:
    request = construct_request_v2(
        build_trusted_fixture(ExperimentFixture.STORAGE_UNKNOWN)
    )
    assert request.curated_knowledge_items[0].statement == STORAGE_KNOWLEDGE.statement


def test_v2_is_not_referenced_by_backend_routes_or_frontend() -> None:
    forbidden_roots = (
        REPOSITORY_ROOT / "backend/app/main.py",
        REPOSITORY_ROOT / "frontend/src",
    )
    for root in forbidden_roots:
        files = [root] if root.is_file() else list(root.rglob("*"))
        for path in files:
            if not path.is_file():
                continue
            text = path.read_text(errors="ignore")
            assert "moving_service_questions_v2" not in text
            assert PROMPT_VERSION_V2 not in text
