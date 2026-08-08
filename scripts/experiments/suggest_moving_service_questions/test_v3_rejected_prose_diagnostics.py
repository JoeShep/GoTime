"""Bounded, observational diagnostics for future rejected prose."""

from __future__ import annotations

import copy
import json

import pytest

from moving_service_questions_v2 import (
    MovingServiceQuestionResponseV2,
    ProseValidationError,
    collect_prose_violation_codes,
    validate_response_v2,
)
from moving_service_questions_v3 import PROMPT_VERSION_V3, SCHEMA_VERSION_V3
from rejected_prose_diagnostics import (
    STORAGE_MODALITY_TRIGGERS,
    collect_prose_violation_diagnostics,
)
from run_openai_stage_b_v2_pilot import prepare_frozen_v2_pilot
from test_openai_stage_b_v2_pilot import valid_response
from v3_sequence_4_generation_gate import generation_paths, write_generation_outcome
from datetime import datetime, timezone


FIELDS = ("question", "information_it_would_clarify", "why_it_matters", "grounding_summary")


def _response(field: str, text: str) -> tuple[object, MovingServiceQuestionResponseV2]:
    prepared = prepare_frozen_v2_pilot()
    document = copy.deepcopy(valid_response())
    document["suggestions"][0][field] = text
    return prepared.request, MovingServiceQuestionResponseV2.model_validate(document)


@pytest.mark.parametrize("trigger", STORAGE_MODALITY_TRIGGERS)
@pytest.mark.parametrize("field", FIELDS)
def test_every_storage_trigger_has_bounded_field_and_offsets(trigger: str, field: str) -> None:
    prefix = "Ask whether storage is "
    text = f"{prefix}{trigger.upper()} today."
    request, response = _response(field, text)
    diagnostics = [
        item for item in collect_prose_violation_diagnostics(request, response)
        if item.violation_code == "storage_modality_overstatement"
    ]
    assert collect_prose_violation_codes(request, response)[0] == "storage_modality_overstatement"
    assert len(diagnostics) == 1
    item = diagnostics[0]
    assert item.field == field
    assert item.start_offset == len(prefix)
    assert item.end_offset == len(prefix) + len(trigger)
    assert item.canonical_trigger == trigger
    assert item.occurrence_count == 1
    assert set(item.as_dict()) == {
        "violation_code", "rule_id", "field", "start_offset", "end_offset",
        "canonical_trigger", "occurrence_count",
    }


def test_multiple_occurrences_and_different_triggers_are_deterministic() -> None:
    text = "Storage MUST be discussed; storage must wait; storage will\n need review."
    request, response = _response("question", text)
    diagnostics = [item for item in collect_prose_violation_diagnostics(request, response)
                   if item.violation_code == "storage_modality_overstatement"]
    assert [(item.canonical_trigger, item.occurrence_count) for item in diagnostics] == [
        ("must", 2), ("will need", 1),
    ]
    assert text[diagnostics[0].start_offset:diagnostics[0].end_offset] == "MUST"
    assert text[diagnostics[1].start_offset:diagnostics[1].end_offset] == "will\n need"


@pytest.mark.parametrize("text", [
    "Storage may be needed.", "Storage might be needed.", "Storage could be needed.",
    "Storage likely needs discussion.", "Storage is necessary.",
    "Storage and mustard are separate.", "The storage requirementful note.",
])
def test_harmless_or_out_of_vocabulary_forms_have_no_modality_diagnostic(text: str) -> None:
    request, response = _response("question", text)
    assert not [item for item in collect_prose_violation_diagnostics(request, response)
                if item.violation_code == "storage_modality_overstatement"]


def test_punctuation_boundaries_and_cross_rule_order_match_existing_validator() -> None:
    request, response = _response(
        "question", "Storage: required; identify appropriate moving services."
    )
    old_codes = collect_prose_violation_codes(request, response)
    diagnostics = collect_prose_violation_diagnostics(request, response)
    new_codes = tuple(dict.fromkeys(item.violation_code for item in diagnostics))
    assert old_codes == new_codes == (
        "storage_modality_overstatement", "unsupported_service_selection_language",
    )


@pytest.mark.parametrize("text", [
    "Storage is required.", "You must discuss storage.",
    "Storage is a requirement and will need review.",
    "Storage may be needed.", "Identify appropriate moving services.",
])
def test_validation_decisions_and_order_are_unchanged(text: str) -> None:
    request, response = _response("question", text)
    old_codes = collect_prose_violation_codes(request, response)
    diagnostic_codes = tuple(dict.fromkeys(
        item.violation_code for item in collect_prose_violation_diagnostics(request, response)
    ))
    assert diagnostic_codes == old_codes
    if old_codes:
        with pytest.raises(ProseValidationError) as error:
            validate_response_v2(request, response.model_dump(mode="json"))
        assert error.value.violation_codes == old_codes
    else:
        assert validate_response_v2(request, response.model_dump(mode="json")) == response


def test_future_audit_retains_only_bounded_diagnostics(tmp_path) -> None:
    raw = copy.deepcopy(valid_response())
    raw["prompt_version"] = PROMPT_VERSION_V3
    raw["schema_version"] = SCHEMA_VERSION_V3
    full_question = "PRIVATE SYNTHETIC PREFIX storage WILL NEED attention PRIVATE SYNTHETIC SUFFIX"
    raw["suggestions"][0]["question"] = full_question
    outcome = write_generation_outcome(output_root=tmp_path, raw=raw, now=datetime.now(timezone.utc))
    paths = generation_paths(tmp_path)
    audit_text = paths.audit.read_text()
    audit = json.loads(audit_text)
    assert outcome["validation_outcome"] == "prose_failure"
    assert audit["rejected_prose_diagnostics"] == [{
        "canonical_trigger": "will need",
        "end_offset": 42,
        "field": "question",
        "occurrence_count": 1,
        "rule_id": "moving-service-prose-v2.1",
        "start_offset": 33,
        "violation_code": "storage_modality_overstatement",
    }]
    assert full_question not in audit_text
    assert "PRIVATE SYNTHETIC PREFIX" not in audit_text
    assert "PRIVATE SYNTHETIC SUFFIX" not in audit_text
    assert "storage WILL NEED attention" not in audit_text
    assert "provider_raw_response" not in audit
    assert "response" not in audit
    assert not paths.response_evidence.exists()


def test_json_string_rejection_has_identical_bounded_diagnostics(tmp_path) -> None:
    raw = copy.deepcopy(valid_response())
    raw["prompt_version"] = PROMPT_VERSION_V3
    raw["schema_version"] = SCHEMA_VERSION_V3
    raw["suggestions"][0]["question"] = "Storage is required."
    outcome = write_generation_outcome(
        output_root=tmp_path, raw=json.dumps(raw), now=datetime.now(timezone.utc)
    )
    assert outcome["prose_violation_codes"] == ["storage_modality_overstatement"]
    assert outcome["rejected_prose_diagnostics"][0]["canonical_trigger"] == "required"
