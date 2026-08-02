"""Network-disabled tests for the isolated v2 follow-up-pilot boundary."""

from __future__ import annotations

import hashlib
import json
import pickle
import shutil
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest

SCRIPT_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = REPOSITORY_ROOT / "backend"
for import_path in (SCRIPT_ROOT, BACKEND_ROOT):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from app.moving_service_questions import STORAGE_KNOWLEDGE  # noqa: E402
from openai_transport import OpenAIPreflightResult  # noqa: E402
from real_model_adapter import MovingServiceTransportResult  # noqa: E402
from run_openai_stage_b_v2_pilot import (  # noqa: E402
    CREDENTIAL_NAME,
    DEFAULT_EXECUTION_MANIFEST,
    ENABLEMENT_NAME,
    FALLBACK_VERSION_V2,
    OPERATOR_INTENT,
    V2FollowUpPilotError,
    V2PreflightEvidence,
    _EVIDENCE_TOKEN,
    _fingerprint,
    _paths,
    execute_authorized_v2_pilot_offline,
    prepare_frozen_v2_pilot,
    run_v2_follow_up_pilot,
    run_v2_follow_up_pilot_with_injected_boundaries,
)
from v2_follow_up_authorization import (  # noqa: E402
    AUTHORIZATION_VERSION,
    FIXTURE_ID,
    RUN_SERIES_ID,
    SEQUENCE,
    VerifiedV2FollowUpAuthorization,
    V2FollowUpAuthorizationError,
    close_v2_follow_up_authorization,
    load_manifest_bound_v2_authorization,
)


def valid_response() -> dict[str, object]:
    return {
        "capability": "suggest_moving_service_questions",
        "prompt_version": "moving-service-questions-prompt-v2",
        "schema_version": "moving-service-questions-schema-v2",
        "suggestions": [
            {
                "question_id": "ai-temporary_storage_need-v2",
                "question": "Might you need temporary storage before final delivery?",
                "why_it_matters": "A possible storage need is relevant to services to request.",
                "information_it_would_clarify": "Whether storage may be needed",
                "affected_decision_id": "moving-service-model",
                "selected_missing_information_category": "temporary_storage_need",
                "relevant_knowledge_ids": [STORAGE_KNOWLEDGE.knowledge_id],
                "grounding_summary": STORAGE_KNOWLEDGE.statement,
                "reason_not_deterministic": "The user must confirm the missing information.",
                "uncertainties": [],
                "suggested_answer_type": "boolean",
                "requires_user_confirmation": True,
            }
        ],
        "fallback_recommended": False,
        "warnings": [],
    }


def rejected_stage_b_response() -> dict[str, object]:
    response = valid_response()
    suggestion = response["suggestions"][0]  # type: ignore[index]
    suggestion.update(  # type: ignore[union-attr]
        question=(
            "Will temporary storage be required before delivery to your new home "
            "in Northern California?"
        ),
        why_it_matters="This helps identify appropriate moving services.",
        information_it_would_clarify="Whether temporary storage will be required",
        grounding_summary="Broadened grounding.",
    )
    return response


class FakeTransport:
    def __init__(self, response: dict[str, object], fingerprint: str):
        self.response = response
        self.fingerprint = fingerprint
        self.preflight_calls = 0
        self.generation_calls = 0

    def preflight(self, request) -> OpenAIPreflightResult:
        self.preflight_calls += 1
        return OpenAIPreflightResult(
            request_fingerprint=self.fingerprint,
            input_tokens=2176,
            duration_ms=2.0,
            conservative_cost=Decimal("0.0016704"),
        )

    def generate(self, request, preflight) -> MovingServiceTransportResult:
        self.generation_calls += 1
        return MovingServiceTransportResult(
            response_content=self.response,
            input_tokens=2176,
            cached_input_tokens=0,
            uncached_input_tokens=2176,
            output_tokens=180,
            duration_ms=10.0,
            preflight_duration_ms=2.0,
            generation_duration_ms=8.0,
            cache_status="miss",
            provider_name="OpenAI",
            provider_model_identifier="gpt-4.1-mini-2025-04-14",
            estimated_cost="$0.00115840",
        )


def verified_authorization() -> VerifiedV2FollowUpAuthorization:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    return VerifiedV2FollowUpAuthorization(
        path=Path("offline-test-authorization.toml"),
        digest="a" * 64,
        artifact={},
        approved_at=now - timedelta(seconds=1),
        expires_at=now + timedelta(minutes=10),
    )


def open_authorization_repository(tmp_path: Path) -> tuple[Path, Path, datetime]:
    repository = tmp_path / "repo"
    source = REPOSITORY_ROOT / "docs/experiments/suggest-moving-service-questions/v2"
    target = repository / "docs/experiments/suggest-moving-service-questions/v2"
    shutil.copytree(source, target)
    frozen_manifest = target / "manifest.json"
    frozen = json.loads(frozen_manifest.read_text())
    approved = datetime(2026, 8, 2, 12, 0, tzinfo=timezone.utc)
    authorization = repository / "active.toml"
    authorization.write_text(
        f'''[metadata]
capability = "suggest_moving_service_questions"
authorization_version = "{AUTHORIZATION_VERSION}"
authorization_status = "approved_v2_follow_up_pilot"
evaluation_only = true
production_use_prohibited = true

[bindings]
frozen_v2_manifest_path = "docs/experiments/suggest-moving-service-questions/v2/manifest.json"
frozen_v2_manifest_digest = "{hashlib.sha256(frozen_manifest.read_bytes()).hexdigest()}"
prompt_version = "moving-service-questions-prompt-v2"
schema_version = "moving-service-questions-schema-v2"
fallback_version = "moving-service-fallback-v2"
pilot_configuration_path = "{frozen["follow_up_pilot_path"]}"
pilot_configuration_digest = "{frozen["artifact_digests"]["openai-follow-up-pilot.toml"]}"

[authorization]
credential_access_authorized = true
token_preflight_authorized = true
ai_generation_authorized = true
formal_evaluation_authorized = false
stage_c_authorized = false
production_use_authorized = false

[scope]
run_series_id = "{RUN_SERIES_ID}"
sequence = {SEQUENCE}
fixture_id = "{FIXTURE_ID}"
maximum_credential_reads = 1
maximum_client_constructions = 1
maximum_token_preflight_requests = 1
maximum_ai_generation_requests = 1
automatic_retries = 0
maximum_total_spend_usd = "0.03"
single_use = true

[approval]
approver = "Offline Test Reviewer"
approved_at = "2026-08-02T12:00:00Z"
expires_at = "2026-08-02T12:15:00Z"
maximum_authorization_duration_seconds = 900
'''
    )
    execution = repository / "execution.json"
    execution.write_text(
        json.dumps(
            {
                "capability": "suggest_moving_service_questions",
                "status": "v2_follow_up_pilot_authorized",
                "frozen_v2_manifest_path": (
                    "docs/experiments/suggest-moving-service-questions/v2/manifest.json"
                ),
                "frozen_v2_manifest_digest": hashlib.sha256(
                    frozen_manifest.read_bytes()
                ).hexdigest(),
                "authorization_path": "active.toml",
                "authorization_digest": hashlib.sha256(
                    authorization.read_bytes()
                ).hexdigest(),
                "follow_up_pilot_authorized": True,
                "credential_access_authorized": True,
                "token_preflight_authorized": True,
                "ai_generation_authorized": True,
                "formal_evaluation_authorized": False,
                "stage_c_authorized": False,
                "production_use_authorized": False,
            }
        )
    )
    return repository, execution, approved + timedelta(minutes=1)


class ExplodingEnvironment(dict):
    def get(self, key, default=None):
        raise AssertionError("Closed authorization inspected the environment.")


def test_committed_authorization_is_closed_before_environment_inspection() -> None:
    with pytest.raises(V2FollowUpPilotError, match="repository_authorization_closed"):
        run_v2_follow_up_pilot(
            environment=ExplodingEnvironment(),
            operator_intent=OPERATOR_INTENT,
        )


def test_frozen_payload_uses_only_v2_bindings_and_fixed_parameters() -> None:
    prepared = prepare_frozen_v2_pilot()
    request = prepared.provider_request
    serialized = json.loads(request.deterministic_request_json)
    assert serialized["prompt_version"] == "moving-service-questions-prompt-v2"
    assert serialized["schema_version"] == "moving-service-questions-schema-v2"
    assert [item["category_id"] for item in serialized["missing_information"]] == [
        "temporary_storage_need"
    ]
    assert request.model_identifier == "gpt-4.1-mini-2025-04-14"
    assert request.model_parameters == {"temperature": 0}
    assert request.maximum_output_tokens == 500
    assert request.timeout_seconds == 12
    assert request.retry_count == 0
    assert request.response_json_schema["properties"]["prompt_version"]["const"] == (
        "moving-service-questions-prompt-v2"
    )
    assert "For prompt v2" in request.system_instructions
    assert prepared.pilot_configuration["model_parameters"] == {
        "temperature": 0,
        "top_p": "omitted",
        "seed": "omitted",
        "maximum_output_tokens": 500,
        "store": False,
        "stream": False,
        "background": False,
        "truncation": "disabled",
        "tools": [],
    }
    assert prepared.pilot_configuration["transport"][
        "token_preflight_timeout_seconds"
    ] == 5


def test_compliant_fake_attempt_writes_bounded_audit_and_evidence(tmp_path) -> None:
    prepared = prepare_frozen_v2_pilot()
    transport = FakeTransport(valid_response(), _fingerprint(prepared))
    received: list[str] = []
    result = execute_authorized_v2_pilot_offline(
        authorization=verified_authorization(),
        environment={CREDENTIAL_NAME: "synthetic-test-only"},
        output_root=tmp_path,
        client_constructor=lambda credential: received.append(credential) or object(),
        transport_factory=lambda client, value: transport,
        closure=lambda: True,
    )
    assert received == ["synthetic-test-only"]
    assert transport.preflight_calls == transport.generation_calls == 1
    assert result["generation_succeeded"] is True
    assert result["human_review_status"] == "pending"
    audit, evidence, closure = _paths(tmp_path)
    assert audit.exists() and evidence.exists() and closure.exists()
    combined = audit.read_text() + evidence.read_text() + closure.read_text()
    for prohibited in (
        "synthetic-test-only",
        "system_instructions",
        "deterministic_request_json",
        "trusted_state",
        "authorization_headers",
    ):
        assert prohibited not in combined


def test_exact_open_gates_reach_one_fake_preflight_and_generation(tmp_path) -> None:
    repository, execution, now = open_authorization_repository(tmp_path)
    prepared = prepare_frozen_v2_pilot()
    transport = FakeTransport(valid_response(), _fingerprint(prepared))
    result = run_v2_follow_up_pilot_with_injected_boundaries(
        execution_manifest_path=execution,
        repository_root=repository,
        environment={
            ENABLEMENT_NAME: "1",
            CREDENTIAL_NAME: "synthetic-test-only",
        },
        operator_intent=OPERATOR_INTENT,
        run_series_id=RUN_SERIES_ID,
        sequence=SEQUENCE,
        fixture_id=FIXTURE_ID,
        output_root=tmp_path / "records",
        client_constructor=lambda credential: object(),
        transport_factory=lambda client, value: transport,
        closure=lambda: True,
        now=now,
    )
    assert result["generation_succeeded"] is True
    assert transport.preflight_calls == 1
    assert transport.generation_calls == 1


def test_operator_intent_cannot_broaden_open_repository_scope(tmp_path) -> None:
    repository, execution, now = open_authorization_repository(tmp_path)
    with pytest.raises(V2FollowUpPilotError, match="pilot_slot_rejected"):
        run_v2_follow_up_pilot_with_injected_boundaries(
            execution_manifest_path=execution,
            repository_root=repository,
            environment={ENABLEMENT_NAME: "1", CREDENTIAL_NAME: "synthetic"},
            operator_intent=OPERATOR_INTENT,
            run_series_id=RUN_SERIES_ID,
            sequence=2,
            fixture_id=FIXTURE_ID,
            output_root=tmp_path / "records",
            client_constructor=lambda credential: object(),
            transport_factory=lambda client, value: FakeTransport({}, ""),
            closure=lambda: True,
            now=now,
        )


def test_rejected_stage_b_wording_records_all_codes_and_v2_fallback(tmp_path) -> None:
    prepared = prepare_frozen_v2_pilot()
    transport = FakeTransport(rejected_stage_b_response(), _fingerprint(prepared))
    with pytest.raises(V2FollowUpPilotError, match="prose_validation_failure"):
        execute_authorized_v2_pilot_offline(
            authorization=verified_authorization(),
            environment={CREDENTIAL_NAME: "synthetic-test-only"},
            output_root=tmp_path,
            client_constructor=lambda credential: object(),
            transport_factory=lambda client, value: transport,
            closure=lambda: True,
        )
    audit = json.loads(_paths(tmp_path)[0].read_text())
    assert audit["prose_violation_codes"] == [
        "irrelevant_location_reference",
        "unsupported_home_or_property_assertion",
        "storage_modality_overstatement",
        "unsupported_service_selection_language",
        "grounding_summary_mismatch",
    ]
    assert audit["fallback_used"] is True
    assert audit["fallback_version"] == FALLBACK_VERSION_V2
    assert _paths(tmp_path)[1].exists() is False


def test_evidence_is_nonserializable_single_use_and_bound() -> None:
    preflight = OpenAIPreflightResult("fingerprint", 1, 1.0, Decimal("0.01"))
    binding = ("exact",)
    evidence = V2PreflightEvidence(
        construction_token=_EVIDENCE_TOKEN,
        binding=binding,
        preflight=preflight,
    )
    with pytest.raises(TypeError):
        pickle.dumps(evidence)
    assert evidence.consume(binding) is preflight
    with pytest.raises(V2FollowUpPilotError, match="preflight_evidence_rejected"):
        evidence.consume(binding)

    failed = V2PreflightEvidence(
        construction_token=_EVIDENCE_TOKEN,
        binding=binding,
        preflight=OpenAIPreflightResult(
            "fingerprint",
            None,
            1.0,
            None,
        ),
    )
    with pytest.raises(V2FollowUpPilotError, match="preflight_evidence_rejected"):
        failed.consume(binding)


def test_mismatched_preflight_fails_before_generation(tmp_path) -> None:
    transport = FakeTransport(valid_response(), "wrong")
    with pytest.raises(V2FollowUpPilotError, match="preflight_failure"):
        execute_authorized_v2_pilot_offline(
            authorization=verified_authorization(),
            environment={CREDENTIAL_NAME: "synthetic-test-only"},
            output_root=tmp_path,
            client_constructor=lambda credential: object(),
            transport_factory=lambda client, value: transport,
            closure=lambda: True,
        )
    assert transport.preflight_calls == 1
    assert transport.generation_calls == 0


def test_existing_slot_cannot_be_overwritten(tmp_path) -> None:
    audit, _, _ = _paths(tmp_path)
    audit.parent.mkdir(parents=True)
    audit.write_text("reserved")
    with pytest.raises(FileExistsError):
        execute_authorized_v2_pilot_offline(
            authorization=verified_authorization(),
            environment={CREDENTIAL_NAME: "synthetic-test-only"},
            output_root=tmp_path,
            client_constructor=lambda credential: object(),
            transport_factory=lambda client, value: FakeTransport({}, ""),
            closure=lambda: True,
        )


@pytest.mark.parametrize(
    ("mutate", "classification"),
    (
        (
            lambda response: response.update(extra_field="forbidden"),
            "pydantic_validation_failure",
        ),
        (
            lambda response: response["suggestions"][0].update(  # type: ignore[index]
                selected_missing_information_category="packing_preference"
            ),
            "semantic_validation_failure",
        ),
    ),
)
def test_structural_and_semantic_failures_remain_distinct(
    tmp_path,
    mutate,
    classification: str,
) -> None:
    response = valid_response()
    mutate(response)
    prepared = prepare_frozen_v2_pilot()
    transport = FakeTransport(response, _fingerprint(prepared))
    with pytest.raises(V2FollowUpPilotError, match=classification):
        execute_authorized_v2_pilot_offline(
            authorization=verified_authorization(),
            environment={CREDENTIAL_NAME: "synthetic-test-only"},
            output_root=tmp_path,
            client_constructor=lambda credential: object(),
            transport_factory=lambda client, value: transport,
            closure=lambda: True,
        )
    audit = json.loads(_paths(tmp_path)[0].read_text())
    assert audit["bounded_failure_classification"] == classification
    assert audit["authorization_closed"] is True


def test_closed_authorization_and_frozen_manifest_are_exactly_bound() -> None:
    execution = json.loads(DEFAULT_EXECUTION_MANIFEST.read_text())
    authorization = REPOSITORY_ROOT / execution["authorization_path"]
    assert hashlib.sha256(authorization.read_bytes()).hexdigest() == execution[
        "authorization_digest"
    ]
    with pytest.raises(V2FollowUpAuthorizationError, match="authorization is closed"):
        load_manifest_bound_v2_authorization(
            DEFAULT_EXECUTION_MANIFEST,
            repository_root=REPOSITORY_ROOT,
        )


def test_v1_authorization_cannot_substitute_for_v2(tmp_path) -> None:
    copied = tmp_path / "repo"
    shutil.copytree(
        REPOSITORY_ROOT / "docs/experiments/suggest-moving-service-questions/v2",
        copied / "docs/experiments/suggest-moving-service-questions/v2",
    )
    v1_authorization = (
        REPOSITORY_ROOT
        / "docs/experiments/suggest-moving-service-questions/v1/"
        "openai-execution-authorization.toml"
    )
    target = copied / "v1-authorization.toml"
    shutil.copyfile(v1_authorization, target)
    frozen = copied / "docs/experiments/suggest-moving-service-questions/v2/manifest.json"
    execution = {
        "capability": "suggest_moving_service_questions",
        "frozen_v2_manifest_path": str(frozen.relative_to(copied)),
        "frozen_v2_manifest_digest": hashlib.sha256(frozen.read_bytes()).hexdigest(),
        "authorization_path": str(target.relative_to(copied)),
        "authorization_digest": hashlib.sha256(target.read_bytes()).hexdigest(),
    }
    manifest = copied / "execution.json"
    manifest.write_text(json.dumps(execution))
    with pytest.raises(V2FollowUpAuthorizationError):
        load_manifest_bound_v2_authorization(manifest, repository_root=copied)


def test_closure_restores_exact_permanent_closed_state_and_is_idempotent(
    tmp_path,
) -> None:
    repository, active_manifest, now = open_authorization_repository(tmp_path)
    pilot_directory = (
        repository / "docs/experiments/suggest-moving-service-questions/v2-pilot"
    )
    pilot_directory.mkdir(parents=True)
    source = (
        REPOSITORY_ROOT
        / "docs/experiments/suggest-moving-service-questions/v2-pilot"
    )
    closed_manifest = pilot_directory / "closed-execution-manifest.json"
    closed_authorization = pilot_directory / "openai-execution-authorization.toml"
    shutil.copyfile(source / closed_manifest.name, closed_manifest)
    shutil.copyfile(source / closed_authorization.name, closed_authorization)
    active_authorization = repository / "active.toml"
    closure_record = tmp_path / "closure.json"

    close_v2_follow_up_authorization(
        execution_manifest_path=active_manifest,
        closed_manifest_path=closed_manifest,
        repository_root=repository,
        active_authorization_path=active_authorization,
        closure_record_path=closure_record,
        reason="success",
        closed_at=now,
    )
    assert active_manifest.read_bytes() == closed_manifest.read_bytes()
    assert active_authorization.exists() is False
    assert json.loads(closure_record.read_text())["authorization_closed"] is True

    close_v2_follow_up_authorization(
        execution_manifest_path=active_manifest,
        closed_manifest_path=closed_manifest,
        repository_root=repository,
        active_authorization_path=active_authorization,
        closure_record_path=closure_record,
        reason="success",
        closed_at=now,
    )


def test_v2_modules_remain_unreachable_from_backend_and_frontend() -> None:
    for root in (REPOSITORY_ROOT / "backend/app", REPOSITORY_ROOT / "frontend/src"):
        for path in root.rglob("*"):
            if path.is_file():
                text = path.read_text(errors="ignore")
                assert "run_openai_stage_b_v2_pilot" not in text
                assert "v2_follow_up_authorization" not in text
