from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


LIKELY_WORKPLACE_AREA_MAX_LENGTH = 120


class DomainModel(BaseModel):
    model_config = ConfigDict(frozen=True)


class DecisionReadiness(StrEnum):
    PARTIALLY_READY = "partially_ready"


class AssumptionStatus(StrEnum):
    UNCONFIRMED = "unconfirmed"


class WorkArrangement(StrEnum):
    """Acceptable spouse work arrangements for the relocation proof."""

    REMOTE = "remote"
    HYBRID = "hybrid"
    ON_SITE = "on_site"
    FLEXIBLE = "flexible"


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
    acceptable_work_arrangement: WorkArrangement | None = None
    acceptable_commute_minutes: int | None = Field(default=None, gt=0)
    likely_workplace_area: str | None = Field(
        default=None, max_length=LIKELY_WORKPLACE_AREA_MAX_LENGTH
    )
    success_criteria: tuple[SuccessCriterion, ...]
    constraints: tuple[Constraint, ...]
    preferences: tuple[Preference, ...]
    decisions: tuple[Decision, ...]
    assumptions: tuple[Assumption, ...]

    @field_validator("likely_workplace_area")
    @classmethod
    def validate_likely_workplace_area(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped_value = value.strip()
        if not stripped_value:
            raise ValueError("Likely workplace area must not be blank.")
        return stripped_value

    @model_validator(mode="after")
    def validate_commute_requirement(self) -> "Goal":
        if (
            self.acceptable_commute_minutes is not None
            and self.acceptable_work_arrangement
            not in (WorkArrangement.HYBRID, WorkArrangement.ON_SITE)
        ):
            raise ValueError(
                "An acceptable commute limit requires a hybrid or on-site "
                "work arrangement."
            )
        if self.likely_workplace_area is not None and (
            self.acceptable_work_arrangement
            not in (WorkArrangement.HYBRID, WorkArrangement.ON_SITE)
            or self.acceptable_commute_minutes is None
        ):
            raise ValueError(
                "A likely workplace area requires a hybrid or on-site work "
                "arrangement and an acceptable commute limit."
            )
        return self


class Recommendation(DomainModel):
    what: str
    why: tuple[str, ...]
    why_now: str
    related_decision_id: str | None = None
    relevant_dependencies: tuple[str, ...]
    blocked_downstream_work: tuple[str, ...]
    related_assumptions: tuple[Assumption, ...]
