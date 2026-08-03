"""Network-disabled tests for inactive v2 phase-candidate rendering."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
import tomllib
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

SCRIPT_ROOT = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_ROOT.parents[2] / "backend"
for value in (SCRIPT_ROOT, BACKEND_ROOT):
    if str(value) not in sys.path:
        sys.path.insert(0, str(value))

from run_openai_stage_b_v2_pilot import _fingerprint, prepare_frozen_v2_pilot  # noqa: E402
from run_openai_stage_b_v2_two_gate import frozen_binding_identity  # noqa: E402
from v2_phase_authorization_candidates import (  # noqa: E402
    MANIFEST_PATH, PHASE_PATHS, UMBRELLA_DIGEST, V2PhaseCandidateError,
    load_inactive_phase_candidate, render_generation_candidate,
    render_preflight_candidate, validate_inactive_phase_candidate,
)
from v2_two_gate_authorization import V2TwoGateAuthorizationError, validate_phase_authorization  # noqa: E402

NOW = datetime(2030, 1, 1, 12, 5, tzinfo=timezone.utc)
APPROVED = "2030-01-01T12:00:00Z"
ACTIVATED = "2030-01-01T12:04:00Z"
EXPIRES = "2030-01-01T12:15:00Z"


def candidate(phase: str) -> dict[str, object]:
    return tomllib.loads(PHASE_PATHS[phase].read_text(encoding="utf-8"))


def evidence_files(tmp_path: Path, **changes) -> tuple[Path, Path]:
    prepared = prepare_frozen_v2_pilot()
    request_digest = hashlib.sha256(
        prepared.provider_request.deterministic_request_json.encode("utf-8")
    ).hexdigest()
    attempt_digest = _fingerprint(prepared)
    evidence = {
        "run_series_id": "moving-service-stage-b-v2-pilot-20260802", "sequence": 1,
        "fixture_id": "storage_unknown", "phase": "preflight",
        **frozen_binding_identity(prepared), "deterministic_request_digest": request_digest,
        "canonical_attempt_digest": attempt_digest, "provider_preflight_fingerprint": attempt_digest,
        "input_tokens": 2176, "conservative_maximum_generation_cost": "0.0016704",
        "review_deadline": "2030-01-01T12:20:00Z", "consumed": False,
        "human_review_status": "pending",
    }
    evidence.update(changes)
    evidence_path = tmp_path / "evidence.json"
    evidence_path.write_text(json.dumps(evidence, sort_keys=True) + "\n", encoding="utf-8")
    evidence_digest = hashlib.sha256(evidence_path.read_bytes()).hexdigest()
    review = {
        "run_series_id": "moving-service-stage-b-v2-pilot-20260802", "sequence": 1,
        "fixture_id": "storage_unknown", "phase": "preflight_review",
        "review_status": "approved", "reviewer": "Human Reviewer",
        "reviewed_at": "2030-01-01T12:03:00Z", "token_count_plausible": True,
        "spend_within_ceiling": True, "frozen_bindings_match": True,
        "evidence_fresh_and_unused": True, "preflight_evidence_digest": evidence_digest,
    }
    review_path = tmp_path / "review.json"
    review_path.write_text(json.dumps(review, sort_keys=True) + "\n", encoding="utf-8")
    return evidence_path, review_path


def test_phase_package_loads_inactive_non_authoritative_candidates() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text())
    assert manifest["umbrella_candidate_digest"] == UMBRELLA_DIGEST
    for phase in ("preflight", "generation"):
        verified = load_inactive_phase_candidate(phase)
        assert verified.digest == hashlib.sha256(verified.path.read_bytes()).hexdigest()
        assert verified.artifact["metadata"]["valid_for_execution"] is False
        assert set(verified.artifact["authorization"].values()) == {False}
        assert "APPROVER_ID_REQUIRED" in verified.unresolved_placeholders


@pytest.mark.parametrize("phase", ["preflight", "generation"])
def test_inactive_candidate_cannot_satisfy_active_validator(phase: str) -> None:
    verified = load_inactive_phase_candidate(phase)
    with pytest.raises(V2TwoGateAuthorizationError):
        validate_phase_authorization(
            verified.artifact, digest=verified.digest, phase=phase, now=NOW,
            expected_bindings=frozen_binding_identity(prepare_frozen_v2_pilot()),
        )


@pytest.mark.parametrize(
    ("phase", "section", "field", "value"),
    [
        ("preflight", "scope", "run_series_id", "wrong"),
        ("preflight", "scope", "sequence", 2),
        ("preflight", "scope", "fixture_id", "complete"),
        ("preflight", "bindings", "provider", "Other"),
        ("preflight", "bindings", "ai_model_identifier", "other"),
        ("preflight", "bindings", "sdk_pin", "openai==0"),
        ("preflight", "bindings", "prompt_version", "moving-service-questions-prompt-v1"),
        ("preflight", "bindings", "umbrella_candidate_digest", "0" * 64),
        ("preflight", "scope", "maximum_token_preflight_requests", 2),
        ("generation", "scope", "maximum_ai_generation_requests", 2),
        ("generation", "scope", "automatic_retries", 1),
        ("generation", "scope", "maximum_total_spend_usd", "0.04"),
        ("preflight", "proposed_authorization", "ai_generation_authorized", True),
        ("generation", "proposed_authorization", "token_preflight_authorized", True),
        ("generation", "proposed_authorization", "stage_c_authorized", True),
        ("generation", "proposed_authorization", "formal_evaluation_authorized", True),
        ("generation", "proposed_authorization", "production_use_authorized", True),
    ],
)
def test_candidate_rejects_drift(phase: str, section: str, field: str, value: object) -> None:
    changed = copy.deepcopy(candidate(phase))
    changed[section][field] = value  # type: ignore[index]
    with pytest.raises(V2PhaseCandidateError):
        validate_inactive_phase_candidate(changed, phase=phase)


def test_unknown_phase_and_unknown_field_are_rejected() -> None:
    with pytest.raises(V2PhaseCandidateError, match="Unknown"):
        load_inactive_phase_candidate("both")
    changed = candidate("preflight")
    changed["scope"]["unknown"] = True  # type: ignore[index]
    with pytest.raises(V2PhaseCandidateError):
        validate_inactive_phase_candidate(changed, phase="preflight")


@pytest.mark.parametrize(
    ("approver", "approved", "activated", "expires", "reason", "message"),
    [
        ("APPROVER_ID_REQUIRED", APPROVED, ACTIVATED, EXPIRES, "reason", "approver"),
        ("Reviewer", "APPROVED_AT_UTC_REQUIRED", ACTIVATED, EXPIRES, "reason", "whole-second"),
        ("Reviewer", APPROVED, ACTIVATED, EXPIRES, "AUTHORIZATION_REASON_REQUIRED", "reason"),
        ("Reviewer", APPROVED, "2030-01-01T12:00:00", EXPIRES, "reason", "UTC"),
        ("Reviewer", APPROVED, ACTIVATED, "2030-01-01T12:19:01Z", "reason", "exceeds"),
        ("Reviewer", APPROVED, ACTIVATED, "2030-01-01T12:04:59Z", "reason", "expired"),
        ("Reviewer", "2030-01-01T12:06:00Z", "2030-01-01T12:06:00Z", EXPIRES, "reason", "future"),
    ],
)
def test_preflight_rendering_rejects_unresolved_or_invalid_values(
    tmp_path: Path, approver: str, approved: str, activated: str, expires: str,
    reason: str, message: str,
) -> None:
    with pytest.raises(V2PhaseCandidateError, match=message):
        render_preflight_candidate(
            output_path=tmp_path / "active.toml", approver=approver, approved_at=approved,
            activated_at=activated, expires_at=expires, authorization_reason=reason, now=NOW,
        )


def test_preflight_dry_run_renders_only_to_new_tmp_file(tmp_path: Path) -> None:
    rendered = render_preflight_candidate(
        output_path=tmp_path / "preflight.toml", approver="Human Reviewer",
        approved_at=APPROVED, activated_at=ACTIVATED, expires_at=EXPIRES,
        authorization_reason="One reviewed preflight", now=NOW,
    )
    assert rendered.path.stat().st_mode & 0o777 == 0o600
    assert rendered.artifact["authorization"]["ai_generation_authorized"] is False
    assert rendered.artifact["scope"]["maximum_ai_generation_requests"] == 0
    with pytest.raises(V2PhaseCandidateError, match="new file"):
        render_preflight_candidate(
            output_path=rendered.path, approver="Human Reviewer", approved_at=APPROVED,
            activated_at=ACTIVATED, expires_at=EXPIRES,
            authorization_reason="One reviewed preflight", now=NOW,
        )


def test_generation_dry_run_requires_and_binds_approved_evidence(tmp_path: Path) -> None:
    evidence_path, review_path = evidence_files(tmp_path)
    rendered = render_generation_candidate(
        output_path=tmp_path / "generation.toml", evidence_path=evidence_path,
        review_path=review_path, approver="Generation Approver", approved_at=ACTIVATED,
        activated_at="2030-01-01T12:05:00Z", expires_at="2030-01-01T12:15:00Z",
        authorization_reason="One reviewed generation", now=NOW,
    )
    binding = rendered.artifact["evidence_binding"]
    assert binding["preflight_evidence_digest"] == hashlib.sha256(evidence_path.read_bytes()).hexdigest()
    assert binding["preflight_review_digest"] == hashlib.sha256(review_path.read_bytes()).hexdigest()
    assert rendered.artifact["authorization"]["token_preflight_authorized"] is False
    assert rendered.artifact["scope"]["maximum_token_preflight_requests"] == 0


@pytest.mark.parametrize(
    ("evidence_changes", "review_change", "message"),
    [
        ({"consumed": True}, None, "consumed"),
        ({"review_deadline": "2030-01-01T12:04:00Z"}, None, "expired"),
        ({"run_series_id": "wrong"}, None, "binding"),
        ({"input_tokens": 0}, None, "token"),
        ({"conservative_maximum_generation_cost": "0.04"}, None, "ceiling"),
        ({"deterministic_request_digest": "bad"}, None, "request_digest"),
        ({}, ("review_status", "rejected"), "Approved"),
        ({}, ("evidence_fresh_and_unused", False), "bounded check"),
    ],
)
def test_generation_rendering_rejects_bad_evidence_or_review(
    tmp_path: Path, evidence_changes: dict[str, object], review_change, message: str,
) -> None:
    evidence_path, review_path = evidence_files(tmp_path, **evidence_changes)
    if review_change:
        review = json.loads(review_path.read_text())
        review[review_change[0]] = review_change[1]
        review_path.write_text(json.dumps(review, sort_keys=True) + "\n")
    with pytest.raises(V2PhaseCandidateError, match=message):
        render_generation_candidate(
            output_path=tmp_path / "generation.toml", evidence_path=evidence_path,
            review_path=review_path, approver="Generation Approver", approved_at=ACTIVATED,
            activated_at="2030-01-01T12:05:00Z", expires_at="2030-01-01T12:15:00Z",
            authorization_reason="One reviewed generation", now=NOW,
        )


def test_generation_approval_cannot_predate_review(tmp_path: Path) -> None:
    evidence_path, review_path = evidence_files(tmp_path)
    with pytest.raises(V2PhaseCandidateError, match="predates"):
        render_generation_candidate(
            output_path=tmp_path / "generation.toml", evidence_path=evidence_path,
            review_path=review_path, approver="Generation Approver",
            approved_at="2030-01-01T12:02:00Z", activated_at=ACTIVATED,
            expires_at=EXPIRES, authorization_reason="One reviewed generation", now=NOW,
        )


def test_renderers_do_not_inspect_environment_or_replace_closed_state(tmp_path: Path) -> None:
    source = (SCRIPT_ROOT / "v2_phase_authorization_candidates.py").read_text()
    assert "os.environ" not in source
    execution_manifest = SCRIPT_ROOT.parents[2] / (
        "docs/experiments/suggest-moving-service-questions/v2-pilot/execution-manifest.json"
    )
    before = execution_manifest.read_bytes()
    render_preflight_candidate(
        output_path=tmp_path / "preflight.toml", approver="Human Reviewer",
        approved_at=APPROVED, activated_at=ACTIVATED, expires_at=EXPIRES,
        authorization_reason="One reviewed preflight", now=NOW,
    )
    assert execution_manifest.read_bytes() == before


def test_cross_version_and_cross_phase_shapes_fail_closed() -> None:
    preflight = candidate("preflight")
    with pytest.raises(V2PhaseCandidateError):
        validate_inactive_phase_candidate(preflight, phase="generation")
    changed = candidate("generation")
    changed["bindings"]["prompt_version"] = "moving-service-questions-prompt-v1"  # type: ignore[index]
    with pytest.raises(V2PhaseCandidateError):
        validate_inactive_phase_candidate(changed, phase="generation")
