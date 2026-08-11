from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from v4_formal_evaluation_live_deterministic import (
    ProviderBoundaryEntered, bind_frozen_case, deterministic_outcome,
    resolve_deterministic_cases,
)
from v4_formal_evaluation_live_models import EMPTY_CASE_IDS
from v4_formal_evaluation_live_state import AggregateStateError, AggregateStore, _event_digest


class Clock:
    def __init__(self) -> None:
        self.now = datetime(2026, 8, 10, 12, tzinfo=timezone.utc)

    def __call__(self):
        return self.now


@pytest.fixture
def active(tmp_path):
    clock = Clock()
    store = AggregateStore(tmp_path, clock)
    store.initialize("Operator", "Reviewer")
    store.resume("Reviewer")
    return store, clock


def _rehash_event(store, event):
    event["event_sha256"] = _event_digest(event)
    event["after_state"]["history_head_sha256"] = event["event_sha256"]
    journal = json.loads(store.journal_path.read_text())
    journal["events"].append(event)
    store.journal_path.write_text(json.dumps(journal))
    store.snapshot_path.write_text(json.dumps(event["after_state"]))


def _valid_completion_event(store, case_id):
    before = store.load()
    outcome = deterministic_outcome(case_id)
    after = json.loads(json.dumps(before))
    record = after["cases"][case_id]
    record.update(
        coordination_status="terminal",
        deterministic_initialization_pending=False,
        deterministic_outcome=outcome,
    )
    return store._make_event(
        before, after, "deterministic_case_completed",
        {"case_id": case_id, "outcome": outcome},
    )


@pytest.mark.parametrize(
    ("case_id", "reason_state"),
    (("eval-v4-07", "known(false)"), ("eval-v4-08", "not_applicable")),
)
def test_exact_empty_outcomes_and_provider_constructor_nonentry(case_id, reason_state):
    calls = 0

    def forbidden(*args, **kwargs):
        nonlocal calls
        calls += 1
        raise AssertionError("provider constructor entered")

    case, behavior, identity = bind_frozen_case(case_id, forbidden)
    outcome = deterministic_outcome(case_id)
    assert calls == 0
    assert case["case_id"] == case_id
    assert behavior["deterministic_gate_action"] == "return_empty_without_generation"
    assert identity["provider_request_expected"] is False
    assert outcome["reason_state"] == reason_state
    assert outcome["deterministic_result"] == "empty"
    assert outcome["terminal"] is True
    assert outcome["provider_request_constructed"] is False
    assert outcome["provider_attempt"] == "none"
    assert outcome["provider_spend_usd"] == "0.00"


def test_ai_positive_control_reaches_provider_preparation_boundary_only():
    calls = 0

    def boundary(*args, **kwargs):
        nonlocal calls
        calls += 1
        raise ProviderBoundaryEntered("positive control")

    with pytest.raises(ProviderBoundaryEntered, match="positive control"):
        bind_frozen_case("eval-v4-01", boundary)
    assert calls == 1


def test_resolve_both_is_ordered_terminal_idempotent_and_zero_provider(active):
    store, _ = active
    first = resolve_deterministic_cases(store)
    count = store.load()["history_count"]
    second = resolve_deterministic_cases(store)
    state = store.load()
    assert [item["case_id"] for item in first["results"]] == list(EMPTY_CASE_IDS)
    assert all(state["cases"][case_id]["coordination_status"] == "terminal" for case_id in EMPTY_CASE_IDS)
    assert all(item["already_completed"] for item in second["results"])
    assert state["history_count"] == count
    assert state["next_case_id"] == "eval-v4-01"
    assert set(state["cases"]) - set(EMPTY_CASE_IDS) == {
        "eval-v4-01", "eval-v4-02", "eval-v4-03", "eval-v4-04",
        "eval-v4-05", "eval-v4-06", "eval-v4-09", "eval-v4-10",
    }
    assert all(state["cases"][case_id]["coordination_status"] == "untouched" for case_id in set(state["cases"]) - set(EMPTY_CASE_IDS))
    assert set(state["counters"].values()) == {0, "0.00"}
    assert state["immutable_package"]["budget_policy"]["spending_authorized"] is False
    assert state["provider_authority"] is False


def test_partial_fresh_process_resume_completes_only_08(active):
    store, clock = active
    store._record_deterministic_outcome("eval-v4-07", deterministic_outcome("eval-v4-07"))
    partial = AggregateStore(store.root, clock).load()
    assert partial["cases"]["eval-v4-07"]["coordination_status"] == "terminal"
    assert partial["cases"]["eval-v4-08"]["coordination_status"] == "untouched"
    count = partial["history_count"]
    result = resolve_deterministic_cases(AggregateStore(store.root, clock))
    assert result["results"][0]["already_completed"] is True
    assert result["results"][1]["already_completed"] is False
    assert AggregateStore(store.root, clock).load()["history_count"] == count + 1


def test_expiration_between_cases_preserves_07_and_blocks_08(active):
    store, clock = active
    completed = store._record_deterministic_outcome("eval-v4-07", deterministic_outcome("eval-v4-07"))
    clock.now = datetime.fromisoformat(completed["expires_at"].replace("Z", "+00:00"))
    with pytest.raises(AggregateStateError, match="active fixed empty case"):
        resolve_deterministic_cases(store)
    expired = store.load()
    assert expired["status"] == "expired_paused"
    assert expired["cases"]["eval-v4-07"]["coordination_status"] == "terminal"
    assert expired["cases"]["eval-v4-08"]["coordination_status"] == "untouched"
    assert expired["next_case_id"] is None


def test_crash_after_history_commit_recovers_deterministic_projection(active):
    store, clock = active

    def fail(boundary):
        if boundary == "after_history_replace":
            raise RuntimeError("synthetic crash")

    crashing = AggregateStore(store.root, clock, fail)
    with pytest.raises(RuntimeError, match="synthetic crash"):
        crashing._record_deterministic_outcome("eval-v4-07", deterministic_outcome("eval-v4-07"))
    history = store.journal_path.read_bytes()
    recovered = AggregateStore(store.root, clock).load()
    assert store.journal_path.read_bytes() == history
    assert recovered["cases"]["eval-v4-07"]["coordination_status"] == "terminal"
    assert recovered["cases"]["eval-v4-08"]["coordination_status"] == "untouched"
    assert recovered["history_count"] == 4
    resolved = resolve_deterministic_cases(AggregateStore(store.root, clock))
    assert resolved["results"][0]["already_completed"] is True
    assert resolved["results"][1]["already_completed"] is False
    assert AggregateStore(store.root, clock).load()["history_count"] == 5


@pytest.mark.parametrize("mutation", ["swapped", "counter", "budget", "other_case", "expiration"])
def test_fully_rehashed_semantic_mutations_are_rejected(active, mutation):
    store, _ = active
    event = _valid_completion_event(store, "eval-v4-07")
    if mutation == "swapped":
        event["after_state"]["cases"]["eval-v4-07"]["deterministic_outcome"]["reason_state"] = "not_applicable"
        event["metadata"]["outcome"]["reason_state"] = "not_applicable"
    elif mutation == "counter":
        event["after_state"]["counters"]["generations_consumed"] = 1
    elif mutation == "budget":
        event["after_state"]["immutable_package"]["budget_policy"]["maximum_generations"] = 9
    elif mutation == "other_case":
        event["after_state"]["cases"]["eval-v4-08"]["coordination_status"] = "terminal"
        event["after_state"]["cases"]["eval-v4-08"]["deterministic_initialization_pending"] = False
        event["after_state"]["cases"]["eval-v4-08"]["deterministic_outcome"] = deterministic_outcome("eval-v4-08")
    else:
        event["after_state"]["expires_at"] = "2026-08-18T12:00:00Z"
    _rehash_event(store, event)
    with pytest.raises(AggregateStateError):
        store.load(observe_expiry=False)


def test_fully_rehashed_ai_case_completion_is_rejected(active):
    store, _ = active
    event = _valid_completion_event(store, "eval-v4-07")
    outcome = event["metadata"]["outcome"]
    outcome["case_id"] = "eval-v4-01"
    event["metadata"]["case_id"] = "eval-v4-01"
    event["after_state"]["cases"]["eval-v4-01"].update(
        coordination_status="terminal", deterministic_outcome=outcome,
    )
    event["after_state"]["cases"]["eval-v4-07"] = event["before_state"]["cases"]["eval-v4-07"]
    _rehash_event(store, event)
    with pytest.raises(AggregateStateError, match="AI case"):
        store.load(observe_expiry=False)


def test_fully_rehashed_case_input_identity_attack_is_rejected(active):
    store, _ = active
    event = _valid_completion_event(store, "eval-v4-07")
    event["after_state"]["cases"]["eval-v4-07"]["deterministic_case_input_sha256"] = "0" * 64
    event["after_state"]["cases"]["eval-v4-07"]["deterministic_outcome"]["deterministic_case_input_sha256"] = "0" * 64
    event["metadata"]["outcome"]["deterministic_case_input_sha256"] = "0" * 64
    _rehash_event(store, event)
    with pytest.raises(AggregateStateError):
        store.load(observe_expiry=False)


def test_duplicate_event_and_terminal_reopen_are_rejected(active):
    store, _ = active
    store._record_deterministic_outcome("eval-v4-07", deterministic_outcome("eval-v4-07"))
    before = store.load()
    duplicate = store._make_event(
        before, before, "deterministic_case_completed",
        {"case_id": "eval-v4-07", "outcome": deterministic_outcome("eval-v4-07")},
    )
    _rehash_event(store, duplicate)
    with pytest.raises(AggregateStateError):
        store.load(observe_expiry=False)


def test_fully_rehashed_terminal_case_cannot_reopen(active):
    store, _ = active
    store._record_deterministic_outcome("eval-v4-07", deterministic_outcome("eval-v4-07"))
    before = store.load()
    after = json.loads(json.dumps(before))
    after["cases"]["eval-v4-07"].update(
        coordination_status="untouched",
        deterministic_initialization_pending=True,
        deterministic_outcome=None,
    )
    event = store._make_event(
        before, after, "deterministic_case_completed",
        {"case_id": "eval-v4-07", "outcome": deterministic_outcome("eval-v4-07")},
    )
    _rehash_event(store, event)
    with pytest.raises(AggregateStateError):
        store.load(observe_expiry=False)


def test_08_cannot_complete_before_07_and_conflict_cannot_replace_terminal(active):
    store, _ = active
    with pytest.raises(AggregateStateError, match="frozen order"):
        store._record_deterministic_outcome("eval-v4-08", deterministic_outcome("eval-v4-08"))
    correct = deterministic_outcome("eval-v4-07")
    store._record_deterministic_outcome("eval-v4-07", correct)
    conflicting = dict(correct, reason_state="not_applicable")
    with pytest.raises(AggregateStateError, match="conflicting"):
        store._record_deterministic_outcome("eval-v4-07", conflicting)
