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
    WorkArrangement.FLEXIBLE: (
        "Accepting several work arrangements keeps more candidate regions viable, but "
        "each region still needs suitable employment opportunities.",
        "Suitable employment across acceptable arrangements",
    ),
}

COMMUTING_ARRANGEMENT_LABELS = {
    WorkArrangement.HYBRID: "hybrid",
    WorkArrangement.ON_SITE: "on-site",
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

    if goal.acceptable_work_arrangement in COMMUTING_ARRANGEMENT_LABELS:
        arrangement_label = COMMUTING_ARRANGEMENT_LABELS[
            goal.acceptable_work_arrangement
        ]
        if goal.acceptable_commute_minutes is None:
            return Recommendation(
                what=(
                    "Define the longest workable one-way commute before evaluating "
                    "candidate locations."
                ),
                why=(
                    f"{arrangement_label.capitalize()} work makes commute viability "
                    "relevant to the location decision.",
                    "A user-defined maximum is needed before candidate locations can "
                    "eventually be evaluated against this requirement.",
                    "A likely workplace location and credible travel-time evidence "
                    "will still be needed.",
                    "The suitable-employment assumption remains unconfirmed.",
                ),
                why_now=(
                    "The acceptable work arrangement is known, but the longest workable "
                    "one-way commute is still unclear. Defining that boundary provides "
                    "the next concrete requirement without prematurely choosing a "
                    "location."
                ),
                related_decision_id=target_location.id,
                relevant_dependencies=(
                    "Maximum acceptable one-way commute",
                    "Likely workplace location",
                    "Credible travel-time evidence",
                    "Suitable employment availability",
                ),
                blocked_downstream_work=target_location.downstream_work,
                related_assumptions=(employment,),
            )

        commute_minutes = goal.acceptable_commute_minutes
        if goal.likely_workplace_area is not None:
            workplace_area = goal.likely_workplace_area
            arrangement_uncertainties = (
                (
                    "Hybrid work frequency remains unresolved and may affect which "
                    "travel-time evidence is representative.",
                )
                if goal.acceptable_work_arrangement is WorkArrangement.HYBRID
                else ()
            )
            return Recommendation(
                what=(
                    "Gather credible one-way travel-time evidence between candidate "
                    f"locations and the likely {workplace_area} workplace area."
                ),
                why=(
                    (
                        f"{workplace_area} is a user-provided likely workplace area, "
                        "not a confirmed employer location or verified workplace."
                    ),
                    (
                        f"The maximum {commute_minutes}-minute one-way commute is the "
                        "user's hard evaluation boundary."
                    ),
                    "No route or travel time has been calculated.",
                    "Typical traffic conditions and travel mode remain unresolved.",
                    *arrangement_uncertainties,
                    "No candidate location currently passes or fails this requirement.",
                    "The suitable-employment assumption remains unconfirmed.",
                ),
                why_now=(
                    "The likely workplace area and acceptable commute boundary are now "
                    "known, so the next honest step is to gather credible travel-time "
                    "evidence before evaluating candidate locations."
                ),
                related_decision_id=target_location.id,
                relevant_dependencies=(
                    "Credible travel-time evidence",
                    "Typical traffic conditions",
                    "Travel mode",
                    "Hybrid work frequency"
                    if goal.acceptable_work_arrangement is WorkArrangement.HYBRID
                    else "Suitable employment availability",
                ),
                blocked_downstream_work=target_location.downstream_work,
                related_assumptions=(employment,),
            )

        frequency_reason = (
            "Hybrid work frequency remains unknown and may affect how the commute "
            "boundary is applied."
            if goal.acceptable_work_arrangement is WorkArrangement.HYBRID
            else (
                "The likely on-site workplace location remains unknown, so the commute "
                "boundary cannot yet be tested."
            )
        )
        return Recommendation(
            what=(
                f"Evaluate candidate locations against the {arrangement_label}-work "
                f"requirement and a maximum {commute_minutes}-minute one-way commute."
            ),
            why=(
                (
                    f"A one-way commute longer than {commute_minutes} minutes would "
                    "not be acceptable to the user."
                ),
                "A likely workplace location is still needed before any candidate can "
                "be evaluated.",
                "Credible travel-time evidence is still needed; the submitted limit is "
                "a user-provided boundary, not an observed commute time.",
                frequency_reason,
                "No candidate location currently passes or fails this requirement.",
                "The suitable-employment assumption remains unconfirmed.",
            ),
            why_now=(
                "The work arrangement and maximum acceptable one-way commute are now "
                "known, so candidate-location research can use both requirements while "
                "waiting for workplace and travel-time evidence."
            ),
            related_decision_id=target_location.id,
            relevant_dependencies=(
                "Likely workplace location",
                "Credible travel-time evidence",
                "Hybrid work frequency"
                if goal.acceptable_work_arrangement is WorkArrangement.HYBRID
                else "Suitable on-site employment location",
                "Suitable employment availability",
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
