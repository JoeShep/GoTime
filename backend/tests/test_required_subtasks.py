from __future__ import annotations

import pytest

from app.relocation_plan_models import TaskCreate, TaskStatus, TaskUpdate
from app.relocation_plan_recommendation import recommend_relocation_task
from app.relocation_plan_repository import (
    InvalidHierarchyError,
    ParentChangeConfirmationRequired,
    SQLiteRelocationPlanRepository,
)


def task(task_id: str, **changes: object) -> TaskCreate:
    values: dict[str, object] = {
        "id": task_id, "title": task_id.replace("-", " ").title(),
        "description": None, "phase_id": "prepare", "categories": (),
        "status": "not_started", "assignees": (), "start_date": None,
        "due_date": None, "priority": "medium", "dependency_task_ids": (),
        "parent_task_id": None, "subtask_position": None,
    }
    values.update(changes)
    return TaskCreate.model_validate(values)


def update(value, **changes: object) -> TaskUpdate:
    values = value.model_dump(exclude={"id", "blocked", "stored_status", "automatic_status", "manual_status_override", "is_parent", "subtask_count", "completed_subtask_count"})
    values.update(changes)
    return TaskUpdate.model_validate(values)


def by_id(plan, task_id: str):
    return next(item for item in plan.tasks if item.id == task_id)


def test_additive_migration_creates_no_relationships(tmp_path) -> None:
    repository = SQLiteRelocationPlanRepository(tmp_path / "plan.db")
    repository.create_task(task("ordinary"))
    reopened = SQLiteRelocationPlanRepository(tmp_path / "plan.db")
    assert by_id(reopened.get_plan(), "ordinary").parent_task_id is None


def test_parent_status_is_derived_reversible_and_parent_is_not_recommended(tmp_path) -> None:
    repository = SQLiteRelocationPlanRepository(tmp_path / "plan.db")
    repository.create_task(task("parent", priority="critical"))
    repository.create_task(task("first", parent_task_id="parent", subtask_position=1))
    plan = repository.create_task(task("second", parent_task_id="parent", subtask_position=2))
    assert by_id(plan, "parent").status is TaskStatus.NOT_STARTED
    plan = repository.update_task_status("first", TaskStatus.IN_PROGRESS)
    assert by_id(plan, "parent").status is TaskStatus.IN_PROGRESS
    repository.update_task_status("first", TaskStatus.COMPLETED)
    plan = repository.update_task_status("second", TaskStatus.COMPLETED)
    assert by_id(plan, "parent").status is TaskStatus.COMPLETED
    plan = repository.update_task_status("first", TaskStatus.NOT_STARTED)
    assert by_id(plan, "parent").status is TaskStatus.IN_PROGRESS
    assert recommend_relocation_task(plan).task_id == "first"


def test_manual_override_survives_children_and_can_return_to_automatic(tmp_path) -> None:
    repository = SQLiteRelocationPlanRepository(tmp_path / "plan.db")
    repository.create_task(task("parent"))
    repository.create_task(task("child", parent_task_id="parent"))
    with pytest.raises(ParentChangeConfirmationRequired):
        repository.update_task_status("parent", TaskStatus.COMPLETED)
    plan = repository.update_task_status("parent", TaskStatus.COMPLETED, confirm_manual_override=True)
    assert by_id(plan, "parent").manual_status_override is TaskStatus.COMPLETED
    plan = repository.update_task_status("child", TaskStatus.IN_PROGRESS)
    assert by_id(plan, "parent").status is TaskStatus.COMPLETED
    plan = repository.return_parent_to_automatic_status("parent")
    assert by_id(plan, "parent").status is TaskStatus.IN_PROGRESS
    assert by_id(plan, "parent").manual_status_override is None


def test_hierarchy_is_one_level_same_phase_and_parent_move_is_confirmed(tmp_path) -> None:
    repository = SQLiteRelocationPlanRepository(tmp_path / "plan.db")
    repository.create_task(task("parent"))
    repository.create_task(task("child", parent_task_id="parent"))
    with pytest.raises(InvalidHierarchyError):
        repository.create_task(task("grandchild", parent_task_id="child"))
    with pytest.raises(InvalidHierarchyError):
        repository.update_task("child", update(by_id(repository.get_plan(), "child"), phase_id="move"))
    parent = by_id(repository.get_plan(), "parent")
    with pytest.raises(ParentChangeConfirmationRequired):
        repository.update_task("parent", update(parent, phase_id="move"))
    plan = repository.update_task("parent", update(parent, phase_id="move", confirm_parent_phase_move=True))
    assert by_id(plan, "parent").phase_id == by_id(plan, "child").phase_id == "move"


def test_parent_dependencies_block_children_and_effective_parent_controls_downstream(tmp_path) -> None:
    repository = SQLiteRelocationPlanRepository(tmp_path / "plan.db")
    repository.create_task(task("prerequisite"))
    repository.create_task(task("parent", dependency_task_ids=("prerequisite",)))
    plan = repository.create_task(task("child", parent_task_id="parent"))
    assert by_id(plan, "child").blocked is True
    repository.update_task_status("prerequisite", TaskStatus.COMPLETED)
    downstream = repository.create_task(task("downstream", dependency_task_ids=("parent",)))
    assert by_id(downstream, "downstream").blocked is True
    repository.update_task_status("child", TaskStatus.COMPLETED)
    assert by_id(repository.get_plan(), "downstream").blocked is False


def test_detaching_final_child_preserves_effective_parent_status(tmp_path) -> None:
    repository = SQLiteRelocationPlanRepository(tmp_path / "plan.db")
    repository.create_task(task("parent"))
    repository.create_task(task("child", parent_task_id="parent", status="in_progress"))
    child = by_id(repository.get_plan(), "child")
    plan = repository.update_task("child", update(child, parent_task_id=None, subtask_position=None))
    parent = by_id(plan, "parent")
    assert parent.is_parent is False
    assert parent.status is TaskStatus.IN_PROGRESS
