"""Offline diagnostic matrices for the unchanged prompt-v2 prose guardrails."""

from __future__ import annotations

import copy

import pytest

from moving_service_questions_v2 import (
    MovingServiceQuestionResponseV2,
    _contains_selection_language,
    _contains_storage_modality_overstatement,
    collect_prose_violation_codes,
)
from run_openai_stage_b_v2_pilot import prepare_frozen_v2_pilot
from test_openai_stage_b_v2_pilot import valid_response


@pytest.mark.parametrize(("text", "rejected"), [
    ("Temporary storage may be needed.", False),
    ("Temporary storage might be needed.", False),
    ("Temporary storage could be needed.", False),
    ("Temporary storage may need to be arranged.", False),
    ("Do you need temporary storage?", False),
    ("You likely need temporary storage.", False),
    ("You are expected to need temporary storage.", False),
    ("Temporary storage is necessary.", False),
    ("Is temporary storage required?", True),
    ("Is temporary storage a requirement?", True),
    ("You must arrange temporary storage.", True),
    ("You will need temporary storage.", True),
])
def test_storage_modality_diagnostic_matrix(text: str, rejected: bool) -> None:
    assert _contains_storage_modality_overstatement(text) is rejected


@pytest.mark.parametrize(("text", "rejected"), [
    ("Which services to request", False),
    ("Which moving services to request", False),
    ("Services that may be needed", False),
    ("Services to discuss", False),
    ("Available service options", False),
    ("Possible service needs", False),
    ("Appropriate, moving services", False),
    ("Appropriate local moving services", False),
    ("Appropriate moving services", True),
    ("Best moving services", True),
    ("Suitable movers", True),
    ("Recommended service model", True),
])
def test_service_selection_diagnostic_matrix(text: str, rejected: bool) -> None:
    assert _contains_selection_language(text) is rejected


@pytest.mark.parametrize(
    "field",
    ("question", "information_it_would_clarify", "why_it_matters", "grounding_summary"),
)
def test_storage_modality_exact_field_coverage(field: str) -> None:
    prepared = prepare_frozen_v2_pilot()
    document = copy.deepcopy(valid_response())
    document["suggestions"][0][field] = "Temporary storage will need confirmation."  # type: ignore[index]
    response = MovingServiceQuestionResponseV2.model_validate(document)
    assert "storage_modality_overstatement" in collect_prose_violation_codes(
        prepared.request, response
    )


@pytest.mark.parametrize(
    "field", ("question", "information_it_would_clarify", "why_it_matters")
)
def test_service_selection_exact_field_coverage(field: str) -> None:
    prepared = prepare_frozen_v2_pilot()
    document = copy.deepcopy(valid_response())
    document["suggestions"][0][field] = "Identify appropriate moving services."  # type: ignore[index]
    response = MovingServiceQuestionResponseV2.model_validate(document)
    assert "unsupported_service_selection_language" in collect_prose_violation_codes(
        prepared.request, response
    )


def test_service_selection_does_not_inspect_grounding_or_reason_fields() -> None:
    prepared = prepare_frozen_v2_pilot()
    document = copy.deepcopy(valid_response())
    suggestion = document["suggestions"][0]  # type: ignore[index]
    suggestion["grounding_summary"] = "Identify appropriate moving services."
    suggestion["reason_not_deterministic"] = "Identify recommended providers."
    response = MovingServiceQuestionResponseV2.model_validate(document)
    codes = collect_prose_violation_codes(prepared.request, response)
    assert "unsupported_service_selection_language" not in codes
    assert codes == ("grounding_summary_mismatch",)


def test_live_pair_retains_stable_policy_order() -> None:
    prepared = prepare_frozen_v2_pilot()
    document = copy.deepcopy(valid_response())
    suggestion = document["suggestions"][0]  # type: ignore[index]
    suggestion["question"] = "Will temporary storage be required?"
    suggestion["why_it_matters"] = "Identify appropriate moving services."
    response = MovingServiceQuestionResponseV2.model_validate(document)
    assert collect_prose_violation_codes(prepared.request, response) == (
        "storage_modality_overstatement",
        "unsupported_service_selection_language",
    )
