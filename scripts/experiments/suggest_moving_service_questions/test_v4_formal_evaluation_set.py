"""Offline integrity tests for the frozen-v4 formal-evaluation set."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from app.moving_service_questions import InformationStatus, MovingServiceTrustedState
from freeze_v4_formal_evaluation_set import (
    BUDGET_PRECEDENCE,
    EMPTY_CASE_IDS,
    GENERATION_CASE_IDS,
    PACKAGE_ROOT,
    PLAN_DIGEST,
    PLAN_PATH,
    SET_ID,
    _request_for_case,
    bind_case,
    build_documents,
    execution_budget_bytes,
    manifest_bytes,
    materialized_files,
    source_cases,
    validate_documents,
    verify_package,
)
from real_model_adapter import MovingServiceProviderRequest
from run_openai_stage_b_v4_pilot import prepare_frozen_v4_provider_metadata


EXPECTED_IDENTITIES = {
    "eval-v4-01": (
        "10dbcf24cb1a656fe3de1892f873b2fe43c07bc95185a5728488c321bdadd328",
        "f5a8c7e06d2ad9e133a5b0b92c322f09ed67205feb25314c5114fa1849fcdd0a",
        "7a3c0f7ace4ee4289f4149224fc001b215e71d4cc168edea604516fd133f450d",
        "15caaaaa6a3b43860c426c7555be7f4c7a6bf50d658c92c3c8564c1d43cb5656",
    ),
    "eval-v4-02": (
        "458f510cad775437b14310512c741b977896cc5182abca42da0048f3a0a72c3b",
        "3148281b4c699a04ca21970e99a0d996620e2edfed722ad66a6fdcf3fda4bbdd",
        "84c48181c8a9872e3429a5d8555b048808f30e71fca400a11ac998bbc91556be",
        "84766f0749c8e1a4933e19b34aeeaee75d5691ef5b32b9a00bcc1d135953a6eb",
    ),
    "eval-v4-03": (
        "541134e246bd0db3d35fb75ca8afd01b4e9197ad02a54789c83d9f996f66ed12",
        "ca02884ee9d3436f27f5093ec4d0c58bb311cce0c7cb6e6db80a3e3941f2e59f",
        "e5afeed28bf3077e2f036367e444b35ece97c2b422467a7f8eab404028cfc3d3",
        "50f9380967c1b1b125bfd9b4eb9fcba1e9227b9c1b588e6c58d28f6ac08e20b4",
    ),
    "eval-v4-04": (
        "f8c8cec42eb32fe496fb1811a31e20148c0596f2bc5109960591e3b633796673",
        "85fe16de4fa49d3e62537d51fb7af243b89faf661f8297c94b7c94329a3409c7",
        "430ce154bebff7cf855dc23f7b87f2ae88f46b2a19ac17eb74c15252efe1cca6",
        "576ee005c31f6a2e0c51a5e232a23d167f4926fae6729d0e328d1a19030f3468",
    ),
    "eval-v4-05": (
        "37b10a593ae5abb555d18a40e3eb901528a24e5c44ec4620304691de8e174d09",
        "b16966d265b0f61adf17ee3572ddc31956bcb2c3d309bea0a98789ea16edb842",
        "268d022c35c3f25e1c742bf7a765a242e574cc5e737357e8cca47deb88219ad6",
        "3bb193ec17dc60b0702bec4cf9668094e4751bf234825e48ffdcc8fdc009e595",
    ),
    "eval-v4-06": (
        "9311f91bfb49ff3138b7871582de049fb9b35d913eee8662c0bf9c7dad6c94cd",
        "53fa84d57a2c79ab268132ba75b85c4a5c25673223acf5d533a899c6817a58b0",
        "71f7b8e4e51d1c6a7eec39fe9eec3ad1fd1e32d78ce623834bcda98c215a895d",
        "ae963d3b195ae5b74791ed03362ace156facfff897bffa26c862232e4c35b7c7",
    ),
    "eval-v4-07": (
        "7cd9a1550204fbe6f228bca12f1598534ba920dfaedbd74ae7254e7f02ec2ae3",
        None,
        None,
        None,
    ),
    "eval-v4-08": (
        "bfc1ab4f6666ce10ddac6a666d8c537b63609291341db4072aa36aad0e78698e",
        None,
        None,
        None,
    ),
    "eval-v4-09": (
        "b05c696fa867a45bf2ab28c0c4a3da368d4ccfb3f4f14cc95efc4560a5a9632e",
        "10948a677230e1e959c1ac176921a701cb1a9f0a76f4e3b03e6b0cda4e2d9d00",
        "042246d50846e1d9db44dbfb07ddf867c8597f4c645958435a8ac379fda9a755",
        "0e0aaea2d0b7446281afffd9df2737598c637458cfc17e60e958bede2dd092a8",
    ),
    "eval-v4-10": (
        "1e34e5a2d4e41eef8c45b51adac3f07d31b8ecf47209bdb3b9482c902b2c652d",
        "c56e6ed36c6a509d772d9466fbf74c994d1fa86ea3394eddf6b0198d1613cfaa",
        "8e1015bf7d2f7b800d0426d1daa848b0d1d6e7f7a36adfe88394f4299de459b2",
        "5dde7725b2c5bf3775b50fc500d56858dc1be754f44abc89ec519610ad2e2075",
    ),
}


def _by_id(document: dict[str, object], field: str) -> dict[str, dict[str, object]]:
    return {item["case_id"]: item for item in document[field]}


def test_plan_and_materialized_package_are_exact() -> None:
    assert hashlib.sha256(PLAN_PATH.read_bytes()).hexdigest() == PLAN_DIGEST
    verify_package()
    files = materialized_files()
    assert (PACKAGE_ROOT / "manifest.json").read_bytes() == manifest_bytes(files)


def test_all_ten_cases_validate_and_serialize_deterministically() -> None:
    cases, _, _ = build_documents()
    assert cases["evaluation_set_id"] == SET_ID
    assert [case["case_id"] for case in cases["cases"]] == list(EXPECTED_IDENTITIES)
    for case in cases["cases"]:
        state = MovingServiceTrustedState.model_validate(case["trusted_input_state"])
        assert state.model_dump(mode="json") == MovingServiceTrustedState.model_validate_json(
            state.model_dump_json()
        ).model_dump(mode="json")
        request = _request_for_case(case)
        assert request.model_dump_json(exclude_none=False, exclude_defaults=False) == (
            _request_for_case(case).model_dump_json(exclude_none=False, exclude_defaults=False)
        )


def test_expected_behavior_is_fixed_before_model_output() -> None:
    cases, expected, identities = build_documents()
    case_map = _by_id(cases, "cases")
    behavior_map = _by_id(expected, "expected_behaviors")
    identity_map = _by_id(identities, "request_identities")
    eligible = {f"eval-v4-{index:02d}" for index in (*range(1, 7), 9, 10)}
    for case_id in EXPECTED_IDENTITIES:
        should_generate = case_id in eligible
        assert case_map[case_id]["expected_nonempty"] is should_generate
        assert behavior_map[case_id]["provider_request_expected"] is should_generate
        assert behavior_map[case_id]["deterministic_gate_action"] == (
            "invoke_ai_generation" if should_generate else "return_empty_without_generation"
        )
        assert identity_map[case_id]["provider_request_expected"] is should_generate


def test_case_7_known_false_and_case_8_not_applicable_are_empty() -> None:
    cases, _, identities = build_documents()
    case_map = _by_id(cases, "cases")
    identity_map = _by_id(identities, "request_identities")
    assert case_map["eval-v4-07"]["trusted_input_state"]["temporary_storage_need"] == {
        "status": "known", "value": False
    }
    assert case_map["eval-v4-08"]["trusted_input_state"]["temporary_storage_need"] == {
        "status": InformationStatus.NOT_APPLICABLE.value, "value": None
    }
    for case_id in ("eval-v4-07", "eval-v4-08"):
        assert _request_for_case(case_map[case_id]).missing_information == ()
        assert identity_map[case_id]["deterministic_request_sha256"] is None
        assert identity_map[case_id]["canonical_attempt_sha256"] is None
        assert identity_map[case_id]["provider_fingerprint"] is None


@pytest.mark.parametrize("case_id", EMPTY_CASE_IDS)
def test_empty_cases_never_enter_provider_request_construction(case_id: str) -> None:
    calls = 0

    def forbidden_constructor(*_args: object) -> object:
        nonlocal calls
        calls += 1
        raise AssertionError("empty case entered provider-request construction")

    source = next(case for case in source_cases() if case["case_id"] == case_id)
    case, behavior, identity = bind_case(
        source, prepare_frozen_v4_provider_metadata(), forbidden_constructor
    )
    assert calls == 0
    assert case["provider_request_expected"] is False
    assert behavior["deterministic_gate_action"] == "return_empty_without_generation"
    assert identity["deterministic_request_sha256"] is None
    assert identity["canonical_attempt_sha256"] is None
    assert identity["provider_fingerprint"] is None


def test_empty_case_non_entry_regression_guard_covers_both_states() -> None:
    calls: list[str] = []

    def recording_constructor(**_kwargs: object) -> object:
        calls.append("MovingServiceProviderRequest")
        raise AssertionError("resolved state must not construct a provider request")

    metadata = prepare_frozen_v4_provider_metadata()
    empty_sources = [case for case in source_cases() if case["case_id"] in EMPTY_CASE_IDS]
    assert [case["case_id"] for case in empty_sources] == list(EMPTY_CASE_IDS)
    for source in empty_sources:
        bind_case(source, metadata, recording_constructor)
    assert calls == []


def test_generation_case_enters_actual_provider_constructor_once() -> None:
    calls = 0

    def constructor_spy(**kwargs: object) -> MovingServiceProviderRequest:
        nonlocal calls
        calls += 1
        return MovingServiceProviderRequest(**kwargs)

    source = next(case for case in source_cases() if case["case_id"] == "eval-v4-01")
    case, behavior, identity = bind_case(
        source, prepare_frozen_v4_provider_metadata(), constructor_spy
    )
    assert calls == 1
    assert case["provider_request_expected"] is True
    assert behavior["deterministic_gate_action"] == "invoke_ai_generation"
    assert (
        identity["deterministic_request_sha256"],
        identity["canonical_attempt_sha256"],
        identity["provider_fingerprint"],
    ) == EXPECTED_IDENTITIES["eval-v4-01"][1:]


def test_raising_actual_constructor_separates_empty_and_generation_cases() -> None:
    calls = 0

    def raising_constructor(**_kwargs: object) -> MovingServiceProviderRequest:
        nonlocal calls
        calls += 1
        raise AssertionError("actual provider-request constructor entered")

    metadata = prepare_frozen_v4_provider_metadata()
    sources = {case["case_id"]: case for case in source_cases()}
    for case_id in EMPTY_CASE_IDS:
        case, _, _ = bind_case(sources[case_id], metadata, raising_constructor)
        assert case["provider_request_expected"] is False
    assert calls == 0
    with pytest.raises(AssertionError, match="actual provider-request constructor entered"):
        bind_case(sources["eval-v4-01"], metadata, raising_constructor)
    assert calls == 1


def test_literal_case_and_request_identities_are_frozen() -> None:
    _, _, identities = build_documents()
    actual = _by_id(identities, "request_identities")
    for case_id, values in EXPECTED_IDENTITIES.items():
        assert (
            actual[case_id]["deterministic_case_input_sha256"],
            actual[case_id]["deterministic_request_sha256"],
            actual[case_id]["canonical_attempt_sha256"],
            actual[case_id]["provider_fingerprint"],
        ) == values


@pytest.mark.parametrize(
    "field",
    ("deterministic_request_sha256", "canonical_attempt_sha256", "provider_fingerprint"),
)
def test_request_identity_mutation_fails_closed(field: str) -> None:
    cases, expected, identities = build_documents()
    mutated = copy.deepcopy(identities)
    mutated["request_identities"][0][field] = "0" * 64
    with pytest.raises(ValueError, match="exact request identities drifted"):
        validate_documents(cases, expected, mutated)


def test_cross_case_identity_substitution_fails_closed() -> None:
    cases, expected, identities = build_documents()
    mutated = copy.deepcopy(identities)
    first, second = mutated["request_identities"][:2]
    first["deterministic_request_sha256"] = second["deterministic_request_sha256"]
    first["canonical_attempt_sha256"] = second["canonical_attempt_sha256"]
    first["provider_fingerprint"] = second["provider_fingerprint"]
    with pytest.raises(ValueError, match="exact request identities drifted"):
        validate_documents(cases, expected, mutated)


def test_cases_are_distinct_by_state_and_testing_purpose() -> None:
    cases, _, identities = build_documents()
    assert len({case["case_purpose"] for case in cases["cases"]}) == 10
    assert len({case["deterministic_case_input_sha256"] for case in cases["cases"]}) == 10
    eligible = [item for item in identities["request_identities"] if item["provider_request_expected"]]
    assert len({item["deterministic_request_sha256"] for item in eligible}) == 8
    assert len({item["canonical_attempt_sha256"] for item in eligible}) == 8
    assert len({item["provider_fingerprint"] for item in eligible}) == 8


def test_manifest_binds_every_non_manifest_artifact() -> None:
    manifest = json.loads((PACKAGE_ROOT / "manifest.json").read_text())
    assert manifest["evaluation_set_id"] == SET_ID
    assert manifest["case_count"] == 10
    assert manifest["generation_eligible_case_count"] == 8
    assert manifest["deterministic_empty_case_count"] == 2
    assert manifest["live_authorized"] is False
    assert manifest["runtime_reachable"] is False
    for name, digest in manifest["artifact_sha256"].items():
        assert hashlib.sha256((PACKAGE_ROOT / name).read_bytes()).hexdigest() == digest
    assert "manifest.json" not in manifest["artifact_sha256"]


def test_execution_budget_explicitly_supersedes_only_provisional_plan_budget() -> None:
    budget = json.loads(execution_budget_bytes())
    assert hashlib.sha256(PLAN_PATH.read_bytes()).hexdigest() == PLAN_DIGEST
    assert budget == {
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
    }
    assert "supersedes only the provisional live-call budget" in budget["precedence"]
    assert "All other plan requirements and graduation criteria remain unchanged" in budget["precedence"]


def test_budget_case_ids_and_all_budget_artifacts_are_consistent() -> None:
    _, expected, _ = build_documents()
    budget = json.loads((PACKAGE_ROOT / "execution-budget.json").read_text())
    manifest = json.loads((PACKAGE_ROOT / "manifest.json").read_text())
    generation_ids = tuple(
        item["case_id"] for item in expected["expected_behaviors"]
        if item["provider_request_expected"]
    )
    empty_ids = tuple(
        item["case_id"] for item in expected["expected_behaviors"]
        if not item["provider_request_expected"]
    )
    assert generation_ids == GENERATION_CASE_IDS == tuple(budget["generation_case_ids"])
    assert empty_ids == EMPTY_CASE_IDS == tuple(budget["deterministic_empty_case_ids"])
    assert expected["future_generation_attempts"] == budget["maximum_generation_attempts"] == 8
    assert expected["future_token_preflight_measurements"] == budget["maximum_token_preflights"] == 8
    assert expected["deterministic_empty_results"] == budget["deterministic_empty_cases"] == 2
    assert expected["retries"] == budget["retries"] == 0
    assert expected["maximum_provider_spend_usd"] == budget["maximum_provider_spend_usd"] == "0.24"
    assert manifest["case_count"] == budget["total_evaluation_outcomes"] == 10
    assert manifest["generation_eligible_case_count"] == budget["generation_eligible_cases"] == 8
    assert manifest["deterministic_empty_case_count"] == budget["deterministic_empty_cases"] == 2
    assert budget["spending_authorized"] is False
    assert budget["empty_case_provider_requests"] == 0
    assert "execution-budget.json" in manifest["artifact_sha256"]
    assert manifest["artifact_sha256"]["execution-budget.json"] == hashlib.sha256(
        (PACKAGE_ROOT / "execution-budget.json").read_bytes()
    ).hexdigest()


def test_formal_evaluation_code_is_offline_and_not_runtime_imported() -> None:
    repository = Path(__file__).resolve().parents[3]
    runtime_roots = (repository / "backend/app", repository / "frontend/src")
    needle = "freeze_v4_formal_evaluation_set"
    assert all(
        needle not in path.read_text(errors="ignore")
        for root in runtime_roots
        for path in root.rglob("*")
        if path.is_file()
    )
