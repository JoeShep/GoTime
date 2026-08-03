"""Offline review, deletion, and closure lifecycle for the v2 pilot only."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

from moving_service_questions_v2 import MovingServiceQuestionResponseV2
from run_openai_stage_b_v2_pilot import DEFAULT_OUTPUT_ROOT, _paths
from v2_follow_up_authorization import (
    FIXTURE_ID,
    RUN_SERIES_ID,
    SEQUENCE,
    close_v2_follow_up_authorization,
)

REVIEW_STATUSES = frozenset({"approved", "rejected"})
FALLBACK_COMPARISONS = frozenset(
    {"materially_better", "slightly_better", "equivalent", "slightly_worse", "materially_worse"}
)
MAX_NOTES = 500


class V2LifecycleError(ValueError):
    pass


def lifecycle_paths(output_root: Path = DEFAULT_OUTPUT_ROOT) -> dict[str, Path]:
    audit, evidence, closure = _paths(output_root)
    prefix = f"{SEQUENCE:03d}-{FIXTURE_ID}"
    return {
        "audit": audit,
        "evidence": evidence,
        "closure": closure,
        "review": audit.parent / f"{prefix}-human-review.json",
        "deletion": audit.parent / f"{prefix}-evidence-deletion.json",
    }


def _load(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise V2LifecycleError("Lifecycle artifact must be an object.")
    return value


def _exclusive(path: Path, value: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def _update_audit(path: Path, updates: Mapping[str, object]) -> None:
    audit = _load(path)
    if set(updates) - set(audit):
        raise V2LifecycleError("Lifecycle update contains unknown audit fields.")
    audit.update(updates)
    temporary = path.with_name(f".{path.name}.update")
    _exclusive(temporary, audit)
    os.replace(temporary, path)


def _timestamp(now: datetime | None) -> str:
    value = now or datetime.now(timezone.utc)
    if value.tzinfo is None:
        raise V2LifecycleError("Lifecycle time must be timezone-aware.")
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def delete_v2_response_evidence(
    *, output_root: Path = DEFAULT_OUTPUT_ROOT, reason: str, review_status: str, now: datetime | None = None
) -> Mapping[str, object]:
    paths = lifecycle_paths(output_root)
    if paths["deletion"].exists():
        return _load(paths["deletion"])
    if reason not in {"review_signoff", "retention_deadline"}:
        raise V2LifecycleError("Deletion reason is unsupported.")
    audit = _load(paths["audit"])
    stamp = _timestamp(now)
    if reason == "review_signoff" and review_status not in REVIEW_STATUSES:
        raise V2LifecycleError("Review sign-off requires a final review.")
    if reason == "retention_deadline":
        deadline = datetime.fromisoformat(str(audit["response_evidence_delete_by"]).replace("Z", "+00:00"))
        current = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        if current < deadline:
            raise V2LifecycleError("Retention deadline has not arrived.")
    existed = paths["evidence"].exists()
    if existed:
        paths["evidence"].unlink()
    record = {
        "run_series_id": RUN_SERIES_ID,
        "sequence": SEQUENCE,
        "fixture_id": FIXTURE_ID,
        "evidence_path_identifier": paths["evidence"].name,
        "deletion_reason": reason,
        "deleted_at": stamp,
        "review_status": review_status,
        "evidence_existed_before_deletion": existed,
        "deletion_completed": not paths["evidence"].exists(),
    }
    _exclusive(paths["deletion"], record)
    _update_audit(paths["audit"], {"response_evidence_deleted": True, "response_evidence_deletion_recorded_at": stamp})
    return record


def finalize_v2_human_review(
    *, review: Mapping[str, object], output_root: Path = DEFAULT_OUTPUT_ROOT, now: datetime | None = None
) -> Mapping[str, object]:
    expected = {
        "human_review_status", "grounding_supported", "invented_user_fact_present",
        "scope_overstatement_present", "provider_or_service_recommendation_present",
        "storage_required_claim_present", "clarity_score", "usefulness_score",
        "fallback_comparison", "reviewer", "bounded_review_notes",
    }
    if set(review) != expected or review["human_review_status"] not in REVIEW_STATUSES:
        raise V2LifecycleError("Human review fields are missing, unknown, or invalid.")
    for field in expected & {"grounding_supported", "invented_user_fact_present", "scope_overstatement_present", "provider_or_service_recommendation_present", "storage_required_claim_present"}:
        if not isinstance(review[field], bool):
            raise V2LifecycleError("Human review safety fields must be boolean.")
    if any(not isinstance(review[field], int) or not 1 <= review[field] <= 5 for field in ("clarity_score", "usefulness_score")):
        raise V2LifecycleError("Human review scores must be from 1 to 5.")
    if review["fallback_comparison"] not in FALLBACK_COMPARISONS:
        raise V2LifecycleError("Fallback comparison is invalid.")
    if not isinstance(review["reviewer"], str) or not review["reviewer"].strip():
        raise V2LifecycleError("Reviewer is required.")
    if not isinstance(review["bounded_review_notes"], str) or len(review["bounded_review_notes"]) > MAX_NOTES:
        raise V2LifecycleError("Review notes are invalid or unbounded.")
    safe_grounding = (
        review["grounding_supported"] is True
        and review["invented_user_fact_present"] is False
        and review["scope_overstatement_present"] is False
        and review["provider_or_service_recommendation_present"] is False
        and review["storage_required_claim_present"] is False
    )
    if review["human_review_status"] == "approved" and not safe_grounding:
        raise V2LifecycleError("Approved review must pass every grounding check.")
    paths = lifecycle_paths(output_root)
    audit = _load(paths["audit"])
    evidence_bytes = paths["evidence"].read_bytes()
    evidence = json.loads(evidence_bytes)
    MovingServiceQuestionResponseV2.model_validate(evidence)
    if hashlib.sha256(evidence_bytes).hexdigest() != audit.get("response_evidence_sha256"):
        raise V2LifecycleError("Response-evidence digest drifted.")
    stamp = _timestamp(now)
    record = {"run_series_id": RUN_SERIES_ID, "sequence": SEQUENCE, "fixture_id": FIXTURE_ID, **review, "reviewed_at": stamp}
    _exclusive(paths["review"], record)
    _update_audit(paths["audit"], {**review, "reviewed_at": stamp})
    delete_v2_response_evidence(output_root=output_root, reason="review_signoff", review_status=str(review["human_review_status"]), now=now)
    return record


def close_v2_pilot_and_update_audit(**kwargs: object) -> None:
    """Run the reviewed closure and reflect it in an existing bounded audit."""
    output_root = kwargs.pop("output_root", DEFAULT_OUTPUT_ROOT)
    paths = lifecycle_paths(output_root)
    close_v2_follow_up_authorization(closure_record_path=paths["closure"], **kwargs)
    if paths["audit"].exists():
        _update_audit(paths["audit"], {"authorization_closed": True, "closure_record_path": str(paths["closure"])})
