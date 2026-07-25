import pytest

from app.models import WorkArrangement
from app.reasoning import recommend_next_step
from app.scenarios import (
    build_relocation_scenario,
    build_work_arrangement_scenario,
)


def test_recommends_clarifying_spouse_employment_requirements() -> None:
    recommendation = recommend_next_step(build_relocation_scenario())

    assert recommendation.what == (
        "Clarify spouse employment requirements before choosing a final target location."
    )
    assert recommendation.why == (
        "Employment requirements affect which locations are viable.",
        "Employment income affects housing affordability.",
        "The target-location decision is only partially ready.",
        "Several downstream decisions and actions depend on resolving this uncertainty.",
    )
    assert "highest-leverage unresolved input" in recommendation.why_now
    assert "separate assumption that suitable employment exists" in recommendation.why_now


def test_recommendation_exposes_dependencies_blocked_work_and_assumption() -> None:
    recommendation = recommend_next_step(build_relocation_scenario())

    assert recommendation.relevant_dependencies == (
        "Employment location or remote-work requirements",
        "Expected employment income",
        "Commute expectations",
        "Acceptable work arrangement",
    )
    assert recommendation.blocked_downstream_work == (
        "Housing affordability analysis",
        "Commute viability analysis",
        "Healthcare access research",
        "Neighborhood research",
        "Move sequencing",
    )
    assert len(recommendation.related_assumptions) == 1
    assert recommendation.related_decision_id == "target-location"
    assert recommendation.related_assumptions[0].id == "spouse-employment"
    assert recommendation.related_assumptions[0].status == "unconfirmed"
    assert recommendation.related_assumptions[0].description == (
        "Suitable employment for the spouse exists within one or more viable "
        "Northern California candidate regions."
    )


@pytest.mark.parametrize(
    ("work_arrangement", "expected_reason", "expected_dependency"),
    (
        (
            WorkArrangement.REMOTE,
            "do not need to support a routine workplace commute",
            "Reliable remote-work feasibility",
        ),
        (
            WorkArrangement.HYBRID,
            "support a viable recurring commute",
            "Recurring commute viability",
        ),
        (
            WorkArrangement.ON_SITE,
            "local employment availability and daily commute viability",
            "Local employment and daily commute viability",
        ),
        (
            WorkArrangement.FLEXIBLE,
            "keeps more candidate regions viable",
            "Suitable employment across acceptable arrangements",
        ),
    ),
)
def test_work_arrangement_produces_meaningful_clarified_reasoning(
    work_arrangement: WorkArrangement,
    expected_reason: str,
    expected_dependency: str,
) -> None:
    original_goal = build_relocation_scenario()
    clarified_goal = build_work_arrangement_scenario(original_goal, work_arrangement)

    original = recommend_next_step(original_goal)
    clarified = recommend_next_step(clarified_goal)

    assert clarified.what == (
        "Evaluate candidate locations against the clarified employment requirements."
    )
    assert clarified != original
    assert clarified.related_decision_id == "target-location"
    assert clarified.related_assumptions[0].status == "unconfirmed"
    assert "The suitable-employment assumption remains unconfirmed." in clarified.why
    assert expected_reason in clarified.why[0]
    assert expected_dependency in clarified.relevant_dependencies


def test_work_arrangement_snapshot_does_not_mutate_original_goal() -> None:
    original = build_relocation_scenario()

    clarified = build_work_arrangement_scenario(original, WorkArrangement.HYBRID)

    assert original.acceptable_work_arrangement is None
    assert clarified.acceptable_work_arrangement is WorkArrangement.HYBRID
    assert "remain unclear" in original.current_state
    assert "acceptable hybrid work arrangement" in clarified.current_state
    assert original.assumptions[0].status == clarified.assumptions[0].status == "unconfirmed"


def test_non_applicable_goal_fails_predictably() -> None:
    goal = build_relocation_scenario().model_copy(update={"decisions": ()})

    with pytest.raises(ValueError, match="does not apply to this goal"):
        recommend_next_step(goal)
