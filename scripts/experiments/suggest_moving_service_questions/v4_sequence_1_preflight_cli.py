"""Fixed public-command backend for frozen-v4 sequence-1 preflight."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from v4_sequence_1_preflight import (
    DEFAULT_OUTPUT_ROOT, OPERATOR_INTENT, RENDERED_TMP, V4PreflightError,
    activate, activation_review, cleanup_review_package, close,
    generation_binding_dry_run, install, paths, plan, render, review_evidence,
    verify_active, verify_static,
)


def emit(values) -> None:
    for key, value in values.items():
        if isinstance(value, bool): value = str(value).lower()
        elif isinstance(value, (list, dict)): value = json.dumps(value, separators=(",", ":"), sort_keys=True)
        print(f"{key}={value}")


def current() -> datetime:
    if os.environ.get("GOTIME_V4_SEQUENCE_1_PREFLIGHT_OFFLINE_TEST") == "1":
        synthetic = os.environ.get("GOTIME_V4_SEQUENCE_1_PREFLIGHT_SYNTHETIC_NOW")
        if synthetic:
            return datetime.fromisoformat(synthetic.replace("Z", "+00:00"))
    return datetime.now(timezone.utc)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(); commands = result.add_subparsers(dest="operation", required=True)
    render_parser = commands.add_parser("render")
    for name in ("approver", "approved-at", "activated-at", "expires-at", "reason"): render_parser.add_argument(f"--{name}", required=True)
    install_parser = commands.add_parser("install"); install_parser.add_argument("--expected-sha256", required=True)
    review = commands.add_parser("activation-review"); review.add_argument("--artifact-sha256", required=True); review.add_argument("--reviewer", required=True); review.add_argument("--decision", required=True, choices=("approve", "reject", "request_changes")); review.add_argument("--reviewed-at", required=True); review.add_argument("--notes", required=True)
    for operation in ("plan", "activate"):
        command = commands.add_parser(operation)
        for name in ("artifact-sha256", "installation-record-sha256", "activation-review-sha256"): command.add_argument(f"--{name}", required=True)
        if operation == "activate": command.add_argument("--operator", required=True); command.add_argument("--operator-intent", required=True)
    commands.add_parser("verify-active")
    close_parser = commands.add_parser("close"); close_parser.add_argument("--reason", required=True, choices=("success", "bounded_failure", "expiration", "operator_cancellation", "activation_recovery"))
    evidence = commands.add_parser("evidence-review")
    evidence.add_argument("--evidence-sha256", required=True); evidence.add_argument("--input-tokens", required=True, type=int); evidence.add_argument("--conservative-cost", required=True); evidence.add_argument("--reviewer", required=True); evidence.add_argument("--decision", required=True, choices=("approve", "reject", "request_changes")); evidence.add_argument("--reviewed-at", required=True)
    for name in ("token-count-plausible", "cost-within-limit", "frozen-bindings-confirmed", "evidence-history-confirmed"): evidence.add_argument(f"--{name}", required=True, choices=("true", "false"))
    evidence.add_argument("--notes", required=True)
    commands.add_parser("generation-binding-dry-run")
    cleanup = commands.add_parser("cleanup"); cleanup.add_argument("--confirm-delete", action="store_true"); cleanup.add_argument("--operator")
    commands.add_parser("readiness")
    return result


def main(argv=None) -> int:
    args = parser().parse_args(argv); now = current()
    try:
        if args.operation == "render": emit(render(approver=args.approver, approved_at=args.approved_at, activated_at=args.activated_at, expires_at=args.expires_at, reason=args.reason, now=now))
        elif args.operation == "install": emit(install(source=RENDERED_TMP, expected_sha256=args.expected_sha256, now=now))
        elif args.operation == "activation-review": emit(activation_review(artifact_sha256=args.artifact_sha256, reviewer=args.reviewer, decision=args.decision, reviewed_at=args.reviewed_at, notes=args.notes, now=now))
        elif args.operation == "plan": emit(plan(artifact_sha256=args.artifact_sha256, installation_sha256=args.installation_record_sha256, review_sha256=args.activation_review_sha256, now=now))
        elif args.operation == "activate": emit(activate(artifact_sha256=args.artifact_sha256, installation_sha256=args.installation_record_sha256, review_sha256=args.activation_review_sha256, operator=args.operator, operator_intent=args.operator_intent, now=now))
        elif args.operation == "verify-active": emit(verify_active(now=now, minimum_seconds=180))
        elif args.operation == "close": emit(close(reason=args.reason, now=now))
        elif args.operation == "evidence-review": emit(review_evidence(evidence_sha256=args.evidence_sha256, input_tokens=args.input_tokens, conservative_cost=args.conservative_cost, reviewer=args.reviewer, decision=args.decision, reviewed_at=args.reviewed_at, token_count_plausible=args.token_count_plausible == "true", cost_within_limit=args.cost_within_limit == "true", frozen_bindings_confirmed=args.frozen_bindings_confirmed == "true", evidence_history_confirmed=args.evidence_history_confirmed == "true", notes=args.notes, now=now))
        elif args.operation == "generation-binding-dry-run": emit(generation_binding_dry_run())
        elif args.operation == "cleanup": emit(cleanup_review_package(confirm=args.confirm_delete, operator=args.operator, now=now))
        else:
            status = verify_static(); target = paths()
            if any(path.exists() for path in vars(target).values() if path not in (target.execution, target.closed)) or RENDERED_TMP.exists(): raise V4PreflightError("real v4 preflight state exists")
            emit({**status, "run_series_id": "moving-service-stage-b-v4-pilot-20260808", "sequence": 1, "generation_authorized": False, "readiness_valid": True})
    except (OSError, ValueError, AssertionError):
        print(f"v4_sequence_1_{args.operation.replace('-', '_')}_error=rejected", file=sys.stderr); return 4
    return 0


if __name__ == "__main__": raise SystemExit(main())
