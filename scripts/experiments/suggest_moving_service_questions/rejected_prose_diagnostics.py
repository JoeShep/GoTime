"""Observational diagnostics layered beside the immutable v2 prose validator."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.moving_service_questions import MissingInformationCategory, STORAGE_KNOWLEDGE
from moving_service_questions_v2 import (
    HOME_OR_PROPERTY_PHRASES,
    PROSE_FIELDS,
    PROSE_VIOLATION_CODE_ORDER,
    SELECTION_ADJECTIVES,
    SELECTION_NOUN_PATTERNS,
    STORAGE_MODALITY_FIELDS,
    MovingServiceQuestionRequestV2,
    MovingServiceQuestionResponseV2,
    collect_prose_violation_codes,
)

RULE_ID = "moving-service-prose-v2.1"
STORAGE_MODALITY_TRIGGERS = ("required", "requirement", "must", "will need")


@dataclass(frozen=True)
class ProseViolationDiagnostic:
    violation_code: str
    rule_id: str
    field: str
    start_offset: int
    end_offset: int
    canonical_trigger: str
    occurrence_count: int = 1

    def as_dict(self) -> dict[str, object]:
        return {
            "violation_code": self.violation_code, "rule_id": self.rule_id,
            "field": self.field, "start_offset": self.start_offset,
            "end_offset": self.end_offset, "canonical_trigger": self.canonical_trigger,
            "occurrence_count": self.occurrence_count,
        }


def _normalize(value: str) -> tuple[str, tuple[int, ...]]:
    normalized: list[str] = []
    offsets: list[int] = []
    pending_space: int | None = None
    for offset, character in enumerate(value):
        if character.isspace():
            if normalized and pending_space is None:
                pending_space = offset
            continue
        if pending_space is not None:
            normalized.append(" ")
            offsets.append(pending_space)
            pending_space = None
        for folded in character.casefold():
            normalized.append(folded)
            offsets.append(offset)
    return "".join(normalized), tuple(offsets)


def _add_matches(
    target: list[ProseViolationDiagnostic], *, value: str, field: str,
    code: str, pattern: str, canonical: str,
) -> None:
    normalized, offsets = _normalize(value)
    matches = tuple(re.finditer(pattern, normalized))
    if matches:
        first = matches[0]
        target.append(ProseViolationDiagnostic(
            code, RULE_ID, field, offsets[first.start()], offsets[first.end() - 1] + 1,
            canonical, len(matches),
        ))


def collect_prose_violation_diagnostics(
    request: MovingServiceQuestionRequestV2,
    response: MovingServiceQuestionResponseV2,
) -> tuple[ProseViolationDiagnostic, ...]:
    diagnostics: list[ProseViolationDiagnostic] = []
    for suggestion in response.suggestions:
        if suggestion.selected_missing_information_category is not MissingInformationCategory.TEMPORARY_STORAGE_NEED:
            continue
        for field in PROSE_FIELDS:
            value = getattr(suggestion, field)
            for location_name, location in (
                ("origin_region", request.trusted_state.origin_region),
                ("destination_region", request.trusted_state.destination_region),
            ):
                phrase = " ".join(location.casefold().split())
                if phrase:
                    _add_matches(diagnostics, value=value, field=field,
                                 code="irrelevant_location_reference",
                                 pattern=rf"(?<!\w){re.escape(phrase)}(?!\w)",
                                 canonical=f"supplied_{location_name}")
            for phrase in HOME_OR_PROPERTY_PHRASES:
                _add_matches(diagnostics, value=value, field=field,
                             code="unsupported_home_or_property_assertion",
                             pattern=rf"(?<!\w){re.escape(phrase)}(?!\w)", canonical=phrase)

        for field in STORAGE_MODALITY_FIELDS:
            value = getattr(suggestion, field)
            normalized, _ = _normalize(value)
            if re.search(r"\bstorage\b", normalized):
                for trigger in STORAGE_MODALITY_TRIGGERS:
                    _add_matches(diagnostics, value=value, field=field,
                                 code="storage_modality_overstatement",
                                 pattern=rf"\b{re.escape(trigger)}\b", canonical=trigger)

        adjectives = "|".join(map(re.escape, SELECTION_ADJECTIVES))
        nouns = "|".join(SELECTION_NOUN_PATTERNS)
        pattern = rf"\b(?P<adjective>{adjectives})\s+(?P<noun>{nouns})\b"
        for field in PROSE_FIELDS:
            value = getattr(suggestion, field)
            normalized, offsets = _normalize(value)
            grouped: dict[str, list[re.Match[str]]] = {}
            for match in re.finditer(pattern, normalized):
                canonical = f"{match.group('adjective')} {match.group('noun').replace('-', ' ')}"
                grouped.setdefault(canonical, []).append(match)
            for canonical, matches in grouped.items():
                first = matches[0]
                diagnostics.append(ProseViolationDiagnostic(
                    "unsupported_service_selection_language", RULE_ID, field,
                    offsets[first.start()], offsets[first.end() - 1] + 1,
                    canonical, len(matches),
                ))

        if suggestion.relevant_knowledge_ids != (STORAGE_KNOWLEDGE.knowledge_id,):
            diagnostics.append(ProseViolationDiagnostic(
                "grounding_summary_mismatch", RULE_ID, "relevant_knowledge_ids",
                0, 0, "knowledge_id_mismatch",
            ))
        if suggestion.grounding_summary != STORAGE_KNOWLEDGE.statement:
            diagnostics.append(ProseViolationDiagnostic(
                "grounding_summary_mismatch", RULE_ID, "grounding_summary",
                0, 0, "exact_grounding_summary_mismatch",
            ))

    order = {code: index for index, code in enumerate(PROSE_VIOLATION_CODE_ORDER)}
    result = tuple(sorted(diagnostics, key=lambda item: (
        order[item.violation_code], item.field, item.start_offset, item.canonical_trigger,
    )))
    diagnostic_codes = tuple(code for code in PROSE_VIOLATION_CODE_ORDER
                             if any(item.violation_code == code for item in result))
    validator_codes = collect_prose_violation_codes(request, response)
    if diagnostic_codes != validator_codes:
        raise RuntimeError("bounded prose diagnostics drifted from validator behavior")
    return result
