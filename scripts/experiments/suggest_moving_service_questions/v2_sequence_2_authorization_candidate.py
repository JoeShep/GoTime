"""Fixed loader and renderer boundary for the inactive sequence-2 candidate."""

from __future__ import annotations

import copy
import hashlib
import json
import tomllib
from pathlib import Path
from typing import Mapping

from run_openai_stage_b_v2_pilot import prepare_frozen_v2_pilot
from run_openai_stage_b_v2_two_gate import frozen_binding_identity
from v2_phase_authorization_candidates import (
    REPOSITORY_ROOT,
    UMBRELLA_DIGEST,
    V2PhaseCandidateError,
    VerifiedPhaseCandidate,
    validate_inactive_phase_candidate,
)

SEQUENCE = 2
AUDIT_PREFIX = "002-storage_unknown"
SEQUENCE_1_CANDIDATE_DIGEST = "a3f1000bb1b336bad4fb35e9316520f59eb1eeb96e257f19eb13e9d495504a6c"
PACKAGE_ROOT = REPOSITORY_ROOT / (
    "docs/experiments/suggest-moving-service-questions/v2-pilot/authorization-review/"
    "phase-candidates/sequence-2"
)
CANDIDATE_PATH = PACKAGE_ROOT / "inactive-sequence-2-preflight-authorization-candidate.toml"
MANIFEST_PATH = PACKAGE_ROOT / "sequence-2-candidate-manifest.json"


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _regular_bytes(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise V2PhaseCandidateError("Sequence-2 candidate package path is unsafe.")
    return path.read_bytes()


def _expected_manifest_bindings() -> Mapping[str, object]:
    binding = frozen_binding_identity(prepare_frozen_v2_pilot())
    return {
        "frozen_v2_manifest_digest": binding["frozen_v2_manifest_digest"],
        "prompt_digest": binding["prompt_digest"],
        "provider_schema_digest": binding["provider_schema_digest"],
        "follow_up_pilot_configuration_digest": binding["pilot_configuration_digest"],
    }


def load_sequence_2_preflight_candidate(phase: str = "preflight") -> VerifiedPhaseCandidate:
    """Load only the fixed sequence-2 preflight candidate and verify every binding."""
    if phase != "preflight":
        raise V2PhaseCandidateError("Sequence-2 package supports preflight only.")
    manifest_bytes = _regular_bytes(MANIFEST_PATH)
    candidate_bytes = _regular_bytes(CANDIDATE_PATH)
    manifest = json.loads(manifest_bytes)
    candidate_digest = hashlib.sha256(candidate_bytes).hexdigest()
    expected_manifest_keys = {
        "capability", "manifest_version", "purpose", "package_status", "digest_algorithm",
        "sequence", "audit_prefix", "sequence_2_candidate_path", "sequence_2_candidate_digest",
        "sequence_1_candidate_path", "sequence_1_candidate_digest", "sequence_1_role",
        "umbrella_candidate_path", "umbrella_candidate_digest", "frozen_v2_manifest_digest",
        "prompt_digest", "provider_schema_digest", "provider_schema_review_digest",
        "schema_adaptation_digest", "deterministic_baseline_digest", "request_fixtures_digest",
        "response_fixtures_digest", "expected_results_digest",
        "follow_up_pilot_configuration_digest", "permanent_closed_execution_manifest_digest",
        "permanent_closed_authorization_digest", "active_repository_authority",
        "valid_for_execution", "credential_access_authorized", "token_preflight_authorized",
        "ai_generation_authorized", "formal_evaluation_authorized", "stage_c_authorized",
        "production_use_authorized",
    }
    if (
        set(manifest) != expected_manifest_keys
        or manifest.get("capability") != "suggest_moving_service_questions"
        or manifest.get("manifest_version")
        != "moving-service-openai-v2-preflight-sequence-2-candidate-manifest-v1"
        or manifest.get("purpose") != "inactive_sequence_2_preflight_authorization_review"
        or manifest.get("package_status") != "inactive_non_authoritative"
        or manifest.get("sequence") != SEQUENCE
        or manifest.get("audit_prefix") != AUDIT_PREFIX
        or manifest.get("sequence_2_candidate_path")
        != str(CANDIDATE_PATH.relative_to(REPOSITORY_ROOT))
        or manifest.get("sequence_2_candidate_digest") != candidate_digest
        or manifest.get("sequence_1_candidate_digest") != SEQUENCE_1_CANDIDATE_DIGEST
        or manifest.get("sequence_1_role") != "historical_non_authority"
        or manifest.get("umbrella_candidate_digest") != UMBRELLA_DIGEST
        or any(manifest.get(key) is not False for key in (
            "active_repository_authority", "valid_for_execution",
            "credential_access_authorized", "token_preflight_authorized",
            "ai_generation_authorized", "formal_evaluation_authorized",
            "stage_c_authorized", "production_use_authorized",
        ))
    ):
        raise V2PhaseCandidateError("Sequence-2 candidate manifest drifted or grants authority.")
    sequence_1_path = REPOSITORY_ROOT / str(manifest["sequence_1_candidate_path"])
    umbrella_path = REPOSITORY_ROOT / str(manifest["umbrella_candidate_path"])
    if (
        sequence_1_path.resolve()
        != CANDIDATE_PATH.parent.parent / "inactive-preflight-authorization-candidate.toml"
        or _digest(sequence_1_path) != SEQUENCE_1_CANDIDATE_DIGEST
        or _digest(umbrella_path) != UMBRELLA_DIGEST
    ):
        raise V2PhaseCandidateError("Historical candidate or umbrella binding drifted.")
    for key, value in _expected_manifest_bindings().items():
        if manifest.get(key) != value:
            raise V2PhaseCandidateError("Sequence-2 frozen binding drifted.")
    artifact = tomllib.loads(candidate_bytes.decode("utf-8"))
    if (
        artifact.get("metadata", {}).get("candidate_version")
        != "moving-service-openai-v2-preflight-sequence-2-candidate-v1"
        or artifact.get("scope", {}).get("sequence") != SEQUENCE
    ):
        raise V2PhaseCandidateError("Sequence-2 candidate identity drifted.")
    # Reuse the reviewed v1 phase validator after substituting only its two
    # intentionally versioned identity fields in an in-memory copy.
    compatibility = copy.deepcopy(artifact)
    compatibility["metadata"]["candidate_version"] = "moving-service-openai-v2-preflight-candidate-v1"
    compatibility["scope"]["sequence"] = 1
    blockers = validate_inactive_phase_candidate(compatibility, phase="preflight")
    if artifact["bindings"] != compatibility["bindings"]:
        raise V2PhaseCandidateError("Sequence-2 candidate broadened frozen bindings.")
    manifest_to_binding = {
        "provider_schema_review_digest": "provider_schema_review_digest",
        "schema_adaptation_digest": "schema_adaptation_digest",
        "deterministic_baseline_digest": "deterministic_baseline_digest",
        "request_fixtures_digest": "request_fixtures_digest",
        "response_fixtures_digest": "response_fixtures_digest",
        "expected_results_digest": "expected_results_digest",
        "permanent_closed_execution_manifest_digest": "closed_execution_manifest_digest",
        "permanent_closed_authorization_digest": "permanent_closed_authorization_digest",
    }
    if any(manifest[key] != artifact["bindings"][binding_key] for key, binding_key in manifest_to_binding.items()):
        raise V2PhaseCandidateError("Sequence-2 manifest and candidate bindings differ.")
    return VerifiedPhaseCandidate("preflight", CANDIDATE_PATH, candidate_digest, artifact, blockers)
