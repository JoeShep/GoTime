"""Offline sequence-4 generation gate, validation, review, and deletion tests."""

from __future__ import annotations

import copy
import hashlib
import json
import shutil
import sys
import tomllib
from datetime import datetime, timezone
from pathlib import Path

import pytest

SCRIPT_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = SCRIPT_ROOT.parents[2]
BACKEND_ROOT = REPOSITORY_ROOT / "backend"
for value in (SCRIPT_ROOT, BACKEND_ROOT):
    if str(value) not in sys.path:
        sys.path.insert(0, str(value))

from test_openai_stage_b_v2_pilot import rejected_stage_b_response, valid_response  # noqa: E402
from v2_sequence_4_generation_gate import (  # noqa: E402
    CANDIDATE_DIGEST,
    CANDIDATE_PATH,
    PREFLIGHT_EVIDENCE_DIGEST,
    PREFLIGHT_REVIEW_DIGEST,
    Sequence4GenerationGateError,
    OPERATOR_INTENT,
    activate_generation_authority,
    close_generation_authority,
    generation_paths,
    review_and_delete_response,
    validate_generated_response,
    verify_exact_generation_attempt,
    verify_candidate_and_preflight,
    write_generation_outcome,
)
from run_openai_stage_b_v2_pilot import prepare_frozen_v2_pilot  # noqa: E402
from run_openai_stage_b_v2_sequence_4_generation_live import (  # noqa: E402
    verify_attempt_then_read_credential,
)
from dataclasses import replace

NOW = datetime(2030, 1, 1, tzinfo=timezone.utc)
REAL_STATE = REPOSITORY_ROOT / ".local/evaluations/suggest-moving-service-questions/moving-service-stage-b-v2-pilot-20260802"


def state(tmp_path: Path) -> tuple[Path, Path]:
    repository = tmp_path / "repository"
    docs = repository / "docs/experiments/suggest-moving-service-questions/v2-pilot"
    docs.mkdir(parents=True)
    closed = REPOSITORY_ROOT / "docs/experiments/suggest-moving-service-questions/v2-pilot/closed-execution-manifest.json"
    shutil.copyfile(closed, docs / "closed-execution-manifest.json")
    shutil.copyfile(closed, docs / "execution-manifest.json")
    output = tmp_path / "state"
    base = output / "moving-service-stage-b-v2-pilot-20260802"
    base.mkdir(parents=True)
    shutil.copyfile(REAL_STATE / "004-storage_unknown-preflight-evidence.json", base / "004-storage_unknown-preflight-evidence.json")
    shutil.copyfile(REAL_STATE / "004-storage_unknown-preflight-review.json", base / "004-storage_unknown-preflight-review.json")
    return repository, output


def rendered_artifact_bytes() -> bytes:
    candidate = tomllib.loads(CANDIDATE_PATH.read_text())
    artifact = {
        "metadata": {"capability": "suggest_moving_service_questions", "authorization_version": "moving-service-openai-v2-generation-sequence-4-v1", "authorization_status": "approved_v2_generation", "phase": "generation", "active_repository_authority": True},
        "bindings": candidate["bindings"], "approved_preflight": candidate["approved_preflight"],
        "authorization": candidate["proposed_authorization"], "scope": candidate["scope"],
        "approval": {"approver": "Synthetic Approver", "approved_at": "2030-01-01T00:00:00Z", "activated_at": "2030-01-01T00:00:00Z", "expires_at": "2030-01-01T00:15:00Z", "maximum_duration_seconds": 900, "authorization_reason": "Synthetic recovery test"},
    }
    lines = []
    for section, values in artifact.items():
        lines.append(f"[{section}]")
        for key, value in values.items():
            lines.append(f"{key} = {json.dumps(value)}" if not isinstance(value, bool) else f"{key} = {str(value).lower()}")
        lines.append("")
    return ("\n".join(lines).rstrip() + "\n").encode()


def test_candidate_binds_exact_approved_preflight_and_closed_state(tmp_path) -> None:
    repository, output = state(tmp_path)
    result = verify_candidate_and_preflight(repository_root=repository, output_root=output)
    assert result["candidate_digest"] == CANDIDATE_DIGEST
    assert result["input_tokens"] == 2228
    assert result["conservative_maximum_generation_cost"] == "0.0016912"


def test_exact_generation_attempt_is_credential_free_and_frozen(tmp_path) -> None:
    repository, output = state(tmp_path)
    attempt = verify_exact_generation_attempt(output_root=output)
    assert attempt.deterministic_request_digest == "3150794ae420dfe6671ca141b762cda0a39d5fdeb11b1dbe2d97817b9ef5bfea"
    assert attempt.canonical_attempt_digest == "d1f6b54caebf3745ba0447b8644edbc71b6f95879d8c6ed64d77b0ee590118ce"
    assert attempt.provider_fingerprint == "60e29402cc77e914b36d038f04a6a2eb1a0d6fcfb8fe9fd20e6837f3b887d4ef"


@pytest.mark.parametrize("drift", [
    "prompt_digest", "prompt_identifier", "schema_identifier", "provider_schema",
    "pilot_configuration", "deterministic_request", "canonical_attempt",
    "provider_fingerprint", "model_identifier", "temperature", "maximum_output_tokens",
    "retry_count", "generation_timeout",
])
def test_every_exact_request_drift_rejects_before_credential_lookup(tmp_path, drift) -> None:
    repository, output = state(tmp_path)
    original = prepare_frozen_v2_pilot()
    prepared = copy.deepcopy(original)
    fingerprint_builder = None
    if drift == "prompt_digest":
        prepared.frozen_manifest["artifact_digests"]["real-model-prompt.toml"] = "0" * 64
    elif drift == "prompt_identifier":
        prepared = replace(prepared, request=prepared.request.model_copy(update={"prompt_version": "drift"}))
    elif drift == "schema_identifier":
        prepared = replace(prepared, request=prepared.request.model_copy(update={"schema_version": "drift"}))
    elif drift == "provider_schema":
        prepared = replace(prepared, provider_request=replace(prepared.provider_request, response_json_schema={"type": "object"}))
    elif drift == "pilot_configuration":
        prepared.pilot_configuration["identity"]["provider"] = "Drift"
    elif drift == "deterministic_request":
        prepared = replace(prepared, provider_request=replace(prepared.provider_request, deterministic_request_json="{}"))
    elif drift == "canonical_attempt":
        fingerprint_builder = lambda value: "0" * 64
    elif drift == "provider_fingerprint":
        fingerprint_builder = lambda value: "0" * 64
    elif drift == "model_identifier":
        prepared = replace(prepared, provider_request=replace(prepared.provider_request, model_identifier="gpt-drift"))
    elif drift == "temperature":
        prepared = replace(prepared, provider_request=replace(prepared.provider_request, model_parameters={"temperature": 1}))
    elif drift == "maximum_output_tokens":
        object.__setattr__(prepared.provider_request, "maximum_output_tokens", 499)
    elif drift == "retry_count":
        object.__setattr__(prepared.provider_request, "retry_count", 1)
    else:
        object.__setattr__(prepared.provider_request, "timeout_seconds", 11.0)
    observed = {"credential": False, "client": False, "generation": False}
    def rejected(**kwargs):
        return verify_exact_generation_attempt(
            output_root=output, prepared_builder=lambda: prepared,
            provider_fingerprint_builder=fingerprint_builder,
        )
    class CredentialSpy(dict):
        def get(self, key, default=None):
            observed["credential"] = True
            return super().get(key, default)
    with pytest.raises((Sequence4GenerationGateError, ValueError)):
        verify_attempt_then_read_credential(environment=CredentialSpy(), attempt_verifier=rejected)
    assert observed == {"credential": False, "client": False, "generation": False}


@pytest.mark.parametrize("filename", [
    "004-storage_unknown-preflight-evidence.json",
    "004-storage_unknown-preflight-review.json",
])
def test_historical_digest_drift_rejects_before_credential_lookup(tmp_path, filename) -> None:
    repository, output = state(tmp_path)
    target = output / "moving-service-stage-b-v2-pilot-20260802" / filename
    target.write_text("{}\n")
    touched = {"credential": False}
    class CredentialSpy(dict):
        def get(self, key, default=None):
            touched["credential"] = True
            return None
    with pytest.raises(Sequence4GenerationGateError):
        verify_attempt_then_read_credential(
            environment=CredentialSpy(),
            attempt_verifier=lambda **kwargs: verify_exact_generation_attempt(output_root=output),
        )
    assert touched["credential"] is False


@pytest.mark.parametrize(("field", "value"), [
    ("input_tokens", 2227),
    ("conservative_maximum_generation_cost", "0.0016913"),
    ("store", True),
    ("stream", True),
    ("background", True),
    ("truncation", "auto"),
    ("tools", [{"type": "function"}]),
    ("automatic_retries", 1),
    ("maximum_output_tokens", 499),
    ("temperature", 1),
    ("ai_generation_timeout_seconds", 11),
])
def test_evidence_parameter_drift_rejects_before_credential_lookup(
    tmp_path, field, value
) -> None:
    repository, output = state(tmp_path)
    target = output / "moving-service-stage-b-v2-pilot-20260802/004-storage_unknown-preflight-evidence.json"
    evidence = json.loads(target.read_text())
    evidence[field] = value
    target.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    touched = {"credential": False}
    class CredentialSpy(dict):
        def get(self, key, default=None):
            touched["credential"] = True
            return None
    with pytest.raises(Sequence4GenerationGateError):
        verify_attempt_then_read_credential(
            environment=CredentialSpy(),
            attempt_verifier=lambda **kwargs: verify_exact_generation_attempt(output_root=output),
        )
    assert touched["credential"] is False


@pytest.mark.parametrize(("filename", "expected"), [
    ("004-storage_unknown-preflight-evidence.json", "approved preflight history drifted"),
    ("004-storage_unknown-preflight-review.json", "approved preflight history drifted"),
])
def test_wrong_evidence_or_review_digest_fails(tmp_path, filename, expected) -> None:
    repository, output = state(tmp_path)
    path = output / "moving-service-stage-b-v2-pilot-20260802" / filename
    path.write_text("{}\n", encoding="utf-8")
    with pytest.raises(Sequence4GenerationGateError, match=expected):
        verify_candidate_and_preflight(repository_root=repository, output_root=output)


def test_generation_validation_paths_are_distinct_and_prose_order_is_stable() -> None:
    assert validate_generated_response(valid_response())[0] == "validated"
    classification, codes = validate_generated_response(rejected_stage_b_response())
    assert classification == "prose_failure"
    assert codes == (
        "irrelevant_location_reference",
        "unsupported_home_or_property_assertion",
        "storage_modality_overstatement",
        "unsupported_service_selection_language",
        "grounding_summary_mismatch",
    )
    assert validate_generated_response([])[0] == "structural_failure"
    semantic = valid_response()
    semantic["suggestions"][0]["selected_missing_information_category"] = "packing_preference"  # type: ignore[index]
    assert validate_generated_response(semantic)[0] == "semantic_failure"


def test_compliant_generation_writes_review_evidence_then_review_deletes_it(tmp_path) -> None:
    output = tmp_path / "state"
    result = write_generation_outcome(output_root=output, raw=valid_response(), now=NOW)
    paths = generation_paths(output)
    assert result["preflight_attempted"] is False
    assert result["generation_request_count"] == 1
    assert paths.response_evidence.stat().st_mode & 0o777 == 0o600
    evidence_digest = result["response_evidence_sha256"]
    review = review_and_delete_response(
        output_root=output, evidence_sha256=str(evidence_digest), reviewer="Synthetic Reviewer",
        decision="approve", reviewed_at=NOW, grounding_accuracy=True,
        invented_user_fact=False, irrelevant_detail=False, modality_overstatement=False,
        service_selection_overstatement=False, clarity_score=5, usefulness_score=5,
        fallback_comparison="materially_better", notes="Synthetic bounded review.",
    )
    assert review["decision"] == "approve"
    assert not paths.response_evidence.exists()
    deletion = json.loads(paths.deletion.read_text())
    assert deletion["contains_response_content"] is False
    assert deletion["deletion_completed"] is True


@pytest.mark.parametrize("response", [rejected_stage_b_response(), []])
def test_rejected_generation_uses_fallback_writes_no_evidence_closes_and_cannot_reuse(tmp_path, response) -> None:
    output = tmp_path / "state"
    result = write_generation_outcome(output_root=output, raw=response, now=NOW)
    paths = generation_paths(output)
    assert result["fallback_used"] is True
    assert result["fallback_version"] == "moving-service-fallback-v2"
    assert not paths.response_evidence.exists()
    assert json.loads(paths.closure.read_text())["ai_generation_authorized"] is False
    with pytest.raises(Sequence4GenerationGateError, match="already consumed"):
        write_generation_outcome(output_root=output, raw=valid_response(), now=NOW)


def test_review_reject_and_request_changes_delete_evidence_without_authority(tmp_path) -> None:
    for decision in ("reject", "request_changes"):
        output = tmp_path / decision
        result = write_generation_outcome(output_root=output, raw=valid_response(), now=NOW)
        review = review_and_delete_response(
            output_root=output, evidence_sha256=str(result["response_evidence_sha256"]),
            reviewer="Synthetic Reviewer", decision=decision, reviewed_at=NOW,
            grounding_accuracy=False, invented_user_fact=True, irrelevant_detail=False,
            modality_overstatement=False, service_selection_overstatement=False,
            clarity_score=2, usefulness_score=2, fallback_comparison="materially_worse",
            notes="Synthetic rejection.",
        )
        assert review["generation_authorized"] is False


def test_exact_historical_digests_are_constants() -> None:
    assert PREFLIGHT_EVIDENCE_DIGEST == "e19a7b412f6a7f1517dcef32ab6fb7c305049ced90aac252bd8e55f7b0a9a38c"
    assert PREFLIGHT_REVIEW_DIGEST == "7846de2614f673e3afb7af9e26c20ba06b785547deb1eb3f76d3409a4168c541"


@pytest.mark.parametrize("failpoint", [
    "after_prepared", "after_authorization_installed",
    "after_manifest_transition", "after_activation_record",
])
def test_activation_interruption_recovers_exact_closed_state(tmp_path, failpoint) -> None:
    repository, output = state(tmp_path)
    paths = generation_paths(output)
    paths.review_rendered.parent.mkdir(parents=True, exist_ok=True)
    paths.review_rendered.write_bytes(rendered_artifact_bytes())
    paths.installation.write_text("{}\n")
    paths.activation_review.write_text(json.dumps({"decision": "approve", "activation_eligible": True}) + "\n")
    with pytest.raises(OSError, match="synthetic interruption"):
        activate_generation_authority(
            repository_root=repository, output_root=output,
            artifact_sha256=__import__("hashlib").sha256(paths.review_rendered.read_bytes()).hexdigest(),
            installation_sha256=__import__("hashlib").sha256(paths.installation.read_bytes()).hexdigest(),
            review_sha256=__import__("hashlib").sha256(paths.activation_review.read_bytes()).hexdigest(),
            operator="Synthetic Operator", operator_intent=OPERATOR_INTENT,
            now=NOW, failpoint=failpoint,
        )
    docs = repository / "docs/experiments/suggest-moving-service-questions/v2-pilot"
    assert (docs / "execution-manifest.json").read_bytes() == (docs / "closed-execution-manifest.json").read_bytes()
    assert not paths.active.exists()
    assert json.loads(paths.transaction.read_text())["state"] == "rolled_back"
    assert close_generation_authority(repository_root=repository, output_root=output,
                                      reason="activation_recovery", now=NOW)["authorization_closed"] is True
