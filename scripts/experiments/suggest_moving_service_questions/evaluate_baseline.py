#!/usr/bin/env python3
"""Validate v1 artifacts against the runtime experiment contracts."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tomllib
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
    MAXIMUM_OUTPUT_TOKENS,
    MAXIMUM_QUESTIONS,
    PROMPT_VERSION,
    SCHEMA_VERSION,
    STORAGE_KNOWLEDGE,
    CuratedKnowledgeItem,
    ExperimentFixture,
    FallbackQuestion,
    MissingInformationCategory,
    MissingInformationItem,
    MovingServiceQuestionRequest,
    MovingServiceQuestionResponse,
    MovingServiceQuestionSuggestion,
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
PROMPT_FILE = "real-model-prompt.toml"
OPENAI_RUN_CONFIGURATION_FILE = "openai-run-configuration.toml"
OPENAI_RESPONSE_SCHEMA_FILE = "openai-response-schema.json"
OPENAI_RESPONSE_SCHEMA_REVIEW_FILE = "openai-response-schema-review.md"
OPENAI_EXECUTION_AUTHORIZATION_FILE = "openai-execution-authorization.toml"


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


def load_artifacts(directory: Path | None = None) -> dict[str, object]:
    root = Path(directory or default_artifact_dir())
    artifacts = {
        name: json.loads((root / filename).read_text())
        for name, filename in FILES.items()
    }
    prompt_bytes = (root / PROMPT_FILE).read_bytes()
    artifacts["prompt"] = tomllib.loads(prompt_bytes.decode("utf-8"))
    artifacts["prompt_sha256"] = hashlib.sha256(prompt_bytes).hexdigest()
    run_configuration_bytes = (root / OPENAI_RUN_CONFIGURATION_FILE).read_bytes()
    artifacts["openai_run_configuration"] = tomllib.loads(
        run_configuration_bytes.decode("utf-8")
    )
    artifacts["openai_run_configuration_sha256"] = hashlib.sha256(
        run_configuration_bytes
    ).hexdigest()
    response_schema_bytes = (root / OPENAI_RESPONSE_SCHEMA_FILE).read_bytes()
    artifacts["openai_response_schema"] = json.loads(response_schema_bytes)
    artifacts["openai_response_schema_sha256"] = hashlib.sha256(
        response_schema_bytes
    ).hexdigest()
    artifacts["openai_response_schema_review"] = (
        root / OPENAI_RESPONSE_SCHEMA_REVIEW_FILE
    ).read_text(encoding="utf-8")
    authorization_bytes = (root / OPENAI_EXECUTION_AUTHORIZATION_FILE).read_bytes()
    artifacts["openai_execution_authorization"] = tomllib.loads(
        authorization_bytes.decode("utf-8")
    )
    artifacts["openai_execution_authorization_sha256"] = hashlib.sha256(
        authorization_bytes
    ).hexdigest()
    return artifacts


def adapt_response_schema_for_openai(value: object) -> object:
    """Remove only nonsemantic Pydantic title annotations."""
    if isinstance(value, dict):
        return {
            key: adapt_response_schema_for_openai(item)
            for key, item in value.items()
            if key != "title"
        }
    if isinstance(value, list):
        return [adapt_response_schema_for_openai(item) for item in value]
    return value


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
            "prompt_artifact_path",
            "prompt_artifact_digest_algorithm",
            "prompt_artifact_digest",
            "prompt_artifact_digest_status",
            "prompt_artifact_reviewed",
            "prompt_artifact_frozen_for_adapter_implementation",
            "openai_run_configuration_path",
            "openai_run_configuration_digest_algorithm",
            "openai_run_configuration_digest",
            "openai_run_configuration_approval_date",
            "openai_run_configuration_approved",
            "openai_run_configuration_frozen",
            "openai_response_schema_path",
            "openai_response_schema_digest_algorithm",
            "openai_response_schema_digest",
            "openai_response_schema_review_path",
            "openai_response_schema_status",
            "openai_execution_authorization_path",
            "openai_execution_authorization_version",
            "openai_execution_authorization_digest_algorithm",
            "openai_execution_authorization_digest",
            "openai_execution_authorization_status",
            "contract_test_eligible",
            "contract_test_ineligibility_reasons",
            "contract_artifacts_ready",
            "prompt_artifact_ready",
            "adapter_implementation_authorized",
            "real_model_execution_authorized",
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
    expected_prompt_path = (
        "docs/experiments/suggest-moving-service-questions/v1/"
        "real-model-prompt.toml"
    )
    if manifest["prompt_artifact_path"] != expected_prompt_path:
        _fail("manifest: prompt artifact path is unsupported")
    if manifest["prompt_artifact_digest_algorithm"] != "sha256":
        _fail("manifest: prompt digest algorithm must be sha256")
    if manifest["prompt_artifact_digest"] != artifacts["prompt_sha256"]:
        _fail("manifest: prompt digest does not match exact artifact bytes")
    if manifest["prompt_artifact_digest_status"] != "recorded":
        _fail("manifest: frozen prompt digest must be recorded")
    if manifest["prompt_artifact_reviewed"] is not True:
        _fail("manifest: frozen prompt must be reviewed")
    if manifest["prompt_artifact_frozen_for_adapter_implementation"] is not True:
        _fail("manifest: prompt must be frozen for adapter implementation")
    if manifest["status"] != "openai_execution_authorization_closed":
        _fail("manifest: closed OpenAI execution authorization is required")
    if manifest["contract_artifacts_ready"] is not True:
        _fail("manifest: contract artifacts must remain ready")
    if manifest["prompt_artifact_ready"] is not True:
        _fail("manifest: validated prompt artifact must remain ready")
    if manifest["adapter_implementation_authorized"] is not False:
        _fail("manifest: adapter implementation must not be authorized")
    if manifest["real_model_execution_authorized"] is not False:
        _fail("manifest: real-model execution must not be authorized")
    if manifest["real_model_evaluation_eligible"]:
        _fail("manifest: draft prompt must not be real-model eligible")


def _validate_openai_artifacts(artifacts: dict[str, object]) -> None:
    manifest = artifacts["manifest"]
    configuration = artifacts["openai_run_configuration"]
    if not isinstance(manifest, dict) or not isinstance(configuration, dict):
        _fail("OpenAI artifacts: manifest and configuration must be objects")

    expected_paths = {
        "openai_run_configuration_path": (
            "docs/experiments/suggest-moving-service-questions/v1/"
            "openai-run-configuration.toml"
        ),
        "openai_response_schema_path": (
            "docs/experiments/suggest-moving-service-questions/v1/"
            "openai-response-schema.json"
        ),
        "openai_response_schema_review_path": (
            "docs/experiments/suggest-moving-service-questions/v1/"
            "openai-response-schema-review.md"
        ),
    }
    for field, expected in expected_paths.items():
        if manifest[field] != expected:
            _fail(f"manifest: {field} is unsupported")
    if manifest["openai_run_configuration_digest_algorithm"] != "sha256":
        _fail("manifest: run-configuration digest algorithm must be sha256")
    if manifest["openai_run_configuration_digest"] != artifacts[
        "openai_run_configuration_sha256"
    ]:
        _fail("manifest: run-configuration digest does not match exact bytes")
    if manifest["openai_response_schema_digest_algorithm"] != "sha256":
        _fail("manifest: provider-schema digest algorithm must be sha256")
    if manifest["openai_response_schema_digest"] != artifacts[
        "openai_response_schema_sha256"
    ]:
        _fail("manifest: provider-schema digest does not match exact bytes")
    if manifest["openai_run_configuration_approved"] is not True:
        _fail("manifest: run configuration must be approved")
    if manifest["openai_run_configuration_frozen"] is not True:
        _fail("manifest: run configuration must be frozen")
    if manifest["openai_response_schema_status"] != "reviewed_and_frozen":
        _fail("manifest: provider schema must be reviewed and frozen")
    review = artifacts["openai_response_schema_review"]
    if not isinstance(review, str) or "status: reviewed_and_frozen" not in review:
        _fail("provider schema: review record is missing or incomplete")

    status = _require(
        configuration.get("status"),
        (
            "configuration_status",
            "approved",
            "frozen",
            "provider_transport_implementation_authorized",
            "credentials_authorized",
            "real_model_execution_authorized",
            "production_use_authorized",
        ),
        "OpenAI run configuration status",
    )
    expected_status = {
        "configuration_status": "approved_and_frozen",
        "approved": True,
        "frozen": True,
        "provider_transport_implementation_authorized": False,
        "credentials_authorized": False,
        "real_model_execution_authorized": False,
        "production_use_authorized": False,
    }
    for field, expected in expected_status.items():
        if status[field] != expected:
            _fail(f"OpenAI run configuration: {field} must be {expected}")

    identity = configuration.get("identity", {})
    prompt = configuration.get("prompt", {})
    contracts = configuration.get("contracts", {})
    transport = configuration.get("transport", {})
    if identity.get("capability") != CAPABILITY:
        _fail("OpenAI run configuration: capability has drifted")
    if identity.get("provider") != "OpenAI":
        _fail("OpenAI run configuration: provider has drifted")
    if identity.get("ai_model_identifier") != "gpt-4.1-mini-2025-04-14":
        _fail("OpenAI run configuration: AI model identifier has drifted")
    if identity.get("sdk_pin") != "openai==2.45.0":
        _fail("OpenAI run configuration: SDK pin has drifted")
    if prompt.get("version") != PROMPT_VERSION:
        _fail("OpenAI run configuration: prompt version has drifted")
    if prompt.get("digest") != artifacts["prompt_sha256"]:
        _fail("OpenAI run configuration: prompt digest has drifted")
    if contracts.get("request_schema_version") != SCHEMA_VERSION:
        _fail("OpenAI run configuration: request schema version has drifted")
    if contracts.get("response_schema_version") != SCHEMA_VERSION:
        _fail("OpenAI run configuration: response schema version has drifted")
    if contracts.get("knowledge_fixture_version") != KNOWLEDGE_VERSION:
        _fail("OpenAI run configuration: knowledge version has drifted")
    if contracts.get("provider_schema_snapshot_status") != "reviewed_and_frozen":
        _fail("OpenAI run configuration: provider schema is not frozen")
    expected_transport = {
        "token_preflight_timeout_seconds": 5,
        "generation_timeout_seconds": 12,
        "automatic_retries": 0,
        "structured_output_mode": "strict_json_schema",
    }
    for field, expected in expected_transport.items():
        if transport.get(field) != expected:
            _fail(f"OpenAI run configuration: {field} has drifted")

    generated_schema = MovingServiceQuestionResponse.model_json_schema()
    adapted_schema = adapt_response_schema_for_openai(generated_schema)
    if adapted_schema != artifacts["openai_response_schema"]:
        _fail("provider schema: snapshot has drifted from Pydantic generation")
    if not isinstance(adapted_schema, dict):
        _fail("provider schema: root must be an object")

    def require_closed_objects(value: object, path: str = "root") -> None:
        if isinstance(value, dict):
            if value.get("type") == "object" and value.get(
                "additionalProperties"
            ) is not False:
                _fail(f"provider schema: {path} must forbid extra fields")
            for key, item in value.items():
                require_closed_objects(item, f"{path}.{key}")
        elif isinstance(value, list):
            for index, item in enumerate(value):
                require_closed_objects(item, f"{path}[{index}]")

    require_closed_objects(adapted_schema)


def _require_exact_fields(
    value: object,
    expected_fields: tuple[str, ...],
    context: str,
) -> dict:
    document = _require(value, expected_fields, context)
    unknown = sorted(set(document) - set(expected_fields))
    if unknown:
        _fail(f"{context}: unknown fields fail closed: {', '.join(unknown)}")
    return document


def _validate_openai_execution_authorization(
    artifacts: dict[str, object],
) -> None:
    manifest = artifacts["manifest"]
    authorization = artifacts["openai_execution_authorization"]
    if not isinstance(manifest, dict) or not isinstance(authorization, dict):
        _fail("execution authorization: artifacts must be objects")
    expected_top_level = (
        "metadata",
        "bindings",
        "authorization",
        "scope",
        "policy",
        "validation",
    )
    _require_exact_fields(
        authorization,
        expected_top_level,
        "execution authorization",
    )
    expected_manifest = {
        "openai_execution_authorization_path": (
            "docs/experiments/suggest-moving-service-questions/v1/"
            "openai-execution-authorization.toml"
        ),
        "openai_execution_authorization_version": (
            "moving-service-openai-execution-authorization-v1"
        ),
        "openai_execution_authorization_digest_algorithm": "sha256",
        "openai_execution_authorization_status": (
            "closed_no_execution_authorized"
        ),
    }
    for field, expected in expected_manifest.items():
        if manifest.get(field) != expected:
            _fail(f"manifest: {field} is incompatible")
    if manifest.get("openai_execution_authorization_digest") != artifacts.get(
        "openai_execution_authorization_sha256"
    ):
        _fail("manifest: execution-authorization digest does not match exact bytes")

    metadata = _require_exact_fields(
        authorization["metadata"],
        (
            "capability",
            "authorization_version",
            "authorization_status",
            "created_date",
            "evaluation_only",
            "default_deny",
        ),
        "execution authorization metadata",
    )
    expected_metadata = {
        "capability": CAPABILITY,
        "authorization_version": (
            "moving-service-openai-execution-authorization-v1"
        ),
        "authorization_status": "closed_no_execution_authorized",
        "evaluation_only": True,
        "default_deny": True,
    }
    for field, expected in expected_metadata.items():
        if metadata[field] != expected:
            _fail(f"execution authorization metadata: {field} is incompatible")

    bindings = _require_exact_fields(
        authorization["bindings"],
        (
            "prompt_artifact_path",
            "prompt_version",
            "prompt_digest_algorithm",
            "prompt_digest",
            "run_configuration_path",
            "run_configuration_digest_algorithm",
            "run_configuration_digest",
            "provider_schema_path",
            "provider_schema_digest_algorithm",
            "provider_schema_digest",
            "request_schema_version",
            "response_schema_version",
            "knowledge_fixture_version",
            "provider",
            "ai_model_identifier",
            "sdk_pin",
        ),
        "execution authorization bindings",
    )
    expected_bindings = {
        "prompt_artifact_path": manifest["prompt_artifact_path"],
        "prompt_version": PROMPT_VERSION,
        "prompt_digest_algorithm": "sha256",
        "prompt_digest": artifacts["prompt_sha256"],
        "run_configuration_path": manifest["openai_run_configuration_path"],
        "run_configuration_digest_algorithm": "sha256",
        "run_configuration_digest": artifacts["openai_run_configuration_sha256"],
        "provider_schema_path": manifest["openai_response_schema_path"],
        "provider_schema_digest_algorithm": "sha256",
        "provider_schema_digest": artifacts["openai_response_schema_sha256"],
        "request_schema_version": SCHEMA_VERSION,
        "response_schema_version": SCHEMA_VERSION,
        "knowledge_fixture_version": KNOWLEDGE_VERSION,
        "provider": "OpenAI",
        "ai_model_identifier": "gpt-4.1-mini-2025-04-14",
        "sdk_pin": "openai==2.45.0",
    }
    for field, expected in expected_bindings.items():
        if bindings[field] != expected:
            _fail(f"execution authorization binding: {field} has drifted")

    permissions = _require_exact_fields(
        authorization["authorization"],
        (
            "credential_access_authorized",
            "token_preflight_authorized",
            "ai_generation_authorized",
            "formal_evaluation_authorized",
        ),
        "execution authorization permissions",
    )
    for field, value in permissions.items():
        if value is not False:
            _fail(f"execution authorization permission: {field} must be False")

    scope = _require_exact_fields(
        authorization["scope"],
        (
            "authorized_run_series_id",
            "authorized_sequence_numbers",
            "authorized_fixture_ids",
            "maximum_authorized_spend",
            "approval_date",
            "expiration_date",
            "approved_by",
        ),
        "execution authorization scope",
    )
    expected_scope = {
        "authorized_run_series_id": "",
        "authorized_sequence_numbers": [],
        "authorized_fixture_ids": [],
        "maximum_authorized_spend": "0.00",
        "approval_date": "not_authorized",
        "expiration_date": "not_authorized",
        "approved_by": "none",
    }
    for field, expected in expected_scope.items():
        if scope[field] != expected:
            _fail(f"execution authorization scope: {field} must remain closed")

    policy = _require_exact_fields(
        authorization["policy"],
        (
            "operator_intent_is_authority",
            "environment_values_may_override_authorization",
            "command_line_flags_may_override_authorization",
            "missing_or_unknown_fields_fail_closed",
            "authorization_changes_require_human_review",
            "authorization_changes_require_new_digest",
            "authorization_changes_require_manifest_update",
            "credential_access_requires_all_non_secret_gates",
            "token_preflight_requires_credential_access_authorization",
            "ai_generation_requires_successful_token_preflight",
            "formal_evaluation_requires_ai_generation_authorization",
        ),
        "execution authorization policy",
    )
    for field in (
        "operator_intent_is_authority",
        "environment_values_may_override_authorization",
        "command_line_flags_may_override_authorization",
    ):
        if policy[field] is not False:
            _fail(f"execution authorization policy: {field} must be False")
    for field in set(policy) - {
        "operator_intent_is_authority",
        "environment_values_may_override_authorization",
        "command_line_flags_may_override_authorization",
    }:
        if policy[field] is not True:
            _fail(f"execution authorization policy: {field} must be True")

    validation = _require_exact_fields(
        authorization["validation"],
        (
            "non_secret_gate_order",
            "first_secret_stage",
            "first_network_stage",
            "generation_stage",
        ),
        "execution authorization validation",
    )
    if validation["non_secret_gate_order"] != [
        "artifact_integrity",
        "repository_authorization",
        "fixture_and_sequence_validation",
        "output_path_checks",
        "budget_checks",
        "operator_intent_check",
    ]:
        _fail("execution authorization: non-secret gate order has drifted")
    expected_stages = {
        "first_secret_stage": "credential_access",
        "first_network_stage": "token_preflight",
        "generation_stage": "possible_generation",
    }
    for field, expected in expected_stages.items():
        if validation[field] != expected:
            _fail(f"execution authorization: {field} has drifted")


def _validate_prompt(artifacts: dict[str, dict]) -> None:
    prompt = _require(
        artifacts["prompt"],
        (
            "system_instructions",
            "metadata",
            "serialization",
            "structured_output",
            "examples",
            "versioning",
            "readiness",
            "human_review",
        ),
        "prompt",
    )
    if not isinstance(prompt["system_instructions"], str) or not prompt[
        "system_instructions"
    ].strip():
        _fail("prompt: system instructions must be nonblank")

    metadata = _require(
        prompt["metadata"],
        (
            "capability",
            "prompt_version",
            "compatible_request_schema_version",
            "compatible_response_schema_version",
            "compatible_knowledge_fixture_version",
            "maximum_questions",
            "preferred_questions",
            "maximum_input_tokens",
            "maximum_output_tokens",
            "formal_evaluation_retries",
            "evaluation_only",
            "production_use_prohibited",
            "live_research_prohibited",
            "prompt_status",
            "prompt_artifact_digest_status",
        ),
        "prompt metadata",
    )
    expected_metadata = {
        "capability": CAPABILITY,
        "prompt_version": PROMPT_VERSION,
        "compatible_request_schema_version": SCHEMA_VERSION,
        "compatible_response_schema_version": SCHEMA_VERSION,
        "compatible_knowledge_fixture_version": KNOWLEDGE_VERSION,
        "maximum_questions": MAXIMUM_QUESTIONS,
        "preferred_questions": 1,
        "maximum_input_tokens": MAXIMUM_INPUT_TOKENS,
        "maximum_output_tokens": MAXIMUM_OUTPUT_TOKENS,
        "formal_evaluation_retries": 0,
        "evaluation_only": True,
        "production_use_prohibited": True,
        "live_research_prohibited": True,
        "prompt_status": "frozen_for_adapter_implementation",
        "prompt_artifact_digest_status": "recorded_in_manifest",
    }
    for field, expected in expected_metadata.items():
        if metadata[field] != expected:
            _fail(f"prompt metadata: {field} does not match runtime or policy")

    serialization = prompt["serialization"]
    if serialization["top_level_field_order"] != list(
        MovingServiceQuestionRequest.model_fields
    ):
        _fail("prompt serialization: request fields do not match runtime")
    structured_output = prompt["structured_output"]
    if structured_output["response_field_order"] != list(
        MovingServiceQuestionResponse.model_fields
    ):
        _fail("prompt output: response fields do not match runtime")
    if structured_output["suggestion_field_order"] != list(
        MovingServiceQuestionSuggestion.model_fields
    ):
        _fail("prompt output: suggestion fields do not match runtime")
    if structured_output["warnings_policy"] != "always_empty":
        _fail("prompt output: warnings must remain empty")
    if structured_output["fallback_recommended_policy"] != "always_false":
        _fail("prompt output: model fallback recommendation must remain false")

    readiness = prompt["readiness"]
    expected_readiness = {
        "draft": False,
        "reviewed": True,
        "ready_for_human_review": False,
        "frozen_for_adapter_implementation": True,
        "frozen_for_real_model_execution": False,
        "adapter_implementation_authorized": False,
        "real_model_execution_authorized": False,
    }
    for field, expected in expected_readiness.items():
        if readiness.get(field) is not expected:
            _fail(f"prompt readiness: {field} must be {expected}")


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


def validate_artifacts(artifacts: dict[str, object]) -> dict[str, object]:
    """Validate artifact data by passing it through runtime behavior."""
    _validate_manifest(artifacts)
    _validate_prompt(artifacts)
    _validate_openai_artifacts(artifacts)
    _validate_openai_execution_authorization(artifacts)
    knowledge_items = _validate_knowledge(artifacts)
    _validate_baseline(artifacts)
    requests = _build_scenario_requests(artifacts)
    response_results = _validate_response_fixtures(artifacts, requests)
    execution_results = _validate_execution_expectations(artifacts)
    return {
        "manifest": artifacts["manifest"],
        "openai_run_configuration_sha256": artifacts[
            "openai_run_configuration_sha256"
        ],
        "openai_response_schema_sha256": artifacts[
            "openai_response_schema_sha256"
        ],
        "openai_execution_authorization_sha256": artifacts[
            "openai_execution_authorization_sha256"
        ],
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
