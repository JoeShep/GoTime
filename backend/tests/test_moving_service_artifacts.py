import copy
import sys
from pathlib import Path

import pytest

from app.moving_service_questions import ExperimentFixture, run_experiment


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_SCRIPT_ROOT = (
    REPOSITORY_ROOT
    / "scripts/experiments/suggest_moving_service_questions"
)
if str(ARTIFACT_SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(ARTIFACT_SCRIPT_ROOT))

import evaluate_baseline as artifact_compatibility


def test_v1_artifacts_are_compatible_with_runtime_contracts() -> None:
    result = artifact_compatibility.validate_artifacts(
        artifact_compatibility.load_artifacts()
    )

    assert result["manifest"]["contract_test_eligible"] is True
    assert result["manifest"]["prompt_artifact_ready"] is True
    assert result["manifest"]["prompt_artifact_reviewed"] is True
    assert (
        result["manifest"]["prompt_artifact_frozen_for_adapter_implementation"]
        is True
    )
    assert result["manifest"]["adapter_implementation_authorized"] is False
    assert result["manifest"]["real_model_execution_authorized"] is False
    assert result["manifest"]["real_model_evaluation_eligible"] is False
    assert result["manifest"]["openai_run_configuration_approved"] is True
    assert result["manifest"]["openai_run_configuration_frozen"] is True
    assert (
        result["manifest"]["openai_response_schema_status"]
        == "reviewed_and_frozen"
    )
    assert result["openai_run_configuration_sha256"] == (
        "e665e04b56d8aeaa01f4c9df2fd2f5f4eed37150802fdba869cba54d1e5bc782"
    )
    assert result["openai_response_schema_sha256"] == (
        "9e5a3a667a1049d150734fd16669dad98cc982c2dc7a9a18f3e0b8cb3e891afb"
    )
    assert result["manifest"]["openai_execution_authorization_status"] == (
        "closed_no_execution_authorized"
    )
    assert result["openai_execution_authorization_sha256"] == (
        "6e3ca9cb4488764f012703ab77daae4f4b952895100f7d935935aeb6a0978be5"
    )
    assert result["manifest"][
        "openai_stage_a_authorization_candidate_activated"
    ] is False
    assert result["openai_stage_a_authorization_candidate_sha256"] == (
        "b523426249b9c697f0ad8fa5c7e3cdc0d965db35c5ab5f8f1a7dc66fd4655202"
    )
    assert result["knowledge_item_count"] == 1
    assert len(result["request_fixtures"]) == 3
    assert len(result["response_results"]) == 10
    assert len(result["execution_results"]) == 7


def test_openai_response_schema_snapshot_rejects_drift() -> None:
    artifacts = artifact_compatibility.load_artifacts()
    drifted = copy.deepcopy(artifacts)
    del drifted["openai_response_schema"]["properties"]["capability"]

    with pytest.raises(
        artifact_compatibility.ArtifactValidationError,
        match="snapshot has drifted",
    ):
        artifact_compatibility.validate_artifacts(drifted)


def test_openai_run_configuration_rejects_authorization_drift() -> None:
    artifacts = artifact_compatibility.load_artifacts()
    drifted = copy.deepcopy(artifacts)
    drifted["openai_run_configuration"]["status"][
        "real_model_execution_authorized"
    ] = True

    with pytest.raises(
        artifact_compatibility.ArtifactValidationError,
        match="real_model_execution_authorized must be False",
    ):
        artifact_compatibility.validate_artifacts(drifted)


def test_openai_run_configuration_rejects_digest_drift() -> None:
    artifacts = artifact_compatibility.load_artifacts()
    drifted = copy.deepcopy(artifacts)
    drifted["openai_run_configuration_sha256"] = "0" * 64

    with pytest.raises(
        artifact_compatibility.ArtifactValidationError,
        match="digest does not match exact bytes",
    ):
        artifact_compatibility.validate_artifacts(drifted)


def test_openai_execution_authorization_rejects_permission_drift() -> None:
    artifacts = artifact_compatibility.load_artifacts()
    drifted = copy.deepcopy(artifacts)
    drifted["openai_execution_authorization"]["authorization"][
        "credential_access_authorized"
    ] = True

    with pytest.raises(
        artifact_compatibility.ArtifactValidationError,
        match="credential_access_authorized must be False",
    ):
        artifact_compatibility.validate_artifacts(drifted)


def test_openai_execution_authorization_rejects_digest_drift() -> None:
    artifacts = artifact_compatibility.load_artifacts()
    drifted = copy.deepcopy(artifacts)
    drifted["openai_execution_authorization_sha256"] = "0" * 64

    with pytest.raises(
        artifact_compatibility.ArtifactValidationError,
        match="digest does not match exact bytes",
    ):
        artifact_compatibility.validate_artifacts(drifted)


def test_openai_stage_a_candidate_rejects_activation_drift() -> None:
    artifacts = artifact_compatibility.load_artifacts()
    drifted = copy.deepcopy(artifacts)
    drifted["manifest"][
        "openai_stage_a_authorization_candidate_activated"
    ] = True

    with pytest.raises(
        artifact_compatibility.ArtifactValidationError,
        match="candidate_activated is incompatible",
    ):
        artifact_compatibility.validate_artifacts(drifted)


def test_openai_stage_a_candidate_rejects_generation_permission() -> None:
    artifacts = artifact_compatibility.load_artifacts()
    drifted = copy.deepcopy(artifacts)
    drifted["openai_stage_a_authorization_candidate"]["authorization"][
        "ai_generation_authorized"
    ] = True

    with pytest.raises(
        artifact_compatibility.ArtifactValidationError,
        match="candidate permissions are incompatible",
    ):
        artifact_compatibility.validate_artifacts(drifted)


def test_production_experiment_does_not_load_document_artifacts(
    monkeypatch,
) -> None:
    def reject_file_access(*args, **kwargs):
        raise AssertionError("Production experiment attempted file access.")

    monkeypatch.setattr("builtins.open", reject_file_access)

    result = run_experiment(ExperimentFixture.STORAGE_UNKNOWN)

    assert result.suggestion is not None
    assert result.source == "fake_ai_adapter"
