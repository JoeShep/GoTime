from app.models import (
    Assumption,
    AssumptionStatus,
    Constraint,
    Decision,
    DecisionReadiness,
    EmploymentRequirementsStatus,
    Goal,
    Preference,
    SuccessCriterion,
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
        relocation_employment_requirements_status=EmploymentRequirementsStatus.UNCLEAR,
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


def build_clarified_employment_requirements_scenario(goal: Goal) -> Goal:
    """Derive the second relocation snapshot without mutating the original."""
    return goal.model_copy(
        update={
            "current_state": (
                "The family lives in Tennessee. A target location in Northern "
                "California has not been selected, and the spouse's employment "
                "requirements have been clarified."
            ),
            "relocation_employment_requirements_status": (
                EmploymentRequirementsStatus.CLARIFIED
            ),
        }
    )
