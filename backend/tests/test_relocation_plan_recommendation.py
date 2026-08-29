import asyncio
from datetime import date

from httpx import ASGITransport, AsyncClient

from app.main import create_app
from app.relocation_plan_models import Phase, RelocationPlan, Task
from app.relocation_plan_recommendation import recommend_relocation_task


PHASES = (
    Phase(id="decide", title="Decide where and how to move", position=10),
    Phase(id="prepare", title="Prepare for the move", position=20),
)
TODAY = date(2026, 8, 13)


def task(task_id: str, **changes: object) -> Task:
    values: dict[str, object] = {
        "id": task_id,
        "title": task_id.replace("-", " ").title(),
        "description": None,
        "phase_id": "prepare",
        "categories": ("logistics",),
        "status": "not_started",
        "assignees": ("Joe",),
        "start_date": None,
        "due_date": None,
        "priority": "medium",
        "dependency_task_ids": (),
        "blocked": False,
    }
    values.update(changes)
    return Task(**values)


def plan(*tasks: Task) -> RelocationPlan:
    return RelocationPlan(
        id="family-relocation-plan",
        title="Relocate the family to Northern California",
        phases=PHASES,
        tasks=tasks,
    )


def test_completed_tasks_are_never_recommended() -> None:
    recommendation = recommend_relocation_task(
        plan(task("completed", status="completed", priority="critical"), task("available")),
        today=TODAY,
    )

    assert recommendation.task_id == "available"


def test_blocked_tasks_are_never_recommended() -> None:
    recommendation = recommend_relocation_task(
        plan(task("blocked", blocked=True, priority="critical"), task("available")),
        today=TODAY,
    )

    assert recommendation.task_id == "available"


def test_future_start_tasks_are_never_recommended() -> None:
    recommendation = recommend_relocation_task(
        plan(
            task("future", start_date="2026-08-14", priority="critical"),
            task("available"),
        ),
        today=TODAY,
    )

    assert recommendation.task_id == "available"


def test_category_assignments_do_not_change_recommendation_order() -> None:
    recommendation = recommend_relocation_task(
        plan(
            task("b-task", categories=()),
            task("a-task", categories=("employment", "housing", "logistics")),
        ),
        today=TODAY,
    )

    assert recommendation.task_id == "a-task"


def test_critical_undated_beats_low_priority_future_dated() -> None:
    recommendation = recommend_relocation_task(
        plan(
            task("low-dated", priority="low", due_date="2026-12-31"),
            task("critical-undated", priority="critical"),
        ),
        today=TODAY,
    )

    assert recommendation.task_id == "critical-undated"


def test_high_priority_undated_beats_medium_priority_distant_dated() -> None:
    recommendation = recommend_relocation_task(
        plan(
            task("medium-distant", priority="medium", due_date="2027-08-13"),
            task("high-undated", priority="high"),
        ),
        today=TODAY,
    )

    assert recommendation.task_id == "high-undated"


def test_earlier_overdue_beats_due_today_regardless_of_priority() -> None:
    recommendation = recommend_relocation_task(
        plan(
            task("overdue-low", priority="low", due_date="2026-08-12"),
            task("critical-today", priority="critical", due_date="2026-08-13"),
        ),
        today=TODAY,
    )

    assert recommendation.task_id == "overdue-low"


def test_overdue_then_earlier_due_date_wins_for_equal_priority() -> None:
    recommendation = recommend_relocation_task(
        plan(
            task("upcoming", priority="high", due_date="2026-08-14"),
            task("later-overdue", priority="high", due_date="2026-08-12"),
            task("earlier-overdue", priority="high", due_date="2026-08-01"),
        ),
        today=TODAY,
    )

    assert recommendation.task_id == "earlier-overdue"
    assert recommendation.ranking_factors is not None
    assert recommendation.ranking_factors.due_state == "overdue"


def test_priority_orders_tasks_with_equivalent_dates() -> None:
    recommendation = recommend_relocation_task(
        plan(task("medium"), task("critical", priority="critical")), today=TODAY
    )

    assert recommendation.task_id == "critical"


def test_in_progress_wins_when_attention_is_otherwise_close() -> None:
    recommendation = recommend_relocation_task(
        plan(task("not-started"), task("started", status="in_progress")), today=TODAY
    )

    assert recommendation.task_id == "started"
    assert recommendation.why == ("Already in progress.",)


def test_task_that_directly_unblocks_more_downstream_work_wins() -> None:
    recommendation = recommend_relocation_task(
        plan(
            task("lever-a"),
            task("lever-b"),
            task("downstream-1", dependency_task_ids=("lever-b",), blocked=True),
            task("downstream-2", dependency_task_ids=("lever-b",), blocked=True),
        ),
        today=TODAY,
    )

    assert recommendation.task_id == "lever-b"
    assert recommendation.directly_unblocks_task_ids == (
        "downstream-1",
        "downstream-2",
    )


def test_phase_then_task_id_are_stable_final_tie_breakers() -> None:
    recommendation = recommend_relocation_task(
        plan(
            task("a-prepare"),
            task("z-decide", phase_id="decide"),
            task("a-decide", phase_id="decide"),
        ),
        today=TODAY,
    )

    assert recommendation.task_id == "a-decide"


def test_no_actionable_task_explains_the_current_state() -> None:
    recommendation = recommend_relocation_task(
        plan(
            task("done", status="completed"),
            task("blocked", blocked=True),
            task("future", start_date="2026-08-14"),
        ),
        today=TODAY,
    )

    assert recommendation.status == "no_actionable_task"
    assert recommendation.task_id is None
    assert recommendation.why == (
        "1 completed, 1 blocked, and 1 scheduled for later.",
    )


def test_api_returns_a_recommendation_from_the_persisted_plan(tmp_path) -> None:
    async def exercise() -> dict[str, object]:
        app = create_app(tmp_path / "gotime.db")
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            created = await client.post(
                "/api/relocation-plan/tasks",
                json={
                    "id": "book-movers",
                    "title": "Book movers",
                    "description": None,
                    "phase_id": "prepare",
                    "categories": ["logistics"],
                    "status": "not_started",
                    "assignees": ["Joe"],
                    "start_date": None,
                    "due_date": None,
                    "priority": "high",
                    "dependency_task_ids": [],
                },
            )
            assert created.status_code == 201
            response = await client.get("/api/relocation-plan/recommendation")
            assert response.status_code == 200
            return response.json()

    recommendation = asyncio.run(exercise())

    assert recommendation["status"] == "recommended"
    assert recommendation["task_id"] == "book-movers"
    assert recommendation["task_title"] == "Book movers"
    assert recommendation["phase_title"] == "Prepare for the move"


def test_api_uses_strict_explicit_evaluation_date_and_compatible_fallback(tmp_path) -> None:
    async def exercise() -> tuple[int, int, int]:
        app = create_app(tmp_path / "gotime.db")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            valid = await client.get("/api/relocation-plan/recommendation?evaluation_date=2026-08-28")
            omitted = await client.get("/api/relocation-plan/recommendation")
            invalid = await client.get("/api/relocation-plan/recommendation?evaluation_date=2026-08-28T23:00:00Z")
            return valid.status_code, omitted.status_code, invalid.status_code

    assert asyncio.run(exercise()) == (200, 200, 422)


def test_api_recommends_through_dependency_chain_completion_and_reopening(
    tmp_path,
) -> None:
    database_path = tmp_path / "gotime.db"

    async def exercise() -> tuple[str, str, str, dict[str, object]]:
        app = create_app(database_path)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            for task_id, dependencies in (
                ("c", []),
                ("b", ["c"]),
                ("a", ["b"]),
            ):
                response = await client.post(
                    "/api/relocation-plan/tasks",
                    json={
                        "id": task_id,
                        "title": task_id.upper(),
                        "description": None,
                        "phase_id": "prepare",
                        "categories": ["logistics"],
                        "status": "not_started",
                        "assignees": [],
                        "start_date": None,
                        "due_date": None,
                        "priority": "medium",
                        "dependency_task_ids": dependencies,
                    },
                )
                assert response.status_code == 201

            first = (await client.get("/api/relocation-plan/recommendation")).json()
            await client.patch(
                "/api/relocation-plan/tasks/c/status", json={"status": "completed"}
            )
            second = (await client.get("/api/relocation-plan/recommendation")).json()
            await client.patch(
                "/api/relocation-plan/tasks/b/status", json={"status": "completed"}
            )
            third = (await client.get("/api/relocation-plan/recommendation")).json()
            reopened = await client.patch(
                "/api/relocation-plan/tasks/b/status", json={"status": "not_started"}
            )
            fourth = (await client.get("/api/relocation-plan/recommendation")).json()
            return (
                first["task_id"],
                second["task_id"],
                third["task_id"],
                {"recommendation": fourth, "plan": reopened.json()},
            )

    first, second, third, reopened = asyncio.run(exercise())

    assert (first, second, third) == ("c", "b", "a")
    assert reopened["recommendation"]["task_id"] == "b"
    tasks = {task["id"]: task for task in reopened["plan"]["tasks"]}
    assert tasks["a"]["blocked"] is True
    assert tasks["a"]["dependency_task_ids"] == ["b"]
    assert tasks["b"]["dependency_task_ids"] == ["c"]
