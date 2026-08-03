"""Network-disabled integration tests for v2 transport and lifecycle."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.moving_service_questions import STORAGE_KNOWLEDGE
from openai_transport_v2 import OpenAIV2MovingServiceEvaluationTransport
from run_openai_stage_b_v2_pilot import (
    CREDENTIAL_NAME,
    _fingerprint,
    _paths,
    execute_authorized_v2_pilot_offline,
    prepare_frozen_v2_pilot,
)
from openai_client_factory import EvaluationCredentialError, _read_evaluation_credential
from test_openai_stage_b_v2_pilot import valid_response, verified_authorization
from v2_follow_up_lifecycle import (
    close_v2_pilot_and_update_audit,
    delete_v2_response_evidence,
    finalize_v2_human_review,
    lifecycle_paths,
)


class FakeCount:
    def __init__(self, calls): self.calls = calls
    def count(self, **kwargs):
        self.calls.append(("preflight", kwargs))
        return SimpleNamespace(input_tokens=2176)


class FakeResponses:
    def __init__(self, calls):
        self.calls = calls
        self.input_tokens = FakeCount(calls)
    def create(self, **kwargs):
        self.calls.append(("generation", kwargs))
        return SimpleNamespace(
            status="completed", incomplete_details=None,
            output=[SimpleNamespace(type="message", content=[SimpleNamespace(type="output_text", text=json.dumps(valid_response()))])],
            usage=SimpleNamespace(input_tokens=2176, output_tokens=180, input_tokens_details=SimpleNamespace(cached_tokens=0)),
            model="gpt-4.1-mini-2025-04-14", _request_id="req_offline",
        )


class FakeClient:
    max_retries = 0
    def __init__(self):
        self.calls = []
        self.responses = FakeResponses(self.calls)
        self.closed = False
    def close(self): self.closed = True


def test_reviewed_transport_mechanics_receive_exact_v2_payload() -> None:
    prepared = prepare_frozen_v2_pilot()
    client = FakeClient()
    transport = OpenAIV2MovingServiceEvaluationTransport(client=client, prepared=prepared)
    preflight = transport.preflight(prepared.provider_request)
    result = transport.generate(prepared.provider_request, preflight)
    assert result.provider_request_id == "req_offline"
    assert [name for name, _ in client.calls] == ["preflight", "generation"]
    preflight_payload = client.calls[0][1]
    generation_payload = client.calls[1][1]
    assert preflight_payload["timeout"] == 5
    assert generation_payload["timeout"] == 12
    assert generation_payload["temperature"] == 0
    assert generation_payload["max_output_tokens"] == 500
    assert generation_payload["store"] is False
    assert generation_payload["stream"] is False
    assert generation_payload["background"] is False
    assert generation_payload["truncation"] == "disabled"
    assert "tools" not in generation_payload
    assert generation_payload["text"]["format"]["name"].endswith("_v2")
    assert generation_payload["text"]["format"]["strict"] is True
    assert generation_payload["instructions"] == prepared.provider_request.system_instructions
    assert generation_payload["input"] == prepared.provider_request.deterministic_request_json


def test_complete_v2_path_closes_client_and_lifecycle_deletes_evidence(tmp_path) -> None:
    prepared = prepare_frozen_v2_pilot()
    client = FakeClient()
    state = execute_authorized_v2_pilot_offline(
        authorization=verified_authorization(),
        environment={CREDENTIAL_NAME: "synthetic-test-only"},
        output_root=tmp_path,
        client_constructor=lambda _: client,
        transport_factory=lambda value, _: OpenAIV2MovingServiceEvaluationTransport(client=value, prepared=prepared),
        closure=lambda: True,
    )
    assert state["generation_succeeded"] is True
    assert client.closed is True
    audit, evidence, _ = _paths(tmp_path)
    assert evidence.stat().st_mode & 0o777 == 0o600
    review = finalize_v2_human_review(
        output_root=tmp_path,
        now=datetime(2026, 8, 2, 12, tzinfo=timezone.utc),
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
    assert not evidence.exists()
    deletion = json.loads(lifecycle_paths(tmp_path)["deletion"].read_text())
    assert "response" not in deletion
    assert delete_v2_response_evidence(
        output_root=tmp_path, reason="review_signoff", review_status="approved"
    ) == deletion
    assert json.loads(audit.read_text())["response_evidence_deleted"] is True


def test_lifecycle_rejects_unbounded_review(tmp_path) -> None:
    with pytest.raises(Exception):
        finalize_v2_human_review(output_root=tmp_path, review={"unknown": True})


def test_only_evaluation_specific_credential_name_is_accepted() -> None:
    with pytest.raises(EvaluationCredentialError, match="Conventional"):
        _read_evaluation_credential({"OPENAI_API_KEY": "synthetic"})
    credential = _read_evaluation_credential({CREDENTIAL_NAME: "synthetic"})
    assert "synthetic" not in repr(credential)


def test_conventional_environment_is_rejected_before_client_construction(tmp_path) -> None:
    constructed = []
    with pytest.raises(Exception, match="credential_configuration_rejected"):
        execute_authorized_v2_pilot_offline(
            authorization=verified_authorization(),
            environment={CREDENTIAL_NAME: "synthetic", "OPENAI_API_KEY": "prohibited"},
            output_root=tmp_path,
            client_constructor=lambda value: constructed.append(value),
            transport_factory=lambda *_: None,
            closure=lambda: True,
        )
    assert constructed == []


def test_v2_closure_wrapper_updates_bounded_audit(tmp_path, monkeypatch) -> None:
    prepared = prepare_frozen_v2_pilot()
    execute_authorized_v2_pilot_offline(
        authorization=verified_authorization(),
        environment={CREDENTIAL_NAME: "synthetic"},
        output_root=tmp_path,
        client_constructor=lambda _: FakeClient(),
        transport_factory=lambda client, _: OpenAIV2MovingServiceEvaluationTransport(
            client=client, prepared=prepared
        ),
        closure=lambda: True,
    )
    paths = lifecycle_paths(tmp_path)
    paths["closure"].unlink()

    def fake_close(**kwargs):
        Path(kwargs["closure_record_path"]).write_text(
            json.dumps({"authorization_closed": True}), encoding="utf-8"
        )

    monkeypatch.setattr("v2_follow_up_lifecycle.close_v2_follow_up_authorization", fake_close)
    close_v2_pilot_and_update_audit(output_root=tmp_path)
    audit = json.loads(paths["audit"].read_text())
    assert audit["authorization_closed"] is True
    assert audit["closure_record_path"] == str(paths["closure"])
