"""Locked durable coordination state with no provider execution capability."""

from __future__ import annotations

import fcntl
import json
import os
import tempfile
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Callable, Mapping

from v4_formal_evaluation_live_cases import (
    AiCaseEnvelopeError, build_all_ai_case_envelopes, envelope_digest_map,
    validate_ai_case_envelopes,
)
from v4_formal_evaluation_live_models import (
    AGGREGATE_ID, AI_CASE_ORDER, CASE_ORDER, EMPTY_CASE_IDS, MAX_TOKEN_PREFLIGHTS,
    AggregateFoundationError, canonical_json, digest, immutable_package,
    package_identity, validate_human_label, validate_zero_counters,
)
from v4_formal_evaluation_live_budget import (
    BudgetError, build_preflight_reservation, derive_budget_accounting,
    enforce_prospective_capacity, validate_reservation,
)

STATE_VERSION = 1
JOURNAL_VERSION = 1
AGGREGATE_STATES = (
    "prepared", "approved", "in_progress", "ready_to_finalize",
    "expired_paused", "abandoned", "closed",
)
CASE_STATES = ("untouched", "in_progress", "awaiting_acknowledgement", "terminal")
OPERATION_STATES = {
    "aggregate_initialized": (None, "prepared"),
    "aggregate_approved": ("prepared", "approved"),
    "aggregate_started": ("approved", "in_progress"),
    "aggregate_expired": ({"prepared", "approved", "in_progress"}, "expired_paused"),
    "aggregate_ready_to_finalize": ("in_progress", "ready_to_finalize"),
    "aggregate_abandoned": ({"prepared", "approved", "in_progress", "expired_paused"}, "abandoned"),
    "aggregate_closed": ({"ready_to_finalize", "abandoned"}, "closed"),
    "deterministic_case_completed": ("in_progress", "in_progress"),
    "ai_case_envelopes_bound": ("in_progress", "in_progress"),
    "preflight_grant_prepared": ("in_progress", "in_progress"),
    "provider_budget_reserved": ("in_progress", "in_progress"),
    "provider_budget_released": ({"in_progress", "expired_paused"}, {"in_progress", "expired_paused"}),
}
TERMINAL_STATES = {"abandoned", "closed"}


class AggregateStateError(AggregateFoundationError):
    pass


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_time(value: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise AggregateStateError("timestamp must use canonical UTC Z form")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as error:
        raise AggregateStateError("timestamp is malformed") from error
    if parsed.tzinfo != timezone.utc:
        raise AggregateStateError("timestamp must be UTC")
    return parsed


def format_time(value: datetime) -> str:
    if value.tzinfo is None:
        raise AggregateStateError("timestamp must be timezone-aware")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def default_root() -> Path:
    repo = Path(__file__).resolve().parents[3]
    return repo / ".local/evaluations/suggest-moving-service-questions" / AGGREGATE_ID


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _atomic_json(path: Path, document: Mapping[str, object], before_replace: Callable[[], None] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w") as handle:
            handle.write(canonical_json(document) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        if before_replace is not None:
            before_replace()
        os.replace(temporary, path)
        _fsync_directory(path.parent)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextmanager
def _lock(root: Path):
    root.mkdir(parents=True, exist_ok=True)
    path = root / "aggregate.lock"
    with path.open("a+b") as handle:
        os.chmod(path, 0o600)
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        yield
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def derive_next_case(state: Mapping[str, object]) -> str | None:
    acknowledgement = state["acknowledgement"]
    if state["status"] != "in_progress" or acknowledgement["acknowledgement_required"]:
        return None
    cases = state["cases"]
    if any(
        cases[case_id]["coordination_status"] in {"in_progress", "awaiting_acknowledgement"}
        for case_id in CASE_ORDER
    ):
        return None
    return next(
        (case_id for case_id in AI_CASE_ORDER if cases[case_id]["coordination_status"] != "terminal"),
        None,
    )


def _neutral_acknowledgement() -> dict[str, object]:
    return {
        "acknowledgement_required": False,
        "acknowledged": False,
        "blocking_case_id": None,
        "blocking_outcome_digest": None,
    }


def _validate_acknowledgement(value: object) -> None:
    if not isinstance(value, dict) or set(value) != {
        "acknowledgement_required", "acknowledged", "blocking_case_id",
        "blocking_outcome_digest",
    }:
        raise AggregateStateError("acknowledgement coordination fields are malformed")
    required = value["acknowledgement_required"]
    if not isinstance(required, bool) or value["acknowledged"] is not False:
        raise AggregateStateError("acknowledgement state is unavailable before Milestone 11")
    if not required:
        if value["blocking_case_id"] is not None or value["blocking_outcome_digest"] is not None:
            raise AggregateStateError("clear acknowledgement state cannot retain a block")
        return
    if value["blocking_case_id"] not in CASE_ORDER:
        raise AggregateStateError("acknowledgement block case is not bound")
    outcome = value["blocking_outcome_digest"]
    if not isinstance(outcome, str) or len(outcome) != 64 or any(character not in "0123456789abcdef" for character in outcome):
        raise AggregateStateError("acknowledgement block requires an outcome digest")


def _all_cases_terminal(state: Mapping[str, object]) -> bool:
    return all(state["cases"][case_id]["coordination_status"] == "terminal" for case_id in CASE_ORDER)


def _event_digest(event: Mapping[str, object]) -> str:
    unsigned = {key: value for key, value in event.items() if key != "event_sha256"}
    unsigned["after_state"] = dict(unsigned["after_state"], history_head_sha256="<event>")
    return digest(unsigned)


class AggregateStore:
    def __init__(
        self,
        root: Path | None = None,
        clock: Callable[[], datetime] = utc_now,
        fault_injector: Callable[[str], None] | None = None,
    ) -> None:
        self.root = root or default_root()
        self.snapshot_path = self.root / "aggregate.json"
        self.journal_path = self.root / "aggregate-history.json"
        self.clock = clock
        self.fault_injector = fault_injector

    def _fault(self, boundary: str) -> None:
        if self.fault_injector is not None:
            self.fault_injector(boundary)

    def initialize(self, operator: str, reviewer: str) -> Mapping[str, object]:
        validate_human_label(operator, "operator")
        validate_human_label(reviewer, "reviewer")
        package = immutable_package()
        now = self.clock()
        with _lock(self.root):
            if self.journal_path.exists():
                current = self._load_unlocked(observe_expiry=False, recover_projection=True)
                if (
                    current["operator"] == operator
                    and current["reviewer"] == reviewer
                    and current["status"] == "prepared"
                    and all(item["coordination_status"] == "untouched" for item in current["cases"].values())
                ):
                    return current
                raise AggregateStateError("conflicting aggregate initialization; existing state is never reset")
            if self.snapshot_path.exists():
                raise AggregateStateError("projection exists without authoritative aggregate history")
            stale = [path for path in self.root.iterdir() if path.is_file() and path.name != "aggregate.lock"]
            if stale:
                raise AggregateStateError("conflicting local aggregate artifacts require review")
            state = {
                "state_version": STATE_VERSION,
                "aggregate_id": AGGREGATE_ID,
                "package_identity_sha256": digest(package),
                "immutable_package": package,
                "operator": operator,
                "reviewer": reviewer,
                "status": "prepared",
                "initialized_at": format_time(now),
                "expires_at": format_time(now + timedelta(days=7)),
                "coordination_only": True,
                "provider_authority": False,
                "ai_case_envelopes": {},
                "preflight_grants": {},
                "provider_budget_reservations": {},
                "budget_accounting": derive_budget_accounting({}),
                "cases": {
                    item["case_id"]: {
                        "case_id": item["case_id"],
                        "deterministic_case_input_sha256": item["deterministic_case_input_sha256"],
                        "coordination_status": "untouched",
                        "deterministic_initialization_pending": item["case_id"] in EMPTY_CASE_IDS,
                        "deterministic_outcome": None,
                    }
                    for item in package["case_bindings"]
                },
                "counters": {
                    "token_preflights_consumed": 0,
                    "token_preflights_reserved": 0,
                    "generations_consumed": 0,
                    "generations_reserved": 0,
                    "retries": 0,
                    "provider_spend_reserved_usd": "0.00",
                    "provider_spend_consumed_usd": "0.00",
                },
                "acknowledgement": _neutral_acknowledgement(),
                "extension_history": [],
                "next_case_id": None,
                "history_count": 1,
                "history_head_sha256": "<event>",
            }
            state["next_case_id"] = derive_next_case(state)
            event = self._make_event(None, state, "aggregate_initialized", {}, occurred_at=now)
            state = event["after_state"]
            journal = self._initial_journal([event])
            self._validate_journal(journal)
            self._commit(journal, state)
            return state

    def load(self, observe_expiry: bool = True) -> Mapping[str, object]:
        with _lock(self.root):
            return self._load_unlocked(observe_expiry=observe_expiry, recover_projection=True)

    def resume(self, reviewer: str) -> Mapping[str, object]:
        validate_human_label(reviewer, "reviewer")
        with _lock(self.root):
            state = self._load_unlocked(observe_expiry=True, recover_projection=True)
            if reviewer != state["reviewer"]:
                raise AggregateStateError("reviewer does not match initialized audit label")
            if state["status"] == "prepared":
                state = self._append_transition(state, "approved", "aggregate_approved", {"reviewer": reviewer})
            if state["status"] == "approved":
                return self._append_transition(state, "in_progress", "aggregate_started", {"reviewer": reviewer})
            if state["status"] == "expired_paused":
                raise AggregateStateError("extension is fail-closed and owned by Milestone 12")
            if state["status"] == "in_progress":
                return state
            raise AggregateStateError("aggregate cannot resume from its current state")

    def close(self, reviewer: str, abandon: bool = False) -> Mapping[str, object]:
        validate_human_label(reviewer, "reviewer")
        with _lock(self.root):
            state = self._load_unlocked(observe_expiry=True, recover_projection=True)
            if reviewer != state["reviewer"]:
                raise AggregateStateError("reviewer mismatch")
            if abandon and state["status"] in {"prepared", "approved", "in_progress", "expired_paused"}:
                state = self._append_transition(state, "abandoned", "aggregate_abandoned", {"reviewer": reviewer})
            if state["status"] not in {"ready_to_finalize", "abandoned"}:
                raise AggregateStateError("close requires ready_to_finalize or explicit abandonment")
            return self._append_transition(state, "closed", "aggregate_closed", {"reviewer": reviewer})

    def request_extension(self, reviewer: str, reason: str) -> None:
        validate_human_label(reviewer, "reviewer")
        raise AggregateStateError("reviewed extension is structurally reserved for Milestone 12 and fails closed")

    def _initial_journal(self, events: list[Mapping[str, object]]) -> dict[str, object]:
        return {
            "journal_version": JOURNAL_VERSION,
            "aggregate_id": AGGREGATE_ID,
            "package_identity_sha256": package_identity(),
            "genesis_sha256": digest({"aggregate_id": AGGREGATE_ID, "package_identity_sha256": package_identity()}),
            "events": events,
        }

    def _load_unlocked(self, observe_expiry: bool, recover_projection: bool) -> dict[str, object]:
        journal = self._read_journal()
        states = self._validate_journal(journal)
        canonical = states[-1]
        projection = self._read_projection_optional()
        if projection != canonical:
            if not recover_projection or not self._projection_is_recoverable(projection, states):
                raise AggregateStateError("aggregate projection conflicts with authoritative history")
            _atomic_json(self.snapshot_path, canonical)
        if (
            observe_expiry
            and canonical["status"] in {"prepared", "approved", "in_progress"}
            and self.clock() >= parse_time(canonical["expires_at"])
        ):
            canonical = self._append_transition(canonical, "expired_paused", "aggregate_expired", {})
        return canonical

    def _read_journal(self) -> dict[str, object]:
        try:
            journal = json.loads(self.journal_path.read_text())
        except (OSError, json.JSONDecodeError) as error:
            raise AggregateStateError("aggregate history is missing or malformed") from error
        if not isinstance(journal, dict):
            raise AggregateStateError("aggregate history is malformed")
        return journal

    def _read_projection_optional(self) -> dict[str, object] | None:
        if not self.snapshot_path.exists():
            return None
        try:
            projection = json.loads(self.snapshot_path.read_text())
        except (OSError, json.JSONDecodeError) as error:
            raise AggregateStateError("aggregate projection is malformed") from error
        if not isinstance(projection, dict):
            raise AggregateStateError("aggregate projection is malformed")
        return projection

    def _projection_is_recoverable(self, projection: Mapping[str, object] | None, states: list[dict[str, object]]) -> bool:
        if projection is None:
            return True
        return any(projection == prior for prior in states[:-1])

    def _validate_journal(self, journal: Mapping[str, object]) -> list[dict[str, object]]:
        expected_keys = {"journal_version", "aggregate_id", "package_identity_sha256", "genesis_sha256", "events"}
        expected_genesis = digest({"aggregate_id": AGGREGATE_ID, "package_identity_sha256": package_identity()})
        if (
            set(journal) != expected_keys
            or journal.get("journal_version") != JOURNAL_VERSION
            or journal.get("aggregate_id") != AGGREGATE_ID
            or journal.get("package_identity_sha256") != package_identity()
            or journal.get("genesis_sha256") != expected_genesis
        ):
            raise AggregateStateError("aggregate history genesis mismatch")
        events = journal.get("events")
        if not isinstance(events, list) or not events:
            raise AggregateStateError("aggregate history must contain initialization")
        previous_state: dict[str, object] | None = None
        previous_digest = expected_genesis
        previous_time: datetime | None = None
        states: list[dict[str, object]] = []
        for sequence, event in enumerate(events, 1):
            if not isinstance(event, dict) or set(event) != {
                "sequence", "operation", "occurred_at", "metadata", "previous_sha256",
                "before_state", "after_state", "event_sha256",
            }:
                raise AggregateStateError("aggregate history event schema mismatch")
            occurred_at = parse_time(event["occurred_at"])
            if previous_time is not None and occurred_at < previous_time:
                raise AggregateStateError("aggregate history timestamps are not monotonic")
            if (
                event["sequence"] != sequence
                or event["previous_sha256"] != previous_digest
                or event["event_sha256"] != _event_digest(event)
                or event["before_state"] != previous_state
            ):
                raise AggregateStateError("aggregate history chain or continuity mismatch")
            self._validate_operation_semantics(event, previous_time)
            after = event["after_state"]
            if after["history_count"] != sequence or after["history_head_sha256"] != event["event_sha256"]:
                raise AggregateStateError("aggregate history count or head mismatch")
            self._validate_state(after)
            states.append(after)
            previous_state = after
            previous_digest = event["event_sha256"]
            previous_time = occurred_at
        return states

    def _validate_operation_semantics(self, event: Mapping[str, object], previous_time: datetime | None) -> None:
        operation = event["operation"]
        if operation not in OPERATION_STATES:
            raise AggregateStateError("aggregate history operation is unavailable through Milestone 4")
        before, after = event["before_state"], event["after_state"]
        expected_before, expected_after = OPERATION_STATES[operation]
        actual_before = None if before is None else before.get("status")
        before_matches = actual_before in expected_before if isinstance(expected_before, set) else actual_before == expected_before
        actual_after = None if not isinstance(after, dict) else after.get("status")
        after_matches = actual_after in expected_after if isinstance(expected_after, set) else actual_after == expected_after
        if not before_matches or not after_matches:
            raise AggregateStateError("aggregate operation state transition mismatch")
        occurred_at = parse_time(event["occurred_at"])
        metadata = event["metadata"]
        if not isinstance(metadata, dict):
            raise AggregateStateError("aggregate event metadata is malformed")
        if operation == "aggregate_initialized":
            if previous_time is not None or metadata or occurred_at != parse_time(after["initialized_at"]):
                raise AggregateStateError("aggregate initialization event semantics mismatch")
            self._validate_initial_state(after)
            return
        if operation == "deterministic_case_completed":
            self._validate_deterministic_completion(event)
            return
        if operation == "ai_case_envelopes_bound":
            self._validate_ai_envelope_binding(event)
            return
        if operation == "preflight_grant_prepared":
            self._validate_preflight_grant_preparation(event)
            return
        if operation == "provider_budget_reserved":
            self._validate_budget_reservation_event(event)
            return
        if operation == "provider_budget_released":
            self._validate_budget_release_event(event)
            return
        if before is None or before["status"] == "closed":
            raise AggregateStateError("terminal aggregate cannot transition")
        allowed_metadata = {"reviewer"} if operation in {
            "aggregate_approved", "aggregate_started", "aggregate_abandoned", "aggregate_closed",
        } else set()
        if set(metadata) != allowed_metadata:
            raise AggregateStateError("aggregate event metadata is not exact")
        if allowed_metadata and metadata["reviewer"] != before["reviewer"]:
            raise AggregateStateError("aggregate event reviewer mismatch")
        allowed_fields = {"status", "next_case_id", "history_count", "history_head_sha256"}
        changed = {key for key in before if before[key] != after[key]}
        if not changed <= allowed_fields or "status" not in changed:
            raise AggregateStateError("aggregate operation mutated prohibited fields")
        if after["history_count"] != before["history_count"] + 1:
            raise AggregateStateError("aggregate operation history count mismatch")
        if after["cases"] != before["cases"] or after["acknowledgement"] != before["acknowledgement"]:
            raise AggregateStateError("aggregate lifecycle operation cannot mutate case or acknowledgement state")
        self._validate_budget_state(after)
        if operation == "aggregate_expired" and occurred_at < parse_time(before["expires_at"]):
            raise AggregateStateError("aggregate cannot expire before its boundary")
        if operation == "aggregate_started" and occurred_at >= parse_time(before["expires_at"]):
            raise AggregateStateError("aggregate cannot start at or after its expiration boundary")
        if operation == "aggregate_ready_to_finalize" and (
            not _all_cases_terminal(after) or after["acknowledgement"]["acknowledgement_required"]
        ):
            raise AggregateStateError("aggregate is not ready to finalize")

    def _validate_initial_state(self, state: Mapping[str, object]) -> None:
        self._validate_state(state)
        if (
            state["status"] != "prepared"
            or state["history_count"] != 1
            or state["cases"] != self._expected_initial_cases()
            or state["ai_case_envelopes"] != {}
            or state["preflight_grants"] != {}
            or state["provider_budget_reservations"] != {}
            or state["budget_accounting"] != derive_budget_accounting({})
            or state["acknowledgement"] != _neutral_acknowledgement()
            or state["extension_history"] != []
            or state["next_case_id"] is not None
        ):
            raise AggregateStateError("aggregate initialization state is not exact")
        validate_zero_counters(state["counters"])

    def _expected_initial_cases(self) -> dict[str, object]:
        return {
            item["case_id"]: {
                "case_id": item["case_id"],
                "deterministic_case_input_sha256": item["deterministic_case_input_sha256"],
                "coordination_status": "untouched",
                "deterministic_initialization_pending": item["case_id"] in EMPTY_CASE_IDS,
                "deterministic_outcome": None,
            }
            for item in immutable_package()["case_bindings"]
        }

    def _validate_state(self, state: Mapping[str, object]) -> None:
        required = {
            "state_version", "aggregate_id", "package_identity_sha256", "immutable_package",
            "operator", "reviewer", "status", "initialized_at", "expires_at",
            "coordination_only", "provider_authority", "ai_case_envelopes", "preflight_grants",
            "provider_budget_reservations", "budget_accounting", "cases", "counters",
            "acknowledgement", "extension_history", "next_case_id", "history_count",
            "history_head_sha256",
        }
        if (
            not isinstance(state, dict)
            or set(state) != required
            or state["state_version"] != STATE_VERSION
            or state["aggregate_id"] != AGGREGATE_ID
            or state["immutable_package"] != immutable_package()
            or state["package_identity_sha256"] != package_identity()
        ):
            raise AggregateStateError("aggregate identity or schema mismatch")
        validate_human_label(state["operator"], "operator")
        validate_human_label(state["reviewer"], "reviewer")
        if state["status"] not in AGGREGATE_STATES or state["coordination_only"] is not True or state["provider_authority"] is not False:
            raise AggregateStateError("aggregate status or authority boundary mismatch")
        if tuple(state["cases"]) != CASE_ORDER:
            raise AggregateStateError("case membership or order drift")
        bindings = {item["case_id"]: item for item in state["immutable_package"]["case_bindings"]}
        for case_id, record in state["cases"].items():
            if (
                set(record) != {"case_id", "deterministic_case_input_sha256", "coordination_status", "deterministic_initialization_pending", "deterministic_outcome"}
                or record["case_id"] != case_id
                or record["deterministic_case_input_sha256"] != bindings[case_id]["deterministic_case_input_sha256"]
                or record["coordination_status"] not in CASE_STATES
                or record["deterministic_initialization_pending"] is not (
                    case_id in EMPTY_CASE_IDS and record["coordination_status"] != "terminal"
                )
            ):
                raise AggregateStateError("case coordination binding mismatch")
            if case_id not in EMPTY_CASE_IDS and record["deterministic_outcome"] is not None:
                raise AggregateStateError("AI case cannot contain a deterministic outcome")
            if case_id in EMPTY_CASE_IDS:
                outcome = record["deterministic_outcome"]
                if record["coordination_status"] == "terminal":
                    self._validate_exact_deterministic_outcome(case_id, record, outcome)
                elif outcome is not None:
                    raise AggregateStateError("nonterminal deterministic case cannot contain an outcome")
        self._validate_budget_state(state)
        try:
            validate_ai_case_envelopes(state["ai_case_envelopes"], allow_unbound=True)
        except AiCaseEnvelopeError as error:
            raise AggregateStateError(str(error)) from error
        self._validate_preflight_grants(state)
        _validate_acknowledgement(state["acknowledgement"])
        if state["extension_history"] != []:
            raise AggregateStateError("extensions are not implemented until Milestone 12")
        if state["next_case_id"] != derive_next_case(state):
            raise AggregateStateError("next-case derivation mismatch")
        initialized, expires = parse_time(state["initialized_at"]), parse_time(state["expires_at"])
        if expires - initialized != timedelta(days=7):
            raise AggregateStateError("seven-day coordination lifetime mismatch")
        if state["status"] == "ready_to_finalize" and (
            not _all_cases_terminal(state) or state["acknowledgement"]["acknowledgement_required"]
        ):
            raise AggregateStateError("ready_to_finalize requires ten terminal unblocked cases")

    def _make_event(
        self,
        before: Mapping[str, object] | None,
        after: Mapping[str, object],
        operation: str,
        metadata: Mapping[str, object],
        occurred_at: datetime | None = None,
    ) -> dict[str, object]:
        previous_digest = (
            digest({"aggregate_id": AGGREGATE_ID, "package_identity_sha256": package_identity()})
            if before is None else before["history_head_sha256"]
        )
        sequence = 1 if before is None else before["history_count"] + 1
        event = {
            "sequence": sequence,
            "operation": operation,
            "occurred_at": format_time(occurred_at or self.clock()),
            "metadata": dict(metadata),
            "previous_sha256": previous_digest,
            "before_state": None if before is None else json.loads(canonical_json(before)),
            "after_state": json.loads(canonical_json(after)),
        }
        event["after_state"]["history_count"] = sequence
        event["after_state"]["history_head_sha256"] = "<event>"
        event["event_sha256"] = _event_digest(event)
        event["after_state"]["history_head_sha256"] = event["event_sha256"]
        return event

    def _append_transition(self, state: Mapping[str, object], new_status: str, operation: str, metadata: Mapping[str, object]) -> dict[str, object]:
        after = json.loads(canonical_json(state))
        after["status"] = new_status
        after["next_case_id"] = derive_next_case(after)
        event = self._make_event(state, after, operation, metadata)
        journal = self._read_journal()
        journal["events"].append(event)
        states = self._validate_journal(journal)
        canonical = states[-1]
        self._commit(journal, canonical)
        return canonical

    def _validate_exact_deterministic_outcome(
        self, case_id: str, record: Mapping[str, object], outcome: object,
    ) -> None:
        reasons = {"eval-v4-07": "known(false)", "eval-v4-08": "not_applicable"}
        expected = {
            "case_id": case_id,
            "deterministic_case_input_sha256": record["deterministic_case_input_sha256"],
            "provider_eligible": False,
            "deterministic_result": "empty",
            "reason_state": reasons[case_id],
            "terminal": True,
            "provider_request_constructed": False,
            "provider_attempt": "none",
            "provider_spend_usd": "0.00",
        }
        if outcome != expected or record["deterministic_initialization_pending"] is not False:
            raise AggregateStateError("deterministic terminal outcome is not exact")

    def _validate_deterministic_completion(self, event: Mapping[str, object]) -> None:
        before, after = event["before_state"], event["after_state"]
        metadata = event["metadata"]
        if not isinstance(metadata, dict) or set(metadata) != {"case_id", "outcome"}:
            raise AggregateStateError("deterministic completion metadata is not exact")
        case_id = metadata["case_id"]
        if case_id not in EMPTY_CASE_IDS:
            raise AggregateStateError("deterministic completion cannot target an AI case")
        old_record = before["cases"][case_id]
        new_record = after["cases"][case_id]
        if (
            old_record["coordination_status"] != "untouched"
            or old_record["deterministic_initialization_pending"] is not True
            or old_record["deterministic_outcome"] is not None
            or new_record["coordination_status"] != "terminal"
            or metadata["outcome"] != new_record["deterministic_outcome"]
        ):
            raise AggregateStateError("deterministic case completion or duplicate is invalid")
        self._validate_exact_deterministic_outcome(case_id, new_record, metadata["outcome"])
        if case_id == "eval-v4-08" and before["cases"]["eval-v4-07"]["coordination_status"] != "terminal":
            raise AggregateStateError("deterministic cases must complete in frozen order")
        expected_cases = json.loads(canonical_json(before["cases"]))
        expected_cases[case_id] = new_record
        if after["cases"] != expected_cases:
            raise AggregateStateError("deterministic completion mutated another case")
        allowed = {"cases", "next_case_id", "history_count", "history_head_sha256"}
        changed = {key for key in before if before[key] != after[key]}
        if not changed <= allowed or "cases" not in changed:
            raise AggregateStateError("deterministic completion mutated prohibited aggregate fields")
        if after["history_count"] != before["history_count"] + 1:
            raise AggregateStateError("deterministic completion history count mismatch")
        if parse_time(event["occurred_at"]) >= parse_time(before["expires_at"]):
            raise AggregateStateError("deterministic completion cannot occur at or after expiration")
        self._validate_budget_state(after)

    def _complete_deterministic_case(
        self, state: Mapping[str, object], case_id: str, outcome: Mapping[str, object],
    ) -> dict[str, object]:
        if state["status"] != "in_progress" or case_id not in EMPTY_CASE_IDS:
            raise AggregateStateError("deterministic completion requires active fixed empty case")
        record = state["cases"][case_id]
        if record["coordination_status"] == "terminal":
            if record["deterministic_outcome"] == outcome:
                return dict(state)
            raise AggregateStateError("conflicting deterministic completion")
        after = json.loads(canonical_json(state))
        after_record = after["cases"][case_id]
        after_record["coordination_status"] = "terminal"
        after_record["deterministic_initialization_pending"] = False
        after_record["deterministic_outcome"] = dict(outcome)
        after["next_case_id"] = derive_next_case(after)
        event = self._make_event(
            state, after, "deterministic_case_completed",
            {"case_id": case_id, "outcome": dict(outcome)},
        )
        journal = self._read_journal()
        journal["events"].append(event)
        canonical = self._validate_journal(journal)[-1]
        self._commit(journal, canonical)
        return canonical

    def _record_deterministic_outcome(
        self, case_id: str, outcome: Mapping[str, object],
    ) -> dict[str, object]:
        """Internal fixed-case entry used only by the deterministic Milestone 2 service."""
        with _lock(self.root):
            state = self._load_unlocked(observe_expiry=True, recover_projection=True)
            return self._complete_deterministic_case(state, case_id, outcome)

    def _validate_ai_envelope_binding(self, event: Mapping[str, object]) -> None:
        before, after = event["before_state"], event["after_state"]
        expected = build_all_ai_case_envelopes()
        metadata = event["metadata"]
        if metadata != {
            "envelope_count": len(AI_CASE_ORDER),
            "envelope_digests": envelope_digest_map(expected),
        }:
            raise AggregateStateError("AI envelope binding metadata is not exact")
        if before["ai_case_envelopes"] != {} or after["ai_case_envelopes"] != expected:
            raise AggregateStateError("AI envelopes must bind exactly once as a complete set")
        if any(
            before["cases"][case_id]["coordination_status"] != "terminal"
            for case_id in EMPTY_CASE_IDS
        ):
            raise AggregateStateError("deterministic cases must be terminal before AI envelope binding")
        allowed = {"ai_case_envelopes", "next_case_id", "history_count", "history_head_sha256"}
        changed = {key for key in before if before[key] != after[key]}
        if not changed <= allowed or "ai_case_envelopes" not in changed:
            raise AggregateStateError("AI envelope binding mutated prohibited aggregate fields")
        if after["cases"] != before["cases"] or after["history_count"] != before["history_count"] + 1:
            raise AggregateStateError("AI envelope binding changed cases or history count")
        if parse_time(event["occurred_at"]) >= parse_time(before["expires_at"]):
            raise AggregateStateError("AI envelopes cannot bind at or after expiration")
        validate_zero_counters(after["counters"])

    def bind_ai_case_envelopes(self) -> dict[str, object]:
        with _lock(self.root):
            state = self._load_unlocked(observe_expiry=True, recover_projection=True)
            if state["status"] != "in_progress":
                raise AggregateStateError("AI envelope binding requires active coordination")
            expected = build_all_ai_case_envelopes()
            if state["ai_case_envelopes"]:
                if state["ai_case_envelopes"] == expected:
                    return dict(state)
                raise AggregateStateError("conflicting AI envelope binding")
            after = json.loads(canonical_json(state))
            after["ai_case_envelopes"] = expected
            after["next_case_id"] = derive_next_case(after)
            event = self._make_event(
                state, after, "ai_case_envelopes_bound",
                {
                    "envelope_count": len(AI_CASE_ORDER),
                    "envelope_digests": envelope_digest_map(expected),
                },
            )
            journal = self._read_journal()
            journal["events"].append(event)
            canonical = self._validate_journal(journal)[-1]
            self._commit(journal, canonical)
            return canonical

    def _validate_preflight_grants(self, state: Mapping[str, object]) -> None:
        from v4_formal_evaluation_live_grants import (
            PreflightGrantError, budget_authorized_lifecycle, released_lifecycle,
            prepared_lifecycle, validate_preflight_grant,
        )

        grants = state["preflight_grants"]
        if not isinstance(grants, dict) or len(grants) > len(AI_CASE_ORDER):
            raise AggregateStateError("at most one exact preflight grant per AI case may be retained")
        for case_id, grant in grants.items():
            if case_id not in AI_CASE_ORDER or case_id not in state["ai_case_envelopes"]:
                raise AggregateStateError("preflight grant target is not an enveloped AI case")
            try:
                validate_preflight_grant(grant, case_id, state["ai_case_envelopes"][case_id])
            except PreflightGrantError as error:
                raise AggregateStateError(str(error)) from error
            reservation = state["provider_budget_reservations"].get(case_id)
            lifecycle = grant["lifecycle"]
            if reservation is None and lifecycle != prepared_lifecycle():
                raise AggregateStateError("grant authorization requires a matching durable reservation")
            if reservation is not None:
                expected_lifecycle = (
                    budget_authorized_lifecycle()
                    if reservation["lifecycle"]["status"] == "reserved"
                    else released_lifecycle()
                )
                if lifecycle != expected_lifecycle:
                    raise AggregateStateError("grant lifecycle does not match its durable reservation")

    def _validate_budget_state(self, state: Mapping[str, object]) -> None:
        reservations = state["provider_budget_reservations"]
        if not isinstance(reservations, dict) or len(reservations) > 8:
            raise AggregateStateError("provider budget reservations are malformed")
        try:
            derived = derive_budget_accounting(reservations)
        except (BudgetError, KeyError, TypeError) as error:
            raise AggregateStateError(str(error)) from error
        aggregate = derived["aggregate"]
        if (
            aggregate["token_preflights_reserved"]
            + aggregate["token_preflights_consumed"]
            > MAX_TOKEN_PREFLIGHTS
        ):
            raise AggregateStateError("provider preflight operation count exceeds frozen maximum")
        for case_id, reservation in reservations.items():
            if case_id not in AI_CASE_ORDER or case_id not in state["preflight_grants"]:
                raise AggregateStateError("budget reservation targets an unavailable AI grant")
            try:
                validate_reservation(
                    reservation,
                    state["preflight_grants"][case_id],
                    state["ai_case_envelopes"][case_id],
                )
            except (BudgetError, KeyError) as error:
                raise AggregateStateError(str(error)) from error
        if state["budget_accounting"] != derived:
            raise AggregateStateError("persisted budget totals do not match independently derived accounting")
        expected_counters = {
            "token_preflights_consumed": aggregate["token_preflights_consumed"],
            "token_preflights_reserved": aggregate["token_preflights_reserved"],
            "generations_consumed": aggregate["generations_consumed"],
            "generations_reserved": aggregate["generations_reserved"],
            "retries": aggregate["retries"],
            "provider_spend_reserved_usd": aggregate["total_provider_exposure_reserved_usd"],
            "provider_spend_consumed_usd": aggregate["total_provider_exposure_consumed_usd"],
        }
        if state["counters"] != expected_counters:
            raise AggregateStateError("provider counters do not match derived budget accounting")

    def _validate_preflight_grant_preparation(self, event: Mapping[str, object]) -> None:
        from v4_formal_evaluation_live_grants import validate_preflight_grant

        before, after = event["before_state"], event["after_state"]
        metadata = event["metadata"]
        if not isinstance(metadata, dict) or set(metadata) != {"case_id", "grant_sha256"}:
            raise AggregateStateError("preflight grant preparation metadata is not exact")
        case_id = metadata["case_id"]
        if (
            case_id not in AI_CASE_ORDER
            or before["next_case_id"] != case_id
            or case_id in before["preflight_grants"]
            or case_id not in before["ai_case_envelopes"]
        ):
            raise AggregateStateError("preflight grant must target the exact next enveloped AI case")
        grant = after["preflight_grants"].get(case_id)
        validate_preflight_grant(grant, case_id, before["ai_case_envelopes"][case_id])
        if metadata["grant_sha256"] != grant["grant_sha256"]:
            raise AggregateStateError("preflight grant event identity mismatch")
        expected = json.loads(canonical_json(before))
        expected["preflight_grants"][case_id] = grant
        expected["history_count"] = after["history_count"]
        expected["history_head_sha256"] = after["history_head_sha256"]
        if after != expected:
            raise AggregateStateError("preflight grant preparation mutated prohibited aggregate fields")
        occurred = parse_time(event["occurred_at"])
        if occurred != parse_time(grant["immutable_binding"]["activated_at"]):
            raise AggregateStateError("preflight grant activation timestamp must match its event")
        if occurred >= parse_time(before["expires_at"]):
            raise AggregateStateError("preflight grant cannot prepare at or after aggregate expiration")
        self._validate_budget_state(after)

    def prepare_preflight_grant(self) -> dict[str, object]:
        from v4_formal_evaluation_live_grants import build_preflight_grant, grant_is_expired

        with _lock(self.root):
            state = self._load_unlocked(observe_expiry=True, recover_projection=True)
            if state["status"] != "in_progress" or state["acknowledgement"]["acknowledgement_required"]:
                raise AggregateStateError("preflight grant preparation requires active unblocked coordination")
            if any(state["cases"][case_id]["coordination_status"] != "terminal" for case_id in EMPTY_CASE_IDS):
                raise AggregateStateError("deterministic cases must be terminal before grant preparation")
            case_id = state["next_case_id"]
            if case_id not in AI_CASE_ORDER or case_id not in state["ai_case_envelopes"]:
                raise AggregateStateError("no exact next enveloped AI case is available")
            if state["cases"][case_id]["coordination_status"] != "untouched":
                raise AggregateStateError("next AI case is not untouched")
            if state["ai_case_envelopes"][case_id]["phase_lifecycle"]["preflight_status"] != "not_authorized":
                raise AggregateStateError("preflight phase is not eligible")
            existing = state["preflight_grants"].get(case_id)
            if existing is not None:
                if not grant_is_expired(existing, self.clock()):
                    return dict(state)
                raise AggregateStateError("expired preflight grant cannot be replaced")
            occurred_at = self.clock()
            grant = build_preflight_grant(case_id, state["ai_case_envelopes"][case_id], occurred_at)
            after = json.loads(canonical_json(state))
            after["preflight_grants"][case_id] = grant
            event = self._make_event(
                state, after, "preflight_grant_prepared",
                {"case_id": case_id, "grant_sha256": grant["grant_sha256"]},
                occurred_at=occurred_at,
            )
            journal = self._read_journal()
            journal["events"].append(event)
            canonical = self._validate_journal(journal)[-1]
            self._commit(journal, canonical)
            return canonical

    def _set_derived_budget(self, state: dict[str, object]) -> None:
        accounting = derive_budget_accounting(state["provider_budget_reservations"])
        state["budget_accounting"] = accounting
        aggregate = accounting["aggregate"]
        state["counters"] = {
            "token_preflights_consumed": aggregate["token_preflights_consumed"],
            "token_preflights_reserved": aggregate["token_preflights_reserved"],
            "generations_consumed": aggregate["generations_consumed"],
            "generations_reserved": aggregate["generations_reserved"],
            "retries": aggregate["retries"],
            "provider_spend_reserved_usd": aggregate["total_provider_exposure_reserved_usd"],
            "provider_spend_consumed_usd": aggregate["total_provider_exposure_consumed_usd"],
        }

    def _validate_budget_reservation_event(self, event: Mapping[str, object]) -> None:
        from v4_formal_evaluation_live_grants import budget_authorized_lifecycle, prepared_lifecycle

        before, after, metadata = event["before_state"], event["after_state"], event["metadata"]
        if not isinstance(metadata, dict) or set(metadata) != {
            "case_id", "grant_sha256", "reservation_sha256",
        }:
            raise AggregateStateError("provider budget reservation metadata is not exact")
        case_id = metadata["case_id"]
        if (
            case_id not in AI_CASE_ORDER
            or before["next_case_id"] != case_id
            or case_id not in before["preflight_grants"]
            or before["preflight_grants"][case_id]["lifecycle"] != prepared_lifecycle()
            or case_id in before["provider_budget_reservations"]
        ):
            raise AggregateStateError("provider budget reservation must target the exact prepared next-case grant")
        reservation = after["provider_budget_reservations"].get(case_id)
        if reservation is None:
            raise AggregateStateError("budget-authorized grant is missing its reservation")
        if (
            metadata["grant_sha256"] != before["preflight_grants"][case_id]["grant_sha256"]
            or metadata["reservation_sha256"] != reservation["reservation_sha256"]
            or event["occurred_at"] != reservation["immutable_binding"]["reserved_at"]
            or parse_time(event["occurred_at"]) >= parse_time(before["expires_at"])
            or parse_time(event["occurred_at"]) >= parse_time(before["preflight_grants"][case_id]["immutable_binding"]["expires_at"])
        ):
            raise AggregateStateError("provider budget reservation identity or lifetime mismatch")
        expected = json.loads(canonical_json(before))
        expected["provider_budget_reservations"][case_id] = reservation
        expected["preflight_grants"][case_id]["lifecycle"] = budget_authorized_lifecycle()
        self._set_derived_budget(expected)
        expected["history_count"] = after["history_count"]
        expected["history_head_sha256"] = after["history_head_sha256"]
        if after != expected:
            raise AggregateStateError("provider budget reservation mutated prohibited aggregate fields")
        self._validate_budget_state(after)

    def authorize_preflight_budget(self) -> dict[str, object]:
        from v4_formal_evaluation_live_grants import budget_authorized_lifecycle, grant_is_expired, prepared_lifecycle

        with _lock(self.root):
            state = self._load_unlocked(observe_expiry=True, recover_projection=True)
            if state["status"] != "in_progress" or state["acknowledgement"]["acknowledgement_required"]:
                raise AggregateStateError("budget authorization requires active unblocked coordination")
            case_id = state["next_case_id"]
            if case_id not in AI_CASE_ORDER or case_id not in state["preflight_grants"]:
                raise AggregateStateError("budget authorization requires the exact prepared next-case grant")
            grant = state["preflight_grants"][case_id]
            reservation = state["provider_budget_reservations"].get(case_id)
            if reservation is not None:
                if reservation["lifecycle"]["status"] == "reserved" and grant["lifecycle"] == budget_authorized_lifecycle():
                    return dict(state)
                raise AggregateStateError("conflicting or released budget reservation cannot be replaced")
            if grant["lifecycle"] != prepared_lifecycle() or grant_is_expired(grant, self.clock()):
                raise AggregateStateError("prepared preflight grant is unavailable or expired")
            accounting = derive_budget_accounting(state["provider_budget_reservations"])["aggregate"]
            case_accounting = state["budget_accounting"]["cases"][case_id]
            amount = Decimal(grant["immutable_binding"]["conservative_operation_ceiling_usd"])
            enforce_prospective_capacity(
                case_reserved=Decimal(case_accounting["total_reserved_provider_exposure_usd"]),
                case_consumed=Decimal(case_accounting["total_consumed_provider_exposure_usd"]),
                aggregate_reserved=Decimal(accounting["total_provider_exposure_reserved_usd"]),
                aggregate_consumed=Decimal(accounting["total_provider_exposure_consumed_usd"]),
                preflights_reserved=accounting["token_preflights_reserved"],
                preflights_consumed=accounting["token_preflights_consumed"],
                requested_amount=amount,
            )
            occurred_at = self.clock()
            reservation = build_preflight_reservation(
                grant, state["ai_case_envelopes"][case_id], format_time(occurred_at),
            )
            after = json.loads(canonical_json(state))
            after["provider_budget_reservations"][case_id] = reservation
            after["preflight_grants"][case_id]["lifecycle"] = budget_authorized_lifecycle()
            self._set_derived_budget(after)
            event = self._make_event(
                state, after, "provider_budget_reserved",
                {
                    "case_id": case_id,
                    "grant_sha256": grant["grant_sha256"],
                    "reservation_sha256": reservation["reservation_sha256"],
                },
                occurred_at=occurred_at,
            )
            journal = self._read_journal()
            journal["events"].append(event)
            canonical = self._validate_journal(journal)[-1]
            self._commit(journal, canonical)
            return canonical

    def _validate_budget_release_event(self, event: Mapping[str, object]) -> None:
        from v4_formal_evaluation_live_grants import budget_authorized_lifecycle, released_lifecycle

        before, after, metadata = event["before_state"], event["after_state"], event["metadata"]
        if not isinstance(metadata, dict) or set(metadata) != {
            "case_id", "reservation_sha256", "proof",
        } or metadata["proof"] != "expired_unused_dispatch_not_started":
            raise AggregateStateError("provider budget release metadata is not exact")
        case_id = metadata["case_id"]
        reservation = before["provider_budget_reservations"].get(case_id)
        if (
            reservation is None
            or reservation["lifecycle"]["status"] != "reserved"
            or reservation["lifecycle"]["provider_dispatch_status"] != "not_started"
            or before["preflight_grants"][case_id]["lifecycle"] != budget_authorized_lifecycle()
            or metadata["reservation_sha256"] != reservation["reservation_sha256"]
            or parse_time(event["occurred_at"]) < parse_time(before["preflight_grants"][case_id]["immutable_binding"]["expires_at"])
        ):
            raise AggregateStateError("provider budget release lacks proof of expired non-dispatch")
        expected = json.loads(canonical_json(before))
        expected_reservation = expected["provider_budget_reservations"][case_id]
        expected_reservation["lifecycle"].update(
            status="released",
            released_amount_usd=expected_reservation["immutable_binding"]["reservation_amount_usd"],
            release_reason="expired_unused_dispatch_not_started",
            released_at=event["occurred_at"],
        )
        expected["preflight_grants"][case_id]["lifecycle"] = released_lifecycle()
        self._set_derived_budget(expected)
        expected["history_count"] = after["history_count"]
        expected["history_head_sha256"] = after["history_head_sha256"]
        if after != expected:
            raise AggregateStateError("provider budget release mutated prohibited aggregate fields")
        self._validate_budget_state(after)

    def release_expired_preflight_budget(self) -> dict[str, object]:
        from v4_formal_evaluation_live_grants import budget_authorized_lifecycle, released_lifecycle

        with _lock(self.root):
            state = self._load_unlocked(observe_expiry=True, recover_projection=True)
            releasable = [
                (case_id, reservation)
                for case_id, reservation in state["provider_budget_reservations"].items()
                if reservation["lifecycle"]["status"] == "reserved"
            ]
            if not releasable:
                if state["provider_budget_reservations"] and all(
                    reservation["lifecycle"]["status"] == "released"
                    and state["preflight_grants"][case_id]["lifecycle"] == released_lifecycle()
                    for case_id, reservation in state["provider_budget_reservations"].items()
                ):
                    return dict(state)
                raise AggregateStateError("no reserved preflight budget is available for release")
            expired = [
                (case_id, reservation)
                for case_id, reservation in releasable
                if self.clock() >= parse_time(
                    state["preflight_grants"][case_id]["immutable_binding"]["expires_at"]
                )
            ]
            if len(expired) != 1:
                raise AggregateStateError("release requires exactly one expired grant with reserved preflight budget")
            case_id, reservation = expired[0]
            grant = state["preflight_grants"][case_id]
            if (
                grant["lifecycle"] != budget_authorized_lifecycle()
                or self.clock() < parse_time(grant["immutable_binding"]["expires_at"])
                or reservation["lifecycle"]["provider_dispatch_status"] != "not_started"
            ):
                raise AggregateStateError("reservation release requires expired grant and proven non-dispatch")
            occurred_at = self.clock()
            after = json.loads(canonical_json(state))
            after_reservation = after["provider_budget_reservations"][case_id]
            after_reservation["lifecycle"].update(
                status="released",
                released_amount_usd=after_reservation["immutable_binding"]["reservation_amount_usd"],
                release_reason="expired_unused_dispatch_not_started",
                released_at=format_time(occurred_at),
            )
            after["preflight_grants"][case_id]["lifecycle"] = released_lifecycle()
            self._set_derived_budget(after)
            event = self._make_event(
                state, after, "provider_budget_released",
                {
                    "case_id": case_id,
                    "reservation_sha256": reservation["reservation_sha256"],
                    "proof": "expired_unused_dispatch_not_started",
                },
                occurred_at=occurred_at,
            )
            journal = self._read_journal()
            journal["events"].append(event)
            canonical = self._validate_journal(journal)[-1]
            self._commit(journal, canonical)
            return canonical

    def _commit(self, journal: Mapping[str, object], projection: Mapping[str, object]) -> None:
        _atomic_json(self.journal_path, journal, lambda: self._fault("before_history_replace"))
        self._fault("after_history_replace")
        _atomic_json(self.snapshot_path, projection, lambda: self._fault("before_projection_replace"))

    # Synthetic/test-only seam. It is neither persisted nor part of the event grammar.
    def _synthetic_case_status(
        self,
        case_id: str,
        status: str,
        *,
        acknowledgement_required: bool = False,
        blocking_outcome_digest: str | None = None,
    ) -> Mapping[str, object]:
        if case_id not in CASE_ORDER or status not in CASE_STATES:
            raise AggregateStateError("invalid synthetic case transition")
        with _lock(self.root):
            state = self._load_unlocked(observe_expiry=True, recover_projection=True)
            if state["status"] != "in_progress":
                raise AggregateStateError("synthetic case transition requires active coordination")
            state = json.loads(canonical_json(state))
            state["cases"][case_id]["coordination_status"] = status
            state["acknowledgement"] = {
                "acknowledgement_required": acknowledgement_required,
                "acknowledged": False,
                "blocking_case_id": case_id if acknowledgement_required else None,
                "blocking_outcome_digest": blocking_outcome_digest if acknowledgement_required else None,
            }
            state["next_case_id"] = derive_next_case(state)
            return state
