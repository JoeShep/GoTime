from app.models import (
    AssumptionStatus,
    CommuteTravelMode,
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
            if goal.intended_commute_travel_mode is None:
                return Recommendation(
                    what=(
                        "Clarify the most likely commute travel mode before gathering "
                        "travel-time evidence."
                    ),
                    why=(
                        (
                            f"{workplace_area} is a user-provided likely workplace area, "
                            "not a confirmed employer location or verified workplace."
                        ),
                        (
                            f"The maximum {commute_minutes}-minute one-way commute is "
                            "the user's hard evaluation boundary."
                        ),
                        "Driving and public transit require different credible evidence.",
                        "No route or travel time has been calculated.",
                        "No candidate location currently passes or fails this requirement.",
                        "The suitable-employment assumption remains unconfirmed.",
                    ),
                    why_now=(
                        "The likely workplace area and commute boundary are known, but "
                        "the intended travel mode is still needed to define what evidence "
                        "to gather."
                    ),
                    related_decision_id=target_location.id,
                    relevant_dependencies=(
                        "Intended commute travel mode",
                        "Credible travel-time evidence",
                        "Hybrid work frequency"
                        if goal.acceptable_work_arrangement is WorkArrangement.HYBRID
                        else "Suitable employment availability",
                    ),
                    blocked_downstream_work=target_location.downstream_work,
                    related_assumptions=(employment,),
                )

            travel_mode = goal.intended_commute_travel_mode
            if travel_mode is CommuteTravelMode.DRIVE:
                evidence_description = "one-way driving-time evidence"
                travel_mode_description = "driving"
                mode_reason = (
                    "Typical traffic conditions remain unresolved, so credible "
                    "driving evidence must account for them."
                )
                mode_dependencies = ("Typical traffic conditions",)
            elif travel_mode is CommuteTravelMode.PUBLIC_TRANSIT:
                evidence_description = "one-way public-transit travel-time evidence"
                travel_mode_description = "public transit"
                mode_reason = (
                    "Transit schedules, transfers, and station access remain "
                    "unresolved, so credible public-transit evidence must account "
                    "for them."
                )
                mode_dependencies = (
                    "Transit schedules",
                    "Transfers and station access",
                )
            else:
                evidence_description = (
                    "one-way driving and public-transit evidence"
                )
                travel_mode_description = "driving or public transit"
                mode_reason = (
                    "Both modes are acceptable, so credible evidence must cover "
                    "typical driving traffic as well as transit schedules, transfers, "
                    "and station access; those conditions remain unresolved."
                )
                mode_dependencies = (
                    "Typical traffic conditions",
                    "Transit schedules",
                    "Transfers and station access",
                )

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
                    f"Gather credible {evidence_description} between candidate "
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
                    (
                        f"The intended travel mode ({travel_mode_description}) "
                        "is user-provided planning context, not observed travel behavior."
                    ),
                    "No route or travel time has been calculated.",
                    mode_reason,
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
                    *mode_dependencies,
                    "Hybrid work frequency"
                    if goal.acceptable_work_arrangement is WorkArrangement.HYBRID
                    else "Suitable employment availability",
                ),
                blocked_downstream_work=target_location.downstream_work,
                related_assumptions=(employment,),
            )

        return Recommendation(
            what="Gather a likely workplace area before collecting commute evidence.",
            why=(
                (
                    f"A one-way commute longer than {commute_minutes} minutes would "
                    "not be acceptable to the user."
                ),
                "A likely workplace area is needed to orient later travel-time research.",
                "The workplace and suitable employment remain unconfirmed.",
                "No route or travel time has been calculated.",
                "No candidate location currently passes or fails this requirement.",
                "The suitable-employment assumption remains unconfirmed.",
            ),
            why_now=(
                "The work arrangement and commute boundary are known, so the next "
                "missing planning input is the likely workplace area."
            ),
            related_decision_id=target_location.id,
            relevant_dependencies=(
                "Likely workplace area",
                "Intended commute travel mode",
                "Credible travel-time evidence",
                "Hybrid work frequency"
                if goal.acceptable_work_arrangement is WorkArrangement.HYBRID
                else "Suitable employment availability",
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
