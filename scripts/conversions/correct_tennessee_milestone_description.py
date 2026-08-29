#!/usr/bin/env python3
"""Apply the approved family-facing Tennessee Milestone copy correction."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.conversions.convert_tennessee_home_marketing import audit

MILESTONE_ID = "put-tennessee-home-on-market-2027"
MILESTONE_TITLE = "Put our Tennessee home on the market"
OLD_DESCRIPTION = (
    "Editable user-provided test target. Achievement is explicitly confirmed by the user: "
    "for List publicly, when the listing is live; for Seek builder offers directly, when the "
    "property has been actively offered to selected builders; for Pursue both paths, when both "
    "paths have begun. A realtor meeting or Decision selection alone does not achieve it."
)
NEW_DESCRIPTION = (
    "Mark this milestone achieved when the public listing is live, the property has been offered "
    "directly to selected builders, or—if pursuing both paths—both have begun. Meeting with the "
    "realtor or choosing a marketing option alone does not achieve it."
)


class MilestoneCopyCorrectionError(RuntimeError):
    """The isolated target does not match either approved copy state."""


def _target(connection: sqlite3.Connection) -> dict[str, Any]:
    rows = connection.execute(
        "SELECT * FROM milestones WHERE id = ? OR title = ? ORDER BY id",
        (MILESTONE_ID, MILESTONE_TITLE),
    ).fetchall()
    if len(rows) != 1:
        raise MilestoneCopyCorrectionError("Expected exactly one Milestone target; target is missing or duplicated.")
    row = dict(rows[0])
    expected_identity = {
        "id": MILESTONE_ID,
        "plan_id": "family-relocation-plan",
        "title": MILESTONE_TITLE,
        "target_earliest_date": "2027-01-04",
        "target_latest_date": "2027-01-15",
        "achieved_at": None,
    }
    if any(row.get(key) != value for key, value in expected_identity.items()):
        raise MilestoneCopyCorrectionError("Milestone identity, window, or pending state differs from the approved target.")
    if row["description"] not in {OLD_DESCRIPTION, NEW_DESCRIPTION}:
        raise MilestoneCopyCorrectionError("Milestone description differs from both approved copy states.")
    return row


def correct_database(path: Path, *, fail_after_update: bool = False) -> dict[str, Any]:
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    before = audit(connection, path)
    try:
        connection.execute("BEGIN IMMEDIATE")
        target = _target(connection)
        result = "unchanged"
        if target["description"] == OLD_DESCRIPTION:
            cursor = connection.execute(
                "UPDATE milestones SET description = ? WHERE id = ? AND description = ?",
                (NEW_DESCRIPTION, MILESTONE_ID, OLD_DESCRIPTION),
            )
            if cursor.rowcount != 1:
                raise MilestoneCopyCorrectionError("The exact Milestone field update did not affect one row.")
            result = "applied"
            if fail_after_update:
                raise MilestoneCopyCorrectionError("Injected copy-correction failure")
        corrected = _target(connection)
        if corrected["description"] != NEW_DESCRIPTION:
            raise MilestoneCopyCorrectionError("The approved description was not established.")
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()

    with sqlite3.connect(path) as verified:
        verified.row_factory = sqlite3.Row
        after = audit(verified, path)
    return {
        "correction": "tennessee-milestone-description-v2",
        "result": result,
        "target_id": MILESTONE_ID,
        "field": "description",
        "old": OLD_DESCRIPTION,
        "new": NEW_DESCRIPTION,
        "before": before,
        "after": after,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("database", type=Path)
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()
    manifest = correct_database(args.database)
    rendered = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    if args.manifest:
        args.manifest.write_text(rendered)
    print(rendered, end="")


if __name__ == "__main__":
    main()
