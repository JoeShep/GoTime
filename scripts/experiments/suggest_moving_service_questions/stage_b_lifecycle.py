"""Offline review, retention, and closure lifecycle for the Stage B pilot."""

from __future__ import annotations

import hashlib
import json
import os
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

from pydantic import ValidationError

from real_model_adapter import MovingServiceQuestionResponse
from run_openai_stage_b_pilot import RUN_SERIES_ID, _paths
from run_real_model_evaluation import DEFAULT_MANIFEST_PATH, DEFAULT_OUTPUT_ROOT
from stage_b_authorization import (
    AUTHORIZATION_STATUS,
    AUTHORIZATION_VERSION,
    FINAL_ARTIFACT_PATH,
    MANIFEST_STATUS,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CLOSED_ARTIFACT_PATH = (
    "docs/experiments/suggest-moving-service-questions/v1/"
    "openai-execution-authorization.toml"
)
CLOSED_AUTHORIZATION_VERSION = "moving-service-openai-execution-authorization-v1"
CLOSED_AUTHORIZATION_STATUS = "closed_no_execution_authorized"
CLOSED_MANIFEST_STATUS = "openai_execution_authorization_closed"
CLOSED_AUTHORIZATION_DIGEST = (
    "6e3ca9cb4488764f012703ab77daae4f4b952895100f7d935935aeb6a0978be5"
)
REVIEW_STATUSES = frozenset({"approved", "rejected"})
FALLBACK_COMPARISONS = frozenset(
    {
        "materially_better",
        "slightly_better",
        "equivalent",
        "slightly_worse",
        "materially_worse",
    }
)
CLOSURE_REASONS = frozenset(
    {"success", "bounded_failure", "expiration", "operator_cancellation"}
)
DELETION_REASONS = frozenset({"review_signoff", "retention_deadline"})
MAXIMUM_REVIEW_NOTES_CHARACTERS = 500


class StageBLifecycleError(ValueError):
    """A bounded Stage B lifecycle transition failed closed."""


def lifecycle_paths(output_root: Path = DEFAULT_OUTPUT_ROOT) -> dict[str, Path]:
    audit, evidence = _paths(output_root)
    directory = audit.parent
    return {
        "audit": audit,
        "evidence": evidence,
        "review": directory / "001-storage_unknown-human-review.json",
        "deletion": directory / "001-storage_unknown-evidence-deletion.json",
        "closure": directory / "001-storage_unknown-generation-pilot-closure.json",
    }


def _utc_now(now: datetime | None) -> datetime:
    value = now or datetime.now(timezone.utc)
    if value.tzinfo is None:
        raise StageBLifecycleError("Lifecycle timestamps must be timezone-aware.")
    return value.astimezone(timezone.utc).replace(microsecond=0)


def _stamp(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _load_object(path: Path, label: str) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise StageBLifecycleError(f"Stage B {label} is unavailable or invalid.") from error
    if not isinstance(value, dict):
        raise StageBLifecycleError(f"Stage B {label} must be an object.")
    return value


def _write_exclusive(path: Path, value: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as output:
        json.dump(value, output, indent=2, sort_keys=True)
        output.write("\n")


def _update_audit_lifecycle(path: Path, updates: Mapping[str, object]) -> None:
    audit = _load_object(path, "audit record")
    unknown = set(updates) - set(audit)
    if unknown:
        raise StageBLifecycleError("Lifecycle update contains unknown audit fields.")
    audit.update(updates)
    temporary = path.with_name(f".{path.name}.lifecycle-update")
    if temporary.exists():
        raise StageBLifecycleError("A lifecycle audit update is already pending.")
    _write_exclusive(temporary, audit)
    os.replace(temporary, path)


def _validated_review_input(review: Mapping[str, object]) -> dict[str, object]:
    expected = {
        "human_review_status",
        "grounding_supported",
        "invented_user_fact_present",
        "scope_overstatement_present",
        "provider_or_service_recommendation_present",
        "storage_required_claim_present",
        "clarity_score",
        "usefulness_score",
        "fallback_comparison",
        "reviewer",
        "bounded_review_notes",
    }
    if set(review) != expected:
        raise StageBLifecycleError("Human review fields are missing or unknown.")
    status = review["human_review_status"]
    if status not in REVIEW_STATUSES:
        raise StageBLifecycleError("Human review status is unsupported.")
    for field in (
        "grounding_supported",
        "invented_user_fact_present",
        "scope_overstatement_present",
        "provider_or_service_recommendation_present",
        "storage_required_claim_present",
    ):
        if not isinstance(review[field], bool):
            raise StageBLifecycleError(f"Human review {field} must be boolean.")
    for field in ("clarity_score", "usefulness_score"):
        value = review[field]
        if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 5:
            raise StageBLifecycleError(f"Human review {field} must be from 1 to 5.")
    if review["fallback_comparison"] not in FALLBACK_COMPARISONS:
        raise StageBLifecycleError("Human review fallback comparison is unsupported.")
    reviewer = review["reviewer"]
    if not isinstance(reviewer, str) or not 1 <= len(reviewer.strip()) <= 100:
        raise StageBLifecycleError("Human reviewer identity is invalid.")
    notes = review["bounded_review_notes"]
    if not isinstance(notes, str) or len(notes) > MAXIMUM_REVIEW_NOTES_CHARACTERS:
        raise StageBLifecycleError("Human review notes are invalid or unbounded.")
    safe_grounding = (
        review["grounding_supported"] is True
        and review["invented_user_fact_present"] is False
        and review["scope_overstatement_present"] is False
        and review["provider_or_service_recommendation_present"] is False
        and review["storage_required_claim_present"] is False
    )
    if status == "approved" and not safe_grounding:
        raise StageBLifecycleError(
            "An approved human review must pass every grounding safety check."
        )
    return dict(review)


def delete_stage_b_response_evidence(
    *,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    reason: str,
    review_status: str,
    now: datetime | None = None,
) -> Mapping[str, object]:
    """Delete exact evidence once and create an idempotent bounded record."""
    if reason not in DELETION_REASONS or review_status not in REVIEW_STATUSES | {"not_reviewed"}:
        raise StageBLifecycleError("Evidence-deletion reason or review status is invalid.")
    paths = lifecycle_paths(output_root)
    if paths["deletion"].exists():
        return _load_object(paths["deletion"], "evidence deletion record")
    audit = _load_object(paths["audit"], "audit record")
    current = _utc_now(now)
    if reason == "review_signoff" and review_status not in REVIEW_STATUSES:
        raise StageBLifecycleError("Review sign-off requires a completed review.")
    if reason == "retention_deadline":
        deadline = audit.get("response_evidence_delete_by")
        if not isinstance(deadline, str):
            raise StageBLifecycleError("Evidence deletion deadline is unavailable.")
        try:
            deadline_value = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
        except ValueError as error:
            raise StageBLifecycleError("Evidence deletion deadline is invalid.") from error
        if current < deadline_value:
            raise StageBLifecycleError("The evidence retention deadline has not arrived.")
    evidence_existed = paths["evidence"].exists()
    if evidence_existed:
        paths["evidence"].unlink()
    record = {
        "run_series_id": RUN_SERIES_ID,
        "run_sequence": 1,
        "fixture_id": "storage_unknown",
        "evidence_path_identifier": paths["evidence"].name,
        "deletion_reason": reason,
        "deleted_at": _stamp(current),
        "review_status": review_status,
        "evidence_existed_before_deletion": evidence_existed,
        "deletion_completed": not paths["evidence"].exists(),
    }
    _write_exclusive(paths["deletion"], record)
    _update_audit_lifecycle(
        paths["audit"],
        {
            "response_evidence_deleted": record["deletion_completed"],
            "response_evidence_deletion_recorded_at": record["deleted_at"],
        },
    )
    return record


def finalize_stage_b_human_review(
    *,
    review: Mapping[str, object],
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    now: datetime | None = None,
) -> Mapping[str, object]:
    """Validate bounded review input, preserve provider evidence, then delete it."""
    paths = lifecycle_paths(output_root)
    if paths["review"].exists():
        raise FileExistsError("The Stage B human-review record already exists.")
    audit = _load_object(paths["audit"], "audit record")
    if audit.get("generation_succeeded") is not True or audit.get("semantic_validation_succeeded") is not True:
        raise StageBLifecycleError("Only a validated successful response can be reviewed.")
    try:
        evidence_bytes = paths["evidence"].read_bytes()
        evidence = json.loads(evidence_bytes)
        MovingServiceQuestionResponse.model_validate(evidence)
    except (OSError, json.JSONDecodeError, ValidationError) as error:
        raise StageBLifecycleError("Validated response evidence is unavailable or invalid.") from error
    if hashlib.sha256(evidence_bytes).hexdigest() != audit.get("response_evidence_sha256"):
        raise StageBLifecycleError("Response-evidence digest does not match the audit.")
    validated = _validated_review_input(review)
    reviewed_at = _stamp(_utc_now(now))
    record = {
        "run_series_id": RUN_SERIES_ID,
        "run_sequence": 1,
        "fixture_id": "storage_unknown",
        **validated,
        "reviewed_at": reviewed_at,
        "response_evidence_sha256": audit["response_evidence_sha256"],
    }
    _write_exclusive(paths["review"], record)
    _update_audit_lifecycle(
        paths["audit"],
        {**validated, "reviewed_at": reviewed_at},
    )
    delete_stage_b_response_evidence(
        output_root=output_root,
        reason="review_signoff",
        review_status=str(validated["human_review_status"]),
        now=now,
    )
    return record


def _verify_closed_authorization(repository_root: Path) -> Path:
    path = repository_root / CLOSED_ARTIFACT_PATH
    try:
        data = path.read_bytes()
        artifact = tomllib.loads(data.decode("utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        raise StageBLifecycleError("Permanent closed authorization is unavailable.") from error
    if hashlib.sha256(data).hexdigest() != CLOSED_AUTHORIZATION_DIGEST:
        raise StageBLifecycleError("Permanent closed authorization digest drifted.")
    permissions = artifact.get("authorization")
    if permissions != {
        "credential_access_authorized": False,
        "token_preflight_authorized": False,
        "ai_generation_authorized": False,
        "formal_evaluation_authorized": False,
    }:
        raise StageBLifecycleError("Permanent closed permissions drifted.")
    return path


def close_stage_b_authorization(
    *,
    reason: str,
    repository_root: Path = REPOSITORY_ROOT,
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    now: datetime | None = None,
) -> Mapping[str, object]:
    """Restore exact permanent closed authority without touching credentials."""
    if reason not in CLOSURE_REASONS:
        raise StageBLifecycleError("Stage B closure reason is unsupported.")
    paths = lifecycle_paths(output_root)
    if paths["closure"].exists():
        return _load_object(paths["closure"], "closure record")
    _verify_closed_authorization(repository_root)
    manifest = _load_object(manifest_path, "manifest")
    active_path = repository_root / FINAL_ARTIFACT_PATH
    currently_closed = (
        manifest.get("openai_execution_authorization_path") == CLOSED_ARTIFACT_PATH
        and manifest.get("openai_execution_authorization_digest") == CLOSED_AUTHORIZATION_DIGEST
        and manifest.get("status") == CLOSED_MANIFEST_STATUS
    )
    if not currently_closed:
        expected_active = {
            "openai_execution_authorization_path": FINAL_ARTIFACT_PATH,
            "openai_execution_authorization_version": AUTHORIZATION_VERSION,
            "openai_execution_authorization_status": AUTHORIZATION_STATUS,
            "status": MANIFEST_STATUS,
            "adapter_implementation_authorized": False,
            "real_model_execution_authorized": False,
            "real_model_evaluation_eligible": False,
        }
        if any(manifest.get(key) != value for key, value in expected_active.items()):
            raise StageBLifecycleError("Manifest is neither exact Stage B nor permanently closed.")
        digest = manifest.get("openai_execution_authorization_digest")
        if not isinstance(digest, str) or not active_path.exists() or hashlib.sha256(active_path.read_bytes()).hexdigest() != digest:
            raise StageBLifecycleError("Active Stage B authorization integrity failed.")
        manifest.update(
            {
                "artifact_version": "1.6.0",
                "openai_execution_authorization_path": CLOSED_ARTIFACT_PATH,
                "openai_execution_authorization_version": CLOSED_AUTHORIZATION_VERSION,
                "openai_execution_authorization_digest_algorithm": "sha256",
                "openai_execution_authorization_digest": CLOSED_AUTHORIZATION_DIGEST,
                "openai_execution_authorization_status": CLOSED_AUTHORIZATION_STATUS,
                "status": CLOSED_MANIFEST_STATUS,
                "adapter_implementation_authorized": False,
                "real_model_execution_authorized": False,
                "real_model_evaluation_eligible": False,
            }
        )
        temporary = manifest_path.with_name(f".{manifest_path.name}.stage-b-close")
        _write_exclusive(temporary, manifest)
        os.replace(temporary, manifest_path)
        active_path.unlink()
    elif active_path.exists():
        raise StageBLifecycleError("Closed manifest must not preserve an active Stage B artifact.")
    current = _utc_now(now)
    record = {
        "run_series_id": RUN_SERIES_ID,
        "run_sequence": 1,
        "fixture_id": "storage_unknown",
        "closure_reason": reason,
        "closure_status": "closed_and_verified",
        "closed_at": _stamp(current),
        "closed_authorization_path": CLOSED_ARTIFACT_PATH,
        "closed_authorization_digest": CLOSED_AUTHORIZATION_DIGEST,
        "active_stage_b_artifact_removed": not active_path.exists(),
        "credential_access_permitted_after_closure": False,
        "token_preflight_permitted_after_closure": False,
        "ai_generation_permitted_after_closure": False,
        "formal_evaluation_permitted_after_closure": False,
    }
    _write_exclusive(paths["closure"], record)
    if paths["audit"].exists():
        _update_audit_lifecycle(
            paths["audit"],
            {
                "authorization_closed": True,
                "closure_status": "closed_and_verified",
                "closure_record_path": str(paths["closure"]),
            },
        )
    return record
