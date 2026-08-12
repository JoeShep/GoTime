from __future__ import annotations

import ast
import json
import socket
import tomllib
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import openai
import pytest

import run_openai_stage_b_v4_pilot as frozen_provider
from v4_formal_evaluation_live_budget import (
    BUDGET_RESERVATION_SCHEMA, BUDGET_RESERVATION_VERSION, BudgetError,
    build_preflight_reservation, derive_budget_accounting,
    enforce_prospective_capacity, reservation_identity,
)
from v4_formal_evaluation_live_deterministic import resolve_deterministic_cases
from v4_formal_evaluation_live_grants import (
    BudgetAuthorizationUnavailable, activate_preflight_grant,
    budget_authorized_lifecycle, released_lifecycle,
)
from v4_formal_evaluation_live_models import (
    AGGREGATE_PROVIDER_CEILING_USD, MAX_GENERATIONS, MAX_RETRIES,
    MAX_TOKEN_PREFLIGHTS, PER_CASE_PROVIDER_CEILING_USD,
    PREFLIGHT_CONSERVATIVE_PROVIDER_EXPOSURE_USD,
)
from v4_formal_evaluation_live_cli import parser
from v4_formal_evaluation_live_state import AggregateStateError, AggregateStore, _event_digest
from v4_formal_evaluation_live_state import (
    _lock, canonical_json, derive_next_case,
)


class Clock:
    def __init__(self) -> None:
        self.now = datetime(2026, 8, 10, 12, tzinfo=timezone.utc)

    def __call__(self):
        return self.now


class SequentialBudgetStore(AggregateStore):
    """Test-only persisted case advancement; never accepted by production replay."""

    _SYNTHETIC_ADVANCE = "_synthetic_budget_case_advanced"

    def _validate_operation_semantics(self, event, previous_time):
        if event["operation"] != self._SYNTHETIC_ADVANCE:
            return super()._validate_operation_semantics(event, previous_time)
        before, after, metadata = event["before_state"], event["after_state"], event["metadata"]
        case_id = metadata.get("case_id") if isinstance(metadata, dict) else None
        if (
            set(metadata or {}) != {"case_id", "test_only"}
            or metadata["test_only"] is not True
            or case_id != before["next_case_id"]
            or before["status"] != "in_progress"
            or before["cases"][case_id]["coordination_status"] != "untouched"
        ):
            raise AggregateStateError("synthetic budget case advancement is invalid")
        expected = json.loads(canonical_json(before))
        expected["cases"][case_id]["coordination_status"] = "terminal"
        expected["next_case_id"] = derive_next_case(expected)
        expected["history_count"] = after["history_count"]
        expected["history_head_sha256"] = after["history_head_sha256"]
        if after != expected:
            raise AggregateStateError("synthetic budget case advancement mutated prohibited state")

    def synthetic_advance_current_case(self):
        with _lock(self.root):
            state = self._load_unlocked(observe_expiry=True, recover_projection=True)
            case_id = state["next_case_id"]
            if case_id not in state["provider_budget_reservations"]:
                raise AggregateStateError("synthetic advancement requires the current case reservation")
            after = json.loads(canonical_json(state))
            after["cases"][case_id]["coordination_status"] = "terminal"
            after["next_case_id"] = derive_next_case(after)
            event = self._make_event(
                state,
                after,
                self._SYNTHETIC_ADVANCE,
                {"case_id": case_id, "test_only": True},
            )
            journal = self._read_journal()
            journal["events"].append(event)
            canonical = self._validate_journal(journal)[-1]
            self._commit(journal, canonical)
            return canonical


@pytest.fixture
def budget_ready(tmp_path):
    return _make_budget_ready(tmp_path)


def _make_budget_ready(root, store_class=AggregateStore):
    clock = Clock()
    store = store_class(root, clock)
    store.initialize("Operator", "Reviewer")
    store.resume("Reviewer")
    resolve_deterministic_cases(store)
    store.bind_ai_case_envelopes()
    store.prepare_preflight_grant()
    return store, clock


def _rewrite_last_budget_event(store, mutate):
    journal = json.loads(store.journal_path.read_text())
    event = journal["events"][-1]
    after = event["after_state"]
    mutate(event, after)
    event["event_sha256"] = _event_digest(event)
    after["history_head_sha256"] = event["event_sha256"]
    store.journal_path.write_text(json.dumps(journal))
    store.snapshot_path.write_text(json.dumps(after))


def _recompute_projection_accounting(state):
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


def test_canonical_budget_policy_and_decimal_arithmetic():
    assert MAX_TOKEN_PREFLIGHTS == MAX_GENERATIONS == 8
    assert MAX_RETRIES == 0
    assert PER_CASE_PROVIDER_CEILING_USD == "0.03"
    assert AGGREGATE_PROVIDER_CEILING_USD == "0.24"
    assert PREFLIGHT_CONSERVATIVE_PROVIDER_EXPOSURE_USD == "0.00"
    assert Decimal(PER_CASE_PROVIDER_CEILING_USD) * 8 == Decimal(AGGREGATE_PROVIDER_CEILING_USD)
    source = (Path(__file__).parent / "v4_formal_evaluation_live_budget.py").read_text()
    assert "float(" not in source
    assert "PER_CASE_PROVIDER_CEILING_USD" in source
    assert "AGGREGATE_PROVIDER_CEILING_USD" in source


def test_first_exact_reservation_is_reproducible_scoped_and_idempotent(budget_ready):
    store, clock = budget_ready
    first = store.authorize_preflight_budget()
    count = first["history_count"]
    assert store.authorize_preflight_budget() == first
    assert first["history_count"] == count
    grant = first["preflight_grants"]["eval-v4-01"]
    reservation = first["provider_budget_reservations"]["eval-v4-01"]
    expected = build_preflight_reservation(
        {**grant, "lifecycle": {"ignored": True}},
        first["ai_case_envelopes"]["eval-v4-01"],
        clock.now.isoformat().replace("+00:00", "Z"),
    )
    assert reservation == expected
    assert reservation["reservation_schema"] == BUDGET_RESERVATION_SCHEMA
    assert reservation["reservation_version"] == BUDGET_RESERVATION_VERSION
    assert reservation["reservation_sha256"] == reservation_identity(reservation)
    assert reservation["reservation_sha256"] == "8edf28f8378a97796b197bdcb0d0b5bc64b59fbcb2260d5627e313c87c4daec0"
    assert reservation["immutable_binding"]["reservation_amount_usd"] == "0.00"
    assert reservation["immutable_binding"]["operation_count"] == 1
    assert grant["lifecycle"] == budget_authorized_lifecycle()
    assert first["provider_authority"] is False
    assert first["immutable_package"]["budget_policy"]["spending_authorized"] is False
    assert first["counters"] == {
        "token_preflights_consumed": 0, "token_preflights_reserved": 1,
        "generations_consumed": 0, "generations_reserved": 0, "retries": 0,
        "provider_spend_reserved_usd": "0.00", "provider_spend_consumed_usd": "0.00",
    }
    assert first["budget_accounting"]["aggregate"]["remaining_provider_capacity_usd"] == "0.24"
    assert first["budget_accounting"]["cases"]["eval-v4-01"]["remaining_provider_capacity_usd"] == "0.03"


def test_released_case_01_and_reserved_case_02_coexist_in_authoritative_history(tmp_path):
    store, clock = _make_budget_ready(tmp_path, SequentialBudgetStore)
    case_01_reserved = store.authorize_preflight_budget()
    case_01_digest = case_01_reserved["provider_budget_reservations"]["eval-v4-01"]["reservation_sha256"]
    clock.now += timedelta(minutes=15)
    store.release_expired_preflight_budget()
    store.synthetic_advance_current_case()
    store.prepare_preflight_grant()
    case_02_reserved = store.authorize_preflight_budget()

    assert tuple(case_02_reserved["preflight_grants"]) == ("eval-v4-01", "eval-v4-02")
    assert tuple(case_02_reserved["provider_budget_reservations"]) == ("eval-v4-01", "eval-v4-02")
    assert case_02_reserved["provider_budget_reservations"]["eval-v4-01"]["reservation_sha256"] == case_01_digest
    assert case_02_reserved["provider_budget_reservations"]["eval-v4-01"]["lifecycle"]["status"] == "released"
    assert case_02_reserved["provider_budget_reservations"]["eval-v4-02"]["lifecycle"]["status"] == "reserved"
    assert case_02_reserved["counters"]["token_preflights_reserved"] == 1
    assert case_02_reserved["counters"]["provider_spend_reserved_usd"] == "0.00"
    assert case_02_reserved["budget_accounting"]["cases"]["eval-v4-01"]["remaining_provider_capacity_usd"] == "0.03"
    assert case_02_reserved["budget_accounting"]["cases"]["eval-v4-02"]["remaining_provider_capacity_usd"] == "0.03"
    assert SequentialBudgetStore(store.root, clock).load() == case_02_reserved


def test_frozen_preflight_fee_source_and_generation_headroom_are_consistent(tmp_path):
    root = Path(__file__).resolve().parents[3]
    pricing = tomllib.loads(
        (root / "docs/experiments/suggest-moving-service-questions/v1/openai-run-configuration.toml").read_text()
    )["pricing"]
    assert pricing["token_counting_fee"] == "no_separate_fee_documented_as_of_2026-07-30"
    assert pricing["request_or_platform_fee"] == "no_separate_fee_documented_as_of_2026-07-30"
    assert PREFLIGHT_CONSERVATIVE_PROVIDER_EXPOSURE_USD == "0.00"

    store, _ = _make_budget_ready(tmp_path)
    store.authorize_preflight_budget()
    dispatched = store.record_provider_dispatch_started()
    case = dispatched["budget_accounting"]["cases"]["eval-v4-01"]
    assert case["consumed_preflight_exposure_usd"] == "0.00"
    assert Decimal(case["remaining_provider_capacity_usd"]) == Decimal("0.03")
    generation_ceiling = Decimal("0.0019408")
    assert Decimal(case["consumed_preflight_exposure_usd"]) + generation_ceiling <= Decimal(
        PER_CASE_PROVIDER_CEILING_USD
    )


def test_all_eight_authoritative_reservations_coexist_and_rehashed_ninth_slot_fails(tmp_path):
    store, clock = _make_budget_ready(tmp_path, SequentialBudgetStore)
    for index, case_id in enumerate(("eval-v4-01", "eval-v4-02", "eval-v4-03", "eval-v4-04", "eval-v4-05", "eval-v4-06", "eval-v4-09", "eval-v4-10")):
        if index:
            store.prepare_preflight_grant()
        state = store.authorize_preflight_budget()
        assert case_id in state["provider_budget_reservations"]
        if index < 7:
            store.synthetic_advance_current_case()

    assert len(state["preflight_grants"]) == len(state["provider_budget_reservations"]) == 8
    assert state["counters"]["token_preflights_reserved"] == 8
    assert state["counters"]["provider_spend_reserved_usd"] == "0.00"
    assert state["budget_accounting"]["aggregate"]["remaining_provider_capacity_usd"] == "0.24"

    def ninth_counted_slot(event, after):
        reservation = after["provider_budget_reservations"]["eval-v4-10"]
        reservation["immutable_binding"]["operation_count"] = 2
        reservation["reservation_sha256"] = reservation_identity(reservation)
        event["metadata"]["reservation_sha256"] = reservation["reservation_sha256"]
        _recompute_projection_accounting(after)

    _rewrite_last_budget_event(store, ninth_counted_slot)
    with pytest.raises(
        AggregateStateError,
        match="provider preflight operation count exceeds frozen maximum",
    ):
        store.load(observe_expiry=False)


def test_multi_case_history_rejects_deleted_replaced_or_reactivated_prior_record(tmp_path):
    def case_02_store(root):
        store, clock = _make_budget_ready(root, SequentialBudgetStore)
        store.authorize_preflight_budget()
        clock.now += timedelta(minutes=15)
        store.release_expired_preflight_budget()
        store.synthetic_advance_current_case()
        store.prepare_preflight_grant()
        store.authorize_preflight_budget()
        return store

    attacks = {
        "deleted": lambda _event, after: (
            after["provider_budget_reservations"].pop("eval-v4-01"),
            after["preflight_grants"].pop("eval-v4-01"),
            _recompute_projection_accounting(after),
        ),
        "grant_mismatch": lambda _event, after: after["provider_budget_reservations"]["eval-v4-01"]["immutable_binding"].update(
            prepared_grant_sha256=after["preflight_grants"]["eval-v4-02"]["grant_sha256"]
        ),
        "reactivated": lambda _event, after: (
            after["provider_budget_reservations"]["eval-v4-01"]["lifecycle"].update(
                status="reserved", released_amount_usd="0.00", release_reason=None, released_at=None,
            ),
            after["preflight_grants"]["eval-v4-01"].update(lifecycle=budget_authorized_lifecycle()),
            _recompute_projection_accounting(after),
        ),
    }
    for name, attack in attacks.items():
        store = case_02_store(tmp_path / name)
        def mutate(event, after, attack=attack):
            attack(event, after)
            for reservation in after["provider_budget_reservations"].values():
                reservation["reservation_sha256"] = reservation_identity(reservation)
            current = after["provider_budget_reservations"].get("eval-v4-02")
            if current is not None:
                event["metadata"]["reservation_sha256"] = current["reservation_sha256"]
        _rewrite_last_budget_event(store, mutate)
        with pytest.raises((AggregateStateError, BudgetError, KeyError)):
            store.load(observe_expiry=False)


def test_case_02_reservation_history_crash_recovers_both_case_records(tmp_path):
    store, clock = _make_budget_ready(tmp_path, SequentialBudgetStore)
    store.authorize_preflight_budget()
    clock.now += timedelta(minutes=15)
    store.release_expired_preflight_budget()
    store.synthetic_advance_current_case()
    store.prepare_preflight_grant()

    def fail(boundary):
        if boundary == "after_history_replace":
            raise RuntimeError("synthetic crash")

    with pytest.raises(RuntimeError, match="synthetic crash"):
        SequentialBudgetStore(store.root, clock, fail).authorize_preflight_budget()
    history = store.journal_path.read_bytes()
    recovered = SequentialBudgetStore(store.root, clock).load()
    assert store.journal_path.read_bytes() == history
    assert tuple(recovered["provider_budget_reservations"]) == ("eval-v4-01", "eval-v4-02")
    assert recovered["provider_budget_reservations"]["eval-v4-01"]["lifecycle"]["status"] == "released"
    assert recovered["provider_budget_reservations"]["eval-v4-02"]["lifecycle"]["status"] == "reserved"
    assert recovered["counters"]["token_preflights_reserved"] == 1
    assert recovered["counters"]["provider_spend_reserved_usd"] == "0.00"


@pytest.mark.parametrize(
    "case_reserved,case_consumed,requested,allowed",
    [
        ("0.00", "0.00", "0.02", True),
        ("0.00", "0.00", "0.03", True),
        ("0.00", "0.00", "0.04", False),
        ("0.01", "0.00", "0.03", False),
        ("0.00", "0.01", "0.03", False),
    ],
)
def test_per_case_prospective_capacity(case_reserved, case_consumed, requested, allowed):
    kwargs = dict(
        case_reserved=Decimal(case_reserved), case_consumed=Decimal(case_consumed),
        aggregate_reserved=Decimal("0.00"), aggregate_consumed=Decimal("0.00"),
        preflights_reserved=0, preflights_consumed=0,
        requested_amount=Decimal(requested),
    )
    if allowed:
        enforce_prospective_capacity(**kwargs)
    else:
        with pytest.raises(BudgetError, match="per-case"):
            enforce_prospective_capacity(**kwargs)


@pytest.mark.parametrize(
    "reserved,consumed,requested,allowed",
    [
        ("0.20", "0.00", "0.03", True),
        ("0.21", "0.00", "0.03", True),
        ("0.22", "0.00", "0.03", False),
        ("0.12", "0.10", "0.03", False),
    ],
)
def test_aggregate_prospective_capacity(reserved, consumed, requested, allowed):
    kwargs = dict(
        case_reserved=Decimal("0.00"), case_consumed=Decimal("0.00"),
        aggregate_reserved=Decimal(reserved), aggregate_consumed=Decimal(consumed),
        preflights_reserved=0, preflights_consumed=0,
        requested_amount=Decimal(requested),
    )
    if allowed:
        enforce_prospective_capacity(**kwargs)
    else:
        with pytest.raises(BudgetError, match="aggregate"):
            enforce_prospective_capacity(**kwargs)


def test_other_case_exposure_counts_only_against_aggregate_capacity():
    enforce_prospective_capacity(
        case_reserved=Decimal("0.00"), case_consumed=Decimal("0.00"),
        aggregate_reserved=Decimal("0.21"), aggregate_consumed=Decimal("0.00"),
        preflights_reserved=7, preflights_consumed=0,
        requested_amount=Decimal("0.03"),
    )
    with pytest.raises(BudgetError, match="aggregate"):
        enforce_prospective_capacity(
            case_reserved=Decimal("0.00"), case_consumed=Decimal("0.00"),
            aggregate_reserved=Decimal("0.22"), aggregate_consumed=Decimal("0.00"),
            preflights_reserved=7, preflights_consumed=0,
            requested_amount=Decimal("0.03"),
        )


@pytest.mark.parametrize("reserved,consumed,allowed", [(7, 0, True), (0, 7, True), (8, 0, False), (4, 4, False)])
def test_preflight_operation_count_limit(reserved, consumed, allowed):
    kwargs = dict(
        case_reserved=Decimal("0.00"), case_consumed=Decimal("0.00"),
        aggregate_reserved=Decimal("0.00"), aggregate_consumed=Decimal("0.00"),
        preflights_reserved=reserved, preflights_consumed=consumed,
        requested_amount=Decimal("0.01"),
    )
    if allowed:
        enforce_prospective_capacity(**kwargs)
    else:
        with pytest.raises(BudgetError, match="operation maximum"):
            enforce_prospective_capacity(**kwargs)


def test_release_requires_expired_grant_and_restores_only_reserved_capacity(budget_ready):
    store, clock = budget_ready
    reserved = store.authorize_preflight_budget()
    with pytest.raises(AggregateStateError, match="expired grant"):
        store.release_expired_preflight_budget()
    clock.now += timedelta(minutes=15)
    released = store.release_expired_preflight_budget()
    assert released["preflight_grants"]["eval-v4-01"]["lifecycle"] == released_lifecycle()
    lifecycle = released["provider_budget_reservations"]["eval-v4-01"]["lifecycle"]
    assert lifecycle["status"] == "released"
    assert lifecycle["provider_dispatch_status"] == "not_started"
    assert lifecycle["released_amount_usd"] == "0.00"
    assert lifecycle["consumed_amount_usd"] == "0.00"
    assert released["counters"]["token_preflights_reserved"] == 0
    assert released["counters"]["provider_spend_reserved_usd"] == "0.00"
    assert released["budget_accounting"]["aggregate"]["remaining_provider_capacity_usd"] == "0.24"
    assert store.release_expired_preflight_budget() == released
    assert reserved["history_count"] + 1 == released["history_count"]


def test_aggregate_expiry_preserves_reservation_until_proven_unused_release(budget_ready):
    store, clock = budget_ready
    reserved = store.authorize_preflight_budget()
    clock.now = datetime.fromisoformat(reserved["expires_at"].replace("Z", "+00:00"))
    expired = store.load()
    assert expired["status"] == "expired_paused"
    assert expired["provider_budget_reservations"] == reserved["provider_budget_reservations"]
    assert expired["counters"]["token_preflights_reserved"] == 1
    assert expired["next_case_id"] is None
    with pytest.raises(AggregateStateError, match="active"):
        store.authorize_preflight_budget()
    released = store.release_expired_preflight_budget()
    assert released["status"] == "expired_paused"
    assert released["counters"]["token_preflights_reserved"] == 0


@pytest.mark.parametrize(
    "mutation",
    (
        "amount", "case", "grant", "phase", "count", "case_ceiling",
        "aggregate_ceiling", "envelope", "negative", "released_over", "deterministic", "future_case",
    ),
)
def test_fully_rehashed_budget_reservation_attacks_fail(budget_ready, mutation):
    store, _ = budget_ready
    store.authorize_preflight_budget()

    def mutate(event, after):
        reservation = after["provider_budget_reservations"].pop("eval-v4-01")
        binding, lifecycle = reservation["immutable_binding"], reservation["lifecycle"]
        if mutation == "amount": binding["reservation_amount_usd"] = "0.01"
        elif mutation == "case": binding["case_id"] = "eval-v4-02"
        elif mutation == "grant": binding["prepared_grant_sha256"] = "0" * 64
        elif mutation == "phase": binding["phase"] = "generation"
        elif mutation == "count": binding["operation_count"] = 2
        elif mutation == "case_ceiling": binding["per_case_provider_ceiling_usd"] = "0.04"
        elif mutation == "aggregate_ceiling": binding["aggregate_provider_ceiling_usd"] = "0.25"
        elif mutation == "envelope": binding["case_envelope_sha256"] = "0" * 64
        elif mutation == "negative": binding["reservation_amount_usd"] = "-0.01"
        elif mutation == "released_over":
            lifecycle.update(status="released", released_amount_usd="0.01", release_reason="expired_unused_dispatch_not_started", released_at=event["occurred_at"])
        elif mutation == "deterministic": binding["case_id"] = "eval-v4-07"
        elif mutation == "future_case": binding["case_id"] = "eval-v4-02"
        reservation["reservation_sha256"] = reservation_identity(reservation)
        key = binding["case_id"] if mutation in {"case", "deterministic", "future_case"} else "eval-v4-01"
        after["provider_budget_reservations"] = {key: reservation}
        event["metadata"]["case_id"] = key
        event["metadata"]["reservation_sha256"] = reservation["reservation_sha256"]
        try:
            _recompute_projection_accounting(after)
        except (BudgetError, KeyError):
            pass

    _rewrite_last_budget_event(store, mutate)
    with pytest.raises((AggregateStateError, BudgetError, KeyError)):
        store.load(observe_expiry=False)


def test_rehashed_derived_total_and_missing_reservation_attacks_fail(budget_ready, tmp_path):
    store, _ = _make_budget_ready(tmp_path / "missing")
    store.authorize_preflight_budget()
    _rewrite_last_budget_event(
        store,
        lambda _event, after: after["budget_accounting"]["aggregate"].update(
            total_provider_exposure_reserved_usd="0.02"
        ),
    )
    with pytest.raises(AggregateStateError):
        store.load(observe_expiry=False)

    store, _ = budget_ready
    store.authorize_preflight_budget()
    def remove(_event, after):
        after["provider_budget_reservations"] = {}
        _recompute_projection_accounting(after)
    _rewrite_last_budget_event(store, remove)
    with pytest.raises(AggregateStateError, match="missing"):
        store.load(observe_expiry=False)


def test_rehashed_consumed_total_and_duplicate_reservation_attacks_fail(budget_ready, tmp_path):
    store, _ = budget_ready
    store.authorize_preflight_budget()
    _rewrite_last_budget_event(
        store,
        lambda _event, after: after["budget_accounting"]["aggregate"].update(
            total_provider_exposure_consumed_usd="0.01"
        ),
    )
    with pytest.raises(AggregateStateError):
        store.load(observe_expiry=False)

    store, _ = _make_budget_ready(tmp_path / "duplicate")
    store.authorize_preflight_budget()
    def duplicate(_event, after):
        original = after["provider_budget_reservations"]["eval-v4-01"]
        after["provider_budget_reservations"]["eval-v4-02"] = json.loads(json.dumps(original))
        _recompute_projection_accounting(after)
    _rewrite_last_budget_event(store, duplicate)
    with pytest.raises(AggregateStateError):
        store.load(observe_expiry=False)


def test_crash_after_reservation_history_recovers_without_double_count(budget_ready):
    store, clock = budget_ready
    def fail(boundary):
        if boundary == "after_history_replace":
            raise RuntimeError("synthetic crash")
    with pytest.raises(RuntimeError, match="synthetic crash"):
        AggregateStore(store.root, clock, fail).authorize_preflight_budget()
    history = store.journal_path.read_bytes()
    recovered = AggregateStore(store.root, clock).load()
    assert store.journal_path.read_bytes() == history
    assert recovered["counters"]["token_preflights_reserved"] == 1
    assert recovered["counters"]["provider_spend_reserved_usd"] == "0.00"
    assert AggregateStore(store.root, clock).authorize_preflight_budget()["history_count"] == recovered["history_count"]


def test_release_history_first_crash_recovers_exactly(budget_ready):
    store, clock = budget_ready
    store.authorize_preflight_budget()
    clock.now += timedelta(minutes=15)
    def fail(boundary):
        if boundary == "after_history_replace":
            raise RuntimeError("synthetic crash")
    with pytest.raises(RuntimeError, match="synthetic crash"):
        AggregateStore(store.root, clock, fail).release_expired_preflight_budget()
    history = store.journal_path.read_bytes()
    recovered = AggregateStore(store.root, clock).load()
    assert store.journal_path.read_bytes() == history
    assert recovered["provider_budget_reservations"]["eval-v4-01"]["lifecycle"]["status"] == "released"
    assert recovered["counters"]["token_preflights_reserved"] == 0


def test_budget_authorization_never_enters_provider_client_or_network(budget_ready, monkeypatch):
    store, _ = budget_ready
    calls = {"request": 0, "client": 0, "network": 0}
    def request(*_args, **_kwargs): calls["request"] += 1; raise AssertionError
    def client(*_args, **_kwargs): calls["client"] += 1; raise AssertionError
    def network(*_args, **_kwargs): calls["network"] += 1; raise AssertionError
    monkeypatch.setattr(frozen_provider, "construct_frozen_v4_provider_request", request)
    monkeypatch.setattr(openai, "OpenAI", client)
    monkeypatch.setattr(socket, "create_connection", network)
    state = store.authorize_preflight_budget()
    lifecycle = state["preflight_grants"]["eval-v4-01"]["lifecycle"]
    assert activate_preflight_grant(
        state["preflight_grants"]["eval-v4-01"], state, store.clock(),
    )["lifecycle"] == budget_authorized_lifecycle()
    assert calls == {"request": 0, "client": 0, "network": 0}
    assert lifecycle["preflight_budget_authorized"] is True
    assert lifecycle["preflight_grant_active"] is True
    assert lifecycle["preflight_spending_authorized"] is True
    assert lifecycle["provider_authority"] is False
    assert lifecycle["spending_authorized"] is False
    assert lifecycle["generation_authorized"] is False
    assert lifecycle["dispatch_authorized"] is False
    assert lifecycle["retry_authorized"] is False
    assert lifecycle["provider_execution_authorized"] is False


def test_activation_has_no_path_around_exact_reservation_and_derived_accounting(budget_ready):
    store, clock = budget_ready
    state = store.authorize_preflight_budget()
    forged = json.loads(json.dumps(state))
    forged["budget_accounting"]["aggregate"]["remaining_provider_capacity_usd"] = "0.23"
    with pytest.raises(BudgetAuthorizationUnavailable, match="projection"):
        activate_preflight_grant(
            forged["preflight_grants"]["eval-v4-01"], forged, clock.now,
        )


def test_public_runtime_budget_modules_have_no_provider_capability():
    root = Path(__file__).parent
    for name in (
        "v4_formal_evaluation_live_budget.py", "v4_formal_evaluation_live_grants.py",
        "v4_formal_evaluation_live_state.py", "v4_formal_evaluation_live_cli.py",
    ):
        source = (root / name).read_text()
        tree = ast.parse(source)
        imports = {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
        imports |= {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
        assert not any(item.startswith(("openai", "httpx", "requests", "socket")) for item in imports)
        assert "OPENAI_API_KEY" not in source
    assert "provider_dispatch_started" not in (root / "v4_formal_evaluation_live_cli.py").read_text()


def test_public_budget_commands_accept_no_case_amount_or_policy_overrides():
    for command in ("authorize-preflight-budget", "release-preflight-budget"):
        with pytest.raises(SystemExit):
            parser().parse_args([command, "--case-id", "eval-v4-02"])
        with pytest.raises(SystemExit):
            parser().parse_args([command, "--amount", "0.01"])
