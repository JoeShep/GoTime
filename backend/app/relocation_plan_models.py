from __future__ import annotations

from datetime import date
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


class TaskPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


def _trimmed(value: str, field_name: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError(f"{field_name} must not be blank.")
    return stripped


class Phase(PlanModel):
    id: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=120)
    position: int = Field(ge=0)


class TaskFields(PlanModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2_000)
    phase_id: str = Field(min_length=1, max_length=64)
    category: TaskCategory
    status: TaskStatus = TaskStatus.NOT_STARTED
    assignees: tuple[str, ...] = Field(default=(), max_length=10)
    start_date: date | None = None
    due_date: date | None = None
    priority: TaskPriority = TaskPriority.MEDIUM
    dependency_task_ids: tuple[str, ...] = Field(default=(), max_length=50)

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
    category: TaskCategory
    status: TaskStatus
    assignees: tuple[str, ...] = Field(max_length=10)
    start_date: date | None
    due_date: date | None
    priority: TaskPriority
    dependency_task_ids: tuple[str, ...] = Field(max_length=50)

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


class Task(TaskFields):
    id: str
    blocked: bool


class RelocationPlan(PlanModel):
    id: str
    title: str
    phases: tuple[Phase, ...]
    tasks: tuple[Task, ...]
