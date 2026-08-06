"""Fixed loader boundary for the inactive sequence-3 preflight candidate."""

from __future__ import annotations

import copy
import hashlib
import json
import tomllib
from pathlib import Path

from v2_phase_authorization_candidates import (
    REPOSITORY_ROOT,
    UMBRELLA_DIGEST,
    V2PhaseCandidateError,
    VerifiedPhaseCandidate,
    validate_inactive_phase_candidate,
)
from v2_sequence_2_authorization_candidate import (
    CANDIDATE_PATH as SEQUENCE_2_CANDIDATE_PATH,
    SEQUENCE_1_CANDIDATE_DIGEST,
    _expected_manifest_bindings,
)

SEQUENCE = 3
AUDIT_PREFIX = "003-storage_unknown"
SEQUENCE_2_CANDIDATE_DIGEST = "389ab7811bd56d650e84d2f3e46c7d3f8f5e5cab6eee58019602b132d106bf7f"
PACKAGE_ROOT = REPOSITORY_ROOT / (
    "docs/experiments/suggest-moving-service-questions/v2-pilot/authorization-review/"
    "phase-candidates/sequence-3"
)
CANDIDATE_PATH = PACKAGE_ROOT / "inactive-sequence-3-preflight-authorization-candidate.toml"
MANIFEST_PATH = PACKAGE_ROOT / "sequence-3-candidate-manifest.json"


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _regular_bytes(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise V2PhaseCandidateError("Sequence-3 candidate package path is unsafe.")
    return path.read_bytes()


def load_sequence_3_preflight_candidate(phase: str = "preflight") -> VerifiedPhaseCandidate:
    if phase != "preflight":
        raise V2PhaseCandidateError("Sequence-3 package supports preflight only.")
    candidate_bytes = _regular_bytes(CANDIDATE_PATH)
    manifest = json.loads(_regular_bytes(MANIFEST_PATH))
    candidate_digest = hashlib.sha256(candidate_bytes).hexdigest()
    expected_keys = {
        "capability", "manifest_version", "purpose", "package_status", "digest_algorithm",
        "sequence", "audit_prefix", "sequence_3_candidate_path", "sequence_3_candidate_digest",
        "sequence_2_candidate_path", "sequence_2_candidate_digest", "sequence_2_role",
        "sequence_1_candidate_path", "sequence_1_candidate_digest", "sequence_1_role",
        "umbrella_candidate_path", "umbrella_candidate_digest", "frozen_v2_manifest_digest",
        "prompt_digest", "provider_schema_digest", "provider_schema_review_digest",
        "schema_adaptation_digest", "deterministic_baseline_digest", "request_fixtures_digest",
        "response_fixtures_digest", "expected_results_digest", "follow_up_pilot_configuration_digest",
        "permanent_closed_execution_manifest_digest", "permanent_closed_authorization_digest",
        "active_repository_authority", "valid_for_execution", "credential_access_authorized",
        "token_preflight_authorized", "ai_generation_authorized", "formal_evaluation_authorized",
        "stage_c_authorized", "production_use_authorized",
    }
    if set(manifest) != expected_keys:
        raise V2PhaseCandidateError("Sequence-3 candidate manifest shape drifted.")
    required = {
        "capability": "suggest_moving_service_questions",
        "manifest_version": "moving-service-openai-v2-preflight-sequence-3-candidate-manifest-v1",
        "purpose": "inactive_sequence_3_preflight_authorization_review",
        "package_status": "inactive_non_authoritative",
        "sequence": SEQUENCE,
        "audit_prefix": AUDIT_PREFIX,
        "sequence_3_candidate_path": str(CANDIDATE_PATH.relative_to(REPOSITORY_ROOT)),
        "sequence_3_candidate_digest": candidate_digest,
        "sequence_2_candidate_digest": SEQUENCE_2_CANDIDATE_DIGEST,
        "sequence_1_candidate_digest": SEQUENCE_1_CANDIDATE_DIGEST,
        "umbrella_candidate_digest": UMBRELLA_DIGEST,
    }
    if any(manifest.get(key) != value for key, value in required.items()):
        raise V2PhaseCandidateError("Sequence-3 candidate manifest drifted.")
    if (
        _digest(REPOSITORY_ROOT / manifest["sequence_2_candidate_path"])
        != SEQUENCE_2_CANDIDATE_DIGEST
        or (REPOSITORY_ROOT / manifest["sequence_2_candidate_path"]).resolve()
        != SEQUENCE_2_CANDIDATE_PATH.resolve()
        or _digest(REPOSITORY_ROOT / manifest["sequence_1_candidate_path"])
        != SEQUENCE_1_CANDIDATE_DIGEST
        or _digest(REPOSITORY_ROOT / manifest["umbrella_candidate_path"]) != UMBRELLA_DIGEST
    ):
        raise V2PhaseCandidateError("Historical candidate binding drifted.")
    for key, value in _expected_manifest_bindings().items():
        if manifest.get(key) != value:
            raise V2PhaseCandidateError("Sequence-3 frozen binding drifted.")
    if any(manifest.get(key) is not False for key in (
        "active_repository_authority", "valid_for_execution", "credential_access_authorized",
        "token_preflight_authorized", "ai_generation_authorized", "formal_evaluation_authorized",
        "stage_c_authorized", "production_use_authorized",
    )):
        raise V2PhaseCandidateError("Sequence-3 manifest grants authority.")
    artifact = tomllib.loads(candidate_bytes.decode("utf-8"))
    if (
        artifact.get("metadata", {}).get("candidate_version")
        != "moving-service-openai-v2-preflight-sequence-3-candidate-v1"
        or artifact.get("scope", {}).get("sequence") != SEQUENCE
    ):
        raise V2PhaseCandidateError("Sequence-3 candidate identity drifted.")
    compatibility = copy.deepcopy(artifact)
    compatibility["metadata"]["candidate_version"] = "moving-service-openai-v2-preflight-candidate-v1"
    compatibility["scope"]["sequence"] = 1
    blockers = validate_inactive_phase_candidate(compatibility, phase="preflight")
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
    if any(manifest[key] != artifact["bindings"][binding] for key, binding in manifest_to_binding.items()):
        raise V2PhaseCandidateError("Sequence-3 manifest and candidate bindings differ.")
    return VerifiedPhaseCandidate("preflight", CANDIDATE_PATH, candidate_digest, artifact, blockers)
