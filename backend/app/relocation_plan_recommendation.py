from __future__ import annotations

from datetime import date
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from app.relocation_plan_models import (
    RelocationPlan,
    Task,
    TaskPriority,
    TaskStatus,
)


class RecommendationStatus(StrEnum):
    RECOMMENDED = "recommended"
    NO_ACTIONABLE_TASK = "no_actionable_task"


class RankingFactors(BaseModel):
    model_config = ConfigDict(frozen=True)

    due_state: str
    due_date: date | None
    priority: TaskPriority
    task_status: TaskStatus
    directly_unblocks_count: int
    phase_position: int


class RelocationTaskRecommendation(BaseModel):
    model_config = ConfigDict(frozen=True)

    status: RecommendationStatus
    task_id: str | None
    task_title: str | None
    phase_id: str | None
    phase_title: str | None
    why: tuple[str, ...]
    why_now: str
    directly_unblocks_task_ids: tuple[str, ...]
    ranking_factors: RankingFactors | None


PRIORITY_ORDER = {
    TaskPriority.CRITICAL: 0,
    TaskPriority.HIGH: 1,
    TaskPriority.MEDIUM: 2,
    TaskPriority.LOW: 3,
}

STATUS_ORDER = {
    TaskStatus.IN_PROGRESS: 0,
    TaskStatus.NOT_STARTED: 1,
}


def _due_rank(task: Task, today: date) -> tuple[int, date]:
    if task.due_date is not None and task.due_date < today:
        return (0, task.due_date)
    if task.due_date is not None:
        return (1, task.due_date)
    return (2, date.max)


def _due_state(task: Task, today: date) -> str:
    if task.due_date is None:
        return "no_due_date"
    if task.due_date < today:
        return "overdue"
    if task.due_date == today:
        return "due_today"
    return "upcoming"


def _directly_unblocked_by(plan: RelocationPlan, candidate: Task) -> tuple[str, ...]:
    status_by_id = {task.id: task.status for task in plan.tasks}
    unblocked = []
    for task in plan.tasks:
        if (
            task.status is TaskStatus.COMPLETED
            or candidate.id not in task.dependency_task_ids
        ):
            continue
        other_dependencies = (
            dependency_id
            for dependency_id in task.dependency_task_ids
            if dependency_id != candidate.id
        )
        if all(
            status_by_id[dependency_id] is TaskStatus.COMPLETED
            for dependency_id in other_dependencies
        ):
            unblocked.append(task.id)
    return tuple(sorted(unblocked))


def recommend_relocation_task(
    plan: RelocationPlan, *, today: date | None = None
) -> RelocationTaskRecommendation:
    """Choose one actionable task through an explicit stable comparison order."""
    current_date = today or date.today()
    phase_by_id = {phase.id: phase for phase in plan.phases}
    actionable = tuple(
        task
        for task in plan.tasks
        if not task.is_parent
        and task.status is not TaskStatus.COMPLETED
        and not task.blocked
        and (task.start_date is None or task.start_date <= current_date)
    )

    if not actionable:
        completed = sum(task.status is TaskStatus.COMPLETED for task in plan.tasks)
        blocked = sum(
            task.status is not TaskStatus.COMPLETED and task.blocked
            for task in plan.tasks
        )
        future = sum(
            task.status is not TaskStatus.COMPLETED
            and not task.blocked
            and task.start_date is not None
            and task.start_date > current_date
            for task in plan.tasks
        )
        if not plan.tasks:
            state_summary = "The relocation plan does not contain any tasks."
            next_step = "Add a task before asking GoTime what to do next."
        elif completed == len(plan.tasks):
            state_summary = "All stored relocation tasks are completed."
            next_step = "There is no remaining stored task to recommend."
        else:
            state_summary = (
                f"{completed} completed, {blocked} blocked, and {future} "
                "scheduled for later."
            )
            next_step = (
                "No stored task is actionable today. Complete a prerequisite or wait "
                "until a scheduled task can begin."
            )
        return RelocationTaskRecommendation(
            status=RecommendationStatus.NO_ACTIONABLE_TASK,
            task_id=None,
            task_title=None,
            phase_id=None,
            phase_title=None,
            why=(state_summary,),
            why_now=next_step,
            directly_unblocks_task_ids=(),
            ranking_factors=None,
        )

    leverage = {task.id: _directly_unblocked_by(plan, task) for task in actionable}
    selected = min(
        actionable,
        key=lambda task: (
            PRIORITY_ORDER[task.priority],
            *_due_rank(task, current_date),
            STATUS_ORDER[task.status],
            -len(leverage[task.id]),
            phase_by_id[task.phase_id].position,
            task.id,
        ),
    )
    phase = phase_by_id[selected.phase_id]
    due_state = _due_state(selected, current_date)
    reasons = [f"Its user priority is {selected.priority.value}."]
    if due_state == "overdue":
        reasons.append(f"It is overdue from {selected.due_date.isoformat()}.")
    elif due_state == "due_today":
        reasons.append("It is due today.")
    elif selected.due_date is not None:
        reasons.append(f"It is due on {selected.due_date.isoformat()}.")
    else:
        reasons.append("It is actionable and has no later start-date restriction.")
    if selected.status is TaskStatus.IN_PROGRESS:
        reasons.append("It is already in progress.")

    directly_unblocks = leverage[selected.id]
    if directly_unblocks:
        count = len(directly_unblocks)
        why_now = (
            f"Completing it will directly unblock {count} incomplete "
            f"{'task' if count == 1 else 'tasks'}."
        )
    else:
        why_now = "It is available to work on now and has no incomplete prerequisites."

    return RelocationTaskRecommendation(
        status=RecommendationStatus.RECOMMENDED,
        task_id=selected.id,
        task_title=selected.title,
        phase_id=phase.id,
        phase_title=phase.title,
        why=tuple(reasons),
        why_now=why_now,
        directly_unblocks_task_ids=directly_unblocks,
        ranking_factors=RankingFactors(
            due_state=due_state,
            due_date=selected.due_date,
            priority=selected.priority,
            task_status=selected.status,
            directly_unblocks_count=len(directly_unblocks),
            phase_position=phase.position,
        ),
    )
