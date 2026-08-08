"""Frozen-v4 sequence-1 preflight identity and lifecycle tests."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from unittest import SkipTest

import pytest
import v4_sequence_1_preflight as gate

SCRIPT = Path(__file__).resolve().parent
ROOT = SCRIPT.parents[2]
for value in (SCRIPT, ROOT / "backend"):
    if str(value) not in sys.path: sys.path.insert(0, str(value))

from run_openai_stage_b_v2_pilot import prepare_frozen_v2_pilot  # noqa: E402
from run_openai_stage_b_v3_pilot import prepare_frozen_v3_pilot  # noqa: E402
from run_openai_stage_b_v4_pilot import canonical_attempt_digest, deterministic_request_digest, prepare_frozen_v4_pilot  # noqa: E402
from openai_transport import OpenAIPreflightResult  # noqa: E402
from v4_sequence_1_preflight import (  # noqa: E402
    CANDIDATE, CANDIDATE_DIGEST, CANONICAL_DIGEST, MANIFEST, MANIFEST_DIGEST,
    OPERATOR_INTENT, PROVIDER_FINGERPRINT, REQUEST_DIGEST, RUN_SERIES,
    RENDERED_TMP, V4PreflightError, activate, activation_review,
    execute_preflight, generation_binding_dry_run, install, paths, render, review_evidence,
    verify_lifecycle_history, verify_static,
)


def test_exact_attempt_verification_precedes_credential_lookup(monkeypatch) -> None:
    credential_lookup_attempted = False

    def client_builder(_credential):
        nonlocal credential_lookup_attempted
        credential_lookup_attempted = True
        raise AssertionError("credential boundary crossed")

    monkeypatch.setattr(gate, "verify_active", lambda **_kwargs: {"generation_authorized": False})
    monkeypatch.setattr(
        gate, "verify_preflight_attempt",
        lambda: (_ for _ in ()).throw(V4PreflightError("synthetic exact-attempt drift")),
    )
    with pytest.raises(V4PreflightError, match="exact-attempt drift"):
        gate.execute_preflight(
            environment={}, now=datetime.now(timezone.utc), client_builder=client_builder,
            output_root=Path("/tmp/unused-v4-preflight-state"),
            repository_root=Path("/tmp/unused-v4-preflight-repository"),
        )
    assert credential_lookup_attempted is False


def test_candidate_manifest_and_exact_v4_request_are_bound() -> None:
    status = verify_static()
    assert status == {"candidate_digest": CANDIDATE_DIGEST, "manifest_digest": MANIFEST_DIGEST, "request": REQUEST_DIGEST, "canonical": CANONICAL_DIGEST, "fingerprint": PROVIDER_FINGERPRINT}
    assert hashlib.sha256(CANDIDATE.read_bytes()).hexdigest() == CANDIDATE_DIGEST
    assert hashlib.sha256(MANIFEST.read_bytes()).hexdigest() == MANIFEST_DIGEST
    candidate = tomllib.loads(CANDIDATE.read_text())
    assert candidate["bindings"]["run_series_id"] == RUN_SERIES
    assert candidate["bindings"]["sequence"] == 1
    assert candidate["bindings"]["audit_prefix"] == "001-storage_unknown"
    assert candidate["authorization"] == {"credential_access_authorized": False, "token_preflight_authorized": False, "ai_generation_authorized": False}
    assert candidate["scope"]["maximum_token_preflight_requests"] == 1
    assert candidate["scope"]["maximum_ai_generation_requests"] == 0
    assert candidate["scope"]["automatic_retries"] == 0


def test_v4_request_differs_from_v2_v3_and_mixed_identity_fails() -> None:
    v2 = prepare_frozen_v2_pilot(); v3 = prepare_frozen_v3_pilot(); v4 = prepare_frozen_v4_pilot()
    assert deterministic_request_digest(v4) == REQUEST_DIGEST
    assert canonical_attempt_digest(v4) == CANONICAL_DIGEST
    assert hashlib.sha256(v2.provider_request.deterministic_request_json.encode()).hexdigest() != REQUEST_DIGEST
    assert deterministic_request_digest(v3) != REQUEST_DIGEST
    assert canonical_attempt_digest(v3) != CANONICAL_DIGEST
    assert v2.provider_request.response_json_schema != v4.provider_request.response_json_schema
    with pytest.raises(Exception): type(v4.request).model_validate(v2.request.model_dump())
    with pytest.raises(Exception): type(v2.request).model_validate(v4.request.model_dump())
    with pytest.raises(Exception): type(v4.request).model_validate(v3.request.model_dump())


def test_every_operational_path_is_fixed_to_new_v4_series() -> None:
    target = paths(Path("/tmp/v4-state"), Path("/tmp/v4-repository"))
    operational = [value for key, value in vars(target).items() if key not in {"execution", "closed"}]
    for path in operational:
        assert "moving-service-stage-b-v4-pilot-20260808" in str(path)
        assert "001-storage_unknown" in path.name
        assert "004-storage_unknown" not in str(path)
        assert "moving-service-stage-b-v2-pilot-20260802" not in str(path)


def _closed_repository(tmp_path: Path) -> Path:
    repository = tmp_path / "repository"; docs = repository / "docs/experiments/suggest-moving-service-questions/v2-pilot"; docs.mkdir(parents=True)
    closed = ROOT / "docs/experiments/suggest-moving-service-questions/v2-pilot/closed-execution-manifest.json"
    shutil.copyfile(closed, docs / "closed-execution-manifest.json"); shutil.copyfile(closed, docs / "execution-manifest.json")
    return repository


def _json(path: Path, value: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _toml(path: Path, value: dict) -> str:
    lines = []
    for section, fields in value.items():
        lines.append(f"[{section}]")
        for key, item in fields.items():
            if isinstance(item, bool): encoded = str(item).lower()
            else: encoded = json.dumps(item)
            lines.append(f"{key} = {encoded}")
        lines.append("")
    path.write_text("\n".join(lines).rstrip() + "\n")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rebind_semantic_mutation(output: Path, repository: Path, stage: str) -> str:
    """Recompute every digest downstream of an intentionally wrong source record."""
    target = paths(output, repository)
    evidence = json.loads(target.evidence.read_text())
    if stage == "authorization":
        authorization_digest = hashlib.sha256(target.rendered.read_bytes()).hexdigest()
        installation = json.loads(target.installation.read_text()); installation["installed_digest"] = authorization_digest
        installation_digest = _json(target.installation, installation)
        activation_review_record = json.loads(target.activation_review.read_text())
        activation_review_record["installed_artifact_digest"] = authorization_digest
        activation_review_record["installation_record_digest"] = installation_digest
        activation_review_digest = _json(target.activation_review, activation_review_record)
        activation = json.loads(target.activation.read_text())
        activation["authorization_digest"] = authorization_digest
        activation["activation_review_digest"] = activation_review_digest
        activation["active_manifest_digest"] = hashlib.sha256(gate.active_manifest_bytes(authorization_digest)).hexdigest()
        _json(target.activation, activation)
    if stage in {"authorization", "activation"}:
        activation_digest = hashlib.sha256(target.activation.read_bytes()).hexdigest()
        transaction = json.loads(target.transaction.read_text())
        transaction["activation_record_digest"] = activation_digest
        if stage == "authorization":
            transaction["artifact_digest"] = hashlib.sha256(target.rendered.read_bytes()).hexdigest()
            transaction["activation_review_digest"] = hashlib.sha256(target.activation_review.read_bytes()).hexdigest()
        _json(target.transaction, transaction)
        audit = json.loads(target.audit.read_text()); audit["activation_record_digest"] = activation_digest
        if stage == "authorization": audit["authorization_digest"] = hashlib.sha256(target.rendered.read_bytes()).hexdigest()
        _json(target.audit, audit)
        consumption = json.loads(target.consumption.read_text()); consumption["activation_record_digest"] = activation_digest
        if stage == "authorization": consumption["authorization_digest"] = hashlib.sha256(target.rendered.read_bytes()).hexdigest()
        _json(target.consumption, consumption)
        closure = json.loads(target.closure.read_text()); closure["activation_record_digest"] = activation_digest
        if stage == "authorization":
            closure["authorization_digest"] = hashlib.sha256(target.rendered.read_bytes()).hexdigest()
            closure["activation_review_digest"] = hashlib.sha256(target.activation_review.read_bytes()).hexdigest()
        _json(target.closure, closure)
    if stage in {"authorization", "activation", "transaction"}:
        transaction_digest = hashlib.sha256(target.transaction.read_bytes()).hexdigest()
        closure = json.loads(target.closure.read_text()); closure["transaction_journal_digest"] = transaction_digest
        _json(target.closure, closure)
    if stage in {"authorization", "activation", "audit"}:
        audit = json.loads(target.audit.read_text()); audit_digest = hashlib.sha256(target.audit.read_bytes()).hexdigest()
        consumption = json.loads(target.consumption.read_text()); consumption["audit_sha256"] = audit_digest
        _json(target.consumption, consumption)
        closure = json.loads(target.closure.read_text()); closure["audit_sha256"] = audit_digest
        _json(target.closure, closure)
        evidence.update(audit); evidence["audit_sha256"] = audit_digest
    if stage in {"authorization", "activation", "audit", "consumption"}:
        consumption_digest = hashlib.sha256(target.consumption.read_bytes()).hexdigest()
        closure = json.loads(target.closure.read_text()); closure["consumption_record_sha256"] = consumption_digest
        _json(target.closure, closure); evidence["consumption_record_sha256"] = consumption_digest
    evidence["authorization_digest"] = hashlib.sha256(target.rendered.read_bytes()).hexdigest()
    evidence["installation_record_sha256"] = hashlib.sha256(target.installation.read_bytes()).hexdigest()
    evidence["activation_review_sha256"] = hashlib.sha256(target.activation_review.read_bytes()).hexdigest()
    evidence["activation_record_sha256"] = hashlib.sha256(target.activation.read_bytes()).hexdigest()
    evidence["transaction_journal_sha256"] = hashlib.sha256(target.transaction.read_bytes()).hexdigest()
    evidence["closure_sha256"] = hashlib.sha256(target.closure.read_bytes()).hexdigest()
    return _json(target.evidence, evidence)


def _review_state(tmp_path: Path) -> tuple[Path, Path, str]:
    output = tmp_path / "state"; repository = _closed_repository(tmp_path)
    now = datetime.now(timezone.utc).replace(microsecond=0)
    RENDERED_TMP.unlink(missing_ok=True)
    rendered = render(approver="Synthetic Approver",
        approved_at=gate.stamp(now - timedelta(seconds=12)),
        activated_at=gate.stamp(now - timedelta(seconds=10)),
        expires_at=gate.stamp(now + timedelta(seconds=890)),
        reason="Synthetic realistic lifecycle", now=now - timedelta(seconds=8))
    installed = install(source=RENDERED_TMP, expected_sha256=rendered["sha256"],
        now=now - timedelta(seconds=8), output_root=output)
    reviewed = activation_review(artifact_sha256=rendered["sha256"], reviewer="Synthetic Reviewer",
        decision="approve", reviewed_at=gate.stamp(now - timedelta(seconds=7)),
        notes="Synthetic activation review", now=now - timedelta(seconds=7), output_root=output)
    activate(artifact_sha256=rendered["sha256"],
        installation_sha256=installed["installation_record_digest"],
        review_sha256=reviewed["review_sha256"], operator="Synthetic Operator",
        operator_intent=OPERATOR_INTENT, now=now - timedelta(seconds=5),
        output_root=output, repository_root=repository)
    RENDERED_TMP.unlink(missing_ok=True)

    class Owned:
        client = object()
        def close(self): pass

    class Transport:
        def __init__(self, prepared): self.prepared = prepared
        def request_fingerprint(self, _request): return PROVIDER_FINGERPRINT
        def preflight(self, request):
            assert request is self.prepared.provider_request
            return OpenAIPreflightResult(PROVIDER_FINGERPRINT, 4242, 1.25, Decimal("0.0024242"))

    execute_preflight(environment={
        "GOTIME_MOVING_SERVICE_EVAL_ENABLED": "1",
        "GOTIME_MOVING_SERVICE_EVAL_OPERATOR_INTENT": OPERATOR_INTENT,
        "GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY": "synthetic-not-a-real-credential",
    }, now=now, client_builder=lambda _credential: Owned(),
        transport_factory=lambda _client, prepared: Transport(prepared),
        output_root=output, repository_root=repository)
    target = paths(output, repository)
    return output, repository, hashlib.sha256(target.evidence.read_bytes()).hexdigest()


def _review_clock(output: Path, repository: Path, *, stale: bool = False) -> tuple[str, datetime]:
    evidence = json.loads(paths(output, repository).evidence.read_text())
    value = gate.utc(evidence["review_deadline"] if stale else evidence["created_at"])
    return gate.stamp(value), value


def test_immediate_review_and_generation_binding_are_non_authoritative(tmp_path) -> None:
    output, repository, evidence_digest = _review_state(tmp_path)
    reviewed_at, now = _review_clock(output, repository)
    result = review_evidence(evidence_sha256=evidence_digest, input_tokens=4242, conservative_cost="0.0024242", reviewer="Reviewer", decision="approve", reviewed_at=reviewed_at, token_count_plausible=True, cost_within_limit=True, frozen_bindings_confirmed=True, evidence_history_confirmed=True, notes="Synthetic review", now=now, output_root=output, repository_root=repository)
    assert result["generation_gate_binding_eligible"] is True
    binding = generation_binding_dry_run(output_root=output, repository_root=repository)
    assert binding["writes_performed"] is False and binding["generation_authorized"] is False
    assert binding["preflight_evidence_digest"] == evidence_digest


@pytest.mark.parametrize("field,value", [
    ("run_series_id", "moving-service-stage-b-v3-pilot-20260807"),
    ("frozen_v4_manifest_digest", "44da0c5005515784c2c13737ca12a4382c084f1aa56fea5b4a4d40e66fb8659c"),
    ("deterministic_request_digest", "952b8003f184de1ff9617103c8c93ab64d87e63cb4e4daee84647b7dd505ed79"),
    ("canonical_attempt_digest", "d9d8141853b7d034ce30de8c9c2689d9738b0bfd73d812a2150b823111b3bdcf"),
    ("provider_preflight_fingerprint", "a5895ad53d54d6d03652152aeadbf8b71a2c672cab86640d1798a3a3680a15e4"),
])
def test_generation_binding_preview_rejects_cross_version_or_drift(
        tmp_path, field: str, value: str) -> None:
    output, repository, evidence_digest = _review_state(tmp_path)
    target = paths(output, repository)
    evidence = json.loads(target.evidence.read_text()); evidence[field] = value
    target.evidence.write_text(json.dumps(evidence, sort_keys=True) + "\n")
    review = {
        "run_series_id": RUN_SERIES, "sequence": 1, "fixture_id": "storage_unknown",
        "phase": "preflight_review", "preflight_evidence_digest": hashlib.sha256(target.evidence.read_bytes()).hexdigest(),
        "frozen_v4_manifest_digest": "3cdbd2bf3606191aa52108d8284c8ab300d58a511f313f78a06be51d95fac649",
        "request_identity_artifact_digest": "b5125e2075779306f0a4374676d442fa3016702bdb5143bc8e3a6b7173d9dd35",
        "deterministic_request_digest": REQUEST_DIGEST, "canonical_attempt_digest": CANONICAL_DIGEST,
        "provider_fingerprint": PROVIDER_FINGERPRINT, "decision": "approve",
        "reviewed_at": "2030-01-01T00:00:10Z", "generation_gate_binding_eligible": True,
    }
    target.evidence_review.write_text(json.dumps(review, sort_keys=True) + "\n")
    with pytest.raises(V4PreflightError, match="cannot resolve"):
        generation_binding_dry_run(output_root=output, repository_root=repository)


def test_late_evidence_approval_fails_closed(tmp_path) -> None:
    output, repository, evidence_digest = _review_state(tmp_path)
    reviewed_at, now = _review_clock(output, repository, stale=True)
    with pytest.raises(V4PreflightError, match="invalid or late"):
        review_evidence(evidence_sha256=evidence_digest, input_tokens=4242, conservative_cost="0.0024242", reviewer="Reviewer", decision="approve", reviewed_at=reviewed_at, token_count_plausible=True, cost_within_limit=True, frozen_bindings_confirmed=True, evidence_history_confirmed=True, notes="Late", now=now, output_root=output, repository_root=repository)
    assert not paths(output, repository).evidence_review.exists()


HISTORY_REJECTION_CASES = (
    "empty_audit", "empty_consumption", "empty_closure",
    "altered_audit", "altered_consumption", "altered_closure",
    "wrong_audit_digest", "wrong_consumption_digest", "wrong_closure_digest",
    "v3_audit", "v3_closure", "wrong_run_series", "wrong_sequence",
    "wrong_fixture", "wrong_phase", "wrong_authorization_binding",
    "wrong_activation_binding", "wrong_transaction_id", "not_consumed",
    "reusable", "active_authorization", "execution_not_closed",
    "preflight_not_attempted", "preflight_not_succeeded",
    "wrong_preflight_count", "generation_attempted", "generation_count",
    "stale_evidence",
)


@pytest.mark.parametrize("case", HISTORY_REJECTION_CASES)
def test_lifecycle_history_rejects_incomplete_mismatched_or_stale_records(
        tmp_path, case: str) -> None:
    output, repository, evidence_digest = _review_state(tmp_path)
    target = paths(output, repository)
    evidence = json.loads(target.evidence.read_text())

    record_path = None
    field = None
    value = None
    if case.startswith("empty_"):
        record_path = {"empty_audit": target.audit, "empty_consumption": target.consumption,
                       "empty_closure": target.closure}[case]
        record_path.write_text("{}\n")
    elif case.startswith("altered_"):
        record_path = {"altered_audit": target.audit, "altered_consumption": target.consumption,
                       "altered_closure": target.closure}[case]
        record = json.loads(record_path.read_text()); record["unexpected"] = True; _json(record_path, record)
    elif case.startswith("wrong_") and case.endswith("_digest"):
        field = {"wrong_audit_digest": "audit_sha256", "wrong_consumption_digest": "consumption_record_sha256",
                 "wrong_closure_digest": "closure_sha256"}[case]
        evidence[field] = "0" * 64
        evidence_digest = _json(target.evidence, evidence)
    elif case in {"v3_audit", "wrong_run_series", "wrong_sequence", "wrong_fixture", "wrong_phase",
                  "wrong_authorization_binding", "wrong_activation_binding", "wrong_transaction_id",
                  "preflight_not_attempted", "preflight_not_succeeded", "wrong_preflight_count",
                  "generation_attempted", "generation_count"}:
        record_path = target.audit; record = json.loads(record_path.read_text())
        field, value = {
            "v3_audit": ("run_series_id", "moving-service-stage-b-v3-pilot-20260807"),
            "wrong_run_series": ("run_series_id", "wrong-series"), "wrong_sequence": ("sequence", 2),
            "wrong_fixture": ("fixture_id", "wrong_fixture"), "wrong_phase": ("phase", "generation"),
            "wrong_authorization_binding": ("authorization_digest", "0" * 64),
            "wrong_activation_binding": ("activation_record_digest", "0" * 64),
            "wrong_transaction_id": ("transaction_id", "wrong-transaction"),
            "preflight_not_attempted": ("token_preflight_attempted", False),
            "preflight_not_succeeded": ("token_preflight_succeeded", False),
            "wrong_preflight_count": ("preflight_request_count", 2),
            "generation_attempted": ("ai_generation_attempted", True),
            "generation_count": ("generation_request_count", 1),
        }[case]
        record[field] = value; _json(record_path, record)
    elif case == "v3_closure":
        record = json.loads(target.closure.read_text()); record["run_series_id"] = "moving-service-stage-b-v3-pilot-20260807"; _json(target.closure, record)
    elif case in {"not_consumed", "reusable"}:
        record = json.loads(target.consumption.read_text())
        record["authorization_consumed" if case == "not_consumed" else "reusable"] = case != "not_consumed"
        _json(target.consumption, record)
    elif case == "active_authorization":
        target.active.write_bytes(target.rendered.read_bytes())
    elif case == "execution_not_closed":
        target.execution.write_text('{"status":"active"}\n')

    reviewed_at, now = _review_clock(output, repository, stale=case == "stale_evidence")
    with pytest.raises(V4PreflightError):
        review_evidence(evidence_sha256=evidence_digest, input_tokens=4242,
            conservative_cost="0.0024242", reviewer="Reviewer", decision="approve",
            reviewed_at=reviewed_at, token_count_plausible=True, cost_within_limit=True,
            frozen_bindings_confirmed=True, evidence_history_confirmed=True, notes="Synthetic review",
            now=now, output_root=output, repository_root=repository)
    assert not target.evidence_review.exists()


def test_unapproved_review_cannot_bind_generation(tmp_path) -> None:
    output, repository, evidence_digest = _review_state(tmp_path)
    reviewed_at, now = _review_clock(output, repository)
    review_evidence(evidence_sha256=evidence_digest, input_tokens=4242,
        conservative_cost="0.0024242", reviewer="Reviewer", decision="reject",
        reviewed_at=reviewed_at, token_count_plausible=True, cost_within_limit=True,
        frozen_bindings_confirmed=True, evidence_history_confirmed=True, notes="Synthetic rejection",
        now=now, output_root=output,
        repository_root=repository)
    with pytest.raises(V4PreflightError):
        generation_binding_dry_run(output_root=output, repository_root=repository)


def test_approved_review_rejects_subsequently_mutated_history(tmp_path) -> None:
    output, repository, evidence_digest = _review_state(tmp_path)
    reviewed_at, now = _review_clock(output, repository)
    review_evidence(evidence_sha256=evidence_digest, input_tokens=4242,
        conservative_cost="0.0024242", reviewer="Reviewer", decision="approve",
        reviewed_at=reviewed_at, token_count_plausible=True, cost_within_limit=True,
        frozen_bindings_confirmed=True, evidence_history_confirmed=True, notes="Synthetic approval",
        now=now, output_root=output,
        repository_root=repository)
    target = paths(output, repository); closure = json.loads(target.closure.read_text())
    closure["authorization_reusable"] = True; _json(target.closure, closure)
    with pytest.raises(V4PreflightError):
        generation_binding_dry_run(output_root=output, repository_root=repository)


AUTHORIZATION_SEMANTIC_MUTATIONS = (
    ("wrong_frozen_manifest", "bindings", "frozen_v4_manifest_digest", "0" * 64),
        ("wrong_prompt_identity", "bindings", "prompt_version", "wrong-prompt-identity"),
        ("wrong_schema_identity", "bindings", "schema_version", "wrong-schema-identity"),
    ("wrong_request", "bindings", "deterministic_request_digest", "0" * 64),
    ("wrong_canonical", "bindings", "canonical_attempt_digest", "0" * 64),
    ("wrong_fingerprint", "bindings", "provider_fingerprint", "0" * 64),
    ("wrong_provider", "bindings", "provider", "Other"),
    ("wrong_model", "bindings", "ai_model_identifier", "other-model"),
    ("wrong_sdk", "bindings", "sdk_pin", "openai==0.0.0"),
    ("wrong_intent", "scope", "operator_intent", "WRONG_INTENT"),
    ("wrong_credential_limit", "scope", "maximum_credential_lookups", 2),
    ("wrong_client_limit", "scope", "maximum_client_constructions", 2),
    ("wrong_preflight_limit", "scope", "maximum_token_preflight_requests", 2),
    ("wrong_generation_limit", "scope", "maximum_ai_generation_requests", 1),
    ("wrong_retry_limit", "scope", "automatic_retries", 1),
    ("wrong_timeout", "scope", "preflight_timeout_seconds", 6),
    ("wrong_spend", "scope", "maximum_total_spend_usd", "0.04"),
    ("generation_authorized", "authorization", "ai_generation_authorized", True),
    ("prohibited_scope", "scope", "formal_evaluation_authorized", True),
)

ACTIVATION_SEMANTIC_MUTATIONS = (
    ("wrong_active_manifest", "active_manifest_digest", "0" * 64),
    ("wrong_authorization", "authorization_digest", "0" * 64),
    ("wrong_activation_review", "activation_review_digest", "0" * 64),
    ("wrong_transaction", "transaction_id", "wrong-transaction"),
    ("wrong_activation_state", "activation_state", "pending"),
    ("malformed_activation_time", "activated_at", "not-a-time"),
)

TRANSACTION_SEMANTIC_MUTATIONS = (
    ("wrong_closed_manifest", "closed_manifest_digest", "0" * 64),
    ("wrong_transaction_id", "transaction_id", "wrong-transaction"),
    ("wrong_authorization", "artifact_digest", "0" * 64),
    ("wrong_final_state", "state", "committed"),
    ("malformed_transaction_time", "closed_at", "not-a-time"),
)

AUDIT_SEMANTIC_MUTATIONS = (
    ("credential_not_attempted", "credential_lookup_attempted", False),
    ("credential_not_succeeded", "credential_lookup_succeeded", False),
    ("client_not_attempted", "client_construction_attempted", False),
    ("client_not_succeeded", "client_construction_succeeded", False),
    ("preflight_not_attempted", "token_preflight_attempted", False),
    ("preflight_not_succeeded", "token_preflight_succeeded", False),
    ("wrong_preflight_count", "preflight_request_count", 2),
    ("generation_attempted", "ai_generation_attempted", True),
    ("generation_count", "generation_request_count", 1),
    ("retries", "automatic_retries", 1),
)

CLOSURE_SEMANTIC_MUTATIONS = (
    ("wrong_closed_manifest", "closure", "closed_manifest_digest", "0" * 64),
    ("active_authorization", "active", "active", True),
    ("reusable", "closure", "authorization_reusable", True),
    ("preflight_authority_active", "closure", "token_preflight_authorized", True),
    ("generation_authority_active", "closure", "ai_generation_authorized", True),
    ("closure_before_consumption", "closure", "closed_at", "2000-01-01T00:00:00Z"),
    ("consumption_before_audit", "consumption", "consumed_at", "2000-01-01T00:00:00Z"),
    ("malformed_closure_time", "closure", "closed_at", "not-a-time"),
)

TIMESTAMP_SEMANTIC_MUTATIONS = (
    ("malformed_approval", "authorization", "approved_at", "not-a-time"),
    ("approval_after_eligibility", "authorization", "approved_at", "2099-01-01T00:00:00Z"),
    ("review_before_eligibility", "activation_review", "reviewed_at", "2000-01-01T00:00:00Z"),
    ("audit_before_preflight", "audit", "audit_completed_at", "2000-01-01T00:00:00Z"),
    ("evidence_before_closure", "evidence", "created_at", "2000-01-01T00:00:00Z"),
    ("wrong_review_deadline", "evidence", "review_deadline", "2099-01-01T00:00:00Z"),
)


@pytest.mark.parametrize("case,section,key,value", AUTHORIZATION_SEMANTIC_MUTATIONS)
def test_self_consistent_wrong_authorization_source_fails_semantically(
        tmp_path, case, section, key, value) -> None:
    output, repository, _ = _review_state(tmp_path); target = paths(output, repository)
    authorization = tomllib.loads(target.rendered.read_text()); authorization[section][key] = value
    _toml(target.rendered, authorization)
    evidence_digest = _rebind_semantic_mutation(output, repository, "authorization")
    _assert_approval_rejected(output, repository, evidence_digest)


@pytest.mark.parametrize("case,key,value", ACTIVATION_SEMANTIC_MUTATIONS)
def test_self_consistent_wrong_activation_source_fails_semantically(
        tmp_path, case, key, value) -> None:
    output, repository, _ = _review_state(tmp_path); target = paths(output, repository)
    record = json.loads(target.activation.read_text()); record[key] = value; _json(target.activation, record)
    evidence_digest = _rebind_semantic_mutation(output, repository, "activation")
    _assert_approval_rejected(output, repository, evidence_digest)


@pytest.mark.parametrize("case,key,value", TRANSACTION_SEMANTIC_MUTATIONS)
def test_self_consistent_wrong_transaction_source_fails_semantically(
        tmp_path, case, key, value) -> None:
    output, repository, _ = _review_state(tmp_path); target = paths(output, repository)
    record = json.loads(target.transaction.read_text()); record[key] = value; _json(target.transaction, record)
    evidence_digest = _rebind_semantic_mutation(output, repository, "transaction")
    _assert_approval_rejected(output, repository, evidence_digest)


@pytest.mark.parametrize("case,key,value", AUDIT_SEMANTIC_MUTATIONS)
def test_self_consistent_wrong_audit_source_fails_semantically(
        tmp_path, case, key, value) -> None:
    output, repository, _ = _review_state(tmp_path); target = paths(output, repository)
    record = json.loads(target.audit.read_text()); record[key] = value; _json(target.audit, record)
    evidence_digest = _rebind_semantic_mutation(output, repository, "audit")
    _assert_approval_rejected(output, repository, evidence_digest)


@pytest.mark.parametrize("case,stage,key,value", CLOSURE_SEMANTIC_MUTATIONS)
def test_self_consistent_wrong_closure_or_order_source_fails_semantically(
        tmp_path, case, stage, key, value) -> None:
    output, repository, _ = _review_state(tmp_path); target = paths(output, repository)
    if stage == "active":
        target.active.write_bytes(target.rendered.read_bytes()); evidence_digest = hashlib.sha256(target.evidence.read_bytes()).hexdigest()
    else:
        path = target.closure if stage == "closure" else target.consumption
        record = json.loads(path.read_text()); record[key] = value; _json(path, record)
        evidence_digest = _rebind_semantic_mutation(output, repository, stage)
    _assert_approval_rejected(output, repository, evidence_digest)


@pytest.mark.parametrize("case,stage,key,value", TIMESTAMP_SEMANTIC_MUTATIONS)
def test_self_consistent_wrong_timestamp_source_fails_semantically(
        tmp_path, case, stage, key, value) -> None:
    output, repository, _ = _review_state(tmp_path); target = paths(output, repository)
    if stage == "authorization":
        record = tomllib.loads(target.rendered.read_text()); record["approval"][key] = value
        _toml(target.rendered, record); evidence_digest = _rebind_semantic_mutation(output, repository, "authorization")
    elif stage == "activation_review":
        record = json.loads(target.activation_review.read_text()); record[key] = value
        _json(target.activation_review, record); evidence_digest = _rebind_semantic_mutation(output, repository, "authorization")
    elif stage == "audit":
        record = json.loads(target.audit.read_text()); record[key] = value
        _json(target.audit, record); evidence_digest = _rebind_semantic_mutation(output, repository, "audit")
    else:
        evidence = json.loads(target.evidence.read_text()); evidence[key] = value
        evidence_digest = _json(target.evidence, evidence)
    _assert_approval_rejected(output, repository, evidence_digest)


def _assert_approval_rejected(output: Path, repository: Path, evidence_digest: str) -> None:
    reviewed_at, now = _review_clock(output, repository)
    with pytest.raises(V4PreflightError):
        review_evidence(evidence_sha256=evidence_digest, input_tokens=4242,
            conservative_cost="0.0024242", reviewer="Reviewer", decision="approve",
            reviewed_at=reviewed_at, token_count_plausible=True, cost_within_limit=True,
            frozen_bindings_confirmed=True, evidence_history_confirmed=True,
            notes="Semantic mutation must fail", now=now, output_root=output,
            repository_root=repository)
    assert not paths(output, repository).evidence_review.exists()


def test_activation_interruption_recovers_permanent_closed_state(tmp_path) -> None:
    repository = _closed_repository(tmp_path); output = tmp_path / "state"
    now = datetime.now(timezone.utc).replace(microsecond=0)
    RENDERED_TMP.unlink(missing_ok=True)
    try:
        rendered = render(approver="Synthetic", approved_at=(now - timedelta(seconds=10)).isoformat().replace("+00:00", "Z"), activated_at=(now - timedelta(seconds=5)).isoformat().replace("+00:00", "Z"), expires_at=(now + timedelta(seconds=895)).isoformat().replace("+00:00", "Z"), reason="Synthetic recovery", now=now)
        installed = install(source=RENDERED_TMP, expected_sha256=rendered["sha256"], now=now, output_root=output)
        reviewed = activation_review(artifact_sha256=rendered["sha256"], reviewer="Reviewer", decision="approve", reviewed_at=now.isoformat().replace("+00:00", "Z"), notes="Synthetic approval", now=now, output_root=output)
        with pytest.raises(OSError, match="synthetic interruption"):
            activate(artifact_sha256=rendered["sha256"], installation_sha256=installed["installation_record_digest"], review_sha256=reviewed["review_sha256"], operator="Operator", operator_intent=OPERATOR_INTENT, now=now, output_root=output, repository_root=repository, failpoint="manifest")
        target = paths(output, repository)
        assert target.execution.read_bytes() == target.closed.read_bytes()
        assert not target.active.exists()
        assert json.loads(target.transaction.read_text())["state"] == "rolled_back"
        assert json.loads(target.closure.read_text())["authorization_closed"] is True
    finally:
        RENDERED_TMP.unlink(missing_ok=True)


def test_runbook_inventory_is_fixed_and_executable() -> None:
    runbook = (ROOT / "docs/experiments/suggest-moving-service-questions/v4-preflight-operator-runbook.md").read_text()
    scripts = set(re.findall(r"scripts/experiments/suggest_moving_service_questions/[A-Za-z0-9_.-]+", runbook))
    assert "--sequence" not in runbook and "--version" not in runbook
    for relative in scripts:
        path = ROOT / relative
        assert path.is_file() and path.stat().st_mode & 0o111


def test_same_shell_script_preserves_credential_boundary_and_traps() -> None:
    text = (SCRIPT / "run_v4_live_preflight_operator.zsh").read_text()
    assert 'read -s "GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY?OpenAI evaluation key: "' in text
    assert OPERATOR_INTENT in text
    assert "local exit_code=$?" in text and "local status=" not in text
    for signal, code in (("INT", 130), ("TERM", 143), ("HUP", 129)): assert f"trap 'exit {code}' {signal}" in text
    assert text.count("unset GOTIME_MOVING_SERVICE_EVAL_") == 3
    launcher = (SCRIPT / "run_openai_stage_b_v4_sequence_1_preflight_docker.sh").read_text()
    assert "--env GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY" in launcher
    assert "${GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY}" not in launcher


def test_backend_frontend_have_no_v4_preflight_reachability() -> None:
    for root in (ROOT / "backend/app", ROOT / "frontend/src"):
        for path in root.rglob("*"):
            if path.is_file(): assert "moving-service-stage-b-v4-pilot-20260808" not in path.read_text(errors="ignore")


def _stubbed_operator(*, launcher_status: int = 0, signal_name: str | None = None,
                      closure_status: int = 0):
    if shutil.which("zsh") is None: raise SkipTest("zsh is required")
    with tempfile.TemporaryDirectory(prefix="gotime-v4-preflight-shell-") as directory:
        root = Path(directory); operator = SCRIPT / "run_v4_live_preflight_operator.zsh"
        copied = root / "scripts/experiments/suggest_moving_service_questions" / operator.name
        copied.parent.mkdir(parents=True); copied.write_bytes(operator.read_bytes()); copied.chmod(0o755)
        bin_path = root / "bin"; bin_path.mkdir(); log = root / "calls.log"
        action = f"kill -{signal_name} $PPID; exit 99" if signal_name else (
            'test "$GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY" = synthetic-v4-secret || exit 88; '
            'test "$GOTIME_MOVING_SERVICE_EVAL_ENABLED" = 1 || exit 88; '
            f'test "$GOTIME_MOVING_SERVICE_EVAL_OPERATOR_INTENT" = {OPERATOR_INTENT} || exit 88; exit {launcher_status}'
        )
        stub = bin_path / "sh"
        stub.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$v4_CALL_LOG"\ncase "$*" in\n*verify*) exit 0;;\n*run_openai*) ' + action + f';;\n*close*) exit {closure_status};;\nesac\nexit 0\n'); stub.chmod(0o755)
        read_fd, write_fd = os.pipe(); os.write(write_fd, b"synthetic-v4-secret\n"); os.close(write_fd)
        environment = os.environ.copy(); environment.update({"PATH": f"{bin_path}:{environment['PATH']}", "GOTIME_V4_SEQUENCE_1_PREFLIGHT_OFFLINE_TEST": "1", "GOTIME_V4_SEQUENCE_1_PREFLIGHT_SYNTHETIC_INPUT_FD": str(read_fd), "v4_CALL_LOG": str(log)})
        result = subprocess.run(["zsh", str(copied)], cwd=root, env=environment, pass_fds=(read_fd,), text=True, capture_output=True, timeout=20); os.close(read_fd)
        return result, log.read_text()


def test_same_shell_success_failure_signals_and_closure_failure() -> None:
    success, calls = _stubbed_operator(); assert success.returncode == 0; assert "synthetic-v4-secret" not in success.stdout + success.stderr; assert "--reason success" in calls
    failure, calls = _stubbed_operator(launcher_status=9); assert failure.returncode == 9; assert "bounded_failure" in calls
    for signal, code in (("INT", 130), ("TERM", 143), ("HUP", 129)):
        result, calls = _stubbed_operator(signal_name=signal); assert result.returncode == code; assert "bounded_failure" in calls; assert "synthetic-v4-secret" not in result.stdout + result.stderr
    result, calls = _stubbed_operator(closure_status=17); assert result.returncode == 17; assert "--reason success" in calls and "bounded_failure" in calls
