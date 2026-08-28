#!/usr/bin/env python3
"""Convert the reviewed Tennessee home-marketing slice on an isolated DB copy."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

EXPECTED_SOURCE_SHA256 = "09bf1f9c2453254c0319b58d1bd3beb59bc8c37f4701bdb6269d0b87749f9f7a"
EXPECTED_SOURCE_HASHES = {
    "decision_options": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
    "decision_preparation_tasks": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
    "decisions": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
    "milestones": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
    "phases": "77e694dd42fa94fb15d3fb75f452ff37aab2fb590f2d317e68e24c3ea8130340",
    "relocation_plans": "2c2620d61df783578e34379c44863b0ab43678a69076dc48e0494ab9d4bb888a",
    "task_assignees": "f48e530c451580111b46d897df93106639159180de737024667389e133429815",
    "task_categories": "11133af06a50d2861d67f7b6da27a4c7899ea529d3b0690d761d375df97c1c68",
    "task_dependencies": "bbf459be9ccffd21ba2ccc078943726bebff1923b835c73a0ec3b8a9f26eb5c1",
    "task_hierarchy": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
    "task_parent_status_overrides": "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945",
    "tasks": "f25a1c68a3070611f22b2d44eb5a59b7148ece17901d21c72c7d82e27806cc21",
}

PLAN_ID = "family-relocation-plan"
PHASE_ID = "prepare"
PARENT_ID = "reengage-with-tn-realtor-e71dd74d-01e4-4338-9a94-0570bec0f3d2"
PARENT_SOURCE_TITLE = "Reengage with TN realtor"
PARENT_TARGET_TITLE = "Reengage with the realtor"
MILESTONE_ID = "put-tennessee-home-on-market-2027"
DECISION_ID = "choose-how-to-market-our-home"

TASKS = (
    ("prepare-questions-for-realtor-meeting", "Prepare questions for the realtor meeting"),
    ("contact-the-realtor", "Contact the realtor"),
    ("schedule-the-realtor-meeting", "Schedule the realtor meeting"),
    ("meet-with-the-realtor", "Meet with the realtor"),
)
TASK_IDS = {item[0] for item in TASKS}
OPTIONS = (
    (
        "list-publicly",
        "List publicly",
        "Market through the realtor; pricing, repairs, and “as-is” positioning can be decided from the realtor’s evidence.",
    ),
    (
        "seek-builder-offers-directly",
        "Seek builder offers directly",
        "Approach selected builders without relying on a public listing.",
    ),
    (
        "pursue-both-paths",
        "Pursue both paths",
        "Launch the public listing and direct builder outreach in parallel.",
    ),
)
OPTION_IDS = {item[0] for item in OPTIONS}

MILESTONE_DESCRIPTION = (
    "Editable user-provided test target. Achievement is explicitly confirmed by the user: "
    "for List publicly, when the listing is live; for Seek builder offers directly, when the "
    "property has been actively offered to selected builders; for Pursue both paths, when both "
    "paths have begun. A realtor meeting or Decision selection alone does not achieve it."
)
QUESTIONS_DESCRIPTION = (
    "Prepare questions covering: likely interest from move-in buyers despite nearby teardowns; "
    "likely builder pricing and resulting net proceeds; whether a public “as-is” listing is "
    "realistic given the pool and garage issues; and expected commissions, fees, loan payoff, "
    "and other deductions affecting net proceeds."
)
MEETING_DESCRIPTION = "Complete only after the realtor meeting actually occurs, not when it is merely scheduled."

EXPECTED_PARENT_ROW = {
    "id": PARENT_ID,
    "plan_id": PLAN_ID,
    "phase_id": PHASE_ID,
    "title": PARENT_SOURCE_TITLE,
    "description": None,
    "status": "not_started",
    "start_date": "2026-08-13",
    "due_date": "2026-09-01",
    "priority": "high",
}
TARGET_PARENT_ROW = {
    **EXPECTED_PARENT_ROW,
    "title": PARENT_TARGET_TITLE,
    "start_date": None,
    "due_date": None,
}


class ConversionError(RuntimeError):
    """Fail-closed conversion validation error."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tables(connection: sqlite3.Connection) -> list[str]:
    return [
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
    ]


def _rows(connection: sqlite3.Connection, table: str) -> list[dict[str, Any]]:
    quoted = '"' + table.replace('"', '""') + '"'
    return [dict(row) for row in connection.execute(f"SELECT * FROM {quoted}")]


def _row_hash(rows: list[dict[str, Any]]) -> str:
    ordered = sorted(
        rows,
        key=lambda row: json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False),
    )
    payload = json.dumps(
        ordered, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def audit(connection: sqlite3.Connection, path: Path) -> dict[str, Any]:
    tables = _tables(connection)
    rows = {table: _rows(connection, table) for table in tables}
    return {
        "database_sha256": _sha256(path),
        "integrity_check": [row[0] for row in connection.execute("PRAGMA integrity_check")],
        "foreign_key_check": [list(row) for row in connection.execute("PRAGMA foreign_key_check")],
        "counts": {table: len(rows[table]) for table in tables},
        "stable_row_hashes": {table: _row_hash(rows[table]) for table in tables},
    }


def _baseline_projection_hashes(connection: sqlite3.Connection) -> dict[str, str]:
    projected: dict[str, list[dict[str, Any]]] = {}
    for table in _tables(connection):
        rows = _rows(connection, table)
        if table == "tasks":
            rows = [row for row in rows if row["id"] not in TASK_IDS]
            for row in rows:
                if row["id"] == PARENT_ID:
                    row["title"] = PARENT_SOURCE_TITLE
                    row["start_date"] = EXPECTED_PARENT_ROW["start_date"]
                    row["due_date"] = EXPECTED_PARENT_ROW["due_date"]
        elif table in {"task_categories", "task_assignees"}:
            rows = [row for row in rows if row["task_id"] not in TASK_IDS]
            if table == "task_assignees":
                rows = [
                    row
                    for row in rows
                    if not (row["task_id"] == PARENT_ID and row["name"] == "Joe")
                ]
        elif table == "task_dependencies":
            rows = [row for row in rows if row["task_id"] not in TASK_IDS]
        elif table == "task_hierarchy":
            rows = [row for row in rows if row["child_task_id"] not in TASK_IDS]
        elif table == "milestones":
            rows = [row for row in rows if row["id"] != MILESTONE_ID]
        elif table == "decisions":
            rows = [row for row in rows if row["id"] != DECISION_ID]
        elif table == "decision_options":
            rows = [row for row in rows if row["id"] not in OPTION_IDS]
        elif table == "decision_preparation_tasks":
            rows = [row for row in rows if row["decision_id"] != DECISION_ID]
        projected[table] = rows
    return {table: _row_hash(rows) for table, rows in projected.items()}


def _one(connection: sqlite3.Connection, query: str, values: tuple[Any, ...]) -> dict[str, Any] | None:
    row = connection.execute(query, values).fetchone()
    return dict(row) if row else None


def _validate_source_identity(connection: sqlite3.Connection) -> None:
    parent = _one(connection, "SELECT * FROM tasks WHERE id = ?", (PARENT_ID,))
    if parent != EXPECTED_PARENT_ROW:
        raise ConversionError("The reused realtor Task no longer matches its approved source snapshot.")
    if _one(connection, "SELECT * FROM phases WHERE id = ?", (PHASE_ID,)) != {
        "id": PHASE_ID, "plan_id": PLAN_ID, "title": "Prepare for the move", "position": 20,
    }:
        raise ConversionError("The approved preparation phase identity no longer matches.")
    assignees = [row[0] for row in connection.execute(
        "SELECT name FROM task_assignees WHERE task_id = ? ORDER BY position", (PARENT_ID,)
    )]
    categories = [row[0] for row in connection.execute(
        "SELECT category FROM task_categories WHERE task_id = ? ORDER BY category", (PARENT_ID,)
    )]
    if assignees != ["Anne"] or categories != ["housing"]:
        raise ConversionError("The reused realtor Task assignments or categories changed.")


def _expected_task(task_id: str, title: str) -> dict[str, Any]:
    description = QUESTIONS_DESCRIPTION if task_id == TASKS[0][0] else MEETING_DESCRIPTION if task_id == TASKS[3][0] else None
    return {
        "id": task_id, "plan_id": PLAN_ID, "phase_id": PHASE_ID, "title": title,
        "description": description, "status": "not_started", "start_date": None,
        "due_date": None, "priority": "medium",
    }


def _target_is_exact(connection: sqlite3.Connection) -> bool:
    parent = _one(connection, "SELECT * FROM tasks WHERE id = ?", (PARENT_ID,))
    if parent != TARGET_PARENT_ROW:
        return False
    milestone = _one(connection, "SELECT * FROM milestones WHERE id = ?", (MILESTONE_ID,))
    if milestone != {
        "id": MILESTONE_ID, "plan_id": PLAN_ID,
        "title": "Put our Tennessee home on the market", "description": MILESTONE_DESCRIPTION,
        "target_earliest_date": "2027-01-04", "target_latest_date": "2027-01-15",
        "achieved_at": None,
    }:
        return False
    decision = _one(connection, "SELECT * FROM decisions WHERE id = ?", (DECISION_ID,))
    if decision != {
        "id": DECISION_ID, "plan_id": PLAN_ID, "milestone_id": MILESTONE_ID,
        "title": "Choose how to market our home", "description": None,
        "selected_option_id": None,
    }:
        return False
    if [_one(connection, "SELECT * FROM decision_options WHERE id = ?", (option_id,)) for option_id, _, _ in OPTIONS] != [
        {"id": option_id, "decision_id": DECISION_ID, "title": title, "description": description, "position": position}
        for position, (option_id, title, description) in enumerate(OPTIONS)
    ]:
        return False
    if [_one(connection, "SELECT * FROM tasks WHERE id = ?", (task_id,)) for task_id, _ in TASKS] != [
        _expected_task(task_id, title) for task_id, title in TASKS
    ]:
        return False
    expected_assignees = [(PARENT_ID, 0, "Anne"), (PARENT_ID, 1, "Joe")] + [
        (task_id, position, name)
        for task_id, _ in TASKS for position, name in enumerate(("Anne", "Joe"))
    ]
    actual_assignees = [tuple(row) for row in connection.execute(
        "SELECT task_id, position, name FROM task_assignees WHERE task_id = ? OR task_id IN (?,?,?,?) ORDER BY task_id, position",
        (PARENT_ID, *[item[0] for item in TASKS]),
    )]
    if sorted(actual_assignees) != sorted(expected_assignees):
        return False
    if [tuple(row) for row in connection.execute(
        "SELECT task_id, category FROM task_categories WHERE task_id IN (?,?,?,?) ORDER BY task_id",
        tuple(item[0] for item in TASKS),
    )] != sorted((task_id, "housing") for task_id, _ in TASKS):
        return False
    if [tuple(row) for row in connection.execute(
        "SELECT child_task_id, parent_task_id, position FROM task_hierarchy WHERE parent_task_id = ? ORDER BY position",
        (PARENT_ID,),
    )] != [(task_id, PARENT_ID, position) for position, (task_id, _) in enumerate(TASKS)]:
        return False
    expected_dependencies = [
        (TASKS[2][0], TASKS[1][0], 0),
        (TASKS[3][0], TASKS[2][0], 0),
        (TASKS[3][0], TASKS[0][0], 1),
    ]
    if [tuple(row) for row in connection.execute(
        "SELECT task_id, dependency_task_id, position FROM task_dependencies WHERE task_id IN (?,?,?,?) ORDER BY task_id, position",
        tuple(item[0] for item in TASKS),
    )] != sorted(expected_dependencies, key=lambda item: (item[0], item[2])):
        return False
    if [tuple(row) for row in connection.execute(
        "SELECT decision_id, task_id FROM decision_preparation_tasks WHERE decision_id = ?", (DECISION_ID,)
    )] != [(DECISION_ID, PARENT_ID)]:
        return False
    if connection.execute("SELECT 1 FROM task_parent_status_overrides WHERE parent_task_id = ?", (PARENT_ID,)).fetchone():
        return False
    return True


def _insert_target(connection: sqlite3.Connection) -> None:
    connection.execute(
        "UPDATE tasks SET title = ?, start_date = NULL, due_date = NULL WHERE id = ?",
        (PARENT_TARGET_TITLE, PARENT_ID),
    )
    connection.execute(
        "INSERT INTO task_assignees(task_id, position, name) VALUES (?, 1, 'Joe')", (PARENT_ID,)
    )
    connection.execute(
        "INSERT INTO milestones VALUES (?, ?, ?, ?, ?, ?, NULL)",
        (MILESTONE_ID, PLAN_ID, "Put our Tennessee home on the market", MILESTONE_DESCRIPTION, "2027-01-04", "2027-01-15"),
    )
    connection.execute(
        "INSERT INTO decisions VALUES (?, ?, ?, ?, NULL, NULL)",
        (DECISION_ID, PLAN_ID, MILESTONE_ID, "Choose how to market our home"),
    )
    connection.executemany(
        "INSERT INTO decision_options(id, decision_id, title, description, position) VALUES (?, ?, ?, ?, ?)",
        [(option_id, DECISION_ID, title, description, position) for position, (option_id, title, description) in enumerate(OPTIONS)],
    )
    for position, (task_id, title) in enumerate(TASKS):
        task = _expected_task(task_id, title)
        connection.execute(
            "INSERT INTO tasks(id, plan_id, phase_id, title, description, status, start_date, due_date, priority) VALUES (:id,:plan_id,:phase_id,:title,:description,:status,:start_date,:due_date,:priority)",
            task,
        )
        connection.execute("INSERT INTO task_categories VALUES (?, 'housing')", (task_id,))
        connection.executemany(
            "INSERT INTO task_assignees VALUES (?, ?, ?)",
            ((task_id, assignee_position, name) for assignee_position, name in enumerate(("Anne", "Joe"))),
        )
        connection.execute("INSERT INTO task_hierarchy VALUES (?, ?, ?)", (task_id, PARENT_ID, position))
    connection.executemany(
        "INSERT INTO task_dependencies VALUES (?, ?, ?)",
        ((TASKS[2][0], TASKS[1][0], 0), (TASKS[3][0], TASKS[2][0], 0), (TASKS[3][0], TASKS[0][0], 1)),
    )
    connection.execute("INSERT INTO decision_preparation_tasks VALUES (?, ?)", (DECISION_ID, PARENT_ID))


def convert_database(
    path: Path,
    *,
    expected_source_sha256: str = EXPECTED_SOURCE_SHA256,
    expected_source_hashes: dict[str, str] = EXPECTED_SOURCE_HASHES,
    fail_after_apply: bool = False,
) -> dict[str, Any]:
    path = path.resolve()
    connection = sqlite3.connect(path, isolation_level=None)
    try:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        before = audit(connection, path)
        if before["integrity_check"] != ["ok"] or before["foreign_key_check"]:
            raise ConversionError("Database integrity or foreign-key validation failed.")
        projection = _baseline_projection_hashes(connection)
        if projection != expected_source_hashes:
            raise ConversionError("Source-state logical fingerprint does not match the approved family plan.")
        is_exact_source = before["database_sha256"] == expected_source_sha256 and before["stable_row_hashes"] == expected_source_hashes
        if is_exact_source:
            _validate_source_identity(connection)
        elif _target_is_exact(connection):
            return _manifest("unchanged", before, before)
        else:
            raise ConversionError("Database is neither the exact approved source nor the complete approved target state.")
        try:
            connection.execute("BEGIN IMMEDIATE")
            _insert_target(connection)
            if fail_after_apply:
                raise ConversionError("Injected rehearsal failure after target writes.")
            if not _target_is_exact(connection):
                raise ConversionError("Post-conversion target validation failed.")
            if _baseline_projection_hashes(connection) != expected_source_hashes:
                raise ConversionError("An unrelated preexisting row changed during conversion.")
            foreign_keys = [list(row) for row in connection.execute("PRAGMA foreign_key_check")]
            if foreign_keys:
                raise ConversionError(f"Post-conversion foreign-key violations: {foreign_keys}")
            connection.execute("COMMIT")
        except Exception:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            raise
        after = audit(connection, path)
        return _manifest("applied", before, after)
    finally:
        connection.close()


def _manifest(result: str, before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    return {
        "conversion": "tennessee-home-marketing-v1",
        "result": result,
        "source_fingerprint": EXPECTED_SOURCE_SHA256,
        "reused_tasks": [{
            "id": PARENT_ID,
            "source_title": PARENT_SOURCE_TITLE,
            "target_title": PARENT_TARGET_TITLE,
            "approved_mutations": {
                "start_date": {"before": "2026-08-13", "after": None},
                "due_date": {"before": "2026-09-01", "after": None},
            },
        }],
        "created_tasks": [{"id": task_id, "title": title} for task_id, title in TASKS],
        "created_milestone_id": MILESTONE_ID,
        "created_decision_id": DECISION_ID,
        "before": before,
        "after": after,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path)
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()
    manifest = convert_database(args.database)
    rendered = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    if args.manifest:
        args.manifest.write_text(rendered)
    print(rendered, end="")


if __name__ == "__main__":
    main()
