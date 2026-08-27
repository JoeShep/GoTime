from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from app.relocation_plan_models import (
    Decision, DecisionPreparationReadiness, DecisionStatus, RelocationPlan, Task,
    TaskCategory, TaskPriority, TaskStatus,
)


class RecommendationStatus(StrEnum):
    RECOMMENDED = "recommended"
    NO_ACTIONABLE_TASK = "no_actionable_task"


class RecommendationCandidateType(StrEnum):
    TASK = "task"
    DECISION = "decision"


class RecommendationSignalKind(StrEnum):
    READY_TO_DECIDE = "ready_to_decide"
    DIRECT_DECISION_PREPARATION = "direct_decision_preparation"
    INHERITED_DECISION_PREPARATION = "inherited_decision_preparation"
    UNBLOCKS_DECISION_PREPARATION = "unblocks_decision_preparation"


class RecommendationSignal(BaseModel):
    model_config = ConfigDict(frozen=True)
    kind: RecommendationSignalKind
    decision_id: str
    decision_title: str
    preparation_task_id: str | None = None
    preparation_task_title: str | None = None
    parent_task_id: str | None = None
    parent_task_title: str | None = None
    blocked_task_id: str | None = None
    blocked_task_title: str | None = None
    dependency_path_task_ids: tuple[str, ...] = ()


class TaskRecommendationMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)
    status: TaskStatus
    assignees: tuple[str, ...]
    categories: tuple[TaskCategory, ...]
    start_date: date | None
    due_date: date | None
    priority: TaskPriority


class RankingFactors(BaseModel):
    model_config = ConfigDict(frozen=True)
    due_state: str
    due_date: date | None
    effective_due_date: date | None = None
    priority: TaskPriority
    task_status: TaskStatus
    directly_unblocks_count: int
    phase_position: int
    decision_context_rank: int = 2


class RecommendationItem(BaseModel):
    model_config = ConfigDict(frozen=True)
    candidate_type: RecommendationCandidateType
    task_id: str | None = None
    task_title: str | None = None
    decision_id: str | None = None
    decision_title: str | None = None
    phase_id: str | None = None
    phase_title: str | None = None
    why: tuple[str, ...]
    why_now: str
    directly_unblocks_task_ids: tuple[str, ...] = ()
    signals: tuple[RecommendationSignal, ...] = ()
    task_metadata: TaskRecommendationMetadata | None = None
    ranking_factors: RankingFactors | None = None


class RelocationTaskRecommendation(BaseModel):
    model_config = ConfigDict(frozen=True)
    status: RecommendationStatus
    candidate_type: RecommendationCandidateType | None = None
    task_id: str | None = None
    task_title: str | None = None
    decision_id: str | None = None
    decision_title: str | None = None
    phase_id: str | None = None
    phase_title: str | None = None
    why: tuple[str, ...]
    why_now: str
    directly_unblocks_task_ids: tuple[str, ...] = ()
    signals: tuple[RecommendationSignal, ...] = ()
    task_metadata: TaskRecommendationMetadata | None = None
    ranking_factors: RankingFactors | None = None
    upcoming: tuple[RecommendationItem, ...] = ()


PRIORITY_ORDER = {TaskPriority.CRITICAL: 0, TaskPriority.HIGH: 1, TaskPriority.MEDIUM: 2, TaskPriority.LOW: 3}
STATUS_ORDER = {TaskStatus.IN_PROGRESS: 0, TaskStatus.NOT_STARTED: 1}


@dataclass(frozen=True)
class _TaskSignal:
    signal: RecommendationSignal
    pressure_due_date: date | None


@dataclass(frozen=True)
class _RankedItem:
    sort_key: tuple[object, ...]
    item: RecommendationItem


def _due_rank_value(due_date: date | None, today: date) -> tuple[int, date]:
    if due_date is not None and due_date < today:
        return (0, due_date)
    if due_date is not None:
        return (1, due_date)
    return (2, date.max)


def _due_state_value(due_date: date | None, today: date) -> str:
    if due_date is None:
        return "no_due_date"
    if due_date < today:
        return "overdue"
    if due_date == today:
        return "due_today"
    return "upcoming"


def _directly_unblocked_by(plan: RelocationPlan, candidate: Task) -> tuple[str, ...]:
    status_by_id = {task.id: task.status for task in plan.tasks}
    unblocked = []
    for task in plan.tasks:
        if task.status is TaskStatus.COMPLETED or candidate.id not in task.dependency_task_ids:
            continue
        others = (item for item in task.dependency_task_ids if item != candidate.id)
        if all(status_by_id[item] is TaskStatus.COMPLETED for item in others):
            unblocked.append(task.id)
    return tuple(sorted(unblocked))


def _is_actionable(task: Task, today: date) -> bool:
    return task.active and not task.is_parent and task.status is not TaskStatus.COMPLETED and not task.blocked and (task.start_date is None or task.start_date <= today)


def _children_by_parent(plan: RelocationPlan) -> dict[str, tuple[Task, ...]]:
    grouped: dict[str, list[Task]] = {}
    for task in plan.tasks:
        if task.parent_task_id:
            grouped.setdefault(task.parent_task_id, []).append(task)
    return {key: tuple(sorted(value, key=lambda child: (child.subtask_position or 0, child.id))) for key, value in grouped.items()}


def _dependency_ids(task: Task, task_by_id: dict[str, Task]) -> tuple[str, ...]:
    inherited = task_by_id[task.parent_task_id].dependency_task_ids if task.parent_task_id and task.parent_task_id in task_by_id else ()
    return tuple(dict.fromkeys((*task.dependency_task_ids, *inherited)))


def _frontier(task: Task, *, today: date, task_by_id: dict[str, Task], children_by_parent: dict[str, tuple[Task, ...]], path: tuple[str, ...] = ()) -> tuple[tuple[Task, tuple[str, ...]], ...]:
    if task.id in path or not task.active or task.status is TaskStatus.COMPLETED:
        return ()
    next_path = (*path, task.id)
    if task.is_parent:
        return tuple(item for child in children_by_parent.get(task.id, ()) for item in _frontier(child, today=today, task_by_id=task_by_id, children_by_parent=children_by_parent, path=next_path))
    if _is_actionable(task, today):
        return ((task, next_path),)
    dependencies = tuple(task_by_id[item] for item in _dependency_ids(task, task_by_id) if item in task_by_id and task_by_id[item].status is not TaskStatus.COMPLETED)
    return tuple(item for dependency in dependencies for item in _frontier(dependency, today=today, task_by_id=task_by_id, children_by_parent=children_by_parent, path=next_path))


def _decision_signals(plan: RelocationPlan, today: date) -> tuple[dict[str, list[_TaskSignal]], tuple[Decision, ...]]:
    task_by_id = {task.id: task for task in plan.tasks}
    children = _children_by_parent(plan)
    signals: dict[str, list[_TaskSignal]] = {}
    ready: list[Decision] = []
    for decision in plan.decisions:
        if decision.status is DecisionStatus.RESOLVED:
            continue
        if decision.preparation_readiness is DecisionPreparationReadiness.READY_TO_DECIDE:
            ready.append(decision)
            continue
        if decision.preparation_readiness is not DecisionPreparationReadiness.PREPARATION_INCOMPLETE:
            continue
        for preparation_id in decision.preparation_task_ids:
            preparation = task_by_id.get(preparation_id)
            if not preparation or not preparation.active or preparation.status is TaskStatus.COMPLETED:
                continue
            roots = children.get(preparation.id, ()) if preparation.is_parent else (preparation,)
            for root in roots:
                if root.status is TaskStatus.COMPLETED or not root.active:
                    continue
                for frontier, path in _frontier(root, today=today, task_by_id=task_by_id, children_by_parent=children):
                    inherited = preparation.is_parent
                    unblocks = frontier.id != root.id
                    kind = RecommendationSignalKind.UNBLOCKS_DECISION_PREPARATION if unblocks else RecommendationSignalKind.INHERITED_DECISION_PREPARATION if inherited else RecommendationSignalKind.DIRECT_DECISION_PREPARATION
                    parent = preparation if inherited else task_by_id.get(root.parent_task_id or "")
                    signals.setdefault(frontier.id, []).append(_TaskSignal(
                        signal=RecommendationSignal(
                            kind=kind, decision_id=decision.id, decision_title=decision.title,
                            preparation_task_id=preparation.id, preparation_task_title=preparation.title,
                            parent_task_id=parent.id if parent else None, parent_task_title=parent.title if parent else None,
                            blocked_task_id=root.id if unblocks else None, blocked_task_title=root.title if unblocks else None,
                            dependency_path_task_ids=path,
                        ),
                        pressure_due_date=root.due_date or preparation.due_date,
                    ))
    return signals, tuple(ready)


def _deduplicate_signals(signals: list[_TaskSignal]) -> tuple[RecommendationSignal, ...]:
    by_decision: dict[str, RecommendationSignal] = {}
    for contextual in signals:
        current = by_decision.get(contextual.signal.decision_id)
        if current is None or len(contextual.signal.dependency_path_task_ids) < len(current.dependency_path_task_ids):
            by_decision[contextual.signal.decision_id] = contextual.signal
    return tuple(by_decision[key] for key in sorted(by_decision))


def _task_item(plan: RelocationPlan, task: Task, task_signals: list[_TaskSignal], *, today: date) -> _RankedItem:
    phase = next(phase for phase in plan.phases if phase.id == task.phase_id)
    leverage = _directly_unblocked_by(plan, task)
    signals = _deduplicate_signals(task_signals)
    pressure_dates = [item.pressure_due_date for item in task_signals if item.pressure_due_date]
    effective_due_date = min([value for value in (task.due_date, *pressure_dates) if value], key=lambda value: _due_rank_value(value, today), default=None)
    due_state = _due_state_value(task.due_date, today)
    reasons = [f"Its user priority is {task.priority.value}."]
    if due_state == "overdue": reasons.append(f"It is overdue from {task.due_date.isoformat()}.")
    elif due_state == "due_today": reasons.append("It is due today.")
    elif task.due_date is not None: reasons.append(f"It is due on {task.due_date.isoformat()}.")
    else: reasons.append("It is actionable and has no later start-date restriction.")
    if task.status is TaskStatus.IN_PROGRESS: reasons.append("It is already in progress.")
    if signals: why_now = "It advances preparation for an unresolved decision."
    elif leverage:
        count = len(leverage)
        why_now = f"Completing it will directly unblock {count} incomplete {'task' if count == 1 else 'tasks'}."
    else: why_now = "It is available to work on now and has no incomplete prerequisites."
    context_rank = 1 if signals else 2
    item = RecommendationItem(
        candidate_type=RecommendationCandidateType.TASK, task_id=task.id, task_title=task.title,
        phase_id=phase.id, phase_title=phase.title, why=tuple(reasons), why_now=why_now,
        directly_unblocks_task_ids=leverage, signals=signals,
        task_metadata=TaskRecommendationMetadata(status=task.status, assignees=task.assignees, categories=task.categories, start_date=task.start_date, due_date=task.due_date, priority=task.priority),
        ranking_factors=RankingFactors(due_state=due_state, due_date=task.due_date, effective_due_date=effective_due_date, priority=task.priority, task_status=task.status, directly_unblocks_count=len(leverage), phase_position=phase.position, decision_context_rank=context_rank),
    )
    return _RankedItem(sort_key=(PRIORITY_ORDER[task.priority], *_due_rank_value(effective_due_date, today), STATUS_ORDER[task.status], context_rank, -len(leverage), phase.position, task.parent_task_id or "", task.subtask_position if task.subtask_position is not None else 1_000_000, task.id), item=item)


def _decision_item(decision: Decision, today: date) -> _RankedItem:
    item = RecommendationItem(
        candidate_type=RecommendationCandidateType.DECISION, decision_id=decision.id,
        decision_title=decision.title, why=("All currently tracked preparation work is complete.",),
        why_now="This unresolved decision is ready for your review.",
        signals=(RecommendationSignal(kind=RecommendationSignalKind.READY_TO_DECIDE, decision_id=decision.id, decision_title=decision.title),),
        ranking_factors=RankingFactors(due_state="no_due_date", due_date=None, effective_due_date=None, priority=TaskPriority.MEDIUM, task_status=TaskStatus.NOT_STARTED, directly_unblocks_count=0, phase_position=0, decision_context_rank=0),
    )
    return _RankedItem(sort_key=(PRIORITY_ORDER[TaskPriority.MEDIUM], *_due_rank_value(None, today), STATUS_ORDER[TaskStatus.NOT_STARTED], 0, 0, 0, "", 1_000_000, decision.id), item=item)


def recommend_relocation_task(plan: RelocationPlan, *, today: date | None = None) -> RelocationTaskRecommendation:
    """Rank deterministic Task and ready-Decision candidates from one Plan."""
    current_date = today or date.today()
    signals_by_task, ready_decisions = _decision_signals(plan, current_date)
    ranked = [_task_item(plan, task, signals_by_task.get(task.id, []), today=current_date) for task in plan.tasks if _is_actionable(task, current_date)]
    ranked.extend(_decision_item(decision, current_date) for decision in ready_decisions)
    ranked.sort(key=lambda candidate: candidate.sort_key)
    if not ranked:
        completed = sum(task.status is TaskStatus.COMPLETED for task in plan.tasks)
        blocked = sum(task.status is not TaskStatus.COMPLETED and task.blocked for task in plan.tasks)
        future = sum(task.status is not TaskStatus.COMPLETED and not task.blocked and task.start_date is not None and task.start_date > current_date for task in plan.tasks)
        if not plan.tasks:
            state_summary, next_step = "The relocation plan does not contain any tasks.", "Add a task before asking GoTime what to do next."
        elif completed == len(plan.tasks):
            state_summary, next_step = "All stored relocation tasks are completed.", "There is no remaining stored task or ready decision to recommend."
        else:
            state_summary, next_step = f"{completed} completed, {blocked} blocked, and {future} scheduled for later.", "No stored work is actionable today. Complete a prerequisite or wait until scheduled work can begin."
        return RelocationTaskRecommendation(status=RecommendationStatus.NO_ACTIONABLE_TASK, why=(state_summary,), why_now=next_step)
    primary = ranked[0].item
    return RelocationTaskRecommendation(status=RecommendationStatus.RECOMMENDED, **primary.model_dump(), upcoming=tuple(candidate.item for candidate in ranked[1:3]))
