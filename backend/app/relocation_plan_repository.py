from __future__ import annotations

import sqlite3
from collections.abc import Iterable
from pathlib import Path

from app.relocation_plan_models import (
    Phase,
    RelocationPlan,
    Task,
    TaskCreate,
    TaskStatus,
    TaskUpdate,
)


RELOCATION_PLAN_ID = "family-relocation-plan"
RELOCATION_PLAN_TITLE = "Relocate the family to Northern California"
DEFAULT_PHASES = (
    Phase(id="decide", title="Decide where and how to move", position=10),
    Phase(id="prepare", title="Prepare for the move", position=20),
    Phase(id="move", title="Complete the move", position=30),
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


class DependencyCycleError(RelocationPlanError):
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
                    category TEXT NOT NULL CHECK (category IN (
                        'administrative', 'employment', 'family', 'financial',
                        'healthcare', 'housing', 'logistics'
                    )),
                    status TEXT NOT NULL CHECK (status IN (
                        'not_started', 'in_progress', 'completed'
                    )),
                    start_date TEXT,
                    due_date TEXT,
                    priority TEXT NOT NULL CHECK (priority IN (
                        'low', 'medium', 'high', 'critical'
                    ))
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
            dependencies = self._group_values(
                connection.execute(
                    """
                    SELECT task_id, dependency_task_id AS value
                    FROM task_dependencies ORDER BY task_id, position
                    """
                ).fetchall()
            )

        if plan_row is None:
            raise RelocationPlanError("The singleton relocation plan is missing.")

        status_by_id = {row["id"]: TaskStatus(row["status"]) for row in task_rows}
        tasks = tuple(
            Task(
                id=row["id"],
                title=row["title"],
                description=row["description"],
                phase_id=row["phase_id"],
                category=row["category"],
                status=row["status"],
                assignees=assignees.get(row["id"], ()),
                start_date=row["start_date"],
                due_date=row["due_date"],
                priority=row["priority"],
                dependency_task_ids=dependencies.get(row["id"], ()),
                blocked=(
                    status_by_id[row["id"]] is not TaskStatus.COMPLETED
                    and any(
                        status_by_id[dependency_id] is not TaskStatus.COMPLETED
                        for dependency_id in dependencies.get(row["id"], ())
                    )
                ),
            )
            for row in task_rows
        )
        return RelocationPlan(
            id=plan_row["id"],
            title=plan_row["title"],
            phases=tuple(Phase(**dict(row)) for row in phase_rows),
            tasks=tasks,
        )

    @staticmethod
    def _group_values(rows: Iterable[sqlite3.Row]) -> dict[str, tuple[str, ...]]:
        grouped: dict[str, list[str]] = {}
        for row in rows:
            grouped.setdefault(row["task_id"], []).append(row["value"])
        return {task_id: tuple(values) for task_id, values in grouped.items()}

    def create_task(self, task: TaskCreate) -> RelocationPlan:
        with self._connect() as connection:
            if self._task_exists(connection, task.id):
                raise TaskAlreadyExistsError(f"Task '{task.id}' already exists.")
            self._validate_task_bindings(
                connection, task.id, task.phase_id, task.dependency_task_ids
            )
            self._insert_task(connection, task.id, task)
            self._reject_cycles(connection)
        return self.get_plan()

    def update_task(self, task_id: str, task: TaskUpdate) -> RelocationPlan:
        with self._connect() as connection:
            if not self._task_exists(connection, task_id):
                raise TaskNotFoundError(f"Task '{task_id}' does not exist.")
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
            connection.execute(
                """
                UPDATE tasks SET phase_id = ?, title = ?, description = ?,
                    category = ?, status = ?, start_date = ?, due_date = ?, priority = ?
                WHERE id = ?
                """,
                (
                    task.phase_id,
                    task.title,
                    task.description,
                    task.category.value,
                    task.status.value,
                    task.start_date.isoformat() if task.start_date else None,
                    task.due_date.isoformat() if task.due_date else None,
                    task.priority.value,
                    task_id,
                ),
            )
            self._replace_relations(
                connection, task_id, task.assignees, task.dependency_task_ids
            )
            self._reject_cycles(connection)
        return self.get_plan()

    def update_task_status(self, task_id: str, status: TaskStatus) -> RelocationPlan:
        with self._connect() as connection:
            if not self._task_exists(connection, task_id):
                raise TaskNotFoundError(f"Task '{task_id}' does not exist.")
            connection.execute(
                "UPDATE tasks SET status = ? WHERE id = ?", (status.value, task_id)
            )
        return self.get_plan()

    @staticmethod
    def _task_exists(connection: sqlite3.Connection, task_id: str) -> bool:
        return connection.execute(
            "SELECT 1 FROM tasks WHERE id = ?", (task_id,)
        ).fetchone() is not None

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

    def _insert_task(
        self, connection: sqlite3.Connection, task_id: str, task: TaskCreate
    ) -> None:
        connection.execute(
            """
            INSERT INTO tasks (
                id, plan_id, phase_id, title, description, category, status,
                start_date, due_date, priority
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task_id,
                RELOCATION_PLAN_ID,
                task.phase_id,
                task.title,
                task.description,
                task.category.value,
                task.status.value,
                task.start_date.isoformat() if task.start_date else None,
                task.due_date.isoformat() if task.due_date else None,
                task.priority.value,
            ),
        )
        self._replace_relations(
            connection, task_id, task.assignees, task.dependency_task_ids
        )

    @staticmethod
    def _replace_relations(
        connection: sqlite3.Connection,
        task_id: str,
        assignees: tuple[str, ...],
        dependencies: tuple[str, ...],
    ) -> None:
        connection.execute("DELETE FROM task_assignees WHERE task_id = ?", (task_id,))
        connection.execute("DELETE FROM task_dependencies WHERE task_id = ?", (task_id,))
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
