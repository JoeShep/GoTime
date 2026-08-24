import asyncio
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app
from app.relocation_plan_models import (
    DecisionCreate,
    DecisionUpdate,
    MilestoneCreate,
    MilestoneUpdate,
    TaskCreate,
    TaskUpdate,
)
from app.relocation_plan_repository import (
    DuplicateDecisionTitleError,
    DuplicateMilestoneTitleError,
    DuplicateTaskTitleError,
    SQLiteRelocationPlanRepository,
)


def task(task_id: str, title: str, **changes: object) -> TaskCreate:
    values = {
        "id": task_id,
        "title": title,
        "description": None,
        "phase_id": "prepare",
        "categories": (),
        "status": "not_started",
        "assignees": (),
        "start_date": None,
        "due_date": None,
        "priority": "medium",
        "dependency_task_ids": (),
    }
    values.update(changes)
    return TaskCreate.model_validate(values)


def task_update(item: TaskCreate, **changes: object) -> TaskUpdate:
    values = item.model_dump(exclude={"id"})
    values.update(changes)
    return TaskUpdate.model_validate(values)


def milestone(item_id: str, title: str) -> MilestoneCreate:
    return MilestoneCreate.model_validate({
        "id": item_id, "title": title, "description": None,
        "target_earliest_date": None, "target_latest_date": None,
    })


def milestone_update(item: MilestoneCreate, **changes: object) -> MilestoneUpdate:
    values = item.model_dump(exclude={"id"})
    values.update(changes)
    return MilestoneUpdate.model_validate(values)


def decision(item_id: str, title: str, milestone_id: str) -> DecisionCreate:
    return DecisionCreate.model_validate({
        "id": item_id, "title": title, "description": None,
        "milestone_id": milestone_id,
        "options": [
            {"id": f"{item_id}-a", "title": "First"},
            {"id": f"{item_id}-b", "title": "Second"},
        ],
    })


def decision_update(item: DecisionCreate, **changes: object) -> DecisionUpdate:
    values = item.model_dump(exclude={"id"})
    values.update(changes)
    return DecisionUpdate.model_validate(values)


@pytest.mark.parametrize(
    ("second_title", "changes"),
    [
        ("Wash windows", {}),
        ("wash windows", {"phase_id": "move"}),
        ("WASH WINDOWS", {"status": "completed"}),
        ("  Wash   windows  ", {}),
    ],
)
def test_task_creation_rejects_plan_wide_canonical_duplicates(
    tmp_path, second_title, changes
) -> None:
    repository = SQLiteRelocationPlanRepository(tmp_path / "gotime.db")
    repository.create_task(task("first", "Wash windows"))

    with pytest.raises(
        DuplicateTaskTitleError,
        match="A task with this title already exists in this plan.",
    ):
        repository.create_task(task("second", second_title, **changes))

    assert [item.id for item in repository.get_plan().tasks] == ["first"]


def test_task_rename_rejects_duplicate_but_self_equivalent_edits_are_valid(tmp_path) -> None:
    repository = SQLiteRelocationPlanRepository(tmp_path / "gotime.db")
    first = task("first", "Wash windows", description="Keep me")
    second = task("second", "Pack boxes")
    repository.create_task(first)
    repository.create_task(second)

    with pytest.raises(DuplicateTaskTitleError):
        repository.update_task("second", task_update(second, title=" wash   WINDOWS "))
    unchanged = next(item for item in repository.get_plan().tasks if item.id == "second")
    assert unchanged.title == "Pack boxes"

    canonical_edit = repository.update_task(
        "first", task_update(first, title="  WASH   WINDOWS  ", description="Updated")
    )
    saved = next(item for item in canonical_edit.tasks if item.id == "first")
    assert saved.title == "WASH   WINDOWS"
    assert saved.description == "Updated"


def test_legacy_task_duplicates_allow_unchanged_canonical_edit(tmp_path) -> None:
    path = tmp_path / "gotime.db"
    repository = SQLiteRelocationPlanRepository(path)
    original = task("first", "Same title")
    repository.create_task(original)
    with sqlite3.connect(path) as connection:
        connection.execute(
            "INSERT INTO tasks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("legacy", "family-relocation-plan", "move", "same  TITLE", None,
             "completed", None, None, "medium"),
        )

    result = repository.update_task(
        "first", task_update(original, title=" SAME   TITLE ", description="Allowed")
    )
    assert next(item for item in result.tasks if item.id == "first").description == "Allowed"


def test_same_task_title_in_different_plans_is_allowed(tmp_path) -> None:
    path = tmp_path / "gotime.db"
    repository = SQLiteRelocationPlanRepository(path)
    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("INSERT INTO relocation_plans VALUES (?, ?)", ("other", "Other"))
        connection.execute("INSERT INTO phases VALUES (?, ?, ?, ?)", ("other-phase", "other", "Other", 10))
        connection.execute(
            "INSERT INTO tasks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("other-task", "other", "other-phase", "Wash windows", None,
             "not_started", None, None, "medium"),
        )

    result = repository.create_task(task("default-task", "WASH WINDOWS"))
    assert any(item.id == "default-task" for item in result.tasks)


def test_milestone_and_decision_titles_are_unique_within_type_only(tmp_path) -> None:
    repository = SQLiteRelocationPlanRepository(tmp_path / "gotime.db")
    first_milestone = milestone("first-milestone", "Start selling home")
    second_milestone = milestone("second-milestone", "Choose strategy")
    repository.create_milestone(first_milestone)
    repository.create_milestone(second_milestone)
    with pytest.raises(DuplicateMilestoneTitleError):
        repository.create_milestone(milestone("third-milestone", " start  SELLING home "))
    with pytest.raises(DuplicateMilestoneTitleError):
        repository.update_milestone(
            "second-milestone",
            milestone_update(second_milestone, title="START SELLING HOME"),
        )
    repository.update_milestone(
        "first-milestone", milestone_update(first_milestone, title=" START  SELLING HOME ")
    )

    first_decision = decision("first-decision", "Choose route", "first-milestone")
    second_decision = decision("second-decision", "Choose timing", "first-milestone")
    repository.create_decision(first_decision)
    repository.create_decision(second_decision)
    with pytest.raises(DuplicateDecisionTitleError):
        repository.create_decision(decision("third-decision", " choose  ROUTE ", "first-milestone"))
    with pytest.raises(DuplicateDecisionTitleError):
        repository.update_decision(
            "second-decision", decision_update(second_decision, title="CHOOSE ROUTE")
        )
    repository.update_decision(
        "first-decision", decision_update(first_decision, title=" CHOOSE  ROUTE ")
    )

    repository.create_task(task("cross-type", "Start selling home"))
    repository.create_decision(
        decision("cross-type-decision", "Start selling home", "first-milestone")
    )


def test_duplicate_api_response_is_stable_and_machine_readable(tmp_path) -> None:
    path = tmp_path / "gotime.db"
    repository = SQLiteRelocationPlanRepository(path)
    repository.create_task(task("first", "Wash windows"))

    async def send() -> tuple[int, dict]:
        app = create_app(path)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/relocation-plan/tasks",
                json=task("second", " wash  WINDOWS ").model_dump(mode="json"),
            )
        return response.status_code, response.json()

    status, body = asyncio.run(send())
    assert status == 409
    assert body == {"detail": {
        "code": "duplicate_task_title",
        "message": "A task with this title already exists in this plan.",
    }}


def test_concurrent_task_creation_serializes_title_check_and_write(tmp_path) -> None:
    path = tmp_path / "gotime.db"
    SQLiteRelocationPlanRepository(path)

    def create(item_id: str) -> str:
        try:
            SQLiteRelocationPlanRepository(path).create_task(
                task(item_id, "Concurrent title")
            )
            return "created"
        except DuplicateTaskTitleError:
            return "duplicate"

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(create, ("first", "second")))

    assert sorted(outcomes) == ["created", "duplicate"]
    assert len(SQLiteRelocationPlanRepository(path).get_plan().tasks) == 1
