from app.models import (
    AssumptionStatus,
    DecisionReadiness,
    Goal,
    Recommendation,
)
from app.scenarios import (
    SPOUSE_EMPLOYMENT_ASSUMPTION_ID,
    TARGET_LOCATION_DECISION_ID,
)


def recommend_next_step(goal: Goal) -> Recommendation:
    """Apply the MVP's single relocation-specific reasoning rule."""
    target_location = next(
        (decision for decision in goal.decisions if decision.id == TARGET_LOCATION_DECISION_ID),
        None,
    )
    employment = next(
        (
            assumption
            for assumption in goal.assumptions
            if assumption.id == SPOUSE_EMPLOYMENT_ASSUMPTION_ID
        ),
        None,
    )

    if (
        target_location is None
        or employment is None
        or target_location.readiness is not DecisionReadiness.PARTIALLY_READY
        or employment.status is not AssumptionStatus.UNCONFIRMED
    ):
        raise ValueError("The relocation reasoning rule does not apply to this goal.")

    return Recommendation(
        what=(
            "Clarify spouse employment requirements before choosing a final "
            "target location."
        ),
        why=(
            "Employment requirements affect which locations are viable.",
            "Employment income affects housing affordability.",
            "The target-location decision is only partially ready.",
            "Several downstream decisions and actions depend on resolving this uncertainty.",
        ),
        why_now=(
            "Employment requirements are the highest-leverage unresolved input that "
            "can be clarified now; defining them makes it possible to evaluate the "
            "separate assumption that suitable employment exists and avoids rework "
            "downstream."
        ),
        related_decision_id=target_location.id,
        relevant_dependencies=(
            "Employment location or remote-work requirements",
            "Expected employment income",
            "Commute expectations",
            "Acceptable work arrangement",
        ),
        blocked_downstream_work=target_location.downstream_work,
        related_assumptions=(employment,),
    )
