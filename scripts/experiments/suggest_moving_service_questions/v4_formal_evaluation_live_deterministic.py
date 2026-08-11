"""Deterministic-only resolution of frozen formal-evaluation cases 07 and 08."""

from __future__ import annotations

from typing import Callable, Mapping

from freeze_v4_formal_evaluation_set import bind_case, source_cases
from run_openai_stage_b_v4_pilot import prepare_frozen_v4_provider_metadata
from v4_formal_evaluation_live_models import EMPTY_CASE_IDS, immutable_package
from v4_formal_evaluation_live_state import AggregateStateError, AggregateStore

DETERMINISTIC_ORDER = EMPTY_CASE_IDS
REASON_STATES = {
    "eval-v4-07": "known(false)",
    "eval-v4-08": "not_applicable",
}
EXPECTED_EMPTY_REASONS = {
    "eval-v4-07": "temporary_storage_need is already known false",
    "eval-v4-08": "temporary_storage_need uses existing status not_applicable and is not missing",
}


class ProviderBoundaryEntered(RuntimeError):
    pass


def _forbidden_provider_constructor(*args: object, **kwargs: object) -> object:
    raise ProviderBoundaryEntered("deterministic case entered provider request construction")


def bind_frozen_case(
    case_id: str,
    provider_request_constructor: Callable[..., object] = _forbidden_provider_constructor,
) -> tuple[Mapping[str, object], Mapping[str, object], Mapping[str, object]]:
    """Reuse the frozen eligibility boundary; AI controls stop at constructor entry."""
    sources = {item["case_id"]: item for item in source_cases()}
    if case_id not in sources:
        raise AggregateStateError("case is not part of the frozen evaluation set")
    return bind_case(
        sources[case_id], prepare_frozen_v4_provider_metadata(), provider_request_constructor,
    )


def deterministic_outcome(case_id: str) -> dict[str, object]:
    if case_id not in DETERMINISTIC_ORDER:
        raise AggregateStateError("deterministic resolution cannot target an AI case")
    case, behavior, identity = bind_frozen_case(case_id)
    package_binding = {
        item["case_id"]: item for item in immutable_package()["case_bindings"]
    }[case_id]
    if (
        case["expected_empty_reason"] != EXPECTED_EMPTY_REASONS[case_id]
        or behavior["deterministic_gate_action"] != "return_empty_without_generation"
        or behavior["expected_suggestion_count"] != 0
        or behavior["fallback_recommended"] is not False
        or identity != package_binding
        or identity["provider_request_expected"] is not False
        or any(identity[key] is not None for key in (
            "deterministic_request_sha256", "canonical_attempt_sha256",
            "provider_fingerprint", "provider", "ai_model_identifier", "sdk",
        ))
    ):
        raise AggregateStateError("frozen deterministic binding is not exact")
    return {
        "case_id": case_id,
        "deterministic_case_input_sha256": identity["deterministic_case_input_sha256"],
        "provider_eligible": False,
        "deterministic_result": "empty",
        "reason_state": REASON_STATES[case_id],
        "terminal": True,
        "provider_request_constructed": False,
        "provider_attempt": "none",
        "provider_spend_usd": "0.00",
    }


def resolve_deterministic_cases(store: AggregateStore) -> dict[str, object]:
    results: list[dict[str, object]] = []
    for case_id in DETERMINISTIC_ORDER:
        outcome = deterministic_outcome(case_id)
        before = store.load()
        already_completed = before["cases"][case_id]["coordination_status"] == "terminal"
        state = store._record_deterministic_outcome(case_id, outcome)
        results.append({
            "case_id": case_id,
            "already_completed": already_completed,
            "outcome": state["cases"][case_id]["deterministic_outcome"],
        })
    final = store.load()
    return {
        "aggregate_id": final["aggregate_id"],
        "status": final["status"],
        "results": results,
        "next_case_id": final["next_case_id"],
        "counters": final["counters"],
        "provider_authority": final["provider_authority"],
        "spending_authorized": final["immutable_package"]["budget_policy"]["spending_authorized"],
    }
