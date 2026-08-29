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
    MILESTONE_DESCRIPTION,
    audit,
)
from scripts.conversions.correct_tennessee_milestone_description import (  # noqa: E402
    MILESTONE_ID,
    NEW_DESCRIPTION,
    OLD_DESCRIPTION,
    MilestoneCopyCorrectionError,
    correct_database,
)
from app.relocation_plan_repository import SQLiteRelocationPlanRepository  # noqa: E402
from app.relocation_plan_models import MilestoneCreate  # noqa: E402


def _fixture(path: Path, description: str = OLD_DESCRIPTION) -> None:
    repository = SQLiteRelocationPlanRepository(path)
    repository.create_milestone(MilestoneCreate(
        id=MILESTONE_ID,
        title="Put our Tennessee home on the market",
        description=description,
        target_earliest_date="2027-01-04",
        target_latest_date="2027-01-15",
    ))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_copy_correction_changes_one_field_and_is_idempotent(tmp_path: Path) -> None:
    path = tmp_path / "plan.db"
    _fixture(path)
    with sqlite3.connect(path) as connection:
        connection.row_factory = sqlite3.Row
        before = audit(connection, path)
    first = correct_database(path)
    second = correct_database(path)
    assert first["result"] == "applied"
    assert second["result"] == "unchanged"
    assert first["before"]["counts"] == first["after"]["counts"]
    changed = {table for table in before["stable_row_hashes"] if before["stable_row_hashes"][table] != first["after"]["stable_row_hashes"][table]}
    assert changed == {"milestones"}
    assert MILESTONE_DESCRIPTION == NEW_DESCRIPTION


def test_injected_failure_rolls_back_completely(tmp_path: Path) -> None:
    path = tmp_path / "plan.db"
    _fixture(path)
    before = _sha(path)
    with pytest.raises(MilestoneCopyCorrectionError, match="Injected"):
        correct_database(path, fail_after_update=True)
    assert _sha(path) == before
    with sqlite3.connect(path) as connection:
        assert connection.execute("SELECT description FROM milestones WHERE id = ?", (MILESTONE_ID,)).fetchone()[0] == OLD_DESCRIPTION


@pytest.mark.parametrize("change", ("description", "identity", "missing", "duplicate"))
def test_unexpected_targets_fail_without_mutation(tmp_path: Path, change: str) -> None:
    path = tmp_path / "plan.db"
    _fixture(path, "Unexpected" if change == "description" else OLD_DESCRIPTION)
    with sqlite3.connect(path) as connection:
        if change == "identity":
            connection.execute("UPDATE milestones SET target_latest_date = '2027-01-16'")
        elif change == "missing":
            connection.execute("DELETE FROM milestones")
        elif change == "duplicate":
            connection.execute(
                "INSERT INTO milestones VALUES ('duplicate', 'family-relocation-plan', ?, NULL, NULL, NULL, NULL)",
                ("Put our Tennessee home on the market",),
            )
    before = _sha(path)
    with pytest.raises(MilestoneCopyCorrectionError):
        correct_database(path)
    assert _sha(path) == before
