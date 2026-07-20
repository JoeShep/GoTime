from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class DomainModel(BaseModel):
    model_config = ConfigDict(frozen=True)


class DecisionReadiness(StrEnum):
    PARTIALLY_READY = "partially_ready"


class AssumptionStatus(StrEnum):
    UNCONFIRMED = "unconfirmed"


class EmploymentRequirementsStatus(StrEnum):
    """Relocation-specific scenario state for the current MVP proof."""

    UNCLEAR = "unclear"
    CLARIFIED = "clarified"


class SuccessCriterion(DomainModel):
    id: str
    description: str


class Constraint(DomainModel):
    id: str
    description: str


class Preference(DomainModel):
    id: str
    description: str


class Decision(DomainModel):
    id: str
    title: str
    readiness: DecisionReadiness
    required_information: tuple[str, ...]
    downstream_work: tuple[str, ...]


class Assumption(DomainModel):
    id: str
    description: str
    status: AssumptionStatus
    related_decision_ids: tuple[str, ...]
    validation_method: str


class Goal(DomainModel):
    id: str
    title: str
    current_state: str
    relocation_employment_requirements_status: EmploymentRequirementsStatus
    success_criteria: tuple[SuccessCriterion, ...]
    constraints: tuple[Constraint, ...]
    preferences: tuple[Preference, ...]
    decisions: tuple[Decision, ...]
    assumptions: tuple[Assumption, ...]


class Recommendation(DomainModel):
    what: str
    why: tuple[str, ...]
    why_now: str
    related_decision_id: str | None = None
    relevant_dependencies: tuple[str, ...]
    blocked_downstream_work: tuple[str, ...]
    related_assumptions: tuple[Assumption, ...]
