from datetime import date
import sqlite3

import pytest
from pydantic import ValidationError

from app.milestone_timing import analyze_fixed_milestone, critical_path_range
from app.relocation_plan_models import Milestone, MilestoneCreate, Task, TaskCreate
from app.relocation_plan_recommendation import recommend_relocation_task
from app.relocation_plan_repository import RelocationPlanError, SQLiteRelocationPlanRepository


TODAY = date(2026, 8, 29)


def task(task_id: str, **changes: object) -> Task:
    values: dict[str, object] = {
        "id": task_id, "title": task_id.replace("-", " ").title(),
        "description": None, "phase_id": "prepare", "categories": (),
        "status": "not_started", "assignees": (), "start_date": None,
        "due_date": None, "priority": "medium", "dependency_task_ids": (),
        "blocked": False, "expected_elapsed_min_days": 1,
        "expected_elapsed_max_days": 1,
    }
    values.update(changes)
    return Task(**values)


def milestone(**changes: object) -> Milestone:
    values: dict[str, object] = {
        "id": "move", "title": "Move", "description": None,
        "target_earliest_date": "2026-09-10", "target_latest_date": "2026-09-10",
        "timing_mode": "fixed_date", "governed_phase_id": "prepare",
        "status": "pending", "achieved_at": None,
    }
    values.update(changes)
    return Milestone(**values)


@pytest.mark.parametrize("minimum,maximum", [(-1, 1), (1, -1), (1, 0), (1, None), (None, 1), (3651, 3651), (1.5, 2)])
def test_duration_range_rejects_invalid_values(minimum: object, maximum: object) -> None:
    with pytest.raises(ValidationError):
        TaskCreate(
            id="task", title="Task", phase_id="prepare", categories=(),
            expected_elapsed_min_days=minimum, expected_elapsed_max_days=maximum,
        )


def test_same_day_exact_and_calendar_boundaries() -> None:
    item = task("same-day", expected_elapsed_min_days=0, expected_elapsed_max_days=0)
    analysis = analyze_fixed_milestone(milestone(target_earliest_date="2026-09-01", target_latest_date="2026-09-01"), tasks=(item,), evaluation_date=date(2026, 9, 1))
    assert analysis and analysis.duration_min_days == analysis.duration_max_days == 0
    assert analysis.conservative_latest_start == date(2026, 9, 1)
    one_day = analyze_fixed_milestone(milestone(target_earliest_date="2027-01-01", target_latest_date="2027-01-01"), tasks=(item.model_copy(update={"expected_elapsed_min_days": 1, "expected_elapsed_max_days": 1}),), evaluation_date=TODAY)
    assert one_day and one_day.conservative_latest_start == date(2026, 12, 31)


def test_sequential_parallel_and_join_paths() -> None:
    first = task("first", expected_elapsed_min_days=2, expected_elapsed_max_days=3)
    parallel = task("parallel", expected_elapsed_min_days=4, expected_elapsed_max_days=5)
    join = task("join", dependency_task_ids=(first.id, parallel.id), expected_elapsed_min_days=1, expected_elapsed_max_days=2)
    minimum, maximum, critical = critical_path_range({first.id, parallel.id, join.id}, task_by_id={item.id: item for item in (first, parallel, join)})
    assert (minimum, maximum) == (5, 7)
    assert critical == (parallel.id, join.id)


def test_completed_in_progress_unknown_and_fixed_date_boundaries() -> None:
    done = task("done", status="completed", expected_elapsed_min_days=None, expected_elapsed_max_days=None)
    running = task("running", status="in_progress", expected_elapsed_min_days=5, expected_elapsed_max_days=8)
    unknown = task("unknown", expected_elapsed_min_days=None, expected_elapsed_max_days=None)
    complete = analyze_fixed_milestone(milestone(), tasks=(done, running), evaluation_date=date(2026, 9, 2))
    assert complete and (complete.duration_min_days, complete.duration_max_days) == (5, 8)
    assert complete.status == "time_to_begin"
    assert analyze_fixed_milestone(milestone(), tasks=(unknown,), evaluation_date=TODAY).status == "timing_incomplete"
    assert analyze_fixed_milestone(milestone(), tasks=(running,), evaluation_date=date(2026, 9, 1)).status == "not_yet_time_sensitive"
    assert analyze_fixed_milestone(milestone(), tasks=(running,), evaluation_date=date(2026, 9, 3)).status == "at_risk"
    assert analyze_fixed_milestone(milestone(), tasks=(running,), evaluation_date=date(2026, 9, 6)).status == "likely_to_miss"


def test_phase_scope_cross_phase_dependency_inactive_and_conflicts() -> None:
    prerequisite = task("prerequisite", phase_id="decide")
    governed = task("governed", dependency_task_ids=(prerequisite.id,), blocked=True, start_date="2026-09-09", due_date="2026-09-20")
    inactive = task("inactive", active=False, expected_elapsed_min_days=None, expected_elapsed_max_days=None)
    analysis = analyze_fixed_milestone(milestone(), tasks=(prerequisite, governed, inactive), evaluation_date=TODAY)
    assert analysis and set(analysis.governed_task_ids) == {prerequisite.id, governed.id}
    assert analysis.actionable_task_ids == (prerequisite.id,)
    assert len(analysis.conflicts) == 2


def test_migration_is_idempotent_unknown_by_default_and_conflicts_fail_closed(tmp_path) -> None:
    path = tmp_path / "plan.db"
    repository = SQLiteRelocationPlanRepository(path)
    repository.create_task(TaskCreate(id="task", title="Task", phase_id="prepare", categories=()))
    repository.create_milestone(MilestoneCreate.model_validate(milestone().model_dump(include={"id", "title", "description", "target_earliest_date", "target_latest_date", "timing_mode", "governed_phase_id"})))
    first = SQLiteRelocationPlanRepository(path).get_plan(evaluation_date=TODAY)
    second = SQLiteRelocationPlanRepository(path).get_plan(evaluation_date=TODAY)
    assert first == second
    assert first.tasks[0].expected_elapsed_min_days is None
    with pytest.raises(RelocationPlanError, match="already governed"):
        repository.create_milestone(MilestoneCreate.model_validate(milestone(id="other", title="Other").model_dump(include={"id", "title", "description", "target_earliest_date", "target_latest_date", "timing_mode", "governed_phase_id"})))
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM milestones").fetchone()[0] == 1


def test_injected_migration_failure_rolls_back_and_partial_schema_fails_closed(tmp_path, monkeypatch) -> None:
    path = tmp_path / "rollback.db"
    monkeypatch.setenv("GOTIME_INJECT_MILESTONE_TIMING_MIGRATION_FAILURE", "1")
    with pytest.raises(RelocationPlanError, match="Injected"):
        SQLiteRelocationPlanRepository(path)
    monkeypatch.delenv("GOTIME_INJECT_MILESTONE_TIMING_MIGRATION_FAILURE")
    with sqlite3.connect(path) as connection:
        task_columns = {row[1] for row in connection.execute("PRAGMA table_info(tasks)")}
        assert "expected_elapsed_min_days" not in task_columns
        assert connection.execute("SELECT 1 FROM sqlite_master WHERE name='milestone_governed_phases'").fetchone() is None
    SQLiteRelocationPlanRepository(path)
    with sqlite3.connect(path) as connection:
        connection.execute("DROP TABLE milestone_governed_phases")
    with pytest.raises(RelocationPlanError, match="failed closed"):
        SQLiteRelocationPlanRepository(path)


def test_no_scope_achieved_pressure_and_recommendation_frontier() -> None:
    open_task = task("open")
    no_scope = analyze_fixed_milestone(milestone(governed_phase_id=None), tasks=(open_task,), evaluation_date=TODAY)
    assert no_scope and no_scope.status == "no_work_linked"
    achieved = milestone(achieved_at="2026-08-29T00:00:00+00:00", status="achieved")
    from app.relocation_plan_models import Phase, RelocationPlan
    pending_plan = RelocationPlan(id="plan", title="Plan", phases=(Phase(id="prepare", title="Prepare", position=1),), tasks=(open_task,), milestones=(milestone().model_copy(update={"timing": analyze_fixed_milestone(milestone(), tasks=(open_task,), evaluation_date=date(2026, 9, 9))}),))
    result = recommend_relocation_task(pending_plan, today=date(2026, 9, 9))
    assert any(signal.kind == "milestone_timing" for signal in result.signals)
    achieved_plan = pending_plan.model_copy(update={"milestones": (achieved.model_copy(update={"timing": analyze_fixed_milestone(achieved, tasks=(open_task,), evaluation_date=date(2026, 9, 9))}),)})
    assert all(signal.kind != "milestone_timing" for signal in recommend_relocation_task(achieved_plan, today=date(2026, 9, 9)).signals)
