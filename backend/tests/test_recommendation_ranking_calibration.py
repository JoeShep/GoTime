from datetime import date

import pytest

from app.relocation_plan_models import Decision, Phase, RelocationPlan, Task
from app.relocation_plan_recommendation import recommend_relocation_task

TODAY = date(2026, 8, 28)
PHASES = (Phase(id="first", title="First", position=10), Phase(id="second", title="Second", position=20))


def task(task_id: str, **changes: object) -> Task:
    values: dict[str, object] = dict(id=task_id, title=task_id.replace("-", " ").title(), description=None,
        phase_id="first", categories=(), status="not_started", assignees=(), start_date=None,
        due_date=None, priority="medium", dependency_task_ids=(), blocked=False)
    values.update(changes)
    return Task(**values)


def decision(preparation: tuple[str, ...], **changes: object) -> Decision:
    values: dict[str, object] = dict(id="decision", title="Choose route", description=None, milestone_id="milestone",
        options=({"id": "a", "title": "A", "description": None}, {"id": "b", "title": "B", "description": None}), status="unresolved", selected_option_id=None,
        preparation_task_ids=preparation, preparation_readiness="preparation_incomplete", completed_preparation_task_count=0)
    values.update(changes)
    return Decision(**values)


def plan(*tasks: Task, decisions: tuple[Decision, ...] = ()) -> RelocationPlan:
    return RelocationPlan(id="plan", title="Plan", phases=PHASES, tasks=tasks, decisions=decisions)


@pytest.mark.parametrize(("days", "expected"), [(-1, "dated"), (0, "dated"), (1, "dated"), (3, "dated"), (4, "dated"), (7, "dated"), (8, "dated"), (30, "dated"), (31, "ordinary")])
def test_due_date_band_boundaries(days: int, expected: str) -> None:
    dated = task("dated", due_date=date.fromordinal(TODAY.toordinal() + days), priority="low")
    ordinary = task("ordinary", priority="medium")
    assert recommend_relocation_task(plan(dated, ordinary), today=TODAY).task_id == expected


def test_future_hold_and_in_progress_override_do_not_mutate_date() -> None:
    held = task("held", start_date="2026-08-29", priority="critical")
    assert recommend_relocation_task(plan(held, task("open")), today=TODAY).task_id == "open"
    started = task("held", start_date="2026-08-29", priority="critical", status="in_progress")
    result = recommend_relocation_task(plan(started, task("open")), today=TODAY)
    assert result.task_id == "held" and result.task_metadata.start_date.isoformat() == "2026-08-29"
    assert recommend_relocation_task(plan(held, task("open")), today=TODAY).task_id == "open"


def test_parent_hold_uses_latest_child_hold_but_does_not_cross_dependencies() -> None:
    parent = task("parent", is_parent=True, subtask_count=2, status="in_progress", start_date="2026-08-30")
    inherited = task("inherited", parent_task_id="parent", subtask_position=0)
    later = task("later", parent_task_id="parent", subtask_position=1, start_date="2026-09-01")
    prerequisite = task("prerequisite")
    held_dependent = task("held-dependent", start_date="2026-09-01", dependency_task_ids=(prerequisite.id,), blocked=True)
    result = recommend_relocation_task(plan(parent, inherited, later, prerequisite, held_dependent), today=TODAY)
    assert result.task_id == "prerequisite"


def test_deadline_propagates_to_deep_and_branching_actionable_frontier_once() -> None:
    left, right = task("left"), task("right")
    middle = task("middle", dependency_task_ids=(left.id, right.id), blocked=True)
    deadline = task("deadline", dependency_task_ids=(middle.id,), blocked=True, due_date=TODAY)
    result = recommend_relocation_task(plan(left, right, middle, deadline, task("urgent-later", due_date="2026-08-29")), today=TODAY)
    items = (result, *result.upcoming)
    assert {item.task_id for item in items[:2]} == {"left", "right"}
    assert all(item.ranking_factors.effective_due_date == TODAY for item in items[:2])


def test_strongest_direct_or_inherited_deadline_is_used_without_stacking() -> None:
    prerequisite = task("prerequisite", due_date="2026-09-04")
    blocked = task("blocked", blocked=True, dependency_task_ids=(prerequisite.id,), due_date="2026-08-30")
    result = recommend_relocation_task(plan(prerequisite, blocked), today=TODAY)
    assert result.ranking_factors.effective_due_date.isoformat() == "2026-08-30"
    assert sum("Needed before" in reason for reason in result.why) == 1


def test_parent_due_pressure_reaches_actionable_children() -> None:
    parent = task("parent", is_parent=True, subtask_count=1, status="in_progress", due_date=TODAY)
    child = task("child", parent_task_id=parent.id, subtask_position=0)
    assert recommend_relocation_task(plan(parent, child, task("ordinary", due_date="2026-08-29")), today=TODAY).task_id == "child"


def test_actual_unlock_requires_the_final_incomplete_prerequisite() -> None:
    useful, other, momentum = task("useful"), task("other"), task("momentum", status="in_progress")
    partially_blocked = task("blocked", blocked=True, dependency_task_ids=(useful.id, other.id))
    assert recommend_relocation_task(plan(useful, other, momentum, partially_blocked), today=TODAY).task_id == "momentum"
    final = task("other", status="completed")
    assert recommend_relocation_task(plan(useful, final, momentum, partially_blocked), today=TODAY).task_id == "useful"


def test_final_child_gets_parent_release_and_final_preparation_consequences() -> None:
    parent = task("parent", is_parent=True, subtask_count=2, status="in_progress")
    done = task("done", status="completed", parent_task_id=parent.id, subtask_position=0)
    final = task("final", parent_task_id=parent.id, subtask_position=1)
    dependent = task("dependent", blocked=True, dependency_task_ids=(parent.id,))
    result = recommend_relocation_task(plan(parent, done, final, dependent, decisions=(decision((parent.id,)),)), today=TODAY)
    assert result.task_id == "final"
    assert "dependent" in result.directly_unblocks_task_ids
    assert any("Final step" in reason for reason in result.why)


def test_ready_resolved_and_reopened_decision_behavior() -> None:
    done = task("done", status="completed")
    ready = decision((done.id,), preparation_readiness="ready_to_decide", completed_preparation_task_count=1)
    assert recommend_relocation_task(plan(done, task("ordinary"), decisions=(ready,)), today=TODAY).candidate_type == "decision"
    resolved = decision((done.id,), preparation_readiness="ready_to_decide", completed_preparation_task_count=1, status="resolved", selected_option_id="a")
    assert recommend_relocation_task(plan(done, task("ordinary"), decisions=(resolved,)), today=TODAY).task_id == "ordinary"
    assert recommend_relocation_task(plan(done, task("ordinary"), decisions=(ready,)), today=TODAY).candidate_type == "decision"


def test_accumulation_priority_phase_and_stable_order() -> None:
    moderate = task("moderate", due_date="2026-09-02", priority="critical", phase_id="second")
    combined = task("combined", status="in_progress", priority="low")
    dependent = task("dependent", blocked=True, dependency_task_ids=(combined.id,))
    result = recommend_relocation_task(plan(moderate, combined, dependent), today=TODAY)
    assert result.task_id == "combined"
    assert recommend_relocation_task(plan(task("low", priority="low"), task("high", priority="high")), today=TODAY).task_id == "high"
    assert recommend_relocation_task(plan(task("z", phase_id="second"), task("a", phase_id="first")), today=TODAY).task_id == "a"
    assert recommend_relocation_task(plan(task("z"), task("a")), today=TODAY).task_id == "a"


def test_reasons_are_concise_and_never_cite_priority_phase_or_availability() -> None:
    candidate = task("candidate", status="in_progress", due_date="2026-09-01", priority="critical")
    result = recommend_relocation_task(plan(candidate), today=TODAY)
    assert len(result.why) <= 2
    assert not any(word in " ".join(result.why).lower() for word in ("priority", "phase", "actionable", "restriction"))
