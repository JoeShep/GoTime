from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from run_openai_stage_b_v4_pilot import prepare_frozen_v4_provider_metadata
from v4_formal_evaluation_live_cases import (
    AiCaseEnvelopeError, ENVELOPE_SCHEMA, ENVELOPE_VERSION,
    build_ai_case_envelope, build_all_ai_case_envelopes, envelope_digest_map,
)
from v4_formal_evaluation_live_deterministic import resolve_deterministic_cases
from v4_formal_evaluation_live_models import AI_CASE_ORDER, EMPTY_CASE_IDS, digest, immutable_package
from v4_formal_evaluation_live_state import AggregateStateError, AggregateStore, _event_digest


class Clock:
    def __init__(self) -> None:
        self.now = datetime(2026, 8, 10, 12, tzinfo=timezone.utc)

    def __call__(self):
        return self.now


@pytest.fixture
def deterministic_ready(tmp_path):
    clock = Clock()
    store = AggregateStore(tmp_path, clock)
    store.initialize("Operator", "Reviewer")
    store.resume("Reviewer")
    resolve_deterministic_cases(store)
    return store, clock


def _valid_binding_event(store):
    before = store.load()
    envelopes = build_all_ai_case_envelopes()
    after = json.loads(json.dumps(before))
    after["ai_case_envelopes"] = envelopes
    return store._make_event(
        before, after, "ai_case_envelopes_bound",
        {"envelope_count": 8, "envelope_digests": envelope_digest_map(envelopes)},
    )


def _rehash_envelope(envelope):
    envelope["envelope_sha256"] = digest({
        "envelope_schema": envelope["envelope_schema"],
        "envelope_version": envelope["envelope_version"],
        "immutable_binding": envelope["immutable_binding"],
    })


def _persist_rehashed_attack(store, event):
    envelopes = event["after_state"]["ai_case_envelopes"]
    event["metadata"] = {
        "envelope_count": len(envelopes),
        "envelope_digests": {
            case_id: envelope["envelope_sha256"] for case_id, envelope in envelopes.items()
        },
    }
    event["event_sha256"] = _event_digest(event)
    event["after_state"]["history_head_sha256"] = event["event_sha256"]
    journal = json.loads(store.journal_path.read_text())
    journal["events"].append(event)
    store.journal_path.write_text(json.dumps(journal))
    store.snapshot_path.write_text(json.dumps(event["after_state"]))


def _rewrite_rehashed_bound_event(store, mutate_envelopes):
    store.bind_ai_case_envelopes()
    journal = json.loads(store.journal_path.read_text())
    event = journal["events"][-1]
    envelopes = mutate_envelopes(event["after_state"]["ai_case_envelopes"])
    event["after_state"]["ai_case_envelopes"] = envelopes
    event["metadata"] = {
        "envelope_count": len(envelopes),
        "envelope_digests": {
            case_id: envelope["envelope_sha256"] for case_id, envelope in envelopes.items()
        },
    }
    event["event_sha256"] = _event_digest(event)
    event["after_state"]["history_head_sha256"] = event["event_sha256"]
    store.journal_path.write_text(json.dumps(journal))
    store.snapshot_path.write_text(json.dumps(event["after_state"]))
    return event


def test_all_eight_envelopes_are_exact_unique_and_non_authoritative():
    envelopes = build_all_ai_case_envelopes()
    assert envelopes == build_all_ai_case_envelopes()
    assert tuple(envelopes) == AI_CASE_ORDER
    assert len(set(envelope_digest_map(envelopes).values())) == 8
    for case_id, envelope in envelopes.items():
        assert envelope["envelope_schema"] == ENVELOPE_SCHEMA
        assert envelope["envelope_version"] == ENVELOPE_VERSION
        assert envelope["immutable_binding"]["case_id"] == case_id
        assert envelope["immutable_binding"]["provider_authority"] is False
        assert envelope["immutable_binding"]["case_budget_policy"] == {
            "maximum_token_preflights": 1,
            "maximum_generations": 1,
            "maximum_retries": 0,
            "provider_ceiling_usd": "0.03",
            "spending_authorized": False,
        }
        assert envelope["phase_lifecycle"] == {
            "preflight_status": "not_authorized",
            "generation_status": "not_authorized",
            "provider_attempts_consumed": 0,
            "terminal": False,
            "review_status": "not_started",
            "evidence_deletion_status": "not_applicable",
            "closure_status": "open",
        }


@pytest.mark.parametrize("case_id", EMPTY_CASE_IDS)
def test_deterministic_cases_cannot_build_ai_envelopes(case_id):
    with pytest.raises(AiCaseEnvelopeError, match="not a frozen AI case"):
        build_ai_case_envelope(case_id)


def test_each_envelope_matches_frozen_request_identity_and_provider_metadata():
    envelopes = build_all_ai_case_envelopes()
    bindings = {item["case_id"]: item for item in immutable_package()["case_bindings"]}
    metadata = prepare_frozen_v4_provider_metadata()
    for case_id in AI_CASE_ORDER:
        immutable = envelopes[case_id]["immutable_binding"]
        frozen = bindings[case_id]
        assert immutable["deterministic_case_input_sha256"] == frozen["deterministic_case_input_sha256"]
        assert immutable["deterministic_request_sha256"] == frozen["deterministic_request_sha256"]
        assert immutable["canonical_attempt_sha256"] == frozen["canonical_attempt_sha256"]
        assert immutable["provider_fingerprint"] == frozen["provider_fingerprint"]
        assert immutable["provider"] == metadata.pilot_configuration["identity"]["provider"]
        assert immutable["ai_model_identifier"] == metadata.pilot_configuration["identity"]["ai_model_identifier"]
        assert immutable["sdk"] == metadata.pilot_configuration["identity"]["sdk_pin"]


def test_binding_is_atomic_durable_and_idempotent(deterministic_ready):
    store, clock = deterministic_ready
    first = store.bind_ai_case_envelopes()
    count = first["history_count"]
    second = store.bind_ai_case_envelopes()
    resumed = AggregateStore(store.root, clock).load()
    assert second == first == resumed
    assert count == 6
    assert tuple(resumed["ai_case_envelopes"]) == AI_CASE_ORDER
    assert resumed["next_case_id"] == "eval-v4-01"
    assert set(resumed["counters"].values()) == {0, "0.00"}
    assert resumed["provider_authority"] is False
    assert resumed["immutable_package"]["budget_policy"]["spending_authorized"] is False
    assert resumed["cases"]["eval-v4-07"]["deterministic_outcome"]["reason_state"] == "known(false)"
    assert resumed["cases"]["eval-v4-08"]["deterministic_outcome"]["reason_state"] == "not_applicable"


@pytest.mark.parametrize(
    "mutation",
    (
        "request", "attempt", "fingerprint", "whole_swap", "case_input",
        "provider", "model", "sdk", "aggregate", "manifest", "configuration",
        "ceiling", "missing", "extra", "deterministic_target",
    ),
)
def test_fully_rehashed_cross_case_and_envelope_attacks_fail(deterministic_ready, mutation):
    store, _ = deterministic_ready
    event = _valid_binding_event(store)
    envelopes = event["after_state"]["ai_case_envelopes"]
    first, second = envelopes["eval-v4-01"], envelopes["eval-v4-02"]
    if mutation in {"request", "attempt", "fingerprint"}:
        field = {
            "request": "deterministic_request_sha256",
            "attempt": "canonical_attempt_sha256",
            "fingerprint": "provider_fingerprint",
        }[mutation]
        first["immutable_binding"][field] = second["immutable_binding"][field]
        _rehash_envelope(first)
    elif mutation == "whole_swap":
        envelopes["eval-v4-01"], envelopes["eval-v4-02"] = second, first
    elif mutation == "case_input":
        first["immutable_binding"]["deterministic_case_input_sha256"] = "0" * 64
        _rehash_envelope(first)
    elif mutation in {"provider", "model", "sdk", "aggregate", "manifest", "configuration", "ceiling"}:
        field, value = {
            "provider": ("provider", "ForeignProvider"),
            "model": ("ai_model_identifier", "foreign-model"),
            "sdk": ("sdk", "openai==0.0.0"),
            "aggregate": ("aggregate_id", "foreign-aggregate"),
            "manifest": ("frozen_v4_manifest_sha256", "0" * 64),
            "configuration": ("request_configuration", dict(first["immutable_binding"]["request_configuration"], automatic_retries=1)),
            "ceiling": ("case_budget_policy", dict(first["immutable_binding"]["case_budget_policy"], provider_ceiling_usd="0.04")),
        }[mutation]
        first["immutable_binding"][field] = value
        _rehash_envelope(first)
    elif mutation == "missing":
        del envelopes["eval-v4-10"]
    elif mutation == "extra":
        envelopes["eval-v4-11"] = json.loads(json.dumps(first))
    else:
        envelopes["eval-v4-07"] = json.loads(json.dumps(first))
    _persist_rehashed_attack(store, event)
    with pytest.raises(AggregateStateError):
        store.load(observe_expiry=False)


def test_replay_rejects_fully_rehashed_ai_envelope_order_drift(deterministic_ready):
    store, _ = deterministic_ready
    changed_order = (
        "eval-v4-02", "eval-v4-01", "eval-v4-03", "eval-v4-04",
        "eval-v4-05", "eval-v4-06", "eval-v4-09", "eval-v4-10",
    )

    def reorder(envelopes):
        return {case_id: envelopes[case_id] for case_id in changed_order}

    event = _rewrite_rehashed_bound_event(store, reorder)
    persisted = event["after_state"]["ai_case_envelopes"]
    assert tuple(persisted) == changed_order
    assert set(persisted) == set(AI_CASE_ORDER)
    assert {
        case_id: persisted[case_id]["envelope_sha256"] for case_id in AI_CASE_ORDER
    } == envelope_digest_map(build_all_ai_case_envelopes())
    assert event["event_sha256"] == _event_digest(event)
    with pytest.raises(AggregateStateError, match="AI case envelopes do not match"):
        store.load(observe_expiry=False)


def test_replay_rejects_self_consistent_duplicate_ai_envelope_digest(deterministic_ready):
    store, _ = deterministic_ready

    def duplicate(envelopes):
        envelopes["eval-v4-02"] = json.loads(json.dumps(envelopes["eval-v4-01"]))
        return envelopes

    event = _rewrite_rehashed_bound_event(store, duplicate)
    persisted = event["after_state"]["ai_case_envelopes"]
    first, duplicate_copy = persisted["eval-v4-01"], persisted["eval-v4-02"]
    assert first == duplicate_copy
    assert first["envelope_sha256"] == digest({
        "envelope_schema": first["envelope_schema"],
        "envelope_version": first["envelope_version"],
        "immutable_binding": first["immutable_binding"],
    })
    assert len({envelope["envelope_sha256"] for envelope in persisted.values()}) == 7
    assert event["event_sha256"] == _event_digest(event)
    with pytest.raises(AggregateStateError, match="AI envelope binding metadata is not exact"):
        store.load(observe_expiry=False)


def test_crash_after_history_commit_recovers_all_envelopes(deterministic_ready):
    store, clock = deterministic_ready

    def fail(boundary):
        if boundary == "after_history_replace":
            raise RuntimeError("synthetic crash")

    with pytest.raises(RuntimeError, match="synthetic crash"):
        AggregateStore(store.root, clock, fail).bind_ai_case_envelopes()
    history = store.journal_path.read_bytes()
    recovered = AggregateStore(store.root, clock).load()
    assert store.journal_path.read_bytes() == history
    assert recovered["ai_case_envelopes"] == build_all_ai_case_envelopes()
    assert recovered["history_count"] == 6
    assert AggregateStore(store.root, clock).bind_ai_case_envelopes()["history_count"] == 6


def test_expiry_before_binding_fails_closed(deterministic_ready):
    store, clock = deterministic_ready
    state = store.load()
    clock.now = datetime.fromisoformat(state["expires_at"].replace("Z", "+00:00"))
    with pytest.raises(AggregateStateError, match="active coordination"):
        store.bind_ai_case_envelopes()
    expired = store.load()
    assert expired["status"] == "expired_paused"
    assert expired["ai_case_envelopes"] == {}
    assert expired["next_case_id"] is None


def test_expiry_after_binding_preserves_inactive_envelopes(deterministic_ready):
    store, clock = deterministic_ready
    bound = store.bind_ai_case_envelopes()
    clock.now = datetime.fromisoformat(bound["expires_at"].replace("Z", "+00:00"))
    expired = store.load()
    assert expired["status"] == "expired_paused"
    assert expired["ai_case_envelopes"] == bound["ai_case_envelopes"]
    assert expired["next_case_id"] is None
    assert all(
        envelope["phase_lifecycle"]["preflight_status"] == "not_authorized"
        and envelope["phase_lifecycle"]["generation_status"] == "not_authorized"
        for envelope in expired["ai_case_envelopes"].values()
    )
