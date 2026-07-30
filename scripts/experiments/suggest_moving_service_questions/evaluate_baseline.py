#!/usr/bin/env python3
"""Validate v1 artifacts against the runtime experiment contracts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = REPOSITORY_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.moving_service_questions import (  # noqa: E402
    ANSWER_TYPES,
    CAPABILITY,
    FALLBACK_QUESTIONS,
    FALLBACK_VERSION,
    KNOWLEDGE_VERSION,
    MAXIMUM_INPUT_TOKENS,
    PROMPT_VERSION,
    SCHEMA_VERSION,
    STORAGE_KNOWLEDGE,
    CuratedKnowledgeItem,
    ExperimentFixture,
    FallbackQuestion,
    MissingInformationCategory,
    MissingInformationItem,
    MovingServiceQuestionRequest,
    MovingServiceTrustedState,
    ResponseValidationError,
    construct_request,
    run_experiment,
    select_fallback,
    validate_response,
)

FILES = {
    "manifest": "manifest.json",
    "knowledge": "curated-knowledge.json",
    "baseline": "deterministic-baseline.json",
    "scenarios": "scenarios.json",
    "responses": "response-fixtures.json",
    "expected": "expected-results.json",
}


class ArtifactValidationError(ValueError):
    pass


def _fail(message: str) -> None:
    raise ArtifactValidationError(message)


def _require(document: object, fields: tuple[str, ...], context: str) -> dict:
    if not isinstance(document, dict):
        _fail(f"{context}: must be an object")
    missing = [field for field in fields if field not in document]
    if missing:
        _fail(f"{context}: missing required fields: {', '.join(missing)}")
    return document


def default_artifact_dir() -> Path:
    return (
        REPOSITORY_ROOT
        / "docs/experiments/suggest-moving-service-questions/v1"
    )


def load_artifacts(directory: Path | None = None) -> dict[str, dict]:
    root = Path(directory or default_artifact_dir())
    return {
        name: json.loads((root / filename).read_text())
        for name, filename in FILES.items()
    }


def _validate_readiness(
    manifest: dict, value_field: str, reasons_field: str
) -> None:
    value = manifest[value_field]
    reasons = manifest[reasons_field]
    if not isinstance(value, bool):
        _fail(f"manifest: {value_field} must be boolean")
    if not isinstance(reasons, list) or not all(
        isinstance(reason, str) and reason.strip() for reason in reasons
    ):
        _fail(f"manifest: {reasons_field} must contain nonblank strings")
    if value and reasons:
        _fail(f"manifest: {reasons_field} must be empty when eligible")
    if not value and not reasons:
        _fail(f"manifest: {reasons_field} is required when ineligible")


def _validate_manifest(artifacts: dict[str, dict]) -> None:
    manifest = _require(
        artifacts["manifest"],
        (
            "capability",
            "artifact_version",
            "prompt_version",
            "schema_version",
            "knowledge_fixture_version",
            "fallback_version",
            "scenario_version",
            "response_fixture_version",
            "expectations_version",
            "status",
            "contract_test_eligible",
            "contract_test_ineligibility_reasons",
            "real_model_evaluation_eligible",
            "real_model_ineligibility_reasons",
        ),
        "manifest",
    )
    if manifest["capability"] != CAPABILITY:
        _fail("manifest: capability does not match runtime")
    runtime_versions = {
        "prompt_version": PROMPT_VERSION,
        "schema_version": SCHEMA_VERSION,
        "knowledge_fixture_version": KNOWLEDGE_VERSION,
        "fallback_version": FALLBACK_VERSION,
    }
    for field, runtime_value in runtime_versions.items():
        if manifest[field] != runtime_value:
            _fail(f"manifest: {field} does not match runtime")
    artifact_versions = {
        "scenario_version": artifacts["scenarios"].get("scenario_version"),
        "response_fixture_version": artifacts["responses"].get(
            "response_fixture_version"
        ),
        "expectations_version": artifacts["expected"].get(
            "expectations_version"
        ),
    }
    for field, artifact_value in artifact_versions.items():
        if manifest[field] != artifact_value:
            _fail(f"manifest: {field} does not match its artifact")
    _validate_readiness(
        manifest,
        "contract_test_eligible",
        "contract_test_ineligibility_reasons",
    )
    _validate_readiness(
        manifest,
        "real_model_evaluation_eligible",
        "real_model_ineligibility_reasons",
    )
    if not manifest["contract_test_eligible"]:
        _fail("manifest: reconciled v1 package must be contract-test eligible")
    if manifest["status"] != "controlled_storage_question_evaluation_ready":
        _fail("manifest: controlled storage evaluation status is required")
    if not manifest["real_model_evaluation_eligible"]:
        _fail(
            "manifest: approved storage fixture must be eligible for its "
            "controlled real-model evaluation"
        )


def _validate_knowledge(artifacts: dict[str, dict]) -> tuple[CuratedKnowledgeItem, ...]:
    knowledge = _require(
        artifacts["knowledge"],
        (
            "fixture_version",
            "status",
            "valid_for",
            "real_model_grounding_approved",
            "limitations",
            "items",
        ),
        "knowledge",
    )
    if knowledge["fixture_version"] != KNOWLEDGE_VERSION:
        _fail("knowledge: fixture version does not match runtime")
    if knowledge["status"] != "reviewed_controlled_evaluation_fixture":
        _fail("knowledge: approved fixture status is required")
    if knowledge["real_model_grounding_approved"] is not True:
        _fail("knowledge: approved storage grounding must be recorded")
    if (
        "controlled_storage_question_model_evaluation"
        not in knowledge["valid_for"]
    ):
        _fail("knowledge: controlled evaluation scope is required")
    if not knowledge["limitations"]:
        _fail("knowledge: controlled-evaluation limitations are required")
    try:
        items = tuple(
            CuratedKnowledgeItem.model_validate(item)
            for item in knowledge["items"]
        )
    except ValueError as error:
        raise ArtifactValidationError(
            "knowledge: item does not match the runtime contract"
        ) from error
    if [item.model_dump(mode="json") for item in items] != [
        STORAGE_KNOWLEDGE.model_dump(mode="json")
    ]:
        _fail("knowledge: items have drifted from the runtime fixture")
    return items


def _runtime_missing_information_contracts() -> list[dict]:
    contracts = []
    for category in MissingInformationCategory:
        answer_type, allowed_values = ANSWER_TYPES[category]
        contracts.append(
            MissingInformationItem(
                category_id=category,
                state_field=category,
                answer_type=answer_type,
                allowed_enum_values=allowed_values,
                reason_missing=f"{category.value} has not been confirmed.",
            ).model_dump(mode="json")
        )
    return contracts


def _validate_baseline(artifacts: dict[str, dict]) -> None:
    baseline = _require(
        artifacts["baseline"],
        (
            "fallback_version",
            "status",
            "missing_information_contracts",
            "questions",
        ),
        "baseline",
    )
    if baseline["fallback_version"] != FALLBACK_VERSION:
        _fail("baseline: fallback version does not match runtime")
    try:
        contracts = [
            MissingInformationItem.model_validate(item)
            for item in baseline["missing_information_contracts"]
        ]
        questions = [
            FallbackQuestion.model_validate(item)
            for item in baseline["questions"]
        ]
    except ValueError as error:
        raise ArtifactValidationError(
            "baseline: data does not match runtime models"
        ) from error
    if [item.model_dump(mode="json") for item in contracts] != (
        _runtime_missing_information_contracts()
    ):
        _fail("baseline: missing-information contracts have drifted from runtime")
    if [item.model_dump(mode="json") for item in questions] != [
        item.model_dump(mode="json") for item in FALLBACK_QUESTIONS
    ]:
        _fail("baseline: fallback questions have drifted from runtime")


def _build_scenario_requests(
    artifacts: dict[str, dict],
) -> dict[str, MovingServiceQuestionRequest]:
    scenarios = _require(
        artifacts["scenarios"],
        (
            "scenario_version",
            "status",
            "expected_request_fields",
            "excluded_request_fields",
            "scenarios",
        ),
        "scenarios",
    )
    requests: dict[str, MovingServiceQuestionRequest] = {}
    for scenario in scenarios["scenarios"]:
        scenario = _require(
            scenario,
            (
                "fixture_id",
                "purpose",
                "trusted_state",
                "expected_missing_categories",
                "expected_knowledge_ids",
            ),
            "scenario",
        )
        fixture_id = scenario["fixture_id"]
        if fixture_id in requests:
            _fail(f"scenarios: duplicate fixture_id {fixture_id}")
        try:
            trusted_state = MovingServiceTrustedState.model_validate(
                scenario["trusted_state"]
            )
            request = construct_request(trusted_state)
        except ValueError as error:
            raise ArtifactValidationError(
                f"scenario {fixture_id}: does not match runtime contracts"
            ) from error
        serialized = request.model_dump(mode="json")
        if set(serialized) != set(scenarios["expected_request_fields"]):
            _fail(f"scenario {fixture_id}: request fields have drifted")
        if set(serialized) & set(scenarios["excluded_request_fields"]):
            _fail(f"scenario {fixture_id}: excluded request field is present")
        actual_categories = [
            item.category_id.value for item in request.missing_information
        ]
        if actual_categories != scenario["expected_missing_categories"]:
            _fail(f"scenario {fixture_id}: missing categories do not match")
        actual_knowledge_ids = [
            item.knowledge_id for item in request.curated_knowledge_items
        ]
        if actual_knowledge_ids != scenario["expected_knowledge_ids"]:
            _fail(f"scenario {fixture_id}: knowledge IDs do not match")
        request_bytes = len(
            json.dumps(serialized, separators=(",", ":")).encode("utf-8")
        )
        if request_bytes > MAXIMUM_INPUT_TOKENS:
            _fail(
                f"scenario {fixture_id}: request exceeds the conservative "
                "3,000-token byte upper bound"
            )
        requests[fixture_id] = request
    return requests


def _validate_response_fixtures(
    artifacts: dict[str, dict],
    requests: dict[str, MovingServiceQuestionRequest],
) -> list[dict]:
    responses = _require(
        artifacts["responses"],
        ("response_fixture_version", "status", "cases"),
        "responses",
    )
    results = []
    fixture_ids: set[str] = set()
    for case in responses["cases"]:
        case = _require(
            case,
            (
                "response_fixture_id",
                "request_fixture_id",
                "response",
                "expected_valid",
                "expected_fallback_question_id",
                "expected_fallback_reason",
            ),
            "response case",
        )
        response_fixture_id = case["response_fixture_id"]
        if response_fixture_id in fixture_ids:
            _fail(f"responses: duplicate fixture {response_fixture_id}")
        fixture_ids.add(response_fixture_id)
        request = requests.get(case["request_fixture_id"])
        if request is None:
            _fail(
                f"response {response_fixture_id}: unknown request fixture"
            )
        valid = True
        try:
            validate_response(request, case["response"])
        except ResponseValidationError:
            valid = False
        if valid is not case["expected_valid"]:
            _fail(
                f"response {response_fixture_id}: validity expectation failed"
            )
        fallback = select_fallback(request) if not valid else None
        fallback_id = fallback.question_id if fallback else None
        if fallback_id != case["expected_fallback_question_id"]:
            _fail(
                f"response {response_fixture_id}: fallback expectation failed"
            )
        expected_reason = (
            "invalid_adapter_response" if not valid and fallback else None
        )
        if expected_reason != case["expected_fallback_reason"]:
            _fail(
                f"response {response_fixture_id}: fallback reason is inconsistent"
            )
        results.append(
            {
                "response_fixture_id": response_fixture_id,
                "valid": valid,
                "fallback_question_id": fallback_id,
            }
        )
    return results


def _validate_execution_expectations(
    artifacts: dict[str, dict],
) -> list[dict]:
    expected = _require(
        artifacts["expected"],
        (
            "expectations_version",
            "status",
            "stable_observability_fields",
            "excluded_observability_payloads",
            "execution_cases",
        ),
        "expected",
    )
    results = []
    for case in expected["execution_cases"]:
        fixture = ExperimentFixture(case["fixture_id"])
        result = run_experiment(fixture)
        observability = result.observability.model_dump(mode="json")
        stable_observability = {
            field: observability[field]
            for field in expected["stable_observability_fields"]
        }
        if set(stable_observability) != set(
            expected["stable_observability_fields"]
        ):
            _fail(f"execution {fixture.value}: observability fields drifted")
        if set(observability) & set(expected["excluded_observability_payloads"]):
            _fail(f"execution {fixture.value}: excluded payload was observed")
        actual = {
            "expected_source": result.source.value,
            "expected_question_id": (
                result.suggestion.question_id if result.suggestion else None
            ),
            "expected_schema_valid": result.observability.schema_valid,
            "expected_fallback_used": result.observability.fallback_used,
            "expected_fallback_reason": result.observability.fallback_reason,
            "expected_suggestion_count": result.observability.suggestion_count,
            "expected_cost": result.observability.estimated_cost,
            "expected_referenced_knowledge_ids": list(
                result.observability.referenced_knowledge_ids
            ),
        }
        for field, value in actual.items():
            if case[field] != value:
                _fail(
                    f"execution {fixture.value}: {field} does not match runtime"
                )
        results.append(
            {
                "fixture_id": fixture.value,
                "source": result.source.value,
                "question_id": actual["expected_question_id"],
                "observability": stable_observability,
            }
        )
    return results


def validate_artifacts(artifacts: dict[str, dict]) -> dict[str, object]:
    """Validate artifact data by passing it through runtime behavior."""
    _validate_manifest(artifacts)
    knowledge_items = _validate_knowledge(artifacts)
    _validate_baseline(artifacts)
    requests = _build_scenario_requests(artifacts)
    response_results = _validate_response_fixtures(artifacts, requests)
    execution_results = _validate_execution_expectations(artifacts)
    return {
        "manifest": artifacts["manifest"],
        "knowledge_item_count": len(knowledge_items),
        "request_fixtures": {
            fixture_id: request.model_dump(mode="json")
            for fixture_id, request in requests.items()
        },
        "response_results": response_results,
        "execution_results": execution_results,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts", type=Path, default=default_artifact_dir())
    args = parser.parse_args()
    result = validate_artifacts(load_artifacts(args.artifacts))
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
