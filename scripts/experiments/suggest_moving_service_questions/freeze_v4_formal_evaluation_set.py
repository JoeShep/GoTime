"""Build and verify the offline frozen-v4 formal-evaluation case package."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Callable, Mapping

from app.moving_service_questions import (
    InformationStatus,
    MovingServiceTrustedState,
)
from moving_service_questions_v2 import construct_request_v2
from moving_service_questions_v4 import (
    PROMPT_VERSION_V4,
    SCHEMA_VERSION_V4,
    MovingServiceQuestionRequestV4,
)
from openai_transport_v4 import make_v4_openai_transport
from real_model_adapter import MovingServiceProviderRequest
from run_openai_stage_b_v2_pilot import PreparedV2Pilot
from run_openai_stage_b_v4_pilot import (
    FROZEN_V4_MANIFEST_DIGEST,
    FrozenV4ProviderMetadata,
    canonical_attempt_digest,
    construct_frozen_v4_provider_request,
    deterministic_request_digest,
    prepare_frozen_v4_provider_metadata,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
PLAN_PATH = REPOSITORY_ROOT / "docs/experiments/suggest-moving-service-questions/v4-formal-evaluation-plan.md"
PACKAGE_ROOT = REPOSITORY_ROOT / "docs/experiments/suggest-moving-service-questions/v4-formal-evaluation"
SET_ID = "suggest-moving-service-questions-v4-formal-evaluation-set-v1"
PLAN_DIGEST = "5c5d84effe84fa7a951ae991759db05b2fea1038f4ef20a8aa297a3feff78a22"
KNOWLEDGE_ID = "moving-service.temporary-storage-planning.fmcsa.v1"
FALLBACK_BASIS = (
    "Compare clarity and usefulness with fallback-temporary-storage-v2: "
    "Might you need temporary storage before final delivery?"
)
GENERATION_CASE_IDS = tuple(f"eval-v4-{index:02d}" for index in (*range(1, 7), 9, 10))
EMPTY_CASE_IDS = ("eval-v4-07", "eval-v4-08")
BUDGET_PRECEDENCE = (
    "The case-bound execution budget in this artifact supersedes only the provisional "
    "live-call budget values in the approved evaluation plan. All other plan requirements "
    "and graduation criteria remain unchanged."
)


def _information(status: str, value: object = None) -> dict[str, object]:
    return {"status": status, "value": value}


def _state(*, goal: str, origin: str, destination: str, target: str,
           household: str, storage: str = "missing", storage_value: object = None,
           packing: str = "full_packing", drive: bool = False,
           preference: str = "balance", specialty: bool = False,
           constraints: tuple[str, ...] = ()) -> dict[str, object]:
    return {
        "goal_summary": goal,
        "move_type": "interstate",
        "origin_region": origin,
        "destination_region": destination,
        "target_move_window": target,
        "household_size": _information("known", household),
        "temporary_storage_need": _information(storage, storage_value),
        "packing_preference": _information("known", packing),
        "willing_to_drive_rental_truck": _information("known", drive),
        "cost_vs_convenience_preference": _information("known", preference),
        "specialty_item_needs": _information("known", specialty),
        "known_constraints": list(constraints),
    }


def _case(*, case_id: str, purpose: str, state: dict[str, object],
          expected_nonempty: bool, failure_modes: tuple[str, ...],
          fallback_basis: str = FALLBACK_BASIS,
          context: str = "Clarify unresolved moving-service needs before investigating service models.",
          expected_empty_reason: str | None = None) -> dict[str, object]:
    return {
        "case_id": case_id,
        "case_purpose": purpose,
        "trusted_input_state": state,
        "deterministic_context_current_recommendation": context,
        "intentionally_missing_information": (
            ["temporary_storage_need"] if expected_nonempty else []
        ),
        "applicable_missing_information_categories": (
            ["temporary_storage_need"] if expected_nonempty else []
        ),
        "relevant_knowledge_ids": [KNOWLEDGE_ID],
        "expected_nonempty": expected_nonempty,
        "expected_category": "temporary_storage_need" if expected_nonempty else None,
        "expected_answer_type": "boolean" if expected_nonempty else None,
        "expected_requires_user_confirmation": True if expected_nonempty else None,
        "expected_empty_reason": expected_empty_reason,
        "primary_failure_modes": list(failure_modes),
        "fallback_comparison_basis": fallback_basis,
        "frozen_v4_manifest_sha256": FROZEN_V4_MANIFEST_DIGEST,
        "prompt_version": PROMPT_VERSION_V4,
        "schema_version": SCHEMA_VERSION_V4,
        "knowledge_fixture_version": "moving-service-storage-fixture-v2",
        "request_model": "MovingServiceQuestionRequestV4",
    }


def source_cases() -> list[dict[str, object]]:
    default_constraint = ("The household is unwilling to drive a rental truck.",)
    return [
        _case(case_id="eval-v4-01", purpose="ordinary baseline", expected_nonempty=True,
              state=_state(goal="Relocate the household from Tennessee to Northern California.",
                           origin="Tennessee", destination="Northern California",
                           target="explicitly_unknown", household="household",
                           constraints=default_constraint),
              failure_modes=("wrong_category", "unsupported_fact", "grounding_failure", "modality_overstatement")),
        _case(case_id="eval-v4-02", purpose="ordinary concrete timing and self-packing", expected_nonempty=True,
              state=_state(goal="Relocate the household from Illinois to Oregon.", origin="Illinois",
                           destination="Oregon", target="September-October 2026", household="two_adults",
                           packing="self_pack"),
              failure_modes=("irrelevant_location_or_timing", "invented_delivery_plan", "missing_confirmation")),
        _case(case_id="eval-v4-03", purpose="ordinary larger move with specialty-item distraction", expected_nonempty=True,
              state=_state(goal="Relocate the household from Georgia to Colorado.", origin="Georgia",
                           destination="Colorado", target="explicitly_unknown", household="family_of_five",
                           packing="partial_help", specialty=True,
                           constraints=("A piano may need special handling.",)),
              failure_modes=("category_drift", "specialty_item_diversion", "unsupported_service_claim")),
        _case(case_id="eval-v4-04", purpose="ordinary cost-sensitive self-drive context", expected_nonempty=True,
              state=_state(goal="Relocate the household from New York to Texas.", origin="New York",
                           destination="Texas", target="explicitly_unknown", household="one_adult",
                           packing="self_pack", drive=True, preference="minimize_cost"),
              failure_modes=("price_claim", "self_drive_recommendation", "service_selection", "modality_overstatement")),
        _case(case_id="eval-v4-05", purpose="ambiguous lease and delivery scheduling", expected_nonempty=True,
              state=_state(goal="Relocate the household from Minnesota to Washington.", origin="Minnesota",
                           destination="Washington", target="date_not_final", household="household",
                           constraints=("The current lease end is not final.", "The delivery schedule is not known.")),
              failure_modes=("inferred_timing_gap", "invented_booking", "invented_delivery_arrangement", "storage_necessity")),
        _case(case_id="eval-v4-06", purpose="ambiguous packing, effort, and artwork distractions", expected_nonempty=True,
              state=_state(goal="Relocate the household from Florida to Virginia.", origin="Florida",
                           destination="Virginia", target="explicitly_unknown", household="two_adults",
                           preference="minimize_hands_on_work", specialty=True,
                           constraints=("Fragile artwork may need special handling.",)),
              failure_modes=("irrelevant_detail", "provider_recommendation", "specialty_item_diversion", "invented_fact")),
        _case(case_id="eval-v4-07", purpose="expected empty because storage is known false", expected_nonempty=False,
              state=_state(goal="Relocate the household from Tennessee to Northern California.",
                           origin="Tennessee", destination="Northern California",
                           target="explicitly_unknown", household="household", storage="known",
                           storage_value=False, constraints=default_constraint),
              expected_empty_reason="temporary_storage_need is already known false",
              failure_modes=("reask_known_state", "manufactured_alternative_question", "fallback_selection"),
              fallback_basis="Correct empty result versus erroneously asking fallback-temporary-storage-v2."),
        _case(case_id="eval-v4-08", purpose="expected empty because storage is not applicable", expected_nonempty=False,
              state=_state(goal="Relocate the household from Alaska to Washington.", origin="Alaska",
                           destination="Washington", target="explicitly_unknown", household="one_adult",
                           storage=InformationStatus.NOT_APPLICABLE.value, packing="self_pack", drive=True,
                           preference="minimize_cost"),
              expected_empty_reason="temporary_storage_need uses existing status not_applicable and is not missing",
              failure_modes=("treat_not_applicable_as_missing", "manufactured_question", "manufactured_warning"),
              fallback_basis="Correct empty result versus any generated or fallback question."),
        _case(case_id="eval-v4-09", purpose="modality and service-selection stress", expected_nonempty=True,
              state=_state(goal="Relocate the household from Ohio to Arizona.", origin="Ohio",
                           destination="Arizona", target="explicitly_unknown", household="household",
                           constraints=("A planning worksheet labels storage necessary.",)),
              context="Determine whether storage is required and choose the best full-service mover.",
              failure_modes=("required", "requirement", "must", "will_need", "necessity_equivalent",
                             "service_provider_or_model_selection")),
        _case(case_id="eval-v4-10", purpose="grounding and unsupported-inference stress", expected_nonempty=True,
              state=_state(goal="Relocate after a possible home sale from Tennessee to California.",
                           origin="Tennessee", destination="California",
                           target="after_sale_timing_unconfirmed", household="family",
                           constraints=("Destination housing is undecided.", "No delivery arrangement is confirmed.")),
              failure_modes=("invented_home_or_property_fact", "invented_destination_fact", "invented_timing_fact",
                             "invented_storage_circumstance", "service_requirement", "grounding_mismatch")),
    ]


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _digest_path(path: Path) -> str:
    return _digest_bytes(path.read_bytes())


def _request_for_case(case: Mapping[str, object]) -> MovingServiceQuestionRequestV4:
    trusted = MovingServiceTrustedState.model_validate(case["trusted_input_state"])
    request_v2 = construct_request_v2(trusted)
    document = request_v2.model_dump(mode="python")
    document["prompt_version"] = PROMPT_VERSION_V4
    document["schema_version"] = SCHEMA_VERSION_V4
    document["deterministic_context"]["current_recommendation"] = case[
        "deterministic_context_current_recommendation"
    ]
    return MovingServiceQuestionRequestV4.model_validate(document)


def bind_case(source: Mapping[str, object], metadata: FrozenV4ProviderMetadata,
              provider_request_constructor: Callable[..., MovingServiceProviderRequest]
              = MovingServiceProviderRequest) -> tuple[dict[str, object],
                                                        dict[str, object],
                                                        dict[str, object]]:
    """Bind one case, entering provider-request construction only when eligible."""
    case = dict(source)
    request = _request_for_case(case)
    missing = [item.category_id.value for item in request.missing_information]
    generation_eligible = missing == ["temporary_storage_need"]
    expected_nonempty = bool(case["expected_nonempty"])
    if generation_eligible != expected_nonempty:
        raise ValueError(f"deterministic eligibility drifted for {case['case_id']}")
    case_input = {
        "trusted_input_state": case["trusted_input_state"],
        "deterministic_context_current_recommendation": case[
            "deterministic_context_current_recommendation"
        ],
        "intentionally_missing_information": case["intentionally_missing_information"],
    }
    case["deterministic_case_input_sha256"] = _digest_bytes(_canonical(case_input))
    case["provider_request_expected"] = generation_eligible
    if generation_eligible:
        provider_request = construct_frozen_v4_provider_request(
            metadata, request, provider_request_constructor
        )
        prepared = PreparedV2Pilot(
            request, provider_request, metadata.manifest, metadata.pilot_configuration
        )
        request_digest = deterministic_request_digest(prepared)
        attempt_digest = canonical_attempt_digest(prepared)
        fingerprint = make_v4_openai_transport(
            SimpleNamespace(max_retries=0), prepared
        ).request_fingerprint(prepared.provider_request)
    else:
        request_digest = attempt_digest = fingerprint = None
    case["deterministic_request_sha256"] = request_digest
    case["canonical_attempt_sha256"] = attempt_digest
    case["provider_fingerprint"] = fingerprint
    expected = {
        "case_id": case["case_id"],
        "deterministic_gate_action": "invoke_ai_generation" if generation_eligible else "return_empty_without_generation",
        "provider_request_expected": generation_eligible,
        "expected_suggestion_count": 1 if generation_eligible else 0,
        "expected_category": case["expected_category"],
        "expected_answer_type": case["expected_answer_type"],
        "expected_requires_user_confirmation": case["expected_requires_user_confirmation"],
        "fallback_recommended": False,
        "warnings": [],
    }
    identity = {
        "case_id": case["case_id"],
        "provider_request_expected": generation_eligible,
        "deterministic_case_input_sha256": case["deterministic_case_input_sha256"],
        "deterministic_request_sha256": request_digest,
        "canonical_attempt_sha256": attempt_digest,
        "provider_fingerprint": fingerprint,
        "provider": "OpenAI" if generation_eligible else None,
        "ai_model_identifier": "gpt-4.1-mini-2025-04-14" if generation_eligible else None,
        "sdk": "openai==2.45.0" if generation_eligible else None,
    }
    return case, expected, identity


def build_documents() -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    if _digest_path(PLAN_PATH) != PLAN_DIGEST:
        raise ValueError("formal evaluation plan digest drifted")
    metadata = prepare_frozen_v4_provider_metadata()
    cases: list[dict[str, object]] = []
    expected: list[dict[str, object]] = []
    identities: list[dict[str, object]] = []
    for source in source_cases():
        case, behavior, identity = bind_case(source, metadata)
        cases.append(case)
        expected.append(behavior)
        identities.append(identity)
    return (
        {"evaluation_set_id": SET_ID, "evaluation_set_version": 1,
         "plan_sha256": PLAN_DIGEST, "cases": cases},
        {"evaluation_set_id": SET_ID, "expected_behaviors": expected,
         "future_generation_attempts": 8, "deterministic_empty_results": 2,
         "future_token_preflight_measurements": 8, "retries": 0,
         "maximum_provider_spend_usd": "0.24"},
        {"evaluation_set_id": SET_ID, "request_identities": identities},
    )


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def review_bytes() -> bytes:
    return (
        "# Frozen-v4 formal-evaluation case-binding review\n\n"
        f"Evaluation-set ID: `{SET_ID}`.\n\n"
        "All ten approved cases validate through the existing frozen-v4 domain and request "
        "schemas. Cases 1–6, 9, and 10 are generation-eligible. Case 7 uses "
        "`known(false)` and case 8 uses the existing `not_applicable` status; both are "
        "deterministically empty before provider-request construction.\n\n"
        "The eight provider-eligible cases bind literal deterministic-request, canonical-attempt, "
        "and provider-fingerprint digests. The empty cases bind null provider identities rather "
        "than invented hashes. Frozen v4, validator, fallback, and runtime reachability are unchanged.\n\n"
        "The manifest-bound `execution-budget.json` explicitly supersedes only the plan's "
        "provisional live-call budget. Future maximums are eight token preflights, eight "
        "generations, zero retries, and a `$0.24` aggregate provider ceiling. All other plan "
        "requirements and graduation criteria remain unchanged. This record authorizes no "
        "provider operation.\n"
    ).encode("utf-8")


def execution_budget_bytes() -> bytes:
    return _json_bytes({
        "deterministic_empty_case_ids": list(EMPTY_CASE_IDS),
        "deterministic_empty_cases": 2,
        "empty_case_provider_requests": 0,
        "evaluation_set_id": SET_ID,
        "generation_case_ids": list(GENERATION_CASE_IDS),
        "generation_eligible_cases": 8,
        "maximum_attempts_per_generation_case": 1,
        "maximum_generation_attempts": 8,
        "maximum_provider_spend_usd": "0.24",
        "maximum_token_preflights": 8,
        "precedence": BUDGET_PRECEDENCE,
        "retries": 0,
        "source_plan_sha256": PLAN_DIGEST,
        "spending_authorized": False,
        "status": "final_case_bound_budget",
        "supersedes": "provisional_live_call_budget_in_plan",
        "total_evaluation_outcomes": 10,
    })


def materialized_files() -> dict[str, bytes]:
    cases, expected, identities = build_documents()
    return {
        "evaluation-cases.json": _json_bytes(cases),
        "expected-behavior.json": _json_bytes(expected),
        "request-identities.json": _json_bytes(identities),
        "case-binding-review.md": review_bytes(),
        "execution-budget.json": execution_budget_bytes(),
    }


def validate_documents(cases: Mapping[str, object], expected: Mapping[str, object],
                       identities: Mapping[str, object]) -> None:
    """Reject any semantically or cryptographically drifted case binding."""
    rebuilt_cases, rebuilt_expected, rebuilt_identities = build_documents()
    if cases != rebuilt_cases:
        raise ValueError("evaluation cases or exact case bindings drifted")
    if expected != rebuilt_expected:
        raise ValueError("expected deterministic behavior drifted")
    if identities != rebuilt_identities:
        raise ValueError("exact request identities drifted")


def manifest_bytes(files: Mapping[str, bytes]) -> bytes:
    manifest = {
        "evaluation_set_id": SET_ID,
        "evaluation_set_version": 1,
        "status": "frozen_offline_only",
        "plan_path": str(PLAN_PATH.relative_to(REPOSITORY_ROOT)),
        "plan_sha256": PLAN_DIGEST,
        "frozen_v4_manifest_sha256": FROZEN_V4_MANIFEST_DIGEST,
        "artifact_sha256": {name: _digest_bytes(value) for name, value in sorted(files.items())},
        "case_count": 10,
        "generation_eligible_case_count": 8,
        "deterministic_empty_case_count": 2,
        "live_authorized": False,
        "runtime_reachable": False,
    }
    return _json_bytes(manifest)


def write_package() -> None:
    PACKAGE_ROOT.mkdir(parents=True, exist_ok=True)
    files = materialized_files()
    for name, value in files.items():
        (PACKAGE_ROOT / name).write_bytes(value)
    (PACKAGE_ROOT / "manifest.json").write_bytes(manifest_bytes(files))


def verify_package() -> None:
    files = materialized_files()
    for name, expected in files.items():
        if (PACKAGE_ROOT / name).read_bytes() != expected:
            raise ValueError(f"evaluation artifact drifted: {name}")
    expected_manifest = manifest_bytes(files)
    if (PACKAGE_ROOT / "manifest.json").read_bytes() != expected_manifest:
        raise ValueError("evaluation manifest drifted")
    validate_documents(
        json.loads((PACKAGE_ROOT / "evaluation-cases.json").read_text()),
        json.loads((PACKAGE_ROOT / "expected-behavior.json").read_text()),
        json.loads((PACKAGE_ROOT / "request-identities.json").read_text()),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    write_package() if args.write else verify_package()
    print(f"evaluation_set_id={SET_ID}")
    print("case_count=10")
    print("generation_eligible=8")
    print("deterministic_empty=2")
    print("provider_operations_performed=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
