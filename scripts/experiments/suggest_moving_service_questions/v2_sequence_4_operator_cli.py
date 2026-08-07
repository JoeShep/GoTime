"""Internal fixed sequence-4 CLI used only by capability-specific wrappers."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from render_v2_preflight_authorization_candidate import validate_output_path
from run_openai_stage_b_v2_pilot import DEFAULT_OUTPUT_ROOT
from v2_phase_authorization_candidates import render_preflight_candidate_for_sequence
from v2_preflight_authorization_activation import activation_paths, load_active_preflight_authorization
from v2_sequence_4_authorization_candidate import load_sequence_4_preflight_candidate
from v2_sequence_4_preflight_evidence_review import review_sequence_4_preflight_evidence
from v2_sequence_4_preflight_authorization import (
    activate_sequence_4_preflight,
    install_sequence_4_for_review,
    plan_sequence_4_activation,
    recover_sequence_4_preflight,
    review_sequence_4_activation,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _emit(values) -> None:
    for key, value in values.items():
        if isinstance(value, bool):
            value = str(value).lower()
        elif isinstance(value, list):
            value = json.dumps(value, separators=(",", ":"))
        print(f"{key}={value}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="operation", required=True)
    render = commands.add_parser("render")
    for name in ("output", "approver", "approved-at", "activated-at", "expires-at", "reason"):
        render.add_argument(f"--{name}", required=True)
    install = commands.add_parser("install")
    install.add_argument("--source", required=True); install.add_argument("--expected-sha256", required=True)
    review = commands.add_parser("review")
    review.add_argument("--artifact-sha256", required=True); review.add_argument("--reviewer", required=True)
    review.add_argument("--decision", required=True, choices=("approve", "reject", "request_changes"))
    review.add_argument("--reviewed-at", required=True); review.add_argument("--notes", required=True)
    evidence_review = commands.add_parser("evidence-review")
    evidence_review.add_argument("--evidence-sha256", required=True)
    evidence_review.add_argument("--input-tokens", required=True, type=int)
    evidence_review.add_argument("--conservative-cost", required=True)
    evidence_review.add_argument("--reviewer", required=True)
    evidence_review.add_argument("--decision", required=True, choices=("approve", "reject", "request_changes"))
    evidence_review.add_argument("--reviewed-at", required=True)
    for name in ("token-count-plausible", "cost-within-limit", "frozen-bindings-confirmed", "evidence-history-confirmed"):
        evidence_review.add_argument(f"--{name}", required=True, choices=("true", "false"))
    evidence_review.add_argument("--notes", required=True)
    plan = commands.add_parser("plan")
    activate = commands.add_parser("activate")
    for command in (plan, activate):
        for name in ("artifact-sha256", "installation-record-sha256", "activation-review-sha256"):
            command.add_argument(f"--{name}", required=True)
    activate.add_argument("--operator", required=True); activate.add_argument("--operator-intent", required=True)
    close = commands.add_parser("close")
    close.add_argument("--reason", required=True, choices=("success", "activation_recovery", "operator_cancellation", "expiration", "bounded_failure"))
    commands.add_parser("verify-active")
    args = parser.parse_args(argv)
    try:
        now = _now()
        if args.operation == "render":
            output = validate_output_path(args.output)
            result = render_preflight_candidate_for_sequence(sequence=4,
                candidate_loader=load_sequence_4_preflight_candidate, output_path=output,
                approver=args.approver, approved_at=args.approved_at,
                activated_at=args.activated_at, expires_at=args.expires_at,
                authorization_reason=args.reason, now=now)
            _emit({"output_path": result.path, "sha256": result.digest})
        elif args.operation == "install":
            result = install_sequence_4_for_review(source=Path(args.source), expected_sha256=args.expected_sha256, now=now)
            _emit({key: result[key] for key in ("installed_path", "sha256", "installation_record", "installation_record_sha256", "authoritative")})
        elif args.operation == "review":
            result = review_sequence_4_activation(artifact_sha256=args.artifact_sha256,
                reviewer=args.reviewer, decision=args.decision, reviewed_at=args.reviewed_at,
                notes=args.notes, now=now)
            _emit({key: result[key] for key in ("review_path", "review_sha256", "decision", "authoritative", "activated")})
        elif args.operation == "evidence-review":
            result = review_sequence_4_preflight_evidence(
                evidence_sha256=args.evidence_sha256, input_tokens=args.input_tokens,
                conservative_cost=args.conservative_cost, reviewer=args.reviewer,
                decision=args.decision, reviewed_at=args.reviewed_at,
                token_count_plausible=args.token_count_plausible == "true",
                cost_within_limit=args.cost_within_limit == "true",
                frozen_bindings_confirmed=args.frozen_bindings_confirmed == "true",
                evidence_history_confirmed=args.evidence_history_confirmed == "true",
                notes=args.notes, now=now)
            _emit(result)
        elif args.operation == "plan":
            _emit(plan_sequence_4_activation(artifact_sha256=args.artifact_sha256,
                installation_record_sha256=args.installation_record_sha256,
                activation_review_sha256=args.activation_review_sha256, now=now))
        elif args.operation == "activate":
            _emit(activate_sequence_4_preflight(artifact_sha256=args.artifact_sha256,
                installation_record_sha256=args.installation_record_sha256,
                activation_review_sha256=args.activation_review_sha256,
                operator=args.operator, operator_intent=args.operator_intent, now=now))
        elif args.operation == "close":
            result = recover_sequence_4_preflight(reason=args.reason, now=now)
            path = activation_paths(sequence=4).closure
            _emit({"closure_path": path.resolve(), "closure_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                   "transaction_state": result["transaction_state"], "authorization_closed": result["authorization_closed"],
                   "sequence": 4, "generation_authorized": False})
        else:
            active = load_active_preflight_authorization(now=now, expected_sequence=4)
            remaining = int((active.authorization.expires_at - now).total_seconds())
            if remaining < 180:
                raise ValueError("fewer than 180 seconds remain")
            _emit({"sequence": 4, "phase": "preflight", "transaction_state": "committed",
                   "generation_authorized": False, "seconds_remaining": remaining})
    except (OSError, ValueError) as error:
        print(f"sequence_4_{args.operation.replace('-', '_')}_error: rejected", file=sys.stderr)
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
