#!/usr/bin/env python3
"""Fixed, provider-free human preflight evidence review entry point."""

from __future__ import annotations

import argparse
import json

from v4_formal_evaluation_live_state import AggregateStore, parse_time


def _boolean(value: str) -> bool:
    if value not in {"true", "false"}:
        raise argparse.ArgumentTypeError("expected true or false")
    return value == "true"


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Review the exact current frozen-v4 preflight evidence")
    result.add_argument("--reviewer", required=True)
    result.add_argument("--decision", required=True, choices=("approve", "reject", "request_changes"))
    result.add_argument("--reviewed-at", required=True)
    result.add_argument("--token-count-plausible", required=True, type=_boolean)
    result.add_argument("--cost-within-limit", required=True, type=_boolean)
    result.add_argument("--frozen-bindings-confirmed", required=True, type=_boolean)
    result.add_argument("--evidence-history-confirmed", required=True, type=_boolean)
    result.add_argument("--notes", required=True)
    return result


def main() -> int:
    arguments = parser().parse_args()
    state = AggregateStore().review_preflight_evidence(
        reviewer=arguments.reviewer, decision=arguments.decision,
        reviewed_at=parse_time(arguments.reviewed_at),
        token_count_plausible=arguments.token_count_plausible,
        cost_within_limit=arguments.cost_within_limit,
        frozen_bindings_confirmed=arguments.frozen_bindings_confirmed,
        evidence_history_confirmed=arguments.evidence_history_confirmed,
        notes=arguments.notes,
    )
    case_id = state["next_case_id"]
    review = state["preflight_reviews"][case_id]
    print(json.dumps({
        "case_id": case_id, "decision": review["immutable_binding"]["decision"],
        "review_sha256": review["review_sha256"],
        "generation_gate_binding_eligible": case_id in state["reviewed_preflight_evidence"],
        "provider_operation_performed": False,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
