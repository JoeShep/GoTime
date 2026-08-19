import asyncio
import sqlite3
from pathlib import Path

from httpx import ASGITransport, AsyncClient

from app.main import create_app
from app.relocation_plan_models import (
    DecisionCreate,
    DecisionOptionFields,
    DecisionUpdate,
    MilestoneCreate,
    MilestoneUpdate,
)
from app.relocation_plan_repository import (
    InvalidDecisionError,
    SQLiteRelocationPlanRepository,
)


def milestone(**changes: object) -> MilestoneCreate:
    values = {
        "id": "start-selling-home",
        "title": "Start selling our home",
        "description": "Selected buyer-seeking channels are active.",
        "target_earliest_date": "2027-01-02",
        "target_latest_date": None,
    }
    values.update(changes)
    return MilestoneCreate.model_validate(values)


def decision(**changes: object) -> DecisionCreate:
    values = {
        "id": "select-sale-strategy",
        "title": "Select the initial home-sale strategy",
        "description": "Compare credible routes.",
        "milestone_id": "start-selling-home",
        "options": [
            {"id": "as-is", "title": "Public listing as-is"},
            {"id": "builder", "title": "Builder outreach"},
        ],
    }
    values.update(changes)
    return DecisionCreate.model_validate(values)


def test_empty_and_repeated_startup_create_idempotent_foundation(tmp_path) -> None:
    path = tmp_path / "gotime.db"
    first = SQLiteRelocationPlanRepository(path).get_plan()
    second = SQLiteRelocationPlanRepository(path).get_plan()

    assert first.milestones == second.milestones == ()
    assert first.decisions == second.decisions == ()
    with sqlite3.connect(path) as connection:
        tables = {row[0] for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )}
        indexes = {row[0] for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'index'"
        )}
    assert {"milestones", "decisions", "decision_options"} <= tables
    assert {
        "idx_milestones_plan_id", "idx_decisions_plan_id",
        "idx_decisions_milestone_id",
    } <= indexes


def test_current_normalized_schema_is_preserved_during_migration(tmp_path) -> None:
    path = tmp_path / "gotime.db"
    SQLiteRelocationPlanRepository(path)
    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA foreign_keys = OFF")
        connection.execute("DROP TABLE decision_options")
        connection.execute("DROP TABLE decisions")
        connection.execute("DROP TABLE milestones")
        connection.execute(
            "INSERT INTO tasks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("preserved", "family-relocation-plan", "prepare", "Preserved", None,
             "not_started", None, None, "medium"),
        )
        connection.execute(
            "INSERT INTO task_categories VALUES (?, ?)", ("preserved", "housing")
        )

    plan = SQLiteRelocationPlanRepository(path).get_plan()
    assert [task.id for task in plan.tasks] == ["preserved"]
    assert plan.tasks[0].categories == ("housing",)
    assert plan.milestones == ()
    assert plan.decisions == ()


def test_milestone_crud_target_validation_and_explicit_achievement(tmp_path) -> None:
    repository = SQLiteRelocationPlanRepository(tmp_path / "gotime.db")
    created = repository.create_milestone(milestone())
    item = created.milestones[0]
    assert item.status == "pending"
    assert item.target_earliest_date.isoformat() == "2027-01-02"
    assert item.target_latest_date is None

    achieved = repository.set_milestone_achievement(item.id, True).milestones[0]
    assert achieved.status == "achieved"
    assert achieved.achieved_at is not None
    reopened = repository.set_milestone_achievement(item.id, False).milestones[0]
    assert reopened.status == "pending"
    assert reopened.achieved_at is None

    updated = repository.update_milestone(
        item.id,
        MilestoneUpdate.model_validate({
            "title": "Start selling our home",
            "description": None,
            "target_earliest_date": "2027-01-05",
            "target_latest_date": "2027-01-05",
        }),
    ).milestones[0]
    assert updated.target_latest_date == updated.target_earliest_date


def test_decision_options_are_ordered_and_selection_is_user_controlled(tmp_path) -> None:
    repository = SQLiteRelocationPlanRepository(tmp_path / "gotime.db")
    repository.create_milestone(milestone())
    created = repository.create_decision(decision()).decisions[0]
    assert [option.id for option in created.options] == ["as-is", "builder"]
    assert created.status == "unresolved"

    selected = repository.select_decision_option(created.id, "builder").decisions[0]
    assert selected.status == "resolved"
    assert selected.selected_option_id == "builder"
    revised = repository.select_decision_option(created.id, "as-is").decisions[0]
    assert revised.selected_option_id == "as-is"
    unresolved = repository.select_decision_option(created.id, None).decisions[0]
    assert unresolved.status == "unresolved"

    reordered = DecisionUpdate.model_validate({
        "title": created.title,
        "description": created.description,
        "milestone_id": created.milestone_id,
        "options": [option.model_dump() for option in reversed(created.options)],
    })
    result = repository.update_decision(created.id, reordered).decisions[0]
    assert [option.id for option in result.options] == ["builder", "as-is"]


def test_decision_rejects_unknown_milestone_and_foreign_option(tmp_path) -> None:
    repository = SQLiteRelocationPlanRepository(tmp_path / "gotime.db")
    try:
        repository.create_decision(decision())
    except InvalidDecisionError:
        pass
    else:
        raise AssertionError("Unknown Milestone should be rejected")

    repository.create_milestone(milestone())
    repository.create_decision(decision())
    try:
        repository.select_decision_option("select-sale-strategy", "unknown")
    except InvalidDecisionError:
        pass
    else:
        raise AssertionError("Foreign option should be rejected")


async def api_request(path: Path, method: str, endpoint: str, body: dict) -> tuple[int, dict]:
    app = create_app(path)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.request(method, endpoint, json=body)
    return response.status_code, response.json()


def test_foundation_endpoints_and_validation(tmp_path) -> None:
    path = tmp_path / "gotime.db"
    status, body = asyncio.run(api_request(
        path, "POST", "/api/relocation-plan/milestones", milestone().model_dump(mode="json")
    ))
    assert status == 201
    assert body["milestones"][0]["status"] == "pending"

    invalid = milestone(target_earliest_date="2027-01-10", target_latest_date=None).model_dump(mode="json")
    invalid["target_earliest_date"] = None
    invalid["target_latest_date"] = "2027-01-10"
    status, _ = asyncio.run(api_request(path, "POST", "/api/relocation-plan/milestones", invalid))
    assert status == 422

    status, body = asyncio.run(api_request(
        path, "POST", "/api/relocation-plan/decisions", decision().model_dump(mode="json")
    ))
    assert status == 201
    assert body["decisions"][0]["selected_option_id"] is None
    status, body = asyncio.run(api_request(
        path, "PATCH", "/api/relocation-plan/decisions/select-sale-strategy/selection",
        {"selected_option_id": "builder"},
    ))
    assert status == 200
    assert body["decisions"][0]["selected_option_id"] == "builder"
    status, body = asyncio.run(api_request(
        path, "PATCH", "/api/relocation-plan/milestones/start-selling-home/achievement",
        {"achieved": True},
    ))
    assert status == 200
    assert body["milestones"][0]["status"] == "achieved"
