"""Offline generation-grant structures for Architecture A Milestone 7.

Production state cannot yet create the required reviewed preflight evidence;
Milestone 9 owns that retained result lifecycle.  These functions validate the
exact contract and are exercised through an explicitly test-only state seam.
"""

from __future__ import annotations

import tomllib
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Mapping

from v4_formal_evaluation_live_budget import decimal_money, money
from v4_formal_evaluation_live_models import (
    AGGREGATE_ID, AGGREGATE_PROVIDER_CEILING_USD, AI_CASE_ORDER,
    FROZEN_V4_MANIFEST_SHA256, MAX_RETRIES, PER_CASE_PROVIDER_CEILING_USD,
    REQUEST_IDENTITIES_SHA256, digest, package_identity,
)
from v4_formal_evaluation_live_state import format_time, parse_time

GENERATION_GRANT_SCHEMA = "suggest-moving-service-questions-v4-formal-evaluation-generation-grant-v1"
GENERATION_GRANT_VERSION = 1
GENERATION_GRANT_LIFETIME = timedelta(minutes=15)
PREFLIGHT_EVIDENCE_SCHEMA = "suggest-moving-service-questions-v4-formal-evaluation-preflight-evidence-binding-v1"
PREFLIGHT_EVIDENCE_VERSION = 1
ROOT = Path(__file__).resolve().parents[3]
PRICING_PATH = ROOT / "docs/experiments/suggest-moving-service-questions/v1/openai-run-configuration.toml"


class GenerationGrantError(ValueError):
    pass


def frozen_maximum_output_tokens(
    request_configuration: Mapping[str, object] | None = None,
) -> int:
    """Read the output bound from the canonical frozen-v4 request configuration."""
    if request_configuration is None:
        from v4_formal_evaluation_live_cases import _frozen_provider_metadata

        request_configuration = _frozen_provider_metadata()["request_configuration"]
    try:
        value = request_configuration["model_parameters"]["maximum_output_tokens"]
    except (KeyError, TypeError) as error:
        raise GenerationGrantError("frozen generation output-token bound is unavailable") from error
    if not isinstance(value, int) or value <= 0:
        raise GenerationGrantError("frozen generation output-token bound is invalid")
    return value


def conservative_generation_exposure(
    input_tokens: int,
    request_configuration: Mapping[str, object] | None = None,
) -> str:
    if not isinstance(input_tokens, int) or input_tokens <= 0:
        raise GenerationGrantError("preflight input-token count must be positive")
    pricing = tomllib.loads(PRICING_PATH.read_text())["pricing"]
    if pricing["unit_tokens"] != 1_000_000:
        raise GenerationGrantError("frozen pricing unit drifted")
    amount = (
        Decimal(input_tokens) * Decimal(pricing["uncached_input_price"])
        + Decimal(frozen_maximum_output_tokens(request_configuration))
        * Decimal(pricing["output_price"])
    ) / Decimal(pricing["unit_tokens"])
    return money(amount)


def build_reviewed_preflight_evidence(
    case_id: str, envelope: Mapping[str, object], *, input_tokens: int,
    evidence_sha256: str, review_sha256: str,
) -> dict[str, object]:
    if case_id not in AI_CASE_ORDER or envelope["immutable_binding"]["case_id"] != case_id:
        raise GenerationGrantError("preflight evidence target is not an exact AI case")
    binding = envelope["immutable_binding"]
    immutable = {
        "aggregate_id": AGGREGATE_ID,
        "aggregate_package_sha256": package_identity(),
        "case_id": case_id,
        "case_envelope_sha256": envelope["envelope_sha256"],
        "deterministic_case_input_sha256": binding["deterministic_case_input_sha256"],
        "deterministic_request_sha256": binding["deterministic_request_sha256"],
        "canonical_attempt_sha256": binding["canonical_attempt_sha256"],
        "provider_fingerprint": binding["provider_fingerprint"],
        "frozen_v4_manifest_sha256": FROZEN_V4_MANIFEST_SHA256,
        "request_identities_sha256": REQUEST_IDENTITIES_SHA256,
        "preflight_evidence_sha256": evidence_sha256,
        "preflight_review_sha256": review_sha256,
        "input_tokens": input_tokens,
        "conservative_generation_exposure_usd": conservative_generation_exposure(
            input_tokens, binding["request_configuration"]),
        "review_decision": "approve",
        "generation_gate_binding_eligible": True,
        "preflight_attempt_consumed": True,
    }
    return {
        "evidence_schema": PREFLIGHT_EVIDENCE_SCHEMA,
        "evidence_version": PREFLIGHT_EVIDENCE_VERSION,
        "evidence_binding_sha256": digest({
            "evidence_schema": PREFLIGHT_EVIDENCE_SCHEMA,
            "evidence_version": PREFLIGHT_EVIDENCE_VERSION,
            "immutable_binding": immutable,
        }),
        "immutable_binding": immutable,
    }


def validate_reviewed_preflight_evidence(
    evidence: object, case_id: str, envelope: Mapping[str, object],
) -> None:
    if not isinstance(evidence, dict):
        raise GenerationGrantError("reviewed preflight evidence is required")
    try:
        binding = evidence["immutable_binding"]
        if (
            binding.get("review_decision") != "approve"
            or binding.get("generation_gate_binding_eligible") is not True
            or binding.get("preflight_attempt_consumed") is not True
        ):
            raise GenerationGrantError("reviewed preflight evidence is not generation eligible")
        expected = build_reviewed_preflight_evidence(
            case_id, envelope, input_tokens=binding["input_tokens"],
            evidence_sha256=binding["preflight_evidence_sha256"],
            review_sha256=binding["preflight_review_sha256"],
        )
    except (KeyError, TypeError) as error:
        raise GenerationGrantError("reviewed preflight evidence is malformed") from error
    if evidence != expected:
        raise GenerationGrantError("reviewed preflight evidence does not match the exact case binding")
    for field in ("preflight_evidence_sha256", "preflight_review_sha256"):
        value = binding[field]
        if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
            raise GenerationGrantError("reviewed preflight evidence digest is malformed")


def prepared_generation_lifecycle() -> dict[str, object]:
    return {
        "status": "prepared", "attempt_status": "unused",
        "generation_budget_authorized": False, "generation_grant_active": False,
        "generation_spending_authorized": False, "dispatch_status": "not_started",
        "dispatch_authorized": False, "provider_execution_authorized": False,
        "retry_authorized": False,
    }


def active_generation_lifecycle() -> dict[str, object]:
    lifecycle = prepared_generation_lifecycle()
    lifecycle.update(
        status="active", generation_budget_authorized=True,
        generation_grant_active=True, generation_spending_authorized=True,
    )
    return lifecycle


def consumed_generation_lifecycle() -> dict[str, object]:
    """Future terminal shape; no Milestone 7 production transition creates it."""
    lifecycle = prepared_generation_lifecycle()
    lifecycle.update(
        status="consumed", attempt_status="consumed", dispatch_status="started",
    )
    return lifecycle


def build_generation_grant(
    case_id: str, envelope: Mapping[str, object], evidence: Mapping[str, object],
    activated_at: datetime,
) -> dict[str, object]:
    validate_reviewed_preflight_evidence(evidence, case_id, envelope)
    envelope_binding = envelope["immutable_binding"]
    evidence_binding = evidence["immutable_binding"]
    activated = format_time(activated_at)
    immutable = {
        "aggregate_id": AGGREGATE_ID,
        "aggregate_package_sha256": package_identity(),
        "case_id": case_id,
        "deterministic_case_input_sha256": envelope_binding["deterministic_case_input_sha256"],
        "case_envelope_sha256": envelope["envelope_sha256"],
        "deterministic_request_sha256": envelope_binding["deterministic_request_sha256"],
        "canonical_attempt_sha256": envelope_binding["canonical_attempt_sha256"],
        "provider_fingerprint": envelope_binding["provider_fingerprint"],
        "frozen_v4_manifest_sha256": envelope_binding["frozen_v4_manifest_sha256"],
        "provider": envelope_binding["provider"],
        "ai_model_identifier": envelope_binding["ai_model_identifier"],
        "sdk": envelope_binding["sdk"],
        "request_configuration": envelope_binding["request_configuration"],
        "phase": "generation",
        "preflight_evidence_binding_sha256": evidence["evidence_binding_sha256"],
        "preflight_evidence_sha256": evidence_binding["preflight_evidence_sha256"],
        "preflight_review_sha256": evidence_binding["preflight_review_sha256"],
        "conservative_operation_ceiling_usd": evidence_binding["conservative_generation_exposure_usd"],
        "per_case_provider_ceiling_usd": PER_CASE_PROVIDER_CEILING_USD,
        "aggregate_provider_ceiling_usd": AGGREGATE_PROVIDER_CEILING_USD,
        "operation_count": 1, "maximum_attempts": 1, "maximum_retries": MAX_RETRIES,
        "activated_at": activated,
        "expires_at": format_time(activated_at + GENERATION_GRANT_LIFETIME),
        "single_use": True,
    }
    grant = {
        "grant_schema": GENERATION_GRANT_SCHEMA,
        "grant_version": GENERATION_GRANT_VERSION,
        "grant_sha256": "", "immutable_binding": immutable,
        "lifecycle": prepared_generation_lifecycle(),
    }
    grant["grant_sha256"] = digest({
        "grant_schema": grant["grant_schema"], "grant_version": grant["grant_version"],
        "immutable_binding": immutable,
    })
    return grant


def validate_generation_grant(
    grant: object, case_id: str, envelope: Mapping[str, object], evidence: Mapping[str, object],
) -> None:
    if not isinstance(grant, dict):
        raise GenerationGrantError("generation grant is malformed")
    try:
        binding = grant["immutable_binding"]
        evidence_binding = evidence["immutable_binding"]
        if (
            binding["preflight_evidence_binding_sha256"] != evidence["evidence_binding_sha256"]
            or binding["preflight_evidence_sha256"] != evidence_binding["preflight_evidence_sha256"]
            or binding["preflight_review_sha256"] != evidence_binding["preflight_review_sha256"]
        ):
            raise GenerationGrantError("generation grant reviewed preflight evidence binding mismatch")
        activated = parse_time(grant["immutable_binding"]["activated_at"])
        expected = build_generation_grant(case_id, envelope, evidence, activated)
    except (KeyError, TypeError) as error:
        raise GenerationGrantError("generation grant is malformed") from error
    if {k: grant[k] for k in grant if k != "lifecycle"} != {k: expected[k] for k in expected if k != "lifecycle"}:
        raise GenerationGrantError("generation grant does not match its exact frozen binding")
    if grant.get("lifecycle") not in (
        prepared_generation_lifecycle(), active_generation_lifecycle(),
        consumed_generation_lifecycle(),
    ):
        raise GenerationGrantError("generation grant lifecycle is not exact")
    if parse_time(grant["immutable_binding"]["expires_at"]) - activated != GENERATION_GRANT_LIFETIME:
        raise GenerationGrantError("generation grant lifetime is not exactly 15 minutes")
    decimal_money(grant["immutable_binding"]["conservative_operation_ceiling_usd"], "generation exposure")


def generation_grant_is_expired(grant: Mapping[str, object], now: datetime) -> bool:
    return now >= parse_time(grant["immutable_binding"]["expires_at"])
