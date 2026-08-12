"""Exact, offline-only prospective budget reservation policy for Milestone 5."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Mapping

from v4_formal_evaluation_live_models import (
    AGGREGATE_ID, AGGREGATE_PROVIDER_CEILING_USD, AI_CASE_ORDER,
    MAX_GENERATIONS, MAX_RETRIES, MAX_TOKEN_PREFLIGHTS,
    PER_CASE_PROVIDER_CEILING_USD, PREFLIGHT_CONSERVATIVE_PROVIDER_EXPOSURE_USD,
    digest, package_identity,
)

BUDGET_RESERVATION_SCHEMA = (
    "suggest-moving-service-questions-v4-formal-evaluation-provider-budget-reservation-v1"
)
BUDGET_RESERVATION_VERSION = 1
RESERVATION_STATES = ("reserved", "released", "consumed")
ZERO_MONEY = "0.00"


class BudgetError(ValueError):
    pass


def decimal_money(value: object, field: str) -> Decimal:
    if not isinstance(value, str):
        raise BudgetError(f"{field} must be canonical decimal money")
    try:
        amount = Decimal(value)
    except InvalidOperation as error:
        raise BudgetError(f"{field} is not decimal money") from error
    canonical = format(amount, "f")
    if "." not in canonical:
        canonical += ".00"
    elif len(canonical.rsplit(".", 1)[1]) < 2:
        canonical += "0"
    if amount.is_nan() or amount.is_infinite() or amount < 0 or value != canonical:
        raise BudgetError(f"{field} must be nonnegative canonical decimal USD")
    return amount


def money(value: Decimal) -> str:
    if value.is_nan() or value.is_infinite() or value < 0:
        raise BudgetError("money value must be nonnegative exact decimal USD")
    rendered = format(value, "f")
    if "." not in rendered:
        return rendered + ".00"
    whole, fraction = rendered.split(".")
    fraction = fraction.rstrip("0")
    return f"{whole}.{fraction.ljust(2, '0')}"


def reservation_identity(reservation: Mapping[str, object]) -> str:
    return digest({
        "reservation_schema": reservation["reservation_schema"],
        "reservation_version": reservation["reservation_version"],
        "immutable_binding": reservation["immutable_binding"],
    })


def build_preflight_reservation(
    grant: Mapping[str, object],
    envelope: Mapping[str, object],
    reserved_at: str,
) -> dict[str, object]:
    binding = grant["immutable_binding"]
    case_id = binding["case_id"]
    amount = binding["conservative_operation_ceiling_usd"]
    if case_id not in AI_CASE_ORDER or envelope["envelope_sha256"] != binding["case_envelope_sha256"]:
        raise BudgetError("reservation target is not the exact AI grant envelope")
    if amount != PREFLIGHT_CONSERVATIVE_PROVIDER_EXPOSURE_USD:
        raise BudgetError("grant preflight monetary exposure does not match frozen pricing policy")
    if binding["per_case_provider_ceiling_usd"] != PER_CASE_PROVIDER_CEILING_USD:
        raise BudgetError("grant per-case ceiling does not match frozen policy")
    immutable = {
        "aggregate_id": AGGREGATE_ID,
        "aggregate_package_sha256": package_identity(),
        "case_id": case_id,
        "case_envelope_sha256": envelope["envelope_sha256"],
        "prepared_grant_sha256": grant["grant_sha256"],
        "phase": "preflight",
        "reservation_amount_usd": amount,
        "operation_count": 1,
        "reserved_at": reserved_at,
        "maximum_retries": MAX_RETRIES,
        "single_use": True,
        "per_case_provider_ceiling_usd": PER_CASE_PROVIDER_CEILING_USD,
        "aggregate_provider_ceiling_usd": AGGREGATE_PROVIDER_CEILING_USD,
    }
    reservation = {
        "reservation_schema": BUDGET_RESERVATION_SCHEMA,
        "reservation_version": BUDGET_RESERVATION_VERSION,
        "reservation_sha256": "",
        "immutable_binding": immutable,
        "lifecycle": {
            "status": "reserved",
            "provider_dispatch_status": "not_started",
            "attempt_consumed": False,
            "consumed_amount_usd": ZERO_MONEY,
            "consumed_operation_count": 0,
            "dispatch_started_at": None,
            "released_amount_usd": ZERO_MONEY,
            "release_reason": None,
            "released_at": None,
        },
    }
    reservation["reservation_sha256"] = reservation_identity(reservation)
    return reservation


def build_generation_reservation(
    grant: Mapping[str, object],
    envelope: Mapping[str, object],
    reserved_at: str,
) -> dict[str, object]:
    binding = grant["immutable_binding"]
    case_id = binding["case_id"]
    amount = binding["conservative_operation_ceiling_usd"]
    if case_id not in AI_CASE_ORDER or envelope["envelope_sha256"] != binding["case_envelope_sha256"]:
        raise BudgetError("generation reservation target is not the exact AI grant envelope")
    if binding["phase"] != "generation" or binding["per_case_provider_ceiling_usd"] != PER_CASE_PROVIDER_CEILING_USD:
        raise BudgetError("generation reservation policy binding mismatch")
    decimal_money(amount, "generation reservation amount")
    immutable = {
        "aggregate_id": AGGREGATE_ID,
        "aggregate_package_sha256": package_identity(),
        "case_id": case_id,
        "case_envelope_sha256": envelope["envelope_sha256"],
        "prepared_grant_sha256": grant["grant_sha256"],
        "phase": "generation",
        "reservation_amount_usd": amount,
        "operation_count": 1,
        "reserved_at": reserved_at,
        "maximum_retries": MAX_RETRIES,
        "single_use": True,
        "per_case_provider_ceiling_usd": PER_CASE_PROVIDER_CEILING_USD,
        "aggregate_provider_ceiling_usd": AGGREGATE_PROVIDER_CEILING_USD,
    }
    reservation = {
        "reservation_schema": BUDGET_RESERVATION_SCHEMA,
        "reservation_version": BUDGET_RESERVATION_VERSION,
        "reservation_sha256": "",
        "immutable_binding": immutable,
        "lifecycle": {
            "status": "reserved", "provider_dispatch_status": "not_started",
            "attempt_consumed": False, "consumed_amount_usd": ZERO_MONEY,
            "consumed_operation_count": 0, "dispatch_started_at": None,
            "released_amount_usd": ZERO_MONEY, "release_reason": None,
            "released_at": None,
        },
    }
    reservation["reservation_sha256"] = reservation_identity(reservation)
    return reservation


def validate_reservation(
    reservation: object,
    grant: Mapping[str, object],
    envelope: Mapping[str, object],
) -> None:
    if not isinstance(reservation, dict):
        raise BudgetError("budget reservation is malformed")
    try:
        builder = (build_preflight_reservation
                   if grant["immutable_binding"]["phase"] == "preflight"
                   else build_generation_reservation)
        expected = builder(grant, envelope, reservation["immutable_binding"]["reserved_at"])
        lifecycle = reservation["lifecycle"]
    except (KeyError, TypeError) as error:
        raise BudgetError("budget reservation is malformed") from error
    if reservation.get("reservation_sha256") != reservation_identity(reservation):
        raise BudgetError("budget reservation identity mismatch")
    if reservation["immutable_binding"] != expected["immutable_binding"] or set(reservation) != set(expected):
        raise BudgetError("budget reservation immutable binding mismatch")
    if not isinstance(lifecycle, dict) or set(lifecycle) != set(expected["lifecycle"]):
        raise BudgetError("budget reservation lifecycle is malformed")
    status = lifecycle["status"]
    if status not in RESERVATION_STATES:
        raise BudgetError("budget reservation lifecycle is unavailable")
    amount = decimal_money(reservation["immutable_binding"]["reservation_amount_usd"], "reservation amount")
    consumed = decimal_money(lifecycle["consumed_amount_usd"], "consumed amount")
    released = decimal_money(lifecycle["released_amount_usd"], "released amount")
    if status == "reserved":
        if (
            lifecycle["provider_dispatch_status"] != "not_started"
            or lifecycle["attempt_consumed"] is not False
            or consumed != 0
            or lifecycle["consumed_operation_count"] != 0
            or lifecycle["dispatch_started_at"] is not None
            or released != 0
            or lifecycle["release_reason"] is not None
            or lifecycle["released_at"] is not None
        ):
            raise BudgetError("active reservation cannot contain release state")
    elif status == "released":
        if (
            lifecycle["provider_dispatch_status"] != "not_started"
            or lifecycle["attempt_consumed"] is not False
            or consumed != 0
            or lifecycle["consumed_operation_count"] != 0
            or lifecycle["dispatch_started_at"] is not None
            or released != amount
            or lifecycle["release_reason"] != "expired_unused_dispatch_not_started"
            or not isinstance(lifecycle["released_at"], str)
        ):
            raise BudgetError("released reservation lacks exact proven-unused semantics")
    elif (
        lifecycle["provider_dispatch_status"] != "started"
        or lifecycle["attempt_consumed"] is not True
        or consumed != amount
        or lifecycle["consumed_operation_count"] != 1
        or not isinstance(lifecycle["dispatch_started_at"], str)
        or released != 0
        or lifecycle["release_reason"] is not None
        or lifecycle["released_at"] is not None
    ):
        raise BudgetError("consumed reservation lacks exact dispatch-started semantics")


def derive_budget_accounting(
    reservations: Mapping[str, Mapping[str, object]],
) -> dict[str, object]:
    cases = {
        case_id: {
            "reserved_preflight_exposure_usd": ZERO_MONEY,
            "consumed_preflight_exposure_usd": ZERO_MONEY,
            "reserved_generation_exposure_usd": ZERO_MONEY,
            "consumed_generation_exposure_usd": ZERO_MONEY,
            "total_reserved_provider_exposure_usd": ZERO_MONEY,
            "total_consumed_provider_exposure_usd": ZERO_MONEY,
            "remaining_provider_capacity_usd": PER_CASE_PROVIDER_CEILING_USD,
        }
        for case_id in AI_CASE_ORDER
    }
    reserved_total = Decimal("0.00")
    consumed_total = Decimal("0.00")
    reserved_preflights = consumed_preflights = 0
    reserved_generations = consumed_generations = 0
    for reservation in reservations.values():
        binding, lifecycle = reservation["immutable_binding"], reservation["lifecycle"]
        case_id = binding["case_id"]
        amount = decimal_money(binding["reservation_amount_usd"], "reservation amount")
        consumed = decimal_money(lifecycle["consumed_amount_usd"], "consumed amount")
        active = lifecycle["status"] == "reserved"
        reserved = amount - consumed if active else Decimal("0.00")
        reserved_total += reserved
        consumed_total += consumed
        phase = binding["phase"]
        if phase == "preflight":
            reserved_preflights += binding["operation_count"] if active else 0
            consumed_preflights += lifecycle["consumed_operation_count"]
        elif phase == "generation":
            reserved_generations += binding["operation_count"] if active else 0
            consumed_generations += lifecycle["consumed_operation_count"]
        else:
            raise BudgetError("budget reservation phase is unavailable")
        cases[case_id][f"reserved_{phase}_exposure_usd"] = money(
            Decimal(cases[case_id][f"reserved_{phase}_exposure_usd"]) + reserved)
        cases[case_id][f"consumed_{phase}_exposure_usd"] = money(
            Decimal(cases[case_id][f"consumed_{phase}_exposure_usd"]) + consumed)
        case_reserved = sum(Decimal(cases[case_id][f"reserved_{item}_exposure_usd"]) for item in ("preflight", "generation"))
        case_consumed = sum(Decimal(cases[case_id][f"consumed_{item}_exposure_usd"]) for item in ("preflight", "generation"))
        cases[case_id]["total_reserved_provider_exposure_usd"] = money(case_reserved)
        cases[case_id]["total_consumed_provider_exposure_usd"] = money(case_consumed)
        cases[case_id]["remaining_provider_capacity_usd"] = money(
            Decimal(PER_CASE_PROVIDER_CEILING_USD) - case_reserved - case_consumed
        )
    return {
        "cases": cases,
        "aggregate": {
            "total_provider_exposure_reserved_usd": money(reserved_total),
            "total_provider_exposure_consumed_usd": money(consumed_total),
            "remaining_provider_capacity_usd": money(
                Decimal(AGGREGATE_PROVIDER_CEILING_USD) - reserved_total - consumed_total
            ),
            "token_preflights_reserved": reserved_preflights,
            "token_preflights_consumed": consumed_preflights,
            "generations_reserved": reserved_generations,
            "generations_consumed": consumed_generations,
            "retries": 0,
        },
    }


def enforce_prospective_capacity(
    *,
    case_reserved: Decimal,
    case_consumed: Decimal,
    aggregate_reserved: Decimal,
    aggregate_consumed: Decimal,
    preflights_reserved: int,
    preflights_consumed: int,
    requested_amount: Decimal,
    requested_count: int = 1,
) -> None:
    values = (case_reserved, case_consumed, aggregate_reserved, aggregate_consumed, requested_amount)
    if any(value < 0 for value in values) or requested_count != 1:
        raise BudgetError("prospective accounting inputs are invalid")
    if case_reserved + case_consumed + requested_amount > Decimal(PER_CASE_PROVIDER_CEILING_USD):
        raise BudgetError("prospective reservation exceeds the per-case provider ceiling")
    if aggregate_reserved + aggregate_consumed + requested_amount > Decimal(AGGREGATE_PROVIDER_CEILING_USD):
        raise BudgetError("prospective reservation exceeds the aggregate provider ceiling")
    if preflights_reserved < 0 or preflights_consumed < 0 or preflights_reserved + preflights_consumed + requested_count > MAX_TOKEN_PREFLIGHTS:
        raise BudgetError("prospective reservation exceeds the preflight operation maximum")
    if MAX_GENERATIONS != 8 or MAX_RETRIES != 0:
        raise BudgetError("frozen generation or retry policy mismatch")


def enforce_generation_capacity(
    *, case_reserved: Decimal, case_consumed: Decimal,
    aggregate_reserved: Decimal, aggregate_consumed: Decimal,
    generations_reserved: int, generations_consumed: int,
    requested_amount: Decimal, requested_count: int = 1,
) -> None:
    values = (case_reserved, case_consumed, aggregate_reserved, aggregate_consumed, requested_amount)
    if any(value < 0 for value in values) or requested_count != 1:
        raise BudgetError("prospective generation accounting inputs are invalid")
    if case_reserved + case_consumed + requested_amount > Decimal(PER_CASE_PROVIDER_CEILING_USD):
        raise BudgetError("prospective generation reservation exceeds the per-case provider ceiling")
    if aggregate_reserved + aggregate_consumed + requested_amount > Decimal(AGGREGATE_PROVIDER_CEILING_USD):
        raise BudgetError("prospective generation reservation exceeds the aggregate provider ceiling")
    if (generations_reserved < 0 or generations_consumed < 0
            or generations_reserved + generations_consumed + requested_count > MAX_GENERATIONS):
        raise BudgetError("prospective generation reservation exceeds the generation operation maximum")
    if MAX_RETRIES != 0:
        raise BudgetError("frozen retry policy mismatch")
