"""Immutable, coordination-only bindings for frozen-v4 live evaluation state."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Mapping

AGGREGATE_ID = "suggest-moving-service-questions-v4-formal-evaluation-live-v1"
AGGREGATE_VERSION = 1
EVALUATION_SET_ID = "suggest-moving-service-questions-v4-formal-evaluation-set-v1"
EVALUATION_MANIFEST_SHA256 = "38c4db2e92368ead41f9c6f87146a83103ae7780328aa7423d13340239134e94"
FROZEN_V4_MANIFEST_SHA256 = "3cdbd2bf3606191aa52108d8284c8ab300d58a511f313f78a06be51d95fac649"
RUNNER_ID = "suggest-moving-service-questions-v4-formal-evaluation-runner-v1"
RUNNER_VERSION = 1
EXECUTION_BUDGET_SHA256 = "0d848bce8866023a5b7f7912795a6ee80b3aae471189f447911244da10777b6b"
REQUEST_IDENTITIES_SHA256 = "a23de86e93c3b83b7d51ffa5f73c5d694cd8266c5013c6d14833ad64bddd40ee"
PERMANENT_CLOSED_MANIFEST_SHA256 = "18a22d62a3e368f5a021649be56a211af959fed7b0305eab61d063022b1387fa"
AI_CASE_ORDER = tuple(f"eval-v4-{number:02d}" for number in (*range(1, 7), 9, 10))
EMPTY_CASE_IDS = ("eval-v4-07", "eval-v4-08")
CASE_ORDER = tuple(f"eval-v4-{number:02d}" for number in range(1, 11))
COORDINATION_LIFETIME_DAYS = 7
MAX_TOKEN_PREFLIGHTS = 8
MAX_GENERATIONS = 8
MAX_RETRIES = 0
PER_CASE_PROVIDER_CEILING_USD = "0.03"
AGGREGATE_PROVIDER_CEILING_USD = "0.24"
# The frozen pricing record documents no separate token-counting or
# request/platform fee. This is the preflight operation's monetary exposure,
# distinct from the total per-case provider ceiling above.
PREFLIGHT_CONSERVATIVE_PROVIDER_EXPOSURE_USD = "0.00"

ROOT = Path(__file__).resolve().parents[3]
PACKAGE = ROOT / "docs/experiments/suggest-moving-service-questions/v4-formal-evaluation"
CLOSED_MANIFEST = ROOT / "docs/experiments/suggest-moving-service-questions/v2-pilot/closed-execution-manifest.json"


class AggregateFoundationError(RuntimeError):
    pass


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_human_label(value: str, field: str) -> str:
    if not isinstance(value, str) or not 1 <= len(value) <= 80:
        raise AggregateFoundationError(f"{field} must contain 1-80 characters")
    if value != value.strip() or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 ._@'()-]*", value):
        raise AggregateFoundationError(f"{field} has invalid local audit-label format")
    return value


def verify_frozen_foundation() -> tuple[Mapping[str, object], ...]:
    expected = {
        "manifest.json": EVALUATION_MANIFEST_SHA256,
        "execution-budget.json": EXECUTION_BUDGET_SHA256,
        "request-identities.json": REQUEST_IDENTITIES_SHA256,
    }
    for name, expected_sha in expected.items():
        if file_sha256(PACKAGE / name) != expected_sha:
            raise AggregateFoundationError(f"frozen artifact mismatch: {name}")
    if file_sha256(CLOSED_MANIFEST) != PERMANENT_CLOSED_MANIFEST_SHA256:
        raise AggregateFoundationError("permanent closed execution manifest mismatch")
    closed = json.loads(CLOSED_MANIFEST.read_text())
    if closed.get("status") != "closed_no_execution_authorized":
        raise AggregateFoundationError("permanent execution manifest is not closed")
    manifest = json.loads((PACKAGE / "manifest.json").read_text())
    if (manifest.get("evaluation_set_id") != EVALUATION_SET_ID
            or manifest.get("frozen_v4_manifest_sha256") != FROZEN_V4_MANIFEST_SHA256
            or manifest.get("live_authorized") is not False
            or manifest.get("runtime_reachable") is not False):
        raise AggregateFoundationError("frozen evaluation manifest binding mismatch")
    identities = tuple(json.loads((PACKAGE / "request-identities.json").read_text())["request_identities"])
    if tuple(item.get("case_id") for item in identities) != CASE_ORDER:
        raise AggregateFoundationError("case membership or order drift")
    for item in identities:
        case_id = item["case_id"]
        expected_provider = case_id in AI_CASE_ORDER
        if item.get("provider_request_expected") is not expected_provider:
            raise AggregateFoundationError("case provider expectation drift")
        triple = (item.get("deterministic_request_sha256"), item.get("canonical_attempt_sha256"), item.get("provider_fingerprint"))
        if expected_provider != all(triple) or (not expected_provider and any(triple)):
            raise AggregateFoundationError("request identity triple drift")
    return identities


def immutable_package() -> dict[str, object]:
    identities = verify_frozen_foundation()
    package = {
        "aggregate_id": AGGREGATE_ID,
        "aggregate_version": AGGREGATE_VERSION,
        "evaluation_set_id": EVALUATION_SET_ID,
        "evaluation_manifest_sha256": EVALUATION_MANIFEST_SHA256,
        "frozen_v4_manifest_sha256": FROZEN_V4_MANIFEST_SHA256,
        "runner_id": RUNNER_ID,
        "runner_version": RUNNER_VERSION,
        "execution_budget_sha256": EXECUTION_BUDGET_SHA256,
        "request_identities_sha256": REQUEST_IDENTITIES_SHA256,
        "permanent_closed_manifest_sha256": PERMANENT_CLOSED_MANIFEST_SHA256,
        "case_order": list(CASE_ORDER),
        "ai_case_order": list(AI_CASE_ORDER),
        "deterministic_empty_case_ids": list(EMPTY_CASE_IDS),
        "case_bindings": list(identities),
        "lifetime_policy": {"calendar_days": COORDINATION_LIFETIME_DAYS, "coordination_only": True, "automatic_rollover": False},
        "budget_policy": {
            "maximum_token_preflights": MAX_TOKEN_PREFLIGHTS,
            "maximum_generations": MAX_GENERATIONS,
            "maximum_retries": MAX_RETRIES,
            "per_case_provider_ceiling_usd": PER_CASE_PROVIDER_CEILING_USD,
            "aggregate_provider_ceiling_usd": AGGREGATE_PROVIDER_CEILING_USD,
            "spending_authorized": False,
        },
        "zero_retry_rule": True,
        "provider_authority": False,
    }
    return package


def package_identity() -> str:
    return digest(immutable_package())


def validate_zero_counters(counters: Mapping[str, object]) -> None:
    expected = {
        "token_preflights_consumed": 0,
        "token_preflights_reserved": 0,
        "generations_consumed": 0,
        "generations_reserved": 0,
        "retries": 0,
        "provider_spend_reserved_usd": "0.00",
        "provider_spend_consumed_usd": "0.00",
    }
    if dict(counters) != expected:
        raise AggregateFoundationError("Milestone 1 provider counters must remain exactly zero")
    Decimal(str(counters["provider_spend_consumed_usd"]))
