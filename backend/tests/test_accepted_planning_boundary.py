from __future__ import annotations

import asyncio

from httpx import ASGITransport, AsyncClient

from app.main import create_app
from app.relocation_plan_models import DecisionCreate, MilestoneCreate, TaskCreate
from app.relocation_plan_repository import SQLiteRelocationPlanRepository


def test_accepted_planning_is_available_while_experiments_remain_off(
    tmp_path, monkeypatch,
) -> None:
    monkeypatch.setenv("GOTIME_ENABLE_EXPERIMENTS", "false")
    path = tmp_path / "gotime.db"
    repository = SQLiteRelocationPlanRepository(path)
    repository.create_task(TaskCreate.model_validate({
        "id": "parent", "title": "Prepare the decision", "phase_id": "prepare",
        "categories": ["housing"], "status": "not_started", "assignees": ["Anne", "Joe"],
        "priority": "high", "dependency_task_ids": [],
    }))
    repository.create_task(TaskCreate.model_validate({
        "id": "child", "title": "Gather evidence", "phase_id": "prepare",
        "categories": ["housing"], "status": "not_started", "assignees": ["Anne", "Joe"],
        "priority": "medium", "dependency_task_ids": [], "parent_task_id": "parent",
        "subtask_position": 0,
    }))
    repository.create_milestone(MilestoneCreate.model_validate({
        "id": "market-home", "title": "Market the home",
        "target_earliest_date": "2027-01-04", "target_latest_date": "2027-01-15",
    }))
    repository.create_decision(DecisionCreate.model_validate({
        "id": "choose-marketing", "title": "Choose marketing", "milestone_id": "market-home",
        "options": [{"id": "public", "title": "List publicly"}, {"id": "both", "title": "Pursue both paths"}],
        "preparation_task_ids": ["parent"],
    }))

    async def exercise() -> tuple[object, object]:
        async with AsyncClient(
            transport=ASGITransport(app=create_app(path)), base_url="http://testserver",
        ) as client:
            plan = await client.get("/api/relocation-plan")
            recommendation = await client.get("/api/relocation-plan/recommendation")
            moving_service = await client.get(
                "/api/experiments/moving-service-question?scenario=storage_unknown"
            )
            prototype = await client.get("/api/recommendations/primary")
        assert plan.status_code == recommendation.status_code == 200
        assert moving_service.status_code == prototype.status_code == 404
        return plan.json(), recommendation.json()

    plan, recommendation = asyncio.run(exercise())
    assert plan["milestones"][0]["title"] == "Market the home"
    assert plan["decisions"][0]["preparation_readiness"] == "preparation_incomplete"
    tasks = {task["id"]: task for task in plan["tasks"]}
    assert tasks["parent"]["automatic_status"] == "not_started"
    assert tasks["child"]["parent_task_id"] == "parent"
    assert recommendation["task_id"] == "child"
    assert recommendation["signals"][0]["kind"] == "inherited_decision_preparation"
