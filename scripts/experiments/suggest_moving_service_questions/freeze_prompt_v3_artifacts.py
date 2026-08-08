"""Deterministically materialize the reviewed, frozen prompt-v3 package."""

from __future__ import annotations

import hashlib
import json
import tomllib
from pathlib import Path
from typing import Any

from moving_service_questions_v2 import MovingServiceQuestionResponseV2
from moving_service_questions_v3 import (
    MovingServiceQuestionResponseV3,
    adapt_response_schema_for_openai_v3,
)


ROOT = Path(__file__).resolve().parents[3]
CAPABILITY_ROOT = ROOT / "docs/experiments/suggest-moving-service-questions"
V2 = CAPABILITY_ROOT / "v2"
DRAFT = CAPABILITY_ROOT / "v3-draft"
V3 = CAPABILITY_ROOT / "v3"


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value if value.endswith("\n") else value + "\n", encoding="utf-8")


def _write_json(path: Path, value: object) -> None:
    _write_text(path, json.dumps(value, indent=2, sort_keys=True))


def _replace_once(value: str, old: str, new: str) -> str:
    if value.count(old) != 1:
        raise ValueError(f"expected one prompt-v2 source block, found {value.count(old)}")
    return value.replace(old, new, 1)


def finalized_prompt_text() -> str:
    source = (V2 / "real-model-prompt.toml").read_text(encoding="utf-8")
    draft = tomllib.loads((DRAFT / "real-model-prompt.toml").read_text(encoding="utf-8"))
    modality = draft["replacement"]["storage_modality"]["review_text"].strip()
    selection = draft["replacement"]["service_selection"]["review_text"].strip()
    services = draft["replacement"]["services_to_request"]["review_text"].strip()
    why = draft["replacement"]["why_it_matters"]["review_text"].strip()
    old_modality = """Across `question`, `information_it_would_clarify`, `why_it_matters`, and
`grounding_summary`, describe temporary storage only as a possible need or
something that may be needed. Do not describe storage as required, a
requirement, something the user must use, or something the user will need."""
    old_selection = """Do not describe a service, provider, mover, or moving-service type as
appropriate, best, suitable, or recommended. Do not select, recommend,
compare, rank, or score a moving-service model or provider."""
    source = _replace_once(source, old_modality, modality)
    source = _replace_once(source, old_selection, selection + "\n\n" + services)
    source = _replace_once(
        source,
        "For each suggestion:\n",
        why + "\n\nFor each suggestion:\n",
    )
    source = _replace_once(
        source,
        "- Keep `why_it_matters` and `reason_not_deterministic` concise.",
        "- Keep `reason_not_deterministic` concise.",
    )
    source = source.replace("For prompt v2,", "For prompt v3,", 1)
    source = source.replace(
        'prompt_version = "moving-service-questions-prompt-v2"',
        'prompt_version = "moving-service-questions-prompt-v3"',
    )
    source = source.replace(
        'compatible_request_schema_version = "moving-service-questions-schema-v2"',
        'compatible_request_schema_version = "moving-service-questions-schema-v3"',
    )
    source = source.replace(
        'compatible_response_schema_version = "moving-service-questions-schema-v2"',
        'compatible_response_schema_version = "moving-service-questions-schema-v3"',
    )
    source = source.replace(
        'response_model = "MovingServiceQuestionResponseV2"',
        'response_model = "MovingServiceQuestionResponseV3"',
    )
    source = source.replace(
        'source_model = "MovingServiceQuestionRequestV2"',
        'source_model = "MovingServiceQuestionRequestV3"',
    )
    source = source.replace(
        'prompt_artifact_digest_status = "authoritative_digest_in_v2_manifest"',
        'prompt_artifact_digest_status = "authoritative_digest_in_v3_manifest"',
    )
    source = source.replace(
        'digest_status = "authoritative_digest_in_v2_manifest"',
        'digest_status = "authoritative_digest_in_v3_manifest"',
    )
    source = source.replace("prompt_v2_approved = true", "prompt_v3_approved = true")
    source = source.replace("Prompt v2", "Prompt v3")
    return source


def _replace_identities(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _replace_identities(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_replace_identities(item) for item in value]
    if isinstance(value, str):
        replacements = (
            ("MovingServiceQuestionRequestV2", "MovingServiceQuestionRequestV3"),
            ("MovingServiceQuestionResponseV2", "MovingServiceQuestionResponseV3"),
            ("moving-service-questions-prompt-v2", "moving-service-questions-prompt-v3"),
            ("moving-service-questions-schema-v2", "moving-service-questions-schema-v3"),
            ("moving-service-request-fixtures-v2", "moving-service-request-fixtures-v3"),
            ("moving-service-response-fixtures-v2", "moving-service-response-fixtures-v3"),
            ("moving-service-expectations-v2", "moving-service-expectations-v3"),
            ("valid_storage_suggestion_v2", "valid_storage_suggestion_v3"),
            ("valid_zero_suggestions_v2", "valid_zero_suggestions_v3"),
            ("invalid_multiple_prose_violations_v2", "invalid_multiple_prose_violations_v3"),
            (
                "A possible need for temporary storage is relevant when identifying services to request.",
                "This clarifies what to discuss when planning the move.",
            ),
        )
        for old, new in replacements:
            value = value.replace(old, new)
    return value


def provider_schema_review() -> str:
    source = (V2 / "openai-response-schema-review.md").read_text(encoding="utf-8")
    source = source.replace("# OpenAI Response-Schema Review — V2", "# OpenAI Response-Schema Review — V3")
    source = source.replace("review date: 2026-08-02", "freeze date: 2026-08-07")
    source = source.replace("MovingServiceQuestionResponseV2", "MovingServiceQuestionResponseV3")
    source = source.replace("exact v2 prompt literal", "exact v3 prompt literal")
    source = source.replace("exact v2 schema literal", "exact v3 schema literal")
    source = source.replace("prompt-v2 false policy", "prompt-v3 false policy")
    source = source.replace("prompt-v2 empty policy", "prompt-v3 empty policy")
    return source


def _normalize_schema_identity(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _normalize_schema_identity(item)
            for key, item in value.items()
            if key != "title"
        }
    if isinstance(value, list):
        return [_normalize_schema_identity(item) for item in value]
    if value == "moving-service-questions-prompt-v3":
        return "moving-service-questions-prompt-v2"
    if value == "moving-service-questions-schema-v3":
        return "moving-service-questions-schema-v2"
    return value


def schema_diff_record(v2_schema: dict[str, Any], v3_schema: dict[str, Any]) -> dict[str, Any]:
    if _normalize_schema_identity(v2_schema) != _normalize_schema_identity(v3_schema):
        raise ValueError("schema v3 differs from v2 beyond titles and identity literals")
    return {
        "artifact_version": "moving-service-schema-v2-v3-diff-v1",
        "status": "reviewed_and_frozen",
        "source_models": [
            "MovingServiceQuestionResponseV2",
            "MovingServiceQuestionResponseV3",
        ],
        "allowed_difference_classes": [
            "generated_title",
            "prompt_version_literal",
            "schema_version_literal",
        ],
        "observed_identity_changes": {
            "prompt_version": {
                "from": "moving-service-questions-prompt-v2",
                "to": "moving-service-questions-prompt-v3",
            },
            "schema_version": {
                "from": "moving-service-questions-schema-v2",
                "to": "moving-service-questions-schema-v3",
            },
            "root_title": {
                "from": "MovingServiceQuestionResponseV2",
                "to": "MovingServiceQuestionResponseV3",
            },
        },
        "normalized_schemas_equal": True,
        "fields_changed": [],
        "required_lists_changed": False,
        "types_changed": False,
        "enums_changed": False,
        "constraints_changed": False,
        "nested_structures_changed": False,
        "additional_properties_behavior_changed": False,
    }


def freeze_record() -> str:
    return """# Prompt V3 Freeze Record

Prompt v3 responds to the consumed live v2 response that passed structure and
semantics but failed storage-modality and service-selection prose checks. The
raw response was not retained. Existing validators remain unchanged; prompt v3
is intentionally stricter in five documented synthetic cases.

Schema v3 changes only prompt/schema literals and generated root titles.
Fallback remains `moving-service-fallback-v2`. No live v3 generation has
occurred. Bounded rejected-prose diagnostics remain a separate future
milestone. Freezing does not authorize credentials, preflight, generation,
formal evaluation, Stage C, production, FastAPI, or frontend use.
"""


def materialize() -> dict[str, str]:
    V3.mkdir(parents=True, exist_ok=True)
    _write_text(V3 / "real-model-prompt.toml", finalized_prompt_text())
    for name in (
        "deterministic-baseline.json",
        "request-fixtures.json",
        "response-fixtures.json",
        "expected-results.json",
    ):
        value = json.loads((V2 / name).read_text(encoding="utf-8"))
        _write_json(V3 / name, _replace_identities(value))
    _write_text(
        V3 / "knowledge-source-review.md",
        (V2 / "knowledge-source-review.md").read_text(encoding="utf-8"),
    )
    for name in ("synthetic-language-cases.json", "expected-language-results.json"):
        value = json.loads((DRAFT / name).read_text(encoding="utf-8"))
        value["status"] = "reviewed_and_frozen"
        _write_json(V3 / name, value)

    raw_v2_schema = MovingServiceQuestionResponseV2.model_json_schema()
    raw_schema = MovingServiceQuestionResponseV3.model_json_schema()
    provider_schema = adapt_response_schema_for_openai_v3(raw_schema)
    _write_json(V3 / "schema-v2-v3-diff.json", schema_diff_record(raw_v2_schema, raw_schema))
    _write_json(V3 / "openai-response-schema.json", provider_schema)
    _write_text(V3 / "openai-response-schema-review.md", provider_schema_review())
    _write_json(V3 / "provider-schema-adaptation.json", {
        "artifact_version": "moving-service-openai-schema-adaptation-v3",
        "status": "reviewed_and_frozen",
        "source_model": "MovingServiceQuestionResponseV3",
        "source_method": "model_json_schema",
        "provider": "OpenAI",
        "structured_output_mode": "strict_json_schema",
        "mechanical_adaptation": {
            "remove_nonsemantic_titles_only": True,
            "required_fields_may_be_removed": False,
            "types_may_be_broadened": False,
            "allowed_values_may_be_broadened": False,
            "length_or_array_limits_may_be_weakened": False,
            "extra_field_prohibitions_may_be_removed": False,
        },
        "provider_snapshot_path": "docs/experiments/suggest-moving-service-questions/v3/openai-response-schema.json",
        "provider_snapshot_review_path": "docs/experiments/suggest-moving-service-questions/v3/openai-response-schema-review.md",
        "provider_snapshot_created": True,
        "provider_snapshot_reviewed": True,
        "provider_snapshot_frozen": True,
        "runtime_pydantic_validation_authoritative": True,
    })
    _write_text(V3 / "freeze-record.md", freeze_record())

    artifact_names = (
        "real-model-prompt.toml",
        "openai-response-schema.json",
        "openai-response-schema-review.md",
        "provider-schema-adaptation.json",
        "schema-v2-v3-diff.json",
        "deterministic-baseline.json",
        "request-fixtures.json",
        "response-fixtures.json",
        "expected-results.json",
        "knowledge-source-review.md",
        "synthetic-language-cases.json",
        "expected-language-results.json",
        "freeze-record.md",
    )
    digests = {name: _digest(V3 / name) for name in artifact_names}
    manifest = {
        "capability": "suggest_moving_service_questions",
        "artifact_version": "moving-service-prompt-v3-artifacts-v1",
        "status": "reviewed_and_frozen",
        "digest_algorithm": "sha256",
        "prompt_version": "moving-service-questions-prompt-v3",
        "request_schema_version": "moving-service-questions-schema-v3",
        "response_schema_version": "moving-service-questions-schema-v3",
        "knowledge_fixture_version": "moving-service-storage-fixture-v2",
        "fallback_version": "moving-service-fallback-v2",
        "source_draft_commit": "77c8dcaf8f6533f4142c75ebf26a989d84ebd99b",
        "source_frozen_v2_manifest_digest": _digest(V2 / "manifest.json"),
        "artifact_digests": digests,
        "manifest_digest_policy": "computed_after_finalization_and pinned in offline drift tests",
        "prompt_v3_approved": True,
        "prompt_v3_frozen": True,
        "schema_v3_approved": True,
        "schema_v3_frozen": True,
        "provider_schema_reviewed": True,
        "provider_schema_frozen": True,
        "fallback_v2_reused": True,
        "existing_prose_validators_unchanged": True,
        "live_generation_authorized": False,
        "credential_access_authorized": False,
        "token_preflight_authorized": False,
        "formal_evaluation_authorized": False,
        "stage_c_authorized": False,
        "production_use_authorized": False,
        "fastapi_exposure_authorized": False,
        "frontend_exposure_authorized": False,
    }
    _write_json(V3 / "manifest.json", manifest)
    return {**digests, "manifest.json": _digest(V3 / "manifest.json")}


def main() -> int:
    for name, digest in materialize().items():
        print(f"{name}={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
