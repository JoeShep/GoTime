"""Network-disabled tests for separate v2 preflight and generation gates."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest

SCRIPT_ROOT = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_ROOT.parents[2] / "backend"
for value in (SCRIPT_ROOT, BACKEND_ROOT):
    if str(value) not in sys.path:
        sys.path.insert(0, str(value))

from run_openai_stage_b_v2_pilot import (  # noqa: E402
    CREDENTIAL_NAME, ENABLEMENT_NAME, PreparedV2Pilot, V2FollowUpPilotError,
    _fingerprint, prepare_frozen_v2_pilot,
)
from run_openai_stage_b_v2_two_gate import (  # noqa: E402
    close_two_gate_phase_offline,
    GENERATION_INTENT, PREFLIGHT_INTENT, execute_v2_generation_offline,
    execute_v2_preflight_offline, frozen_binding_identity, phase_paths,
    review_v2_preflight_evidence, run_v2_generation_phase, run_v2_preflight_phase,
)
from real_model_adapter import MovingServiceTransportResult, TransportErrorClassification  # noqa: E402
from test_openai_stage_b_v2_pilot import (  # noqa: E402
    FakeTransport, rejected_stage_b_response, valid_response,
)
from v2_two_gate_authorization import (  # noqa: E402
    V2TwoGateAuthorizationError, VerifiedV2PhaseAuthorization,
    validate_phase_authorization,
)
from v2_follow_up_lifecycle import finalize_v2_human_review  # noqa: E402


NOW = datetime(2030, 1, 1, 12, tzinfo=timezone.utc)


class ExplodingEnvironment(dict):
    def get(self, key, default=None):
        raise AssertionError("closed phase inspected environment")
    def __contains__(self, key):
        raise AssertionError("closed phase inspected environment")


def phase_artifact(phase: str, prepared: PreparedV2Pilot, **evidence) -> dict[str, object]:
    return {
        "metadata": {
            "capability": "suggest_moving_service_questions",
            "authorization_version": "moving-service-openai-v2-two-gate-authorization-v1",
            "authorization_status": f"approved_v2_{phase}", "phase": phase,
            "evaluation_only": True, "active_repository_authority": True,
        },
        "bindings": frozen_binding_identity(prepared),
        "authorization": {
            "credential_access_authorized": True,
            "token_preflight_authorized": phase == "preflight",
            "ai_generation_authorized": phase == "generation",
            "formal_evaluation_authorized": False, "stage_c_authorized": False,
            "production_use_authorized": False,
        },
        "scope": {
            "run_series_id": "moving-service-stage-b-v2-pilot-20260802", "sequence": 1,
            "fixture_id": "storage_unknown", "maximum_credential_reads": 1,
            "maximum_client_constructions": 1,
            "maximum_token_preflight_requests": 1 if phase == "preflight" else 0,
            "maximum_ai_generation_requests": 0 if phase == "preflight" else 1,
            "automatic_retries": 0, "maximum_total_spend_usd": "0.03", "single_use": True,
        },
        "approval": {
            "approver": "Offline Reviewer",
            "approved_at": (
                "2030-01-01T12:00:03Z" if phase == "generation" else "2030-01-01T12:00:00Z"
            ),
            "activated_at": (
                "2030-01-01T12:00:03Z" if phase == "generation" else "2030-01-01T12:00:00Z"
            ),
            "expires_at": (
                "2030-01-01T12:15:03Z" if phase == "generation" else "2030-01-01T12:15:00Z"
            ),
            "maximum_duration_seconds": 900,
            "authorization_reason": "Offline phase-boundary test",
        },
        "evidence_binding": evidence or {
            "preflight_evidence_digest": "not_applicable",
            "preflight_review_digest": "not_applicable", "input_tokens": 0,
            "conservative_cost": "0.00",
            "request_digest": "not_applicable", "canonical_attempt_digest": "not_applicable",
            "provider_fingerprint": "not_applicable", "preflight_reviewer": "not_applicable",
            "preflight_reviewed_at": "not_applicable",
        },
    }


def verified_preflight(prepared: PreparedV2Pilot) -> VerifiedV2PhaseAuthorization:
    return validate_phase_authorization(
        phase_artifact("preflight", prepared), digest="a" * 64, phase="preflight",
        now=NOW + timedelta(seconds=1), expected_bindings=frozen_binding_identity(prepared),
    )


def create_preflight_and_review(tmp_path: Path, approved: bool = True):
    prepared = prepare_frozen_v2_pilot()
    transport = FakeTransport(valid_response(), _fingerprint(prepared))
    execute_v2_preflight_offline(
        authorization=verified_preflight(prepared),
        environment={ENABLEMENT_NAME: "1", CREDENTIAL_NAME: "synthetic"},
        operator_intent=PREFLIGHT_INTENT, output_root=tmp_path,
        client_constructor=lambda _: object(), transport_factory=lambda *_: transport,
        closure=lambda: True, now=NOW + timedelta(seconds=2),
    )
    review_v2_preflight_evidence(
        output_root=tmp_path, approved=approved, reviewer="Offline Reviewer",
        token_count_plausible=True, spend_within_ceiling=True,
        frozen_bindings_match=True, evidence_fresh_and_unused=True,
        notes="Bounded.", now=NOW + timedelta(seconds=3),
    )
    paths = phase_paths(tmp_path)
    persisted_evidence = json.loads(paths["preflight_evidence"].read_text())
    evidence_digest = hashlib.sha256(paths["preflight_evidence"].read_bytes()).hexdigest()
    review_digest = hashlib.sha256(paths["preflight_review"].read_bytes()).hexdigest()
    generation = validate_phase_authorization(
        phase_artifact(
            "generation", prepared,
            preflight_evidence_digest=evidence_digest,
            preflight_review_digest=review_digest,
            input_tokens=2176, conservative_cost="0.0016704",
            request_digest=persisted_evidence["deterministic_request_digest"],
            canonical_attempt_digest=persisted_evidence["canonical_attempt_digest"],
            provider_fingerprint=persisted_evidence["provider_preflight_fingerprint"],
            preflight_reviewer="Offline Reviewer",
            preflight_reviewed_at="2030-01-01T12:00:03Z",
        ), digest="b" * 64, phase="generation", now=NOW + timedelta(seconds=4),
        expected_bindings=frozen_binding_identity(prepared),
    )
    return prepared, transport, generation, paths


def test_closed_repository_blocks_both_phases_before_environment() -> None:
    with pytest.raises(V2FollowUpPilotError, match="repository_authorization_closed"):
        run_v2_preflight_phase(environment=ExplodingEnvironment(), operator_intent=PREFLIGHT_INTENT)
    with pytest.raises(V2FollowUpPilotError, match="repository_authorization_closed"):
        run_v2_generation_phase(environment=ExplodingEnvironment(), operator_intent=GENERATION_INTENT)


def test_phase_authorizations_are_mutually_exclusive() -> None:
    prepared = prepare_frozen_v2_pilot()
    with pytest.raises(V2TwoGateAuthorizationError):
        validate_phase_authorization(
            phase_artifact("preflight", prepared), digest="a" * 64, phase="generation",
            now=NOW + timedelta(seconds=1), expected_bindings=frozen_binding_identity(prepared),
        )


def test_phase_authorization_expiration_fails_closed() -> None:
    prepared = prepare_frozen_v2_pilot()
    with pytest.raises(V2TwoGateAuthorizationError, match="expired"):
        validate_phase_authorization(
            phase_artifact("preflight", prepared), digest="a" * 64, phase="preflight",
            now=NOW + timedelta(minutes=20), expected_bindings=frozen_binding_identity(prepared),
        )
    evidence = dict(preflight_evidence_digest="a" * 64, preflight_review_digest="b" * 64,
        input_tokens=1, conservative_cost="0.01", request_digest="c" * 64,
        canonical_attempt_digest="d" * 64, provider_fingerprint="e" * 64,
        preflight_reviewer="Reviewer", preflight_reviewed_at="2030-01-01T12:00:00Z")
    changed = phase_artifact("generation", prepared, **evidence)
    changed["authorization"]["token_preflight_authorized"] = True  # type: ignore[index]
    with pytest.raises(V2TwoGateAuthorizationError):
        validate_phase_authorization(changed, digest="b" * 64, phase="generation", now=NOW,
            expected_bindings=frozen_binding_identity(prepared))
    generation = validate_phase_authorization(
        phase_artifact("generation", prepared, **evidence),
        digest="b" * 64, phase="generation", now=NOW + timedelta(seconds=4),
        expected_bindings=frozen_binding_identity(prepared),
    )
    with pytest.raises(V2FollowUpPilotError, match="preflight_authorization_rejected"):
        execute_v2_preflight_offline(
            authorization=generation, environment=ExplodingEnvironment(), operator_intent=PREFLIGHT_INTENT,
            output_root=Path("/tmp/not-used"), client_constructor=lambda _: object(),
            transport_factory=lambda *_: None, closure=lambda: True, now=NOW,
        )


def test_preflight_writes_bounded_immutable_evidence_and_never_generates(tmp_path) -> None:
    prepared = prepare_frozen_v2_pilot()
    transport = FakeTransport(valid_response(), _fingerprint(prepared))
    state = execute_v2_preflight_offline(
        authorization=verified_preflight(prepared),
        environment={ENABLEMENT_NAME: "1", CREDENTIAL_NAME: "synthetic"},
        operator_intent=PREFLIGHT_INTENT, output_root=tmp_path,
        client_constructor=lambda _: object(), transport_factory=lambda *_: transport,
        closure=lambda: True, now=NOW,
    )
    assert state["preflight_succeeded"] is True
    assert transport.preflight_calls == 1 and transport.generation_calls == 0
    paths = phase_paths(tmp_path)
    evidence_text = paths["preflight_evidence"].read_text()
    for prohibited in ("synthetic", "system_instructions", "trusted_state", "authorization_header"):
        assert prohibited not in evidence_text
    with pytest.raises(FileExistsError):
        execute_v2_preflight_offline(
            authorization=verified_preflight(prepared), environment={}, operator_intent=PREFLIGHT_INTENT,
            output_root=tmp_path, client_constructor=lambda _: object(), transport_factory=lambda *_: transport,
            closure=lambda: True, now=NOW,
        )


def test_generation_requires_approved_exact_fresh_evidence_and_never_preflights(tmp_path) -> None:
    prepared, transport, authorization, paths = create_preflight_and_review(tmp_path)
    state = execute_v2_generation_offline(
        authorization=authorization,
        environment={ENABLEMENT_NAME: "1", CREDENTIAL_NAME: "synthetic"},
        operator_intent=GENERATION_INTENT, output_root=tmp_path,
        client_constructor=lambda _: object(), transport_factory=lambda *_: transport,
        closure=lambda: True, now=NOW + timedelta(seconds=5),
    )
    assert state["generation_succeeded"] is True
    assert transport.preflight_calls == 1 and transport.generation_calls == 1
    assert paths["preflight_consumption"].exists()
    assert paths["response_evidence"].exists()
    with pytest.raises(V2FollowUpPilotError, match="consumed"):
        execute_v2_generation_offline(
            authorization=authorization, environment={}, operator_intent=GENERATION_INTENT,
            output_root=tmp_path, client_constructor=lambda _: object(), transport_factory=lambda *_: transport,
            closure=lambda: True, now=NOW + timedelta(seconds=6),
        )


def test_generation_success_reaches_bounded_grounding_review_and_deletion(tmp_path) -> None:
    prepared, transport, authorization, paths = create_preflight_and_review(tmp_path)
    execute_v2_generation_offline(
        authorization=authorization,
        environment={ENABLEMENT_NAME: "1", CREDENTIAL_NAME: "synthetic"},
        operator_intent=GENERATION_INTENT, output_root=tmp_path,
        client_constructor=lambda _: object(), transport_factory=lambda *_: transport,
        closure=lambda: True, now=NOW + timedelta(seconds=5),
    )
    review = finalize_v2_human_review(
        output_root=tmp_path, now=NOW + timedelta(seconds=6),
        review={
            "human_review_status": "approved", "grounding_supported": True,
            "invented_user_fact_present": False, "scope_overstatement_present": False,
            "provider_or_service_recommendation_present": False,
            "storage_required_claim_present": False, "clarity_score": 5,
            "usefulness_score": 5, "fallback_comparison": "slightly_better",
            "reviewer": "Offline Reviewer", "bounded_review_notes": "Bounded.",
        },
    )
    assert review["human_review_status"] == "approved"
    assert not paths["response_evidence"].exists()


def test_rejected_review_and_missing_or_wrong_digest_block_generation(tmp_path) -> None:
    prepared, _, authorization, paths = create_preflight_and_review(tmp_path, approved=False)
    with pytest.raises(V2FollowUpPilotError, match="not_approved"):
        execute_v2_generation_offline(
            authorization=authorization, environment={}, operator_intent=GENERATION_INTENT,
            output_root=tmp_path, client_constructor=lambda _: object(), transport_factory=lambda *_: None,
            closure=lambda: True, now=NOW + timedelta(seconds=5),
        )


def test_wrong_evidence_or_review_digest_blocks_before_environment(tmp_path) -> None:
    _, _, authorization, paths = create_preflight_and_review(tmp_path)
    wrong_evidence = copy.copy(authorization)
    object.__setattr__(wrong_evidence, "evidence_digest", "0" * 64)
    with pytest.raises(V2FollowUpPilotError, match="evidence_digest_mismatch"):
        execute_v2_generation_offline(
            authorization=wrong_evidence, environment=ExplodingEnvironment(), operator_intent=GENERATION_INTENT,
            output_root=tmp_path, client_constructor=lambda _: object(), transport_factory=lambda *_: None,
            closure=lambda: True, now=NOW + timedelta(seconds=5),
        )
    wrong_review = copy.copy(authorization)
    object.__setattr__(wrong_review, "review_digest", "0" * 64)
    with pytest.raises(V2FollowUpPilotError, match="review_digest_mismatch"):
        execute_v2_generation_offline(
            authorization=wrong_review, environment=ExplodingEnvironment(), operator_intent=GENERATION_INTENT,
            output_root=tmp_path, client_constructor=lambda _: object(), transport_factory=lambda *_: None,
            closure=lambda: True, now=NOW + timedelta(seconds=5),
        )
    paths["preflight_review"].unlink()
    with pytest.raises(FileNotFoundError):
        execute_v2_generation_offline(
            authorization=authorization, environment={}, operator_intent=GENERATION_INTENT,
            output_root=tmp_path, client_constructor=lambda _: object(), transport_factory=lambda *_: None,
            closure=lambda: True, now=NOW + timedelta(seconds=5),
        )


def test_expired_or_mismatched_preflight_blocks_before_environment(tmp_path) -> None:
    prepared, _, authorization, paths = create_preflight_and_review(tmp_path)
    evidence = json.loads(paths["preflight_evidence"].read_text())
    evidence["review_deadline"] = "2030-01-01T11:59:59Z"
    paths["preflight_evidence"].write_text(json.dumps(evidence, sort_keys=True) + "\n")
    changed = copy.copy(authorization)
    evidence_digest = hashlib.sha256(paths["preflight_evidence"].read_bytes()).hexdigest()
    review = json.loads(paths["preflight_review"].read_text())
    review["preflight_evidence_digest"] = evidence_digest
    paths["preflight_review"].write_text(json.dumps(review, sort_keys=True) + "\n")
    object.__setattr__(changed, "evidence_digest", evidence_digest)
    object.__setattr__(changed, "review_digest", hashlib.sha256(paths["preflight_review"].read_bytes()).hexdigest())
    with pytest.raises(V2FollowUpPilotError, match="expired"):
        execute_v2_generation_offline(
            authorization=changed, environment=ExplodingEnvironment(), operator_intent=GENERATION_INTENT,
            output_root=tmp_path, client_constructor=lambda _: object(), transport_factory=lambda *_: None,
            closure=lambda: True, now=NOW + timedelta(seconds=5),
        )


@pytest.mark.parametrize(
    ("mutation", "classification"),
    [
        (lambda value: value.update(deterministic_request_digest="0" * 64), "binding_mismatch"),
        (lambda value: value.update(canonical_attempt_digest="0" * 64), "binding_mismatch"),
        (lambda value: value.update(prompt_digest="0" * 64), "binding_mismatch"),
    ],
)
def test_request_payload_or_frozen_binding_drift_blocks_generation(
    tmp_path, mutation, classification: str
) -> None:
    _, _, authorization, paths = create_preflight_and_review(tmp_path)
    evidence = json.loads(paths["preflight_evidence"].read_text())
    mutation(evidence)
    paths["preflight_evidence"].write_text(json.dumps(evidence, sort_keys=True) + "\n")
    evidence_digest = hashlib.sha256(paths["preflight_evidence"].read_bytes()).hexdigest()
    review = json.loads(paths["preflight_review"].read_text())
    review["preflight_evidence_digest"] = evidence_digest
    paths["preflight_review"].write_text(json.dumps(review, sort_keys=True) + "\n")
    changed = copy.copy(authorization)
    object.__setattr__(changed, "evidence_digest", evidence_digest)
    object.__setattr__(changed, "review_digest", hashlib.sha256(paths["preflight_review"].read_bytes()).hexdigest())
    with pytest.raises(V2FollowUpPilotError, match=classification):
        execute_v2_generation_offline(
            authorization=changed, environment=ExplodingEnvironment(), operator_intent=GENERATION_INTENT,
            output_root=tmp_path, client_constructor=lambda _: object(), transport_factory=lambda *_: None,
            closure=lambda: True, now=NOW + timedelta(seconds=5),
        )


def test_historical_prose_failure_records_all_codes_and_fallback(tmp_path) -> None:
    prepared, _, authorization, _ = create_preflight_and_review(tmp_path)
    transport = FakeTransport(rejected_stage_b_response(), _fingerprint(prepared))
    with pytest.raises(V2FollowUpPilotError, match="prose_validation_failure"):
        execute_v2_generation_offline(
            authorization=authorization,
            environment={ENABLEMENT_NAME: "1", CREDENTIAL_NAME: "synthetic"},
            operator_intent=GENERATION_INTENT, output_root=tmp_path,
            client_constructor=lambda _: object(), transport_factory=lambda *_: transport,
            closure=lambda: True, now=NOW + timedelta(seconds=5),
        )
    audit = json.loads(phase_paths(tmp_path)["generation_audit"].read_text())
    assert audit["prose_violation_codes"] == [
        "irrelevant_location_reference", "unsupported_home_or_property_assertion",
        "storage_modality_overstatement", "unsupported_service_selection_language",
        "grounding_summary_mismatch",
    ]
    assert audit["fallback_used"] is True
    assert audit["fallback_question_id"] == "fallback-temporary-storage-v2"
    assert not phase_paths(tmp_path)["response_evidence"].exists()


@pytest.mark.parametrize(
    ("mutation", "classification"),
    [
        (lambda response: response.update(extra="forbidden"), "pydantic_validation_failure"),
        (
            lambda response: response["suggestions"][0].update(
                selected_missing_information_category="packing_preference"
            ),
            "semantic_validation_failure",
        ),
    ],
)
def test_generation_validation_failures_remain_distinct(tmp_path, mutation, classification) -> None:
    prepared, _, authorization, _ = create_preflight_and_review(tmp_path)
    response = valid_response()
    mutation(response)
    transport = FakeTransport(response, _fingerprint(prepared))
    with pytest.raises(V2FollowUpPilotError, match=classification):
        execute_v2_generation_offline(
            authorization=authorization,
            environment={ENABLEMENT_NAME: "1", CREDENTIAL_NAME: "synthetic"},
            operator_intent=GENERATION_INTENT, output_root=tmp_path,
            client_constructor=lambda _: object(), transport_factory=lambda *_: transport,
            closure=lambda: True, now=NOW + timedelta(seconds=5),
        )
    audit = json.loads(phase_paths(tmp_path)["generation_audit"].read_text())
    assert audit["bounded_failure_classification"] == classification


def test_generation_failure_consumes_evidence_and_cannot_retry(tmp_path) -> None:
    prepared, _, authorization, paths = create_preflight_and_review(tmp_path)

    class FailedTransport(FakeTransport):
        def generate(self, request, preflight):
            self.generation_calls += 1
            return MovingServiceTransportResult(
                response_content=None, input_tokens=2176, duration_ms=5,
                error_classification=TransportErrorClassification.PROVIDER_UNAVAILABLE,
            )

    transport = FailedTransport(valid_response(), _fingerprint(prepared))
    with pytest.raises(V2FollowUpPilotError, match="provider_unavailable"):
        execute_v2_generation_offline(
            authorization=authorization,
            environment={ENABLEMENT_NAME: "1", CREDENTIAL_NAME: "synthetic"},
            operator_intent=GENERATION_INTENT, output_root=tmp_path,
            client_constructor=lambda _: object(), transport_factory=lambda *_: transport,
            closure=lambda: True, now=NOW + timedelta(seconds=5),
        )
    assert paths["preflight_consumption"].exists()
    assert transport.generation_calls == 1
    with pytest.raises(V2FollowUpPilotError, match="consumed"):
        execute_v2_generation_offline(
            authorization=authorization, environment=ExplodingEnvironment(),
            operator_intent=GENERATION_INTENT, output_root=tmp_path,
            client_constructor=lambda _: object(), transport_factory=lambda *_: transport,
            closure=lambda: True, now=NOW + timedelta(seconds=6),
        )


@pytest.mark.parametrize("phase", ["preflight", "generation"])
@pytest.mark.parametrize("reason", ["success", "bounded_failure", "expiration", "cancellation"])
def test_phase_closure_is_closed_and_idempotent(tmp_path, phase: str, reason: str) -> None:
    first = close_two_gate_phase_offline(phase=phase, reason=reason, output_root=tmp_path, now=NOW)
    second = close_two_gate_phase_offline(
        phase=phase, reason=reason, output_root=tmp_path, now=NOW + timedelta(seconds=1)
    )
    assert first == second
    assert first["authorization_closed"] is True
    assert first["token_preflight_authorized"] is False
    assert first["ai_generation_authorized"] is False


def test_cancelled_preflight_phase_permanently_blocks_generation(tmp_path) -> None:
    _, _, authorization, _ = create_preflight_and_review(tmp_path)
    close_two_gate_phase_offline(
        phase="preflight", reason="cancellation", output_root=tmp_path, now=NOW
    )
    with pytest.raises(V2FollowUpPilotError, match="permanently_closed"):
        execute_v2_generation_offline(
            authorization=authorization, environment=ExplodingEnvironment(),
            operator_intent=GENERATION_INTENT, output_root=tmp_path,
            client_constructor=lambda _: object(), transport_factory=lambda *_: None,
            closure=lambda: True, now=NOW + timedelta(seconds=5),
        )
