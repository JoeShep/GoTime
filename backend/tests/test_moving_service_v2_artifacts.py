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


def test_frozen_v1_artifact_digests_remain_unchanged() -> None:
    for filename, expected in FROZEN_V1_DIGESTS.items():
        digest = hashlib.sha256((V1_ROOT / filename).read_bytes()).hexdigest()
        assert digest == expected


def test_historical_v1_package_bytes_remain_unchanged() -> None:
    for filename, expected in HISTORICAL_V1_PACKAGE_DIGESTS.items():
        digest = hashlib.sha256((V1_ROOT / filename).read_bytes()).hexdigest()
        assert digest == expected


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


def test_v2_prompt_is_parseable_bounded_draft_without_examples() -> None:
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
        "prompt_status": "draft_pending_human_review",
        "prompt_artifact_digest_status": "not_computed_not_frozen",
    }
    assert prompt["examples"]["positive_examples_included"] is False
    assert prompt["structured_output"]["human_grounding_review_required"] is True
    assert prompt["readiness"] == {
        "draft": True,
        "reviewed": False,
        "ready_for_human_review": True,
        "prompt_v2_approved": False,
        "frozen_for_adapter_implementation": False,
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
    assert baseline["status"] == "draft_pending_human_review"
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
    expected_false = (
        "prompt_v2_approved",
        "prompt_v2_frozen",
        "schema_v2_approved",
        "follow_up_pilot_authorized",
        "credential_access_authorized",
        "token_preflight_authorized",
        "ai_generation_authorized",
        "stage_c_authorized",
        "production_use_authorized",
    )
    assert all(manifest[field] is False for field in expected_false)
    assert manifest["prose_checks_implemented"] is True
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
    }
    assert all(
        value is False
        for field, value in pilot["status"].items()
        if field.endswith("authorized") or field in {"approved", "frozen"}
    )
    assert pilot["limits"]["maximum_token_preflight_requests"] == 1
    assert pilot["limits"]["maximum_ai_generation_requests"] == 1
    assert pilot["limits"]["automatic_retries"] == 0
    assert pilot["limits"]["maximum_total_spend_usd"] == "0.03"
    assert pilot["contracts"]["fallback_version"] == FALLBACK_VERSION_V2


def test_expected_results_record_stable_codes_and_human_review() -> None:
    expected = json.loads((V2_ROOT / "expected-results.json").read_text())
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
