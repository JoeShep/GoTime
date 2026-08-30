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
    MILESTONE_TIMING = "milestone_timing"


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
    milestone_id: str | None = None
    milestone_title: str | None = None
    milestone_timing_status: str | None = None


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


PRIORITY_CONTRIBUTION = {
    TaskPriority.CRITICAL: 3, TaskPriority.HIGH: 2,
    TaskPriority.MEDIUM: 1, TaskPriority.LOW: 0,
}
DUE_CONTRIBUTION = {0: 100, 1: 60, 2: 30, 3: 12, 4: 0, 5: 0}


@dataclass(frozen=True)
class _TaskSignal:
    signal: RecommendationSignal


@dataclass(frozen=True)
class _RankedItem:
    sort_key: tuple[object, ...]
    item: RecommendationItem


def _due_band(due_date: date | None, today: date) -> int:
    if due_date is None: return 5
    days = (due_date - today).days
    if days <= 0: return 0
    if days <= 3: return 1
    if days <= 7: return 2
    if days <= 30: return 3
    return 4


def _due_state_value(due_date: date | None, today: date) -> str:
    if due_date is None:
        return "no_due_date"
    if due_date < today:
        return "overdue"
    if due_date == today:
        return "due_today"
    return "upcoming"


def _children_by_parent(plan: RelocationPlan) -> dict[str, tuple[Task, ...]]:
    grouped: dict[str, list[Task]] = {}
    for task in plan.tasks:
        if task.parent_task_id:
            grouped.setdefault(task.parent_task_id, []).append(task)
    return {key: tuple(sorted(value, key=lambda child: (child.subtask_position or 0, child.id))) for key, value in grouped.items()}


def _dependency_ids(task: Task, task_by_id: dict[str, Task]) -> tuple[str, ...]:
    inherited = task_by_id[task.parent_task_id].dependency_task_ids if task.parent_task_id and task.parent_task_id in task_by_id else ()
    return tuple(dict.fromkeys((*task.dependency_task_ids, *inherited)))


def _recommendation_hold(task: Task, task_by_id: dict[str, Task]) -> date | None:
    if task.status is TaskStatus.IN_PROGRESS:
        return None
    holds = [task.start_date]
    if task.parent_task_id and task.parent_task_id in task_by_id:
        holds.append(task_by_id[task.parent_task_id].start_date)
    return max((value for value in holds if value is not None), default=None)


def _is_actionable(task: Task, today: date, task_by_id: dict[str, Task]) -> bool:
    hold = _recommendation_hold(task, task_by_id)
    return (
        task.active and not task.is_parent
        and task.status is not TaskStatus.COMPLETED and not task.blocked
        and (hold is None or hold <= today)
    )


def _frontier(task: Task, *, today: date, task_by_id: dict[str, Task], children_by_parent: dict[str, tuple[Task, ...]], path: tuple[str, ...] = ()) -> tuple[tuple[Task, tuple[str, ...]], ...]:
    if task.id in path or not task.active or task.status is TaskStatus.COMPLETED:
        return ()
    next_path = (*path, task.id)
    if task.is_parent:
        return tuple(item for child in children_by_parent.get(task.id, ()) for item in _frontier(child, today=today, task_by_id=task_by_id, children_by_parent=children_by_parent, path=next_path))
    if _is_actionable(task, today, task_by_id):
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
        if decision.preparation_readiness is DecisionPreparationReadiness.READY_TO_DECIDE and decision.preparation_task_ids:
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
                    ))
    return signals, tuple(ready)


def _deduplicate_signals(signals: list[_TaskSignal]) -> tuple[RecommendationSignal, ...]:
    by_decision: dict[str, RecommendationSignal] = {}
    for contextual in signals:
        current = by_decision.get(contextual.signal.decision_id)
        if current is None or len(contextual.signal.dependency_path_task_ids) < len(current.dependency_path_task_ids):
            by_decision[contextual.signal.decision_id] = contextual.signal
    return tuple(by_decision[key] for key in sorted(by_decision))


def _deadline_pressure(plan: RelocationPlan, today: date) -> dict[str, tuple[date, str]]:
    task_by_id = {task.id: task for task in plan.tasks}
    children = _children_by_parent(plan)
    pressure: dict[str, tuple[date, str]] = {}
    for downstream in plan.tasks:
        if not downstream.active or downstream.status is TaskStatus.COMPLETED or downstream.due_date is None:
            continue
        roots = children.get(downstream.id, ()) if downstream.is_parent else (downstream,)
        for root in roots:
            if root.status is TaskStatus.COMPLETED or not root.active:
                continue
            frontier = _frontier(root, today=today, task_by_id=task_by_id, children_by_parent=children)
            for candidate, _ in frontier:
                if candidate.id == downstream.id:
                    continue
                current = pressure.get(candidate.id)
                if current is None or downstream.due_date < current[0]:
                    pressure[candidate.id] = (downstream.due_date, downstream.title)
    return pressure


def _completion_effects(plan: RelocationPlan, candidate: Task) -> tuple[tuple[str, ...], tuple[str, ...]]:
    task_by_id = {task.id: task for task in plan.tasks}
    children = _children_by_parent(plan)
    memo: dict[str, bool] = {}
    def completed(task_id: str) -> bool:
        if task_id == candidate.id: return True
        if task_id in memo: return memo[task_id]
        task = task_by_id[task_id]
        value = task.status is TaskStatus.COMPLETED
        if task.is_parent and task.manual_status_override is None:
            child_items = children.get(task.id, ())
            value = bool(child_items) and all(completed(child.id) for child in child_items)
        memo[task_id] = value
        return value
    unlocked: list[str] = []
    for dependent in plan.tasks:
        if not dependent.active or dependent.status is TaskStatus.COMPLETED or not dependent.blocked:
            continue
        dependencies = _dependency_ids(dependent, task_by_id)
        if dependencies and all(completed(item) for item in dependencies):
            unlocked.append(dependent.id)
    ready: list[str] = []
    for decision in plan.decisions:
        if decision.status is DecisionStatus.RESOLVED or not decision.preparation_task_ids:
            continue
        before_complete = all(task_by_id[item].status is TaskStatus.COMPLETED for item in decision.preparation_task_ids)
        if not before_complete and all(completed(item) for item in decision.preparation_task_ids):
            ready.append(decision.id)
    return tuple(sorted(unlocked)), tuple(sorted(ready))


def _deadline_reason(task: Task, effective_due: date | None, source_title: str | None, today: date) -> str | None:
    if effective_due is None: return None
    days = (effective_due - today).days
    if source_title:
        timing = "overdue" if days < 0 else "due today" if days == 0 else f"due in {days} days"
        return f'Needed before “{source_title},” which is {timing}.'
    if days < 0: return f"Overdue since {effective_due.isoformat()}."
    if days == 0: return "Due today."
    if days <= 3: return f"Due in {days} {'day' if days == 1 else 'days'}."
    if days <= 7: return "Due this week."
    if days <= 30: return "Due within 30 days."
    return None


def _task_item(plan: RelocationPlan, task: Task, task_signals: list[_TaskSignal], deadline: tuple[date, str] | None, milestone_signals: tuple[RecommendationSignal, ...], *, today: date) -> _RankedItem:
    phase = next(phase for phase in plan.phases if phase.id == task.phase_id)
    leverage, readied_decisions = _completion_effects(plan, task)
    signals = _deduplicate_signals(task_signals)
    candidates = [(task.due_date, None), deadline or (None, None)]
    effective_due_date, deadline_source = min(
        (item for item in candidates if item[0] is not None), key=lambda item: item[0], default=(None, None)
    )
    due_state = _due_state_value(effective_due_date, today)
    band = _due_band(effective_due_date, today)
    meaningful: list[tuple[int, str]] = []
    due_reason = _deadline_reason(task, effective_due_date, deadline_source, today)
    if due_reason: meaningful.append((100 if band == 0 else DUE_CONTRIBUTION[band], due_reason))
    if leverage:
        count = len(leverage)
        meaningful.append((48 if count > 1 else 24, f"Completing it unlocks {count} {'Task' if count == 1 else 'Tasks'}."))
    if readied_decisions:
        decision = next(item for item in plan.decisions if item.id == readied_decisions[0])
        meaningful.append((28, f"Final step needed before deciding {decision.title}."))
    if task.status is TaskStatus.IN_PROGRESS: meaningful.append((22, "Already in progress."))
    if signals:
        meaningful.append((10, f"Helps prepare {signals[0].decision_title}."))
    milestone_score = 0
    if milestone_signals:
        state = milestone_signals[0].milestone_timing_status
        milestone_score = {
            "timing_incomplete": 8,
            "time_to_begin": 24,
            "at_risk": 42,
            "likely_to_miss": 58,
        }.get(state or "", 0)
        if state == "at_risk":
            text = "This is on the critical path for a Milestone that is at risk."
        elif state == "likely_to_miss":
            text = f"Starting this now helps keep {milestone_signals[0].milestone_title} on track."
        elif state == "time_to_begin":
            text = f"Starting this now helps keep {milestone_signals[0].milestone_title} on track."
        else:
            text = f"Related timing for {milestone_signals[0].milestone_title} is incomplete."
        meaningful.append((milestone_score, text))
    reasons = tuple(value for _, value in sorted(meaningful, key=lambda item: (-item[0], item[1]))[:2])
    leverage_score = min(48, 24 * (len(leverage) + len(readied_decisions)))
    score = DUE_CONTRIBUTION[band] + leverage_score + (22 if task.status is TaskStatus.IN_PROGRESS else 0) + (10 if signals else 0) + milestone_score + PRIORITY_CONTRIBUTION[task.priority]
    context_rank = 1 if signals else 2
    item = RecommendationItem(
        candidate_type=RecommendationCandidateType.TASK, task_id=task.id, task_title=task.title,
        phase_id=phase.id, phase_title=phase.title, why=reasons, why_now="",
        directly_unblocks_task_ids=leverage, signals=(*signals, *milestone_signals),
        task_metadata=TaskRecommendationMetadata(status=task.status, assignees=task.assignees, categories=task.categories, start_date=task.start_date, due_date=task.due_date, priority=task.priority),
        ranking_factors=RankingFactors(due_state=due_state, due_date=task.due_date, effective_due_date=effective_due_date, priority=task.priority, task_status=task.status, directly_unblocks_count=len(leverage), phase_position=phase.position, decision_context_rank=context_rank),
    )
    return _RankedItem(sort_key=(0 if band == 0 else 1, effective_due_date if band == 0 else date.max, -score, band, effective_due_date or date.max, phase.position, task.parent_task_id or "", task.subtask_position if task.subtask_position is not None else 1_000_000, task.id), item=item)


def _decision_item(decision: Decision, today: date) -> _RankedItem:
    item = RecommendationItem(
        candidate_type=RecommendationCandidateType.DECISION, decision_id=decision.id,
        decision_title=decision.title, why=("All currently tracked preparation work is complete.",),
        why_now="",
        signals=(RecommendationSignal(kind=RecommendationSignalKind.READY_TO_DECIDE, decision_id=decision.id, decision_title=decision.title),),
        ranking_factors=RankingFactors(due_state="no_due_date", due_date=None, effective_due_date=None, priority=TaskPriority.MEDIUM, task_status=TaskStatus.NOT_STARTED, directly_unblocks_count=0, phase_position=0, decision_context_rank=0),
    )
    return _RankedItem(sort_key=(1, date.max, -35, 5, date.max, 0, "", 1_000_000, decision.id), item=item)


def recommend_relocation_task(plan: RelocationPlan, *, today: date | None = None) -> RelocationTaskRecommendation:
    """Rank deterministic Task and ready-Decision candidates from one Plan."""
    current_date = today or date.today()
    task_by_id = {task.id: task for task in plan.tasks}
    signals_by_task, ready_decisions = _decision_signals(plan, current_date)
    deadlines = _deadline_pressure(plan, current_date)
    milestone_signals_by_task: dict[str, list[RecommendationSignal]] = {}
    for milestone in plan.milestones:
        timing = milestone.timing
        if milestone.status.value == "achieved" or timing is None or timing.status.value in {"no_work_linked", "not_yet_time_sensitive"}:
            continue
        for task_id in timing.actionable_task_ids:
            milestone_signals_by_task.setdefault(task_id, []).append(
                RecommendationSignal(
                    kind=RecommendationSignalKind.MILESTONE_TIMING,
                    decision_id="",
                    decision_title="",
                    milestone_id=milestone.id,
                    milestone_title=milestone.title,
                    milestone_timing_status=timing.status.value,
                )
            )
    ranked = [_task_item(plan, task, signals_by_task.get(task.id, []), deadlines.get(task.id), tuple(milestone_signals_by_task.get(task.id, ())), today=current_date) for task in plan.tasks if _is_actionable(task, current_date, task_by_id)]
    ranked.extend(_decision_item(decision, current_date) for decision in ready_decisions)
    ranked.sort(key=lambda candidate: candidate.sort_key)
    if not ranked:
        completed = sum(task.status is TaskStatus.COMPLETED for task in plan.tasks)
        blocked = sum(task.status is not TaskStatus.COMPLETED and task.blocked for task in plan.tasks)
        future = sum(task.status is TaskStatus.NOT_STARTED and not task.blocked and (_recommendation_hold(task, task_by_id) or date.min) > current_date for task in plan.tasks)
        if not plan.tasks:
            state_summary, next_step = "The relocation plan does not contain any tasks.", "Add a task before asking GoTime what to do next."
        elif completed == len(plan.tasks):
            state_summary, next_step = "All stored relocation tasks are completed.", "There is no remaining stored task or ready decision to recommend."
        else:
            state_summary, next_step = f"{completed} completed, {blocked} blocked, and {future} scheduled for later.", "No stored work is actionable today. Complete a prerequisite or wait until scheduled work can begin."
        return RelocationTaskRecommendation(status=RecommendationStatus.NO_ACTIONABLE_TASK, why=(state_summary,), why_now=next_step)
    primary = ranked[0].item
    return RelocationTaskRecommendation(status=RecommendationStatus.RECOMMENDED, **primary.model_dump(), upcoming=tuple(candidate.item for candidate in ranked[1:3]))
