import pytest

from app.models import CommuteTravelMode, WorkArrangement
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


@pytest.mark.parametrize(
    ("work_arrangement", "arrangement_text"),
    (
        (WorkArrangement.HYBRID, "Hybrid work"),
        (WorkArrangement.ON_SITE, "On-site work"),
    ),
)
def test_commuting_arrangement_without_limit_recommends_defining_boundary(
    work_arrangement: WorkArrangement, arrangement_text: str
) -> None:
    goal = build_work_arrangement_scenario(
        build_relocation_scenario(), work_arrangement
    )

    recommendation = recommend_next_step(goal)

    assert recommendation.what == (
        "Define the longest workable one-way commute before evaluating "
        "candidate locations."
    )
    assert arrangement_text in recommendation.why[0]
    assert "Maximum acceptable one-way commute" in recommendation.relevant_dependencies
    assert recommendation.related_assumptions[0].status == "unconfirmed"


@pytest.mark.parametrize(
    "work_arrangement",
    (
        WorkArrangement.HYBRID,
        WorkArrangement.ON_SITE,
    ),
)
def test_commute_limit_requests_likely_workplace_area(
    work_arrangement: WorkArrangement,
) -> None:
    goal = build_work_arrangement_scenario(
        build_relocation_scenario(), work_arrangement, 45
    )

    recommendation = recommend_next_step(goal)

    assert recommendation.what == (
        "Gather a likely workplace area before collecting commute evidence."
    )
    assert "longer than 45 minutes would not be acceptable" in recommendation.why[0]
    assert "likely workplace area is needed" in recommendation.why[1]
    assert "No route or travel time has been calculated." in recommendation.why
    assert "No candidate location currently passes or fails" in recommendation.why[-2]
    assert "suitable-employment assumption remains unconfirmed" in recommendation.why[-1]
    assert recommendation.related_assumptions[0].status == "unconfirmed"


@pytest.mark.parametrize(
    "work_arrangement",
    (
        WorkArrangement.HYBRID,
        WorkArrangement.ON_SITE,
    ),
)
def test_likely_workplace_area_requests_travel_mode(
    work_arrangement: WorkArrangement,
) -> None:
    goal = build_work_arrangement_scenario(
        build_relocation_scenario(),
        work_arrangement,
        45,
        "  San Jose or the surrounding area  ",
    )

    recommendation = recommend_next_step(goal)

    assert goal.likely_workplace_area == "San Jose or the surrounding area"
    assert recommendation.what == (
        "Clarify the most likely commute travel mode before gathering "
        "travel-time evidence."
    )
    assert "user-provided likely workplace area" in recommendation.why[0]
    assert "not a confirmed employer location or verified workplace" in (
        recommendation.why[0]
    )
    assert "maximum 45-minute one-way commute" in recommendation.why[1]
    assert "different credible evidence" in recommendation.why[2]
    assert "No route or travel time has been calculated." in recommendation.why
    assert "No candidate location currently passes or fails" in recommendation.why[-2]
    assert "suitable-employment assumption remains unconfirmed" in (
        recommendation.why[-1]
    )
    assert recommendation.related_assumptions[0].status == "unconfirmed"


@pytest.mark.parametrize(
    ("travel_mode", "evidence_text", "mode_reason"),
    (
        (
            CommuteTravelMode.DRIVE,
            "one-way driving-time evidence",
            "traffic conditions remain unresolved",
        ),
        (
            CommuteTravelMode.PUBLIC_TRANSIT,
            "one-way public-transit travel-time evidence",
            "schedules, transfers, and station access remain unresolved",
        ),
        (
            CommuteTravelMode.EITHER,
            "one-way driving and public-transit evidence",
            "Both modes are acceptable",
        ),
    ),
)
@pytest.mark.parametrize(
    "work_arrangement",
    (WorkArrangement.HYBRID, WorkArrangement.ON_SITE),
)
def test_travel_mode_guides_mode_specific_evidence_gathering(
    work_arrangement: WorkArrangement,
    travel_mode: CommuteTravelMode,
    evidence_text: str,
    mode_reason: str,
) -> None:
    goal = build_work_arrangement_scenario(
        build_relocation_scenario(),
        work_arrangement,
        45,
        "San Jose",
        travel_mode,
    )

    recommendation = recommend_next_step(goal)

    assert evidence_text in recommendation.what
    assert "likely San Jose workplace area" in recommendation.what
    assert "not a confirmed employer location or verified workplace" in (
        recommendation.why[0]
    )
    assert "hard evaluation boundary" in recommendation.why[1]
    assert "user-provided planning context, not observed travel behavior" in (
        recommendation.why[2]
    )
    assert recommendation.why[3] == "No route or travel time has been calculated."
    assert mode_reason in recommendation.why[4]
    if work_arrangement is WorkArrangement.HYBRID:
        assert any(
            "Hybrid work frequency remains unresolved" in reason
            for reason in recommendation.why
        )
    else:
        assert not any("Hybrid work frequency" in reason for reason in recommendation.why)
    assert "No candidate location currently passes or fails" in recommendation.why[-2]
    assert "suitable-employment assumption remains unconfirmed" in (
        recommendation.why[-1]
    )
    assert recommendation.related_assumptions[0].status == "unconfirmed"


def test_work_arrangement_snapshot_does_not_mutate_original_goal() -> None:
    original = build_relocation_scenario()

    clarified = build_work_arrangement_scenario(original, WorkArrangement.HYBRID, 45)

    assert original.acceptable_work_arrangement is None
    assert original.acceptable_commute_minutes is None
    assert original.likely_workplace_area is None
    assert original.intended_commute_travel_mode is None
    assert clarified.acceptable_work_arrangement is WorkArrangement.HYBRID
    assert clarified.acceptable_commute_minutes == 45
    assert clarified.likely_workplace_area is None
    assert clarified.intended_commute_travel_mode is None
    assert "remain unclear" in original.current_state
    assert "acceptable hybrid work arrangement" in clarified.current_state
    assert "maximum acceptable one-way commute is 45 minutes" in clarified.current_state
    assert original.assumptions[0].status == clarified.assumptions[0].status == "unconfirmed"


def test_non_applicable_goal_fails_predictably() -> None:
    goal = build_relocation_scenario().model_copy(update={"decisions": ()})

    with pytest.raises(ValueError, match="does not apply to this goal"):
        recommend_next_step(goal)
