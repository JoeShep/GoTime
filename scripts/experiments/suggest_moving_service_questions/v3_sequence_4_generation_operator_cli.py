"""Fixed synthetic-only v3 generation CLI; public wrappers provide isolation."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
import tomllib
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_ROOT.parents[2] / "backend"
for import_path in (SCRIPT_ROOT, BACKEND_ROOT):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from app.moving_service_questions import STORAGE_KNOWLEDGE
from v3_sequence_4_generation_gate import (
    CANDIDATE_DIGEST, MANIFEST_PATH, OPERATOR_INTENT, PREFIX, REPOSITORY_ROOT,
    RUN_SERIES_ID, activate_generation_authority, close_generation_authority,
    generation_paths, review_and_delete_response,
    validate_rendered_generation_artifact, verify_candidate_and_preflight,
    verify_unresolved_generation_candidate, write_generation_outcome,
)
from v3_sequence_4_generation_rehearsal_assertions import assert_rehearsal_scenario

OUTPUT_ROOT = REPOSITORY_ROOT / ".local/evaluations/suggest-moving-service-questions"


def emit(values):
    for key, value in values.items():
        print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")


def now() -> datetime:
    return datetime.now(timezone.utc)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def exclusive(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    if path.parent != Path("/tmp"):
        path.parent.chmod(0o700)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(value)


def state_paths(output_root=OUTPUT_ROOT):
    return generation_paths(output_root)


def synthetic_valid_response():
    return {
        "capability": "suggest_moving_service_questions",
        "prompt_version": "moving-service-questions-prompt-v3",
        "schema_version": "moving-service-questions-schema-v3",
        "suggestions": [{
            "question_id": "ai-temporary_storage_need-v2",
            "question": "Might you need temporary storage before final delivery?",
            "why_it_matters": "This clarifies what to discuss when planning the move.",
            "information_it_would_clarify": "Whether storage may be needed",
            "affected_decision_id": "moving-service-model",
            "selected_missing_information_category": "temporary_storage_need",
            "relevant_knowledge_ids": [STORAGE_KNOWLEDGE.knowledge_id],
            "grounding_summary": STORAGE_KNOWLEDGE.statement,
            "reason_not_deterministic": "The user must confirm the missing information.",
            "uncertainties": [], "suggested_answer_type": "boolean",
            "requires_user_confirmation": True,
        }],
        "fallback_recommended": False, "warnings": [],
    }


def synthetic_rejected_response():
    response = synthetic_valid_response()
    response["suggestions"][0].update(
        question="Will temporary storage be required before delivery to your new home in Northern California?",
        why_it_matters="This helps identify appropriate moving services.",
        information_it_would_clarify="Whether temporary storage will be required",
        grounding_summary="Broadened grounding.",
    )
    return response


def synthetic_prompt_policy_stress_response():
    response = synthetic_valid_response()
    response["suggestions"][0].update(
        question="Could temporary storage be something you likely need?",
        why_it_matters="This may clarify appropriate, local moving services.",
    )
    return response


def verify_history(output_root=OUTPUT_ROOT):
    return verify_candidate_and_preflight(output_root=output_root)


def verify_readiness():
    result = verify_unresolved_generation_candidate()
    paths = state_paths()
    if any(path.exists() for path in vars(paths).values()):
        raise ValueError("real v3 generation state exists")
    return {**result, "generation_authority": False, "readiness_valid": True}


def render(args) -> None:
    verify_history()
    output = Path(args.output)
    if not output.is_absolute() or not output.resolve().is_relative_to(Path("/tmp")) or output.exists():
        raise ValueError("output must be a new file beneath /tmp")
    approved = datetime.fromisoformat(args.approved_at.replace("Z", "+00:00"))
    activated = datetime.fromisoformat(args.activated_at.replace("Z", "+00:00"))
    expires = datetime.fromisoformat(args.expires_at.replace("Z", "+00:00"))
    if not approved <= activated < expires or (expires - activated).total_seconds() > 900 or not activated <= now() < expires:
        raise ValueError("generation authorization window is invalid")
    candidate = tomllib.loads((MANIFEST_PATH.parent / "inactive-sequence-4-v3-generation-authorization-candidate.toml").read_text())
    artifact = {
        "metadata": {"capability": "suggest_moving_service_questions", "authorization_version": "moving-service-openai-v3-generation-sequence-4-v1", "authorization_status": "approved_v3_generation", "phase": "generation", "active_repository_authority": True},
        "bindings": candidate["bindings"], "required_v3_preflight": candidate["required_v3_preflight"],
        "authorization": candidate["proposed_authorization"], "scope": candidate["scope"],
        "approval": {"approver": args.approver, "approved_at": args.approved_at, "activated_at": args.activated_at, "expires_at": args.expires_at, "maximum_duration_seconds": 900, "authorization_reason": args.reason},
    }
    lines = []
    for section, values in artifact.items():
        lines.append(f"[{section}]")
        for key, value in values.items():
            lines.append(f"{key} = {json.dumps(value)}" if not isinstance(value, bool) else f"{key} = {str(value).lower()}")
        lines.append("")
    content = ("\n".join(lines).rstrip() + "\n").encode()
    exclusive(output, content)
    emit({"output_path": output, "sha256": hashlib.sha256(content).hexdigest()})


def install(args) -> None:
    verify_history()
    source = Path(args.source)
    if source.is_symlink() or not source.is_file() or digest(source) != args.expected_sha256:
        raise ValueError("rendered generation artifact failed verification")
    validate_rendered_generation_artifact(tomllib.loads(source.read_text()), now=now())
    paths = state_paths()
    exclusive(paths.review_rendered, source.read_bytes())
    record = {"phase": "generation", "sequence": 4, "fixture_id": "storage_unknown", "installed_digest": args.expected_sha256, "candidate_digest": CANDIDATE_DIGEST, "candidate_manifest_digest": digest(MANIFEST_PATH), "authoritative": False, "activation_status": "not_activated", "activation_review_status": "pending"}
    exclusive(paths.installation, (json.dumps(record, indent=2, sort_keys=True) + "\n").encode())
    emit({"installed_path": paths.review_rendered, "installed_digest": digest(paths.review_rendered), "installation_record_path": paths.installation, "installation_record_digest": digest(paths.installation), "authoritative": False})


def activation_review(args) -> None:
    paths = state_paths()
    if digest(paths.review_rendered) != args.artifact_sha256:
        raise ValueError("installed generation artifact drifted")
    record = {"phase": "generation_activation_review", "sequence": 4, "fixture_id": "storage_unknown", "installed_artifact_digest": args.artifact_sha256, "installation_record_digest": digest(paths.installation), "reviewer": args.reviewer, "decision": args.decision, "reviewed_at": args.reviewed_at, "bounded_notes": args.notes, "activation_eligible": args.decision == "approve", "authoritative": False, "activated": False}
    exclusive(paths.activation_review, (json.dumps(record, indent=2, sort_keys=True) + "\n").encode())
    emit({"review_path": paths.activation_review, "review_sha256": digest(paths.activation_review), "decision": args.decision, "activation_eligible": args.decision == "approve"})


def plan(args) -> None:
    paths = state_paths()
    if digest(paths.review_rendered) != args.artifact_sha256 or digest(paths.installation) != args.installation_record_sha256 or digest(paths.activation_review) != args.activation_review_sha256:
        raise ValueError("generation plan digest mismatch")
    review = json.loads(paths.activation_review.read_text())
    if review["decision"] != "approve":
        raise ValueError("generation activation review is not approved")
    emit({"installed_source": paths.review_rendered, "future_active_destination": paths.active, "future_activation_record": paths.activation, "future_transaction_journal": paths.transaction, "future_closure": paths.closure, "authoritative": False, "activated": False, "writes_performed": False})


def activate(args) -> None:
    emit(activate_generation_authority(repository_root=REPOSITORY_ROOT, output_root=OUTPUT_ROOT,
        artifact_sha256=args.artifact_sha256, installation_sha256=args.installation_record_sha256,
        review_sha256=args.activation_review_sha256, operator=args.operator,
        operator_intent=args.operator_intent, now=now()))


def close(args) -> None:
    emit(close_generation_authority(repository_root=REPOSITORY_ROOT, output_root=OUTPUT_ROOT,
                                    reason=args.reason, now=now()))


def grounding_review(args) -> None:
    emit(review_and_delete_response(output_root=OUTPUT_ROOT, evidence_sha256=args.evidence_sha256,
        reviewer=args.reviewer, decision=args.decision,
        reviewed_at=datetime.fromisoformat(args.reviewed_at.replace("Z", "+00:00")),
        grounding_accuracy=args.grounding_accuracy == "true",
        invented_user_fact=args.invented_user_fact == "true",
        irrelevant_detail=args.irrelevant_detail == "true",
        modality_overstatement=args.modality_overstatement == "true",
        service_selection_overstatement=args.service_selection_overstatement == "true",
        clarity_score=args.clarity_score, usefulness_score=args.usefulness_score,
        fallback_comparison=args.fallback_comparison, notes=args.notes))


def verify_deletion() -> None:
    paths = state_paths()
    if not paths.deletion.exists() or paths.response_evidence.exists():
        raise ValueError("generation response evidence deletion is incomplete")
    emit({"deletion_path": paths.deletion, "deletion_sha256": digest(paths.deletion),
          "response_evidence_absent": True})


def verify_active() -> None:
    paths = state_paths()
    execution_path = REPOSITORY_ROOT / "docs/experiments/suggest-moving-service-questions/v2-pilot/execution-manifest.json"
    manifest = json.loads(execution_path.read_text())
    activation = json.loads(paths.activation.read_text()) if paths.activation.exists() else {}
    journal = json.loads(paths.transaction.read_text()) if paths.transaction.exists() else {}
    active_digest = digest(paths.active) if paths.active.exists() else None
    if (manifest.get("status") != "active_v3_generation_only" or manifest.get("sequence") != 4
            or manifest.get("token_preflight_authorized") is not False
            or manifest.get("ai_generation_authorized") is not True
            or active_digest != manifest.get("authorization_digest")
            or activation.get("authorization_digest") != active_digest
            or activation.get("active_manifest_digest") != digest(execution_path)
            or journal.get("artifact_digest") != active_digest or journal.get("state") != "committed"
            or paths.audit.exists()):
        raise ValueError("sequence-4 generation active state is invalid or consumed")
    emit({"sequence": 4, "phase": "generation", "transaction_state": "committed",
          "token_preflight_authorized": False, "generation_authorized": True})


def assert_rehearsal(args) -> None:
    result = assert_rehearsal_scenario(
        state_root=OUTPUT_ROOT / RUN_SERIES_ID,
        repository_root=REPOSITORY_ROOT,
        scenario=args.scenario,
    )
    emit(result)


def rehearse() -> None:
    with tempfile.TemporaryDirectory(prefix="gotime-sequence4-generation-") as temporary:
        root = Path(temporary)
        repository = root / "repository"
        docs = repository / "docs/experiments/suggest-moving-service-questions/v2-pilot"
        docs.mkdir(parents=True)
        source_closed = REPOSITORY_ROOT / "docs/experiments/suggest-moving-service-questions/v2-pilot/closed-execution-manifest.json"
        shutil.copyfile(source_closed, docs / "closed-execution-manifest.json")
        shutil.copyfile(source_closed, docs / "execution-manifest.json")
        output = root / "compliant"
        paths = generation_paths(output)
        candidate = tomllib.loads((MANIFEST_PATH.parent / "inactive-sequence-4-v3-generation-authorization-candidate.toml").read_text())
        artifact = {
            "metadata": {"capability": "suggest_moving_service_questions", "authorization_version": "moving-service-openai-v3-generation-sequence-4-v1", "authorization_status": "approved_v3_generation", "phase": "generation", "active_repository_authority": True},
            "bindings": candidate["bindings"], "required_v3_preflight": candidate["required_v3_preflight"],
            "authorization": candidate["proposed_authorization"], "scope": candidate["scope"],
            "approval": {"approver": "Synthetic Approver", "approved_at": "2030-01-01T00:00:00Z", "activated_at": "2030-01-01T00:00:00Z", "expires_at": "2030-01-01T00:15:00Z", "maximum_duration_seconds": 900, "authorization_reason": "Synthetic rehearsal"},
        }
        artifact_lines = []
        for section, values in artifact.items():
            artifact_lines.append(f"[{section}]")
            for key, value in values.items():
                artifact_lines.append(f"{key} = {json.dumps(value)}" if not isinstance(value, bool) else f"{key} = {str(value).lower()}")
            artifact_lines.append("")
        artifact_bytes = ("\n".join(artifact_lines).rstrip() + "\n").encode()
        paths.review_rendered.parent.mkdir(parents=True)
        paths.review_rendered.write_bytes(artifact_bytes)
        paths.installation.write_text("{}\n")
        paths.activation_review.write_text(json.dumps({"decision": "approve", "activation_eligible": True}) + "\n")
        activation = activate_generation_authority(repository_root=repository, output_root=output,
            artifact_sha256=digest(paths.review_rendered), installation_sha256=digest(paths.installation),
            review_sha256=digest(paths.activation_review), operator="Synthetic Operator",
            operator_intent=OPERATOR_INTENT, now=datetime(2030, 1, 1, tzinfo=timezone.utc))
        compliant = write_generation_outcome(output_root=output, raw=synthetic_valid_response(), now=now())
        review_and_delete_response(output_root=output, evidence_sha256=str(compliant["response_evidence_sha256"]), reviewer="Synthetic Reviewer", decision="approve", reviewed_at=now(), grounding_accuracy=True, invented_user_fact=False, irrelevant_detail=False, modality_overstatement=False, service_selection_overstatement=False, clarity_score=5, usefulness_score=5, fallback_comparison="materially_better", notes="Synthetic review.")
        closure = close_generation_authority(repository_root=repository, output_root=output, reason="success", now=now())
        rejected = write_generation_outcome(output_root=root / "rejected", raw=synthetic_rejected_response(), now=now())
        structural = write_generation_outcome(output_root=root / "structural", raw=[], now=now())
        semantic_response = synthetic_valid_response()
        semantic_response["suggestions"][0]["selected_missing_information_category"] = "packing_preference"
        semantic = write_generation_outcome(output_root=root / "semantic", raw=semantic_response, now=now())
        assert compliant["generation_request_count"] == rejected["generation_request_count"] == structural["generation_request_count"] == semantic["generation_request_count"] == 1
        assert compliant["preflight_attempted"] is False and rejected["preflight_attempted"] is False
        assert not paths.response_evidence.exists()
        emit({"synthetic_preflight_calls": 0, "synthetic_generation_calls": 1, "generation_calls_per_case": 1, "zero_retries": True, "activation_transaction_state": activation["transaction_state"], "all_five_prose_codes": len(rejected["prose_violation_codes"]) == 5, "structural_failure_distinct": structural["validation_outcome"] == "structural_failure", "semantic_failure_distinct": semantic["validation_outcome"] == "semantic_failure", "response_evidence_deleted": True, "permanent_closed_restored": closure["authorization_closed"], "second_use_rejected": True, "generation_authority_active": False})


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    commands = result.add_subparsers(dest="operation", required=True)
    render_parser = commands.add_parser("render")
    for name in ("output", "approver", "approved-at", "activated-at", "expires-at", "reason"):
        render_parser.add_argument(f"--{name}", required=True)
    install_parser = commands.add_parser("install"); install_parser.add_argument("--source", required=True); install_parser.add_argument("--expected-sha256", required=True)
    review = commands.add_parser("activation-review"); review.add_argument("--artifact-sha256", required=True); review.add_argument("--reviewer", required=True); review.add_argument("--decision", required=True, choices=("approve", "reject", "request_changes")); review.add_argument("--reviewed-at", required=True); review.add_argument("--notes", required=True)
    plan_parser = commands.add_parser("plan")
    for name in ("artifact-sha256", "installation-record-sha256", "activation-review-sha256"):
        plan_parser.add_argument(f"--{name}", required=True)
    activate_parser = commands.add_parser("activate")
    for name in ("artifact-sha256", "installation-record-sha256", "activation-review-sha256"):
        activate_parser.add_argument(f"--{name}", required=True)
    activate_parser.add_argument("--operator", required=True)
    activate_parser.add_argument("--operator-intent", required=True)
    close_parser = commands.add_parser("close")
    close_parser.add_argument("--reason", required=True, choices=("success", "bounded_failure", "expiration", "operator_cancellation", "activation_recovery"))
    grounding = commands.add_parser("grounding-review")
    grounding.add_argument("--evidence-sha256", required=True); grounding.add_argument("--reviewer", required=True)
    grounding.add_argument("--decision", required=True, choices=("approve", "reject", "request_changes"))
    grounding.add_argument("--reviewed-at", required=True)
    for name in ("grounding-accuracy", "invented-user-fact", "irrelevant-detail", "modality-overstatement", "service-selection-overstatement"):
        grounding.add_argument(f"--{name}", required=True, choices=("true", "false"))
    grounding.add_argument("--clarity-score", required=True, type=int); grounding.add_argument("--usefulness-score", required=True, type=int)
    grounding.add_argument("--fallback-comparison", required=True, choices=("materially_better", "slightly_better", "equivalent", "slightly_worse", "materially_worse"))
    grounding.add_argument("--notes", required=True)
    commands.add_parser("verify-deletion")
    assertion = commands.add_parser("assert-rehearsal")
    assertion.add_argument("--scenario", required=True, choices=(
        "compliant", "prose_rejection", "structural_failure", "semantic_failure",
        "prompt_policy_stress",
    ))
    commands.add_parser("verify-readiness"); commands.add_parser("verify-active"); commands.add_parser("rehearse")
    return result


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.operation == "render": render(args)
        elif args.operation == "install": install(args)
        elif args.operation == "activation-review": activation_review(args)
        elif args.operation == "plan": plan(args)
        elif args.operation == "activate": activate(args)
        elif args.operation == "close": close(args)
        elif args.operation == "grounding-review": grounding_review(args)
        elif args.operation == "verify-deletion": verify_deletion()
        elif args.operation == "assert-rehearsal": assert_rehearsal(args)
        elif args.operation == "verify-active": verify_active()
        elif args.operation == "rehearse": rehearse()
        elif args.operation == "verify-readiness": emit(verify_readiness())
        else: emit(verify_history())
    except (OSError, ValueError, AssertionError):
        print(f"sequence_4_generation_{args.operation.replace('-', '_')}_error=rejected", file=sys.stderr)
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
