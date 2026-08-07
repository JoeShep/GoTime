"""Focused sequence-4 immediate preflight-evidence review tests."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from run_openai_stage_b_v2_pilot import prepare_frozen_v2_pilot
from run_openai_stage_b_v2_two_gate import frozen_binding_identity, phase_paths
from v2_sequence_4_preflight_evidence_review import (
    Sequence4EvidenceReviewError,
    review_sequence_4_preflight_evidence,
)

NOW = datetime(2030, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def _stamp(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _state(tmp_path: Path, *, deadline: datetime | None = None):
    output_root = tmp_path / "local"
    repository_root = tmp_path / "repository"
    pilot = repository_root / "docs/experiments/suggest-moving-service-questions/v2-pilot"
    pilot.mkdir(parents=True)
    closed = b'{"status":"closed_no_execution_authorized"}\n'
    (pilot / "closed-execution-manifest.json").write_bytes(closed)
    (pilot / "execution-manifest.json").write_bytes(closed)
    prepared = prepare_frozen_v2_pilot()
    paths = phase_paths(output_root, sequence=4)
    paths["preflight_evidence"].parent.mkdir(parents=True)
    evidence = {
        "run_series_id": "moving-service-stage-b-v2-pilot-20260802", "sequence": 4,
        "fixture_id": "storage_unknown", "phase": "preflight",
        **frozen_binding_identity(prepared),
        "deterministic_request_digest": "1" * 64,
        "canonical_attempt_digest": "2" * 64,
        "provider_preflight_fingerprint": "3" * 64,
        "maximum_output_tokens": 500, "temperature": 0,
        "token_preflight_timeout_seconds": 5, "ai_generation_timeout_seconds": 12,
        "automatic_retries": 0, "store": False, "stream": False,
        "background": False, "truncation": "disabled", "tools": [],
        "input_tokens": 2176, "cached_input_tokens": None, "uncached_input_tokens": None,
        "conservative_maximum_generation_cost": "0.0016704",
        "preflight_request_id": None, "duration_ms": 1.0,
        "created_at": _stamp(NOW), "review_deadline": _stamp(deadline or NOW + timedelta(minutes=15)),
        "authorization_digest": "4" * 64, "consumed": False, "human_review_status": "pending",
    }
    paths["preflight_evidence"].write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    paths["preflight_audit"].write_text("{}\n")
    paths["preflight_closure"].write_text("{}\n")
    digest = hashlib.sha256(paths["preflight_evidence"].read_bytes()).hexdigest()
    return output_root, repository_root, paths, digest


def _review(tmp_path: Path, *, decision="approve", now=NOW + timedelta(seconds=2), **overrides):
    output_root, repository_root, paths, digest = _state(tmp_path, deadline=overrides.pop("deadline", None))
    values = dict(evidence_sha256=digest, input_tokens=2176, conservative_cost="0.0016704",
        reviewer="Synthetic Reviewer", decision=decision, reviewed_at=_stamp(NOW + timedelta(seconds=1)),
        token_count_plausible=True, cost_within_limit=True, frozen_bindings_confirmed=True,
        evidence_history_confirmed=True, notes="Bounded synthetic review.", now=now,
        output_root=output_root, repository_root=repository_root)
    values.update(overrides)
    return review_sequence_4_preflight_evidence(**values), paths


@pytest.mark.parametrize("decision,eligible", [("approve", True), ("reject", False), ("request_changes", False)])
def test_bounded_decisions_are_append_only_and_non_authoritative(tmp_path: Path, decision: str, eligible: bool) -> None:
    result, paths = _review(tmp_path, decision=decision)
    record = json.loads(paths["preflight_review"].read_text())
    assert result["generation_gate_binding_eligible"] is eligible
    assert record["decision"] == decision and record["authoritative"] is False
    assert record["review_status"] == {"approve": "approved", "reject": "rejected",
                                       "request_changes": "request_changes"}[decision]
    assert record["generation_authorized"] is False
    assert set(("deterministic_request_digest", "canonical_attempt_digest", "provider_fingerprint")) <= set(record)
    assert paths["preflight_review"].stat().st_mode & 0o777 == 0o600


def test_late_approval_is_rejected_without_record(tmp_path: Path) -> None:
    output_root, repository_root, paths, digest = _state(tmp_path, deadline=NOW + timedelta(seconds=1))
    with pytest.raises(Sequence4EvidenceReviewError, match="late"):
        review_sequence_4_preflight_evidence(evidence_sha256=digest, input_tokens=2176,
            conservative_cost="0.0016704", reviewer="Reviewer", decision="approve",
            reviewed_at=_stamp(NOW + timedelta(seconds=1)), token_count_plausible=True,
            cost_within_limit=True, frozen_bindings_confirmed=True, evidence_history_confirmed=True,
            notes="Bounded.", now=NOW + timedelta(seconds=2), output_root=output_root,
            repository_root=repository_root)
    assert not paths["preflight_review"].exists()


@pytest.mark.parametrize("change", ["digest", "tokens", "cost", "sequence", "generation_scope"])
def test_binding_and_scope_drift_is_rejected(tmp_path: Path, change: str) -> None:
    output_root, repository_root, paths, digest = _state(tmp_path)
    arguments = dict(evidence_sha256=digest, input_tokens=2176, conservative_cost="0.0016704")
    if change == "digest": arguments["evidence_sha256"] = "0" * 64
    elif change == "tokens": arguments["input_tokens"] = 1
    elif change == "cost": arguments["conservative_cost"] = "0.02"
    else:
        evidence = json.loads(paths["preflight_evidence"].read_text())
        if change == "sequence": evidence["sequence"] = 3
        else: evidence["maximum_output_tokens"] = 501
        paths["preflight_evidence"].write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
        arguments["evidence_sha256"] = hashlib.sha256(paths["preflight_evidence"].read_bytes()).hexdigest()
    with pytest.raises(Sequence4EvidenceReviewError):
        review_sequence_4_preflight_evidence(**arguments, reviewer="Reviewer", decision="approve",
            reviewed_at=_stamp(NOW + timedelta(seconds=1)), token_count_plausible=True,
            cost_within_limit=True, frozen_bindings_confirmed=True, evidence_history_confirmed=True,
            notes="Bounded.", now=NOW + timedelta(seconds=2), output_root=output_root,
            repository_root=repository_root)
