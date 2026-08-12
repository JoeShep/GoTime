from __future__ import annotations

import ast
import json
from datetime import timedelta
from pathlib import Path

import pytest

from test_v4_formal_evaluation_live_budget import (
    SequentialBudgetStore, _make_budget_ready, _recompute_projection_accounting,
    _rewrite_last_budget_event,
)
from v4_formal_evaluation_live_grants import dispatch_started_lifecycle
from v4_formal_evaluation_live_grants import (
    budget_authorized_lifecycle, prepared_lifecycle, released_lifecycle,
)
from v4_formal_evaluation_live_state import AggregateStateError, AggregateStore


def _dispatch_ready(root, store_class=AggregateStore):
    store, clock = _make_budget_ready(root, store_class)
    store.authorize_preflight_budget()
    return store, clock


def _rewrite_consumed_as(state, status, occurred_at):
    after = json.loads(json.dumps(state))
    lifecycle = after["provider_budget_reservations"]["eval-v4-01"]["lifecycle"]
    if status == "reserved":
        lifecycle.update(
            status="reserved", provider_dispatch_status="not_started",
            attempt_consumed=False, consumed_amount_usd="0.00",
            consumed_operation_count=0, dispatch_started_at=None,
            released_amount_usd="0.00", release_reason=None, released_at=None,
        )
        after["preflight_grants"]["eval-v4-01"]["lifecycle"] = budget_authorized_lifecycle()
    else:
        lifecycle.update(
            status="released", provider_dispatch_status="not_started",
            attempt_consumed=False, consumed_amount_usd="0.00",
            consumed_operation_count=0, dispatch_started_at=None,
            released_amount_usd="0.03",
            release_reason="expired_unused_dispatch_not_started",
            released_at=occurred_at,
        )
        after["preflight_grants"]["eval-v4-01"]["lifecycle"] = released_lifecycle()
    _recompute_projection_accounting(after)
    return after


def _append_rehashed_event(store, event):
    journal = store._read_journal()
    journal["events"].append(event)
    store.journal_path.write_text(json.dumps(journal))
    store.snapshot_path.write_text(json.dumps(event["after_state"]))


def test_provider_dispatch_started_converts_full_reservation_once(tmp_path):
    store, _ = _dispatch_ready(tmp_path)
    before = store.load()
    count = before["history_count"]
    after = store.record_provider_dispatch_started()
    assert store.record_provider_dispatch_started() == after
    assert after["history_count"] == count + 1
    reservation = after["provider_budget_reservations"]["eval-v4-01"]
    assert reservation["lifecycle"] == {
        "status": "consumed", "provider_dispatch_status": "started",
        "attempt_consumed": True, "consumed_amount_usd": "0.03",
        "consumed_operation_count": 1, "dispatch_started_at": "2026-08-10T12:00:00Z",
        "released_amount_usd": "0.00", "release_reason": None, "released_at": None,
    }
    assert after["preflight_grants"]["eval-v4-01"]["lifecycle"] == dispatch_started_lifecycle()
    assert after["counters"]["token_preflights_reserved"] == 0
    assert after["counters"]["token_preflights_consumed"] == 1
    assert after["counters"]["provider_spend_reserved_usd"] == "0.00"
    assert after["counters"]["provider_spend_consumed_usd"] == "0.03"
    assert before["budget_accounting"]["aggregate"]["remaining_provider_capacity_usd"] == after["budget_accounting"]["aggregate"]["remaining_provider_capacity_usd"] == "0.21"
    assert after["budget_accounting"]["cases"]["eval-v4-01"]["remaining_provider_capacity_usd"] == "0.00"
    assert after["provider_authority"] is False
    assert all(after["preflight_grants"]["eval-v4-01"]["lifecycle"][key] is False for key in (
        "generation_authorized", "dispatch_authorized", "retry_authorized",
        "provider_execution_authorized", "spending_authorized",
    ))
    with pytest.raises(AggregateStateError):
        store.release_expired_preflight_budget()


def test_pre_dispatch_failure_and_expiry_do_not_consume(tmp_path):
    store, clock = _dispatch_ready(tmp_path)
    clock.now += timedelta(minutes=15)
    with pytest.raises(AggregateStateError, match="preconditions"):
        store.record_provider_dispatch_started()
    state = store.load(observe_expiry=False)
    assert state["counters"]["token_preflights_reserved"] == 1
    assert state["counters"]["token_preflights_consumed"] == 0
    assert all(event["operation"] != "provider_dispatch_started" for event in store._read_journal()["events"])


def test_crash_before_history_commit_preserves_reserved_state(tmp_path):
    store, clock = _dispatch_ready(tmp_path)
    history = store.journal_path.read_bytes()
    def fail(boundary):
        if boundary == "before_history_replace":
            raise RuntimeError("synthetic crash")
    with pytest.raises(RuntimeError):
        AggregateStore(store.root, clock, fail).record_provider_dispatch_started()
    recovered = AggregateStore(store.root, clock).load()
    assert store.journal_path.read_bytes() == history
    assert recovered["counters"]["token_preflights_reserved"] == 1
    assert recovered["counters"]["token_preflights_consumed"] == 0


def test_crash_after_history_commit_recovers_consumed_once(tmp_path):
    store, clock = _dispatch_ready(tmp_path)
    def fail(boundary):
        if boundary == "after_history_replace":
            raise RuntimeError("synthetic crash")
    with pytest.raises(RuntimeError):
        AggregateStore(store.root, clock, fail).record_provider_dispatch_started()
    history = store.journal_path.read_bytes()
    recovered = AggregateStore(store.root, clock).load()
    assert store.journal_path.read_bytes() == history
    assert recovered["counters"]["token_preflights_reserved"] == 0
    assert recovered["counters"]["token_preflights_consumed"] == 1
    assert AggregateStore(store.root, clock).record_provider_dispatch_started()["history_count"] == recovered["history_count"]


@pytest.mark.parametrize("mutation", (
    "case", "grant", "reservation", "envelope", "phase", "amount", "count",
    "request", "attempt", "consumed_not_increased", "retry", "generation",
))
def test_fully_rehashed_dispatch_semantic_attacks_fail(tmp_path, mutation):
    store, _ = _dispatch_ready(tmp_path)
    store.record_provider_dispatch_started()
    def mutate(event, after):
        metadata = event["metadata"]
        lifecycle = after["provider_budget_reservations"]["eval-v4-01"]["lifecycle"]
        if mutation == "case": metadata["case_id"] = "eval-v4-02"
        elif mutation == "grant": metadata["grant_sha256"] = "0" * 64
        elif mutation == "reservation": metadata["reservation_sha256"] = "0" * 64
        elif mutation == "envelope": metadata["case_envelope_sha256"] = "0" * 64
        elif mutation == "phase": metadata["phase"] = "generation"
        elif mutation == "request": metadata["deterministic_request_sha256"] = "0" * 64
        elif mutation == "attempt": metadata["canonical_attempt_sha256"] = "0" * 64
        elif mutation == "amount": lifecycle["consumed_amount_usd"] = "0.02"
        elif mutation == "count": lifecycle["consumed_operation_count"] = 2
        elif mutation == "consumed_not_increased": lifecycle["consumed_amount_usd"] = "0.00"
        elif mutation == "retry": after["preflight_grants"]["eval-v4-01"]["lifecycle"]["retry_authorized"] = True
        elif mutation == "generation": after["preflight_grants"]["eval-v4-01"]["lifecycle"]["generation_authorized"] = True
        try:
            _recompute_projection_accounting(after)
        except Exception:
            pass
    _rewrite_last_budget_event(store, mutate)
    with pytest.raises((AggregateStateError, KeyError, TypeError)):
        store.load(observe_expiry=False)


def test_fully_rehashed_dispatch_provider_fingerprint_drift_fails_exact_binding(tmp_path):
    store, _ = _dispatch_ready(tmp_path)
    store.record_provider_dispatch_started()
    _rewrite_last_budget_event(
        store,
        lambda event, _after: event["metadata"].update(provider_fingerprint="wrong-fingerprint"),
    )
    with pytest.raises(
        AggregateStateError,
        match="provider dispatch-started identity binding mismatch",
    ):
        store.load(observe_expiry=False)


def test_fully_rehashed_dispatch_cannot_target_deterministic_case(tmp_path):
    store, _ = _dispatch_ready(tmp_path)
    store.record_provider_dispatch_started()
    _rewrite_last_budget_event(
        store,
        lambda event, _after: event["metadata"].update(case_id="eval-v4-07"),
    )
    with pytest.raises(
        AggregateStateError,
        match="deterministic case cannot start provider dispatch",
    ):
        store.load(observe_expiry=False)


def test_fully_rehashed_dispatch_cannot_delete_consumed_reservation(tmp_path):
    store, _ = _dispatch_ready(tmp_path)
    store.record_provider_dispatch_started()

    def delete_consumed_record(_event, after):
        after["provider_budget_reservations"].pop("eval-v4-01")
        after["preflight_grants"]["eval-v4-01"]["lifecycle"] = prepared_lifecycle()
        _recompute_projection_accounting(after)

    _rewrite_last_budget_event(store, delete_consumed_record)
    with pytest.raises(
        AggregateStateError,
        match="consumed dispatch history cannot delete its reservation",
    ):
        store.load(observe_expiry=False)


def test_fully_rehashed_consumed_reservation_cannot_be_restored_to_reserved(tmp_path):
    store, _ = _dispatch_ready(tmp_path)
    store.record_provider_dispatch_started()

    def restore_reserved(_event, after):
        restored = _rewrite_consumed_as(after, "reserved", None)
        after.clear()
        after.update(restored)

    _rewrite_last_budget_event(store, restore_reserved)
    with pytest.raises(
        AggregateStateError,
        match="consumed reservation cannot be released or restored after dispatch started",
    ):
        store.load(observe_expiry=False)


def test_fully_rehashed_consumed_reservation_cannot_be_restored_to_released(tmp_path):
    store, _ = _dispatch_ready(tmp_path)
    store.record_provider_dispatch_started()

    def restore_released(event, after):
        restored = _rewrite_consumed_as(after, "released", event["occurred_at"])
        after.clear()
        after.update(restored)

    _rewrite_last_budget_event(store, restore_released)
    with pytest.raises(
        AggregateStateError,
        match="consumed reservation cannot be released or restored after dispatch started",
    ):
        store.load(observe_expiry=False)


def test_fully_rehashed_release_event_after_dispatch_is_prohibited(tmp_path):
    store, clock = _dispatch_ready(tmp_path)
    consumed = store.record_provider_dispatch_started()
    clock.now += timedelta(minutes=15)
    occurred_at = clock.now.isoformat().replace("+00:00", "Z")
    after = _rewrite_consumed_as(consumed, "released", occurred_at)
    reservation = consumed["provider_budget_reservations"]["eval-v4-01"]
    release = store._make_event(
        consumed,
        after,
        "provider_budget_released",
        {
            "case_id": "eval-v4-01",
            "reservation_sha256": reservation["reservation_sha256"],
            "proof": "expired_unused_dispatch_not_started",
        },
        occurred_at=clock.now,
    )
    _append_rehashed_event(store, release)
    with pytest.raises(
        AggregateStateError,
        match="provider budget release prohibited after dispatch started",
    ):
        store.load(observe_expiry=False)


def test_released_or_budget_unauthorized_reservation_cannot_start_dispatch(tmp_path):
    released_store, released_clock = _dispatch_ready(tmp_path / "released")
    released_clock.now += timedelta(minutes=15)
    released_store.release_expired_preflight_budget()
    with pytest.raises(AggregateStateError, match="preconditions"):
        released_store.record_provider_dispatch_started()

    unauthorized_store, _ = _make_budget_ready(tmp_path / "unauthorized")
    with pytest.raises(AggregateStateError, match="preconditions"):
        unauthorized_store.record_provider_dispatch_started()
    state = unauthorized_store.load()
    assert state["counters"]["token_preflights_consumed"] == 0
    assert all(event["operation"] != "provider_dispatch_started" for event in unauthorized_store._read_journal()["events"])


def test_consumed_case_01_and_reserved_case_02_account_together(tmp_path):
    store, _ = _dispatch_ready(tmp_path, SequentialBudgetStore)
    store.record_provider_dispatch_started()
    store.synthetic_advance_current_case()
    store.prepare_preflight_grant()
    state = store.authorize_preflight_budget()
    assert state["counters"] == {
        "token_preflights_consumed": 1, "token_preflights_reserved": 1,
        "generations_consumed": 0, "generations_reserved": 0, "retries": 0,
        "provider_spend_reserved_usd": "0.03", "provider_spend_consumed_usd": "0.03",
    }
    assert state["budget_accounting"]["aggregate"]["remaining_provider_capacity_usd"] == "0.18"
    assert state["budget_accounting"]["cases"]["eval-v4-01"]["consumed_preflight_exposure_usd"] == "0.03"
    assert state["budget_accounting"]["cases"]["eval-v4-02"]["reserved_preflight_exposure_usd"] == "0.03"


@pytest.mark.parametrize("consumed", (0, 1, 4, 8))
def test_eight_slot_reserved_consumed_combinations_are_valid(tmp_path, consumed):
    store, _ = _dispatch_ready(tmp_path, SequentialBudgetStore)
    for index in range(8):
        if index:
            store.prepare_preflight_grant()
            store.authorize_preflight_budget()
        if index < consumed:
            store.record_provider_dispatch_started()
        if index < 7:
            store.synthetic_advance_current_case()
    state = store.load()
    assert state["counters"]["token_preflights_consumed"] == consumed
    assert state["counters"]["token_preflights_reserved"] == 8 - consumed
    assert state["counters"]["token_preflights_consumed"] + state["counters"]["token_preflights_reserved"] == 8
    assert state["budget_accounting"]["aggregate"]["remaining_provider_capacity_usd"] == "0.00"


def test_dispatch_seam_is_state_only_and_not_public_cli():
    source = Path(__file__).with_name("v4_formal_evaluation_live_state.py").read_text()
    tree = ast.parse(source)
    imports = {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    imports |= {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
    assert not any(name.startswith(("openai", "socket", "httpx", "requests")) for name in imports)
    assert "OPENAI_API_KEY" not in source
    cli = Path(__file__).with_name("v4_formal_evaluation_live_cli.py").read_text()
    assert "provider_dispatch_started" not in cli
    assert "record-preflight-dispatch-started" not in cli
