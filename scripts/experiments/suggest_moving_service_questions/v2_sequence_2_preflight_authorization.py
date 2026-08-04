"""Fixed sequence-2 preflight installation, review, planning, and activation API."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Mapping

from run_openai_stage_b_v2_pilot import DEFAULT_OUTPUT_ROOT
from v2_preflight_authorization_activation import (
    REPOSITORY_ROOT,
    activate_preflight_authorization,
    recover_preflight_activation,
)
from v2_preflight_authorization_installation import (
    install_preflight_for_review,
    plan_preflight_activation,
    review_preflight_activation,
    review_paths,
)
from v2_sequence_2_authorization_candidate import (
    CANDIDATE_PATH,
    MANIFEST_PATH,
    load_sequence_2_preflight_candidate,
)

SEQUENCE = 2
CANDIDATE_DIGEST = "389ab7811bd56d650e84d2f3e46c7d3f8f5e5cab6eee58019602b132d106bf7f"
CANDIDATE_MANIFEST_DIGEST = "c51b9ffcbb01ad7aa3f013eca05061b7ff5f432668944087f702cdfcd89dfb19"
OPERATOR_INTENT = "AUTHORIZE_ONE_STORAGE_UNKNOWN_V2_PREFLIGHT_ONLY"


def _options() -> dict[str, object]:
    return {
        "candidate_loader": load_sequence_2_preflight_candidate,
        "candidate_manifest": MANIFEST_PATH,
        "candidate_digest": CANDIDATE_DIGEST,
        "candidate_manifest_digest": CANDIDATE_MANIFEST_DIGEST,
    }


def sequence_2_review_paths(output_root: Path = DEFAULT_OUTPUT_ROOT) -> Mapping[str, Path]:
    return review_paths(output_root, sequence=SEQUENCE)


def install_sequence_2_for_review(
    *, source: Path, expected_sha256: str, now: datetime,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
) -> Mapping[str, object]:
    return install_preflight_for_review(
        source=source, expected_sha256=expected_sha256, now=now,
        output_root=output_root, sequence=SEQUENCE, **_options(),
    )


def review_sequence_2_activation(
    *, artifact_sha256: str, reviewer: str, decision: str, reviewed_at: str,
    notes: str, now: datetime, output_root: Path = DEFAULT_OUTPUT_ROOT,
) -> Mapping[str, object]:
    return review_preflight_activation(
        artifact_sha256=artifact_sha256, reviewer=reviewer, decision=decision,
        reviewed_at=reviewed_at, notes=notes, now=now, output_root=output_root,
        sequence=SEQUENCE, **_options(),
    )


def plan_sequence_2_activation(
    *, artifact_sha256: str, installation_record_sha256: str,
    activation_review_sha256: str, now: datetime,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
) -> Mapping[str, object]:
    return plan_preflight_activation(
        artifact_sha256=artifact_sha256,
        installation_record_sha256=installation_record_sha256,
        activation_review_sha256=activation_review_sha256, now=now,
        output_root=output_root, sequence=SEQUENCE, **_options(),
    )


def activate_sequence_2_preflight(
    *, artifact_sha256: str, installation_record_sha256: str,
    activation_review_sha256: str, operator: str, operator_intent: str,
    now: datetime, repository_root: Path = REPOSITORY_ROOT,
    output_root: Path = DEFAULT_OUTPUT_ROOT, failpoint: str | None = None,
    transaction_id_factory=lambda: __import__("uuid").uuid4().hex,
) -> Mapping[str, object]:
    if operator_intent != OPERATOR_INTENT:
        from v2_preflight_authorization_activation import ActivationReviewError
        raise ActivationReviewError("sequence-2 operator intent is invalid")
    return activate_preflight_authorization(
        artifact_sha256=artifact_sha256,
        installation_record_sha256=installation_record_sha256,
        activation_review_sha256=activation_review_sha256, operator=operator,
        operator_intent="activate exactly one v2 moving-service preflight authorization",
        now=now, repository_root=repository_root, output_root=output_root,
        failpoint=failpoint, transaction_id_factory=transaction_id_factory,
        sequence=SEQUENCE, installation_options=_options(),
    )


def recover_sequence_2_preflight(
    *, reason: str, now: datetime, repository_root: Path = REPOSITORY_ROOT,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
) -> Mapping[str, object]:
    return recover_preflight_activation(
        reason=reason, now=now, repository_root=repository_root,
        output_root=output_root, sequence=SEQUENCE,
    )
