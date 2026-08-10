"""Offline tests for the frozen-v4 formal evaluation runner."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from freeze_v4_formal_evaluation_set import EMPTY_CASE_IDS, GENERATION_CASE_IDS, PACKAGE_ROOT
from v4_formal_evaluation_runner import (
    CaseDisposition,
    CaseState,
    DurableEvaluationLedger,
    EvaluationRunnerError,
    FormalEvaluationRunner,
    HumanReview,
    ReviewDecision,
    RUNNER_ID,
    SET_ID,
    SyntheticCasePlan,
    SyntheticEvaluationTransport,
    SyntheticPreflightEvidence,
    nominal_review,
    rehearse_scenario,
    score_outcomes,
    synthetic_response,
    validate_case_response,
    _digest,
)


EXPECTED_ARTIFACTS = {
    "v4-formal-evaluation-plan.md": "5c5d84effe84fa7a951ae991759db05b2fea1038f4ef20a8aa297a3feff78a22",
    "v4-formal-evaluation/execution-budget.json": "0d848bce8866023a5b7f7912795a6ee80b3aae471189f447911244da10777b6b",
    "v4-formal-evaluation/manifest.json": "38c4db2e92368ead41f9c6f87146a83103ae7780328aa7423d13340239134e94",
    "v4-formal-evaluation/evaluation-cases.json": "64251f882287dae201f6b23aa33df00b137b9c5585d5c95fb78c1046840cb458",
    "v4-formal-evaluation/expected-behavior.json": "6ecf327b80ecf52bb8766502e6329a866353066096d6339153f284e6e56e47df",
    "v4-formal-evaluation/request-identities.json": "a23de86e93c3b83b7d51ffa5f73c5d694cd8266c5013c6d14833ad64bddd40ee",
}

PUBLIC_COMMANDS = (
    "verify_v4_formal_evaluation_set.sh",
    "preview_v4_formal_evaluation_package.sh",
    "rehearse_v4_formal_evaluation.sh",
    "run_v4_formal_evaluation_empty_case.sh",
    "run_v4_formal_evaluation_preflight_case.sh",
    "run_v4_formal_evaluation_generation_case.sh",
    "record_v4_formal_evaluation_review.sh",
    "delete_v4_formal_evaluation_evidence.sh",
    "finalize_v4_formal_evaluation_report.sh",
    "verify_v4_formal_evaluation_result.sh",
    "close_v4_formal_evaluation_state.sh",
)


def test_frozen_evaluation_artifacts_remain_exact() -> None:
    root = PACKAGE_ROOT.parent
    for name, digest in EXPECTED_ARTIFACTS.items():
        assert hashlib.sha256((root / name).read_bytes()).hexdigest() == digest


def test_fixed_offline_public_command_inventory() -> None:
    script_root = Path(__file__).parent
    runbook = (
        PACKAGE_ROOT.parent / "v4-formal-evaluation-runner.md"
    ).read_text()
    assert len(PUBLIC_COMMANDS) == 11
    for name in PUBLIC_COMMANDS:
        path = script_root / name
        assert path.is_file()
        assert path.stat().st_mode & 0o111
        assert name in runbook
        assert "v4_formal_evaluation_offline.sh" in path.read_text()


def test_offline_wrapper_has_no_network_or_credential_surface() -> None:
    wrapper = (Path(__file__).parent / "v4_formal_evaluation_offline.sh").read_text()
    assert "--network none" in wrapper
    assert ":/workspace:ro" in wrapper
    assert "OPENAI_API_KEY" not in wrapper
    cli = (Path(__file__).parent / "v4_formal_evaluation_cli.py").read_text()
    assert "OpenAI(" not in cli


def test_runner_identity_and_nominal_state_machine() -> None:
    runner = FormalEvaluationRunner()
    assert RUNNER_ID == "suggest-moving-service-questions-v4-formal-evaluation-runner-v1"
    generated = runner.run_case("eval-v4-01")
    assert generated.state_history == (
        CaseState.PENDING, CaseState.PREFLIGHT_READY, CaseState.PREFLIGHT_COMPLETE,
        CaseState.GENERATION_READY, CaseState.GENERATION_COMPLETE,
        CaseState.AWAITING_HUMAN_REVIEW, CaseState.HUMAN_REVIEW_COMPLETE,
        CaseState.CASE_COMPLETE,
    )
    empty = runner.run_case("eval-v4-07")
    assert empty.state_history == (
        CaseState.PENDING, CaseState.DETERMINISTIC_EMPTY_COMPLETE, CaseState.CASE_COMPLETE
    )


@pytest.mark.parametrize("case_id", EMPTY_CASE_IDS)
def test_deterministic_empty_cases_never_construct_or_call_provider(case_id: str) -> None:
    runner = FormalEvaluationRunner()
    outcome = runner.run_case(case_id)
    assert outcome.deterministic_eligibility == "empty"
    assert outcome.provider_request_expected is False
    assert outcome.token_preflight_count == 0
    assert outcome.generation_attempt_count == 0
    assert outcome.retry_count == 0
    assert outcome.expected_empty_correctness is True
    assert outcome.deterministic_request_sha256 is None
    assert outcome.canonical_attempt_sha256 is None
    assert outcome.provider_fingerprint is None


def test_generation_cases_reproduce_exact_frozen_identities() -> None:
    identities = {
        item["case_id"]: item
        for item in json.loads((PACKAGE_ROOT / "request-identities.json").read_text())[
            "request_identities"
        ]
    }
    runner = FormalEvaluationRunner()
    for case_id in GENERATION_CASE_IDS:
        outcome = runner.run_case(case_id)
        assert (
            outcome.deterministic_request_sha256,
            outcome.canonical_attempt_sha256,
            outcome.provider_fingerprint,
        ) == (
            identities[case_id]["deterministic_request_sha256"],
            identities[case_id]["canonical_attempt_sha256"],
            identities[case_id]["provider_fingerprint"],
        )


def test_same_verified_provider_request_object_reaches_synthetic_transport() -> None:
    runner = FormalEvaluationRunner()
    outcome = runner.run_case("eval-v4-01")
    assert outcome.generation_attempt_count == 1
    assert outcome.token_preflight_count == 1
    assert outcome.retry_count == 0


def test_case_cannot_be_rerun_or_replaced() -> None:
    runner = FormalEvaluationRunner()
    first = runner.run_case("eval-v4-01")
    with pytest.raises(EvaluationRunnerError, match="already has a terminal outcome"):
        runner.run_case("eval-v4-01")
    assert runner.ledger["eval-v4-01"] == first


def test_failed_provider_case_consumes_slot_and_cannot_be_replaced() -> None:
    runner = FormalEvaluationRunner(scenario="provider_failure")
    outcome = runner.run_case("eval-v4-06")
    assert outcome.final_case_disposition is CaseDisposition.TRANSPORT_FAILURE
    assert outcome.generation_attempt_count == 1
    with pytest.raises(EvaluationRunnerError, match="already has a terminal outcome"):
        runner.run_case("eval-v4-06")


def test_case_specific_preflight_cannot_cross_case_or_be_reused() -> None:
    evidence = SyntheticPreflightEvidence(
        case_id="eval-v4-01", identity=("a", "b", "c"),
        input_tokens=100, conservative_cost="0.01",
    )
    with pytest.raises(EvaluationRunnerError, match="case-specific preflight evidence rejected"):
        evidence.consume(case_id="eval-v4-02", identity=("a", "b", "c"))
    evidence.consume(case_id="eval-v4-01", identity=("a", "b", "c"))
    with pytest.raises(EvaluationRunnerError, match="case-specific preflight evidence rejected"):
        evidence.consume(case_id="eval-v4-01", identity=("a", "b", "c"))


def test_synthetic_transport_rejects_materially_different_request_object() -> None:
    runner = FormalEvaluationRunner()
    source = runner.cases["eval-v4-01"]
    captured = []

    def constructor(**kwargs):
        from real_model_adapter import MovingServiceProviderRequest
        value = MovingServiceProviderRequest(**kwargs)
        captured.append(value)
        return value

    from freeze_v4_formal_evaluation_set import bind_case
    _, _, identity = bind_case(source, runner.metadata, constructor)
    triple = tuple(identity[key] for key in (
        "deterministic_request_sha256", "canonical_attempt_sha256", "provider_fingerprint"
    ))
    plan = SyntheticCasePlan(review=nominal_review(0))
    transport = SyntheticEvaluationTransport(case_id="eval-v4-01", identity=triple, plan=plan)
    evidence = transport.preflight(captured[0], input_tokens=100, conservative_cost="0.01")
    _, _, _ = bind_case(source, runner.metadata, constructor)
    with pytest.raises(EvaluationRunnerError, match="verified prepared request object was not reused"):
        transport.generate(captured[1], evidence)


def test_nominal_rehearsal_graduates_with_mixed_passing_quality() -> None:
    report = rehearse_scenario("nominal")
    assert report.final_disposition == "graduate"
    assert report.hard_gate_result == "pass"
    assert report.quality_gate_result == "pass"
    assert report.generation_attempts_used == 8
    assert report.token_preflights_used == 8
    assert report.deterministic_empty_results == 2
    assert report.retries == 0
    assert report.average_clarity == "4.38"
    assert report.average_usefulness == "4.25"
    assert report.fallback_comparison_distribution["slightly_better"]["count"] == 4
    assert report.fallback_comparison_distribution["equivalent"]["count"] == 3
    assert report.better_than_fallback_percentage == "62.50"
    assert report.equivalent_to_fallback_percentage == "37.50"
    assert report.worse_than_fallback_percentage == "0.00"


def test_hard_gate_failure_rehearsal_fails() -> None:
    report = rehearse_scenario("hard_gate_failure")
    assert report.final_disposition == "fail"
    assert report.hard_gate_result == "fail"
    assert report.invented_fact_count == 1


def test_quality_gate_failure_remains_experimental() -> None:
    report = rehearse_scenario("quality_gate_failure")
    assert report.final_disposition == "remain_experimental"
    assert report.hard_gate_result == "pass"
    assert report.quality_gate_result == "fail"
    assert report.average_usefulness == "3.00"


def test_provider_failure_is_distinct_and_remains_experimental() -> None:
    report = rehearse_scenario("provider_failure")
    assert report.final_disposition == "remain_experimental"
    assert report.provider_transport_failure_count == 1
    assert report.hard_gate_result == "pass"
    failed = next(item for item in report.case_result_table if item["case_id"] == "eval-v4-06")
    assert failed["final_case_disposition"] == "transport_failure"


@pytest.mark.parametrize(
    ("scenario", "hard_result"),
    (("structural_failure", "fail"), ("semantic_failure", "fail"),
     ("prose_failure", "fail")),
)
def test_automated_failure_scenarios_remain_distinct(scenario: str, hard_result: str) -> None:
    runner = FormalEvaluationRunner(scenario=scenario)
    outcome = runner.run_case("eval-v4-03")
    assert outcome.final_case_disposition is CaseDisposition.AUTOMATED_REJECTED
    assert outcome.validated_response_evidence_sha256 is None
    assert outcome.human_review_applicable is False
    report = runner
    for case_id in tuple(GENERATION_CASE_IDS[:2]) + tuple(GENERATION_CASE_IDS[3:6]) + EMPTY_CASE_IDS + tuple(GENERATION_CASE_IDS[6:]):
        report.run_case(case_id)
    scored = score_outcomes(tuple(report.ledger.values()))
    assert scored.hard_gate_result == hard_result


def test_prose_rejection_retains_only_bounded_diagnostics_and_fallback() -> None:
    runner = FormalEvaluationRunner(scenario="prose_failure")
    outcome = runner.run_case("eval-v4-03")
    assert outcome.ordered_prose_violation_codes == (
        "storage_modality_overstatement", "unsupported_service_selection_language"
    )
    assert outcome.fallback_selected is True
    assert outcome.fallback_version == "moving-service-fallback-v2"
    assert outcome.fallback_question_id == "fallback-temporary-storage-v2"
    serialized = outcome.model_dump_json()
    assert "You will need storage" not in serialized
    for diagnostic in outcome.bounded_rejected_prose_diagnostics:
        assert set(diagnostic) == {
            "violation_code", "rule_id", "field", "start_offset", "end_offset",
            "canonical_trigger", "occurrence_count",
        }


def test_human_review_is_mandatory_and_evidence_is_deleted_after_review() -> None:
    outcome = FormalEvaluationRunner().run_case("eval-v4-01")
    assert outcome.human_review_applicable is True
    assert outcome.human_review_decision == "approve"
    assert outcome.validated_response_evidence_sha256
    assert outcome.human_review_sha256
    assert outcome.evidence_deletion_sha256
    assert outcome.response_evidence_deleted is True
    assert "response" not in outcome.model_dump(mode="json")


@pytest.mark.parametrize("decision", (ReviewDecision.REJECT, ReviewDecision.REQUEST_CHANGES))
def test_nonapproval_human_review_is_terminal_and_still_deletes_evidence(
    decision: ReviewDecision,
) -> None:
    runner = FormalEvaluationRunner()
    runner.plans["eval-v4-01"] = SyntheticCasePlan(
        review=nominal_review(0).model_copy(update={"decision": decision})
    )
    outcome = runner.run_case("eval-v4-01")
    assert outcome.final_case_disposition is CaseDisposition.HUMAN_REJECTED
    assert outcome.response_evidence_deleted is True
    assert outcome.generation_attempt_count == 1
    with pytest.raises(EvaluationRunnerError, match="already has a terminal outcome"):
        runner.run_case("eval-v4-01")


def test_validated_response_without_review_fails_closed() -> None:
    runner = FormalEvaluationRunner()
    runner.plans["eval-v4-01"] = SyntheticCasePlan(review=None)
    with pytest.raises(EvaluationRunnerError, match="mandatory human review"):
        runner.run_case("eval-v4-01")


def test_report_is_deterministic_and_clearly_synthetic() -> None:
    first = rehearse_scenario("nominal")
    second = rehearse_scenario("nominal")
    assert first.model_dump_json() == second.model_dump_json()
    assert first.synthetic_rehearsal is True
    assert "not a statistically representative reliability study" in first.bounded_evaluation_statement


def test_budget_enforcement_fails_closed() -> None:
    runner = FormalEvaluationRunner()
    runner.generations = 9
    with pytest.raises(EvaluationRunnerError, match="generation budget exceeded"):
        runner._enforce_budget()
    runner.generations = 0
    runner.preflights = 9
    with pytest.raises(EvaluationRunnerError, match="preflight budget exceeded"):
        runner._enforce_budget()
    runner.preflights = 0
    runner.retries = 1
    with pytest.raises(EvaluationRunnerError, match="retry budget exceeded"):
        runner._enforce_budget()


def test_aggregate_provider_spend_fails_closed() -> None:
    runner = FormalEvaluationRunner()
    runner.run_all()
    outcomes = tuple(
        item.model_copy(update={"synthetic_conservative_cost_usd": "0.04"})
        if item.case_id in GENERATION_CASE_IDS else item
        for item in runner.ledger.values()
    )
    with pytest.raises(EvaluationRunnerError, match="provider spend budget exceeded"):
        score_outcomes(outcomes)


def test_scoring_threshold_boundaries() -> None:
    runner = FormalEvaluationRunner()
    report = runner.run_all()
    outcomes = list(runner.ledger.values())
    generation_indexes = [index for index, item in enumerate(outcomes) if item.case_id in GENERATION_CASE_IDS]
    for index in generation_indexes:
        outcomes[index] = outcomes[index].model_copy(update={
            "clarity_score": 4, "usefulness_score": 4,
            "fallback_comparison": "slightly_worse",
        })
    for index in generation_indexes[:6]:
        outcomes[index] = outcomes[index].model_copy(update={"fallback_comparison": "equivalent"})
    boundary = score_outcomes(tuple(outcomes))
    assert boundary.average_clarity == "4.00"
    assert boundary.average_usefulness == "4.00"
    assert boundary.equivalent_or_better_percentage == "75.00"
    assert boundary.final_disposition == "graduate"
    outcomes[generation_indexes[5]] = outcomes[generation_indexes[5]].model_copy(
        update={"fallback_comparison": "slightly_worse"}
    )
    below = score_outcomes(tuple(outcomes))
    assert below.equivalent_or_better_percentage == "62.50"
    assert below.final_disposition == "remain_experimental"
    assert report.final_disposition == "graduate"


def test_incorrect_empty_case_maps_to_unauthorized_hard_failure() -> None:
    runner = FormalEvaluationRunner()
    runner.run_all()
    outcomes = list(runner.ledger.values())
    index = next(i for i, item in enumerate(outcomes) if item.case_id == "eval-v4-07")
    outcomes[index] = outcomes[index].model_copy(update={
        "expected_empty_correctness": False,
        "provider_request_expected": True,
        "unauthorized_behavior": True,
    })
    report = score_outcomes(tuple(outcomes))
    assert report.expected_empty_correctness is False
    assert report.final_disposition == "fail"


@pytest.mark.parametrize(
    "mutation",
    (
        {"suggestion_count": 1},
        {"provider_request_expected": True},
        {"deterministic_request_sha256": "a" * 64},
        {"canonical_attempt_sha256": "b" * 64},
        {"provider_fingerprint": "c" * 64},
        {"token_preflight_count": 1},
        {"generation_attempt_count": 1},
        {"selected_category": "temporary_storage_need"},
        {"expected_empty_correctness": False},
    ),
)
def test_every_contradictory_empty_field_is_a_hard_failure(
    mutation: dict[str, object],
) -> None:
    runner = FormalEvaluationRunner()
    runner.run_all()
    outcomes = list(runner.ledger.values())
    index = next(i for i, item in enumerate(outcomes) if item.case_id == "eval-v4-07")
    outcomes[index] = outcomes[index].model_copy(update=mutation)
    report = score_outcomes(tuple(outcomes))
    assert report.expected_empty_correctness is False
    assert report.hard_gate_result == "fail"
    assert report.final_disposition == "fail"


def _review_arguments(case_id: str, evidence: str, **overrides: object) -> list[str]:
    values = {
        "reviewer": "Synthetic Reviewer",
        "decision": "approve",
        "grounding_accurate": "true",
        "invented_user_fact": "false",
        "irrelevant_detail": "false",
        "modality_overstatement": "false",
        "service_selection_overstatement": "false",
        "clarity_score": "5",
        "usefulness_score": "5",
        "fallback_comparison": "slightly_better",
        "bounded_notes": "Bounded synthetic review.",
    }
    values.update(overrides)
    result = ["record-review", "--case-id", case_id, "--evidence-sha256", evidence]
    for key, value in values.items():
        result.extend((f"--{key.replace('_', '-')}", str(value)))
    return result


def _cli(state_dir: Path, *arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        str(Path(__file__).parent / "v4_formal_evaluation_cli.py"),
        "--state-dir", str(state_dir), *arguments,
    ]
    return subprocess.run(
        command, check=check, capture_output=True, text=True,
        env={**os.environ, "PYTHONPATH": os.environ["PYTHONPATH"]},
    )


def test_durable_ledger_schema_identity_and_atomic_write(tmp_path: Path) -> None:
    ledger = DurableEvaluationLedger(tmp_path)
    document = ledger.initialize()
    assert document["ledger_version"] == 2
    assert (tmp_path / "transition-journal.json").is_file()
    assert document["evaluation_set_id"] == "suggest-moving-service-questions-v4-formal-evaluation-set-v1"
    assert document["evaluation_manifest_sha256"] == EXPECTED_ARTIFACTS[
        "v4-formal-evaluation/manifest.json"
    ]
    assert document["runner_id"] == RUNNER_ID
    assert document["spending_authorized"] is False
    assert len(document["cases"]) == 10
    assert not list(tmp_path.glob("*.tmp"))
    assert (tmp_path / "ledger.json").stat().st_mode & 0o077 == 0


def test_cross_process_duplicate_preflight_and_generation_are_rejected(tmp_path: Path) -> None:
    _cli(tmp_path, "package-preview")
    _cli(tmp_path, "run-preflight", "--case-id", "eval-v4-01")
    duplicate_preflight = _cli(
        tmp_path, "run-preflight", "--case-id", "eval-v4-01", check=False
    )
    assert duplicate_preflight.returncode != 0
    first = _cli(tmp_path, "run-generation", "--case-id", "eval-v4-01")
    assert json.loads(first.stdout)["generation_attempt_count"] == 1
    duplicate_generation = _cli(
        tmp_path, "run-generation", "--case-id", "eval-v4-01", check=False
    )
    assert duplicate_generation.returncode != 0


def test_atomic_concurrent_preflight_consumes_exactly_one_attempt(tmp_path: Path) -> None:
    _cli(tmp_path, "package-preview")
    command = [
        sys.executable, str(Path(__file__).parent / "v4_formal_evaluation_cli.py"),
        "--state-dir", str(tmp_path), "run-preflight", "--case-id", "eval-v4-01",
    ]
    environment = {**os.environ, "PYTHONPATH": os.environ["PYTHONPATH"]}
    first = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             text=True, env=environment)
    second = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              text=True, env=environment)
    first.communicate()
    second.communicate()
    assert sorted((first.returncode, second.returncode)) == [0, 1]
    assert DurableEvaluationLedger(tmp_path).load()["cases"]["eval-v4-01"][
        "preflight_attempts_consumed"
    ] == 1


def test_completed_empty_case_cannot_enter_provider_path_cross_process(tmp_path: Path) -> None:
    _cli(tmp_path, "package-preview")
    _cli(tmp_path, "run-empty", "--case-id", "eval-v4-07")
    rejected = _cli(
        tmp_path, "run-generation", "--case-id", "eval-v4-07", check=False
    )
    assert rejected.returncode != 0


@pytest.mark.parametrize(
    ("case_id", "scenario"),
    (("eval-v4-06", "provider_failure"), ("eval-v4-03", "structural_failure")),
)
def test_terminal_machine_failure_or_rejection_cannot_be_replaced(
    tmp_path: Path, case_id: str, scenario: str,
) -> None:
    ledger = DurableEvaluationLedger(tmp_path)
    ledger.initialize()
    ledger.run_preflight(case_id)
    outcome = ledger.run_generation(case_id, scenario=scenario)
    assert outcome.state_history[-1] is CaseState.CASE_COMPLETE
    with pytest.raises(EvaluationRunnerError, match="already consumed|not ready"):
        ledger.run_generation(case_id)


@pytest.mark.parametrize("decision", (ReviewDecision.REJECT, ReviewDecision.REQUEST_CHANGES))
def test_terminal_human_nonapproval_cannot_be_replaced(
    tmp_path: Path, decision: ReviewDecision,
) -> None:
    ledger = DurableEvaluationLedger(tmp_path)
    ledger.initialize()
    ledger.run_preflight("eval-v4-01")
    outcome = ledger.run_generation("eval-v4-01")
    review = nominal_review(0).model_copy(update={"decision": decision})
    review_result = ledger.record_review(
        "eval-v4-01", evidence_sha256=outcome.validated_response_evidence_sha256,
        reviewer="Synthetic Reviewer", review=review,
    )
    ledger.delete_evidence(
        "eval-v4-01", evidence_sha256=outcome.validated_response_evidence_sha256,
        review_sha256=review_result["human_review_sha256"],
    )
    with pytest.raises(EvaluationRunnerError, match="already consumed|not ready"):
        ledger.run_generation("eval-v4-01")


def test_explicit_evidence_review_deletion_and_idempotence(tmp_path: Path) -> None:
    ledger = DurableEvaluationLedger(tmp_path)
    ledger.initialize()
    ledger.run_preflight("eval-v4-01")
    outcome = ledger.run_generation("eval-v4-01")
    evidence = outcome.validated_response_evidence_sha256
    assert (tmp_path / "evidence/eval-v4-01.json").exists()
    with pytest.raises(EvaluationRunnerError, match="all ten ledger cases|deletion"):
        ledger.finalize_report()
    with pytest.raises(EvaluationRunnerError, match="review must complete"):
        ledger.delete_evidence("eval-v4-01", evidence_sha256=evidence, review_sha256="a" * 64)
    review_result = ledger.record_review(
        "eval-v4-01", evidence_sha256=evidence,
        reviewer="Synthetic Reviewer", review=nominal_review(0),
    )
    review_digest = review_result["human_review_sha256"]
    with pytest.raises(EvaluationRunnerError, match="all ten ledger cases|deletion"):
        ledger.finalize_report()
    with pytest.raises(EvaluationRunnerError, match="evidence binding"):
        ledger.delete_evidence(
            "eval-v4-01", evidence_sha256="b" * 64, review_sha256=review_digest
        )
    with pytest.raises(EvaluationRunnerError, match="review binding"):
        ledger.delete_evidence(
            "eval-v4-01", evidence_sha256=evidence, review_sha256="c" * 64
        )
    deleted = ledger.delete_evidence(
        "eval-v4-01", evidence_sha256=evidence, review_sha256=review_digest
    )
    assert deleted["status"] == "deleted"
    assert "response" not in deleted
    assert not (tmp_path / "evidence/eval-v4-01.json").exists()
    deletion_bytes = (tmp_path / "deletions/eval-v4-01.json").read_bytes()
    second = ledger.delete_evidence(
        "eval-v4-01", evidence_sha256=evidence, review_sha256=review_digest
    )
    assert second["status"] == "already_deleted"
    assert (tmp_path / "deletions/eval-v4-01.json").read_bytes() == deletion_bytes
    terminal = ledger.load()["cases"]["eval-v4-01"]
    assert terminal["terminal"] is True
    assert terminal["evidence_deletion_sha256"] == hashlib.sha256(deletion_bytes).hexdigest()


def test_review_rejects_wrong_evidence_wrong_state_and_duplicate(tmp_path: Path) -> None:
    ledger = DurableEvaluationLedger(tmp_path)
    ledger.initialize()
    with pytest.raises(EvaluationRunnerError, match="not awaiting"):
        ledger.record_review(
            "eval-v4-07", evidence_sha256="a" * 64,
            reviewer="Synthetic Reviewer", review=nominal_review(0),
        )
    ledger.run_preflight("eval-v4-03")
    rejected = ledger.run_generation("eval-v4-03", scenario="structural_failure")
    assert rejected.final_case_disposition is CaseDisposition.AUTOMATED_REJECTED
    with pytest.raises(EvaluationRunnerError, match="not awaiting"):
        ledger.record_review(
            "eval-v4-03", evidence_sha256="a" * 64,
            reviewer="Synthetic Reviewer", review=nominal_review(0),
        )
    ledger.run_preflight("eval-v4-01")
    outcome = ledger.run_generation("eval-v4-01")
    with pytest.raises(EvaluationRunnerError, match="evidence binding"):
        ledger.record_review(
            "eval-v4-01", evidence_sha256="b" * 64,
            reviewer="Synthetic Reviewer", review=nominal_review(0),
        )
    ledger.record_review(
        "eval-v4-01", evidence_sha256=outcome.validated_response_evidence_sha256,
        reviewer="Synthetic Reviewer", review=nominal_review(0),
    )
    with pytest.raises(EvaluationRunnerError, match="not awaiting"):
        ledger.record_review(
            "eval-v4-01", evidence_sha256=outcome.validated_response_evidence_sha256,
            reviewer="Another Reviewer", review=nominal_review(0),
        )


def test_deletion_artifact_cannot_retain_response_content(tmp_path: Path) -> None:
    ledger = DurableEvaluationLedger(tmp_path)
    ledger.initialize()
    ledger.run_preflight("eval-v4-01")
    outcome = ledger.run_generation("eval-v4-01")
    review = ledger.record_review(
        "eval-v4-01", evidence_sha256=outcome.validated_response_evidence_sha256,
        reviewer="Synthetic Reviewer", review=nominal_review(0),
    )
    ledger.delete_evidence(
        "eval-v4-01", evidence_sha256=outcome.validated_response_evidence_sha256,
        review_sha256=review["human_review_sha256"],
    )
    deletion_path = tmp_path / "deletions/eval-v4-01.json"
    deletion = json.loads(deletion_path.read_text())
    deletion["response"] = {"forbidden": True}
    deletion_bytes = json.dumps(deletion, sort_keys=True, separators=(",", ":")).encode()
    deletion_path.write_bytes(deletion_bytes)
    ledger_document = json.loads((tmp_path / "ledger.json").read_text())
    record = ledger_document["cases"]["eval-v4-01"]
    deletion_digest = hashlib.sha256(deletion_bytes).hexdigest()
    record["evidence_deletion_sha256"] = deletion_digest
    record["outcome"]["evidence_deletion_sha256"] = deletion_digest
    record["outcome_sha256"] = _digest(record["outcome"])
    (tmp_path / "ledger.json").write_text(
        json.dumps(ledger_document, sort_keys=True, separators=(",", ":"))
    )
    with pytest.raises(EvaluationRunnerError, match="authenticated history|privacy"):
        ledger.load()


def test_completed_review_outcome_without_deletion_is_invalid() -> None:
    pending = FormalEvaluationRunner().run_case("eval-v4-01", defer_human_review=True)
    with pytest.raises(ValidationError, match="before evidence deletion"):
        pending.__class__.model_validate({
            **pending.model_dump(mode="json"),
            "state_history": [*pending.state_history, "human_review_complete", "case_complete"],
            "human_review_decision": "approve",
            "human_review_sha256": "a" * 64,
        })


def test_finalize_uses_existing_ledger_and_binds_provenance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    ledger = DurableEvaluationLedger(tmp_path)
    from v4_formal_evaluation_cli import _complete_rehearsal
    first = _complete_rehearsal(ledger, "nominal")
    report_bytes = (tmp_path / "final-report.json").read_bytes()
    monkeypatch.setattr(
        FormalEvaluationRunner, "run_case",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("must not rerun cases")),
    )
    second = ledger.finalize_report()
    assert first.model_dump_json() == second.model_dump_json()
    assert (tmp_path / "final-report.json").read_bytes() == report_bytes
    assert second.ledger_version == 2
    assert second.transition_journal_terminal_sha256
    assert second.journal_transition_count
    assert len(second.case_closure_sha256) == 10
    assert second.ledger_sha256 == hashlib.sha256((tmp_path / "ledger.json").read_bytes()).hexdigest()
    assert set(second.terminal_outcome_sha256) == {f"eval-v4-{i:02d}" for i in range(1, 11)}


def test_verify_report_rejects_changed_report_bytes(tmp_path: Path) -> None:
    from v4_formal_evaluation_cli import _complete_rehearsal
    ledger = DurableEvaluationLedger(tmp_path)
    _complete_rehearsal(ledger, "nominal")
    (tmp_path / "final-report.json").write_text("{}")
    with pytest.raises(EvaluationRunnerError, match="not deterministic"):
        ledger.verify_report()


def test_ledger_rejects_outcome_digest_and_budget_corruption(tmp_path: Path) -> None:
    ledger = DurableEvaluationLedger(tmp_path)
    ledger.initialize()
    ledger.run_empty("eval-v4-07")
    document = json.loads((tmp_path / "ledger.json").read_text())
    document["cases"]["eval-v4-07"]["outcome_sha256"] = "0" * 64
    (tmp_path / "ledger.json").write_text(json.dumps(document, sort_keys=True, separators=(",", ":")))
    with pytest.raises(EvaluationRunnerError, match="authenticated history|outcome digest"):
        ledger.load()

    other = DurableEvaluationLedger(tmp_path / "budget")
    other.initialize()
    document = json.loads((tmp_path / "budget/ledger.json").read_text())
    document["cases"]["eval-v4-01"]["preflight_attempts_consumed"] = 2
    (tmp_path / "budget/ledger.json").write_text(
        json.dumps(document, sort_keys=True, separators=(",", ":"))
    )
    with pytest.raises(EvaluationRunnerError, match="authenticated history|per-case durable budget"):
        other.load()

    identity = DurableEvaluationLedger(tmp_path / "identity")
    identity.initialize()
    identity.run_preflight("eval-v4-01")
    identity.run_generation("eval-v4-01")
    document = json.loads((tmp_path / "identity/ledger.json").read_text())
    record = document["cases"]["eval-v4-01"]
    record["outcome"]["deterministic_request_sha256"] = "d" * 64
    record["outcome_sha256"] = _digest(record["outcome"])
    (tmp_path / "identity/ledger.json").write_text(
        json.dumps(document, sort_keys=True, separators=(",", ":"))
    )
    with pytest.raises(EvaluationRunnerError, match="authenticated history|request identity"):
        identity.load()


def _complete_rehearsal_through_separate_cli_processes(
    state_dir: Path, scenario: str,
) -> dict[str, object]:
    _cli(state_dir, "package-preview")
    for case_id in EMPTY_CASE_IDS:
        _cli(state_dir, "run-empty", "--case-id", case_id)
    for index, case_id in enumerate(GENERATION_CASE_IDS):
        _cli(state_dir, "run-preflight", "--case-id", case_id)
        case_scenario = scenario if (
            scenario == "provider_failure" and case_id == "eval-v4-06"
        ) else "nominal"
        generated = _cli(
            state_dir, "run-generation", "--case-id", case_id,
            "--scenario", case_scenario,
        )
        outcome = json.loads(generated.stdout)
        if outcome["human_review_applicable"]:
            overrides: dict[str, object] = {}
            if scenario == "hard_gate_failure" and case_id == "eval-v4-10":
                overrides["invented_user_fact"] = "true"
            if scenario == "quality_gate_failure":
                overrides.update({
                    "usefulness_score": "3",
                    "fallback_comparison": "slightly_worse" if index < 4 else "equivalent",
                })
            reviewed = _cli(
                state_dir,
                *_review_arguments(
                    case_id, outcome["validated_response_evidence_sha256"], **overrides
                ),
            )
            review = json.loads(reviewed.stdout)
            _cli(
                state_dir, "delete-evidence", "--case-id", case_id,
                "--evidence-sha256", outcome["validated_response_evidence_sha256"],
                "--review-sha256", review["human_review_sha256"],
            )
    return json.loads(_cli(state_dir, "finalize-report").stdout)


@pytest.mark.parametrize(
    ("scenario", "disposition"),
    (("nominal", "graduate"), ("hard_gate_failure", "fail"),
     ("quality_gate_failure", "remain_experimental"),
     ("provider_failure", "remain_experimental")),
)
def test_full_rehearsal_uses_separate_cli_processes_and_one_ledger(
    tmp_path: Path, scenario: str, disposition: str,
) -> None:
    report = _complete_rehearsal_through_separate_cli_processes(tmp_path, scenario)
    assert report["final_disposition"] == disposition
    assert report["ledger_sha256"]
    assert len(report["terminal_outcome_sha256"]) == 10


@pytest.mark.parametrize(
    ("scenario", "disposition"),
    (("nominal", "graduate"), ("hard_gate_failure", "fail"),
     ("quality_gate_failure", "remain_experimental"),
     ("provider_failure", "remain_experimental")),
)
def test_durable_rehearsal_dispositions(
    tmp_path: Path, scenario: str, disposition: str,
) -> None:
    from v4_formal_evaluation_cli import _complete_rehearsal
    report = _complete_rehearsal(DurableEvaluationLedger(tmp_path), scenario)
    assert report.final_disposition == disposition


def test_case_outcome_schema_is_bounded_and_forbids_extra_fields() -> None:
    outcome = FormalEvaluationRunner().run_case("eval-v4-01")
    with pytest.raises(ValidationError):
        outcome.__class__.model_validate({**outcome.model_dump(), "raw_response": "forbidden"})


def test_no_runtime_reachability() -> None:
    root = Path(__file__).resolve().parents[3]
    needle = "v4_formal_evaluation_runner"
    assert not any(
        needle in path.read_text(errors="ignore")
        for runtime in (root / "backend/app", root / "frontend/src")
        for path in runtime.rglob("*") if path.is_file()
    )


def _write_canonical(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")))


def _rehash_journal(root: Path) -> None:
    journal_path = root / "transition-journal.json"
    ledger_path = root / "ledger.json"
    journal = json.loads(journal_path.read_text())
    previous = journal["genesis_sha256"]
    for sequence, transition in enumerate(journal["transitions"], 1):
        transition["transition_sequence"] = sequence
        transition["previous_transition_sha256"] = previous
        transition.pop("transition_sha256", None)
        transition["transition_sha256"] = _digest(transition)
        previous = transition["transition_sha256"]
    ledger = json.loads(ledger_path.read_text())
    ledger["journal_terminal_sha256"] = previous
    ledger["journal_transition_count"] = len(journal["transitions"])
    _write_canonical(journal_path, journal)
    _write_canonical(ledger_path, ledger)


def test_preflight_artifact_is_required_and_semantically_validated(tmp_path: Path) -> None:
    ledger = DurableEvaluationLedger(tmp_path)
    ledger.initialize()
    result = ledger.run_preflight("eval-v4-01")
    assert result["preflight_artifact_sha256"]
    ledger.run_generation("eval-v4-01")

    missing = DurableEvaluationLedger(tmp_path / "missing")
    missing.initialize()
    missing.run_preflight("eval-v4-01")
    (tmp_path / "missing/preflights/eval-v4-01.json").unlink()
    with pytest.raises(EvaluationRunnerError, match="preflight artifact"):
        missing.run_generation("eval-v4-01")


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("case_id", "eval-v4-02"),
        ("deterministic_request_sha256", "a" * 64),
        ("canonical_attempt_sha256", "b" * 64),
        ("provider_fingerprint", "c" * 64),
        ("token_preflight_succeeded", False),
        ("preflight_request_count", 2),
        ("generation_request_count", 1),
        ("retries", 1),
    ),
)
def test_rehashed_semantically_wrong_preflight_artifact_rejected(
    tmp_path: Path, field: str, value: object,
) -> None:
    ledger = DurableEvaluationLedger(tmp_path)
    ledger.initialize()
    ledger.run_preflight("eval-v4-01")
    artifact_path = tmp_path / "preflights/eval-v4-01.json"
    artifact = json.loads(artifact_path.read_text())
    artifact[field] = value
    _write_canonical(artifact_path, artifact)
    digest = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
    document = json.loads((tmp_path / "ledger.json").read_text())
    journal = json.loads((tmp_path / "transition-journal.json").read_text())
    record = document["cases"]["eval-v4-01"]
    record["preflight_artifact_sha256"] = digest
    transition = journal["transitions"][0]
    transition["new_case_record"] = record
    transition["new_case_state_sha256"] = _digest(record)
    transition["artifact_digests"]["preflight_artifact_sha256"] = digest
    transition.pop("transition_sha256")
    transition["transition_sha256"] = _digest(transition)
    document["journal_terminal_sha256"] = transition["transition_sha256"]
    _write_canonical(tmp_path / "transition-journal.json", journal)
    _write_canonical(tmp_path / "ledger.json", document)
    with pytest.raises(EvaluationRunnerError, match="preflight artifact semantic"):
        DurableEvaluationLedger(tmp_path).load()


def test_preflight_fabricated_digest_and_stale_changed_bytes_rejected(tmp_path: Path) -> None:
    for name, mutate_digest in (("fabricated", True), ("stale-bytes", False)):
        root = tmp_path / name
        ledger = DurableEvaluationLedger(root)
        ledger.initialize()
        ledger.run_preflight("eval-v4-01")
        artifact_path = root / "preflights/eval-v4-01.json"
        artifact = json.loads(artifact_path.read_text())
        artifact["synthetic_input_tokens"] += 1
        _write_canonical(artifact_path, artifact)
        if mutate_digest:
            document = json.loads((root / "ledger.json").read_text())
            journal = json.loads((root / "transition-journal.json").read_text())
            digest = "f" * 64
            document["cases"]["eval-v4-01"]["preflight_artifact_sha256"] = digest
            transition = journal["transitions"][0]
            transition["new_case_record"] = document["cases"]["eval-v4-01"]
            transition["new_case_state_sha256"] = _digest(transition["new_case_record"])
            transition["artifact_digests"]["preflight_artifact_sha256"] = digest
            _write_canonical(root / "transition-journal.json", journal)
            _write_canonical(root / "ledger.json", document)
            _rehash_journal(root)
        with pytest.raises(EvaluationRunnerError, match="preflight artifact"):
            DurableEvaluationLedger(root).run_generation("eval-v4-01")


def test_cross_case_preflight_artifact_substitution_rejected(tmp_path: Path) -> None:
    ledger = DurableEvaluationLedger(tmp_path)
    ledger.initialize()
    ledger.run_preflight("eval-v4-01")
    ledger.run_preflight("eval-v4-02")
    source = tmp_path / "preflights/eval-v4-02.json"
    target = tmp_path / "preflights/eval-v4-01.json"
    target.write_bytes(source.read_bytes())
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    document = json.loads((tmp_path / "ledger.json").read_text())
    journal = json.loads((tmp_path / "transition-journal.json").read_text())
    document["cases"]["eval-v4-01"]["preflight_artifact_sha256"] = digest
    first = journal["transitions"][0]
    first["new_case_record"] = document["cases"]["eval-v4-01"]
    first["new_case_state_sha256"] = _digest(first["new_case_record"])
    first["artifact_digests"]["preflight_artifact_sha256"] = digest
    _write_canonical(tmp_path / "transition-journal.json", journal)
    _write_canonical(tmp_path / "ledger.json", document)
    _rehash_journal(tmp_path)
    with pytest.raises(EvaluationRunnerError, match="preflight artifact semantic"):
        DurableEvaluationLedger(tmp_path).load()


@pytest.mark.parametrize(
    "mutation",
    (
        "snapshot_pending", "generation_count_reset", "preflight_count_reset",
        "terminal_outcome_removed", "review_digest_removed", "deletion_digest_removed",
    ),
)
def test_snapshot_rewrite_disagrees_with_authenticated_history(
    tmp_path: Path, mutation: str,
) -> None:
    ledger = DurableEvaluationLedger(tmp_path)
    from v4_formal_evaluation_cli import _complete_rehearsal
    _complete_rehearsal(ledger, "nominal")
    document = json.loads((tmp_path / "ledger.json").read_text())
    record = document["cases"]["eval-v4-01"]
    if mutation == "snapshot_pending":
        record.update({"current_state": "pending", "terminal": False})
    elif mutation == "generation_count_reset":
        record["generation_attempts_consumed"] = 0
    elif mutation == "preflight_count_reset":
        record["preflight_attempts_consumed"] = 0
    elif mutation == "terminal_outcome_removed":
        record.update({"outcome": None, "outcome_sha256": None})
    elif mutation == "review_digest_removed":
        record["human_review_sha256"] = None
    else:
        record["evidence_deletion_sha256"] = None
    _write_canonical(tmp_path / "ledger.json", document)
    with pytest.raises(EvaluationRunnerError, match="authenticated history"):
        DurableEvaluationLedger(tmp_path).load()


def test_fresh_cli_rejects_canonically_rewritten_terminal_snapshot(tmp_path: Path) -> None:
    ledger = _complete_one_reviewed_case(tmp_path)
    document = json.loads((tmp_path / "ledger.json").read_text())
    original = document["cases"]["eval-v4-01"]
    initial = ledger._initial_document()["cases"]["eval-v4-01"]
    document["cases"]["eval-v4-01"] = initial
    assert original["terminal"] is True and initial["current_state"] == "pending"
    _write_canonical(tmp_path / "ledger.json", document)
    rejected = _cli(
        tmp_path, "run-generation", "--case-id", "eval-v4-01",
        "--scenario", "nominal", check=False,
    )
    assert rejected.returncode != 0
    assert "authenticated history" in rejected.stderr


@pytest.mark.parametrize(
    "mutation",
    ("removed", "reordered", "previous_hash", "state_digest", "duplicate_sequence",
     "skipped_sequence", "wrong_case", "genesis"),
)
def test_transition_journal_tamper_is_rejected(tmp_path: Path, mutation: str) -> None:
    ledger = DurableEvaluationLedger(tmp_path)
    ledger.initialize()
    ledger.run_preflight("eval-v4-01")
    ledger.run_generation("eval-v4-01")
    path = tmp_path / "transition-journal.json"
    journal = json.loads(path.read_text())
    transitions = journal["transitions"]
    if mutation == "removed":
        transitions.pop(0)
    elif mutation == "reordered":
        transitions.reverse()
    elif mutation == "previous_hash":
        transitions[-1]["previous_transition_sha256"] = "0" * 64
    elif mutation == "state_digest":
        transitions[-1]["new_case_state_sha256"] = "1" * 64
    elif mutation == "duplicate_sequence":
        transitions[-1]["transition_sequence"] = 1
    elif mutation == "skipped_sequence":
        transitions[-1]["transition_sequence"] = 3
    elif mutation == "wrong_case":
        transitions[-1]["case_id"] = "eval-v4-02"
    else:
        journal["genesis_sha256"] = "2" * 64
    _write_canonical(path, journal)
    with pytest.raises(EvaluationRunnerError, match="journal|transition"):
        DurableEvaluationLedger(tmp_path).load()


@pytest.mark.parametrize(
    "step",
    (
        "transaction_prepared", "deletion_artifact_written", "evidence_unlinked",
        "evidence_removed_persisted", "deletion_transition_appended",
        "ledger_projection_updated", "before_transaction_committed",
    ),
)
def test_interrupted_deletion_recovers_idempotently(tmp_path: Path, step: str) -> None:
    class CrashingLedger(DurableEvaluationLedger):
        def _deletion_crash_point(self, current: str) -> None:
            if current == step:
                raise RuntimeError("synthetic crash")

    ledger = CrashingLedger(tmp_path)
    ledger.initialize()
    ledger.run_preflight("eval-v4-01")
    outcome = ledger.run_generation("eval-v4-01")
    review = ledger.record_review(
        "eval-v4-01", evidence_sha256=outcome.validated_response_evidence_sha256,
        reviewer="Synthetic Reviewer", review=nominal_review(0),
    )
    with pytest.raises(RuntimeError, match="synthetic crash"):
        ledger.delete_evidence(
            "eval-v4-01", evidence_sha256=outcome.validated_response_evidence_sha256,
            review_sha256=review["human_review_sha256"],
        )
    recovered = DurableEvaluationLedger(tmp_path)
    document = recovered.recover()
    record = document["cases"]["eval-v4-01"]
    assert record["terminal"] is True
    assert not (tmp_path / "evidence/eval-v4-01.json").exists()
    deletion = (tmp_path / "deletions/eval-v4-01.json").read_bytes()
    journal_after_recovery = (tmp_path / "transition-journal.json").read_bytes()
    recovery_journal = json.loads(journal_after_recovery)
    assert recovery_journal["transitions"][-1]["operation_type"] == "recovery_completed"
    recovered.recover()
    assert (tmp_path / "deletions/eval-v4-01.json").read_bytes() == deletion
    assert (tmp_path / "transition-journal.json").read_bytes() == journal_after_recovery
    journal_before = journal_after_recovery
    transaction_before = (tmp_path / "transactions/eval-v4-01-deletion.json").read_bytes()
    idempotent = recovered.delete_evidence(
        "eval-v4-01", evidence_sha256=outcome.validated_response_evidence_sha256,
        review_sha256=review["human_review_sha256"],
    )
    assert idempotent["status"] == "already_deleted"
    assert (tmp_path / "transition-journal.json").read_bytes() == journal_before
    assert (tmp_path / "transactions/eval-v4-01-deletion.json").read_bytes() == transaction_before
    assert idempotent["human_review_sha256"] == review["human_review_sha256"]
    with pytest.raises(EvaluationRunnerError, match="already consumed|not ready"):
        recovered.run_generation("eval-v4-01")


@pytest.mark.parametrize(
    "step", ("basis_persisted", "recovery_prepared_appended", "before_first_repair"),
)
def test_prepared_recovery_resumes_after_each_pre_mutation_boundary(
    tmp_path: Path, step: str,
) -> None:
    class DeletionCrash(DurableEvaluationLedger):
        def _deletion_crash_point(self, current: str) -> None:
            if current == "transaction_prepared":
                raise RuntimeError("deletion crash")

    ledger = DeletionCrash(tmp_path)
    ledger.initialize()
    ledger.run_preflight("eval-v4-01")
    outcome = ledger.run_generation("eval-v4-01")
    review = ledger.record_review(
        "eval-v4-01", evidence_sha256=outcome.validated_response_evidence_sha256,
        reviewer="Synthetic Reviewer", review=nominal_review(0),
    )
    with pytest.raises(RuntimeError, match="deletion crash"):
        ledger.delete_evidence(
            "eval-v4-01", evidence_sha256=outcome.validated_response_evidence_sha256,
            review_sha256=review["human_review_sha256"],
        )

    class RecoveryCrash(DurableEvaluationLedger):
        def _recovery_crash_point(self, current: str) -> None:
            if current == step:
                raise RuntimeError("recovery crash")

    with pytest.raises(RuntimeError, match="recovery crash"):
        RecoveryCrash(tmp_path).recover()
    recovered = DurableEvaluationLedger(tmp_path)
    document = recovered.recover()
    assert document["cases"]["eval-v4-01"]["terminal"] is True
    journal = json.loads((tmp_path / "transition-journal.json").read_text())
    operations = [item["operation_type"] for item in journal["transitions"]]
    assert operations.count("recovery_prepared") == 1
    assert operations.count("recovery_completed") == 1
    for operation in ("recovery_prepared", "recovery_completed"):
        transition = next(item for item in journal["transitions"]
                          if item["operation_type"] == operation)
        assert transition["attempt_counters_before"] == transition["attempt_counters_after"]
    assert recovered.delete_evidence(
        "eval-v4-01", evidence_sha256=outcome.validated_response_evidence_sha256,
        review_sha256=review["human_review_sha256"],
    )["status"] == "already_deleted"


def _prepared_deletion_transaction(root: Path, case_id: str = "eval-v4-01") -> None:
    class DeletionCrash(DurableEvaluationLedger):
        def _deletion_crash_point(self, current: str) -> None:
            if current == "transaction_prepared":
                raise RuntimeError("prepared transaction retained")

    ledger = DeletionCrash(root)
    ledger.initialize()
    ledger.run_preflight(case_id)
    outcome = ledger.run_generation(case_id)
    review = ledger.record_review(
        case_id, evidence_sha256=outcome.validated_response_evidence_sha256,
        reviewer="Synthetic Reviewer", review=nominal_review(0),
    )
    with pytest.raises(RuntimeError, match="prepared transaction retained"):
        ledger.delete_evidence(
            case_id, evidence_sha256=outcome.validated_response_evidence_sha256,
            review_sha256=review["human_review_sha256"],
        )


def test_deletion_transaction_accepts_equivalent_noncanonical_json_formatting(
    tmp_path: Path,
) -> None:
    _prepared_deletion_transaction(tmp_path)
    path = tmp_path / "transactions/eval-v4-01-deletion.json"
    transaction = json.loads(path.read_text())
    path.write_text(json.dumps(transaction, indent=3, sort_keys=False) + "\n")
    assert path.read_bytes() != json.dumps(
        transaction, sort_keys=True, separators=(",", ":")
    ).encode()
    document = DurableEvaluationLedger(tmp_path).recover()
    assert document["cases"]["eval-v4-01"]["terminal"] is True


@pytest.mark.parametrize(
    "mutation",
    (
        "wrong_evaluation", "wrong_runner", "wrong_case", "wrong_transaction_id",
        "wrong_evidence", "wrong_review", "wrong_intended_deletion",
        "wrong_previous_state", "unsupported_state", "prepared_evidence_missing",
        "prepared_committed_binding", "evidence_removed_evidence_present",
        "evidence_removed_deletion_missing", "committed_missing_transition",
        "committed_inconsistent_terminal", "cross_case_valid_transaction",
    ),
)
def test_malformed_persisted_transaction_rejected_before_recovery_preparation(
    tmp_path: Path, mutation: str,
) -> None:
    root = tmp_path / "target"
    _prepared_deletion_transaction(root)
    transaction_path = root / "transactions/eval-v4-01-deletion.json"
    transaction = json.loads(transaction_path.read_text())
    evidence_path = root / "evidence/eval-v4-01.json"
    deletion_path = root / "deletions/eval-v4-01.json"
    deletion_path.parent.mkdir(parents=True, exist_ok=True)
    if mutation == "wrong_evaluation":
        transaction["evaluation_set_id"] = "wrong-set"
    elif mutation == "wrong_runner":
        transaction["runner_id"] = "wrong-runner"
    elif mutation == "wrong_case":
        transaction["case_id"] = "eval-v4-02"
    elif mutation == "wrong_transaction_id":
        transaction["transaction_id"] = "f" * 64
    elif mutation == "wrong_evidence":
        transaction["validated_response_evidence_sha256"] = "a" * 64
    elif mutation == "wrong_review":
        transaction["human_review_sha256"] = "b" * 64
    elif mutation == "wrong_intended_deletion":
        transaction["intended_deletion_sha256"] = "c" * 64
    elif mutation == "wrong_previous_state":
        transaction["previous_case_state_sha256"] = "d" * 64
    elif mutation == "unsupported_state":
        transaction["state"] = "unsupported"
    elif mutation == "prepared_evidence_missing":
        evidence_path.unlink()
    elif mutation == "prepared_committed_binding":
        transaction["committed_event_id"] = "impossible"
    elif mutation == "evidence_removed_evidence_present":
        deletion = {
            "evaluation_set_id": SET_ID, "runner_id": RUNNER_ID,
            "case_id": "eval-v4-01", "synthetic": True,
            "validated_response_evidence_sha256":
                transaction["validated_response_evidence_sha256"],
            "human_review_sha256": transaction["human_review_sha256"],
            "deleted": True, "response_content_retained": False,
        }
        _write_canonical(deletion_path, deletion)
        transaction.update({
            "state": "evidence_removed",
            "removal_prepared_event_id": "eval-v4-01:delete:removal_prepared",
            "evidence_removed_event_id": "eval-v4-01:delete:evidence_removed",
        })
    elif mutation == "evidence_removed_deletion_missing":
        evidence_path.unlink()
        transaction.update({
            "state": "evidence_removed",
            "removal_prepared_event_id": "eval-v4-01:delete:removal_prepared",
            "evidence_removed_event_id": "eval-v4-01:delete:evidence_removed",
        })
    elif mutation in {"committed_missing_transition", "committed_inconsistent_terminal"}:
        evidence_path.unlink()
        deletion = {
            "evaluation_set_id": SET_ID, "runner_id": RUNNER_ID,
            "case_id": "eval-v4-01", "synthetic": True,
            "validated_response_evidence_sha256":
                transaction["validated_response_evidence_sha256"],
            "human_review_sha256": transaction["human_review_sha256"],
            "deleted": True, "response_content_retained": False,
        }
        _write_canonical(deletion_path, deletion)
        transaction.update({
            "state": "committed",
            "removal_prepared_event_id": "eval-v4-01:delete:removal_prepared",
            "evidence_removed_event_id": "eval-v4-01:delete:evidence_removed",
            "deletion_sha256": _digest(deletion), "closure_sha256": "e" * 64,
            "deletion_transition_sha256": "f" * 64,
            "committed_event_id": "eval-v4-01:delete:committed",
        })
    else:
        other = tmp_path / "other"
        _prepared_deletion_transaction(other, "eval-v4-02")
        transaction = json.loads(
            (other / "transactions/eval-v4-02-deletion.json").read_text()
        )
    if mutation not in {"wrong_transaction_id", "prepared_evidence_missing",
                        "cross_case_valid_transaction"}:
        transaction["transaction_id"] = DurableEvaluationLedger(
            root
        )._deletion_transaction_id(transaction)
    _write_canonical(transaction_path, transaction)
    journal_path = root / "transition-journal.json"
    journal_before = journal_path.read_bytes()
    state_before = {
        path: path.read_bytes() for path in (transaction_path, evidence_path, deletion_path)
        if path.exists()
    }
    with pytest.raises(EvaluationRunnerError):
        DurableEvaluationLedger(root).recover()
    assert journal_path.read_bytes() == journal_before
    journal = json.loads(journal_path.read_text())
    assert not any(item["operation_type"] == "recovery_prepared"
                   for item in journal["transitions"])
    assert not list((root / "recoveries").glob("*-basis.json"))
    assert all(path.read_bytes() == value for path, value in state_before.items())


def _complete_one_reviewed_case(root: Path) -> DurableEvaluationLedger:
    ledger = DurableEvaluationLedger(root)
    ledger.initialize()
    ledger.run_preflight("eval-v4-01")
    outcome = ledger.run_generation("eval-v4-01")
    review = ledger.record_review(
        "eval-v4-01", evidence_sha256=outcome.validated_response_evidence_sha256,
        reviewer="Synthetic Reviewer", review=nominal_review(0),
    )
    ledger.delete_evidence(
        "eval-v4-01", evidence_sha256=outcome.validated_response_evidence_sha256,
        review_sha256=review["human_review_sha256"],
    )
    return ledger


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("human_review_reviewer", "Different Reviewer"),
        ("human_review_decision", "reject"),
        ("grounding_accurate", False),
        ("invented_user_fact", True),
        ("modality_overstatement", True),
        ("service_selection_overstatement", True),
        ("clarity_score", 1),
        ("usefulness_score", 1),
        ("fallback_comparison", "materially_worse"),
    ),
)
def test_rehashed_outcome_cannot_disagree_with_review_artifact(
    tmp_path: Path, field: str, value: object,
) -> None:
    _complete_one_reviewed_case(tmp_path)
    ledger_path = tmp_path / "ledger.json"
    journal_path = tmp_path / "transition-journal.json"
    closure_path = tmp_path / "closures/eval-v4-01.json"
    transaction_path = tmp_path / "transactions/eval-v4-01-deletion.json"
    ledger = json.loads(ledger_path.read_text())
    journal = json.loads(journal_path.read_text())
    record = ledger["cases"]["eval-v4-01"]
    record["outcome"][field] = value
    record["outcome_sha256"] = _digest(record["outcome"])
    closure = json.loads(closure_path.read_text())
    closure["terminal_outcome_sha256"] = record["outcome_sha256"]
    _write_canonical(closure_path, closure)
    record["closure_sha256"] = hashlib.sha256(closure_path.read_bytes()).hexdigest()
    final = journal["transitions"][-1]
    final["new_case_record"] = record
    final["new_case_state_sha256"] = _digest(record)
    final["artifact_digests"]["outcome_sha256"] = record["outcome_sha256"]
    final["artifact_digests"]["closure_sha256"] = record["closure_sha256"]
    final.pop("transition_sha256")
    final["transition_sha256"] = _digest(final)
    ledger["journal_terminal_sha256"] = final["transition_sha256"]
    transaction = json.loads(transaction_path.read_text())
    transaction["closure_sha256"] = record["closure_sha256"]
    _write_canonical(transaction_path, transaction)
    _write_canonical(journal_path, journal)
    _write_canonical(ledger_path, ledger)
    with pytest.raises(EvaluationRunnerError, match="review artifact disagrees"):
        DurableEvaluationLedger(tmp_path).load()


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("case_id", "eval-v4-02"),
        ("terminal_outcome_sha256", "a" * 64),
        ("generation_attempts_consumed", 0),
        ("retries", 1),
        ("terminal", False),
        ("reusable", True),
        ("evidence_deletion_sha256", None),
    ),
)
def test_closure_semantics_reject_wrong_rehashed_content(
    tmp_path: Path, field: str, value: object,
) -> None:
    _complete_one_reviewed_case(tmp_path)
    closure_path = tmp_path / "closures/eval-v4-01.json"
    closure = json.loads(closure_path.read_text())
    closure[field] = value
    _write_canonical(closure_path, closure)
    with pytest.raises(EvaluationRunnerError, match="closure"):
        DurableEvaluationLedger(tmp_path).load()


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("preflight_artifact_sha256", None),
        ("preflight_artifact_sha256", "a" * 64),
        ("generation_audit_sha256", None),
        ("generation_audit_sha256", "b" * 64),
        ("validated_response_evidence_sha256", None),
        ("human_review_sha256", "c" * 64),
        ("evidence_deletion_sha256", None),
        ("deletion_transaction_id", "d" * 64),
        ("preflight_attempts_consumed", 0),
        ("terminal_reason", "transport_failure"),
    ),
)
def test_fully_rehashed_closure_lifecycle_mutations_rejected(
    tmp_path: Path, field: str, value: object,
) -> None:
    _complete_one_reviewed_case(tmp_path)
    closure_path = tmp_path / "closures/eval-v4-01.json"
    transaction_path = tmp_path / "transactions/eval-v4-01-deletion.json"
    journal_path = tmp_path / "transition-journal.json"
    ledger_path = tmp_path / "ledger.json"
    closure = json.loads(closure_path.read_text())
    closure[field] = value
    _write_canonical(closure_path, closure)
    closure_digest = hashlib.sha256(closure_path.read_bytes()).hexdigest()
    ledger = json.loads(ledger_path.read_text())
    record = ledger["cases"]["eval-v4-01"]
    record["closure_sha256"] = closure_digest
    journal = json.loads(journal_path.read_text())
    deletion = next(
        item for item in journal["transitions"]
        if item["operation_type"] == "response_evidence_deleted"
    )
    deletion["new_case_record"] = record
    deletion["new_case_state_sha256"] = _digest(record)
    deletion["artifact_digests"]["closure_sha256"] = closure_digest
    transaction = json.loads(transaction_path.read_text())
    transaction["closure_sha256"] = closure_digest
    _write_canonical(transaction_path, transaction)
    _write_canonical(journal_path, journal)
    _write_canonical(ledger_path, ledger)
    _rehash_journal(tmp_path)
    with pytest.raises(EvaluationRunnerError, match="closure"):
        DurableEvaluationLedger(tmp_path).load()


@pytest.mark.parametrize(
    ("scenario", "case_id", "field", "value"),
    (
        ("provider_failure", "eval-v4-06", "generation_audit_sha256", None),
        ("structural_failure", "eval-v4-03", "human_review_sha256", "e" * 64),
        ("provider_failure", "eval-v4-06", "generation_attempts_consumed", 0),
    ),
)
def test_machine_terminal_closure_semantic_mutations_rejected(
    tmp_path: Path, scenario: str, case_id: str, field: str, value: object,
) -> None:
    ledger = DurableEvaluationLedger(tmp_path)
    ledger.initialize()
    ledger.run_preflight(case_id)
    ledger.run_generation(case_id, scenario=scenario)
    closure_path = tmp_path / "closures" / f"{case_id}.json"
    closure = json.loads(closure_path.read_text())
    closure[field] = value
    _write_canonical(closure_path, closure)
    with pytest.raises(EvaluationRunnerError, match="closure"):
        DurableEvaluationLedger(tmp_path).load()


def _fully_rehash_machine_terminal_closure(
    root: Path, *, scenario: str, case_id: str, mutation: str,
) -> None:
    ledger = DurableEvaluationLedger(root)
    ledger.initialize()
    ledger.run_preflight(case_id)
    ledger.run_generation(case_id, scenario=scenario)
    closure_path = root / "closures" / f"{case_id}.json"
    ledger_path = root / "ledger.json"
    journal_path = root / "transition-journal.json"
    closure = json.loads(closure_path.read_text())
    document = json.loads(ledger_path.read_text())
    record = document["cases"][case_id]
    if mutation == "missing_audit":
        closure["generation_audit_sha256"] = None
    elif mutation == "wrong_audit":
        closure["generation_audit_sha256"] = "a" * 64
    elif mutation == "generation_count":
        closure["generation_attempts_consumed"] = 0
    elif mutation == "terminal_reason":
        closure["terminal_reason"] = "passed"
    elif mutation == "evidence_added":
        closure["validated_response_evidence_sha256"] = "b" * 64
    elif mutation == "review_added":
        closure["human_review_sha256"] = "c" * 64
    elif mutation == "deletion_added":
        closure["evidence_deletion_sha256"] = "d" * 64
    elif mutation == "missing_preflight":
        closure["preflight_artifact_sha256"] = None
    elif mutation == "fallback_missing":
        record["outcome"]["fallback_selected"] = False
        record["outcome"]["fallback_version"] = None
        record["outcome"]["fallback_question_id"] = None
        record["outcome_sha256"] = _digest(record["outcome"])
        closure["terminal_outcome_sha256"] = record["outcome_sha256"]
    else:
        raise AssertionError(mutation)
    _write_canonical(closure_path, closure)
    record["closure_sha256"] = hashlib.sha256(closure_path.read_bytes()).hexdigest()
    transition = json.loads(journal_path.read_text())
    target = transition["transitions"][-1]
    target["new_case_record"] = record
    target["new_case_state_sha256"] = _digest(record)
    target["artifact_digests"]["closure_sha256"] = record["closure_sha256"]
    target["artifact_digests"]["outcome_sha256"] = record["outcome_sha256"]
    _write_canonical(journal_path, transition)
    _write_canonical(ledger_path, document)
    _rehash_journal(root)


@pytest.mark.parametrize(
    "mutation",
    (
        "missing_audit", "wrong_audit", "generation_count", "terminal_reason",
        "evidence_added", "review_added", "deletion_added", "missing_preflight",
    ),
)
def test_fully_rehashed_provider_failure_closure_matrix_rejected(
    tmp_path: Path, mutation: str,
) -> None:
    _fully_rehash_machine_terminal_closure(
        tmp_path, scenario="provider_failure", case_id="eval-v4-06",
        mutation=mutation,
    )
    with pytest.raises(EvaluationRunnerError, match="closure|audit"):
        DurableEvaluationLedger(tmp_path).load()


@pytest.mark.parametrize(
    "mutation",
    (
        "missing_audit", "wrong_audit", "fallback_missing", "evidence_added",
        "review_added", "deletion_added", "terminal_reason", "generation_count",
    ),
)
def test_fully_rehashed_automated_rejection_closure_matrix_rejected(
    tmp_path: Path, mutation: str,
) -> None:
    _fully_rehash_machine_terminal_closure(
        tmp_path, scenario="structural_failure", case_id="eval-v4-03",
        mutation=mutation,
    )
    with pytest.raises(EvaluationRunnerError, match="closure|audit"):
        DurableEvaluationLedger(tmp_path).load()


@pytest.mark.parametrize(
    "mutation",
    (
        "false_before", "false_after", "terminal_false", "terminal_true",
        "missing_preflight", "missing_generation_audit", "missing_evidence",
        "missing_review", "missing_deletion", "missing_closure",
        "generation_on_review", "preflight_on_deletion", "wrong_operation",
    ),
)
def test_fully_rehashed_transition_metadata_and_artifact_lies_fail(
    tmp_path: Path, mutation: str,
) -> None:
    _complete_one_reviewed_case(tmp_path)
    path = tmp_path / "transition-journal.json"
    journal = json.loads(path.read_text())
    preflight, generation, review, deletion = journal["transitions"][:4]
    if mutation == "false_before":
        generation["attempt_counters_before"]["preflights"] = 9
    elif mutation == "false_after":
        generation["attempt_counters_after"]["generations"] = 9
    elif mutation == "terminal_false":
        deletion["terminal_state"] = False
    elif mutation == "terminal_true":
        preflight["terminal_state"] = True
    elif mutation == "missing_preflight":
        preflight["artifact_digests"].pop("preflight_artifact_sha256")
    elif mutation == "missing_generation_audit":
        generation["artifact_digests"].pop("generation_audit_sha256")
    elif mutation == "missing_evidence":
        generation["artifact_digests"].pop("validated_response_evidence_sha256")
    elif mutation == "missing_review":
        review["artifact_digests"].pop("human_review_sha256")
    elif mutation == "missing_deletion":
        deletion["artifact_digests"].pop("evidence_deletion_sha256")
    elif mutation == "missing_closure":
        deletion["artifact_digests"].pop("closure_sha256")
    elif mutation == "generation_on_review":
        review["attempt_counters_after"]["generations"] = 2
    elif mutation == "preflight_on_deletion":
        deletion["attempt_counters_after"]["preflights"] = 2
    else:
        preflight["operation_type"] = "human_review_recorded"
    _write_canonical(path, journal)
    _rehash_journal(tmp_path)
    with pytest.raises(EvaluationRunnerError, match="transition"):
        DurableEvaluationLedger(tmp_path).load()


@pytest.mark.parametrize(
    ("scenario", "case_id", "expected_operation", "extra_key"),
    (("structural_failure", "eval-v4-03", "generation_automated_rejected",
      "human_review_sha256"),
     ("provider_failure", "eval-v4-06", "provider_failure_recorded",
      "evidence_deletion_sha256")),
)
def test_rehashed_terminal_machine_transition_rejects_impossible_artifact(
    tmp_path: Path, scenario: str, case_id: str, expected_operation: str,
    extra_key: str,
) -> None:
    ledger = DurableEvaluationLedger(tmp_path)
    ledger.initialize()
    ledger.run_preflight(case_id)
    ledger.run_generation(case_id, scenario=scenario)
    path = tmp_path / "transition-journal.json"
    journal = json.loads(path.read_text())
    target = journal["transitions"][-1]
    assert target["operation_type"] == expected_operation
    target["artifact_digests"][extra_key] = "a" * 64
    _write_canonical(path, journal)
    _rehash_journal(tmp_path)
    with pytest.raises(EvaluationRunnerError, match="artifact"):
        DurableEvaluationLedger(tmp_path).load()


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("evaluation_set_id", "wrong-set"),
        ("runner_id", "wrong-runner"),
        ("case_id", "eval-v4-02"),
        ("transaction_id", "a" * 64),
        ("validated_response_evidence_sha256", "b" * 64),
        ("human_review_sha256", "c" * 64),
        ("intended_deletion_sha256", "d" * 64),
        ("previous_case_state_sha256", "e" * 64),
        ("deletion_sha256", "f" * 64),
        ("deletion_transition_sha256", "1" * 64),
    ),
)
def test_committed_deletion_transaction_semantic_mutations_rejected(
    tmp_path: Path, field: str, value: object,
) -> None:
    _complete_one_reviewed_case(tmp_path)
    path = tmp_path / "transactions/eval-v4-01-deletion.json"
    transaction = json.loads(path.read_text())
    transaction[field] = value
    _write_canonical(path, transaction)
    with pytest.raises(EvaluationRunnerError, match="deletion transaction|committed"):
        DurableEvaluationLedger(tmp_path).load()


def test_projection_only_recovery_is_authenticated_and_noop_is_stable(tmp_path: Path) -> None:
    ledger = _complete_one_reviewed_case(tmp_path)
    document = json.loads((tmp_path / "ledger.json").read_text())
    document["cases"]["eval-v4-01"] = ledger._initial_document()["cases"]["eval-v4-01"]
    _write_canonical(tmp_path / "ledger.json", document)
    recovered = DurableEvaluationLedger(tmp_path)
    result = recovered.recover()
    assert result["cases"]["eval-v4-01"]["terminal"] is True
    journal_path = tmp_path / "transition-journal.json"
    journal = json.loads(journal_path.read_text())
    transition = journal["transitions"][-1]
    assert transition["operation_type"] == "recovery_completed"
    assert transition["bounded_metadata"]["repair_classification"] == "projection_reconciled"
    assert transition["attempt_counters_before"] == transition["attempt_counters_after"]
    stable = journal_path.read_bytes()
    recovered.recover()
    assert journal_path.read_bytes() == stable


def test_transaction_only_commit_recovery_is_authenticated(tmp_path: Path) -> None:
    _complete_one_reviewed_case(tmp_path)
    path = tmp_path / "transactions/eval-v4-01-deletion.json"
    transaction = json.loads(path.read_text())
    for key in ("deletion_sha256", "closure_sha256", "deletion_transition_sha256",
                "committed_event_id"):
        transaction.pop(key)
    transaction["state"] = "evidence_removed"
    _write_canonical(path, transaction)
    ledger = DurableEvaluationLedger(tmp_path)
    ledger.recover()
    journal = json.loads((tmp_path / "transition-journal.json").read_text())
    recovery = journal["transitions"][-1]
    assert recovery["operation_type"] == "recovery_completed"
    assert recovery["bounded_metadata"]["repair_classification"] == (
        "deletion_transaction_committed"
    )
    assert json.loads(path.read_text())["state"] == "committed"


def _recovered_history(root: Path, basis: str) -> None:
    if basis == "projection":
        ledger = _complete_one_reviewed_case(root)
        document = json.loads((root / "ledger.json").read_text())
        document["cases"]["eval-v4-01"] = ledger._initial_document()["cases"][
            "eval-v4-01"
        ]
        _write_canonical(root / "ledger.json", document)
        DurableEvaluationLedger(root).recover()
        return
    if basis == "transaction":
        _complete_one_reviewed_case(root)
        path = root / "transactions/eval-v4-01-deletion.json"
        transaction = json.loads(path.read_text())
        for key in ("deletion_sha256", "closure_sha256", "deletion_transition_sha256",
                    "committed_event_id"):
            transaction.pop(key)
        transaction["state"] = "evidence_removed"
        _write_canonical(path, transaction)
        DurableEvaluationLedger(root).recover()
        return

    class CrashingLedger(DurableEvaluationLedger):
        def _deletion_crash_point(self, step: str) -> None:
            if step == "transaction_prepared":
                raise RuntimeError("synthetic crash")

    ledger = CrashingLedger(root)
    ledger.initialize()
    ledger.run_preflight("eval-v4-01")
    outcome = ledger.run_generation("eval-v4-01")
    review = ledger.record_review(
        "eval-v4-01", evidence_sha256=outcome.validated_response_evidence_sha256,
        reviewer="Synthetic Reviewer", review=nominal_review(0),
    )
    with pytest.raises(RuntimeError, match="synthetic crash"):
        ledger.delete_evidence(
            "eval-v4-01", evidence_sha256=outcome.validated_response_evidence_sha256,
            review_sha256=review["human_review_sha256"],
        )
    DurableEvaluationLedger(root).recover()


def _rewrite_recovery_artifact(root: Path, mutate) -> None:
    journal_path = root / "transition-journal.json"
    journal = json.loads(journal_path.read_text())
    prepared = next(item for item in journal["transitions"]
                    if item["operation_type"] == "recovery_prepared")
    completed = next(item for item in journal["transitions"]
                     if item["operation_type"] == "recovery_completed")
    old_event_id = prepared["bounded_metadata"]["recovery_event_id"]
    basis = json.loads(
        (root / "recoveries" / f"{old_event_id}-basis.json").read_text()
    )
    completion = json.loads(
        (root / "recoveries" / f"{old_event_id}-completed.json").read_text()
    )
    mutate(basis, completed)
    basis.pop("recovery_event_id", None)
    event_id = _digest(basis)
    basis["recovery_event_id"] = event_id
    basis_path = root / "recoveries" / f"{event_id}-basis.json"
    _write_canonical(basis_path, basis)
    prepared["bounded_metadata"]["recovery_event_id"] = event_id
    prepared["artifact_digests"]["recovery_basis_sha256"] = hashlib.sha256(
        basis_path.read_bytes()
    ).hexdigest()
    _write_canonical(journal_path, journal)
    _rehash_journal(root)
    journal = json.loads(journal_path.read_text())
    prepared = next(item for item in journal["transitions"]
                    if item["operation_type"] == "recovery_prepared")
    completed = next(item for item in journal["transitions"]
                     if item["operation_type"] == "recovery_completed")
    completion["recovery_event_id"] = event_id
    completion["recovery_basis_sha256"] = prepared["artifact_digests"][
        "recovery_basis_sha256"
    ]
    completion["recovery_prepared_transition_sha256"] = prepared["transition_sha256"]
    completion_path = root / "recoveries" / f"{event_id}-completed.json"
    _write_canonical(completion_path, completion)
    completed["bounded_metadata"]["recovery_event_id"] = event_id
    completed["artifact_digests"] = {
        "recovery_basis_sha256": completion["recovery_basis_sha256"],
        "recovery_prepared_transition_sha256": prepared["transition_sha256"],
        "recovery_completion_sha256": hashlib.sha256(
            completion_path.read_bytes()
        ).hexdigest(),
    }
    _write_canonical(journal_path, journal)
    _rehash_journal(root)


@pytest.mark.parametrize(
    ("basis", "mutation"),
    (
        ("projection", "as_transaction"),
        ("transaction", "as_projection"),
        ("combined", "as_projection"),
        ("projection", "as_combined"),
        ("projection", "artifact_omitted"),
        ("projection", "wrong_artifact_digest"),
        ("projection", "another_case"),
        ("projection", "wrong_repaired_state"),
        ("projection", "counter_change"),
        ("transaction", "wrong_transaction_state_change"),
    ),
)
def test_fully_rehashed_recovery_classification_basis_mutations_rejected(
    tmp_path: Path, basis: str, mutation: str,
) -> None:
    _recovered_history(tmp_path, basis)
    journal_path = tmp_path / "transition-journal.json"
    if mutation in {"artifact_omitted", "wrong_artifact_digest"}:
        journal = json.loads(journal_path.read_text())
        transition = journal["transitions"][-1]
        if mutation == "artifact_omitted":
            transition["artifact_digests"].pop("recovery_completion_sha256")
        else:
            transition["artifact_digests"]["recovery_completion_sha256"] = "f" * 64
        _write_canonical(journal_path, journal)
        _rehash_journal(tmp_path)
    else:
        def mutate(artifact: dict[str, object], transition: dict[str, object]) -> None:
            if mutation == "as_transaction":
                transition["bounded_metadata"]["repair_classification"] = (
                    "deletion_transaction_committed"
                )
            elif mutation == "as_projection":
                transition["bounded_metadata"]["repair_classification"] = (
                    "projection_reconciled"
                )
            elif mutation == "as_combined":
                transition["bounded_metadata"]["repair_classification"] = (
                    "combined_reconciliation"
                )
            elif mutation == "another_case":
                artifact["case_id"] = "eval-v4-02"
            elif mutation == "wrong_repaired_state":
                artifact["prior_case_state_sha256"] = "a" * 64
            elif mutation == "counter_change":
                artifact["attempt_counters"]["generations"] += 1
            else:
                artifact["deletion_transaction_state_before"] = "committed"
        _rewrite_recovery_artifact(tmp_path, mutate)
    with pytest.raises(EvaluationRunnerError, match="recovery"):
        DurableEvaluationLedger(tmp_path).load()


@pytest.mark.parametrize(
    "mutation",
    (
        "false_preflight_before", "false_preflight_after",
        "false_generation_before", "false_generation_after",
        "false_retry_before", "false_retry_after", "retry_increment",
        "decreased_preflight", "decreased_generation", "decreased_retry",
        "generation_on_review", "generation_on_deletion", "generation_on_recovery",
        "preflight_on_review", "preflight_on_deletion", "preflight_on_recovery",
        "retry_on_review", "retry_on_deletion", "retry_on_recovery",
    ),
)
def test_complete_fully_rehashed_transition_counter_matrix_rejected(
    tmp_path: Path, mutation: str,
) -> None:
    _recovered_history(tmp_path, "projection")
    path = tmp_path / "transition-journal.json"
    journal = json.loads(path.read_text())
    preflight, generation, review, deletion, recovery = journal["transitions"][:5]
    target, side, counter, value = {
        "false_preflight_before": (generation, "before", "preflights", 9),
        "false_preflight_after": (preflight, "after", "preflights", 9),
        "false_generation_before": (generation, "before", "generations", 9),
        "false_generation_after": (generation, "after", "generations", 9),
        "false_retry_before": (generation, "before", "retries", 9),
        "false_retry_after": (generation, "after", "retries", 9),
        "retry_increment": (generation, "after", "retries", 1),
        "decreased_preflight": (generation, "after", "preflights", 0),
        "decreased_generation": (review, "after", "generations", 0),
        "decreased_retry": (review, "after", "retries", -1),
        "generation_on_review": (review, "after", "generations", 2),
        "generation_on_deletion": (deletion, "after", "generations", 2),
        "generation_on_recovery": (recovery, "after", "generations", 2),
        "preflight_on_review": (review, "after", "preflights", 2),
        "preflight_on_deletion": (deletion, "after", "preflights", 2),
        "preflight_on_recovery": (recovery, "after", "preflights", 2),
        "retry_on_review": (review, "after", "retries", 1),
        "retry_on_deletion": (deletion, "after", "retries", 1),
        "retry_on_recovery": (recovery, "after", "retries", 1),
    }[mutation]
    target[f"attempt_counters_{side}"][counter] = value
    _write_canonical(path, journal)
    _rehash_journal(tmp_path)
    with pytest.raises(EvaluationRunnerError, match="transition|recovery"):
        DurableEvaluationLedger(tmp_path).load()
