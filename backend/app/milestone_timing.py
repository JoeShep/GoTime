from __future__ import annotations

from datetime import date, timedelta

from app.relocation_plan_models import (
    Decision,
    Milestone,
    MilestoneStatus,
    MilestoneTimingAnalysis,
    MilestoneTimingMode,
    MilestoneTimingStatus,
    Task,
    TaskStatus,
)


def analyze_milestones(
    *, milestones: tuple[Milestone, ...], decisions: tuple[Decision, ...],
    tasks: tuple[Task, ...], evaluation_date: date,
) -> tuple[Milestone, ...]:
    """Attach deterministic lean fixed-date timing without mutating stored data."""
    del decisions  # Decision-option timing is intentionally deferred.
    return tuple(
        milestone.model_copy(update={"timing": analyze_fixed_milestone(
            milestone, tasks=tasks, evaluation_date=evaluation_date,
        )})
        for milestone in milestones
    )


def analyze_fixed_milestone(
    milestone: Milestone, *, tasks: tuple[Task, ...], evaluation_date: date,
) -> MilestoneTimingAnalysis | None:
    if milestone.timing_mode is not MilestoneTimingMode.FIXED_DATE:
        return MilestoneTimingAnalysis(
            status=MilestoneTimingStatus.NO_WORK_LINKED,
            summary="No work linked yet",
        )
    if milestone.governed_phase_id is None:
        return MilestoneTimingAnalysis(
            status=MilestoneTimingStatus.NO_WORK_LINKED,
            summary="No work linked yet",
        )

    task_by_id = {task.id: task for task in tasks}
    children: dict[str, tuple[str, ...]] = {}
    for task in tasks:
        if task.parent_task_id:
            children[task.parent_task_id] = (*children.get(task.parent_task_id, ()), task.id)

    governed: set[str] = set()

    def include(task_id: str, visiting: frozenset[str] = frozenset()) -> None:
        if task_id in governed or task_id in visiting or task_id not in task_by_id:
            return
        task = task_by_id[task_id]
        if not task.active:
            return
        governed.add(task_id)
        path = visiting | {task_id}
        for child_id in children.get(task_id, ()):
            include(child_id, path)
        for dependency_id in dependency_ids(task, task_by_id):
            dependency = task_by_id.get(dependency_id)
            if dependency and dependency.status is not TaskStatus.COMPLETED:
                include(dependency_id, path)

    for task in tasks:
        if task.phase_id == milestone.governed_phase_id and task.parent_task_id is None:
            include(task.id)

    leaves = {task_id for task_id in governed if not children.get(task_id)}
    remaining = {
        task_id for task_id in leaves
        if task_by_id[task_id].status is not TaskStatus.COMPLETED
    }
    missing = tuple(sorted(
        task_id for task_id in remaining
        if task_by_id[task_id].expected_elapsed_min_days is None
        or task_by_id[task_id].expected_elapsed_max_days is None
    ))
    if missing or milestone.target_earliest_date is None:
        return MilestoneTimingAnalysis(
            status=MilestoneTimingStatus.TIMING_INCOMPLETE,
            summary="Add expected elapsed time to the related work before GoTime can calculate when this phase should begin.",
            governed_task_ids=tuple(sorted(governed)),
            actionable_task_ids=actionable_frontier(governed, task_by_id),
            missing_duration_task_ids=missing,
        )

    minimum, maximum, critical = critical_path_range(remaining, task_by_id=task_by_id)
    fixed_date = milestone.target_earliest_date
    safe_start = fixed_date - timedelta(days=maximum)
    last_plausible = fixed_date - timedelta(days=minimum)
    if milestone.status is MilestoneStatus.ACHIEVED:
        status = MilestoneTimingStatus.NOT_YET_TIME_SENSITIVE
        summary = "Milestone achieved"
    elif evaluation_date < safe_start:
        status = MilestoneTimingStatus.NOT_YET_TIME_SENSITIVE
        summary = "Not yet time-sensitive"
    elif evaluation_date == safe_start:
        status = MilestoneTimingStatus.TIME_TO_BEGIN
        summary = "Time to begin"
    elif evaluation_date <= last_plausible:
        status = MilestoneTimingStatus.AT_RISK
        summary = "At risk"
    else:
        status = MilestoneTimingStatus.LIKELY_TO_MISS
        summary = "Likely to miss"

    return MilestoneTimingAnalysis(
        status=status,
        summary=summary,
        governed_task_ids=tuple(sorted(governed)),
        critical_path_task_ids=critical,
        actionable_task_ids=actionable_frontier(set(critical), task_by_id),
        duration_min_days=minimum,
        duration_max_days=maximum,
        start_window_opening=safe_start,
        conservative_latest_start=safe_start,
        last_plausible_start=last_plausible,
        conflicts=date_conflicts(
            governed, task_by_id=task_by_id, safe_start=safe_start,
            fixed_date=fixed_date,
        ),
    )


def dependency_ids(task: Task, task_by_id: dict[str, Task]) -> tuple[str, ...]:
    parent_dependencies = (
        task_by_id[task.parent_task_id].dependency_task_ids
        if task.parent_task_id and task.parent_task_id in task_by_id else ()
    )
    return tuple(dict.fromkeys((*task.dependency_task_ids, *parent_dependencies)))


def critical_path_range(
    task_ids: set[str], *, task_by_id: dict[str, Task],
) -> tuple[int, int, tuple[str, ...]]:
    """Longest dependency path: sequential work adds and parallel work overlaps."""
    memo: dict[str, tuple[int, int, tuple[str, ...]]] = {}

    def finish(task_id: str, visiting: frozenset[str] = frozenset()) -> tuple[int, int, tuple[str, ...]]:
        if task_id in memo:
            return memo[task_id]
        if task_id in visiting:
            raise ValueError("Milestone timing graph cannot contain a cycle.")
        task = task_by_id[task_id]
        if task.status is TaskStatus.COMPLETED:
            result = (0, 0, ())
        else:
            ranges = [
                finish(item, visiting | {task_id})
                for item in dependency_ids(task, task_by_id) if item in task_ids
            ]
            longest = max(ranges, key=lambda item: (item[1], item[0], item[2]), default=(0, 0, ()))
            longest_min = max((item[0] for item in ranges), default=0)
            own_min = task.expected_elapsed_min_days
            own_max = task.expected_elapsed_max_days
            if own_min is None or own_max is None:
                raise ValueError("Unknown duration cannot be used as zero.")
            result = (longest_min + own_min, longest[1] + own_max, (*longest[2], task_id))
        memo[task_id] = result
        return result

    return max(
        (finish(task_id) for task_id in task_ids),
        key=lambda item: (item[1], item[0], item[2]),
        default=(0, 0, ()),
    )


def actionable_frontier(task_ids: set[str], task_by_id: dict[str, Task]) -> tuple[str, ...]:
    return tuple(sorted(
        task_id for task_id in task_ids
        if task_id in task_by_id and task_by_id[task_id].active
        and not task_by_id[task_id].is_parent and not task_by_id[task_id].blocked
        and task_by_id[task_id].status is not TaskStatus.COMPLETED
    ))


def date_conflicts(
    task_ids: set[str], *, task_by_id: dict[str, Task], safe_start: date,
    fixed_date: date,
) -> tuple[str, ...]:
    messages: list[str] = []
    for task_id in sorted(task_ids):
        task = task_by_id[task_id]
        if task.start_date and task.start_date > safe_start and task.status is TaskStatus.NOT_STARTED:
            messages.append(f"{task.title}: Waiting until this date may put the Milestone at risk.")
        if task.due_date and task.due_date > fixed_date:
            messages.append(f"{task.title}: This Task needs to finish earlier to keep the Milestone on track.")
    return tuple(messages)
