from __future__ import annotations

import ast
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from v4_formal_evaluation_live_budget import (
    BudgetError, build_generation_reservation, build_preflight_reservation,
    derive_budget_accounting, enforce_generation_capacity, reservation_identity,
)
from v4_formal_evaluation_live_deterministic import resolve_deterministic_cases
from v4_formal_evaluation_live_generation import (
    GENERATION_GRANT_LIFETIME, GENERATION_GRANT_SCHEMA, GENERATION_GRANT_VERSION,
    GenerationGrantError, active_generation_lifecycle,
    build_generation_grant, build_reviewed_preflight_evidence,
    conservative_generation_exposure, consumed_generation_lifecycle,
    frozen_maximum_output_tokens, generation_grant_is_expired,
    validate_generation_grant,
)
from v4_formal_evaluation_live_grants import (
    budget_authorized_lifecycle, build_preflight_grant,
    dispatch_started_lifecycle,
)
from v4_formal_evaluation_live_models import AI_CASE_ORDER, MAX_GENERATIONS
from v4_formal_evaluation_live_models import digest
from v4_formal_evaluation_live_state import (
    AggregateStateError, AggregateStore, _atomic_json, _event_digest, _lock,
    canonical_json, derive_next_case, format_time, parse_time,
)

GRANT_SHA256 = "b8eeaa9ed4fa16037cb2fa6e0ce2588cebe75ec3152e6676e9dc249b3f3c95f8"
RESERVATION_SHA256 = "80cea3386b18852029fa814d2022e7642b9cd4e978abf8695d04d148fadfae49"


class Clock:
    def __init__(self): self.now = datetime(2026, 8, 11, 12, tzinfo=timezone.utc)
    def __call__(self): return self.now


class GenerationHarnessStore(AggregateStore):
    """Test-only evidence/case progression; production replay rejects both operations."""

    EVIDENCE = "_synthetic_m7_reviewed_preflight_evidence"
    ADVANCE = "_synthetic_m7_case_advanced"
    CONSUME = "_synthetic_m7_generation_consumed"

    def _validate_operation_semantics(self, event, previous_time):
        if event["operation"] not in {self.EVIDENCE, self.ADVANCE, self.CONSUME}:
            return super()._validate_operation_semantics(event, previous_time)
        before, after, metadata = event["before_state"], event["after_state"], event["metadata"]
        case_id = metadata.get("case_id") if isinstance(metadata, dict) else None
        expected = json.loads(canonical_json(before))
        if event["operation"] == self.EVIDENCE:
            if set(metadata) != {"case_id", "test_only", "evidence_binding_sha256"} or metadata["test_only"] is not True:
                raise AggregateStateError("synthetic generation evidence operation is invalid")
            evidence = after["reviewed_preflight_evidence"].get(case_id)
            if evidence is None or metadata["evidence_binding_sha256"] != evidence["evidence_binding_sha256"]:
                raise AggregateStateError("synthetic generation evidence identity mismatch")
            expected["reviewed_preflight_evidence"][case_id] = evidence
        elif event["operation"] == self.ADVANCE:
            if set(metadata) != {"case_id", "test_only"} or metadata["test_only"] is not True:
                raise AggregateStateError("synthetic generation advance is invalid")
            expected["cases"][case_id]["coordination_status"] = "terminal"
            expected["next_case_id"] = derive_next_case(expected)
        else:
            if set(metadata) != {"case_id", "test_only", "reservation_sha256"} or metadata["test_only"] is not True:
                raise AggregateStateError("synthetic generation consumption operation is invalid")
            key = f"{case_id}:generation"
            reservation = expected["provider_budget_reservations"].get(key)
            if reservation is None or metadata["reservation_sha256"] != reservation["reservation_sha256"]:
                raise AggregateStateError("synthetic generation consumption identity mismatch")
            amount = reservation["immutable_binding"]["reservation_amount_usd"]
            reservation["lifecycle"].update(
                status="consumed", provider_dispatch_status="started",
                attempt_consumed=True, consumed_amount_usd=amount,
                consumed_operation_count=1, dispatch_started_at=event["occurred_at"],
            )
            expected["generation_grants"][case_id]["lifecycle"] = consumed_generation_lifecycle()
            self._set_derived_budget(expected)
        expected["history_count"] = after["history_count"]
        expected["history_head_sha256"] = after["history_head_sha256"]
        if after != expected:
            raise AggregateStateError("synthetic Milestone 7 operation mutated prohibited state")
        self._validate_state(after)

    def inject_reviewed_evidence(self, *, input_tokens=2852):
        with _lock(self.root):
            state = self._load_unlocked(True, True); case_id = state["next_case_id"]
            evidence = build_reviewed_preflight_evidence(
                case_id, state["ai_case_envelopes"][case_id], input_tokens=input_tokens,
                evidence_sha256=digest({"synthetic_m7_evidence": case_id}),
                review_sha256=digest({"synthetic_m7_review": case_id}),
            )
            after = json.loads(canonical_json(state)); after["reviewed_preflight_evidence"][case_id] = evidence
            event = self._make_event(state, after, self.EVIDENCE, {
                "case_id": case_id, "test_only": True,
                "evidence_binding_sha256": evidence["evidence_binding_sha256"],
            })
            journal = self._read_journal(); journal["events"].append(event)
            canonical = self._validate_journal(journal)[-1]; self._commit(journal, canonical)
            return canonical

    def advance(self):
        with _lock(self.root):
            state = self._load_unlocked(True, True); case_id = state["next_case_id"]
            after = json.loads(canonical_json(state)); after["cases"][case_id]["coordination_status"] = "terminal"
            after["next_case_id"] = derive_next_case(after)
            event = self._make_event(state, after, self.ADVANCE, {"case_id": case_id, "test_only": True})
            journal = self._read_journal(); journal["events"].append(event)
            canonical = self._validate_journal(journal)[-1]; self._commit(journal, canonical)
            return canonical

    def consume_generation(self, case_id=None):
        """Represent future consumed retention without a production transition."""
        with _lock(self.root):
            state = self._load_unlocked(True, True); case_id = case_id or state["next_case_id"]
            key = f"{case_id}:generation"; reservation = state["provider_budget_reservations"][key]
            after = json.loads(canonical_json(state)); amount = reservation["immutable_binding"]["reservation_amount_usd"]
            after["provider_budget_reservations"][key]["lifecycle"].update(
                status="consumed", provider_dispatch_status="started", attempt_consumed=True,
                consumed_amount_usd=amount, consumed_operation_count=1,
                dispatch_started_at=self.clock().isoformat().replace("+00:00", "Z"),
            )
            after["generation_grants"][case_id]["lifecycle"] = consumed_generation_lifecycle()
            self._set_derived_budget(after)
            event = self._make_event(state, after, self.CONSUME, {
                "case_id": case_id, "test_only": True,
                "reservation_sha256": reservation["reservation_sha256"],
            })
            journal = self._read_journal(); journal["events"].append(event)
            canonical = self._validate_journal(journal)[-1]; self._commit(journal, canonical)
            return canonical


class SemanticAttackStore(GenerationHarnessStore):
    """Rehashes malicious projections while applying production state validators."""

    ATTACK = "_synthetic_m7_semantic_attack"

    def _validate_operation_semantics(self, event, previous_time):
        if event["operation"] != self.ATTACK:
            return super()._validate_operation_semantics(event, previous_time)
        if event["metadata"] != {"test_only": True}:
            raise AggregateStateError("semantic attack metadata is invalid")
        self._validate_state(event["after_state"])


class RetentionAttackStore(SemanticAttackStore):
    def _validate_operation_semantics(self, event, previous_time):
        if event["operation"] != self.ATTACK:
            return super()._validate_operation_semantics(event, previous_time)
        if event["metadata"] != {"test_only": True}:
            raise AggregateStateError("semantic attack metadata is invalid")
        self._validate_retained_generation_history(event["before_state"], event["after_state"])
        self._validate_consumed_preflight_identity_retention(
            event["before_state"], event["after_state"])
        self._validate_state(event["after_state"])


class ConflictingGrantStore(GenerationHarnessStore):
    def _build_generation_grant_candidate(self, case_id, envelope, evidence, activated_at):
        return super()._build_generation_grant_candidate(
            case_id, envelope, evidence, activated_at + timedelta(seconds=1))


class ConflictingReservationStore(GenerationHarnessStore):
    def _build_generation_reservation_candidate(self, grant, envelope, reserved_at):
        changed = format_time(parse_time(reserved_at) + timedelta(seconds=1))
        return super()._build_generation_reservation_candidate(grant, envelope, changed)


def assert_rehashed_state_attack(store, mutate, message, validator=SemanticAttackStore):
    """Persist a canonical malicious journal/projection and require semantic failure."""
    state = store.load(); after = json.loads(canonical_json(state)); mutate(after)
    event = store._make_event(state, after, SemanticAttackStore.ATTACK, {"test_only": True})
    journal = store._read_journal(); journal["events"].append(event)
    original_journal = store._read_journal(); original_projection = store.load()
    try:
        _atomic_json(store.journal_path, journal); _atomic_json(store.snapshot_path, event["after_state"])
        with pytest.raises(AggregateStateError, match=message):
            validator(store.root, store.clock).load(observe_expiry=False)
    finally:
        _atomic_json(store.journal_path, original_journal); _atomic_json(store.snapshot_path, original_projection)


def assert_rehashed_retention_attack(store, mutate, message):
    assert_rehashed_state_attack(store, mutate, message, RetentionAttackStore)


def assert_rehashed_last_event_metadata_attack(store, case_id, message):
    journal = json.loads(canonical_json(store._read_journal())); event = journal["events"][-1]
    event["metadata"]["case_id"] = case_id
    event["event_sha256"] = _event_digest(event)
    event["after_state"]["history_head_sha256"] = event["event_sha256"]
    original_journal = store._read_journal(); original_projection = store.load()
    try:
        _atomic_json(store.journal_path, journal); _atomic_json(store.snapshot_path, event["after_state"])
        with pytest.raises(AggregateStateError, match=message):
            GenerationHarnessStore(store.root, store.clock).load(observe_expiry=False)
    finally:
        _atomic_json(store.journal_path, original_journal); _atomic_json(store.snapshot_path, original_projection)


def ready(root, store_class=GenerationHarnessStore):
    clock = Clock(); store = store_class(root, clock)
    store.initialize("Operator", "Reviewer"); store.resume("Reviewer")
    resolve_deterministic_cases(store); store.bind_ai_case_envelopes()
    store.prepare_preflight_grant(); store.authorize_preflight_budget(); store.record_provider_dispatch_started()
    return store, clock


def generation_ready(root):
    store, clock = ready(root); store.inject_reviewed_evidence()
    store._prepare_generation_grant_from_reviewed_evidence()
    return store, clock


def test_case_01_cost_budget_grant_and_reservation(tmp_path):
    assert conservative_generation_exposure(2852) == "0.0019408"
    assert frozen_maximum_output_tokens() == 500
    synthetic = {"model_parameters": {"maximum_output_tokens": 600}}
    assert conservative_generation_exposure(2852, synthetic) == "0.0021008"
    source = Path(__file__).with_name("v4_formal_evaluation_live_generation.py").read_text()
    assert "MAXIMUM_OUTPUT_TOKENS = 500" not in source
    store, _ = generation_ready(tmp_path)
    prepared = store.load(); grant = prepared["generation_grants"]["eval-v4-01"]
    assert grant["grant_schema"] == GENERATION_GRANT_SCHEMA
    assert grant["grant_version"] == GENERATION_GRANT_VERSION
    assert grant["immutable_binding"]["phase"] == "generation"
    assert grant["immutable_binding"]["conservative_operation_ceiling_usd"] == "0.0019408"
    assert grant["immutable_binding"]["operation_count"] == 1
    assert grant["grant_sha256"] == GRANT_SHA256
    assert len(grant["grant_sha256"]) == 64
    assert grant["grant_sha256"] == grant["grant_sha256"].lower()
    int(grant["grant_sha256"], 16)
    count = prepared["history_count"]
    assert store._prepare_generation_grant_from_reviewed_evidence()["history_count"] == count
    active = store._authorize_generation_budget()
    reservation = active["provider_budget_reservations"]["eval-v4-01:generation"]
    assert reservation["immutable_binding"]["reservation_amount_usd"] == "0.0019408"
    assert reservation["immutable_binding"]["operation_count"] == 1
    assert reservation["reservation_sha256"] == RESERVATION_SHA256
    assert len(reservation["reservation_sha256"]) == 64
    assert reservation["reservation_sha256"] == reservation["reservation_sha256"].lower()
    int(reservation["reservation_sha256"], 16)
    assert active["generation_grants"]["eval-v4-01"]["lifecycle"] == active_generation_lifecycle()
    assert active["budget_accounting"]["cases"]["eval-v4-01"]["remaining_provider_capacity_usd"] == "0.0280592"
    assert active["budget_accounting"]["aggregate"]["remaining_provider_capacity_usd"] == "0.2380592"
    assert active["counters"]["token_preflights_consumed"] == 1
    assert active["counters"]["generations_reserved"] == 1
    assert active["counters"]["retries"] == 0
    assert store._authorize_generation_budget() == active


def test_evidence_is_mandatory_exact_and_production_inaccessible(tmp_path):
    store, _ = ready(tmp_path)
    before = store.load(); journal_before = store._read_journal()
    with pytest.raises(AggregateStateError, match="fail-closed"):
        store._prepare_generation_grant_from_reviewed_evidence()
    after = store.load(); journal_after = store._read_journal()
    assert after == before
    assert journal_after == journal_before
    assert after["generation_grants"] == {}
    assert not any(key.endswith(":generation") for key in after["provider_budget_reservations"])
    assert after["counters"]["generations_reserved"] == 0
    assert after["counters"]["generations_consumed"] == 0
    assert after["provider_authority"] is False
    assert not any(event["operation"].startswith("generation_") for event in journal_after["events"])
    assert AggregateStore(store.root, store.clock).load() == before
    state = store.inject_reviewed_evidence()
    evidence = state["reviewed_preflight_evidence"]["eval-v4-01"]
    bad = json.loads(canonical_json(evidence)); bad["immutable_binding"]["case_id"] = "eval-v4-02"
    with pytest.raises(GenerationGrantError, match="exact case binding"):
        build_generation_grant("eval-v4-01", state["ai_case_envelopes"]["eval-v4-01"], bad, store.clock())
    with pytest.raises(AggregateStateError, match="operation is unavailable"):
        AggregateStore(store.root, store.clock).load(observe_expiry=False)
    cli = Path(__file__).with_name("v4_formal_evaluation_live_cli.py").read_text()
    assert "generation" not in cli and "synthetic" not in cli


def test_generation_grant_exact_and_conflicting_reruns_are_side_effect_free(tmp_path):
    store, clock = generation_ready(tmp_path)
    original = store.load(); journal = store._read_journal()
    assert store._prepare_generation_grant_from_reviewed_evidence() == original
    assert store._read_journal() == journal
    with pytest.raises(
        AggregateStateError, match="conflicting generation grant preparation is prohibited",
    ):
        ConflictingGrantStore(store.root, clock)._prepare_generation_grant_from_reviewed_evidence()
    assert store.load() == original
    assert store._read_journal() == journal
    assert GenerationHarnessStore(store.root, clock).load()["generation_grants"] == original["generation_grants"]


def test_generation_reservation_exact_and_conflicting_reruns_are_side_effect_free(tmp_path):
    store, clock = generation_ready(tmp_path); original = store._authorize_generation_budget()
    journal = store._read_journal()
    assert store._authorize_generation_budget() == original
    assert store._read_journal() == journal
    with pytest.raises(
        AggregateStateError, match="conflicting generation reservation is prohibited",
    ):
        ConflictingReservationStore(store.root, clock)._authorize_generation_budget()
    assert store.load() == original
    assert store._read_journal() == journal
    fresh = GenerationHarnessStore(store.root, clock).load()
    assert fresh["provider_budget_reservations"] == original["provider_budget_reservations"]
    assert fresh["budget_accounting"] == original["budget_accounting"]
    assert fresh["counters"] == original["counters"]


def test_generation_identity_lifetime_and_expiry_boundary(tmp_path):
    store, clock = generation_ready(tmp_path)
    state = store.load(); grant = state["generation_grants"]["eval-v4-01"]
    validate_generation_grant(grant, "eval-v4-01", state["ai_case_envelopes"]["eval-v4-01"], state["reviewed_preflight_evidence"]["eval-v4-01"])
    assert generation_grant_is_expired(grant, clock.now + GENERATION_GRANT_LIFETIME) is True
    assert generation_grant_is_expired(grant, clock.now + GENERATION_GRANT_LIFETIME - timedelta(microseconds=1)) is False
    clock.now += GENERATION_GRANT_LIFETIME
    with pytest.raises(AggregateStateError, match="unavailable or expired"):
        store._authorize_generation_budget()
    with pytest.raises(AggregateStateError, match="zero retries"):
        store._prepare_generation_grant_from_reviewed_evidence()


def test_generation_capacity_exact_boundaries():
    base = dict(case_reserved=Decimal("0"), case_consumed=Decimal("0"),
                aggregate_reserved=Decimal("0"), aggregate_consumed=Decimal("0"),
                requested_amount=Decimal("0.0019408"))
    enforce_generation_capacity(**base, generations_reserved=7, generations_consumed=0)
    with pytest.raises(BudgetError, match="generation operation maximum"):
        enforce_generation_capacity(**base, generations_reserved=8, generations_consumed=0)
    with pytest.raises(BudgetError, match="per-case"):
        enforce_generation_capacity(**{**base, "case_consumed": Decimal("0.03")}, generations_reserved=0, generations_consumed=0)
    with pytest.raises(BudgetError, match="aggregate"):
        enforce_generation_capacity(**{**base, "aggregate_consumed": Decimal("0.24")}, generations_reserved=0, generations_consumed=0)


def test_multi_case_generation_records_and_eight_slot_limit(tmp_path):
    store, _ = ready(tmp_path)
    for index, case_id in enumerate(AI_CASE_ORDER):
        if index:
            store.prepare_preflight_grant(); store.authorize_preflight_budget(); store.record_provider_dispatch_started()
        store.inject_reviewed_evidence(input_tokens=2852 + index)
        store._prepare_generation_grant_from_reviewed_evidence(); state = store._authorize_generation_budget()
        if index < 7: store.advance()
    assert len(state["generation_grants"]) == 8
    assert len([r for r in state["provider_budget_reservations"].values() if r["immutable_binding"]["phase"] == "generation"]) == 8
    assert state["counters"]["generations_reserved"] == MAX_GENERATIONS
    assert state["counters"]["token_preflights_consumed"] == 8
    assert state["counters"]["provider_spend_consumed_usd"] == "0.00"
    assert Decimal(state["counters"]["provider_spend_reserved_usd"]) > 0
    # Fully reconcile a malicious ninth counted slot. The aggregate invariant
    # executes before the individual immutable-binding check and is the exact rejection.
    def ninth_slot(malicious):
        target = malicious["provider_budget_reservations"]["eval-v4-10:generation"]
        target["immutable_binding"]["operation_count"] = 2
        target["reservation_sha256"] = reservation_identity(target)
        accounting = derive_budget_accounting(malicious["provider_budget_reservations"])
        malicious["budget_accounting"] = accounting
        malicious["counters"]["generations_reserved"] = accounting["aggregate"]["generations_reserved"]
    assert_rehashed_state_attack(
        store, ninth_slot, "provider generation operation count exceeds frozen maximum")


def test_eight_generation_reserved_consumed_combinations_validate(tmp_path):
    store, _ = ready(tmp_path)
    for index, _case_id in enumerate(AI_CASE_ORDER):
        if index:
            store.prepare_preflight_grant(); store.authorize_preflight_budget(); store.record_provider_dispatch_started()
        store.inject_reviewed_evidence(input_tokens=2852 + index)
        store._prepare_generation_grant_from_reviewed_evidence(); state = store._authorize_generation_budget()
        if index < 7:
            store.advance()
    consumed_cases = 0
    for consumed in (0, 1, 4, 8):
        for case_id in AI_CASE_ORDER[consumed_cases:consumed]:
            state = store.consume_generation(case_id)
        consumed_cases = consumed
        aggregate = state["budget_accounting"]["aggregate"]
        assert aggregate["generations_reserved"] == 8 - consumed
        assert aggregate["generations_consumed"] == consumed
        assert store._validate_journal(store._read_journal())[-1] == state
        assert GenerationHarnessStore(store.root, store.clock).load() == state
        with pytest.raises(AggregateStateError, match="operation is unavailable"):
            AggregateStore(store.root, store.clock).load(observe_expiry=False)


def test_generation_grant_rejects_fully_recomputed_identity_drifts(tmp_path):
    store, _ = generation_ready(tmp_path)
    state = store.load(); case_id = "eval-v4-01"
    grant = state["generation_grants"][case_id]
    evidence = state["reviewed_preflight_evidence"][case_id]
    envelope = state["ai_case_envelopes"][case_id]
    attacks = {
        "wrong envelope": ("case_envelope_sha256", "0" * 64),
        "wrong request": ("deterministic_request_sha256", "1" * 64),
        "wrong attempt": ("canonical_attempt_sha256", "2" * 64),
        "wrong fingerprint": ("provider_fingerprint", "3" * 64),
        "provider drift": ("provider", "Other"),
        "model drift": ("ai_model_identifier", "other-model"),
        "sdk drift": ("sdk", "openai==0"),
        "manifest drift": ("frozen_v4_manifest_sha256", "4" * 64),
        "phase drift": ("phase", "preflight"),
        "amount drift": ("conservative_operation_ceiling_usd", "0.02"),
        "operation drift": ("operation_count", 2),
        "retry authority": ("maximum_retries", 1),
    }
    for _name, (field, value) in attacks.items():
        attacked = json.loads(canonical_json(grant)); attacked["immutable_binding"][field] = value
        attacked["grant_sha256"] = digest({
            "grant_schema": attacked["grant_schema"], "grant_version": attacked["grant_version"],
            "immutable_binding": attacked["immutable_binding"],
        })
        with pytest.raises(GenerationGrantError, match="exact frozen binding"):
            validate_generation_grant(attacked, case_id, envelope, evidence)


def test_persisted_deterministic_and_non_next_generation_targets_rejected(tmp_path):
    store, _ = generation_ready(tmp_path)
    assert_rehashed_last_event_metadata_attack(
        store, "eval-v4-07", "deterministic case cannot receive generation authority")
    assert_rehashed_last_event_metadata_attack(
        store, "eval-v4-02", "generation grant must target the exact current AI case")


def test_persisted_reviewed_evidence_attacks_rejected(tmp_path):
    store, _ = generation_ready(tmp_path)

    def missing(state):
        del state["reviewed_preflight_evidence"]["eval-v4-01"]
    assert_rehashed_state_attack(store, missing, "generation grant requires reviewed preflight evidence")

    def foreign(state):
        evidence = state["reviewed_preflight_evidence"]["eval-v4-01"]
        evidence["immutable_binding"]["case_id"] = "eval-v4-02"
        evidence["evidence_binding_sha256"] = digest({
            "evidence_schema": evidence["evidence_schema"],
            "evidence_version": evidence["evidence_version"],
            "immutable_binding": evidence["immutable_binding"],
        })
    assert_rehashed_state_attack(store, foreign, "reviewed preflight evidence does not match the exact case binding")

    def altered(state):
        evidence = state["reviewed_preflight_evidence"]["eval-v4-01"]
        evidence["immutable_binding"]["preflight_review_sha256"] = "a" * 64
        evidence["evidence_binding_sha256"] = digest({
            "evidence_schema": evidence["evidence_schema"],
            "evidence_version": evidence["evidence_version"],
            "immutable_binding": evidence["immutable_binding"],
        })
    assert_rehashed_state_attack(store, altered, "generation grant reviewed preflight evidence binding mismatch")

    def ineligible(state):
        evidence = state["reviewed_preflight_evidence"]["eval-v4-01"]
        evidence["immutable_binding"]["generation_gate_binding_eligible"] = False
        evidence["evidence_binding_sha256"] = digest({
            "evidence_schema": evidence["evidence_schema"],
            "evidence_version": evidence["evidence_version"],
            "immutable_binding": evidence["immutable_binding"],
        })
    assert_rehashed_state_attack(store, ineligible, "reviewed preflight evidence is not generation eligible")


def test_persisted_generation_authority_requires_reservation_and_forbids_drift(tmp_path):
    store, _ = generation_ready(tmp_path); store._authorize_generation_budget()

    def no_reservation(state):
        del state["provider_budget_reservations"]["eval-v4-01:generation"]
        state["budget_accounting"] = derive_budget_accounting(state["provider_budget_reservations"])
        aggregate = state["budget_accounting"]["aggregate"]
        state["counters"].update(
            generations_reserved=aggregate["generations_reserved"],
            generations_consumed=aggregate["generations_consumed"],
            provider_spend_reserved_usd=aggregate["total_provider_exposure_reserved_usd"],
            provider_spend_consumed_usd=aggregate["total_provider_exposure_consumed_usd"],
        )
    assert_rehashed_state_attack(store, no_reservation, "generation grant lifecycle does not match its durable reservation")

    for field, message in (
        ("dispatch_authorized", "generation grant lifecycle is not exact"),
        ("provider_execution_authorized", "generation grant lifecycle is not exact"),
        ("retry_authorized", "generation grant lifecycle is not exact"),
    ):
        def drift(state, field=field):
            state["generation_grants"]["eval-v4-01"]["lifecycle"][field] = True
        assert_rehashed_state_attack(store, drift, message)


def test_generation_cannot_rewrite_consumed_preflight_history(tmp_path):
    store, _ = generation_ready(tmp_path); store._authorize_generation_budget()

    def grant_identity_rewrite(state):
        case_id = "eval-v4-01"
        original_reservation = state["provider_budget_reservations"][case_id]
        replacement = build_preflight_grant(
            case_id, state["ai_case_envelopes"][case_id],
            datetime(2026, 8, 11, 12, 0, 1, tzinfo=timezone.utc),
        )
        replacement["lifecycle"] = dispatch_started_lifecycle()
        reservation = build_preflight_reservation(
            replacement, state["ai_case_envelopes"][case_id],
            original_reservation["immutable_binding"]["reserved_at"],
        )
        reservation["lifecycle"] = json.loads(canonical_json(original_reservation["lifecycle"]))
        state["preflight_grants"][case_id] = replacement
        state["provider_budget_reservations"][case_id] = reservation
        state["budget_accounting"] = derive_budget_accounting(state["provider_budget_reservations"])
    assert_rehashed_retention_attack(
        store, grant_identity_rewrite,
        "consumed preflight history cannot replace its grant identity")

    def reservation_identity_rewrite(state):
        case_id = "eval-v4-01"
        original = state["provider_budget_reservations"][case_id]
        replacement = build_preflight_reservation(
            state["preflight_grants"][case_id], state["ai_case_envelopes"][case_id],
            "2026-08-11T12:00:01Z",
        )
        replacement["lifecycle"] = json.loads(canonical_json(original["lifecycle"]))
        state["provider_budget_reservations"][case_id] = replacement
        state["budget_accounting"] = derive_budget_accounting(state["provider_budget_reservations"])
    assert_rehashed_retention_attack(
        store, reservation_identity_rewrite,
        "consumed preflight history cannot replace its reservation identity")

    def lifecycle_restore(state):
        reservation = state["provider_budget_reservations"]["eval-v4-01"]
        reservation["lifecycle"].update(
            status="reserved", provider_dispatch_status="not_started",
            attempt_consumed=False, consumed_amount_usd="0.00",
            consumed_operation_count=0, dispatch_started_at=None,
        )
        reservation["reservation_sha256"] = reservation_identity(reservation)
        state["preflight_grants"]["eval-v4-01"]["lifecycle"] = budget_authorized_lifecycle()
        state["budget_accounting"] = derive_budget_accounting(state["provider_budget_reservations"])
        aggregate = state["budget_accounting"]["aggregate"]
        state["counters"].update(
            token_preflights_reserved=aggregate["token_preflights_reserved"],
            token_preflights_consumed=aggregate["token_preflights_consumed"],
        )
    assert_rehashed_state_attack(store, lifecycle_restore, "generation evidence requires exact consumed preflight history")


def test_prior_generation_records_cannot_be_deleted_or_replaced(tmp_path):
    store, _ = ready(tmp_path)
    store.inject_reviewed_evidence(); store._prepare_generation_grant_from_reviewed_evidence()
    store._authorize_generation_budget(); store.advance()
    store.prepare_preflight_grant(); store.authorize_preflight_budget()
    store.record_provider_dispatch_started(); store.inject_reviewed_evidence(input_tokens=2853)
    store._prepare_generation_grant_from_reviewed_evidence(); store._authorize_generation_budget()

    def delete_prior(state):
        del state["reviewed_preflight_evidence"]["eval-v4-01"]
        del state["generation_grants"]["eval-v4-01"]
        del state["provider_budget_reservations"]["eval-v4-01:generation"]
        state["budget_accounting"] = derive_budget_accounting(state["provider_budget_reservations"])
        aggregate = state["budget_accounting"]["aggregate"]
        state["counters"].update(
            generations_reserved=aggregate["generations_reserved"],
            generations_consumed=aggregate["generations_consumed"],
            provider_spend_reserved_usd=aggregate["total_provider_exposure_reserved_usd"],
            provider_spend_consumed_usd=aggregate["total_provider_exposure_consumed_usd"],
        )
    assert_rehashed_retention_attack(
        store, delete_prior, "prior generation history cannot delete a retained grant")

    def replace_prior(state):
        case_id = "eval-v4-01"
        original_reservation = state["provider_budget_reservations"][f"{case_id}:generation"]
        replacement = build_generation_grant(
            case_id, state["ai_case_envelopes"][case_id],
            state["reviewed_preflight_evidence"][case_id],
            datetime(2026, 8, 11, 12, 0, 1, tzinfo=timezone.utc),
        )
        replacement["lifecycle"] = active_generation_lifecycle()
        reservation = build_generation_reservation(
            replacement, state["ai_case_envelopes"][case_id],
            "2026-08-11T12:00:01Z",
        )
        state["generation_grants"][case_id] = replacement
        state["provider_budget_reservations"][f"{case_id}:generation"] = reservation
        state["budget_accounting"] = derive_budget_accounting(state["provider_budget_reservations"])
    assert_rehashed_retention_attack(
        store, replace_prior, "prior generation history cannot replace a retained grant")


def test_crash_after_generation_reservation_history_recovers_once(tmp_path):
    store, clock = generation_ready(tmp_path)
    def fail(boundary):
        if boundary == "after_history_replace": raise RuntimeError("synthetic crash")
    with pytest.raises(RuntimeError, match="synthetic crash"):
        GenerationHarnessStore(store.root, clock, fail)._authorize_generation_budget()
    recovered = GenerationHarnessStore(store.root, clock).load()
    assert recovered["counters"]["generations_reserved"] == 1
    assert len(recovered["generation_grants"]) == 1
    assert len([e for e in GenerationHarnessStore(store.root, clock)._read_journal()["events"] if e["operation"] == "generation_budget_reserved"]) == 1


def test_crash_after_generation_grant_history_recovers_once(tmp_path):
    store, clock = ready(tmp_path); store.inject_reviewed_evidence()
    def fail(boundary):
        if boundary == "after_history_replace": raise RuntimeError("synthetic crash")
    with pytest.raises(RuntimeError, match="synthetic crash"):
        GenerationHarnessStore(store.root, clock, fail)._prepare_generation_grant_from_reviewed_evidence()
    recovered = GenerationHarnessStore(store.root, clock).load()
    assert len(recovered["generation_grants"]) == 1
    assert len([e for e in GenerationHarnessStore(store.root, clock)._read_journal()["events"] if e["operation"] == "generation_grant_prepared"]) == 1


def test_generation_code_has_no_provider_or_credential_path():
    paths = [Path(__file__).with_name(name) for name in (
        "v4_formal_evaluation_live_generation.py", "v4_formal_evaluation_live_state.py")]
    for path in paths:
        source = path.read_text(); tree = ast.parse(source)
        imports = {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
        imports |= {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
        assert not any(name.startswith(("openai", "socket", "httpx", "requests")) for name in imports)
        assert "OPENAI_API_KEY" not in source
