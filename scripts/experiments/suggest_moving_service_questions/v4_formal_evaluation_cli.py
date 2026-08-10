#!/usr/bin/env python3
"""Durable offline command surface for the frozen-v4 formal evaluation runner."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from freeze_v4_formal_evaluation_set import EMPTY_CASE_IDS, GENERATION_CASE_IDS, verify_package
from v4_formal_evaluation_runner import (
    DurableEvaluationLedger,
    HumanReview,
    RUNNER_ID,
    nominal_review,
)


def emit(value: object) -> None:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    print(json.dumps(value, sort_keys=True, separators=(",", ":")))


def _boolean(value: str) -> bool:
    if value == "true":
        return True
    if value == "false":
        return False
    raise argparse.ArgumentTypeError("expected true or false")


def _add_review_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--case-id", choices=GENERATION_CASE_IDS, required=True)
    parser.add_argument("--evidence-sha256", required=True)
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--decision", choices=("approve", "reject", "request_changes"), required=True)
    parser.add_argument("--grounding-accurate", type=_boolean, required=True)
    parser.add_argument("--invented-user-fact", type=_boolean, required=True)
    parser.add_argument("--irrelevant-detail", type=_boolean, required=True)
    parser.add_argument("--modality-overstatement", type=_boolean, required=True)
    parser.add_argument("--service-selection-overstatement", type=_boolean, required=True)
    parser.add_argument("--clarity-score", type=int, required=True)
    parser.add_argument("--usefulness-score", type=int, required=True)
    parser.add_argument(
        "--fallback-comparison",
        choices=("materially_better", "slightly_better", "equivalent",
                 "slightly_worse", "materially_worse"),
        required=True,
    )
    parser.add_argument("--bounded-notes", required=True)


def _review_from_args(args: argparse.Namespace) -> HumanReview:
    return HumanReview(
        decision=args.decision,
        grounding_accurate=args.grounding_accurate,
        invented_user_fact=args.invented_user_fact,
        irrelevant_detail=args.irrelevant_detail,
        modality_overstatement=args.modality_overstatement,
        service_selection_overstatement=args.service_selection_overstatement,
        clarity_score=args.clarity_score,
        usefulness_score=args.usefulness_score,
        fallback_comparison=args.fallback_comparison,
        bounded_notes=args.bounded_notes,
    )


def _complete_rehearsal(ledger: DurableEvaluationLedger, scenario: str) -> object:
    ledger.initialize()
    for case_id in EMPTY_CASE_IDS:
        ledger.run_empty(case_id)
    for index, case_id in enumerate(GENERATION_CASE_IDS):
        ledger.run_preflight(case_id)
        case_scenario = scenario if (
            scenario in {"structural_failure", "semantic_failure", "prose_failure"}
            and case_id == "eval-v4-03"
        ) or (scenario == "provider_failure" and case_id == "eval-v4-06") else "nominal"
        outcome = ledger.run_generation(case_id, scenario=case_scenario)
        if outcome.human_review_applicable:
            review = nominal_review(index)
            if scenario == "hard_gate_failure" and case_id == "eval-v4-10":
                review = review.model_copy(update={"invented_user_fact": True})
            if scenario == "quality_gate_failure":
                review = review.model_copy(update={
                    "usefulness_score": 3,
                    "fallback_comparison": "slightly_worse" if index < 4 else "equivalent",
                })
            review_result = ledger.record_review(
                case_id, evidence_sha256=outcome.validated_response_evidence_sha256,
                reviewer="Synthetic Rehearsal Reviewer", review=review,
            )
            ledger.delete_evidence(
                case_id,
                evidence_sha256=outcome.validated_response_evidence_sha256,
                review_sha256=review_result["human_review_sha256"],
            )
    return ledger.finalize_report()


def _rehearse_through_separate_processes(state_dir: Path, scenario: str) -> object:
    script = Path(__file__).resolve()

    def invoke(*arguments: str) -> object:
        completed = subprocess.run(
            [sys.executable, str(script), "--state-dir", str(state_dir), *arguments],
            check=True, capture_output=True, text=True,
        )
        return json.loads(completed.stdout)

    def rejected(*arguments: str) -> bool:
        completed = subprocess.run(
            [sys.executable, str(script), "--state-dir", str(state_dir), *arguments],
            check=False, capture_output=True, text=True,
        )
        return completed.returncode != 0

    invoke("package-preview")
    duplicate_preflight_rejected = False
    duplicate_generation_rejected = False
    for case_id in EMPTY_CASE_IDS:
        invoke("run-empty", "--case-id", case_id)
    for index, case_id in enumerate(GENERATION_CASE_IDS):
        invoke("run-preflight", "--case-id", case_id)
        if case_id == "eval-v4-01":
            duplicate_preflight_rejected = rejected(
                "run-preflight", "--case-id", case_id
            )
        case_scenario = scenario if (
            scenario in {"structural_failure", "semantic_failure", "prose_failure"}
            and case_id == "eval-v4-03"
        ) or (scenario == "provider_failure" and case_id == "eval-v4-06") else "nominal"
        outcome = invoke(
            "run-generation", "--case-id", case_id, "--scenario", case_scenario
        )
        if case_id == "eval-v4-01":
            duplicate_generation_rejected = rejected(
                "run-generation", "--case-id", case_id, "--scenario", "nominal"
            )
        if outcome["human_review_applicable"]:
            review = nominal_review(index)
            if scenario == "hard_gate_failure" and case_id == "eval-v4-10":
                review = review.model_copy(update={"invented_user_fact": True})
            if scenario == "quality_gate_failure":
                review = review.model_copy(update={
                    "usefulness_score": 3,
                    "fallback_comparison": "slightly_worse" if index < 4 else "equivalent",
                })
            review_arguments = [
                "record-review", "--case-id", case_id,
                "--evidence-sha256", outcome["validated_response_evidence_sha256"],
                "--reviewer", "Synthetic Rehearsal Reviewer",
                "--decision", review.decision,
                "--grounding-accurate", str(review.grounding_accurate).lower(),
                "--invented-user-fact", str(review.invented_user_fact).lower(),
                "--irrelevant-detail", str(review.irrelevant_detail).lower(),
                "--modality-overstatement", str(review.modality_overstatement).lower(),
                "--service-selection-overstatement",
                str(review.service_selection_overstatement).lower(),
                "--clarity-score", str(review.clarity_score),
                "--usefulness-score", str(review.usefulness_score),
                "--fallback-comparison", review.fallback_comparison,
                "--bounded-notes", review.bounded_notes,
            ]
            review_result = invoke(*review_arguments)
            invoke(
                "delete-evidence", "--case-id", case_id,
                "--evidence-sha256", outcome["validated_response_evidence_sha256"],
                "--review-sha256", review_result["human_review_sha256"],
            )
    report = invoke("finalize-report")
    report["cross_process_second_preflight_rejected"] = duplicate_preflight_rejected
    report["cross_process_second_generation_rejected"] = duplicate_generation_rejected
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--state-dir", type=Path,
        default=Path(os.environ.get(
            "V4_FORMAL_EVALUATION_STATE_DIR",
            ".local/evaluations/suggest-moving-service-questions/v4-formal-evaluation-runner-v1",
        )),
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("verify-set")
    commands.add_parser("package-preview")
    rehearse = commands.add_parser("rehearse")
    rehearse.add_argument(
        "--scenario",
        choices=("nominal", "hard_gate_failure", "quality_gate_failure", "provider_failure",
                 "structural_failure", "semantic_failure", "prose_failure"),
        default="nominal",
    )
    empty = commands.add_parser("run-empty")
    empty.add_argument("--case-id", choices=EMPTY_CASE_IDS, required=True)
    preflight = commands.add_parser("run-preflight")
    preflight.add_argument("--case-id", choices=GENERATION_CASE_IDS, required=True)
    generation = commands.add_parser("run-generation")
    generation.add_argument("--case-id", choices=GENERATION_CASE_IDS, required=True)
    generation.add_argument(
        "--scenario",
        choices=("nominal", "provider_failure", "structural_failure", "semantic_failure", "prose_failure"),
        default="nominal",
    )
    review = commands.add_parser("record-review")
    _add_review_arguments(review)
    deletion = commands.add_parser("delete-evidence")
    deletion.add_argument("--case-id", choices=GENERATION_CASE_IDS, required=True)
    deletion.add_argument("--evidence-sha256", required=True)
    deletion.add_argument("--review-sha256", required=True)
    commands.add_parser("finalize-report")
    commands.add_parser("verify-report")
    commands.add_parser("close-recover")
    args = parser.parse_args()
    ledger = DurableEvaluationLedger(args.state_dir)

    if args.command == "verify-set":
        verify_package()
        emit({"evaluation_set_verified": True, "runner_id": RUNNER_ID, "offline": True})
    elif args.command == "package-preview":
        document = ledger.initialize()
        emit({
            "ledger_initialized": True, "ledger_version": document["ledger_version"],
            "runner_id": RUNNER_ID, "evaluation_set_id": document["evaluation_set_id"],
            "state_dir": str(args.state_dir), "spending_authorized": False,
            "authoritative": False,
        })
    elif args.command == "rehearse":
        emit(_rehearse_through_separate_processes(args.state_dir, args.scenario))
    elif args.command == "run-empty":
        emit(ledger.run_empty(args.case_id))
    elif args.command == "run-preflight":
        emit(ledger.run_preflight(args.case_id))
    elif args.command == "run-generation":
        emit(ledger.run_generation(args.case_id, scenario=args.scenario))
    elif args.command == "record-review":
        emit(ledger.record_review(
            args.case_id, evidence_sha256=args.evidence_sha256,
            reviewer=args.reviewer, review=_review_from_args(args),
        ))
    elif args.command == "delete-evidence":
        emit(ledger.delete_evidence(
            args.case_id, evidence_sha256=args.evidence_sha256,
            review_sha256=args.review_sha256,
        ))
    elif args.command == "finalize-report":
        emit(ledger.finalize_report())
    elif args.command == "verify-report":
        emit(ledger.verify_report())
    elif args.command == "close-recover":
        document = ledger.recover()
        evidence_present = any((args.state_dir / "evidence").glob("*.json"))
        emit({
            "ledger_verified": True,
            "terminal_cases": sum(item["terminal"] for item in document["cases"].values()),
            "validated_evidence_present": evidence_present,
            "authorization_active": False,
            "permanent_closed_manifest_sha256":
                "18a22d62a3e368f5a021649be56a211af959fed7b0305eab61d063022b1387fa",
        })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
