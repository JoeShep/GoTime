import asyncio
from pathlib import Path

from httpx import ASGITransport, AsyncClient, Response

from app.main import create_app


def task_payload(task_id: str, **changes: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": task_id,
        "title": task_id.replace("-", " ").title(),
        "description": None,
        "phase_id": "prepare",
        "category": "logistics",
        "status": "not_started",
        "assignees": ["Joe"],
        "start_date": None,
        "due_date": None,
        "priority": "medium",
        "dependency_task_ids": [],
    }
    payload.update(changes)
    return payload


async def request(database_path: Path, method: str, path: str, **kwargs: object) -> Response:
    app = create_app(database_path)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        return await client.request(method, path, **kwargs)


def test_get_returns_the_persisted_singleton_plan(tmp_path) -> None:
    response = asyncio.run(request(tmp_path / "gotime.db", "GET", "/api/relocation-plan"))

    assert response.status_code == 200
    assert response.json() == {
        "id": "family-relocation-plan",
        "title": "Relocate the family to Northern California",
        "phases": [
            {"id": "decide", "title": "Decide where and how to move", "position": 10},
            {"id": "prepare", "title": "Prepare for the move", "position": 20},
            {"id": "move", "title": "Complete the move", "position": 30},
            {"id": "settle", "title": "Settle in", "position": 40},
        ],
        "tasks": [],
    }


def test_create_update_and_retrieve_task_across_app_reconstruction(tmp_path) -> None:
    database_path = tmp_path / "gotime.db"
    created = asyncio.run(
        request(
            database_path,
            "POST",
            "/api/relocation-plan/tasks",
            json=task_payload("book-movers", assignees=["Joe", "Sarah"]),
        )
    )
    assert created.status_code == 201

    updated_payload = task_payload(
        "ignored-by-put",
        title="Book an interstate mover",
        description="Select the reviewed quote.",
        phase_id="move",
        category="financial",
        assignees=["Sarah"],
        priority="critical",
        start_date="2026-09-01",
        due_date="2026-09-10",
    )
    updated_payload.pop("id")
    updated = asyncio.run(
        request(
            database_path,
            "PUT",
            "/api/relocation-plan/tasks/book-movers",
            json=updated_payload,
        )
    )
    assert updated.status_code == 200

    recovered = asyncio.run(request(database_path, "GET", "/api/relocation-plan"))
    task = recovered.json()["tasks"][0]
    assert task["id"] == "book-movers"
    assert task["title"] == "Book an interstate mover"
    assert task["phase_id"] == "move"
    assert task["assignees"] == ["Sarah"]
    assert task["priority"] == "critical"


def test_create_and_replace_allow_an_unassigned_task(tmp_path) -> None:
    database_path = tmp_path / "gotime.db"
    payload = task_payload("shared-decision")
    payload.pop("assignees")

    created = asyncio.run(
        request(
            database_path,
            "POST",
            "/api/relocation-plan/tasks",
            json=payload,
        )
    )
    assert created.status_code == 201
    assert created.json()["tasks"][0]["assignees"] == []

    replacement = {key: value for key, value in payload.items() if key != "id"}
    replacement["title"] = "Shared family decision"
    replacement["assignees"] = []
    replaced = asyncio.run(
        request(
            database_path,
            "PUT",
            "/api/relocation-plan/tasks/shared-decision",
            json=replacement,
        )
    )
    assert replaced.status_code == 200
    assert replaced.json()["tasks"][0]["assignees"] == []


def test_incomplete_put_is_rejected_without_resetting_existing_task(tmp_path) -> None:
    database_path = tmp_path / "gotime.db"
    original = task_payload(
        "book-movers",
        description="Keep this description.",
        priority="high",
        start_date="2026-09-01",
        due_date="2026-09-15",
    )
    assert asyncio.run(
        request(
            database_path,
            "POST",
            "/api/relocation-plan/tasks",
            json=original,
        )
    ).status_code == 201

    incomplete = asyncio.run(
        request(
            database_path,
            "PUT",
            "/api/relocation-plan/tasks/book-movers",
            json={"title": "Silently incomplete"},
        )
    )

    assert incomplete.status_code == 422
    recovered = asyncio.run(request(database_path, "GET", "/api/relocation-plan"))
    assert recovered.json()["tasks"][0]["description"] == "Keep this description."
    assert recovered.json()["tasks"][0]["priority"] == "high"
    assert recovered.json()["tasks"][0]["due_date"] == "2026-09-15"


def test_put_cannot_omit_and_silently_erase_dependencies(tmp_path) -> None:
    database_path = tmp_path / "gotime.db"
    for payload in (
        task_payload("choose-mover"),
        task_payload("pay-deposit", dependency_task_ids=["choose-mover"]),
    ):
        assert asyncio.run(
            request(
                database_path,
                "POST",
                "/api/relocation-plan/tasks",
                json=payload,
            )
        ).status_code == 201

    incomplete = task_payload("ignored", title="Updated title")
    incomplete.pop("id")
    incomplete.pop("dependency_task_ids")
    response = asyncio.run(
        request(
            database_path,
            "PUT",
            "/api/relocation-plan/tasks/pay-deposit",
            json=incomplete,
        )
    )

    assert response.status_code == 422
    recovered = asyncio.run(request(database_path, "GET", "/api/relocation-plan"))
    dependent = next(
        item for item in recovered.json()["tasks"] if item["id"] == "pay-deposit"
    )
    assert dependent["title"] == "Pay Deposit"
    assert dependent["dependency_task_ids"] == ["choose-mover"]
    assert dependent["blocked"] is True


def test_complete_put_can_explicitly_clear_nullable_fields(tmp_path) -> None:
    database_path = tmp_path / "gotime.db"
    assert asyncio.run(
        request(
            database_path,
            "POST",
            "/api/relocation-plan/tasks",
            json=task_payload(
                "book-movers",
                description="Clear this later.",
                start_date="2026-09-01",
                due_date="2026-09-15",
            ),
        )
    ).status_code == 201
    replacement = task_payload(
        "ignored",
        title="Book movers now",
        description=None,
        start_date=None,
        due_date=None,
        priority="high",
    )
    replacement.pop("id")

    response = asyncio.run(
        request(
            database_path,
            "PUT",
            "/api/relocation-plan/tasks/book-movers",
            json=replacement,
        )
    )

    assert response.status_code == 200
    updated = response.json()["tasks"][0]
    assert updated["title"] == "Book movers now"
    assert updated["description"] is None
    assert updated["start_date"] is None
    assert updated["due_date"] is None
    assert updated["priority"] == "high"


def test_status_change_unblocks_a_dependent_task(tmp_path) -> None:
    database_path = tmp_path / "gotime.db"
    asyncio.run(
        request(
            database_path,
            "POST",
            "/api/relocation-plan/tasks",
            json=task_payload("choose-mover"),
        )
    )
    blocked = asyncio.run(
        request(
            database_path,
            "POST",
            "/api/relocation-plan/tasks",
            json=task_payload("pay-deposit", dependency_task_ids=["choose-mover"]),
        )
    )
    assert next(item for item in blocked.json()["tasks"] if item["id"] == "pay-deposit")[
        "blocked"
    ] is True

    completed = asyncio.run(
        request(
            database_path,
            "PATCH",
            "/api/relocation-plan/tasks/choose-mover/status",
            json={"status": "completed"},
        )
    )
    assert completed.status_code == 200
    assert next(
        item for item in completed.json()["tasks"] if item["id"] == "pay-deposit"
    )["blocked"] is False


def test_invalid_dependency_cycle_status_and_priority_return_422(tmp_path) -> None:
    database_path = tmp_path / "gotime.db"
    missing = asyncio.run(
        request(
            database_path,
            "POST",
            "/api/relocation-plan/tasks",
            json=task_payload("dependent", dependency_task_ids=["missing"]),
        )
    )
    assert missing.status_code == 422
    assert "missing" in missing.json()["detail"]

    invalid_status = asyncio.run(
        request(
            database_path,
            "POST",
            "/api/relocation-plan/tasks",
            json=task_payload("bad-status", status="invented"),
        )
    )
    assert invalid_status.status_code == 422

    invalid_priority = asyncio.run(
        request(
            database_path,
            "POST",
            "/api/relocation-plan/tasks",
            json=task_payload("bad-priority", priority="urgent-ish"),
        )
    )
    assert invalid_priority.status_code == 422

    first = asyncio.run(
        request(
            database_path,
            "POST",
            "/api/relocation-plan/tasks",
            json=task_payload("first"),
        )
    )
    assert first.status_code == 201
    second = asyncio.run(
        request(
            database_path,
            "POST",
            "/api/relocation-plan/tasks",
            json=task_payload("second", dependency_task_ids=["first"]),
        )
    )
    assert second.status_code == 201
    first_update = task_payload("ignored", dependency_task_ids=["second"])
    first_update.pop("id")
    cycle = asyncio.run(
        request(
            database_path,
            "PUT",
            "/api/relocation-plan/tasks/first",
            json=first_update,
        )
    )
    assert cycle.status_code == 422
    assert "cycle" in cycle.json()["detail"]


def test_unknown_task_returns_404(tmp_path) -> None:
    response = asyncio.run(
        request(
            tmp_path / "gotime.db",
            "PATCH",
            "/api/relocation-plan/tasks/missing/status",
            json={"status": "completed"},
        )
    )

    assert response.status_code == 404
