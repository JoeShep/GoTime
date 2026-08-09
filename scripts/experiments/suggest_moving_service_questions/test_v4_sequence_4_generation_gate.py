"""Offline frozen-v4 sequence-4 generation-gate tests."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sys
import tomllib
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

SCRIPT_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = SCRIPT_ROOT.parents[2]
BACKEND_ROOT = REPOSITORY_ROOT / "backend"
for value in (SCRIPT_ROOT, BACKEND_ROOT):
    if str(value) not in sys.path:
        sys.path.insert(0, str(value))

from run_openai_stage_b_v2_pilot import prepare_frozen_v2_pilot  # noqa: E402
from run_openai_stage_b_v4_pilot import (  # noqa: E402
    FROZEN_V4_MANIFEST_DIGEST,
    canonical_attempt_digest,
    deterministic_request_digest,
    prepare_frozen_v4_pilot,
)
from test_openai_stage_b_v2_pilot import rejected_stage_b_response, valid_response  # noqa: E402
from test_v4_sequence_1_preflight import _review_state  # noqa: E402
import v4_sequence_4_generation_gate as generation_gate  # noqa: E402
import run_openai_stage_b_v4_sequence_4_generation_live as live_generation  # noqa: E402
from run_openai_stage_b_v4_sequence_4_generation_live import verify_attempt_then_read_credential  # noqa: E402
from v4_sequence_4_generation_gate import (  # noqa: E402
    CANDIDATE_DIGEST,
    CANDIDATE_PATH,
    CANONICAL_ATTEMPT_DIGEST,
    MANIFEST_DIGEST,
    MANIFEST_PATH,
    OPERATOR_INTENT,
    PROVIDER_FINGERPRINT,
    REQUEST_DIGEST,
    Sequence4GenerationGateError,
    activate_generation_authority,
    active_generation_manifest_bytes,
    generation_paths,
    validate_generated_response,
    verify_live_generation_precredential,
    verify_candidate_and_preflight,
    verify_resolved_generation_candidate,
    verify_unresolved_generation_candidate,
)
from v4_sequence_1_preflight import (  # noqa: E402
    paths as preflight_paths,
    review_evidence as review_preflight_evidence,
    verify_completed_lifecycle_history,
)


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _toml_bytes(value: dict[str, object]) -> bytes:
    lines: list[str] = []
    for section, fields in value.items():
        lines.append(f"[{section}]")
        for key, item in fields.items():
            rendered = str(item).lower() if isinstance(item, bool) else json.dumps(item)
            lines.append(f"{key} = {rendered}")
        lines.append("")
    return ("\n".join(lines).rstrip() + "\n").encode()


def _json(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def _copy_v4_bindings(repository: Path) -> None:
    source = REPOSITORY_ROOT / "docs/experiments/suggest-moving-service-questions/v4"
    target = repository / "docs/experiments/suggest-moving-service-questions/v4"
    target.mkdir(parents=True, exist_ok=True)
    for name in ("manifest.json", "real-model-prompt.toml", "request-identity.json",
                 "openai-response-schema.json", "offline-pilot-request-config.json"):
        shutil.copyfile(source / name, target / name)


def _active_generation_state(tmp_path: Path):
    output, repository, evidence_digest = _review_state(tmp_path)
    preflight = preflight_paths(output, repository)
    evidence = json.loads(preflight.evidence.read_text())
    reviewed_at = str(evidence["created_at"])
    review_preflight_evidence(
        evidence_sha256=evidence_digest, input_tokens=4242,
        conservative_cost="0.0024242", reviewer="Synthetic Evidence Reviewer",
        decision="approve", reviewed_at=reviewed_at,
        token_count_plausible=True, cost_within_limit=True,
        frozen_bindings_confirmed=True, evidence_history_confirmed=True,
        notes="Synthetic approved evidence", now=datetime.fromisoformat(
            reviewed_at.replace("Z", "+00:00")), output_root=output,
        repository_root=repository)
    _copy_v4_bindings(repository)
    now = datetime.now(timezone.utc).replace(microsecond=0)
    candidate = tomllib.loads(CANDIDATE_PATH.read_text())
    artifact = {
        "metadata": {"capability": "suggest_moving_service_questions",
                     "authorization_version": "moving-service-openai-v4-generation-sequence-4-v1",
                     "authorization_status": "approved_v4_generation", "phase": "generation",
                     "active_repository_authority": True},
        "bindings": candidate["bindings"],
        "required_v4_preflight": candidate["required_v4_preflight"],
        "authorization": candidate["proposed_authorization"], "scope": candidate["scope"],
        "approval": {"approver": "Synthetic Approver",
                     "approved_at": generation_gate._stamp(now - timedelta(seconds=12)),
                     "activated_at": generation_gate._stamp(now - timedelta(seconds=10)),
                     "expires_at": generation_gate._stamp(now + timedelta(seconds=600)),
                     "maximum_duration_seconds": 900,
                     "authorization_reason": "Synthetic active-boundary verification"},
    }
    target = generation_paths(output)
    target.review_rendered.parent.mkdir(parents=True, exist_ok=True)
    target.review_rendered.write_bytes(_toml_bytes(artifact))
    authorization_digest = _digest(target.review_rendered)
    _json(target.installation, {"phase": "generation", "sequence": 4,
        "fixture_id": "storage_unknown", "installed_digest": authorization_digest,
        "candidate_digest": CANDIDATE_DIGEST, "candidate_manifest_digest": MANIFEST_DIGEST,
        "authoritative": False, "activation_status": "not_activated",
        "activation_review_status": "pending"})
    _json(target.activation_review, {"phase": "generation_activation_review", "sequence": 4,
        "fixture_id": "storage_unknown", "installed_artifact_digest": authorization_digest,
        "installation_record_digest": _digest(target.installation), "reviewer": "Synthetic Reviewer",
        "decision": "approve", "reviewed_at": generation_gate._stamp(now - timedelta(seconds=7)),
        "bounded_notes": "Synthetic reviewed generation authorization", "activation_eligible": True,
        "authoritative": False, "activated": False})
    activate_generation_authority(repository_root=repository, output_root=output,
        artifact_sha256=authorization_digest, installation_sha256=_digest(target.installation),
        review_sha256=_digest(target.activation_review), operator="Synthetic Operator",
        operator_intent=OPERATOR_INTENT, now=now - timedelta(seconds=5))
    return output, repository, now


def _synthetic_history_verifier(*, repository_root: Path, output_root: Path):
    evidence = json.loads(preflight_paths(output_root, repository_root).evidence.read_text())
    result = verify_completed_lifecycle_history(
        evidence=evidence, output_root=output_root, repository_root=repository_root)
    return {**result, "input_tokens": evidence["input_tokens"],
            "conservative_maximum_generation_cost": evidence["conservative_maximum_generation_cost"]}


def test_v4_request_bindings_differ_from_v2_and_are_live_preflight_resolved() -> None:
    v2 = prepare_frozen_v2_pilot()
    v4 = prepare_frozen_v4_pilot()
    assert deterministic_request_digest(v4) == REQUEST_DIGEST
    assert canonical_attempt_digest(v4) == CANONICAL_ATTEMPT_DIGEST
    assert REQUEST_DIGEST != hashlib.sha256(
        v2.provider_request.deterministic_request_json.encode()
    ).hexdigest()
    assert v4.request.prompt_version == "moving-service-questions-prompt-v4"
    assert v4.request.schema_version == "moving-service-questions-schema-v4"
    assert v4.frozen_manifest["fallback_version"] == "moving-service-fallback-v2"
    assert v4.frozen_manifest["fallback_v2_reused"] is True
    assert verify_unresolved_generation_candidate()["binding_status"] == "fresh_v4_preflight_required"
    assert verify_resolved_generation_candidate()["binding_status"] == "approved_v4_preflight_bound"


def test_resolved_candidate_is_inactive_v4_only_and_digest_bound() -> None:
    candidate = tomllib.loads(CANDIDATE_PATH.read_text())
    manifest = json.loads(MANIFEST_PATH.read_text())
    assert _digest(CANDIDATE_PATH) == CANDIDATE_DIGEST
    assert _digest(MANIFEST_PATH) == MANIFEST_DIGEST
    assert manifest["candidate_digest"] == CANDIDATE_DIGEST
    assert candidate["metadata"]["active_repository_authority"] is False
    assert candidate["authorization"]["ai_generation_authorized"] is False
    assert candidate["required_v4_preflight"]["binding_status"] == "approved_v4_preflight_bound"
    assert candidate["required_v4_preflight"]["preflight_evidence_digest"] == "f1f995231fc4986c25625f673bc878a82564adb9d6992ad9e62b1fdbccafe62c"
    assert candidate["required_v4_preflight"]["preflight_review_digest"] == "12b71c109aadf82a8d4e471f165bc3b7d450a84cc229ad6eb696e0f17e9d6bd2"
    assert candidate["required_v4_preflight"]["input_tokens"] == 2852
    assert candidate["required_v4_preflight"]["conservative_cost"] == "0.0019408"
    assert candidate["bindings"]["frozen_v4_manifest_digest"] == FROZEN_V4_MANIFEST_DIGEST
    assert candidate["bindings"]["prompt_version"] == "moving-service-questions-prompt-v4"
    assert candidate["bindings"]["schema_version"] == "moving-service-questions-schema-v4"
    assert candidate["scope"]["operator_intent"] == OPERATOR_INTENT
    assert candidate["scope"]["maximum_token_preflight_requests"] == 0
    assert candidate["scope"]["maximum_ai_generation_requests"] == 1
    assert candidate["scope"]["automatic_retries"] == 0


def test_exact_frozen_v4_artifact_digests() -> None:
    expected = {
        "adversarial-policy-cases.json": "b17f18ae1cf434f1b74fa8717c2c11ef17da23885b76644ca96384576c69428a",
        "deterministic-baseline.json": "e2e185dac7411ad7bd7ea9ed049b9d7146c4e4e2ffa3d2125e67f84a72573dbc",
        "expected-policy-results.json": "ef673f73f53fc78cde23a068c52ef113790c7b212fa198120aae3dd1268351e3",
        "expected-results.json": "452b1a8b87f9e4ed438c130559dd62ce1e6725136f9f307bbc008bb424848d9b",
        "freeze-record.md": "a458d941f98298d6f97370c79a05b1073a55bbb449f2593d26afd07b50a8e50b",
        "grounding-fail-closed-cases.json": "bcae538b99f9bec504b27077c2b39560f1a91777c42c0daaf16a841829619232",
        "knowledge-source-review.md": "cb752f280fe6c79c28cd80ff0d10bdb2b751e3af804ee270563b1fc6a89555d7",
        "manifest.json": "3cdbd2bf3606191aa52108d8284c8ab300d58a511f313f78a06be51d95fac649",
        "offline-pilot-request-config.json": "9459094de6b42de7827179fae1f4523712cad1432c4bbc6a3f2a679a6703d82a",
        "real-model-prompt.toml": "78b77f31e8cdc68528c08c106fec947123838813d9bdd82978c32a3b011ffb26",
        "openai-response-schema.json": "4119a12b673b693c958aa623ff8d9377e3d27f5fd1ca6655671c65716363269d",
        "openai-response-schema-review.md": "a1faf4649132ddbd71bc0f86b429788da60e4ac42dce93fa0485846db4489dcf",
        "provider-schema-adaptation.json": "8d53ac72f32d948e787baa645133c7953354784350777032c0f873d8b6ab7624",
        "request-fixtures.json": "08619f1890d1ebf39659ad397733cc4559bb97bfdaa3aaf83d62b08a33a2fac5",
        "response-fixtures.json": "c3e8196128d3cff8ddbd54aaeb2d13b5b986ee0711520efd46fc764c3b7d43cc",
        "request-identity.json": "b5125e2075779306f0a4374676d442fa3016702bdb5143bc8e3a6b7173d9dd35",
        "schema-v3-v4-diff.json": "5318a3064aa423121683800aa9b7ff2f28512c13724506c9f94a8c1b1e1b428b",
    }
    root = REPOSITORY_ROOT / "docs/experiments/suggest-moving-service-questions/v4"
    assert {name: _digest(root / name) for name in expected} == expected


def test_v4_validation_reuses_unchanged_semantic_prose_and_fallback_contracts() -> None:
    compliant = valid_response()
    compliant["prompt_version"] = "moving-service-questions-prompt-v4"
    compliant["schema_version"] = "moving-service-questions-schema-v4"
    assert validate_generated_response(compliant)[0] == "validated"

    rejected = rejected_stage_b_response()
    rejected["prompt_version"] = "moving-service-questions-prompt-v4"
    rejected["schema_version"] = "moving-service-questions-schema-v4"
    classification, codes = validate_generated_response(rejected)
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
    semantic["prompt_version"] = "moving-service-questions-prompt-v4"
    semantic["schema_version"] = "moving-service-questions-schema-v4"
    semantic["suggestions"][0]["selected_missing_information_category"] = "packing_preference"
    assert validate_generated_response(semantic)[0] == "semantic_failure"


def test_prompt_policy_stress_is_documented_as_stricter_than_lexical_validator() -> None:
    response = valid_response()
    response["prompt_version"] = "moving-service-questions-prompt-v4"
    response["schema_version"] = "moving-service-questions-schema-v4"
    response["suggestions"][0]["question"] = "Will you likely need temporary storage before final delivery?"
    response["suggestions"][0]["why_it_matters"] = "This can clarify appropriate, local moving services to discuss."
    classification, codes = validate_generated_response(response)
    assert classification == "validated"
    assert getattr(codes, "prompt_version") == "moving-service-questions-prompt-v4"


def test_cross_version_identities_and_provider_schemas_are_not_interchangeable() -> None:
    v2 = prepare_frozen_v2_pilot()
    v4 = prepare_frozen_v4_pilot()
    assert v2.request.prompt_version != v4.request.prompt_version
    assert v2.request.schema_version != v4.request.schema_version
    assert v2.provider_request.response_json_schema != v4.provider_request.response_json_schema
    with pytest.raises(Exception):
        type(v4.request).model_validate(v2.request.model_dump())
    with pytest.raises(Exception):
        type(v2.request).model_validate(v4.request.model_dump())


def test_no_v4_runtime_or_frontend_exposure() -> None:
    excluded = {SCRIPT_ROOT / "test_v4_sequence_4_generation_gate.py"}
    roots = [REPOSITORY_ROOT / "backend/app", REPOSITORY_ROOT / "frontend/src"]
    for root in roots:
        for path in root.rglob("*"):
            if path.is_file() and path not in excluded:
                assert "moving-service-questions-prompt-v4" not in path.read_text(errors="ignore")


def test_actual_live_verifier_accepts_exact_active_generation_with_closed_preflight_history(
        tmp_path, monkeypatch) -> None:
    output, repository, now = _active_generation_state(tmp_path)
    monkeypatch.setenv("GOTIME_V4_SEQUENCE_4_GENERATION_OFFLINE_TEST", "1")
    attempt = verify_live_generation_precredential(
        output_root=output, repository_root=repository, now=now)
    assert attempt.authorization_digest == _digest(generation_paths(output).active)
    assert attempt.prepared.provider_request is attempt.prepared.provider_request
    assert preflight_paths(output, repository).closure.is_file()
    assert (repository / "docs/experiments/suggest-moving-service-questions/v2-pilot/execution-manifest.json").read_bytes() == active_generation_manifest_bytes(str(attempt.authorization_digest))


def test_actual_live_runner_reaches_credential_only_after_full_active_verification(
        tmp_path, monkeypatch) -> None:
    output, repository, now = _active_generation_state(tmp_path)
    monkeypatch.setenv("GOTIME_V4_SEQUENCE_4_GENERATION_OFFLINE_TEST", "1")
    monkeypatch.setattr(live_generation, "DEFAULT_OUTPUT_ROOT", output)
    monkeypatch.setattr(live_generation, "REPOSITORY_ROOT", repository)
    events: list[str] = []

    class Environment(dict):
        def get(self, key, default=None):
            if key == "GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY":
                events.append("credential_lookup")
            return super().get(key, default)

    def verifier(**kwargs):
        events.append("full_verification")
        return verify_live_generation_precredential(**kwargs)

    attempt, credential = verify_attempt_then_read_credential(
        environment=Environment({
            "GOTIME_MOVING_SERVICE_EVAL_ENABLED": "1",
            "GOTIME_MOVING_SERVICE_EVAL_OPERATOR_INTENT": OPERATOR_INTENT,
            "GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY": "synthetic-not-a-real-credential",
        }), now=now, attempt_verifier=verifier)
    assert events == ["full_verification", "credential_lookup"]
    assert credential == "synthetic-not-a-real-credential"
    assert attempt.authorization_digest == _digest(generation_paths(output).active)


def test_closed_phase_preflight_history_still_rejects_active_generation_manifest(tmp_path) -> None:
    output, repository, _ = _active_generation_state(tmp_path)
    evidence = json.loads(preflight_paths(output, repository).evidence.read_text())
    with pytest.raises(Exception):
        generation_gate.verify_v4_preflight_history(
            evidence=evidence, output_root=output, repository_root=repository)


@pytest.mark.parametrize("case", ("wrong_authorization", "wrong_manifest"))
def test_actual_live_entry_rejects_invalid_active_state_before_all_external_boundaries(
        tmp_path, monkeypatch, case: str) -> None:
    output, repository, _ = _active_generation_state(tmp_path)
    monkeypatch.setenv("GOTIME_V4_SEQUENCE_4_GENERATION_OFFLINE_TEST", "1")
    monkeypatch.setattr(live_generation, "DEFAULT_OUTPUT_ROOT", output)
    monkeypatch.setattr(live_generation, "REPOSITORY_ROOT", repository)
    target = generation_paths(output)
    execution = repository / "docs/experiments/suggest-moving-service-questions/v2-pilot/execution-manifest.json"
    if case == "wrong_authorization":
        artifact = tomllib.loads(target.active.read_text())
        artifact["bindings"]["provider_fingerprint"] = "0" * 64
        target.active.write_bytes(_toml_bytes(artifact))
        target.review_rendered.write_bytes(target.active.read_bytes())
        _rebind_active_chain(target, execution)
    else:
        execution.write_bytes(execution.with_name("closed-execution-manifest.json").read_bytes())

    counts = {"credential": 0, "client": 0, "provider": 0}

    class Environment(dict):
        def get(self, key, default=None):
            if key == "GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY":
                counts["credential"] += 1
            return super().get(key, default)

    def client_builder(_credential):
        counts["client"] += 1
        raise AssertionError("client boundary must not be reached")

    def transport_factory(_client, _prepared):
        counts["provider"] += 1
        raise AssertionError("provider boundary must not be reached")

    with pytest.raises(Sequence4GenerationGateError):
        live_generation.run(environment=Environment({
            "GOTIME_MOVING_SERVICE_EVAL_ENABLED": "1",
            "GOTIME_MOVING_SERVICE_EVAL_OPERATOR_INTENT": OPERATOR_INTENT,
            "GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY": "synthetic-not-a-real-credential",
        }), client_builder=client_builder, transport_factory=transport_factory)
    assert counts == {"credential": 0, "client": 0, "provider": 0}


@pytest.mark.parametrize("case", (
    "wrong_frozen_manifest", "wrong_prompt", "wrong_schema", "wrong_request",
    "wrong_canonical", "wrong_fingerprint", "wrong_evidence", "wrong_review",
    "wrong_tokens", "wrong_cost", "wrong_provider", "wrong_model", "wrong_sdk",
    "wrong_intent", "preflight_limit", "generation_limit", "retries", "timeout",
    "max_output", "spend", "generation_false", "preflight_true", "grounding_false",
    "prohibited_scope", "expired", "wrong_activation_review", "wrong_activation_record",
    "wrong_transaction", "wrong_active_manifest_digest", "closed_current_manifest",
    "active_preflight_manifest", "altered_rehashed_manifest", "mutated_preflight_history",
    "broken_preflight_closure", "v3_authorization", "unresolved_authorization",
))
def test_live_boundary_semantic_mutations_fail_before_credential_access(tmp_path, case: str) -> None:
    output, repository, now = _active_generation_state(tmp_path)
    target = generation_paths(output)
    execution = repository / "docs/experiments/suggest-moving-service-questions/v2-pilot/execution-manifest.json"
    closed = execution.with_name("closed-execution-manifest.json")

    artifact_cases = {
        "wrong_frozen_manifest": ("bindings", "frozen_v4_manifest_digest", "0" * 64),
        "wrong_prompt": ("bindings", "prompt_version", "moving-service-questions-prompt-" + "v3"),
        "wrong_schema": ("bindings", "schema_version", "moving-service-questions-schema-" + "v3"),
        "wrong_request": ("bindings", "deterministic_request_digest", "0" * 64),
        "wrong_canonical": ("bindings", "canonical_attempt_digest", "0" * 64),
        "wrong_fingerprint": ("bindings", "provider_fingerprint", "0" * 64),
        "wrong_evidence": ("required_v4_preflight", "preflight_evidence_digest", "0" * 64),
        "wrong_review": ("required_v4_preflight", "preflight_review_digest", "0" * 64),
        "wrong_tokens": ("required_v4_preflight", "input_tokens", 1),
        "wrong_cost": ("required_v4_preflight", "conservative_cost", "0.03"),
        "wrong_provider": ("bindings", "provider", "Other"),
        "wrong_model": ("bindings", "ai_model_identifier", "other"),
        "wrong_sdk": ("bindings", "sdk_pin", "openai==0"),
        "wrong_intent": ("scope", "operator_intent", "WRONG"),
        "preflight_limit": ("scope", "maximum_token_preflight_requests", 1),
        "generation_limit": ("scope", "maximum_ai_generation_requests", 2),
        "retries": ("scope", "automatic_retries", 1),
        "timeout": ("scope", "ai_generation_timeout_seconds", 11),
        "max_output": ("scope", "maximum_output_tokens", 499),
        "spend": ("scope", "maximum_total_spend_usd", "0.04"),
        "generation_false": ("authorization", "ai_generation_authorized", False),
        "preflight_true": ("authorization", "token_preflight_authorized", True),
        "grounding_false": ("scope", "human_grounding_review_required", False),
        "prohibited_scope": ("scope", "production_use_authorized", True),
    }
    if case in artifact_cases or case in {"expired", "v3_authorization", "unresolved_authorization"}:
        artifact = tomllib.loads(target.active.read_text())
        if case in artifact_cases:
            section, field, value = artifact_cases[case]; artifact[section][field] = value
        elif case == "expired":
            artifact["approval"]["expires_at"] = generation_gate._stamp(now - timedelta(seconds=1))
        elif case == "v3_authorization":
            artifact["metadata"]["authorization_version"] = "moving-service-openai-v3-generation-sequence-4-v1"
        else:
            artifact["required_v4_preflight"]["binding_status"] = "fresh_v4_preflight_required"
        target.active.write_bytes(_toml_bytes(artifact)); target.review_rendered.write_bytes(target.active.read_bytes())
        _rebind_active_chain(target, execution)
    elif case == "wrong_activation_review":
        value = json.loads(target.activation_review.read_text()); value["installed_artifact_digest"] = "0" * 64
        _json(target.activation_review, value); _rebind_activation_chain(target)
    elif case == "wrong_activation_record":
        value = json.loads(target.activation.read_text()); value["authorization_digest"] = "0" * 64
        _json(target.activation, value); _rebind_transaction(target)
    elif case == "wrong_transaction":
        value = json.loads(target.transaction.read_text()); value["transaction_id"] = "wrong"
        _json(target.transaction, value)
    elif case == "wrong_active_manifest_digest":
        value = json.loads(target.activation.read_text()); value["active_manifest_digest"] = "0" * 64
        _json(target.activation, value); _rebind_transaction(target)
    elif case == "closed_current_manifest": execution.write_bytes(closed.read_bytes())
    elif case == "active_preflight_manifest": _json(execution, {"status": "active_v4_preflight_only"})
    elif case == "altered_rehashed_manifest":
        value = json.loads(execution.read_text()); value["maximum_ai_generation_requests"] = 2
        _json(execution, value); activation = json.loads(target.activation.read_text())
        activation["active_manifest_digest"] = _digest(execution); _json(target.activation, activation); _rebind_transaction(target)
    elif case in {"mutated_preflight_history", "broken_preflight_closure"}:
        history = preflight_paths(output, repository)
        source = history.audit if case == "mutated_preflight_history" else history.closure
        value = json.loads(source.read_text()); value["run_series_id"] = "mutated"; _json(source, value)

    credential_lookup_attempted = False
    try:
        verify_live_generation_precredential(output_root=output, repository_root=repository,
            now=now, history_verifier=_synthetic_history_verifier)
        credential_lookup_attempted = True
    except (Sequence4GenerationGateError, Exception):
        pass
    assert credential_lookup_attempted is False


def _rebind_active_chain(target, execution: Path) -> None:
    authorization_digest = _digest(target.active)
    installation = json.loads(target.installation.read_text()); installation["installed_digest"] = authorization_digest
    _json(target.installation, installation)
    review = json.loads(target.activation_review.read_text()); review["installed_artifact_digest"] = authorization_digest
    review["installation_record_digest"] = _digest(target.installation); _json(target.activation_review, review)
    execution.write_bytes(active_generation_manifest_bytes(authorization_digest))
    activation = json.loads(target.activation.read_text()); activation["authorization_digest"] = authorization_digest
    activation["installation_record_digest"] = _digest(target.installation)
    activation["activation_review_digest"] = _digest(target.activation_review)
    activation["active_manifest_digest"] = _digest(execution)
    activation["transaction_id"] = hashlib.sha256(
        f"{authorization_digest}:{activation['activated_at']}".encode()).hexdigest()[:32]
    _json(target.activation, activation); _rebind_transaction(target)


def _rebind_activation_chain(target) -> None:
    activation = json.loads(target.activation.read_text())
    activation["activation_review_digest"] = _digest(target.activation_review)
    _json(target.activation, activation); _rebind_transaction(target)


def _rebind_transaction(target) -> None:
    transaction = json.loads(target.transaction.read_text())
    activation = json.loads(target.activation.read_text())
    transaction["transaction_id"] = activation["transaction_id"]
    transaction["artifact_digest"] = activation["authorization_digest"]
    transaction["activation_record_digest"] = _digest(target.activation)
    _json(target.transaction, transaction)
