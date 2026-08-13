from __future__ import annotations

import json
import os
import stat
import subprocess
import textwrap
from datetime import timedelta
from pathlib import Path

import pytest

from test_v4_formal_evaluation_live_execution import CREDENTIAL, FAKE, SyntheticBoundary, prepared_store
from v4_formal_evaluation_live_cli import PUBLIC_COMMANDS
from v4_formal_evaluation_live_preflight_result import (
    EVIDENCE_SCHEMA, EVIDENCE_VERSION, FAILURE_CLASSIFICATIONS,
    RESULT_SCHEMA, RESULT_VERSION, REVIEW_DECISIONS, REVIEW_LIFETIME,
    PreflightResultError, build_closure, build_evidence, build_validated_result,
    lifecycle_status,
)
from v4_formal_evaluation_live_state import AggregateStateError, AggregateStore
from v4_formal_evaluation_live_state import _atomic_json, canonical_json

RESULT_SHA256 = "f201e07af862bcdfcdfba8d7baeb544d3ff4b6045d49fd140e66a15dbdf7bcac"
EVIDENCE_SHA256 = "449b336abd271eff6697df20828fb8254a569c28993411098f2aee1be535c1af"
REVIEW_SHA256 = "aa39e8d302a6cba5f79a83847b865ccbdb585cd03fff6b0d5ccf4995f0158004"


def consumed_store(tmp_path):
    store, clock = prepared_store(tmp_path)
    store.record_provider_dispatch_started()
    return store, clock


def review(store, clock, decision="approve", **changes):
    values = dict(
        reviewer="Reviewer", decision=decision, reviewed_at=clock.now,
        token_count_plausible=True, cost_within_limit=True,
        frozen_bindings_confirmed=True, evidence_history_confirmed=True,
        notes="Exact frozen-v4 preflight evidence reviewed.",
    )
    values.update(changes)
    return store.review_preflight_evidence(**values)


def test_case01_valid_result_creates_bounded_review_pending_evidence(tmp_path):
    store, clock = consumed_store(tmp_path)
    state = store.record_preflight_success(2852)
    result = state["preflight_results"]["eval-v4-01"]
    evidence = state["preflight_evidence"]["eval-v4-01"]
    assert result["result_schema"] == RESULT_SCHEMA and result["result_version"] == RESULT_VERSION
    assert evidence["evidence_schema"] == EVIDENCE_SCHEMA and evidence["evidence_version"] == EVIDENCE_VERSION
    assert result["immutable_binding"]["input_tokens"] == 2852
    assert result["result_sha256"] == RESULT_SHA256
    assert evidence["evidence_sha256"] == EVIDENCE_SHA256
    assert evidence["immutable_binding"]["conservative_generation_exposure_usd"] == "0.0019408"
    assert lifecycle_status(state, "eval-v4-01") == "review_pending"
    assert state["reviewed_preflight_evidence"] == {}
    serialized = json.dumps({"result": result, "evidence": evidence})
    for prohibited in (FAKE, "Authorization", "prompt_text", "request_body", "environment", "headers"):
        assert prohibited not in serialized
    assert clock.now + REVIEW_LIFETIME == __import__(
        "v4_formal_evaluation_live_state").parse_time(evidence["immutable_binding"]["review_deadline"])


def test_approval_is_distinct_human_transition_and_enables_generation_preparation(tmp_path):
    store, clock = consumed_store(tmp_path); store.record_preflight_success(2852)
    before = store.load(); assert before["reviewed_preflight_evidence"] == {}
    state = review(store, clock)
    binding = state["preflight_reviews"]["eval-v4-01"]["immutable_binding"]
    assert binding["decision"] == "approve" and binding["generation_gate_binding_eligible"] is True
    assert state["preflight_reviews"]["eval-v4-01"]["review_sha256"] == REVIEW_SHA256
    assert set(key for key in binding if key.endswith("confirmed") or key.endswith("plausible") or key == "cost_within_limit") >= {
        "token_count_plausible", "cost_within_limit", "frozen_bindings_confirmed", "evidence_history_confirmed"
    }
    prepared = store._prepare_generation_grant_from_reviewed_evidence()
    assert "eval-v4-01" in prepared["generation_grants"]
    assert prepared["counters"]["generations_consumed"] == 0
    assert not any(event["metadata"].get("phase") == "generation" and event["operation"] == "provider_dispatch_started" for event in store._read_journal()["events"])


@pytest.mark.parametrize("decision", ("reject", "request_changes"))
def test_nonapproval_is_terminal_immutable_and_never_generation_eligible(tmp_path, decision):
    store, clock = consumed_store(tmp_path); store.record_preflight_success(2852)
    state = review(store, clock, decision)
    assert state["preflight_reviews"]["eval-v4-01"]["immutable_binding"]["decision"] == decision
    assert state["reviewed_preflight_evidence"] == {}
    with pytest.raises(AggregateStateError, match="fail-closed without reviewed preflight evidence"):
        store._prepare_generation_grant_from_reviewed_evidence()
    with pytest.raises(AggregateStateError, match="conflicting preflight evidence review"):
        review(store, clock, "approve")


def test_review_contract_identity_confirmations_notes_and_deadline(tmp_path):
    store, clock = consumed_store(tmp_path); store.record_preflight_success(2852)
    with pytest.raises(AggregateStateError, match="reviewer must match"):
        review(store, clock, reviewer="Other Reviewer")
    with pytest.raises(PreflightResultError, match="every confirmation"):
        review(store, clock, frozen_bindings_confirmed=False)
    with pytest.raises(PreflightResultError, match="notes"):
        review(store, clock, notes="")
    evidence = store.load()["preflight_evidence"]["eval-v4-01"]
    deadline = __import__("v4_formal_evaluation_live_state").parse_time(
        evidence["immutable_binding"]["review_deadline"])
    clock.now = deadline
    with pytest.raises(PreflightResultError, match="approval is late"):
        review(store, clock, reviewed_at=deadline)
    assert REVIEW_DECISIONS == ("approve", "reject", "request_changes")


@pytest.mark.parametrize("classification", FAILURE_CLASSIFICATIONS)
def test_provider_failure_is_bounded_consumed_and_not_reviewable(tmp_path, classification):
    store, _ = consumed_store(tmp_path)
    state = store.record_preflight_failure(classification)
    assert state["preflight_results"]["eval-v4-01"]["immutable_binding"]["classification"] == classification
    assert "eval-v4-01" not in state["preflight_evidence"]
    assert state["counters"]["token_preflights_consumed"] == 1
    assert state["counters"]["retries"] == 0
    assert state["reviewed_preflight_evidence"] == {}
    with pytest.raises(AggregateStateError, match="no reviewable"):
        review(store, type("C", (), {"now": store.clock()})())


def test_result_and_review_exact_reruns_are_event_free_conflicts_fail_closed(tmp_path):
    store, clock = consumed_store(tmp_path)
    first = store.record_preflight_success(2852); count = first["history_count"]
    assert store.record_preflight_success(2852)["history_count"] == count
    with pytest.raises(AggregateStateError, match="conflicting preflight result"):
        store.record_preflight_failure("timeout")
    approved = review(store, clock); count = approved["history_count"]
    assert review(store, clock)["history_count"] == count
    with pytest.raises(AggregateStateError, match="conflicting preflight evidence review"):
        review(store, clock, decision="reject")
    assert store.load()["history_count"] == count


def test_dispatch_consumed_result_missing_is_recovery_required_and_never_retried(tmp_path):
    store, _ = consumed_store(tmp_path); state = store.load()
    assert lifecycle_status(state, "eval-v4-01") == "dispatch_consumed_result_missing"
    assert state["counters"]["token_preflights_consumed"] == 1
    assert state["counters"]["retries"] == 0
    before = state["history_count"]
    assert store.record_provider_dispatch_started()["history_count"] == before


def test_history_first_crash_recovers_exact_result_and_review(tmp_path):
    store, clock = consumed_store(tmp_path)
    def fail(point):
        if point == "after_history_replace": raise RuntimeError("projection interrupted")
    failing = AggregateStore(store.root, store.clock, fail)
    with pytest.raises(RuntimeError, match="projection interrupted"):
        failing.record_preflight_success(2852)
    recovered = AggregateStore(store.root, store.clock)
    assert recovered.load()["preflight_evidence"]["eval-v4-01"]["immutable_binding"]["input_tokens"] == 2852
    failing = AggregateStore(store.root, store.clock, fail)
    with pytest.raises(RuntimeError, match="projection interrupted"):
        review(failing, clock)
    final = AggregateStore(store.root, store.clock).load()
    assert final["reviewed_preflight_evidence"]["eval-v4-01"]["immutable_binding"]["generation_gate_binding_eligible"] is True


def test_actual_execution_boundary_records_result_and_failures_once(tmp_path):
    store, _ = prepared_store(tmp_path); boundary = SyntheticBoundary(store, {CREDENTIAL: FAKE})
    assert boundary.execute_preflight() == {"input_tokens": 2852}
    assert boundary.calls == 1 and "eval-v4-01" in store.load()["preflight_evidence"]
    store2, _ = prepared_store(tmp_path / "timeout")
    timed = SyntheticBoundary(store2, {CREDENTIAL: FAKE}, fail=TimeoutError("never persisted"))
    with pytest.raises(TimeoutError): timed.execute_preflight()
    assert timed.calls == 1
    assert store2.load()["preflight_results"]["eval-v4-01"]["immutable_binding"]["classification"] == "timeout"
    assert "never persisted" not in json.dumps(store2.load())
    store3, _ = prepared_store(tmp_path / "invalid")
    class Invalid(SyntheticBoundary):
        def _enter_provider(self, prepared, client):
            self.calls += 1
            return {"input_tokens": -1}
    invalid = Invalid(store3, {CREDENTIAL: FAKE})
    with pytest.raises(Exception, match="token-count result is invalid"):
        invalid.execute_preflight()
    assert invalid.calls == 1
    assert store3.load()["preflight_results"]["eval-v4-01"]["immutable_binding"]["classification"] == "invalid_result"


def test_public_coordination_inventory_and_m7_synthetic_operation_remain_isolated():
    assert len(PUBLIC_COMMANDS) == 10 and not any("review" in command for command in PUBLIC_COMMANDS)
    assert "_synthetic_m7_reviewed_preflight_evidence" not in __import__(
        "v4_formal_evaluation_live_state").AggregateStore.__dict__


class AttackStore(AggregateStore):
    ATTACK = "_synthetic_m9a_semantic_attack"
    def _validate_operation_semantics(self, event, previous_time):
        if event["operation"] != self.ATTACK:
            return super()._validate_operation_semantics(event, previous_time)
        self._validate_retained_generation_history(event["before_state"], event["after_state"])
        self._validate_state(event["after_state"])


def persist_attack(store, mutate):
    attacking = AttackStore(store.root, store.clock)
    before = attacking.load(); after = json.loads(canonical_json(before)); mutate(after)
    event = attacking._make_event(before, after, AttackStore.ATTACK, {"test_only": True})
    journal = attacking._read_journal(); journal["events"].append(event)
    _atomic_json(attacking.journal_path, journal); _atomic_json(attacking.snapshot_path, event["after_state"])
    return attacking


def persist_preflight_result_event(store, result, evidence, closure):
    before = store.load(); after = json.loads(canonical_json(before)); case_id = "eval-v4-01"
    after["preflight_results"][case_id] = result
    if evidence is not None:
        after["preflight_evidence"][case_id] = evidence
    after["preflight_phase_closures"][case_id] = closure
    event = store._make_event(before, after, "preflight_result_validated", {
        "case_id": case_id, "classification": "validated",
        "result_sha256": result["result_sha256"],
        "evidence_sha256": evidence["evidence_sha256"] if evidence else None,
    })
    journal = store._read_journal(); journal["events"].append(event)
    _atomic_json(store.journal_path, journal); _atomic_json(store.snapshot_path, event["after_state"])
    return AggregateStore(store.root, store.clock)


def test_rehashed_validated_result_without_evidence_is_rejected(tmp_path):
    store, clock = consumed_store(tmp_path); state = store.load(); case_id = "eval-v4-01"
    result = build_validated_result(
        case_id, state["ai_case_envelopes"][case_id], state["preflight_grants"][case_id],
        state["provider_budget_reservations"][case_id], state["history_head_sha256"], 2852,
        clock.now,
    )
    closure = build_closure(case_id, result, None, None, clock.now)
    attacked = persist_preflight_result_event(store, result, None, closure)
    with pytest.raises(AggregateStateError, match="result and exact evidence must be recorded atomically"):
        attacked.load()


def test_rehashed_result_evidence_with_wrong_dispatch_digest_is_rejected(tmp_path):
    store, clock = consumed_store(tmp_path); state = store.load(); case_id = "eval-v4-01"
    result = build_validated_result(
        case_id, state["ai_case_envelopes"][case_id], state["preflight_grants"][case_id],
        state["provider_budget_reservations"][case_id], "0" * 64, 2852, clock.now,
    )
    evidence = build_evidence(result, state["ai_case_envelopes"][case_id], clock.now)
    closure = build_closure(case_id, result, evidence, None, clock.now)
    attacked = persist_preflight_result_event(store, result, evidence, closure)
    with pytest.raises(AggregateStateError, match="actual retained provider dispatch event"):
        attacked.load()


def test_fully_rehashed_binding_and_eligibility_attacks_fail_semantically(tmp_path):
    store, clock = consumed_store(tmp_path); store.record_preflight_success(2852); review(store, clock)
    def wrong_result(after):
        result = after["preflight_results"]["eval-v4-01"]
        result["immutable_binding"]["provider_fingerprint"] = "0" * 64
        unsigned = {key: value for key, value in result.items() if key != "result_sha256"}
        result["result_sha256"] = __import__("v4_formal_evaluation_live_models").digest(unsigned)
    attacked = persist_attack(store, wrong_result)
    with pytest.raises(AggregateStateError, match="retained preflight_results history"):
        attacked.load()

    store2, _ = consumed_store(tmp_path / "no-review"); store2.record_preflight_success(2852)
    def forge_eligibility(after):
        after["reviewed_preflight_evidence"]["eval-v4-01"] = {
            "evidence_schema": "forged", "evidence_version": 1,
            "evidence_binding_sha256": "0" * 64, "immutable_binding": {},
        }
    attacked = persist_attack(store2, forge_eligibility)
    with pytest.raises(AggregateStateError, match="requires exact approved preflight review"):
        attacked.load()


def test_retained_review_cannot_be_deleted_by_later_rehashed_transition(tmp_path):
    store, clock = consumed_store(tmp_path); store.record_preflight_success(2852); review(store, clock)
    def remove_review(after):
        after["preflight_reviews"].pop("eval-v4-01")
    attacked = persist_attack(store, remove_review)
    with pytest.raises(AggregateStateError, match="retained preflight_reviews history"):
        attacked.load()


def test_fixed_human_review_docker_action_uses_authoritative_current_evidence(tmp_path):
    from test_v4_formal_evaluation_live_execution import _prepared_real_time_store
    store = _prepared_real_time_store(tmp_path / "state")
    store.record_provider_dispatch_started(); state = store.record_preflight_success(2852)
    reviewed_at = state["preflight_evidence"]["eval-v4-01"]["immutable_binding"]["evidence_created_at"]
    fake_bin = tmp_path / "bin"; fake_bin.mkdir(); fake_docker = fake_bin / "docker"
    fake_docker.write_text(textwrap.dedent("""\
        #!/usr/bin/env python3
        import os, subprocess, sys
        args=sys.argv[1:]; image="gotime-moving-service-stage-b:openai-2.45.0"
        if image not in args: raise SystemExit(91)
        command=args[args.index(image)+1:]
        if command[0] != "python": raise SystemExit(92)
        command[0]=sys.executable
        command[1]=command[1].replace("/workspace", os.environ["M9A_REPO"])
        environment=dict(os.environ)
        environment["PYTHONPATH"]=os.environ["M9A_HOOK"]+os.pathsep+environment.get("PYTHONPATH", "")
        raise SystemExit(subprocess.run(command, cwd=os.environ["M9A_REPO"], env=environment).returncode)
    """)); fake_docker.chmod(fake_docker.stat().st_mode | stat.S_IXUSR)
    hook = tmp_path / "hook"; hook.mkdir()
    (hook / "sitecustomize.py").write_text(textwrap.dedent("""\
        import os
        from pathlib import Path
        import v4_formal_evaluation_live_state as state
        state.default_root=lambda: Path(os.environ["M9A_STATE"])
    """))
    repo = Path(__file__).parents[3]
    environment = dict(os.environ, PATH=f"{fake_bin}:{os.environ['PATH']}",
                       M9A_REPO=str(repo), M9A_HOOK=str(hook), M9A_STATE=str(store.root))
    command = ["sh", str(Path(__file__).with_name(
        "review_v4_formal_evaluation_live_preflight_evidence_docker.sh")),
        "--reviewer", "Reviewer", "--decision", "approve", "--reviewed-at", reviewed_at,
        "--token-count-plausible", "true", "--cost-within-limit", "true",
        "--frozen-bindings-confirmed", "true", "--evidence-history-confirmed", "true",
        "--notes", "Exact frozen-v4 preflight evidence reviewed."]
    completed = subprocess.run(command, cwd=repo, env=environment, text=True, capture_output=True)
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)["generation_gate_binding_eligible"] is True
    assert AggregateStore(store.root).load()["preflight_reviews"]["eval-v4-01"]["review_sha256"]
