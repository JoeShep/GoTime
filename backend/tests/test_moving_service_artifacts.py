import sys
from pathlib import Path

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
    assert result["manifest"]["adapter_implementation_authorized"] is False
    assert result["manifest"]["real_model_execution_authorized"] is False
    assert result["manifest"]["real_model_evaluation_eligible"] is False
    assert result["knowledge_item_count"] == 1
    assert len(result["request_fixtures"]) == 3
    assert len(result["response_results"]) == 10
    assert len(result["execution_results"]) == 7


def test_production_experiment_does_not_load_document_artifacts(
    monkeypatch,
) -> None:
    def reject_file_access(*args, **kwargs):
        raise AssertionError("Production experiment attempted file access.")

    monkeypatch.setattr("builtins.open", reject_file_access)

    result = run_experiment(ExperimentFixture.STORAGE_UNKNOWN)

    assert result.suggestion is not None
    assert result.source == "fake_ai_adapter"
