from datetime import date

from app.relocation_plan_models import Decision, Phase, RelocationPlan, Task
from app.relocation_plan_recommendation import recommend_relocation_task


TODAY = date(2026, 8, 27)
PHASE = Phase(id="prepare", title="Prepare", position=10)


def task(task_id: str, **changes: object) -> Task:
    values: dict[str, object] = {
        "id": task_id, "title": task_id.replace("-", " ").title(),
        "description": None, "phase_id": "prepare", "categories": ("logistics",),
        "status": "not_started", "assignees": (), "start_date": None,
        "due_date": None, "priority": "medium", "dependency_task_ids": (),
        "blocked": False,
    }
    values.update(changes)
    return Task(**values)


def decision(decision_id: str, preparation: tuple[str, ...], **changes: object) -> Decision:
    values: dict[str, object] = {
        "id": decision_id, "title": decision_id.replace("-", " ").title(),
        "description": None, "milestone_id": "milestone", "options": (
            {"id": f"{decision_id}-a", "title": "A", "description": None},
            {"id": f"{decision_id}-b", "title": "B", "description": None},
        ), "status": "unresolved", "selected_option_id": None,
        "preparation_task_ids": preparation,
        "preparation_readiness": "preparation_incomplete",
        "completed_preparation_task_count": 0,
    }
    values.update(changes)
    return Decision(**values)


def plan(tasks: tuple[Task, ...], decisions: tuple[Decision, ...]) -> RelocationPlan:
    return RelocationPlan(id="plan", title="Plan", phases=(PHASE,), tasks=tasks, decisions=decisions)


def test_readiness_states_and_resolved_transitions_are_explicit() -> None:
    work = task("research")
    no_tracking = recommend_relocation_task(plan((work,), (decision("choose", (), preparation_readiness="no_preparation_tracked"),)), today=TODAY)
    incomplete = recommend_relocation_task(plan((work,), (decision("choose", (work.id,)),)), today=TODAY)
    ready = recommend_relocation_task(plan((task("research", status="completed"),), (decision("choose", (work.id,), preparation_readiness="ready_to_decide", completed_preparation_task_count=1),)), today=TODAY)
    resolved = recommend_relocation_task(plan((work,), (decision("choose", (work.id,), status="resolved", selected_option_id="choose-a"),)), today=TODAY)

    assert no_tracking.signals == ()
    assert incomplete.candidate_type == "task"
    assert incomplete.signals[0].kind == "direct_decision_preparation"
    assert ready.candidate_type == "decision"
    assert ready.decision_id == "choose"
    assert resolved.signals == ()


def test_direct_parent_inherited_and_manual_parent_completion() -> None:
    parent = task("parent", is_parent=True, subtask_count=1, status="in_progress")
    child = task("child", parent_task_id="parent", subtask_position=0)
    inherited = recommend_relocation_task(plan((parent, child), (decision("choose", (parent.id,)),)), today=TODAY)
    complete_parent = task("parent", is_parent=True, subtask_count=1, status="completed", manual_status_override="completed")
    no_boost = recommend_relocation_task(plan((complete_parent, child), (decision("choose", (parent.id,), preparation_readiness="ready_to_decide", completed_preparation_task_count=1),)), today=TODAY)

    assert inherited.task_id == "child"
    assert inherited.signals[0].kind == "inherited_decision_preparation"
    assert inherited.signals[0].parent_task_id == "parent"
    assert no_boost.candidate_type == "decision"
    assert all(item.decision_id != "choose" for item in no_boost.upcoming if item.candidate_type == "task")


def test_deep_and_branching_dependencies_reach_each_actionable_frontier() -> None:
    left = task("left")
    right = task("right")
    middle = task("middle", dependency_task_ids=(left.id, right.id), blocked=True)
    preparation = task("prepare-decision", dependency_task_ids=(middle.id,), blocked=True)
    result = recommend_relocation_task(plan((left, right, middle, preparation), (decision("choose", (preparation.id,)),)), today=TODAY)
    candidates = (result, *result.upcoming)

    assert {item.task_id for item in candidates if item.signals} == {"left", "right"}
    for item in candidates:
        if item.signals:
            assert item.signals[0].kind == "unblocks_decision_preparation"
            assert item.signals[0].blocked_task_id == "prepare-decision"


def test_parent_prerequisite_expands_to_actionable_subtasks() -> None:
    prerequisite = task("prerequisite", is_parent=True, subtask_count=2, status="in_progress")
    first = task("first", parent_task_id=prerequisite.id, subtask_position=0)
    second = task("second", parent_task_id=prerequisite.id, subtask_position=1)
    preparation = task("prepare-decision", dependency_task_ids=(prerequisite.id,), blocked=True)
    result = recommend_relocation_task(plan((prerequisite, first, second, preparation), (decision("choose", (preparation.id,)),)), today=TODAY)

    assert result.task_id in {"first", "second"}
    assert result.task_id != "prerequisite"
    assert result.signals[0].kind == "unblocks_decision_preparation"


def test_inactive_preparation_and_frontier_do_not_create_signals() -> None:
    inactive = task("inactive-preparation", active=False)
    ordinary = task("ordinary")
    result = recommend_relocation_task(plan((inactive, ordinary), (decision("choose", (inactive.id,)),)), today=TODAY)

    assert result.task_id == "ordinary"
    assert result.signals == ()
    assert all(item.task_id != "inactive-preparation" for item in result.upcoming)


def test_multiple_decisions_preserve_context_without_stacking_rank() -> None:
    shared = task("shared")
    ordinary = task("a-ordinary")
    result = recommend_relocation_task(plan((shared, ordinary), (decision("one", (shared.id,)), decision("two", (shared.id,)))), today=TODAY)

    assert result.task_id == "shared"
    assert {signal.decision_id for signal in result.signals} == {"one", "two"}
    assert result.ranking_factors.decision_context_rank == 1


def test_context_precedes_priority_but_strong_date_pressure_wins() -> None:
    signaled = task("signaled")
    critical = task("critical", priority="critical")
    result = recommend_relocation_task(plan((signaled, critical), (decision("choose", (signaled.id,)),)), today=TODAY)
    assert result.task_id == "signaled"

    dated = task("dated", due_date="2026-08-28")
    result = recommend_relocation_task(plan((signaled, dated), (decision("choose", (signaled.id,)),)), today=TODAY)
    assert result.task_id == "dated"

    result = recommend_relocation_task(plan((task("z-task"), task("a-task")), ()), today=TODAY)
    assert result.task_id == "a-task"


def test_downstream_due_date_applies_pressure_without_making_blocked_work_eligible() -> None:
    prerequisite = task("prerequisite")
    preparation = task("preparation", blocked=True, dependency_task_ids=(prerequisite.id,), due_date="2026-08-27")
    ordinary = task("ordinary", due_date="2026-09-30")
    result = recommend_relocation_task(plan((prerequisite, preparation, ordinary), (decision("choose", (preparation.id,)),)), today=TODAY)

    assert result.task_id == "prerequisite"
    assert result.ranking_factors.effective_due_date.isoformat() == "2026-08-27"
    assert result.task_id != "preparation"


def test_response_contract_has_candidate_identity_context_and_upcoming_types() -> None:
    preparation = task("preparation")
    ready_work = task("ready-work", status="completed")
    ready = decision("ready", (ready_work.id,), preparation_readiness="ready_to_decide", completed_preparation_task_count=1)
    result = recommend_relocation_task(plan((preparation, ready_work), (ready, decision("working", (preparation.id,)))), today=TODAY)
    payload = result.model_dump(mode="json")

    assert payload["candidate_type"] in {"task", "decision"}
    assert payload["signals"][0]["decision_id"] in {"ready", "working"}
    assert payload["upcoming"]
    assert {payload["candidate_type"], payload["upcoming"][0]["candidate_type"]} == {"task", "decision"}


def test_recalculation_moves_task_to_decision_and_back_without_stored_state() -> None:
    incomplete = task("preparation")
    linked = decision("choose", (incomplete.id,))
    first = recommend_relocation_task(plan((incomplete,), (linked,)), today=TODAY)
    completed = task("preparation", status="completed")
    second = recommend_relocation_task(plan((completed,), (decision("choose", (completed.id,), preparation_readiness="ready_to_decide", completed_preparation_task_count=1),)), today=TODAY)
    third = recommend_relocation_task(plan((incomplete,), (linked,)), today=TODAY)

    assert (first.candidate_type, second.candidate_type, third.candidate_type) == ("task", "decision", "task")
