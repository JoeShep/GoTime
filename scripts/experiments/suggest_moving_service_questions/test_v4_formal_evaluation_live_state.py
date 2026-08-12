from __future__ import annotations

import ast
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from v4_formal_evaluation_live_cli import PUBLIC_COMMANDS
from v4_formal_evaluation_live_models import (
    AGGREGATE_ID, AI_CASE_ORDER, CASE_ORDER, EMPTY_CASE_IDS,
    AggregateFoundationError, immutable_package, package_identity,
)
from v4_formal_evaluation_live_state import (
    AggregateStateError, AggregateStore, _event_digest, derive_next_case,
)

HERE = Path(__file__).parent
CLI = HERE / "v4_formal_evaluation_live_cli.py"


class Clock:
    def __init__(self) -> None:
        self.now = datetime(2026, 8, 10, 12, tzinfo=timezone.utc)

    def __call__(self):
        return self.now


@pytest.fixture
def active(tmp_path):
    clock = Clock()
    store = AggregateStore(tmp_path, clock)
    store.initialize("Local Operator", "Local Reviewer")
    return store, clock, store.resume("Local Reviewer")


def _write_rehashed_last_event(store, mutate_after, *, operation=None, occurred_at=None):
    journal = json.loads(store.journal_path.read_text())
    event = journal["events"][-1]
    mutate_after(event["after_state"])
    if operation is not None:
        event["operation"] = operation
    if occurred_at is not None:
        event["occurred_at"] = occurred_at
    event["event_sha256"] = _event_digest(event)
    event["after_state"]["history_head_sha256"] = event["event_sha256"]
    store.journal_path.write_text(json.dumps(journal))
    store.snapshot_path.write_text(json.dumps(event["after_state"]))


def _append_rehashed_event(store, before, after, operation, *, occurred_at=None, metadata=None):
    journal = json.loads(store.journal_path.read_text())
    event = store._make_event(before, after, operation, metadata or {}, occurred_at=occurred_at)
    journal["events"].append(event)
    store.journal_path.write_text(json.dumps(journal))
    store.snapshot_path.write_text(json.dumps(event["after_state"]))


def test_foundation_identity_is_reproducible_and_exact():
    first, second = immutable_package(), immutable_package()
    assert first == second
    assert package_identity() == package_identity()
    assert first["aggregate_id"] == AGGREGATE_ID
    assert tuple(first["case_order"]) == CASE_ORDER
    assert tuple(first["ai_case_order"]) == AI_CASE_ORDER
    assert tuple(first["deterministic_empty_case_ids"]) == EMPTY_CASE_IDS
    assert first["provider_authority"] is False
    assert first["budget_policy"] == {"maximum_token_preflights": 8, "maximum_generations": 8, "maximum_retries": 0, "per_case_provider_ceiling_usd": "0.03", "aggregate_provider_ceiling_usd": "0.24", "spending_authorized": False}


def test_initialize_round_trip_and_idempotency(tmp_path):
    clock = Clock()
    store = AggregateStore(tmp_path, clock)
    first = store.initialize("Operator 1", "Reviewer 1")
    assert store.initialize("Operator 1", "Reviewer 1") == first
    assert AggregateStore(tmp_path, clock).load() == first
    assert first["status"] == "prepared" and first["next_case_id"] is None
    assert all(record["coordination_status"] == "untouched" for record in first["cases"].values())
    assert first["cases"]["eval-v4-07"]["deterministic_initialization_pending"] is True
    with pytest.raises(AggregateStateError, match="conflicting"):
        store.initialize("Different", "Reviewer 1")


def test_reviewed_resume_uses_legal_transitions_and_fresh_process(tmp_path):
    clock = Clock()
    AggregateStore(tmp_path, clock).initialize("Operator", "Reviewer")
    state = AggregateStore(tmp_path, clock).resume("Reviewer")
    assert state["status"] == "in_progress"
    assert state["history_count"] == 3
    assert state["next_case_id"] == "eval-v4-01"
    assert AggregateStore(tmp_path, clock).load() == state


def test_seven_day_expiry_preserves_cases_counters_and_blocks_resume(active):
    store, clock, before = active
    clock.now += timedelta(days=7)
    expired = AggregateStore(store.root, clock).load()
    assert expired["status"] == "expired_paused" and expired["next_case_id"] is None
    assert expired["cases"] == before["cases"] and expired["counters"] == before["counters"]
    assert expired["expires_at"] == before["expires_at"] and expired["extension_history"] == []
    with pytest.raises(AggregateStateError, match="Milestone 12"):
        store.resume("Local Reviewer")
    with pytest.raises(AggregateStateError, match="Milestone 12"):
        store.request_extension("Local Reviewer", "continue")


def test_expiration_boundary_is_inclusive_and_just_before_remains_active(tmp_path):
    clock = Clock()
    store = AggregateStore(tmp_path, clock)
    initialized = store.initialize("Operator", "Reviewer")
    store.resume("Reviewer")
    expiration = datetime.fromisoformat(initialized["expires_at"].replace("Z", "+00:00"))
    clock.now = expiration - timedelta(seconds=1)
    assert AggregateStore(tmp_path, clock).load()["status"] == "in_progress"
    clock.now = expiration
    expired = AggregateStore(tmp_path, clock).load()
    assert expired["status"] == "expired_paused"
    assert expired["expires_at"] == initialized["expires_at"]


@pytest.mark.parametrize("offset,starts", [(-1, True), (0, False), (1, False)])
def test_prepared_start_respects_inclusive_expiration_boundary(tmp_path, offset, starts):
    clock = Clock()
    store = AggregateStore(tmp_path, clock)
    initialized = store.initialize("Operator", "Reviewer")
    counters = initialized["counters"]
    expiration = datetime.fromisoformat(initialized["expires_at"].replace("Z", "+00:00"))
    clock.now = expiration + timedelta(seconds=offset)
    if starts:
        state = store.resume("Reviewer")
        assert state["status"] == "in_progress"
        assert state["next_case_id"] == "eval-v4-01"
    else:
        with pytest.raises(AggregateStateError, match="Milestone 12"):
            store.resume("Reviewer")
        state = AggregateStore(tmp_path, clock).load()
        assert state["status"] == "expired_paused"
        assert state["next_case_id"] is None
    assert state["counters"] == counters
    assert state["provider_authority"] is False


def test_next_case_is_derived_and_acknowledgement_blocks(active):
    store, _, state = active
    assert derive_next_case(state) == "eval-v4-01"
    synthetic = store._synthetic_case_status("eval-v4-01", "terminal")
    assert synthetic["next_case_id"] == "eval-v4-02"
    in_progress = store._synthetic_case_status("eval-v4-01", "in_progress")
    assert in_progress["next_case_id"] is None
    blocked = store._synthetic_case_status(
        "eval-v4-01", "awaiting_acknowledgement",
        acknowledgement_required=True, blocking_outcome_digest="a" * 64,
    )
    assert blocked["next_case_id"] is None
    assert blocked["acknowledgement"]["acknowledged"] is False


def test_all_ai_cases_terminal_derives_no_next_case(active):
    _, _, state = active
    document = json.loads(json.dumps(state))
    for case_id in AI_CASE_ORDER:
        document["cases"][case_id]["coordination_status"] = "terminal"
    document["next_case_id"] = derive_next_case(document)
    assert document["next_case_id"] is None
    assert all(document["cases"][case_id]["deterministic_initialization_pending"] for case_id in EMPTY_CASE_IDS)


def test_snapshot_rollback_malformed_counter_and_membership_drift_fail(active):
    store, _, current = active
    original = json.loads(store.snapshot_path.read_text())
    mutations = [
        lambda doc: doc.update(history_count=0),
        lambda doc: doc["counters"].update(generations_consumed=1),
        lambda doc: doc["cases"].pop("eval-v4-10"),
        lambda doc: doc.update(aggregate_id="stale"),
    ]
    for mutate in mutations:
        document = json.loads(json.dumps(original))
        mutate(document)
        store.snapshot_path.write_text(json.dumps(document))
        with pytest.raises(AggregateStateError):
            store.load(observe_expiry=False)
    store.snapshot_path.write_text("not-json")
    with pytest.raises(AggregateStateError, match="malformed"):
        store.load()


def test_history_hash_detection(active):
    store, _, _ = active
    journal = json.loads(store.journal_path.read_text())
    journal["events"][0]["event_sha256"] = "0" * 64
    store.journal_path.write_text(json.dumps(journal))
    with pytest.raises(AggregateStateError, match="history chain"):
        store.load(observe_expiry=False)


def test_correctly_rehashed_operation_cannot_mutate_case(active):
    store, _, _ = active
    _write_rehashed_last_event(
        store,
        lambda state: state["cases"]["eval-v4-01"].update(coordination_status="terminal"),
    )
    with pytest.raises(AggregateStateError, match="prohibited fields"):
        store.load(observe_expiry=False)


def test_correctly_rehashed_wrong_operation_for_states_is_rejected(active):
    store, _, _ = active
    _write_rehashed_last_event(store, lambda state: None, operation="aggregate_expired")
    with pytest.raises(AggregateStateError, match="operation state transition"):
        store.load(observe_expiry=False)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda state: state["immutable_package"]["ai_case_order"].reverse(),
        lambda state: state["cases"]["eval-v4-01"].update(deterministic_case_input_sha256="0" * 64),
        lambda state: state["immutable_package"]["budget_policy"].update(maximum_generations=7),
    ],
    ids=["case-order", "case-input-identity", "frozen-budget"],
)
def test_correctly_rehashed_foundation_drift_is_rejected(tmp_path, mutate):
    store = AggregateStore(tmp_path, Clock())
    store.initialize("Operator", "Reviewer")
    _write_rehashed_last_event(store, mutate)
    with pytest.raises(AggregateStateError):
        store.load(observe_expiry=False)


@pytest.mark.parametrize(
    "field,value",
    [
        ("maximum_token_preflights", 7),
        ("maximum_generations", 7),
        ("maximum_retries", 1),
        ("per_case_provider_ceiling_usd", "0.04"),
        ("aggregate_provider_ceiling_usd", "0.25"),
        ("spending_authorized", True),
    ],
)
def test_each_frozen_budget_field_rehashed_mutation_is_rejected(tmp_path, field, value):
    store = AggregateStore(tmp_path, Clock())
    store.initialize("Operator", "Reviewer")
    _write_rehashed_last_event(
        store,
        lambda state: state["immutable_package"]["budget_policy"].update({field: value}),
    )
    with pytest.raises(AggregateStateError):
        store.load(observe_expiry=False)


def test_rehashed_extra_case_is_rejected(tmp_path):
    store = AggregateStore(tmp_path, Clock())
    store.initialize("Operator", "Reviewer")
    _write_rehashed_last_event(
        store,
        lambda state: state["cases"].update({
            "eval-v4-99": {
                "case_id": "eval-v4-99",
                "deterministic_case_input_sha256": "9" * 64,
                "coordination_status": "untouched",
                "deterministic_initialization_pending": False,
            }
        }),
    )
    with pytest.raises(AggregateStateError):
        store.load(observe_expiry=False)


def test_rehashed_deterministic_case_substitution_is_rejected(tmp_path):
    store = AggregateStore(tmp_path, Clock())
    store.initialize("Operator", "Reviewer")
    _write_rehashed_last_event(
        store,
        lambda state: state["cases"]["eval-v4-07"].update(
            case_id="foreign-deterministic-case",
            deterministic_case_input_sha256="7" * 64,
        ),
    )
    with pytest.raises(AggregateStateError):
        store.load(observe_expiry=False)


def test_rehashed_generation_case_request_identity_mutation_is_rejected(tmp_path):
    store = AggregateStore(tmp_path, Clock())
    store.initialize("Operator", "Reviewer")
    _write_rehashed_last_event(
        store,
        lambda state: state["immutable_package"]["case_bindings"][0].update(
            provider_fingerprint="1" * 64,
        ),
    )
    with pytest.raises(AggregateStateError):
        store.load(observe_expiry=False)


@pytest.mark.parametrize(
    "acknowledgement",
    [
        {"acknowledgement_required": False, "acknowledged": False, "blocking_case_id": "eval-v4-01", "blocking_outcome_digest": None},
        {"acknowledgement_required": True, "acknowledged": False, "blocking_case_id": None, "blocking_outcome_digest": "a" * 64},
        {"acknowledgement_required": False, "acknowledged": True, "blocking_case_id": None, "blocking_outcome_digest": None},
        {"acknowledgement_required": True, "acknowledged": False, "blocking_case_id": "eval-v4-99", "blocking_outcome_digest": "a" * 64},
    ],
)
def test_inconsistent_acknowledgement_fields_are_rejected(active, acknowledgement):
    store, _, _ = active
    _write_rehashed_last_event(store, lambda state: state.update(acknowledgement=acknowledgement))
    with pytest.raises(AggregateStateError):
        store.load(observe_expiry=False)


def test_ready_to_finalize_requires_all_ten_terminal(active):
    store, _, state = active
    state = json.loads(json.dumps(state))
    state.update(status="ready_to_finalize", next_case_id=None)
    with pytest.raises(AggregateStateError, match="ready_to_finalize"):
        store._validate_state(state)


def test_rehashed_history_cannot_finalize_before_all_cases_terminal(active):
    store, _, state = active
    after = json.loads(json.dumps(state))
    after.update(status="ready_to_finalize", next_case_id=None)
    _append_rehashed_event(store, state, after, "aggregate_ready_to_finalize")
    with pytest.raises(AggregateStateError, match="not ready to finalize"):
        store.load(observe_expiry=False)


def test_rehashed_unrelated_operation_cannot_extend_expiration(active):
    store, _, state = active
    extended = datetime.fromisoformat(state["expires_at"].replace("Z", "+00:00")) + timedelta(days=7)
    _write_rehashed_last_event(
        store,
        lambda document: document.update(expires_at=extended.isoformat().replace("+00:00", "Z")),
    )
    with pytest.raises(AggregateStateError, match="prohibited fields"):
        store.load(observe_expiry=False)


def test_rehashed_aggregate_started_at_expiration_is_rejected(tmp_path):
    clock = Clock()
    store = AggregateStore(tmp_path, clock)
    prepared = store.initialize("Operator", "Reviewer")
    approved = store._append_transition(
        prepared, "approved", "aggregate_approved", {"reviewer": "Reviewer"},
    )
    expiration = datetime.fromisoformat(approved["expires_at"].replace("Z", "+00:00"))
    after = json.loads(json.dumps(approved))
    after.update(status="in_progress", next_case_id="eval-v4-01")
    _append_rehashed_event(
        store, approved, after, "aggregate_started", occurred_at=expiration,
        metadata={"reviewer": "Reviewer"},
    )
    with pytest.raises(AggregateStateError, match="cannot start at or after"):
        store.load(observe_expiry=False)


def test_early_expiration_event_is_rejected(active):
    store, clock, state = active
    clock.now = datetime.fromisoformat(state["expires_at"].replace("Z", "+00:00"))
    store.load()
    _write_rehashed_last_event(
        store,
        lambda document: None,
        occurred_at=state["initialized_at"],
    )
    with pytest.raises(AggregateStateError, match="before its boundary"):
        store.load(observe_expiry=False)


def test_nonmonotonic_event_timestamp_is_rejected(active):
    store, _, state = active
    initialized = datetime.fromisoformat(state["initialized_at"].replace("Z", "+00:00"))
    _write_rehashed_last_event(
        store, lambda document: None,
        occurred_at=(initialized - timedelta(seconds=1)).isoformat().replace("+00:00", "Z"),
    )
    with pytest.raises(AggregateStateError, match="not monotonic"):
        store.load(observe_expiry=False)


@pytest.mark.parametrize("field,value", [("history_count", 99), ("history_head_sha256", "f" * 64)])
def test_projection_count_and_head_mismatch_are_not_arbitrary_recovery(active, field, value):
    store, _, _ = active
    projection = json.loads(store.snapshot_path.read_text())
    projection[field] = value
    store.snapshot_path.write_text(json.dumps(projection))
    with pytest.raises(AggregateStateError, match="conflicts"):
        store.load(observe_expiry=False)


def test_history_committed_projection_stale_recovers_without_duplicate_event(tmp_path):
    clock = Clock()
    store = AggregateStore(tmp_path, clock)
    store.initialize("Operator", "Reviewer")

    def fail(boundary):
        if boundary == "after_history_replace":
            raise RuntimeError("synthetic crash")

    with pytest.raises(RuntimeError, match="synthetic crash"):
        AggregateStore(tmp_path, clock, fail).resume("Reviewer")
    history_before = json.loads(store.journal_path.read_text())
    assert len(history_before["events"]) == 2
    recovered = AggregateStore(tmp_path, clock).load(observe_expiry=False)
    assert recovered["status"] == "approved"
    assert recovered["history_count"] == 2
    assert recovered["history_head_sha256"] == history_before["events"][-1]["event_sha256"]
    assert json.loads(store.journal_path.read_text()) == history_before
    assert recovered["counters"]["generations_consumed"] == 0
    assert AggregateStore(tmp_path, clock).load(observe_expiry=False) == recovered


def test_initialization_history_without_projection_recovers_idempotently(tmp_path):
    clock = Clock()

    def fail(boundary):
        if boundary == "after_history_replace":
            raise RuntimeError("synthetic crash")

    with pytest.raises(RuntimeError, match="synthetic crash"):
        AggregateStore(tmp_path, clock, fail).initialize("Operator", "Reviewer")
    assert not (tmp_path / "aggregate.json").exists()
    history_before = (tmp_path / "aggregate-history.json").read_bytes()
    recovered = AggregateStore(tmp_path, clock).initialize("Operator", "Reviewer")
    assert recovered["status"] == "prepared" and recovered["history_count"] == 1
    assert (tmp_path / "aggregate-history.json").read_bytes() == history_before


def test_crash_before_history_replace_leaves_old_state_valid(tmp_path):
    clock = Clock()
    store = AggregateStore(tmp_path, clock)
    initial = store.initialize("Operator", "Reviewer")
    history_before = store.journal_path.read_bytes()
    projection_before = store.snapshot_path.read_bytes()

    def fail(boundary):
        if boundary == "before_history_replace":
            raise RuntimeError("synthetic crash")

    with pytest.raises(RuntimeError, match="synthetic crash"):
        AggregateStore(tmp_path, clock, fail).resume("Reviewer")
    assert store.journal_path.read_bytes() == history_before
    assert store.snapshot_path.read_bytes() == projection_before
    assert AggregateStore(tmp_path, clock).load(observe_expiry=False) == initial


def test_human_labels_are_bounded(tmp_path):
    with pytest.raises(AggregateFoundationError):
        AggregateStore(tmp_path).initialize("", "Reviewer")
    with pytest.raises(AggregateFoundationError):
        AggregateStore(tmp_path).initialize("Operator\nInjected", "Reviewer")


def test_close_requires_explicit_abandonment(active):
    store, _, _ = active
    with pytest.raises(AggregateStateError, match="close requires"):
        store.close("Local Reviewer")
    closed = store.close("Local Reviewer", abandon=True)
    assert closed["status"] == "closed" and closed["provider_authority"] is False
    with pytest.raises(AggregateStateError):
        store.resume("Local Reviewer")


def test_public_command_inventory_and_exact_offline_rehearsal(tmp_path):
    assert PUBLIC_COMMANDS == (
        "verify-foundation", "initialize", "inspect", "verify",
        "resolve-deterministic-cases", "bind-ai-case-envelopes", "prepare-preflight-grant",
        "authorize-preflight-budget", "release-preflight-budget", "close",
    )
    base = [sys.executable, str(CLI), "--state-root", str(tmp_path)]
    commands = [
        base + ["verify-foundation"],
        base + ["initialize", "--operator", "CLI Operator", "--reviewer", "CLI Reviewer"],
        base + ["inspect", "--resume", "--reviewer", "CLI Reviewer"],
        base + ["resolve-deterministic-cases"],
        base + ["bind-ai-case-envelopes"],
        base + ["prepare-preflight-grant"],
        base + ["authorize-preflight-budget"],
        base + ["inspect"],
        base + ["verify"],
        base + ["close", "--reviewer", "CLI Reviewer", "--abandon"],
    ]
    outputs = []
    for command in commands:
        result = subprocess.run(
            command, check=True, text=True, capture_output=True,
            env={"PYTHONPATH": str(HERE.parents[2] / "backend")},
        )
        outputs.append(json.loads(result.stdout))
        assert outputs[-1]["provider_authority"] is False
    resolved, bound, authorized, inspected = outputs[3], outputs[4], outputs[6], outputs[7]
    assert [item["outcome"]["reason_state"] for item in resolved["results"]] == [
        "known(false)", "not_applicable",
    ]
    assert inspected["next_case_id"] == "eval-v4-01"
    assert len(bound["ai_case_envelopes"]) == len(AI_CASE_ORDER)
    assert all(inspected["cases"][case_id]["coordination_status"] == "terminal" for case_id in EMPTY_CASE_IDS)
    assert all(inspected["cases"][case_id]["coordination_status"] == "untouched" for case_id in AI_CASE_ORDER)
    assert authorized["counters"]["token_preflights_reserved"] == 1
    assert authorized["counters"]["provider_spend_reserved_usd"] == "0.00"
    assert inspected["budget_accounting"]["aggregate"]["remaining_provider_capacity_usd"] == "0.24"
    assert inspected["immutable_package"]["budget_policy"]["spending_authorized"] is False


def test_live_modules_have_no_provider_network_credential_or_request_capability():
    files = [
        HERE / "v4_formal_evaluation_live_models.py",
        HERE / "v4_formal_evaluation_live_state.py",
        HERE / "v4_formal_evaluation_live_deterministic.py",
        HERE / "v4_formal_evaluation_live_cases.py",
        HERE / "v4_formal_evaluation_live_budget.py",
        CLI,
    ]
    prohibited_import_roots = {"openai", "socket", "httpx", "requests", "urllib"}
    prohibited_text = ("OPENAI_API_KEY", "MovingServiceProviderRequest", "token_preflight_authorized", "ai_generation_authorized")
    for path in files:
        source = path.read_text()
        tree = ast.parse(source)
        imports = {node.names[0].name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import)} | {str(node.module).split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
        assert not imports & prohibited_import_roots
        assert not any(term in source for term in prohibited_text)
    assert "provider_dispatch_started" not in CLI.read_text()
