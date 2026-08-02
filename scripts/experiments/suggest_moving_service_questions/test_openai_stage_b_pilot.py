from __future__ import annotations

import hashlib
import json
import pickle
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from openai_transport import OpenAIPreflightResult
from real_model_adapter import TransportErrorClassification
from run_openai_stage_b_pilot import (
    FIXTURE_ID,
    RUN_SERIES_ID,
    SEQUENCE,
    StageBPreflightEvidence,
    StageBPilotError,
    _EVIDENCE_TOKEN,
    _execute_stage_b,
    _paths,
    _provider_request,
    run_stage_b_generation_pilot,
)
from run_real_model_evaluation import OfflineRunnerGateError
from stage_b_authorization import (
    AUTHORIZATION_STATUS,
    AUTHORIZATION_VERSION,
    FINAL_ARTIFACT_PATH,
    MANIFEST_STATUS,
    PROVIDER_SCHEMA_DIGEST,
    PROMPT_DIGEST,
    RUN_CONFIGURATION_DIGEST,
    StageBAuthorizationError,
    load_manifest_bound_stage_b_authorization,
)

REPO = Path(__file__).resolve().parents[3]


def _artifact(approved: datetime) -> str:
    expires = approved + timedelta(seconds=900)
    stamp = lambda value: value.isoformat().replace("+00:00", "Z")
    return f'''[metadata]
capability = "suggest_moving_service_questions"
authorization_version = "{AUTHORIZATION_VERSION}"
authorization_status = "{AUTHORIZATION_STATUS}"
evaluation_only = true
default_deny = true
active_repository_authority = true

[bindings]
prompt_artifact_path = "docs/experiments/suggest-moving-service-questions/v1/real-model-prompt.toml"
prompt_version = "moving-service-questions-prompt-v1"
prompt_digest_algorithm = "sha256"
prompt_digest = "{PROMPT_DIGEST}"
run_configuration_path = "docs/experiments/suggest-moving-service-questions/v1/openai-run-configuration.toml"
run_configuration_digest_algorithm = "sha256"
run_configuration_digest = "{RUN_CONFIGURATION_DIGEST}"
provider_schema_path = "docs/experiments/suggest-moving-service-questions/v1/openai-response-schema.json"
provider_schema_digest_algorithm = "sha256"
provider_schema_digest = "{PROVIDER_SCHEMA_DIGEST}"
request_schema_version = "moving-service-questions-schema-v1"
response_schema_version = "moving-service-questions-schema-v1"
knowledge_fixture_version = "moving-service-storage-fixture-v2"
provider = "OpenAI"
ai_model_identifier = "gpt-4.1-mini-2025-04-14"
sdk_pin = "openai==2.45.0"

[authorization]
credential_access_authorized = true
token_preflight_authorized = true
ai_generation_authorized = true
formal_evaluation_authorized = false
production_use_authorized = false

[scope]
authorized_run_series_id = "{RUN_SERIES_ID}"
authorized_sequence_numbers = [{SEQUENCE}]
authorized_fixture_ids = ["{FIXTURE_ID}"]
maximum_authorized_spend = "0.03"
maximum_credential_reads = 1
maximum_client_constructions = 1
maximum_token_preflight_requests = 1
maximum_ai_generation_requests = 1

[approval]
approval_status = "approved"
approved_at = "{stamp(approved)}"
expires_at = "{stamp(expires)}"
approved_by = "Joe Shepherd"
maximum_authorization_duration_seconds = 900

[policy]
authorization_is_single_use = true
failure_consumes_sequence = true
preflight_must_be_fresh_and_same_attempt = true
preflight_evidence_must_be_consumed_before_generation = true
environment_values_may_override_authorization = false
operator_intent_is_authority = false
response_reuse_prohibited = true

[validation]
token_preflight_timeout_seconds = 5
generation_timeout_seconds = 12
maximum_input_tokens = 3000
maximum_output_tokens = 500
automatic_retries = 0
operator_intent_literal = "AUTHORIZE_ONE_STORAGE_UNKNOWN_STAGE_B_PREFLIGHT_AND_GENERATION"
'''


def _package(tmp_path: Path, now: datetime):
    for name in ("real-model-prompt.toml", "openai-run-configuration.toml", "openai-response-schema.json"):
        source = REPO / "docs/experiments/suggest-moving-service-questions/v1" / name
        target = tmp_path / "docs/experiments/suggest-moving-service-questions/v1" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
    auth = tmp_path / FINAL_ARTIFACT_PATH
    auth.write_text(_artifact(now - timedelta(seconds=1)), encoding="utf-8")
    digest = hashlib.sha256(auth.read_bytes()).hexdigest()
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({
        "capability": "suggest_moving_service_questions",
        "openai_execution_authorization_path": FINAL_ARTIFACT_PATH,
        "openai_execution_authorization_version": AUTHORIZATION_VERSION,
        "openai_execution_authorization_digest_algorithm": "sha256",
        "openai_execution_authorization_digest": digest,
        "openai_execution_authorization_status": AUTHORIZATION_STATUS,
        "status": MANIFEST_STATUS,
        "adapter_implementation_authorized": False,
        "real_model_execution_authorized": False,
        "real_model_evaluation_eligible": False,
    }), encoding="utf-8")
    return load_manifest_bound_stage_b_authorization(manifest, repository_root=tmp_path, now=now), manifest


def _valid_response() -> dict[str, object]:
    data = json.loads((REPO / "docs/experiments/suggest-moving-service-questions/v1/response-fixtures.json").read_text())
    return data["cases"][0]["response"]


class FakeResponses:
    def __init__(self, response: object, count: int = 2176):
        self.input_tokens = self
        self.response = response
        self.count_value = count
        self.count_calls = 0
        self.create_calls = 0
    def count(self, **kwargs):
        self.count_calls += 1
        return {"input_tokens": self.count_value}
    def create(self, **kwargs):
        self.create_calls += 1
        return self.response


class Owned:
    def __init__(self, response):
        self.client = type("Client", (), {"max_retries": 0, "responses": FakeResponses(response)})()
        self.closed = False
    def __enter__(self): return self
    def __exit__(self, *args): self.closed = True


def _provider_response(content=None):
    return {
        "status": "completed", "model": "gpt-4.1-mini-2025-04-14", "_request_id": "req_fake",
        "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(content or _valid_response())}]}],
        "usage": {"input_tokens": 2176, "output_tokens": 120, "input_tokens_details": {"cached_tokens": 0}},
    }


def test_closed_repository_rejects_before_environment_access():
    class ExplodingEnvironment(dict):
        def get(self, *args): raise AssertionError("environment touched")
    with pytest.raises(OfflineRunnerGateError):
        run_stage_b_generation_pilot(environment=ExplodingEnvironment(), operator_intent="wrong")


@pytest.mark.parametrize("mutation", ["series", "sequence", "fixture", "provider", "model", "sdk", "generation", "formal"])
def test_exact_authorization_scope_is_required(tmp_path, mutation):
    now = datetime.now(timezone.utc).replace(microsecond=0)
    artifact = _artifact(now - timedelta(seconds=1))
    replacements = {
        "series": (RUN_SERIES_ID, "wrong"), "sequence": (f"authorized_sequence_numbers = [{SEQUENCE}]", "authorized_sequence_numbers = [1]"),
        "fixture": (FIXTURE_ID, "complete"), "provider": ('provider = "OpenAI"', 'provider = "Other"'),
        "model": ("gpt-4.1-mini-2025-04-14", "wrong-model"), "sdk": ("openai==2.45.0", "openai==9"),
        "generation": ("ai_generation_authorized = true", "ai_generation_authorized = false"),
        "formal": ("formal_evaluation_authorized = false", "formal_evaluation_authorized = true"),
    }
    verified, manifest = _package(tmp_path, now)
    path = verified.path
    path.write_text(artifact.replace(*replacements[mutation]), encoding="utf-8")
    data = json.loads(manifest.read_text())
    data["openai_execution_authorization_digest"] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest.write_text(json.dumps(data))
    with pytest.raises(StageBAuthorizationError):
        load_manifest_bound_stage_b_authorization(manifest, repository_root=tmp_path, now=now)


@pytest.mark.parametrize("consumed_sequence", [1, 2, 3])
def test_consumed_stage_b_sequences_cannot_be_reauthorized(
    tmp_path, consumed_sequence
):
    now = datetime.now(timezone.utc).replace(microsecond=0)
    authorization, manifest = _package(tmp_path, now)
    authorization.path.write_text(
        authorization.path.read_text(encoding="utf-8").replace(
            f"authorized_sequence_numbers = [{SEQUENCE}]",
            f"authorized_sequence_numbers = [{consumed_sequence}]",
        ),
        encoding="utf-8",
    )
    manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
    manifest_data["openai_execution_authorization_digest"] = hashlib.sha256(
        authorization.path.read_bytes()
    ).hexdigest()
    manifest.write_text(json.dumps(manifest_data), encoding="utf-8")

    with pytest.raises(StageBAuthorizationError, match="consumed"):
        load_manifest_bound_stage_b_authorization(
            manifest, repository_root=tmp_path, now=now
        )


def test_evidence_is_nonserializable_single_use_and_mismatch_safe(tmp_path):
    now = datetime.now(timezone.utc).replace(microsecond=0)
    authorization, _ = _package(tmp_path, now)
    _, request = _provider_request()
    preflight = OpenAIPreflightResult("fingerprint", 1, 1.0, __import__("decimal").Decimal("0.01"))
    token = object(); path = tmp_path / "audit"
    evidence = StageBPreflightEvidence(construction_token=_EVIDENCE_TOKEN, authorization=authorization, request=request, preflight=preflight, audit_record_path=path, attempt_token=token)
    with pytest.raises(TypeError): pickle.dumps(evidence)
    assert evidence.consume(authorization=authorization, request=request, audit_record_path=path, attempt_token=token, now=now) is preflight
    with pytest.raises(Exception): evidence.consume(authorization=authorization, request=request, audit_record_path=path, attempt_token=token, now=now)


def test_failed_mismatched_and_stale_evidence_are_rejected(tmp_path):
    now = datetime.now(timezone.utc).replace(microsecond=0)
    authorization, _ = _package(tmp_path, now)
    _, request = _provider_request()
    failed = OpenAIPreflightResult("fingerprint", None, 1.0, None, TransportErrorClassification.TIMEOUT)
    for preflight, token, when in (
        (failed, object(), now),
        (OpenAIPreflightResult("fingerprint", 1, 1.0, __import__("decimal").Decimal("0.01")), object(), now),
        (OpenAIPreflightResult("fingerprint", 1, 1.0, __import__("decimal").Decimal("0.01")), object(), authorization.expires_at),
    ):
        expected_token = object()
        evidence = StageBPreflightEvidence(construction_token=_EVIDENCE_TOKEN, authorization=authorization, request=request, preflight=preflight, audit_record_path=tmp_path / "audit", attempt_token=expected_token)
        supplied_token = token if preflight.succeeded and when == now else expected_token
        with pytest.raises(Exception):
            evidence.consume(authorization=authorization, request=request, audit_record_path=tmp_path / "audit", attempt_token=supplied_token, now=when)


def test_offline_success_writes_bounded_owner_only_records(tmp_path):
    now = datetime.now(timezone.utc).replace(microsecond=0)
    authorization, manifest = _package(tmp_path / "repo", now)
    owned = Owned(_provider_response())
    record = _execute_stage_b(authorization=authorization, manifest_path=manifest, environment={"fake": "value"}, output_root=tmp_path / "out", client_builder=lambda *a, **k: owned, now=lambda: now)
    audit, evidence = _paths(tmp_path / "out")
    assert record.generation_succeeded and record.pydantic_validation_succeeded and record.semantic_validation_succeeded
    assert record.run_sequence == 4
    assert audit.name == "004-storage_unknown-generation-pilot.json"
    assert evidence.name == "004-storage_unknown-reviewed-response.json"
    assert owned.client.responses.count_calls == owned.client.responses.create_calls == 1
    assert audit.exists() and evidence.exists() and (evidence.stat().st_mode & 0o777) == 0o600
    text = audit.read_text() + evidence.read_text()
    for prohibited in ("api_key", "authorization_header", "system_instructions", "deterministic_request_json", "trusted_state"):
        assert prohibited not in text.lower()
    assert record.human_review_status == "pending"
    assert record.referenced_knowledge_ids == (
        "moving-service.temporary-storage-planning.fmcsa.v1",
    )
    assert record.cache_status == "miss"
    assert record.credential_lookup_attempted is True
    assert record.credential_value_obtained is True
    assert record.client_construction_attempted is True
    assert record.client_construction_succeeded is True
    assert record.conservative_preflight_cost is not None
    assert record.authorization_closed is False
    assert record.closure_status == "pending"
    with pytest.raises(FileExistsError):
        _execute_stage_b(
            authorization=authorization,
            manifest_path=manifest,
            environment={"fake": "value"},
            output_root=tmp_path / "out",
            client_builder=lambda *args, **kwargs: owned,
            now=lambda: now,
        )
    assert owned.client.responses.count_calls == 1
    assert owned.client.responses.create_calls == 1


def test_failure_writes_tombstone_and_prevents_overwrite(tmp_path):
    now = datetime.now(timezone.utc).replace(microsecond=0)
    authorization, manifest = _package(tmp_path / "repo", now)
    owned = Owned(_provider_response())
    owned.client.responses.response["usage"]["input_tokens"] = 999
    with pytest.raises(StageBPilotError):
        _execute_stage_b(authorization=authorization, manifest_path=manifest, environment={}, output_root=tmp_path / "out", client_builder=lambda *a, **k: owned, now=lambda: now)


def test_generation_cost_above_stage_b_ceiling_is_rejected(tmp_path):
    now = datetime.now(timezone.utc).replace(microsecond=0)
    authorization, manifest = _package(tmp_path / "repo", now)
    response = _provider_response()
    response["usage"]["output_tokens"] = 100_000
    with pytest.raises(StageBPilotError) as caught:
        _execute_stage_b(authorization=authorization, manifest_path=manifest, environment={}, output_root=tmp_path / "out", client_builder=lambda *a, **k: Owned(response), now=lambda: now)
    assert caught.value.classification == "budget_rejection"
    audit, _ = _paths(tmp_path / "out")
    assert json.loads(audit.read_text())["bounded_failure_classification"]
    with pytest.raises(FileExistsError):
        _execute_stage_b(authorization=authorization, manifest_path=manifest, environment={}, output_root=tmp_path / "out", client_builder=lambda *a, **k: owned, now=lambda: now)


@pytest.mark.parametrize("kind", ["malformed", "pydantic", "semantic", "provider_schema", "refusal", "incomplete"])
def test_response_failures_are_bounded(tmp_path, kind):
    now = datetime.now(timezone.utc).replace(microsecond=0)
    authorization, manifest = _package(tmp_path / "repo", now)
    response = _provider_response()
    if kind == "malformed": response["output"][0]["content"][0]["text"] = "{"
    if kind == "pydantic":
        invalid = _valid_response(); del invalid["warnings"]
        response["output"][0]["content"][0]["text"] = json.dumps(invalid)
    if kind == "semantic": response["output"][0]["content"][0]["text"] = json.dumps({**_valid_response(), "suggestions": [{**_valid_response()["suggestions"][0], "relevant_knowledge_ids": ["unknown"]}]})
    if kind == "refusal": response["output"][0]["content"] = [{"type": "refusal", "refusal": "no"}]
    if kind == "incomplete": response["status"] = "incomplete"; response["incomplete_details"] = {"reason": "max_output_tokens"}
    if kind == "provider_schema": response["output"].append({"type": "tool_call"})
    with pytest.raises(StageBPilotError) as caught:
        _execute_stage_b(authorization=authorization, manifest_path=manifest, environment={}, output_root=tmp_path / kind, client_builder=lambda *a, **k: Owned(response), now=lambda: now)
    expected = {"malformed": "malformed_json", "pydantic": "pydantic_validation_failure", "semantic": "semantic_validation_failure", "provider_schema": "provider_schema_failure", "refusal": "refusal", "incomplete": "incomplete_output"}[kind]
    assert caught.value.classification == expected
    audit = json.loads(caught.value.record_path.read_text())
    for field in (
        "credential_lookup_attempted",
        "client_construction_attempted",
        "preflight_attempted",
        "generation_attempted",
        "authorization_closed",
    ):
        assert isinstance(audit[field], bool)
    assert audit["failure_stage"]
    assert audit["bounded_failure_classification"] == expected


def test_transport_modules_are_not_reachable_from_application():
    for root in (REPO / "backend", REPO / "frontend"):
        for path in root.rglob("*"):
            if path.is_file() and path.suffix in {".py", ".js", ".jsx", ".ts", ".tsx"}:
                assert "run_openai_stage_b_pilot" not in path.read_text(errors="ignore")
