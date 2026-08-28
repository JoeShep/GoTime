from __future__ import annotations

import hashlib
import shutil
import sqlite3
import sys
from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT))

from scripts.conversions.convert_tennessee_home_marketing import (  # noqa: E402
    ConversionError,
    DECISION_ID,
    PARENT_ID,
    TASKS,
    audit,
    convert_database,
)
from app.relocation_plan_recommendation import recommend_relocation_task  # noqa: E402
from app.relocation_plan_repository import SQLiteRelocationPlanRepository  # noqa: E402


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source_database(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    path = tmp_path / "source.db"
    SQLiteRelocationPlanRepository(path)
    with sqlite3.connect(path) as connection:
        connection.execute(
            """INSERT INTO tasks VALUES (?, 'family-relocation-plan', 'prepare', ?, NULL,
                       'not_started', '2026-08-13', '2026-09-01', 'high')""",
            (PARENT_ID, "Reengage with TN realtor"),
        )
        connection.execute("INSERT INTO task_categories VALUES (?, 'housing')", (PARENT_ID,))
        connection.execute("INSERT INTO task_assignees VALUES (?, 0, 'Anne')", (PARENT_ID,))
    with sqlite3.connect(path) as connection:
        connection.row_factory = sqlite3.Row
        hashes = audit(connection, path)["stable_row_hashes"]
    return path, hashes


def _convert(path: Path, hashes: dict[str, str], **kwargs: object):
    return convert_database(
        path,
        expected_source_sha256=_sha(path),
        expected_source_hashes=hashes,
        **kwargs,
    )


def test_conversion_is_exact_preserving_and_idempotent(tmp_path: Path) -> None:
    path, source_hashes = _source_database(tmp_path)
    first = _convert(path, source_hashes)
    assert first["result"] == "applied"
    after_sha = _sha(path)
    second = convert_database(
        path,
        expected_source_sha256=first["before"]["database_sha256"],
        expected_source_hashes=source_hashes,
    )
    assert second["result"] == "unchanged"
    assert _sha(path) == after_sha

    repository = SQLiteRelocationPlanRepository(path)
    plan = repository.get_plan()
    parent = next(task for task in plan.tasks if task.id == PARENT_ID)
    decision = next(item for item in plan.decisions if item.id == DECISION_ID)
    assert parent.title == "Reengage with the realtor"
    assert parent.status.value == "not_started"
    assert parent.manual_status_override is None
    assert parent.due_date.isoformat() == "2026-09-01"
    children = sorted(
        (child for child in plan.tasks if child.parent_task_id == PARENT_ID),
        key=lambda child: child.subtask_position,
    )
    assert tuple(child.id for child in children) == tuple(task_id for task_id, _ in TASKS)
    assert decision.preparation_task_ids == (PARENT_ID,)
    assert decision.preparation_readiness.value == "preparation_incomplete"
    assert len(plan.milestones) == 1
    assert len(decision.options) == 3
    recommendation = recommend_relocation_task(plan)
    assert recommendation is not None
    assert recommendation.task_id == "contact-the-realtor"
    assert [(signal.kind.value, signal.decision_id, signal.parent_task_id) for signal in recommendation.signals] == [
        ("inherited_decision_preparation", DECISION_ID, PARENT_ID)
    ]

    with sqlite3.connect(path) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        assert connection.execute("SELECT COUNT(*) FROM task_parent_status_overrides").fetchone()[0] == 0
        dependencies = connection.execute(
            "SELECT task_id, dependency_task_id FROM task_dependencies WHERE task_id IN (?,?,?,?) ORDER BY task_id, position",
            tuple(task_id for task_id, _ in TASKS),
        ).fetchall()
    assert dependencies == [
        ("meet-with-the-realtor", "schedule-the-realtor-meeting"),
        ("meet-with-the-realtor", "prepare-questions-for-realtor-meeting"),
        ("schedule-the-realtor-meeting", "contact-the-realtor"),
    ]


def test_injected_failure_rolls_back_every_write(tmp_path: Path) -> None:
    path, source_hashes = _source_database(tmp_path)
    before_sha = _sha(path)
    with pytest.raises(ConversionError, match="Injected rehearsal failure"):
        _convert(path, source_hashes, fail_after_apply=True)
    assert _sha(path) == before_sha
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM milestones").fetchone()[0] == 0
        assert connection.execute("SELECT title FROM tasks WHERE id = ?", (PARENT_ID,)).fetchone()[0] == "Reengage with TN realtor"


def test_partial_or_changed_source_fails_closed_without_further_mutation(tmp_path: Path) -> None:
    path, source_hashes = _source_database(tmp_path)
    _convert(path, source_hashes)
    with sqlite3.connect(path) as connection:
        connection.execute("DELETE FROM decision_options WHERE id = 'pursue-both-paths'")
    partial_sha = _sha(path)
    with pytest.raises(ConversionError, match="neither the exact approved source nor the complete approved target"):
        convert_database(path, expected_source_sha256="not-the-source", expected_source_hashes=source_hashes)
    assert _sha(path) == partial_sha

    changed = tmp_path / "changed.db"
    source, hashes = _source_database(tmp_path / "changed-fixture")
    shutil.copy2(source, changed)
    with sqlite3.connect(changed) as connection:
        connection.execute("UPDATE tasks SET priority = 'critical' WHERE id = ?", (PARENT_ID,))
    changed_sha = _sha(changed)
    with pytest.raises(ConversionError, match="fingerprint"):
        convert_database(changed, expected_source_sha256=_sha(source), expected_source_hashes=hashes)
    assert _sha(changed) == changed_sha
