"""Negative tests for assertion-backed sequence-4 generation rehearsal output."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from v2_sequence_4_generation_rehearsal_assertions import (
    ASSERTION_BACKED_SUMMARY_FIELDS,
    PROSE_CODES,
    RehearsalAssertionError,
    assert_rehearsal_scenario,
)


ROOT = Path(__file__).resolve().parents[3]
PREFIX = "004-storage_unknown-generation"


def _write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def _scenario(tmp_path: Path, scenario: str) -> tuple[Path, Path, dict]:
    repository = tmp_path / "repository"
    pilot = repository / "docs/experiments/suggest-moving-service-questions/v2-pilot"
    pilot.mkdir(parents=True)
    closed = ROOT / "docs/experiments/suggest-moving-service-questions/v2-pilot/closed-execution-manifest.json"
    (pilot / "closed-execution-manifest.json").write_bytes(closed.read_bytes())
    (pilot / "execution-manifest.json").write_bytes(closed.read_bytes())
    state = tmp_path / "state"
    audit = {
        "sequence": 4, "phase": "generation", "preflight_attempted": False,
        "generation_attempted": True, "generation_request_count": 1,
        "automatic_retries": 0, "authorization_consumed": True,
        "pydantic_validation_succeeded": scenario != "structural_failure",
        "semantic_validation_succeeded": scenario in {"compliant", "prose_rejection"},
        "prose_validation_succeeded": scenario == "compliant",
        "validation_outcome": {
            "compliant": "validated", "prose_rejection": "prose_failure",
            "structural_failure": "structural_failure", "semantic_failure": "semantic_failure",
        }[scenario],
        "prose_violation_codes": list(PROSE_CODES) if scenario == "prose_rejection" else [],
        "complete_response_rejected": scenario != "compliant",
        "partial_salvage_used": False,
        "fallback_used": scenario != "compliant",
        "fallback_version": None if scenario == "compliant" else "moving-service-fallback-v2",
        "fallback_question_id": None if scenario == "compliant" else "fallback-temporary-storage-v2",
        "response_evidence_sha256": "a" * 64 if scenario == "compliant" else None,
    }
    _write(state / f"{PREFIX}-audit.json", audit)
    _write(state / f"{PREFIX}-closure.json", {"authorization_closed": True})
    _write(state / f"{PREFIX}-activation-transaction.json", {"state": "rolled_back"})
    (state / ".second-use-rejected").touch()
    (state / ".network-disabled").touch()
    if scenario == "compliant":
        _write(state / f"{PREFIX}-grounding-review.json", {"decision": "approve"})
        _write(state / f"{PREFIX}-evidence-deletion.json", {
            "run_series_id": "moving-service-stage-b-v2-pilot-20260802",
            "sequence": 4, "fixture_id": "storage_unknown",
            "evidence_path_identifier": f"{PREFIX}-validated-response.json",
            "response_evidence_digest": "a" * 64,
            "deletion_reason": "review_signoff", "review_decision": "approve",
            "deleted_at": "2030-01-01T00:00:00Z",
            "deletion_completed": True, "contains_response_content": False,
        })
    return state, repository, audit


@pytest.mark.parametrize(("scenario", "mutation"), [
    ("prose_rejection", lambda audit: audit["prose_violation_codes"].pop()),
    ("prose_rejection", lambda audit: audit.update(prose_violation_codes=list(reversed(PROSE_CODES)))),
    ("prose_rejection", lambda audit: audit.update(fallback_question_id="wrong")),
    ("prose_rejection", lambda audit: audit.update(fallback_version="wrong")),
    ("compliant", lambda audit: audit.update(pydantic_validation_succeeded=False)),
    ("compliant", lambda audit: audit.update(semantic_validation_succeeded=False)),
    ("compliant", lambda audit: audit.update(response_evidence_sha256=None)),
    ("structural_failure", lambda audit: audit.update(validation_outcome="semantic_failure")),
    ("semantic_failure", lambda audit: audit.update(validation_outcome="structural_failure")),
])
def test_mutated_audit_fails_scenario_assertions(tmp_path, scenario, mutation) -> None:
    state, repository, audit = _scenario(tmp_path, scenario)
    mutation(audit)
    _write(state / f"{PREFIX}-audit.json", audit)
    with pytest.raises(RehearsalAssertionError):
        assert_rehearsal_scenario(state_root=state, repository_root=repository, scenario=scenario)


def test_unexpected_or_missing_response_evidence_fails(tmp_path) -> None:
    state, repository, audit = _scenario(tmp_path / "rejected", "prose_rejection")
    (state / f"{PREFIX}-validated-response.json").write_text("{}\n")
    with pytest.raises(RehearsalAssertionError):
        assert_rehearsal_scenario(state_root=state, repository_root=repository, scenario="prose_rejection")
    state, repository, audit = _scenario(tmp_path / "compliant", "compliant")
    (state / f"{PREFIX}-evidence-deletion.json").unlink()
    with pytest.raises(RehearsalAssertionError):
        assert_rehearsal_scenario(state_root=state, repository_root=repository, scenario="compliant")


@pytest.mark.parametrize("missing", ["closure", "second-use"])
def test_incomplete_lifecycle_fails(tmp_path, missing) -> None:
    state, repository, audit = _scenario(tmp_path, "semantic_failure")
    target = state / (f"{PREFIX}-closure.json" if missing == "closure" else ".second-use-rejected")
    target.unlink()
    with pytest.raises((RehearsalAssertionError, FileNotFoundError)):
        assert_rehearsal_scenario(state_root=state, repository_root=repository, scenario="semantic_failure")


def _assert_script_contract(script: str) -> None:
    if "run_scenario semantic_failure" not in script:
        raise AssertionError("semantic scenario is not independently exercised")
    printed = set(re.findall(r"echo '([a-z0-9_]+)=", script))
    if printed != ASSERTION_BACKED_SUMMARY_FIELDS:
        raise AssertionError("printed summary contains an unbacked or missing claim")
    if "assert-rehearsal --scenario \"$scenario\"" not in script:
        raise AssertionError("scenario output is not assertion-checked")


def test_semantic_scenario_and_every_printed_claim_are_assertion_backed() -> None:
    script = (ROOT / "scripts/experiments/suggest_moving_service_questions/rehearse_v2_sequence_4_generation_workflow.sh").read_text()
    _assert_script_contract(script)


def test_omitted_semantic_scenario_fails_script_contract() -> None:
    script = (ROOT / "scripts/experiments/suggest_moving_service_questions/rehearse_v2_sequence_4_generation_workflow.sh").read_text()
    with pytest.raises(AssertionError, match="semantic scenario"):
        _assert_script_contract(script.replace("run_scenario semantic_failure\n", ""))


def test_unbacked_printed_success_claim_fails_script_contract() -> None:
    script = (ROOT / "scripts/experiments/suggest_moving_service_questions/rehearse_v2_sequence_4_generation_workflow.sh").read_text()
    with pytest.raises(AssertionError, match="unbacked"):
        _assert_script_contract(script + "\necho 'unsupported_success=true'\n")
