from app.models import (
    Assumption,
    AssumptionStatus,
    CommuteTravelMode,
    Constraint,
    Decision,
    DecisionReadiness,
    Goal,
    Preference,
    SuccessCriterion,
    WorkArrangement,
)


TARGET_LOCATION_DECISION_ID = "target-location"
SPOUSE_EMPLOYMENT_ASSUMPTION_ID = "spouse-employment"


def build_relocation_scenario() -> Goal:
    return Goal(
        id="relocate-to-northern-california",
        title="Relocate from Tennessee to Northern California",
        current_state=(
            "The family lives in Tennessee. A target location in Northern "
            "California has not been selected, and the spouse's employment "
            "requirements remain unclear."
        ),
        acceptable_work_arrangement=None,
        acceptable_commute_minutes=None,
        likely_workplace_area=None,
        intended_commute_travel_mode=None,
        success_criteria=(
            SuccessCriterion(
                id="affordable-move",
                description="Complete the move with affordable housing.",
            ),
            SuccessCriterion(
                id="healthcare-access",
                description="Maintain access to suitable healthcare.",
            ),
        ),
        constraints=(
            Constraint(
                id="housing-affordability",
                description="Housing must remain affordable for the household.",
            ),
        ),
        preferences=(
            Preference(
                id="viable-commute",
                description="Prefer a location with a viable spouse commute.",
            ),
        ),
        decisions=(
            Decision(
                id=TARGET_LOCATION_DECISION_ID,
                title="Choose the final target location",
                readiness=DecisionReadiness.PARTIALLY_READY,
                required_information=(
                    "Spouse employment requirements",
                    "Housing affordability",
                    "Commute viability",
                    "Healthcare access",
                ),
                downstream_work=(
                    "Housing affordability analysis",
                    "Commute viability analysis",
                    "Healthcare access research",
                    "Neighborhood research",
                    "Move sequencing",
                ),
            ),
        ),
        assumptions=(
            Assumption(
                id=SPOUSE_EMPLOYMENT_ASSUMPTION_ID,
                description=(
                    "Suitable employment for the spouse exists within one or more "
                    "viable Northern California candidate regions."
                ),
                status=AssumptionStatus.UNCONFIRMED,
                related_decision_ids=(TARGET_LOCATION_DECISION_ID,),
                validation_method=(
                    "Evaluate regional employment opportunities through market research, "
                    "employer conversations, interviews, or job offers."
                ),
            ),
        ),
    )


def build_work_arrangement_scenario(
    goal: Goal,
    work_arrangement: WorkArrangement,
    acceptable_commute_minutes: int | None = None,
    likely_workplace_area: str | None = None,
    intended_commute_travel_mode: CommuteTravelMode | None = None,
) -> Goal:
    """Derive a relocation snapshot with one concrete employment requirement."""
    arrangement_label = work_arrangement.value.replace("_", "-")
    commute_state = (
        f" The maximum acceptable one-way commute is "
        f"{acceptable_commute_minutes} minutes."
        if acceptable_commute_minutes is not None
        else ""
    )
    workplace_state = (
        f" The likely workplace area is {likely_workplace_area.strip()}."
        if likely_workplace_area is not None
        else ""
    )
    travel_mode_state = (
        " The intended commute travel mode is "
        f"{intended_commute_travel_mode.value.replace('_', ' ')}."
        if intended_commute_travel_mode is not None
        else ""
    )
    return Goal.model_validate(
        {
            **goal.model_dump(),
            "current_state": (
                "The family lives in Tennessee. A target location in Northern "
                "California has not been selected, and the spouse's employment "
                f"requirements include an acceptable {arrangement_label} work "
                f"arrangement.{commute_state}{workplace_state}{travel_mode_state}"
            ),
            "acceptable_work_arrangement": work_arrangement,
            "acceptable_commute_minutes": acceptable_commute_minutes,
            "likely_workplace_area": likely_workplace_area,
            "intended_commute_travel_mode": intended_commute_travel_mode,
        }
    )
