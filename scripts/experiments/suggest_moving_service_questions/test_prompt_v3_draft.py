"""Offline review tests for the unfrozen, unauthorized prompt-v3 draft."""

from __future__ import annotations

import hashlib
import json
import tomllib
from pathlib import Path

from moving_service_questions_v2 import (
    PROSE_VIOLATION_CODE_ORDER,
    MovingServiceQuestionResponseV2,
    _contains_selection_language,
    _contains_storage_modality_overstatement,
    collect_prose_violation_codes,
)
from run_openai_stage_b_v2_pilot import prepare_frozen_v2_pilot
from test_openai_stage_b_v2_pilot import valid_response


ROOT = Path(__file__).resolve().parents[3]
DRAFT = ROOT / "docs/experiments/suggest-moving-service-questions/v3-draft"
V2_PROMPT = ROOT / "docs/experiments/suggest-moving-service-questions/v2/real-model-prompt.toml"
V2_VALIDATOR = ROOT / "scripts/experiments/suggest_moving_service_questions/moving_service_questions_v2.py"


def _load_cases() -> list[dict[str, object]]:
    return json.loads((DRAFT / "synthetic-language-cases.json").read_text())["cases"]


def _actual_rejection(case: dict[str, object]) -> bool:
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


def test_prompt_v3_draft_parses_and_is_non_authoritative() -> None:
    draft = tomllib.loads((DRAFT / "real-model-prompt.toml").read_text())
    assert draft["draft"] == {
        "status": "draft_unfrozen_unauthorized",
        "artifact_form": "reviewable_delta_from_frozen_v2_not_executable_prompt",
        "live_execution_valid": False,
        "frozen": False,
        "authorized": False,
    }
    assert draft["identity"]["prompt_version"] == "moving-service-questions-prompt-v3"
    assert draft["identity"]["prompt_version"] != "moving-service-questions-prompt-v2"
    assert all(value is False for value in draft["authorization"].values())
    assert draft["examples"]["positive_examples_included"] is False


def test_frozen_v2_and_current_validators_are_exactly_unchanged() -> None:
    assert hashlib.sha256(V2_PROMPT.read_bytes()).hexdigest() == (
        "9bcc190f9c4c51fba1caed8c5d284de9d29d6fe8d675132a04f741cc9a1af7a6"
    )
    assert hashlib.sha256(V2_VALIDATOR.read_bytes()).hexdigest() == (
        "8b00becd2a6491ec5c2fbc267732fbe685cacf509899994480fc4052baf8af33"
    )
    assert PROSE_VIOLATION_CODE_ORDER == (
        "irrelevant_location_reference",
        "unsupported_home_or_property_assertion",
        "storage_modality_overstatement",
        "unsupported_service_selection_language",
        "grounding_summary_mismatch",
    )


def test_schema_v3_proposal_is_literal_only() -> None:
    draft = tomllib.loads((DRAFT / "real-model-prompt.toml").read_text())
    schema = draft["schema_review"]
    assert schema["schema_v3_identity_required"] is True
    for field in (
        "field_changes", "type_changes", "enum_changes", "constraint_changes",
        "required_field_changes", "extra_field_behavior_changes",
    ):
        assert schema[field] == []


def test_every_synthetic_case_matches_the_unchanged_validator() -> None:
    cases = _load_cases()
    assert len(cases) == 28
    for case in cases:
        assert _actual_rejection(case) is case["validator_rejected"], case["id"]


def test_prompt_policy_has_no_allowed_validator_rejection() -> None:
    for case in _load_cases():
        if case["prompt_v3_status"] == "allowed":
            assert case["validator_rejected"] is False, case["id"]


def test_expected_prompt_stricter_mismatches_are_explicit() -> None:
    expected = json.loads((DRAFT / "expected-language-results.json").read_text())
    actual = {
        case["id"]
        for case in _load_cases()
        if case["prompt_v3_status"] == "prohibited"
        and case["validator_rejected"] is False
    }
    assert actual == set(expected["known_mismatch_ids"])
    assert len(actual) == expected["expected_counts"]["known_prompt_validator_mismatches"]


def test_exact_grounding_summary_equality_remains_unchanged() -> None:
    prepared = prepare_frozen_v2_pilot()
    document = valid_response()
    response = MovingServiceQuestionResponseV2.model_validate(document)
    assert "grounding_summary_mismatch" not in collect_prose_violation_codes(
        prepared.request, response
    )
    document["suggestions"][0]["grounding_summary"] += " "  # type: ignore[index]
    response = MovingServiceQuestionResponseV2.model_validate(document)
    assert "grounding_summary_mismatch" in collect_prose_violation_codes(
        prepared.request, response
    )


def test_draft_contains_no_live_configuration_or_authorization_package() -> None:
    names = {path.name for path in DRAFT.iterdir()}
    assert not any("authorization" in name or "pilot" in name for name in names)
    assert names == {
        "real-model-prompt.toml",
        "prompt-v3-design-review.md",
        "synthetic-language-cases.json",
        "expected-language-results.json",
        "schema-diff-review.md",
    }


def test_no_runtime_path_references_prompt_v3_or_exposes_it() -> None:
    offline_v3_files = {
        "freeze_prompt_v3_artifacts.py",
        "moving_service_questions_v3.py",
        "openai_transport_v3.py",
        "run_openai_stage_b_v3_pilot.py",
        "run_openai_stage_b_v3_sequence_1_preflight_live.py",
        "run_openai_stage_b_v3_sequence_1_preflight_synthetic.py",
        "run_openai_stage_b_v3_sequence_4_generation_live.py",
        "run_openai_stage_b_v3_sequence_4_generation_synthetic.py",
        "test_prompt_v3_draft.py",
        "test_prompt_v3_frozen.py",
        "test_v3_sequence_4_generation_gate.py",
        "test_v3_sequence_4_generation_operator_boundary.py",
        "test_v3_sequence_1_preflight.py",
        "test_v3_sequence_1_preflight_operator_boundary.py",
        "v3_sequence_1_preflight.py",
        "v3_sequence_1_preflight_cli.py",
        "v3_sequence_4_generation_gate.py",
        "v3_sequence_4_generation_operator_cli.py",
        "v3_sequence_4_generation_rehearsal_assertions.py",
        "freeze_prompt_v4_artifacts.py",
        "moving_service_questions_v4.py",
        "openai_transport_v4.py",
        "run_openai_stage_b_v4_pilot.py",
        "test_prompt_v4_frozen.py",
    }
    runtime_files = list((ROOT / "backend").rglob("*.py")) + list(
        (ROOT / "scripts/experiments/suggest_moving_service_questions").glob("*.py")
    )
    for path in runtime_files:
        if path.name in offline_v3_files:
            continue
        assert "moving-service-questions-prompt-v3" not in path.read_text(), path
    assert not list((ROOT / "frontend/src").rglob("*v3*"))
