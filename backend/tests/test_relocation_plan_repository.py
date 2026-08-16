import sqlite3

import pytest

from app.relocation_plan_models import TaskCreate, TaskPriority, TaskStatus, TaskUpdate
from app.relocation_plan_repository import (
    DependencyCycleError,
    InvalidDependencyError,
    InvalidPhaseError,
    SQLiteRelocationPlanRepository,
)


def task(task_id: str, **changes: object) -> TaskCreate:
    values: dict[str, object] = {
        "id": task_id,
        "title": task_id.replace("-", " ").title(),
        "description": None,
        "phase_id": "prepare",
        "category": "logistics",
        "status": "not_started",
        "assignees": ("Joe",),
        "start_date": None,
        "due_date": None,
        "priority": "medium",
        "dependency_task_ids": (),
    }
    values.update(changes)
    return TaskCreate.model_validate(values)


def test_plan_and_tasks_survive_repository_reconstruction(tmp_path) -> None:
    database_path = tmp_path / "gotime.db"
    repository = SQLiteRelocationPlanRepository(database_path)
    repository.create_task(
        task(
            "book-movers",
            description="Compare and book the moving company.",
            assignees=("Joe", "Sarah"),
            priority="high",
            start_date="2026-09-01",
            due_date="2026-09-15",
        )
    )

    recovered = SQLiteRelocationPlanRepository(database_path).get_plan()

    assert recovered.id == "family-relocation-plan"
    assert [phase.id for phase in recovered.phases] == [
        "decide",
        "prepare",
        "move",
        "settle",
    ]
    assert len(recovered.tasks) == 1
    assert recovered.tasks[0].title == "Book Movers"
    assert recovered.tasks[0].assignees == ("Joe", "Sarah")
    assert recovered.tasks[0].priority is TaskPriority.HIGH
    assert recovered.tasks[0].due_date.isoformat() == "2026-09-15"


def test_completion_and_reopening_rederive_blocking_without_deleting_dependency(
    tmp_path,
) -> None:
    repository = SQLiteRelocationPlanRepository(tmp_path / "gotime.db")
    repository.create_task(task("choose-mover"))
    plan = repository.create_task(
        task("pay-deposit", dependency_task_ids=("choose-mover",))
    )

    assert next(item for item in plan.tasks if item.id == "pay-deposit").blocked is True

    completed = repository.update_task_status("choose-mover", TaskStatus.COMPLETED)

    dependent = next(item for item in completed.tasks if item.id == "pay-deposit")
    assert dependent.blocked is False
    assert dependent.dependency_task_ids == ("choose-mover",)

    reopened = repository.update_task_status("choose-mover", TaskStatus.IN_PROGRESS)

    dependent = next(item for item in reopened.tasks if item.id == "pay-deposit")
    assert dependent.blocked is True
    assert dependent.dependency_task_ids == ("choose-mover",)


def test_dependency_chain_is_derived_from_direct_relationships(tmp_path) -> None:
    repository = SQLiteRelocationPlanRepository(tmp_path / "gotime.db")
    repository.create_task(task("c"))
    repository.create_task(task("b", dependency_task_ids=("c",)))
    initial = repository.create_task(task("a", dependency_task_ids=("b",)))

    assert next(item for item in initial.tasks if item.id == "b").blocked is True
    assert next(item for item in initial.tasks if item.id == "a").blocked is True

    after_c = repository.update_task_status("c", TaskStatus.COMPLETED)
    assert next(item for item in after_c.tasks if item.id == "b").blocked is False
    assert next(item for item in after_c.tasks if item.id == "a").blocked is True

    after_b = repository.update_task_status("b", TaskStatus.COMPLETED)
    assert next(item for item in after_b.tasks if item.id == "a").blocked is False

    reopened_b = repository.update_task_status("b", TaskStatus.NOT_STARTED)
    task_a = next(item for item in reopened_b.tasks if item.id == "a")
    task_b = next(item for item in reopened_b.tasks if item.id == "b")
    assert task_a.blocked is True
    assert task_a.dependency_task_ids == ("b",)
    assert task_b.dependency_task_ids == ("c",)


def test_completed_tasks_cannot_be_introduced_as_dependencies(tmp_path) -> None:
    repository = SQLiteRelocationPlanRepository(tmp_path / "gotime.db")
    repository.create_task(task("completed", status="completed"))

    with pytest.raises(InvalidDependencyError, match="Completed task.*completed"):
        repository.create_task(task("new", dependency_task_ids=("completed",)))

    repository.create_task(task("existing"))
    with pytest.raises(InvalidDependencyError, match="Completed task.*completed"):
        repository.update_task(
            "existing",
            TaskUpdate.model_validate(
                {
                    **task("existing").model_dump(exclude={"id"}),
                    "dependency_task_ids": ("completed",),
                }
            ),
        )


def test_existing_completed_dependency_can_remain_or_be_removed_but_not_readded(tmp_path) -> None:
    repository = SQLiteRelocationPlanRepository(tmp_path / "gotime.db")
    repository.create_task(task("prerequisite"))
    repository.create_task(task("dependent", dependency_task_ids=("prerequisite",)))
    repository.update_task_status("prerequisite", TaskStatus.COMPLETED)
    original = task("dependent").model_dump(exclude={"id"})

    retained = repository.update_task(
        "dependent",
        TaskUpdate.model_validate(
            {**original, "dependency_task_ids": ("prerequisite",)}
        ),
    )
    retained_dependency_ids = next(
        item for item in retained.tasks if item.id == "dependent"
    ).dependency_task_ids
    assert retained_dependency_ids == ("prerequisite",)

    removed = repository.update_task(
        "dependent",
        TaskUpdate.model_validate({**original, "dependency_task_ids": ()}),
    )
    removed_dependency_ids = next(
        item for item in removed.tasks if item.id == "dependent"
    ).dependency_task_ids
    assert removed_dependency_ids == ()

    with pytest.raises(InvalidDependencyError, match="Completed task.*prerequisite"):
        repository.update_task(
            "dependent",
            TaskUpdate.model_validate(
                {**original, "dependency_task_ids": ("prerequisite",)}
            ),
        )


def test_completed_task_is_not_blocked_by_an_incomplete_dependency(tmp_path) -> None:
    repository = SQLiteRelocationPlanRepository(tmp_path / "gotime.db")
    repository.create_task(task("choose-mover"))
    plan = repository.create_task(
        task(
            "pay-deposit",
            status="completed",
            dependency_task_ids=("choose-mover",),
        )
    )

    assert next(item for item in plan.tasks if item.id == "pay-deposit").blocked is False


def test_missing_phase_and_dependency_are_rejected(tmp_path) -> None:
    repository = SQLiteRelocationPlanRepository(tmp_path / "gotime.db")

    with pytest.raises(InvalidPhaseError, match="Phase 'unknown'"):
        repository.create_task(task("bad-phase", phase_id="unknown"))
    with pytest.raises(InvalidDependencyError, match="missing-task"):
        repository.create_task(
            task("bad-dependency", dependency_task_ids=("missing-task",))
        )


def test_self_dependency_is_rejected_by_the_bounded_model() -> None:
    with pytest.raises(ValueError, match="cannot depend on itself"):
        task("circular", dependency_task_ids=("circular",))


def test_cycle_is_rejected_without_mutating_the_existing_graph(tmp_path) -> None:
    repository = SQLiteRelocationPlanRepository(tmp_path / "gotime.db")
    repository.create_task(task("first"))
    repository.create_task(task("second", dependency_task_ids=("first",)))
    first = next(item for item in repository.get_plan().tasks if item.id == "first")

    with pytest.raises(DependencyCycleError, match="cannot contain a cycle"):
        repository.update_task(
            "first",
            TaskUpdate.model_validate(
                {
                    **first.model_dump(exclude={"id", "blocked"}),
                    "dependency_task_ids": ("second",),
                }
            ),
        )

    unchanged = next(item for item in repository.get_plan().tasks if item.id == "first")
    assert unchanged.dependency_task_ids == ()


def test_sqlite_schema_rejects_invalid_status_and_priority(tmp_path) -> None:
    database_path = tmp_path / "gotime.db"
    repository = SQLiteRelocationPlanRepository(database_path)
    repository.create_task(task("valid-task"))

    with sqlite3.connect(database_path) as connection:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "UPDATE tasks SET status = 'invented' WHERE id = 'valid-task'"
            )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "UPDATE tasks SET priority = 'urgent-ish' WHERE id = 'valid-task'"
            )
