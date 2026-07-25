from app.models import (
    AssumptionStatus,
    DecisionReadiness,
    Goal,
    Recommendation,
    WorkArrangement,
)
from app.scenarios import (
    SPOUSE_EMPLOYMENT_ASSUMPTION_ID,
    TARGET_LOCATION_DECISION_ID,
)


class UnsupportedReasoningStateError(ValueError):
    """Raised when the relocation proof has no rule for a recognized state."""


WORK_ARRANGEMENT_REASONING = {
    WorkArrangement.REMOTE: (
        "Remote work broadens the location search because candidate regions do not "
        "need to support a routine workplace commute.",
        "Reliable remote-work feasibility",
    ),
    WorkArrangement.HYBRID: (
        "Hybrid work requires candidate locations to support a viable recurring "
        "commute to likely employment centers.",
        "Recurring commute viability",
    ),
    WorkArrangement.ON_SITE: (
        "On-site work makes local employment availability and daily commute viability "
        "central to comparing candidate locations.",
        "Local employment and daily commute viability",
    ),
    WorkArrangement.FLEXIBLE: (
        "Accepting several work arrangements keeps more candidate regions viable, but "
        "each region still needs suitable employment opportunities.",
        "Suitable employment across acceptable arrangements",
    ),
}


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

    if goal.acceptable_work_arrangement is None:
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

    if goal.acceptable_work_arrangement is not None:
        arrangement_reason, arrangement_dependency = WORK_ARRANGEMENT_REASONING[
            goal.acceptable_work_arrangement
        ]
        return Recommendation(
            what="Evaluate candidate locations against the clarified employment requirements.",
            why=(
                arrangement_reason,
                "Candidate evaluation can test where suitable employment may exist.",
                "The suitable-employment assumption remains unconfirmed.",
                "The target-location decision is still only partially ready.",
            ),
            why_now=(
                "The acceptable work arrangement is now known, so candidate regions can "
                "be evaluated against a real employment requirement without prematurely "
                "choosing a final location."
            ),
            related_decision_id=target_location.id,
            relevant_dependencies=(
                arrangement_dependency,
                "Housing affordability",
                "Healthcare access",
                "Suitable employment availability",
            ),
            blocked_downstream_work=target_location.downstream_work,
            related_assumptions=(employment,),
        )
