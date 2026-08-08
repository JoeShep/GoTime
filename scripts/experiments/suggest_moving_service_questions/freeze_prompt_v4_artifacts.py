"""Deterministically materialize the approved, offline frozen prompt-v4 package."""

from __future__ import annotations

import hashlib
import json
import tomllib
from pathlib import Path
from typing import Any

from moving_service_questions_v3 import MovingServiceQuestionResponseV3
from moving_service_questions_v4 import MovingServiceQuestionResponseV4, adapt_response_schema_for_openai_v4

ROOT = Path(__file__).resolve().parents[3]
CAPABILITY = ROOT / "docs/experiments/suggest-moving-service-questions"
V3 = CAPABILITY / "v3"
V4 = CAPABILITY / "v4"
DESIGN = CAPABILITY / "prompt-v4-design-memo.md"
PILOT = CAPABILITY / "v2/openai-follow-up-pilot.toml"
DETERMINISTIC_REQUEST_DIGEST = "f5a8c7e06d2ad9e133a5b0b92c322f09ed67205feb25314c5114fa1849fcdd0a"
CANONICAL_ATTEMPT_DIGEST = "7a3c0f7ace4ee4289f4149224fc001b215e71d4cc168edea604516fd133f450d"
PROVIDER_FINGERPRINT = "15caaaaa6a3b43860c426c7555be7f4c7a6bf50d658c92c3c8564c1d43cb5656"


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value if value.endswith("\n") else value + "\n", encoding="utf-8")


def _write_json(path: Path, value: object) -> None:
    _write_text(path, json.dumps(value, indent=2, sort_keys=True))


def _replace_once(value: str, old: str, new: str) -> str:
    if value.count(old) != 1:
        raise ValueError(f"expected exactly one insertion anchor: {old[:40]!r}")
    return value.replace(old, new, 1)


GROUNDING_SEPARATION = """Treat curated knowledge as evidence, not as a writing style to imitate in
generated user-facing prose. `question`, `information_it_would_clarify`, and
`why_it_matters` must independently obey the possibility-language rules.
`grounding_summary` remains a byte-exact copy of the approved statement and is
not paraphrased. The approved statement must itself contain none of the closed
runtime triggers listed below; if it does, do not generate a suggestion."""

CLOSED_RULE = """Closed runtime lexical rule: none of `question`,
`information_it_would_clarify`, `why_it_matters`, or `grounding_summary` may
contain the whole word `required`, `requirement`, or `must`, or the phrase
`will need`. This exact four-trigger rule is narrower than the broader policy
prohibitions above; both sets remain binding."""

FINAL_CHECK = """Before returning JSON, inspect every generated value for `question`,
`information_it_would_clarify`, and `why_it_matters`. Case-insensitively check
for the whole-word triggers `required`, `requirement`, and `must`, and for
`will need` after treating whitespace as a single space. If any trigger
appears, rewrite the affected field using may/might/could possibility language
and check all three fields again. Never rewrite `grounding_summary`; its exact
approved source is validated deterministically before request construction.
Perform this check silently and do not add fields, warnings, commentary, or
reasoning to the JSON."""


def finalized_prompt_text() -> str:
    source = (V3 / "real-model-prompt.toml").read_text(encoding="utf-8")
    modality_anchor = """`grounding_summary` remains the exact supplied knowledge statement
and is not rewritten under this rule.
"""
    source = _replace_once(source, modality_anchor, modality_anchor + "\n" + CLOSED_RULE + "\n")
    grounding_anchor = "For a `temporary_storage_need` suggestion, copy the exact `statement`"
    source = _replace_once(source, grounding_anchor, GROUNDING_SEPARATION + "\n\n" + grounding_anchor)
    output_anchor = "Copy `capability`, `prompt_version`, and `schema_version` exactly from the\nvalidated request. Return exactly one JSON object with this structure:"
    source = _replace_once(
        source, output_anchor,
        "Copy `capability`, `prompt_version`, and `schema_version` exactly from the\nvalidated request.\n\n"
        + FINAL_CHECK + "\n\nReturn exactly one JSON object with this structure:",
    )
    replacements = (
        ("For prompt v3,", "For prompt v4,"),
        ("moving-service-questions-prompt-v3", "moving-service-questions-prompt-v4"),
        ("moving-service-questions-schema-v3", "moving-service-questions-schema-v4"),
        ("MovingServiceQuestionRequestV3", "MovingServiceQuestionRequestV4"),
        ("MovingServiceQuestionResponseV3", "MovingServiceQuestionResponseV4"),
        ("prompt_v3_approved", "prompt_v4_approved"),
        ("Prompt v3", "Prompt v4"),
        ("authoritative_digest_in_v3_manifest", "authoritative_digest_in_v4_manifest"),
    )
    for old, new in replacements:
        source = source.replace(old, new)
    return source


def _replace_identities(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _replace_identities(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_replace_identities(item) for item in value]
    if isinstance(value, str):
        for old, new in (
            ("moving-service-questions-prompt-v3", "moving-service-questions-prompt-v4"),
            ("moving-service-questions-schema-v3", "moving-service-questions-schema-v4"),
            ("MovingServiceQuestionRequestV3", "MovingServiceQuestionRequestV4"),
            ("MovingServiceQuestionResponseV3", "MovingServiceQuestionResponseV4"),
            ("moving-service-request-fixtures-v3", "moving-service-request-fixtures-v4"),
            ("moving-service-response-fixtures-v3", "moving-service-response-fixtures-v4"),
            ("moving-service-expectations-v3", "moving-service-expectations-v4"),
            ("_v3", "_v4"),
        ):
            value = value.replace(old, new)
    return value


def _normalize_schema(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _normalize_schema(item) for key, item in value.items() if key != "title"}
    if isinstance(value, list):
        return [_normalize_schema(item) for item in value]
    return {"moving-service-questions-prompt-v4": "moving-service-questions-prompt-v3",
            "moving-service-questions-schema-v4": "moving-service-questions-schema-v3"}.get(value, value)


def schema_diff_record(v3_schema: dict[str, Any], v4_schema: dict[str, Any]) -> dict[str, Any]:
    if _normalize_schema(v3_schema) != _normalize_schema(v4_schema):
        raise ValueError("schema v4 differs from v3 beyond titles and identity literals")
    return {
        "artifact_version": "moving-service-schema-v3-v4-diff-v1",
        "status": "reviewed_and_frozen",
        "allowed_difference_classes": ["generated_title", "prompt_version_literal", "schema_version_literal"],
        "observed_identity_changes": {
            "prompt_version": {"from": "moving-service-questions-prompt-v3", "to": "moving-service-questions-prompt-v4"},
            "schema_version": {"from": "moving-service-questions-schema-v3", "to": "moving-service-questions-schema-v4"},
            "root_title": {"from": "MovingServiceQuestionResponseV3", "to": "MovingServiceQuestionResponseV4"},
        },
        "normalized_schemas_equal": True, "fields_changed": [],
        "required_lists_changed": False, "types_changed": False, "enums_changed": False,
        "constraints_changed": False, "nested_structures_changed": False,
        "additional_properties_behavior_changed": False,
    }


def policy_cases() -> dict[str, object]:
    cases = [
        ("required", "question", "Storage is required.", "rewrite", True),
        ("requirement", "question", "Storage is a requirement.", "rewrite", True),
        ("must", "question", "Storage must be discussed.", "rewrite", True),
        ("will_need", "question", "Storage will need discussion.", "rewrite", True),
        ("question_field", "question", "Is storage required?", "rewrite", True),
        ("clarify_field", "information_it_would_clarify", "Whether storage is required.", "rewrite", True),
        ("why_field", "why_it_matters", "Storage must be discussed.", "rewrite", True),
        ("grounding_field", "grounding_summary", "Storage is required.", "preparation_fail_closed", True),
        ("safe_may", "question", "May you need storage?", "allow", False),
        ("safe_might", "question", "Might you need storage?", "allow", False),
        ("safe_could", "question", "Could you need storage?", "allow", False),
        ("service_selection", "why_it_matters", "Identify appropriate moving services.", "rewrite", True),
        ("combined", "why_it_matters", "Storage is required for appropriate moving services.", "rewrite", True),
        ("prompt_stricter", "why_it_matters", "Storage is likely necessary for appropriate, local services.", "rewrite", False),
        ("exact_grounding", "grounding_summary", "For an interstate move handled by a household-goods mover, a possible need for temporary storage before final delivery is relevant when identifying the services to request.", "exact_copy", False),
    ]
    return {"artifact_version": "moving-service-prompt-v4-policy-cases-v1", "status": "reviewed_and_frozen",
            "cases": [{"id": i, "field": f, "text": t, "prompt_policy": p,
                       "runtime_validator_rejected": r} for i, f, t, p, r in cases]}


def grounding_cases() -> dict[str, object]:
    return {"artifact_version": "moving-service-v4-grounding-cases-v1", "status": "reviewed_and_frozen",
            "closed_triggers": ["required", "requirement", "must", "will need"],
            "accepted": ["Storage may be needed.", "Storage might be needed.", "Storage could be needed.",
                         "Storage and mustard.", "A requirementful storage note."],
            "rejected": ["Storage is required.", "Storage is a REQUIREMENT.", "Storage MuSt wait.",
                         "Storage WILL\n NEED review.", "Required storage must wait and will need review."]}


def materialize() -> dict[str, str]:
    V4.mkdir(parents=True, exist_ok=True)
    _write_text(V4 / "real-model-prompt.toml", finalized_prompt_text())
    for name in ("deterministic-baseline.json", "request-fixtures.json", "response-fixtures.json", "expected-results.json"):
        _write_json(V4 / name, _replace_identities(json.loads((V3 / name).read_text())))
    _write_text(V4 / "knowledge-source-review.md", (V3 / "knowledge-source-review.md").read_text())
    _write_json(V4 / "adversarial-policy-cases.json", policy_cases())
    _write_json(V4 / "expected-policy-results.json", {
        "artifact_version": "moving-service-prompt-v4-policy-expectations-v1",
        "case_expectations": {case["id"]: {"prompt_policy": case["prompt_policy"],
                                               "runtime_validator_rejected": case["runtime_validator_rejected"]}
                              for case in policy_cases()["cases"]},
    })
    _write_json(V4 / "grounding-fail-closed-cases.json", grounding_cases())
    v3_schema = MovingServiceQuestionResponseV3.model_json_schema()
    v4_schema = MovingServiceQuestionResponseV4.model_json_schema()
    _write_json(V4 / "schema-v3-v4-diff.json", schema_diff_record(v3_schema, v4_schema))
    _write_json(V4 / "openai-response-schema.json", adapt_response_schema_for_openai_v4(v4_schema))
    review = (V3 / "openai-response-schema-review.md").read_text().replace("V3", "V4").replace("v3", "v4")
    _write_text(V4 / "openai-response-schema-review.md", review)
    _write_json(V4 / "provider-schema-adaptation.json", {
        "artifact_version": "moving-service-openai-schema-adaptation-v4", "status": "reviewed_and_frozen",
        "source_model": "MovingServiceQuestionResponseV4", "source_method": "model_json_schema",
        "provider": "OpenAI", "structured_output_mode": "strict_json_schema",
        "remove_nonsemantic_titles_only": True, "constraints_preserved": True,
        "provider_snapshot_path": "docs/experiments/suggest-moving-service-questions/v4/openai-response-schema.json",
        "runtime_pydantic_validation_authoritative": True,
    })
    pilot = tomllib.loads(PILOT.read_text())
    _write_json(V4 / "offline-pilot-request-config.json", {
        "status": "frozen_offline_only", "fixture": "storage_unknown",
        "category": "temporary_storage_need", "provider": pilot["identity"]["provider"],
        "model": pilot["identity"]["ai_model_identifier"], "sdk": pilot["identity"]["sdk_pin"],
        "temperature": pilot["model_parameters"]["temperature"],
        "top_p": pilot["model_parameters"]["top_p"],
        "seed": pilot["model_parameters"]["seed"],
        "maximum_output_tokens": pilot["model_parameters"]["maximum_output_tokens"],
        "truncation": pilot["model_parameters"]["truncation"],
        "token_preflight_timeout_seconds": pilot["transport"]["token_preflight_timeout_seconds"],
        "generation_timeout_seconds": pilot["transport"]["ai_generation_timeout_seconds"],
        "automatic_retries": pilot["transport"]["automatic_retries"],
        "maximum_total_spend_usd": pilot["limits"]["maximum_total_spend_usd"],
        "tools": [], "store": False, "stream": False, "background": False,
        "token_preflight_authorized": False, "generation_authorized": False,
    })
    _write_json(V4 / "request-identity.json", {
        "artifact_version": "moving-service-request-identity-v4",
        "status": "reviewed_and_frozen",
        "prompt_version": "moving-service-questions-prompt-v4",
        "schema_version": "moving-service-questions-schema-v4",
        "fixture": "storage_unknown",
        "category": "temporary_storage_need",
        "deterministic_request_sha256": DETERMINISTIC_REQUEST_DIGEST,
        "canonical_attempt_sha256": CANONICAL_ATTEMPT_DIGEST,
        "provider_fingerprint": PROVIDER_FINGERPRINT,
        "provider": pilot["identity"]["provider"],
        "ai_model_identifier": pilot["identity"]["ai_model_identifier"],
        "sdk": pilot["identity"]["sdk_pin"],
    })
    _write_text(V4 / "freeze-record.md", """# Prompt V4 Freeze Record

Prompt v4 makes only the approved instruction-salience changes after the single
frozen-v3 modality rejection. The historical field and trigger remain unknown.
The existing validator and fallback v2 are unchanged. Grounding remains byte-
exact, and prohibited grounding fails before provider-request construction.
The manifest-bound request-identity artifact freezes the deterministic request,
canonical attempt, and provider fingerprint for exact offline reproduction.
No provider operation or live v4 authorization exists.
""")
    names = tuple(path.name for path in sorted(V4.iterdir()) if path.name != "manifest.json")
    digests = {name: _digest(V4 / name) for name in names}
    _write_json(V4 / "manifest.json", {
        "capability": "suggest_moving_service_questions", "artifact_version": "moving-service-prompt-v4-artifacts-v1",
        "status": "reviewed_and_frozen", "digest_algorithm": "sha256",
        "prompt_version": "moving-service-questions-prompt-v4",
        "request_schema_version": "moving-service-questions-schema-v4",
        "response_schema_version": "moving-service-questions-schema-v4",
        "knowledge_fixture_version": "moving-service-storage-fixture-v2",
        "fallback_version": "moving-service-fallback-v2", "fallback_question_id": "fallback-temporary-storage-v2",
        "source_design_memo_digest": _digest(DESIGN), "source_frozen_v3_manifest_digest": _digest(V3 / "manifest.json"),
        "artifact_digests": digests, "prompt_v4_approved": True, "prompt_v4_frozen": True,
        "schema_v4_approved": True, "schema_v4_frozen": True, "provider_schema_frozen": True,
        "existing_prose_validators_unchanged": True, "fallback_v2_reused": True,
        "live_generation_authorized": False, "credential_access_authorized": False,
        "token_preflight_authorized": False, "formal_evaluation_authorized": False,
        "stage_c_authorized": False, "production_use_authorized": False,
        "fastapi_exposure_authorized": False, "frontend_exposure_authorized": False,
    })
    return {**digests, "manifest.json": _digest(V4 / "manifest.json")}


if __name__ == "__main__":
    for name, digest in materialize().items():
        print(f"{name}={digest}")
