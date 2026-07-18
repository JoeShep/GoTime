from app.reasoning import recommend_next_step
from app.scenarios import build_relocation_scenario


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
