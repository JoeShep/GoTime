from app.models import (
    AssumptionStatus,
    DecisionReadiness,
    EmploymentRequirementsStatus,
    Goal,
    Recommendation,
)
from app.scenarios import (
    SPOUSE_EMPLOYMENT_ASSUMPTION_ID,
    TARGET_LOCATION_DECISION_ID,
)


class UnsupportedReasoningStateError(ValueError):
    """Raised when the relocation proof has no rule for a recognized state."""


def recommend_next_step(goal: Goal) -> Recommendation:
    """Apply the MVP's explicit relocation-specific reasoning paths."""
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
        raise UnsupportedReasoningStateError(
            "The relocation reasoning rule does not apply to this goal."
        )

    if (
        goal.relocation_employment_requirements_status
        is EmploymentRequirementsStatus.UNCLEAR
    ):
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

    if (
        goal.relocation_employment_requirements_status
        is EmploymentRequirementsStatus.CLARIFIED
    ):
        return Recommendation(
            what="Evaluate candidate locations against the clarified employment requirements.",
            why=(
                "Clarified employment requirements provide criteria for comparing locations.",
                "Candidate evaluation can test where suitable employment may exist.",
                "The suitable-employment assumption remains unconfirmed.",
                "The target-location decision is still only partially ready.",
            ),
            why_now=(
                "The requirements are now known, so candidate regions can be evaluated "
                "without prematurely choosing a final location."
            ),
            related_decision_id=target_location.id,
            relevant_dependencies=(
                "Housing affordability",
                "Commute viability",
                "Healthcare access",
                "Suitable employment availability",
            ),
            blocked_downstream_work=target_location.downstream_work,
            related_assumptions=(employment,),
        )

    raise UnsupportedReasoningStateError(
        "The relocation reasoning rule does not support this state."
    )
