from __future__ import annotations

import ast
import json
import socket
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import openai

import run_openai_stage_b_v4_pilot as frozen_provider
import v4_formal_evaluation_live_models as live_models
from v4_formal_evaluation_live_cases import build_all_ai_case_envelopes
from v4_formal_evaluation_live_deterministic import resolve_deterministic_cases
from v4_formal_evaluation_live_grants import (
    BudgetAuthorizationUnavailable, PREFLIGHT_GRANT_LIFETIME,
    PREFLIGHT_GRANT_SCHEMA, PREFLIGHT_GRANT_STATES, PREFLIGHT_GRANT_VERSION, PreflightGrantError,
    _activate_preflight_grant_synthetic, activate_preflight_grant,
    build_preflight_grant, grant_is_expired,
)
from v4_formal_evaluation_live_models import AI_CASE_ORDER, digest
from v4_formal_evaluation_live_state import AggregateStateError, AggregateStore, _event_digest


class Clock:
    def __init__(self) -> None:
        self.now = datetime(2026, 8, 10, 12, tzinfo=timezone.utc)

    def __call__(self):
        return self.now


@pytest.fixture
def grant_ready(tmp_path):
    clock = Clock()
    store = AggregateStore(tmp_path, clock)
    store.initialize("Operator", "Reviewer")
    store.resume("Reviewer")
    resolve_deterministic_cases(store)
    store.bind_ai_case_envelopes()
    return store, clock


def _rehash_grant(grant):
    grant["grant_sha256"] = digest({
        "grant_schema": grant["grant_schema"],
        "grant_version": grant["grant_version"],
        "immutable_binding": grant["immutable_binding"],
    })


def _rewrite_prepared_event(store, mutate):
    store.prepare_preflight_grant()
    journal = json.loads(store.journal_path.read_text())
    event = journal["events"][-1]
    grant = event["after_state"]["preflight_grants"]["eval-v4-01"]
    mutate(grant, event["after_state"])
    _rehash_grant(grant)
    event["metadata"]["grant_sha256"] = grant["grant_sha256"]
    event["event_sha256"] = _event_digest(event)
    event["after_state"]["history_head_sha256"] = event["event_sha256"]
    store.journal_path.write_text(json.dumps(journal))
    store.snapshot_path.write_text(json.dumps(event["after_state"]))


def test_exact_next_case_candidate_is_reproducible_bound_and_non_authoritative(grant_ready):
    store, clock = grant_ready
    first = store.prepare_preflight_grant()
    count = first["history_count"]
    assert store.prepare_preflight_grant() == first
    assert first["history_count"] == count
    grant = first["preflight_grants"]["eval-v4-01"]
    envelope = first["ai_case_envelopes"]["eval-v4-01"]
    assert grant == build_preflight_grant("eval-v4-01", envelope, clock.now)
    assert grant["grant_schema"] == PREFLIGHT_GRANT_SCHEMA
    assert grant["grant_version"] == PREFLIGHT_GRANT_VERSION
    assert grant["grant_sha256"] == "757155c6427132e8ca3a5bdd37a0c3a93adfb0fb386684f403b1940fe0ca0913"
    assert PREFLIGHT_GRANT_STATES == ("prepared", "active", "consumed", "expired", "closed")
    assert grant["immutable_binding"]["case_envelope_sha256"] == envelope["envelope_sha256"]
    assert grant["immutable_binding"]["phase"] == "preflight"
    assert grant["immutable_binding"]["conservative_operation_ceiling_usd"] == live_models.PREFLIGHT_CONSERVATIVE_PROVIDER_EXPOSURE_USD
    assert grant["immutable_binding"]["per_case_provider_ceiling_usd"] == live_models.PER_CASE_PROVIDER_CEILING_USD
    assert live_models.PREFLIGHT_CONSERVATIVE_PROVIDER_EXPOSURE_USD == "0.00"
    assert live_models.PER_CASE_PROVIDER_CEILING_USD == "0.03"
    assert grant["lifecycle"] == {
        "status": "prepared", "attempt_status": "unused",
        "budget_authorization": "unavailable_milestone_5",
        "provider_authority": False, "spending_authorized": False,
        "generation_authorized": False, "dispatch_authorized": False,
    }
    assert first["next_case_id"] == "eval-v4-01"
    assert set(first["counters"].values()) == {0, "0.00"}


def test_grant_runtime_separates_canonical_preflight_exposure_from_case_ceiling():
    source = (Path(__file__).parent / "v4_formal_evaluation_live_grants.py").read_text()
    tree = ast.parse(source)
    string_literals = {
        node.value for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    assert "0.03" not in string_literals
    assert "0.00" not in string_literals
    assert source.count("live_models.PREFLIGHT_CONSERVATIVE_PROVIDER_EXPOSURE_USD") == 1
    assert source.count("live_models.PER_CASE_PROVIDER_CEILING_USD") == 1


def test_deterministic_and_arbitrary_case_targets_are_rejected():
    envelopes = build_all_ai_case_envelopes()
    now = datetime(2026, 8, 10, tzinfo=timezone.utc)
    for case_id in ("eval-v4-07", "eval-v4-08", "eval-v4-02"):
        with pytest.raises(PreflightGrantError, match="does not match"):
            build_preflight_grant(case_id, envelopes["eval-v4-01"], now)


@pytest.mark.parametrize(
    "mutation",
    (
        "case", "envelope", "request", "attempt", "fingerprint", "provider",
        "model", "sdk", "manifest", "phase", "duration", "ceiling", "aggregate",
    ),
)
def test_fully_rehashed_preflight_grant_identity_attacks_fail(grant_ready, mutation):
    store, _ = grant_ready
    other = build_all_ai_case_envelopes()["eval-v4-02"]["immutable_binding"]

    def mutate(grant, _state):
        binding = grant["immutable_binding"]
        field, value = {
            "case": ("case_id", "eval-v4-02"),
            "envelope": ("case_envelope_sha256", build_all_ai_case_envelopes()["eval-v4-02"]["envelope_sha256"]),
            "request": ("deterministic_request_sha256", other["deterministic_request_sha256"]),
            "attempt": ("canonical_attempt_sha256", other["canonical_attempt_sha256"]),
            "fingerprint": ("provider_fingerprint", other["provider_fingerprint"]),
            "provider": ("provider", "ForeignProvider"),
            "model": ("ai_model_identifier", "foreign-model"),
            "sdk": ("sdk", "openai==0"),
            "manifest": ("frozen_v4_manifest_sha256", "0" * 64),
            "phase": ("phase", "generation"),
            "duration": ("expires_at", "2026-08-10T12:16:00Z"),
            "ceiling": ("conservative_operation_ceiling_usd", "0.04"),
            "aggregate": ("aggregate_id", "foreign"),
        }[mutation]
        binding[field] = value

    _rewrite_prepared_event(store, mutate)
    with pytest.raises((AggregateStateError, PreflightGrantError)):
        store.load(observe_expiry=False)


def test_replay_rejects_fully_rehashed_deterministic_case_preflight_target(grant_ready):
    store, _ = grant_ready
    store.prepare_preflight_grant()
    journal = json.loads(store.journal_path.read_text())
    event = journal["events"][-1]
    after = event["after_state"]
    grant = after["preflight_grants"].pop("eval-v4-01")
    grant["immutable_binding"]["case_id"] = "eval-v4-07"
    grant["immutable_binding"]["deterministic_case_input_sha256"] = after["cases"]["eval-v4-07"]["deterministic_case_input_sha256"]
    _rehash_grant(grant)
    after["preflight_grants"] = {"eval-v4-07": grant}
    event["metadata"] = {
        "case_id": "eval-v4-07",
        "grant_sha256": grant["grant_sha256"],
    }
    event["event_sha256"] = _event_digest(event)
    after["history_head_sha256"] = event["event_sha256"]
    store.journal_path.write_text(json.dumps(journal))
    store.snapshot_path.write_text(json.dumps(after))

    assert event["event_sha256"] == _event_digest(event)
    assert after["history_count"] == len(journal["events"])
    assert after["history_head_sha256"] == event["event_sha256"]
    with pytest.raises(AggregateStateError, match="exact next enveloped AI case"):
        store.load(observe_expiry=False)


@pytest.mark.parametrize("offset,expired", [(0, False), (899, False), (900, True), (901, True)])
def test_fifteen_minute_expiration_boundary(grant_ready, offset, expired):
    store, clock = grant_ready
    state = store.prepare_preflight_grant()
    grant = state["preflight_grants"]["eval-v4-01"]
    assert grant_is_expired(grant, clock.now + timedelta(seconds=offset)) is expired
    assert PREFLIGHT_GRANT_LIFETIME == timedelta(minutes=15)


def test_default_budget_port_denies_without_persisting_authority(grant_ready, monkeypatch):
    store, clock = grant_ready
    calls = {"request": 0, "client": 0, "network": 0}

    def forbidden(*_args, **_kwargs):
        calls["request"] += 1
        raise AssertionError("provider constructor entered")

    def forbidden_client(*_args, **_kwargs):
        calls["client"] += 1
        raise AssertionError("provider client constructed")

    def forbidden_network(*_args, **_kwargs):
        calls["network"] += 1
        raise AssertionError("network entered")

    monkeypatch.setattr(frozen_provider, "construct_frozen_v4_provider_request", forbidden)
    monkeypatch.setattr(openai, "OpenAI", forbidden_client)
    monkeypatch.setattr(socket, "create_connection", forbidden_network)
    state = store.prepare_preflight_grant()
    history = store.journal_path.read_bytes()
    grant = state["preflight_grants"]["eval-v4-01"]
    with pytest.raises(BudgetAuthorizationUnavailable, match="Milestone 5"):
        activate_preflight_grant(grant, state, clock.now)
    assert store.journal_path.read_bytes() == history
    assert store.load() == state
    assert calls == {"request": 0, "client": 0, "network": 0}
    assert state["provider_authority"] is False
    assert set(state["counters"].values()) == {0, "0.00"}


def test_test_only_approving_callable_is_ephemeral_and_cannot_dispatch(grant_ready):
    store, clock = grant_ready
    state = store.prepare_preflight_grant()
    grant = state["preflight_grants"]["eval-v4-01"]
    synthetic = _activate_preflight_grant_synthetic(
        grant, state, clock.now, budget_authorize=lambda _: True,
    )
    assert synthetic["lifecycle"]["status"] == "active_synthetic_only"
    assert synthetic["lifecycle"]["provider_authority"] is False
    assert synthetic["lifecycle"]["dispatch_authorized"] is False
    assert store.load() == state


def test_grant_and_aggregate_expiration_both_fail_closed(grant_ready):
    store, clock = grant_ready
    state = store.prepare_preflight_grant()
    grant = state["preflight_grants"]["eval-v4-01"]
    clock.now += timedelta(minutes=15)
    with pytest.raises(PreflightGrantError, match="expired"):
        _activate_preflight_grant_synthetic(grant, state, clock.now, budget_authorize=lambda _: True)
    with pytest.raises(AggregateStateError, match="cannot be replaced"):
        store.prepare_preflight_grant()
    clock.now = datetime.fromisoformat(state["expires_at"].replace("Z", "+00:00"))
    expired = store.load()
    with pytest.raises(PreflightGrantError, match="aggregate is not active"):
        _activate_preflight_grant_synthetic(grant, expired, clock.now, budget_authorize=lambda _: True)
    assert expired["status"] == "expired_paused"
    assert expired["preflight_grants"] == state["preflight_grants"]
    assert expired["next_case_id"] is None


def test_history_first_crash_recovers_prepared_grant(grant_ready):
    store, clock = grant_ready

    def fail(boundary):
        if boundary == "after_history_replace":
            raise RuntimeError("synthetic crash")

    with pytest.raises(RuntimeError, match="synthetic crash"):
        AggregateStore(store.root, clock, fail).prepare_preflight_grant()
    history = store.journal_path.read_bytes()
    recovered = AggregateStore(store.root, clock).load()
    assert store.journal_path.read_bytes() == history
    assert tuple(recovered["preflight_grants"]) == ("eval-v4-01",)
    assert AggregateStore(store.root, clock).prepare_preflight_grant()["history_count"] == recovered["history_count"]


def test_runtime_modules_have_no_provider_client_credential_or_network_capability():
    root = Path(__file__).parent
    for name in ("v4_formal_evaluation_live_grants.py", "v4_formal_evaluation_live_state.py", "v4_formal_evaluation_live_cli.py"):
        source = (root / name).read_text()
        tree = ast.parse(source)
        imports = {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
        imports |= {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
        assert not any(item.startswith(("openai", "httpx", "requests", "socket")) for item in imports)
        assert "OPENAI_API_KEY" not in source
    assert "provider_dispatch_started" not in (root / "v4_formal_evaluation_live_cli.py").read_text()
