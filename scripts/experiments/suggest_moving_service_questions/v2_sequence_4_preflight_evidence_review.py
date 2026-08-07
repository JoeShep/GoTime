"""Bounded, offline human review of exact sequence-4 preflight evidence."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Mapping

from run_openai_stage_b_v2_pilot import DEFAULT_OUTPUT_ROOT, prepare_frozen_v2_pilot
from run_openai_stage_b_v2_two_gate import frozen_binding_identity, phase_paths
from v2_preflight_authorization_activation import REPOSITORY_ROOT, activation_paths

SEQUENCE = 4
RUN_SERIES = "moving-service-stage-b-v2-pilot-20260802"
FIXTURE = "storage_unknown"
DECISIONS = frozenset({"approve", "reject", "request_changes"})
MAX_NOTES = 500


class Sequence4EvidenceReviewError(ValueError):
    pass


def _utc(value: str, field: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z") or "." in value:
        raise Sequence4EvidenceReviewError(f"{field} must be whole-second UTC Z")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise Sequence4EvidenceReviewError(f"{field} is invalid") from error
    if parsed.tzinfo is None or parsed.utcoffset().total_seconds() != 0:
        raise Sequence4EvidenceReviewError(f"{field} must be UTC")
    return parsed


def _stamp(value: datetime) -> str:
    if value.tzinfo is None:
        raise Sequence4EvidenceReviewError("review clock must be timezone-aware")
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_object(path: Path) -> tuple[bytes, dict[str, object]]:
    if path.is_symlink() or not path.is_file():
        raise Sequence4EvidenceReviewError("required evidence path is unsafe or absent")
    raw = path.read_bytes()
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise Sequence4EvidenceReviewError("evidence must be a JSON object")
    return raw, value


def _write_exclusive(path: Path, value: Mapping[str, object]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    payload = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    return hashlib.sha256(payload).hexdigest()


def review_sequence_4_preflight_evidence(
    *, evidence_sha256: str, input_tokens: int, conservative_cost: str,
    reviewer: str, decision: str, reviewed_at: str,
    token_count_plausible: bool, cost_within_limit: bool,
    frozen_bindings_confirmed: bool, evidence_history_confirmed: bool,
    notes: str, now: datetime, output_root: Path = DEFAULT_OUTPUT_ROOT,
    repository_root: Path = REPOSITORY_ROOT,
) -> Mapping[str, object]:
    if decision not in DECISIONS or not reviewer.strip() or not notes.strip() or len(notes) > MAX_NOTES:
        raise Sequence4EvidenceReviewError("review decision, reviewer, or notes are invalid")
    paths = phase_paths(output_root, sequence=SEQUENCE)
    active_paths = activation_paths(repository_root=repository_root, output_root=output_root, sequence=SEQUENCE)
    if paths["preflight_review"].exists():
        raise Sequence4EvidenceReviewError("sequence-4 preflight evidence was already reviewed")
    evidence_bytes, evidence = _load_object(paths["preflight_evidence"])
    actual_digest = hashlib.sha256(evidence_bytes).hexdigest()
    if evidence_sha256 != actual_digest:
        raise Sequence4EvidenceReviewError("preflight evidence digest differs")
    expected_identity = {
        "run_series_id": RUN_SERIES, "sequence": SEQUENCE, "fixture_id": FIXTURE,
        "phase": "preflight", "provider": "OpenAI",
        "ai_model_identifier": "gpt-4.1-mini-2025-04-14", "sdk_pin": "openai==2.45.0",
        "maximum_output_tokens": 500, "token_preflight_timeout_seconds": 5,
        "automatic_retries": 0, "store": False, "stream": False,
        "background": False, "truncation": "disabled", "tools": [],
    }
    if any(evidence.get(key) != value for key, value in expected_identity.items()):
        raise Sequence4EvidenceReviewError("sequence-4 evidence identity or scope differs")
    frozen = frozen_binding_identity(prepare_frozen_v2_pilot())
    if any(evidence.get(key) != value for key, value in frozen.items()):
        raise Sequence4EvidenceReviewError("frozen evidence bindings differ")
    for field in ("deterministic_request_digest", "canonical_attempt_digest", "provider_preflight_fingerprint"):
        value = evidence.get(field)
        if not isinstance(value, str) or len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
            raise Sequence4EvidenceReviewError(f"{field} is invalid")
    try:
        supplied_cost = Decimal(conservative_cost)
        recorded_cost = Decimal(str(evidence.get("conservative_maximum_generation_cost")))
    except (InvalidOperation, ValueError) as error:
        raise Sequence4EvidenceReviewError("conservative cost is invalid") from error
    if evidence.get("input_tokens") != input_tokens or recorded_cost != supplied_cost or recorded_cost > Decimal("0.03"):
        raise Sequence4EvidenceReviewError("token or cost binding differs")
    created_at = _utc(str(evidence.get("created_at")), "created_at")
    deadline = _utc(str(evidence.get("review_deadline")), "review_deadline")
    review_time = _utc(reviewed_at, "reviewed_at")
    current = datetime.fromisoformat(_stamp(now).replace("Z", "+00:00"))
    if review_time < created_at or review_time > current:
        raise Sequence4EvidenceReviewError("review timestamp ordering is invalid")
    confirmations = all((token_count_plausible, cost_within_limit,
                         frozen_bindings_confirmed, evidence_history_confirmed))
    if decision == "approve" and (not confirmations or review_time >= deadline or current >= deadline):
        raise Sequence4EvidenceReviewError("approved evidence review is late or unconfirmed")
    if active_paths.active.exists() or active_paths.execution_manifest.read_bytes() != active_paths.closed_manifest.read_bytes():
        raise Sequence4EvidenceReviewError("repository authority is not permanently closed")
    for required in (paths["preflight_audit"], paths["preflight_closure"]):
        _load_object(required)
    record = {
        "run_series_id": RUN_SERIES, "sequence": SEQUENCE, "fixture_id": FIXTURE,
        "phase": "preflight_review", "decision": decision,
        "review_status": {"approve": "approved", "reject": "rejected",
                          "request_changes": "request_changes"}[decision],
        "reviewer": reviewer.strip(), "reviewed_at": reviewed_at,
        "token_count_plausible": token_count_plausible,
        "cost_within_limit": cost_within_limit,
        "spend_within_ceiling": cost_within_limit,
        "frozen_bindings_confirmed": frozen_bindings_confirmed,
        "frozen_bindings_match": frozen_bindings_confirmed,
        "evidence_history_confirmed": evidence_history_confirmed,
        "evidence_fresh_and_unused": evidence_history_confirmed,
        "bounded_notes": notes,
        "preflight_evidence_digest": actual_digest,
        "input_tokens": input_tokens,
        "conservative_maximum_generation_cost": str(recorded_cost),
        "deterministic_request_digest": evidence["deterministic_request_digest"],
        "canonical_attempt_digest": evidence["canonical_attempt_digest"],
        "provider_fingerprint": evidence["provider_preflight_fingerprint"],
        "frozen_v2_manifest_digest": evidence["frozen_v2_manifest_digest"],
        "prompt_digest": evidence["prompt_digest"],
        "provider_schema_digest": evidence["provider_schema_digest"],
        "pilot_configuration_digest": evidence["pilot_configuration_digest"],
        "provider": evidence["provider"],
        "ai_model_identifier": evidence["ai_model_identifier"],
        "sdk_pin": evidence["sdk_pin"],
        "evidence_created_at": evidence["created_at"],
        "review_deadline": evidence["review_deadline"],
        "authoritative": False, "generation_authorized": False,
        "generation_gate_binding_eligible": decision == "approve",
    }
    review_digest = _write_exclusive(paths["preflight_review"], record)
    return {"review_path": paths["preflight_review"].resolve(), "review_sha256": review_digest,
            "decision": decision, "generation_gate_binding_eligible": decision == "approve",
            "authoritative": False, "generation_authorized": False}
