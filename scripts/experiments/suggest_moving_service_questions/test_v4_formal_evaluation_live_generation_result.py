from __future__ import annotations

import json
import shutil
import subprocess
from copy import deepcopy
from pathlib import Path

import pytest

from test_v4_formal_evaluation_live_execution import CREDENTIAL, FAKE, SyntheticBoundary, prepared_store
from test_v4_formal_evaluation_live_preflight_result import review
from v4_formal_evaluation_live_cli import PUBLIC_COMMANDS
from v4_formal_evaluation_live_execution import ExecutionBoundaryError
from v4_formal_evaluation_live_generation_result import (
    CONTENT_FAILURES, EVIDENCE_SCHEMA, EVIDENCE_VERSION, PROVIDER_FAILURES,
    RESULT_SCHEMA, RESULT_VERSION, lifecycle_status,
)
from v4_formal_evaluation_live_state import AggregateStateError, AggregateStore, _atomic_json, canonical_json
from v4_formal_evaluation_live_models import digest
from v4_formal_evaluation_runner import synthetic_response, valid_synthetic_response

RESULT_SHA256 = "6add9501abe6fe0e52ce8d9e030afda0871187c2a1badf4b7d8f1fd299c9c637"
EVIDENCE_SHA256 = "db870d3ad854ba4a3f044f4be12180f10c6e98ded63f2988970844786d96dc80"
CLOSURE_SHA256 = "246d4eb519b8511fdf05c7ae8af3f134a63f16fa03e5a506369b5d4a051a514c"


def generation_ready(tmp_path):
    store, clock = prepared_store(tmp_path)
    store.record_provider_dispatch_started()
    store.record_preflight_success(2852)
    review(store, clock)
    store._prepare_generation_grant_from_reviewed_evidence()
    store._authorize_generation_budget()
    return store, clock


class GenerationBoundary(SyntheticBoundary):
    def __init__(self, *args, raw=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.raw = raw

    def _enter_provider(self, prepared, client):
        state = self.store.load()
        assert prepared.phase == "generation" and prepared.timeout_seconds == 12
        assert state["provider_budget_reservations"][f"{prepared.case_id}:generation"]["lifecycle"]["status"] == "consumed"
        self.calls += 1
        if self.fail:
            raise self.fail
        return self.raw


def execute(tmp_path, raw):
    store, _ = generation_ready(tmp_path)
    boundary = GenerationBoundary(store, {CREDENTIAL: FAKE}, raw=raw)
    boundary.execute_generation()
    return store, boundary


def test_valid_generation_is_bounded_and_awaits_milestone_10(tmp_path):
    store, boundary = execute(tmp_path, valid_synthetic_response("eval-v4-01"))
    state = store.load(); case_id = "eval-v4-01"
    result = state["generation_results"][case_id]
    evidence = state["generation_evidence"][case_id]
    assert result["result_schema"] == RESULT_SCHEMA and result["result_version"] == RESULT_VERSION
    assert evidence["evidence_schema"] == EVIDENCE_SCHEMA and evidence["evidence_version"] == EVIDENCE_VERSION
    assert result["immutable_binding"]["classification"] == "validated"
    assert result["result_sha256"] == RESULT_SHA256
    assert evidence["evidence_sha256"] == EVIDENCE_SHA256
    assert state["generation_phase_closures"][case_id]["closure_sha256"] == CLOSURE_SHA256
    assert evidence["immutable_binding"]["generation_evidence_review_status"] == "pending"
    assert state["cases"][case_id]["coordination_status"] == "awaiting_generation_evidence_review"
    assert state["next_case_id"] is None and boundary.calls == 1
    assert lifecycle_status(state, case_id) == "awaiting_generation_evidence_review"
    serialized = json.dumps(state)
    assert FAKE not in serialized and "Authorization" not in serialized


@pytest.mark.parametrize("variant,classification", [
    ("structural_failure", "structural_failure"),
    ("semantic_failure", "semantic_failure"),
    ("prose_failure", "prose_failure"),
])
def test_content_failures_are_distinct_use_exact_fallback_and_never_retain_raw(tmp_path, variant, classification):
    raw = synthetic_response("eval-v4-01", variant)
    store, boundary = execute(tmp_path, raw)
    binding = store.load()["generation_results"]["eval-v4-01"]["immutable_binding"]
    assert binding["classification"] == classification
    assert binding["fallback_selected"] is True
    assert binding["fallback_version"] == "moving-service-fallback-v2"
    assert boundary.calls == 1 and store.load()["counters"]["retries"] == 0
    assert json.dumps(raw, sort_keys=True) not in json.dumps(store.load(), sort_keys=True)
    if classification == "prose_failure":
        assert binding["ordered_prose_violation_codes"] and binding["bounded_rejected_prose_diagnostics"]
    else:
        assert binding["ordered_prose_violation_codes"] == []
        assert binding["bounded_rejected_prose_diagnostics"] == []


@pytest.mark.parametrize("failure,classification", [
    (TimeoutError("secret-free timeout"), "timeout"),
    (ConnectionError("secret-free transport"), "transport_error"),
    (RuntimeError("secret-free provider"), "provider_error"),
])
def test_provider_failures_are_bounded_consumed_and_never_retried(tmp_path, failure, classification):
    store, _ = generation_ready(tmp_path)
    boundary = GenerationBoundary(store, {CREDENTIAL: FAKE}, fail=failure)
    with pytest.raises(type(failure)):
        boundary.execute_generation()
    state = store.load(); binding = state["generation_results"]["eval-v4-01"]["immutable_binding"]
    assert binding["classification"] == classification and boundary.calls == 1
    assert state["counters"]["generations_consumed"] == 1 and state["counters"]["retries"] == 0
    assert "eval-v4-01" not in state["generation_evidence"]


def test_generation_requires_exact_approved_9a_gate(tmp_path):
    store, clock = prepared_store(tmp_path); store.record_provider_dispatch_started(); store.record_preflight_success(2852)
    with pytest.raises(AggregateStateError, match="reviewed preflight evidence"):
        store._prepare_generation_grant_from_reviewed_evidence()
    review(store, clock, "reject")
    with pytest.raises(AggregateStateError, match="reviewed preflight evidence"):
        store._prepare_generation_grant_from_reviewed_evidence()
    with pytest.raises(ExecutionBoundaryError):
        GenerationBoundary(store, {CREDENTIAL: FAKE}, raw={}).execute_generation()
    assert "eval-v4-01:generation" not in store.load()["provider_budget_reservations"]


def test_result_rerun_is_idempotent_and_conflict_is_rejected(tmp_path):
    raw = valid_synthetic_response("eval-v4-01")
    store, _ = execute(tmp_path, raw); state = store.load(); count = state["history_count"]
    from v4_formal_evaluation_live_generation_result import classify_generation
    outcome = classify_generation("eval-v4-01", raw)
    assert store.record_generation_outcome(outcome, case_id="eval-v4-01")["history_count"] == count
    with pytest.raises(AggregateStateError, match="conflicting generation result"):
        store.record_generation_outcome({
            "classification": "timeout", "validated_response": None,
            "ordered_prose_violation_codes": [], "bounded_rejected_prose_diagnostics": [],
            "fallback_selected": False, "fallback_version": None, "fallback_question_id": None,
        }, case_id="eval-v4-01")
    assert store.load()["history_count"] == count


def persist_generation_result_event(store, result, evidence, closure, operation="generation_result_validated"):
    before = store.load(); after = json.loads(canonical_json(before)); case_id = "eval-v4-01"
    after.setdefault("generation_results", {})
    after.setdefault("generation_evidence", {})
    after.setdefault("generation_phase_closures", {})
    after["generation_results"][case_id] = result
    if evidence is not None:
        after["generation_evidence"][case_id] = evidence
    after["generation_phase_closures"][case_id] = closure
    after["cases"][case_id]["coordination_status"] = "awaiting_generation_evidence_review" if evidence else "terminal"
    event = store._make_event(before, after, operation, {
        "case_id": case_id, "classification": result["immutable_binding"]["classification"],
        "result_sha256": result["result_sha256"],
        "evidence_sha256": evidence["evidence_sha256"] if evidence else None,
    })
    journal = store._read_journal(); journal["events"].append(event)
    _atomic_json(store.journal_path, journal); _atomic_json(store.snapshot_path, event["after_state"])
    return AggregateStore(store.root, store.clock)


def test_fully_rehashed_wrong_generation_dispatch_digest_is_rejected(tmp_path):
    from v4_formal_evaluation_live_generation_result import build_closure, build_evidence, build_result, classify_generation
    store, clock = generation_ready(tmp_path); store.record_provider_dispatch_started("generation")
    state = store.load(); case_id = "eval-v4-01"
    outcome = classify_generation(case_id, valid_synthetic_response(case_id))
    result = build_result(case_id, state["ai_case_envelopes"][case_id], state["generation_grants"][case_id],
                          state["provider_budget_reservations"][f"{case_id}:generation"], "0" * 64, outcome, clock.now)
    evidence = build_evidence(result, clock.now); closure = build_closure(result, evidence, clock.now)
    attacked = persist_generation_result_event(store, result, evidence, closure)
    with pytest.raises(AggregateStateError, match="actual retained provider dispatch event"):
        attacked.load()


@pytest.mark.parametrize("field", [
    "case_envelope_sha256", "generation_grant_sha256", "generation_reservation_sha256",
    "deterministic_request_sha256", "canonical_attempt_sha256", "provider_fingerprint",
])
def test_fully_rehashed_generation_binding_attacks_are_rejected(tmp_path, field):
    from v4_formal_evaluation_live_generation_result import build_closure, build_evidence, build_result, classify_generation
    store, clock = generation_ready(tmp_path); store.record_provider_dispatch_started("generation")
    state = store.load(); case_id = "eval-v4-01"
    result = build_result(
        case_id, state["ai_case_envelopes"][case_id], state["generation_grants"][case_id],
        state["provider_budget_reservations"][f"{case_id}:generation"], state["history_head_sha256"],
        classify_generation(case_id, valid_synthetic_response(case_id)), clock.now,
    )
    result["immutable_binding"][field] = "0" * 64
    result["result_sha256"] = digest({key: value for key, value in result.items() if key != "result_sha256"})
    evidence = build_evidence(result, clock.now); closure = build_closure(result, evidence, clock.now)
    attacked = persist_generation_result_event(store, result, evidence, closure)
    with pytest.raises(AggregateStateError, match="canonical validation binding"):
        attacked.load()


def test_fully_rehashed_evidence_drift_and_missing_dispatch_are_rejected(tmp_path):
    from v4_formal_evaluation_live_generation_result import build_closure, build_evidence, build_result, classify_generation
    store, clock = generation_ready(tmp_path); store.record_provider_dispatch_started("generation")
    state = store.load(); case_id = "eval-v4-01"
    result = build_result(
        case_id, state["ai_case_envelopes"][case_id], state["generation_grants"][case_id],
        state["provider_budget_reservations"][f"{case_id}:generation"], state["history_head_sha256"],
        classify_generation(case_id, valid_synthetic_response(case_id)), clock.now,
    )
    evidence = build_evidence(result, clock.now)
    evidence["immutable_binding"]["validated_response"]["warnings"] = ["forged"]
    evidence["evidence_sha256"] = digest({key: value for key, value in evidence.items() if key != "evidence_sha256"})
    closure = build_closure(result, evidence, clock.now)
    attacked = persist_generation_result_event(store, result, evidence, closure)
    with pytest.raises(AggregateStateError, match="evidence does not match"):
        attacked.load()

    undisbursed, clock2 = generation_ready(tmp_path / "missing-dispatch")
    state = undisbursed.load()
    result = build_result(
        case_id, state["ai_case_envelopes"][case_id], state["generation_grants"][case_id],
        state["provider_budget_reservations"][f"{case_id}:generation"], state["history_head_sha256"],
        classify_generation(case_id, valid_synthetic_response(case_id)), clock2.now,
    )
    evidence = build_evidence(result, clock2.now); closure = build_closure(result, evidence, clock2.now)
    attacked = persist_generation_result_event(undisbursed, result, evidence, closure)
    with pytest.raises(AggregateStateError, match="consumed dispatch|actual retained provider dispatch"):
        attacked.load()


@pytest.mark.parametrize("mutation", [
    "unknown_code", "wrong_rule", "wrong_field", "negative_offset", "excessive_offset",
    "negative_count", "excessive_count", "short_span", "oversized_trigger", "wrong_order",
])
def test_fully_rehashed_noncanonical_prose_diagnostics_are_rejected(tmp_path, mutation):
    from app.moving_service_questions import MAXIMUM_RESPONSE_CHARACTERS
    from v4_formal_evaluation_live_generation_result import build_closure, build_result, classify_generation
    store, clock = generation_ready(tmp_path); store.record_provider_dispatch_started("generation")
    state = store.load(); case_id = "eval-v4-01"
    outcome = deepcopy(classify_generation(case_id, synthetic_response(case_id, "prose_failure")))
    diagnostic = outcome["bounded_rejected_prose_diagnostics"][0]
    if mutation == "unknown_code":
        outcome["ordered_prose_violation_codes"][0] = "not-a-frozen-code"
        diagnostic["violation_code"] = "not-a-frozen-code"
    elif mutation == "wrong_rule":
        diagnostic["rule_id"] = "not-the-frozen-rule"
    elif mutation == "wrong_field":
        diagnostic["field"] = "arbitrary_provider_text"
    elif mutation == "negative_offset":
        diagnostic["start_offset"] = -1
    elif mutation == "negative_count":
        diagnostic["occurrence_count"] = -1
    elif mutation == "excessive_offset":
        diagnostic["end_offset"] = MAXIMUM_RESPONSE_CHARACTERS + 1
    elif mutation == "excessive_count":
        diagnostic["occurrence_count"] = MAXIMUM_RESPONSE_CHARACTERS + 1
    elif mutation == "short_span":
        diagnostic["end_offset"] = diagnostic["start_offset"] + 1
    elif mutation == "oversized_trigger":
        diagnostic["canonical_trigger"] = "x" * (MAXIMUM_RESPONSE_CHARACTERS + 1)
    else:
        outcome["bounded_rejected_prose_diagnostics"].reverse()
    result = build_result(
        case_id, state["ai_case_envelopes"][case_id], state["generation_grants"][case_id],
        state["provider_budget_reservations"][f"{case_id}:generation"],
        state["history_head_sha256"], outcome, clock.now,
    )
    attacked = persist_generation_result_event(store, result, None, build_closure(result, None, clock.now),
                                               operation="generation_validation_failed")
    with pytest.raises(AggregateStateError, match="prose failure"):
        attacked.load()


def test_canonical_prose_diagnostics_replay_exactly(tmp_path):
    store, boundary = execute(tmp_path, synthetic_response("eval-v4-01", "prose_failure"))
    expected = store.load()["generation_results"]["eval-v4-01"]
    replayed = AggregateStore(store.root, store.clock).load()["generation_results"]["eval-v4-01"]
    assert replayed == expected and boundary.calls == 1


def test_retained_generation_result_cannot_be_deleted_or_reclassified(tmp_path):
    store, _ = execute(tmp_path, valid_synthetic_response("eval-v4-01"))
    class AttackStore(AggregateStore):
        ATTACK = "_synthetic_m9b_semantic_attack"
        def _validate_operation_semantics(self, event, previous_time):
            if event["operation"] != self.ATTACK:
                return super()._validate_operation_semantics(event, previous_time)
            self._validate_retained_generation_history(event["before_state"], event["after_state"])
            self._validate_state(event["after_state"])
    attacking = AttackStore(store.root, store.clock)
    before = attacking.load(); after = json.loads(canonical_json(before))
    after["generation_results"].pop("eval-v4-01")
    event = attacking._make_event(before, after, AttackStore.ATTACK, {"test_only": True})
    journal = attacking._read_journal(); journal["events"].append(event)
    _atomic_json(attacking.journal_path, journal); _atomic_json(attacking.snapshot_path, event["after_state"])
    with pytest.raises(AggregateStateError, match="retained generation_results"):
        attacking.load()


def test_crash_before_result_is_recovery_required_and_after_history_replays(tmp_path):
    store, _ = generation_ready(tmp_path); store.record_provider_dispatch_started("generation")
    assert lifecycle_status(store.load(), "eval-v4-01") == "dispatch_consumed_result_missing"
    before = store.load()["history_count"]
    assert store.record_provider_dispatch_started("generation")["history_count"] == before

    def fail(point):
        if point == "after_history_replace":
            raise RuntimeError("projection interrupted")
    failing = AggregateStore(store.root, store.clock, fail)
    from v4_formal_evaluation_live_generation_result import classify_generation
    with pytest.raises(RuntimeError, match="projection interrupted"):
        failing.record_generation_outcome(classify_generation("eval-v4-01", valid_synthetic_response("eval-v4-01")), case_id="eval-v4-01")
    recovered = AggregateStore(store.root, store.clock).load()
    assert recovered["generation_phase_closures"]["eval-v4-01"]["immutable_binding"]["status"] == "awaiting_generation_evidence_review"
    assert recovered["counters"]["retries"] == 0


def test_public_surface_and_provider_counts_remain_bounded():
    assert len(PUBLIC_COMMANDS) == 10
    assert not any("result" in command or "dispatch" in command for command in PUBLIC_COMMANDS)
    assert CONTENT_FAILURES == ("structural_failure", "semantic_failure", "prose_failure")
    assert PROVIDER_FAILURES == ("timeout", "transport_error", "provider_error", "outcome_unknown")


def test_actual_fixed_generation_launcher_reaches_real_9b_handler(tmp_path):
    if shutil.which("zsh") is None:
        pytest.skip("zsh is required for the fixed generation-launcher rehearsal")
    from test_v4_formal_evaluation_live_execution import _actual_launcher_environment, _prepared_real_time_store
    from v4_formal_evaluation_live_state import parse_time
    store = _prepared_real_time_store(tmp_path / "state")
    store.record_provider_dispatch_started(); state = store.record_preflight_success(2852)
    reviewed_at = parse_time(
        state["preflight_evidence"]["eval-v4-01"]["immutable_binding"]["evidence_created_at"])
    store.review_preflight_evidence(
        reviewer="Reviewer", decision="approve", reviewed_at=reviewed_at,
        token_count_plausible=True, cost_within_limit=True,
        frozen_bindings_confirmed=True, evidence_history_confirmed=True,
        notes="Exact frozen-v4 preflight evidence reviewed.",
    )
    store._prepare_generation_grant_from_reviewed_evidence(); store._authorize_generation_budget()
    environment = _actual_launcher_environment(tmp_path / "launcher", store)
    environment[CREDENTIAL] = FAKE
    launcher = Path(__file__).with_name("run_v4_formal_evaluation_live_generation_operator.zsh")
    completed = subprocess.run(
        ["zsh", str(launcher)], cwd=Path(__file__).parents[3], env=environment,
        text=True, capture_output=True, timeout=30,
    )
    assert completed.returncode == 0, completed.stderr
    assert FAKE not in completed.stdout + completed.stderr
    state = AggregateStore(store.root).load()
    assert state["generation_results"]["eval-v4-01"]["immutable_binding"]["classification"] == "validated"
    assert state["generation_phase_closures"]["eval-v4-01"]["immutable_binding"]["status"] == "awaiting_generation_evidence_review"
    assert (tmp_path / "launcher" / "provider-marker.txt").read_text() == "synthetic-entry=1\n"
    assert FAKE not in json.dumps(state) + json.dumps(store._read_journal())
