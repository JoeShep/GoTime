from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path

from app.relocation_plan_models import (
    CATEGORY_ORDER,
    Decision,
    DecisionCreate,
    DecisionOptionFields,
    DecisionStatus,
    DecisionUpdate,
    Milestone,
    MilestoneCreate,
    MilestoneStatus,
    MilestoneUpdate,
    Phase,
    RelocationPlan,
    Task,
    TaskCategory,
    TaskCreate,
    TaskStatus,
    TaskUpdate,
)


RELOCATION_PLAN_ID = "family-relocation-plan"
RELOCATION_PLAN_TITLE = "Relocate the family to Northern California"
DEFAULT_PHASES = (
    Phase(id="decide", title="Decide where and how to move", position=10),
    Phase(id="prepare", title="Prepare for the move", position=20),
    Phase(id="move", title="Make the move", position=30),
    Phase(id="settle", title="Settle in", position=40),
)


class RelocationPlanError(ValueError):
    pass


class TaskAlreadyExistsError(RelocationPlanError):
    pass


class TaskNotFoundError(RelocationPlanError):
    pass


class InvalidPhaseError(RelocationPlanError):
    pass


class InvalidDependencyError(RelocationPlanError):
    pass


class InvalidHierarchyError(RelocationPlanError):
    pass


class ParentChangeConfirmationRequired(RelocationPlanError):
    def __init__(self, message: str, code: str):
        super().__init__(message)
        self.code = code


class DependencyCycleError(RelocationPlanError):
    pass


class PlanItemAlreadyExistsError(RelocationPlanError):
    pass


class DuplicateTitleError(RelocationPlanError):
    code: str

    def __init__(self, message: str, code: str):
        super().__init__(message)
        self.code = code


class DuplicateTaskTitleError(DuplicateTitleError):
    def __init__(self):
        super().__init__(
            "A task with this title already exists in this plan.",
            "duplicate_task_title",
        )


class DuplicateMilestoneTitleError(DuplicateTitleError):
    def __init__(self):
        super().__init__(
            "A milestone with this title already exists in this plan.",
            "duplicate_milestone_title",
        )


class DuplicateDecisionTitleError(DuplicateTitleError):
    def __init__(self):
        super().__init__(
            "A decision with this title already exists in this plan.",
            "duplicate_decision_title",
        )


def canonicalize_plan_item_title(title: str) -> str:
    return " ".join(title.split()).casefold()


class MilestoneNotFoundError(RelocationPlanError):
    pass


class DecisionNotFoundError(RelocationPlanError):
    pass


class InvalidDecisionError(RelocationPlanError):
    pass


class SQLiteRelocationPlanRepository:
    def __init__(self, database_path: str | Path):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize_schema(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS relocation_plans (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS phases (
                    id TEXT PRIMARY KEY,
                    plan_id TEXT NOT NULL REFERENCES relocation_plans(id),
                    title TEXT NOT NULL,
                    position INTEGER NOT NULL CHECK (position >= 0),
                    UNIQUE (plan_id, position)
                );

                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    plan_id TEXT NOT NULL REFERENCES relocation_plans(id),
                    phase_id TEXT NOT NULL REFERENCES phases(id),
                    title TEXT NOT NULL,
                    description TEXT,
                    status TEXT NOT NULL CHECK (status IN (
                        'not_started', 'in_progress', 'completed'
                    )),
                    start_date TEXT,
                    due_date TEXT,
                    priority TEXT NOT NULL CHECK (priority IN (
                        'low', 'medium', 'high', 'critical'
                    ))
                );

                CREATE TABLE IF NOT EXISTS task_categories (
                    task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                    category TEXT NOT NULL CHECK (category IN (
                        'employment', 'family', 'financial', 'healthcare',
                        'housing', 'logistics'
                    )),
                    PRIMARY KEY (task_id, category)
                );

                CREATE TABLE IF NOT EXISTS task_assignees (
                    task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                    position INTEGER NOT NULL CHECK (position >= 0),
                    name TEXT NOT NULL,
                    PRIMARY KEY (task_id, position),
                    UNIQUE (task_id, name)
                );

                CREATE TABLE IF NOT EXISTS task_dependencies (
                    task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                    dependency_task_id TEXT NOT NULL REFERENCES tasks(id),
                    position INTEGER NOT NULL CHECK (position >= 0),
                    PRIMARY KEY (task_id, dependency_task_id),
                    UNIQUE (task_id, position),
                    CHECK (task_id <> dependency_task_id)
                );
                """
            )
            self._migrate_task_categories(connection)
            self._migrate_milestone_decision_foundation(connection)
            self._migrate_required_subtasks(connection)
            connection.execute(
                "INSERT OR IGNORE INTO relocation_plans (id, title) VALUES (?, ?)",
                (RELOCATION_PLAN_ID, RELOCATION_PLAN_TITLE),
            )
            connection.executemany(
                """
                INSERT OR IGNORE INTO phases (id, plan_id, title, position)
                VALUES (?, ?, ?, ?)
                """,
                (
                    (phase.id, RELOCATION_PLAN_ID, phase.title, phase.position)
                    for phase in DEFAULT_PHASES
                ),
            )
            connection.executemany(
                "UPDATE phases SET title = ?, position = ? WHERE id = ? AND plan_id = ?",
                (
                    (phase.title, phase.position, phase.id, RELOCATION_PLAN_ID)
                    for phase in DEFAULT_PHASES
                ),
            )

    @staticmethod
    def _migrate_required_subtasks(connection: sqlite3.Connection) -> None:
        expected = {"task_hierarchy", "task_parent_status_overrides"}
        present = {
            row["name"] for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ) if row["name"] in expected
        }
        if present and present != expected:
            raise RelocationPlanError(
                "Incomplete required-subtask schema; missing: "
                + ", ".join(sorted(expected - present)) + "."
            )
        if present == expected:
            expected_columns = {
                "task_hierarchy": {"child_task_id", "parent_task_id", "position"},
                "task_parent_status_overrides": {"parent_task_id", "status"},
            }
            for table, columns in expected_columns.items():
                actual = {row["name"] for row in connection.execute(f"PRAGMA table_info({table})")}
                if actual != columns:
                    raise RelocationPlanError(f"Unexpected columns in required-subtask table '{table}'.")
            hierarchy_indexes = {
                row["name"] for row in connection.execute("PRAGMA index_list(task_hierarchy)")
            }
            if "idx_task_hierarchy_parent_position" not in hierarchy_indexes:
                raise RelocationPlanError("Required-subtask ordering index is missing.")
            return
        connection.executescript(
            """
            BEGIN IMMEDIATE;
            CREATE TABLE task_hierarchy (
                child_task_id TEXT PRIMARY KEY REFERENCES tasks(id) ON DELETE CASCADE,
                parent_task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE RESTRICT,
                position INTEGER NOT NULL CHECK (position >= 0),
                CHECK (child_task_id <> parent_task_id)
            );
            CREATE INDEX idx_task_hierarchy_parent_position
                ON task_hierarchy(parent_task_id, position, child_task_id);
            CREATE TABLE task_parent_status_overrides (
                parent_task_id TEXT PRIMARY KEY REFERENCES tasks(id) ON DELETE CASCADE,
                status TEXT NOT NULL CHECK (status IN ('not_started', 'in_progress', 'completed'))
            );
            COMMIT;
            """
        )
    @staticmethod
    def _migrate_milestone_decision_foundation(
        connection: sqlite3.Connection,
    ) -> None:
        expected_tables = {"milestones", "decisions", "decision_options"}
        present_tables = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
            if row["name"] in expected_tables
        }
        if present_tables and present_tables != expected_tables:
            missing = ", ".join(sorted(expected_tables - present_tables))
            raise RelocationPlanError(
                f"Incomplete Milestone/Decision schema; missing: {missing}."
            )
        if present_tables == expected_tables:
            expected_columns = {
                "milestones": {
                    "id", "plan_id", "title", "description",
                    "target_earliest_date", "target_latest_date", "achieved_at",
                },
                "decisions": {
                    "id", "plan_id", "milestone_id", "title", "description",
                    "selected_option_id",
                },
                "decision_options": {
                    "id", "decision_id", "title", "description", "position",
                },
            }
            for table, columns in expected_columns.items():
                actual = {
                    row["name"]
                    for row in connection.execute(f"PRAGMA table_info({table})")
                }
                if actual != columns:
                    raise RelocationPlanError(
                        f"Unexpected columns in Increment-1 table '{table}'."
                    )
            expected_indexes = {
                "idx_milestones_plan_id",
                "idx_decisions_plan_id",
                "idx_decisions_milestone_id",
            }
            actual_indexes = {
                row["name"]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'index'"
                )
            }
            missing_indexes = expected_indexes - actual_indexes
            if missing_indexes:
                raise RelocationPlanError(
                    "Incomplete Increment-1 indexes: "
                    + ", ".join(sorted(missing_indexes))
                    + "."
                )
            return

        connection.executescript(
            """
            BEGIN IMMEDIATE;
            CREATE TABLE milestones (
                id TEXT PRIMARY KEY,
                plan_id TEXT NOT NULL REFERENCES relocation_plans(id),
                title TEXT NOT NULL,
                description TEXT,
                target_earliest_date TEXT CHECK (
                    target_earliest_date IS NULL OR (
                        date(target_earliest_date) IS NOT NULL
                        AND date(target_earliest_date) = target_earliest_date
                    )
                ),
                target_latest_date TEXT CHECK (
                    target_latest_date IS NULL OR (
                        date(target_latest_date) IS NOT NULL
                        AND date(target_latest_date) = target_latest_date
                    )
                ),
                achieved_at TEXT,
                CHECK (
                    target_latest_date IS NULL OR target_earliest_date IS NOT NULL
                ),
                CHECK (
                    target_latest_date IS NULL
                    OR target_latest_date >= target_earliest_date
                )
            );
            CREATE INDEX idx_milestones_plan_id ON milestones(plan_id);

            CREATE TABLE decisions (
                id TEXT PRIMARY KEY,
                plan_id TEXT NOT NULL REFERENCES relocation_plans(id),
                milestone_id TEXT NOT NULL REFERENCES milestones(id),
                title TEXT NOT NULL,
                description TEXT,
                selected_option_id TEXT,
                FOREIGN KEY (selected_option_id, id)
                    REFERENCES decision_options(id, decision_id)
                    DEFERRABLE INITIALLY DEFERRED
            );
            CREATE INDEX idx_decisions_plan_id ON decisions(plan_id);
            CREATE INDEX idx_decisions_milestone_id ON decisions(milestone_id);

            CREATE TABLE decision_options (
                id TEXT PRIMARY KEY,
                decision_id TEXT NOT NULL REFERENCES decisions(id) ON DELETE CASCADE,
                title TEXT NOT NULL COLLATE NOCASE,
                description TEXT,
                position INTEGER NOT NULL CHECK (position >= 0),
                UNIQUE (id, decision_id),
                UNIQUE (decision_id, position),
                UNIQUE (decision_id, title)
            );
            COMMIT;
            """
        )

    @staticmethod
    def _migrate_task_categories(connection: sqlite3.Connection) -> None:
        task_columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(tasks)")
        }
        if "category" not in task_columns:
            return
        connection.executescript(
            """
            BEGIN IMMEDIATE;
            CREATE TABLE tasks_category_migration (
                id TEXT PRIMARY KEY,
                plan_id TEXT NOT NULL REFERENCES relocation_plans(id),
                phase_id TEXT NOT NULL REFERENCES phases(id),
                title TEXT NOT NULL,
                description TEXT,
                status TEXT NOT NULL CHECK (status IN (
                    'not_started', 'in_progress', 'completed'
                )),
                start_date TEXT,
                due_date TEXT,
                priority TEXT NOT NULL CHECK (priority IN (
                    'low', 'medium', 'high', 'critical'
                ))
            );

            INSERT INTO tasks_category_migration (
                id, plan_id, phase_id, title, description, status,
                start_date, due_date, priority
            )
            SELECT id, plan_id, phase_id, title, description, status,
                start_date, due_date, priority
            FROM tasks;

            CREATE TABLE task_categories_category_migration (
                task_id TEXT NOT NULL REFERENCES tasks_category_migration(id) ON DELETE CASCADE,
                category TEXT NOT NULL CHECK (category IN (
                    'employment', 'family', 'financial', 'healthcare',
                    'housing', 'logistics'
                )),
                PRIMARY KEY (task_id, category)
            );
            INSERT INTO task_categories_category_migration (task_id, category)
            SELECT id, CASE category
                WHEN 'administrative' THEN 'logistics'
                ELSE category
            END
            FROM tasks;

            CREATE TABLE task_assignees_category_migration (
                task_id TEXT NOT NULL REFERENCES tasks_category_migration(id) ON DELETE CASCADE,
                position INTEGER NOT NULL CHECK (position >= 0),
                name TEXT NOT NULL,
                PRIMARY KEY (task_id, position),
                UNIQUE (task_id, name)
            );
            INSERT INTO task_assignees_category_migration
            SELECT * FROM task_assignees;

            CREATE TABLE task_dependencies_category_migration (
                task_id TEXT NOT NULL REFERENCES tasks_category_migration(id) ON DELETE CASCADE,
                dependency_task_id TEXT NOT NULL REFERENCES tasks_category_migration(id),
                position INTEGER NOT NULL CHECK (position >= 0),
                PRIMARY KEY (task_id, dependency_task_id),
                UNIQUE (task_id, position),
                CHECK (task_id <> dependency_task_id)
            );
            INSERT INTO task_dependencies_category_migration
            SELECT * FROM task_dependencies;

            DROP TABLE task_categories;
            DROP TABLE task_dependencies;
            DROP TABLE task_assignees;
            DROP TABLE tasks;
            ALTER TABLE tasks_category_migration RENAME TO tasks;
            ALTER TABLE task_categories_category_migration RENAME TO task_categories;
            ALTER TABLE task_assignees_category_migration RENAME TO task_assignees;
            ALTER TABLE task_dependencies_category_migration RENAME TO task_dependencies;
            COMMIT;
            """
        )

    def get_plan(self) -> RelocationPlan:
        with self._connect() as connection:
            plan_row = connection.execute(
                "SELECT id, title FROM relocation_plans WHERE id = ?",
                (RELOCATION_PLAN_ID,),
            ).fetchone()
            phase_rows = connection.execute(
                """
                SELECT id, title, position FROM phases
                WHERE plan_id = ? ORDER BY position, id
                """,
                (RELOCATION_PLAN_ID,),
            ).fetchall()
            task_rows = connection.execute(
                """
                SELECT tasks.* FROM tasks
                JOIN phases ON phases.id = tasks.phase_id
                WHERE tasks.plan_id = ?
                ORDER BY phases.position, tasks.id
                """,
                (RELOCATION_PLAN_ID,),
            ).fetchall()
            assignees = self._group_values(
                connection.execute(
                    """
                    SELECT task_id, name AS value FROM task_assignees
                    ORDER BY task_id, position
                    """
                ).fetchall()
            )
            category_rows = connection.execute(
                "SELECT task_id, category FROM task_categories"
            ).fetchall()
            categories_by_task: dict[str, set[str]] = {}
            for row in category_rows:
                categories_by_task.setdefault(row["task_id"], set()).add(row["category"])
            categories = {
                task_id: tuple(
                    category.value
                    for category in CATEGORY_ORDER
                    if category.value in selected
                )
                for task_id, selected in categories_by_task.items()
            }
            dependencies = self._group_values(
                connection.execute(
                    """
                    SELECT task_id, dependency_task_id AS value
                    FROM task_dependencies ORDER BY task_id, position
                    """
                ).fetchall()
            )
            hierarchy_rows = connection.execute(
                "SELECT child_task_id, parent_task_id, position FROM task_hierarchy "
                "ORDER BY parent_task_id, position, child_task_id"
            ).fetchall()
            override_rows = connection.execute(
                "SELECT parent_task_id, status FROM task_parent_status_overrides"
            ).fetchall()
            milestone_rows = connection.execute(
                """
                SELECT id, title, description, target_earliest_date,
                    target_latest_date, achieved_at
                FROM milestones WHERE plan_id = ? ORDER BY id
                """,
                (RELOCATION_PLAN_ID,),
            ).fetchall()
            decision_rows = connection.execute(
                """
                SELECT id, milestone_id, title, description, selected_option_id
                FROM decisions WHERE plan_id = ? ORDER BY id
                """,
                (RELOCATION_PLAN_ID,),
            ).fetchall()
            option_rows = connection.execute(
                """
                SELECT id, decision_id, title, description
                FROM decision_options ORDER BY decision_id, position
                """
            ).fetchall()

        if plan_row is None:
            raise RelocationPlanError("The singleton relocation plan is missing.")

        stored_status_by_id = {row["id"]: TaskStatus(row["status"]) for row in task_rows}
        parent_by_child = {row["child_task_id"]: row["parent_task_id"] for row in hierarchy_rows}
        position_by_child = {row["child_task_id"]: row["position"] for row in hierarchy_rows}
        children_by_parent: dict[str, list[str]] = {}
        for row in hierarchy_rows:
            children_by_parent.setdefault(row["parent_task_id"], []).append(row["child_task_id"])
        overrides = {row["parent_task_id"]: TaskStatus(row["status"]) for row in override_rows}
        automatic_by_parent: dict[str, TaskStatus] = {}
        for parent_id, child_ids in children_by_parent.items():
            child_statuses = [stored_status_by_id[child_id] for child_id in child_ids]
            automatic_by_parent[parent_id] = (
                TaskStatus.COMPLETED if all(status is TaskStatus.COMPLETED for status in child_statuses)
                else TaskStatus.IN_PROGRESS if any(status is not TaskStatus.NOT_STARTED for status in child_statuses)
                else TaskStatus.NOT_STARTED
            )
        effective_status_by_id = dict(stored_status_by_id)
        for parent_id, automatic in automatic_by_parent.items():
            effective_status_by_id[parent_id] = overrides.get(parent_id, automatic)
        tasks = tuple(
            Task(
                id=row["id"],
                title=row["title"],
                description=row["description"],
                phase_id=row["phase_id"],
                categories=categories.get(row["id"], ()),
                status=effective_status_by_id[row["id"]],
                assignees=assignees.get(row["id"], ()),
                start_date=row["start_date"],
                due_date=row["due_date"],
                priority=row["priority"],
                dependency_task_ids=dependencies.get(row["id"], ()),
                parent_task_id=parent_by_child.get(row["id"]),
                subtask_position=position_by_child.get(row["id"]),
                blocked=(
                    effective_status_by_id[row["id"]] is not TaskStatus.COMPLETED
                    and any(
                        effective_status_by_id[dependency_id] is not TaskStatus.COMPLETED
                        for dependency_id in (
                            dependencies.get(row["id"], ())
                            + (dependencies.get(parent_by_child[row["id"]], ()) if row["id"] in parent_by_child else ())
                        )
                    )
                ),
                stored_status=stored_status_by_id[row["id"]],
                automatic_status=automatic_by_parent.get(row["id"]),
                manual_status_override=overrides.get(row["id"]),
                is_parent=row["id"] in children_by_parent,
                subtask_count=len(children_by_parent.get(row["id"], ())),
                completed_subtask_count=sum(
                    stored_status_by_id[child_id] is TaskStatus.COMPLETED
                    for child_id in children_by_parent.get(row["id"], ())
                ),
            )
            for row in task_rows
        )
        milestones = tuple(
            Milestone(
                id=row["id"],
                title=row["title"],
                description=row["description"],
                target_earliest_date=row["target_earliest_date"],
                target_latest_date=row["target_latest_date"],
                status=(
                    MilestoneStatus.ACHIEVED
                    if row["achieved_at"] is not None
                    else MilestoneStatus.PENDING
                ),
                achieved_at=row["achieved_at"],
            )
            for row in milestone_rows
        )
        options_by_decision: dict[str, list[DecisionOptionFields]] = {}
        for row in option_rows:
            options_by_decision.setdefault(row["decision_id"], []).append(
                DecisionOptionFields(
                    id=row["id"],
                    title=row["title"],
                    description=row["description"],
                )
            )
        decisions = tuple(
            Decision(
                id=row["id"],
                title=row["title"],
                description=row["description"],
                milestone_id=row["milestone_id"],
                options=tuple(options_by_decision.get(row["id"], ())),
                status=(
                    DecisionStatus.RESOLVED
                    if row["selected_option_id"] is not None
                    else DecisionStatus.UNRESOLVED
                ),
                selected_option_id=row["selected_option_id"],
            )
            for row in decision_rows
        )
        return RelocationPlan(
            id=plan_row["id"],
            title=plan_row["title"],
            phases=tuple(Phase(**dict(row)) for row in phase_rows),
            tasks=tasks,
            milestones=milestones,
            decisions=decisions,
        )

    @staticmethod
    def _group_values(rows: Iterable[sqlite3.Row]) -> dict[str, tuple[str, ...]]:
        grouped: dict[str, list[str]] = {}
        for row in rows:
            grouped.setdefault(row["task_id"], []).append(row["value"])
        return {task_id: tuple(values) for task_id, values in grouped.items()}

    def create_task(self, task: TaskCreate) -> RelocationPlan:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if self._task_exists(connection, task.id):
                raise TaskAlreadyExistsError(f"Task '{task.id}' already exists.")
            self._validate_unique_title(
                connection, "tasks", RELOCATION_PLAN_ID, task.title
            )
            self._validate_task_bindings(
                connection, task.id, task.phase_id, task.dependency_task_ids
            )
            self._validate_hierarchy(connection, task.id, task.phase_id, task.parent_task_id)
            self._insert_task(connection, task.id, task)
            self._set_hierarchy(connection, task.id, task.parent_task_id, task.subtask_position)
            self._reject_cycles(connection)
        return self.get_plan()

    def update_task(self, task_id: str, task: TaskUpdate) -> RelocationPlan:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT plan_id, title, phase_id FROM tasks WHERE id = ?", (task_id,)
            ).fetchone()
            if existing is None:
                raise TaskNotFoundError(f"Task '{task_id}' does not exist.")
            self._validate_unique_title(
                connection,
                "tasks",
                existing["plan_id"],
                task.title,
                entity_id=task_id,
                existing_title=existing["title"],
            )
            existing_dependency_ids = {
                row["dependency_task_id"]
                for row in connection.execute(
                    "SELECT dependency_task_id FROM task_dependencies WHERE task_id = ?",
                    (task_id,),
                ).fetchall()
            }
            self._validate_task_bindings(
                connection,
                task_id,
                task.phase_id,
                task.dependency_task_ids,
                allowed_completed_dependency_ids=existing_dependency_ids,
            )
            self._validate_hierarchy(connection, task_id, task.phase_id, task.parent_task_id)
            children = [row["child_task_id"] for row in connection.execute(
                "SELECT child_task_id FROM task_hierarchy WHERE parent_task_id = ?", (task_id,)
            )]
            if children and task.phase_id != existing["phase_id"] and not task.confirm_parent_phase_move:
                raise ParentChangeConfirmationRequired(
                    "Moving this parent also moves all of its subtasks. Confirm the phase change to continue.",
                    "parent_phase_move_confirmation_required",
                )
            previous_parent = connection.execute(
                "SELECT parent_task_id FROM task_hierarchy WHERE child_task_id = ?", (task_id,)
            ).fetchone()
            previous_parent_id = previous_parent["parent_task_id"] if previous_parent else None
            previous_parent_effective = self._effective_parent_status(connection, previous_parent_id) if previous_parent_id else None
            connection.execute(
                """
                UPDATE tasks SET phase_id = ?, title = ?, description = ?,
                    status = ?, start_date = ?, due_date = ?, priority = ?
                WHERE id = ?
                """,
                (
                    task.phase_id,
                    task.title,
                    task.description,
                    task.status.value,
                    task.start_date.isoformat() if task.start_date else None,
                    task.due_date.isoformat() if task.due_date else None,
                    task.priority.value,
                    task_id,
                ),
            )
            self._replace_relations(
                connection,
                task_id,
                task.categories,
                task.assignees,
                task.dependency_task_ids,
            )
            if children and task.phase_id != existing["phase_id"]:
                connection.executemany(
                    "UPDATE tasks SET phase_id = ? WHERE id = ?",
                    ((task.phase_id, child_id) for child_id in children),
                )
            self._set_hierarchy(connection, task_id, task.parent_task_id, task.subtask_position)
            if previous_parent_id and previous_parent_id != task.parent_task_id:
                self._preserve_final_detached_parent_status(connection, previous_parent_id, previous_parent_effective)
            self._reject_cycles(connection)
        return self.get_plan()

    def update_task_status(self, task_id: str, status: TaskStatus, *, confirm_manual_override: bool = False) -> RelocationPlan:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if not self._task_exists(connection, task_id):
                raise TaskNotFoundError(f"Task '{task_id}' does not exist.")
            automatic = self._automatic_parent_status(connection, task_id)
            if automatic is not None:
                if status is automatic:
                    connection.execute("DELETE FROM task_parent_status_overrides WHERE parent_task_id = ?", (task_id,))
                else:
                    if not confirm_manual_override:
                        suffix = " Manually completing it may unblock downstream work." if status is TaskStatus.COMPLETED else ""
                        raise ParentChangeConfirmationRequired(
                            "This status conflicts with the required subtasks." + suffix + " Confirm a visible manual override to continue.",
                            "parent_status_override_confirmation_required",
                        )
                    connection.execute(
                        "INSERT INTO task_parent_status_overrides(parent_task_id, status) VALUES (?, ?) "
                        "ON CONFLICT(parent_task_id) DO UPDATE SET status = excluded.status",
                        (task_id, status.value),
                    )
            else:
                connection.execute("UPDATE tasks SET status = ? WHERE id = ?", (status.value, task_id))
        return self.get_plan()

    def return_parent_to_automatic_status(self, task_id: str) -> RelocationPlan:
        with self._connect() as connection:
            if self._automatic_parent_status(connection, task_id) is None:
                raise InvalidHierarchyError("Only a Task with subtasks has automatic status.")
            connection.execute("DELETE FROM task_parent_status_overrides WHERE parent_task_id = ?", (task_id,))
        return self.get_plan()

    def reorder_subtasks(
        self, parent_task_id: str, child_task_ids: tuple[str, ...]
    ) -> RelocationPlan:
        if len(set(child_task_ids)) != len(child_task_ids):
            raise InvalidHierarchyError(
                "Subtask order cannot contain duplicate Task IDs."
            )
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if not self._task_exists(connection, parent_task_id):
                raise TaskNotFoundError(f"Task '{parent_task_id}' does not exist.")
            current_rows = connection.execute(
                """
                SELECT child_task_id, position
                FROM task_hierarchy
                WHERE parent_task_id = ?
                ORDER BY position, child_task_id
                """,
                (parent_task_id,),
            ).fetchall()
            current_ids = tuple(row["child_task_id"] for row in current_rows)
            if (
                set(child_task_ids) != set(current_ids)
                or len(child_task_ids) != len(current_ids)
            ):
                raise InvalidHierarchyError(
                    "Submitted subtask IDs must exactly match this parent's current subtasks."
                )
            if child_task_ids != current_ids:
                cases = " ".join("WHEN ? THEN ?" for _ in child_task_ids)
                placeholders = ", ".join("?" for _ in child_task_ids)
                values: list[object] = []
                for position, child_task_id in enumerate(child_task_ids):
                    values.extend((child_task_id, position))
                values.extend((parent_task_id, *child_task_ids))
                connection.execute(
                    f"""
                    UPDATE task_hierarchy
                    SET position = CASE child_task_id {cases} ELSE position END
                    WHERE parent_task_id = ? AND child_task_id IN ({placeholders})
                    """,
                    values,
                )
        return self.get_plan()

    def create_milestone(self, milestone: MilestoneCreate) -> RelocationPlan:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if self._plan_item_id_exists(connection, milestone.id):
                raise PlanItemAlreadyExistsError(
                    f"Plan item '{milestone.id}' already exists."
                )
            self._validate_unique_title(
                connection, "milestones", RELOCATION_PLAN_ID, milestone.title
            )
            connection.execute(
                """
                INSERT INTO milestones (
                    id, plan_id, title, description,
                    target_earliest_date, target_latest_date, achieved_at
                ) VALUES (?, ?, ?, ?, ?, ?, NULL)
                """,
                (
                    milestone.id,
                    RELOCATION_PLAN_ID,
                    milestone.title,
                    milestone.description,
                    milestone.target_earliest_date.isoformat()
                    if milestone.target_earliest_date else None,
                    milestone.target_latest_date.isoformat()
                    if milestone.target_latest_date else None,
                ),
            )
        return self.get_plan()

    def update_milestone(
        self, milestone_id: str, milestone: MilestoneUpdate
    ) -> RelocationPlan:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT plan_id, title FROM milestones WHERE id = ?", (milestone_id,)
            ).fetchone()
            if existing is None:
                raise MilestoneNotFoundError(
                    f"Milestone '{milestone_id}' does not exist."
                )
            self._validate_unique_title(
                connection,
                "milestones",
                existing["plan_id"],
                milestone.title,
                entity_id=milestone_id,
                existing_title=existing["title"],
            )
            connection.execute(
                """
                UPDATE milestones SET title = ?, description = ?,
                    target_earliest_date = ?, target_latest_date = ?
                WHERE id = ?
                """,
                (
                    milestone.title,
                    milestone.description,
                    milestone.target_earliest_date.isoformat()
                    if milestone.target_earliest_date else None,
                    milestone.target_latest_date.isoformat()
                    if milestone.target_latest_date else None,
                    milestone_id,
                ),
            )
        return self.get_plan()

    def set_milestone_achievement(
        self, milestone_id: str, achieved: bool
    ) -> RelocationPlan:
        with self._connect() as connection:
            if not self._milestone_exists(connection, milestone_id):
                raise MilestoneNotFoundError(
                    f"Milestone '{milestone_id}' does not exist."
                )
            achieved_at = (
                datetime.now(timezone.utc).isoformat() if achieved else None
            )
            connection.execute(
                "UPDATE milestones SET achieved_at = ? WHERE id = ?",
                (achieved_at, milestone_id),
            )
        return self.get_plan()

    def create_decision(self, decision: DecisionCreate) -> RelocationPlan:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if self._plan_item_id_exists(connection, decision.id):
                raise PlanItemAlreadyExistsError(
                    f"Plan item '{decision.id}' already exists."
                )
            self._validate_unique_title(
                connection, "decisions", RELOCATION_PLAN_ID, decision.title
            )
            self._validate_milestone(connection, decision.milestone_id)
            self._validate_option_ids_available(connection, decision.options)
            connection.execute(
                """
                INSERT INTO decisions (
                    id, plan_id, milestone_id, title, description, selected_option_id
                ) VALUES (?, ?, ?, ?, ?, NULL)
                """,
                (
                    decision.id,
                    RELOCATION_PLAN_ID,
                    decision.milestone_id,
                    decision.title,
                    decision.description,
                ),
            )
            self._insert_decision_options(connection, decision.id, decision.options)
        return self.get_plan()

    def update_decision(
        self, decision_id: str, decision: DecisionUpdate
    ) -> RelocationPlan:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT plan_id, title, selected_option_id FROM decisions WHERE id = ?",
                (decision_id,),
            ).fetchone()
            if row is None:
                raise DecisionNotFoundError(
                    f"Decision '{decision_id}' does not exist."
                )
            self._validate_unique_title(
                connection,
                "decisions",
                row["plan_id"],
                decision.title,
                entity_id=decision_id,
                existing_title=row["title"],
            )
            self._validate_milestone(connection, decision.milestone_id)
            selected_option_id = row["selected_option_id"]
            option_ids = {option.id for option in decision.options}
            if selected_option_id is not None and selected_option_id not in option_ids:
                raise InvalidDecisionError(
                    "A selected Decision option cannot be removed during editing. "
                    "Change or clear the selection first."
                )
            self._validate_option_ids_available(
                connection, decision.options, decision_id=decision_id
            )
            connection.execute(
                """
                UPDATE decisions SET milestone_id = ?, title = ?, description = ?
                WHERE id = ?
                """,
                (
                    decision.milestone_id,
                    decision.title,
                    decision.description,
                    decision_id,
                ),
            )
            connection.execute(
                "DELETE FROM decision_options WHERE decision_id = ?", (decision_id,)
            )
            self._insert_decision_options(connection, decision_id, decision.options)
        return self.get_plan()

    def select_decision_option(
        self, decision_id: str, selected_option_id: str | None
    ) -> RelocationPlan:
        with self._connect() as connection:
            if not self._decision_exists(connection, decision_id):
                raise DecisionNotFoundError(
                    f"Decision '{decision_id}' does not exist."
                )
            if selected_option_id is not None:
                option = connection.execute(
                    """
                    SELECT 1 FROM decision_options
                    WHERE id = ? AND decision_id = ?
                    """,
                    (selected_option_id, decision_id),
                ).fetchone()
                if option is None:
                    raise InvalidDecisionError(
                        f"Option '{selected_option_id}' does not belong to "
                        f"Decision '{decision_id}'."
                    )
            connection.execute(
                "UPDATE decisions SET selected_option_id = ? WHERE id = ?",
                (selected_option_id, decision_id),
            )
        return self.get_plan()

    @staticmethod
    def _plan_item_id_exists(connection: sqlite3.Connection, item_id: str) -> bool:
        return any(
            connection.execute(
                f"SELECT 1 FROM {table} WHERE id = ?", (item_id,)
            ).fetchone()
            is not None
            for table in ("tasks", "milestones", "decisions", "decision_options")
        )

    @staticmethod
    def _milestone_exists(connection: sqlite3.Connection, milestone_id: str) -> bool:
        return connection.execute(
            "SELECT 1 FROM milestones WHERE id = ?", (milestone_id,)
        ).fetchone() is not None

    @staticmethod
    def _decision_exists(connection: sqlite3.Connection, decision_id: str) -> bool:
        return connection.execute(
            "SELECT 1 FROM decisions WHERE id = ?", (decision_id,)
        ).fetchone() is not None

    def _validate_milestone(
        self, connection: sqlite3.Connection, milestone_id: str
    ) -> None:
        if not self._milestone_exists(connection, milestone_id):
            raise InvalidDecisionError(
                f"Milestone '{milestone_id}' does not exist in the relocation plan."
            )

    @staticmethod
    def _validate_option_ids_available(
        connection: sqlite3.Connection,
        options: tuple[DecisionOptionFields, ...],
        *,
        decision_id: str | None = None,
    ) -> None:
        for option in options:
            row = connection.execute(
                "SELECT decision_id FROM decision_options WHERE id = ?", (option.id,)
            ).fetchone()
            if row is not None and row["decision_id"] != decision_id:
                raise PlanItemAlreadyExistsError(
                    f"Plan item '{option.id}' already exists."
                )
            for table in ("tasks", "milestones", "decisions"):
                if connection.execute(
                    f"SELECT 1 FROM {table} WHERE id = ?", (option.id,)
                ).fetchone() is not None:
                    raise PlanItemAlreadyExistsError(
                        f"Plan item '{option.id}' already exists."
                    )

    @staticmethod
    def _insert_decision_options(
        connection: sqlite3.Connection,
        decision_id: str,
        options: tuple[DecisionOptionFields, ...],
    ) -> None:
        connection.executemany(
            """
            INSERT INTO decision_options (
                id, decision_id, title, description, position
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                (option.id, decision_id, option.title, option.description, position)
                for position, option in enumerate(options)
            ),
        )

    @staticmethod
    def _task_exists(connection: sqlite3.Connection, task_id: str) -> bool:
        return connection.execute(
            "SELECT 1 FROM tasks WHERE id = ?", (task_id,)
        ).fetchone() is not None

    @staticmethod
    def _validate_unique_title(
        connection: sqlite3.Connection,
        table: str,
        plan_id: str,
        title: str,
        *,
        entity_id: str | None = None,
        existing_title: str | None = None,
    ) -> None:
        canonical_title = canonicalize_plan_item_title(title)
        if (
            existing_title is not None
            and canonical_title == canonicalize_plan_item_title(existing_title)
        ):
            return
        rows = connection.execute(
            f"SELECT id, title FROM {table} WHERE plan_id = ?",
            (plan_id,),
        ).fetchall()
        if not any(
            row["id"] != entity_id
            and canonicalize_plan_item_title(row["title"]) == canonical_title
            for row in rows
        ):
            return
        error_by_table = {
            "tasks": DuplicateTaskTitleError,
            "milestones": DuplicateMilestoneTitleError,
            "decisions": DuplicateDecisionTitleError,
        }
        raise error_by_table[table]()

    def _validate_task_bindings(
        self,
        connection: sqlite3.Connection,
        task_id: str,
        phase_id: str,
        dependency_ids: tuple[str, ...],
        *,
        allowed_completed_dependency_ids: set[str] | None = None,
    ) -> None:
        phase = connection.execute(
            "SELECT 1 FROM phases WHERE id = ? AND plan_id = ?",
            (phase_id, RELOCATION_PLAN_ID),
        ).fetchone()
        if phase is None:
            raise InvalidPhaseError(
                f"Phase '{phase_id}' does not exist in the relocation plan."
            )
        if task_id in dependency_ids:
            raise InvalidDependencyError("A task cannot depend on itself.")
        existing = (
            {
                row["id"]
                for row in connection.execute(
                    "SELECT id FROM tasks WHERE id IN "
                    f"({','.join('?' for _ in dependency_ids)})",
                    dependency_ids,
                ).fetchall()
            }
            if dependency_ids
            else set()
        )
        missing = set(dependency_ids) - existing
        if missing:
            raise InvalidDependencyError(
                f"Dependency task(s) do not exist: {', '.join(sorted(missing))}."
            )
        completed = (
            {
                row["id"]
                for row in connection.execute(
                    "SELECT id FROM tasks WHERE status = ? AND id IN "
                    f"({','.join('?' for _ in dependency_ids)})",
                    (TaskStatus.COMPLETED.value, *dependency_ids),
                ).fetchall()
            }
            if dependency_ids
            else set()
        )
        newly_completed = completed - (allowed_completed_dependency_ids or set())
        if newly_completed:
            raise InvalidDependencyError(
                "Completed task(s) cannot be added as dependencies: "
                f"{', '.join(sorted(newly_completed))}."
            )

    def _validate_hierarchy(
        self, connection: sqlite3.Connection, task_id: str, phase_id: str,
        parent_task_id: str | None,
    ) -> None:
        if parent_task_id is None:
            return
        if parent_task_id == task_id:
            raise InvalidHierarchyError("A Task cannot be part of itself.")
        parent = connection.execute(
            "SELECT phase_id FROM tasks WHERE id = ? AND plan_id = ?",
            (parent_task_id, RELOCATION_PLAN_ID),
        ).fetchone()
        if parent is None:
            raise InvalidHierarchyError(f"Parent Task '{parent_task_id}' does not exist in this Plan.")
        if parent["phase_id"] != phase_id:
            raise InvalidHierarchyError("A parent and its subtasks must share a phase.")
        if connection.execute(
            "SELECT 1 FROM task_hierarchy WHERE child_task_id = ?", (parent_task_id,)
        ).fetchone():
            raise InvalidHierarchyError("A subtask cannot be a parent.")
        if connection.execute(
            "SELECT 1 FROM task_hierarchy WHERE parent_task_id = ?", (task_id,)
        ).fetchone():
            raise InvalidHierarchyError("A parent cannot become a subtask.")

    @staticmethod
    def _set_hierarchy(
        connection: sqlite3.Connection, task_id: str,
        parent_task_id: str | None, position: int | None,
    ) -> None:
        connection.execute("DELETE FROM task_hierarchy WHERE child_task_id = ?", (task_id,))
        if parent_task_id is None:
            return
        if position is None:
            row = connection.execute(
                "SELECT COALESCE(MAX(position), -1) + 1 AS next_position FROM task_hierarchy WHERE parent_task_id = ?",
                (parent_task_id,),
            ).fetchone()
            position = row["next_position"]
        connection.execute(
            "INSERT INTO task_hierarchy(child_task_id, parent_task_id, position) VALUES (?, ?, ?)",
            (task_id, parent_task_id, position),
        )

    @staticmethod
    def _automatic_parent_status(connection: sqlite3.Connection, parent_task_id: str) -> TaskStatus | None:
        rows = connection.execute(
            "SELECT tasks.status FROM task_hierarchy JOIN tasks ON tasks.id = task_hierarchy.child_task_id "
            "WHERE task_hierarchy.parent_task_id = ?",
            (parent_task_id,),
        ).fetchall()
        if not rows:
            return None
        statuses = [TaskStatus(row["status"]) for row in rows]
        if all(status is TaskStatus.COMPLETED for status in statuses):
            return TaskStatus.COMPLETED
        if any(status is not TaskStatus.NOT_STARTED for status in statuses):
            return TaskStatus.IN_PROGRESS
        return TaskStatus.NOT_STARTED

    def _effective_parent_status(self, connection: sqlite3.Connection, parent_task_id: str) -> TaskStatus | None:
        automatic = self._automatic_parent_status(connection, parent_task_id)
        if automatic is None:
            return None
        row = connection.execute(
            "SELECT status FROM task_parent_status_overrides WHERE parent_task_id = ?", (parent_task_id,)
        ).fetchone()
        return TaskStatus(row["status"]) if row else automatic

    def _preserve_final_detached_parent_status(
        self, connection: sqlite3.Connection, parent_task_id: str,
        effective_status: TaskStatus | None,
    ) -> None:
        if self._automatic_parent_status(connection, parent_task_id) is not None:
            return
        if effective_status is not None:
            connection.execute(
                "UPDATE tasks SET status = ? WHERE id = ?", (effective_status.value, parent_task_id)
            )
        connection.execute(
            "DELETE FROM task_parent_status_overrides WHERE parent_task_id = ?", (parent_task_id,)
        )

    def _insert_task(
        self, connection: sqlite3.Connection, task_id: str, task: TaskCreate
    ) -> None:
        connection.execute(
            """
            INSERT INTO tasks (
                id, plan_id, phase_id, title, description, status,
                start_date, due_date, priority
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task_id,
                RELOCATION_PLAN_ID,
                task.phase_id,
                task.title,
                task.description,
                task.status.value,
                task.start_date.isoformat() if task.start_date else None,
                task.due_date.isoformat() if task.due_date else None,
                task.priority.value,
            ),
        )
        self._replace_relations(
            connection, task_id, task.categories, task.assignees, task.dependency_task_ids
        )

    @staticmethod
    def _replace_relations(
        connection: sqlite3.Connection,
        task_id: str,
        categories: tuple[TaskCategory, ...],
        assignees: tuple[str, ...],
        dependencies: tuple[str, ...],
    ) -> None:
        connection.execute("DELETE FROM task_categories WHERE task_id = ?", (task_id,))
        connection.execute("DELETE FROM task_assignees WHERE task_id = ?", (task_id,))
        connection.execute("DELETE FROM task_dependencies WHERE task_id = ?", (task_id,))
        connection.executemany(
            "INSERT INTO task_categories (task_id, category) VALUES (?, ?)",
            ((task_id, category.value) for category in categories),
        )
        connection.executemany(
            "INSERT INTO task_assignees (task_id, position, name) VALUES (?, ?, ?)",
            ((task_id, position, name) for position, name in enumerate(assignees)),
        )
        connection.executemany(
            """
            INSERT INTO task_dependencies (task_id, dependency_task_id, position)
            VALUES (?, ?, ?)
            """,
            (
                (task_id, dependency_id, position)
                for position, dependency_id in enumerate(dependencies)
            ),
        )

    @staticmethod
    def _reject_cycles(connection: sqlite3.Connection) -> None:
        graph: dict[str, set[str]] = {
            row["id"]: set()
            for row in connection.execute("SELECT id FROM tasks").fetchall()
        }
        for row in connection.execute(
            "SELECT task_id, dependency_task_id FROM task_dependencies"
        ).fetchall():
            graph[row["task_id"]].add(row["dependency_task_id"])

        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(task_id: str) -> None:
            if task_id in visiting:
                raise DependencyCycleError("Task dependencies cannot contain a cycle.")
            if task_id in visited:
                return
            visiting.add(task_id)
            for dependency_id in graph[task_id]:
                visit(dependency_id)
            visiting.remove(task_id)
            visited.add(task_id)

        for task_id in graph:
            visit(task_id)
