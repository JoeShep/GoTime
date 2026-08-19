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
        "categories": ["logistics"],
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
            {"id": "move", "title": "Make the move", "position": 30},
            {"id": "settle", "title": "Settle in", "position": 40},
        ],
        "tasks": [],
        "milestones": [],
        "decisions": [],
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
        categories=["financial"],
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
    assert task["categories"] == ["financial"]


def test_categories_are_required_and_allow_empty_or_multiple_values(tmp_path) -> None:
    database_path = tmp_path / "gotime.db"
    missing_payload = task_payload("missing-categories")
    missing_payload.pop("categories")
    missing = asyncio.run(
        request(database_path, "POST", "/api/relocation-plan/tasks", json=missing_payload)
    )
    assert missing.status_code == 422

    empty = asyncio.run(
        request(
            database_path,
            "POST",
            "/api/relocation-plan/tasks",
            json=task_payload("uncategorized", categories=[]),
        )
    )
    assert empty.status_code == 201
    assert empty.json()["tasks"][0]["categories"] == []

    multiple = asyncio.run(
        request(
            database_path,
            "POST",
            "/api/relocation-plan/tasks",
            json=task_payload(
                "multiple", categories=["logistics", "employment", "housing"]
            ),
        )
    )
    assert multiple.status_code == 201
    task = next(item for item in multiple.json()["tasks"] if item["id"] == "multiple")
    assert task["categories"] == ["employment", "housing", "logistics"]

    incomplete_replacement = task_payload("ignored", categories=["family"])
    incomplete_replacement.pop("id")
    incomplete_replacement.pop("categories")
    rejected = asyncio.run(
        request(
            database_path,
            "PUT",
            "/api/relocation-plan/tasks/multiple",
            json=incomplete_replacement,
        )
    )
    assert rejected.status_code == 422
    recovered = asyncio.run(request(database_path, "GET", "/api/relocation-plan"))
    unchanged = next(
        item for item in recovered.json()["tasks"] if item["id"] == "multiple"
    )
    assert unchanged["categories"] == ["employment", "housing", "logistics"]


def test_duplicate_and_unknown_categories_are_rejected(tmp_path) -> None:
    database_path = tmp_path / "gotime.db"
    duplicate = asyncio.run(
        request(
            database_path,
            "POST",
            "/api/relocation-plan/tasks",
            json=task_payload("duplicate", categories=["family", "family"]),
        )
    )
    unknown = asyncio.run(
        request(
            database_path,
            "POST",
            "/api/relocation-plan/tasks",
            json=task_payload("unknown", categories=["invented"]),
        )
    )

    assert duplicate.status_code == 422
    assert unknown.status_code == 422


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

    reopened = asyncio.run(
        request(
            database_path,
            "PATCH",
            "/api/relocation-plan/tasks/choose-mover/status",
            json={"status": "in_progress"},
        )
    )
    dependent = next(
        item for item in reopened.json()["tasks"] if item["id"] == "pay-deposit"
    )
    assert dependent["blocked"] is True
    assert dependent["dependency_task_ids"] == ["choose-mover"]


def test_completed_dependency_cannot_be_newly_added_but_can_be_retained(
    tmp_path,
) -> None:
    database_path = tmp_path / "gotime.db"
    asyncio.run(
        request(
            database_path,
            "POST",
            "/api/relocation-plan/tasks",
            json=task_payload("prerequisite"),
        )
    )
    asyncio.run(
        request(
            database_path,
            "POST",
            "/api/relocation-plan/tasks",
            json=task_payload("dependent", dependency_task_ids=["prerequisite"]),
        )
    )
    asyncio.run(
        request(
            database_path,
            "PATCH",
            "/api/relocation-plan/tasks/prerequisite/status",
            json={"status": "completed"},
        )
    )

    rejected_create = asyncio.run(
        request(
            database_path,
            "POST",
            "/api/relocation-plan/tasks",
            json=task_payload("new-task", dependency_task_ids=["prerequisite"]),
        )
    )
    assert rejected_create.status_code == 422
    assert "Completed task(s) cannot be added" in rejected_create.json()["detail"]

    retained_payload = task_payload(
        "ignored", dependency_task_ids=["prerequisite"]
    )
    retained_payload.pop("id")
    retained = asyncio.run(
        request(
            database_path,
            "PUT",
            "/api/relocation-plan/tasks/dependent",
            json=retained_payload,
        )
    )
    assert retained.status_code == 200
    dependent = next(
        item for item in retained.json()["tasks"] if item["id"] == "dependent"
    )
    assert dependent["dependency_task_ids"] == ["prerequisite"]

    removed_payload = task_payload("ignored", dependency_task_ids=[])
    removed_payload.pop("id")
    removed = asyncio.run(
        request(
            database_path,
            "PUT",
            "/api/relocation-plan/tasks/dependent",
            json=removed_payload,
        )
    )
    assert removed.status_code == 200

    new_relationship_payload = task_payload(
        "ignored", dependency_task_ids=["prerequisite"]
    )
    new_relationship_payload.pop("id")
    rejected_update = asyncio.run(
        request(
            database_path,
            "PUT",
            "/api/relocation-plan/tasks/dependent",
            json=new_relationship_payload,
        )
    )
    assert rejected_update.status_code == 422
    assert "Completed task(s) cannot be added" in rejected_update.json()["detail"]


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
