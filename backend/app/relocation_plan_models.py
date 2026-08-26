from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class PlanModel(BaseModel):
    model_config = ConfigDict(frozen=True)


class TaskStatus(StrEnum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class TaskCategory(StrEnum):
    EMPLOYMENT = "employment"
    FAMILY = "family"
    FINANCIAL = "financial"
    HEALTHCARE = "healthcare"
    HOUSING = "housing"
    LOGISTICS = "logistics"


CATEGORY_ORDER = tuple(TaskCategory)


class TaskPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MilestoneStatus(StrEnum):
    PENDING = "pending"
    ACHIEVED = "achieved"


class DecisionStatus(StrEnum):
    UNRESOLVED = "unresolved"
    RESOLVED = "resolved"


def _trimmed(value: str, field_name: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError(f"{field_name} must not be blank.")
    return stripped


def _validate_milestone_target_window(
    earliest: date | None, latest: date | None
) -> None:
    if latest is not None and earliest is None:
        raise ValueError("Milestone latest target date requires an earliest date.")
    if earliest is not None and latest is not None and latest < earliest:
        raise ValueError(
            "Milestone latest target date cannot precede its earliest date."
        )


class Phase(PlanModel):
    id: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=120)
    position: int = Field(ge=0)


class TaskFields(PlanModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2_000)
    phase_id: str = Field(min_length=1, max_length=64)
    categories: tuple[TaskCategory, ...]
    status: TaskStatus = TaskStatus.NOT_STARTED
    assignees: tuple[str, ...] = Field(default=(), max_length=10)
    start_date: date | None = None
    due_date: date | None = None
    priority: TaskPriority = TaskPriority.MEDIUM
    dependency_task_ids: tuple[str, ...] = Field(default=(), max_length=50)
    parent_task_id: str | None = Field(default=None, min_length=1, max_length=64)
    subtask_position: int | None = Field(default=None, ge=0)

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        return _trimmed(value, "Task title")

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @field_validator("assignees")
    @classmethod
    def validate_assignees(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(_trimmed(value, "Assignee name") for value in values)
        if len(set(normalized)) != len(normalized):
            raise ValueError("Assignee names must be unique.")
        return normalized

    @field_validator("dependency_task_ids")
    @classmethod
    def validate_dependencies(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if len(set(values)) != len(values):
            raise ValueError("Dependency task IDs must be unique.")
        return values

    @field_validator("categories")
    @classmethod
    def validate_categories(
        cls, values: tuple[TaskCategory, ...]
    ) -> tuple[TaskCategory, ...]:
        if len(set(values)) != len(values):
            raise ValueError("Task categories must be unique.")
        selected = set(values)
        return tuple(category for category in CATEGORY_ORDER if category in selected)

    @model_validator(mode="after")
    def validate_timing(self) -> "TaskFields":
        if (
            self.start_date is not None
            and self.due_date is not None
            and self.due_date < self.start_date
        ):
            raise ValueError("Task due date cannot be before its start date.")
        return self


class TaskCreate(TaskFields):
    id: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9][a-z0-9-]*$")

    @model_validator(mode="after")
    def reject_self_dependency(self) -> "TaskCreate":
        if self.id in self.dependency_task_ids:
            raise ValueError("A task cannot depend on itself.")
        return self


class TaskUpdate(PlanModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(max_length=2_000)
    phase_id: str = Field(min_length=1, max_length=64)
    categories: tuple[TaskCategory, ...]
    status: TaskStatus
    assignees: tuple[str, ...] = Field(max_length=10)
    start_date: date | None
    due_date: date | None
    priority: TaskPriority
    dependency_task_ids: tuple[str, ...] = Field(max_length=50)
    parent_task_id: str | None = Field(default=None, min_length=1, max_length=64)
    subtask_position: int | None = Field(default=None, ge=0)
    confirm_parent_phase_move: bool = False

    _validate_title = field_validator("title")(TaskFields.validate_title.__func__)
    _validate_description = field_validator("description")(
        TaskFields.validate_description.__func__
    )
    _validate_assignees = field_validator("assignees")(
        TaskFields.validate_assignees.__func__
    )
    _validate_dependencies = field_validator("dependency_task_ids")(
        TaskFields.validate_dependencies.__func__
    )
    _validate_categories = field_validator("categories")(
        TaskFields.validate_categories.__func__
    )

    @model_validator(mode="after")
    def validate_timing(self) -> "TaskUpdate":
        if (
            self.start_date is not None
            and self.due_date is not None
            and self.due_date < self.start_date
        ):
            raise ValueError("Task due date cannot be before its start date.")
        return self


class TaskStatusUpdate(PlanModel):
    status: TaskStatus
    confirm_manual_override: bool = False


class SubtaskOrderUpdate(PlanModel):
    child_task_ids: tuple[str, ...]

    @field_validator("child_task_ids")
    @classmethod
    def reject_duplicate_child_ids(cls, child_task_ids: tuple[str, ...]) -> tuple[str, ...]:
        if len(set(child_task_ids)) != len(child_task_ids):
            raise ValueError("Subtask order cannot contain duplicate Task IDs.")
        return child_task_ids


class Task(TaskFields):
    id: str
    blocked: bool
    stored_status: TaskStatus | None = None
    automatic_status: TaskStatus | None = None
    manual_status_override: TaskStatus | None = None
    is_parent: bool = False
    subtask_count: int = 0
    completed_subtask_count: int = 0


class MilestoneFields(PlanModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2_000)
    target_earliest_date: date | None = None
    target_latest_date: date | None = None

    _validate_title = field_validator("title")(TaskFields.validate_title.__func__)
    _validate_description = field_validator("description")(
        TaskFields.validate_description.__func__
    )

    @model_validator(mode="after")
    def validate_target_window(self) -> "MilestoneFields":
        _validate_milestone_target_window(
            self.target_earliest_date, self.target_latest_date
        )
        return self


class MilestoneCreate(MilestoneFields):
    id: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9][a-z0-9-]*$")


class MilestoneUpdate(PlanModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(max_length=2_000)
    target_earliest_date: date | None
    target_latest_date: date | None

    _validate_title = field_validator("title")(TaskFields.validate_title.__func__)
    _validate_description = field_validator("description")(
        TaskFields.validate_description.__func__
    )

    @model_validator(mode="after")
    def validate_target_window(self) -> "MilestoneUpdate":
        _validate_milestone_target_window(
            self.target_earliest_date, self.target_latest_date
        )
        return self


class MilestoneAchievementUpdate(PlanModel):
    achieved: bool


class Milestone(MilestoneFields):
    id: str
    status: MilestoneStatus
    achieved_at: datetime | None


class DecisionOptionFields(PlanModel):
    id: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9][a-z0-9-]*$")
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2_000)

    _validate_title = field_validator("title")(TaskFields.validate_title.__func__)
    _validate_description = field_validator("description")(
        TaskFields.validate_description.__func__
    )


class DecisionFields(PlanModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2_000)
    milestone_id: str = Field(min_length=1, max_length=64)
    options: tuple[DecisionOptionFields, ...] = Field(min_length=2, max_length=20)

    _validate_title = field_validator("title")(TaskFields.validate_title.__func__)
    _validate_description = field_validator("description")(
        TaskFields.validate_description.__func__
    )

    @field_validator("options")
    @classmethod
    def validate_options(
        cls, values: tuple[DecisionOptionFields, ...]
    ) -> tuple[DecisionOptionFields, ...]:
        ids = [value.id for value in values]
        titles = [value.title.casefold() for value in values]
        if len(set(ids)) != len(ids):
            raise ValueError("Decision option IDs must be unique.")
        if len(set(titles)) != len(titles):
            raise ValueError("Decision option titles must be unique.")
        return values


class DecisionCreate(DecisionFields):
    id: str = Field(min_length=1, max_length=64, pattern=r"^[a-z0-9][a-z0-9-]*$")


class DecisionUpdate(PlanModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(max_length=2_000)
    milestone_id: str = Field(min_length=1, max_length=64)
    options: tuple[DecisionOptionFields, ...] = Field(min_length=2, max_length=20)

    _validate_title = field_validator("title")(TaskFields.validate_title.__func__)
    _validate_description = field_validator("description")(
        TaskFields.validate_description.__func__
    )
    _validate_options = field_validator("options")(
        DecisionFields.validate_options.__func__
    )


class DecisionSelectionUpdate(PlanModel):
    selected_option_id: str | None


class Decision(DecisionFields):
    id: str
    status: DecisionStatus
    selected_option_id: str | None


class RelocationPlan(PlanModel):
    id: str
    title: str
    phases: tuple[Phase, ...]
    tasks: tuple[Task, ...]
    milestones: tuple[Milestone, ...] = ()
    decisions: tuple[Decision, ...] = ()
